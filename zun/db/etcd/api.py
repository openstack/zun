# Copyright 2016 IBM, Corp.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

"""etcd storage backend."""

import json

import etcd
from oslo_concurrency import lockutils
from oslo_log import log
from oslo_utils import strutils
from oslo_utils import timeutils
from oslo_utils import uuidutils
import six

from zun.common import exception
from zun.common.i18n import _
from zun.common.i18n import _LE
from zun.common import singleton
import zun.conf
from zun.db.etcd import models


LOG = log.getLogger(__name__)
CONF = zun.conf.CONF


def get_connection():
    connection = EtcdAPI(host=CONF.etcd.etcd_host,
                         port=CONF.etcd.etcd_port)
    return connection


def clean_all_data():
    conn = get_connection()
    conn.clean_all_zun_data()


def add_identity_filter(query, value):
    """Adds an identity filter to a query.

    Filters results by ID, if supplied value is a valid integer.
    Otherwise attempts to filter results by UUID.

    :param query: Initial query to add filter to.
    :param value: Value for filtering results by.
    :return: Modified query.
    """
    if strutils.is_int_like(value):
        return query.filter_by(id=value)
    elif uuidutils.is_uuid_like(value):
        return query.filter_by(uuid=value)
    else:
        raise exception.InvalidIdentity(identity=value)


def translate_etcd_result(etcd_result, model_type):
    """Translate etcd unicode result to etcd models."""
    try:
        data = json.loads(etcd_result.value)
        ret = None
        if model_type == 'container':
            ret = models.Container(data)
        elif model_type == 'zun_service':
            ret = models.ZunService(data)
        elif model_type == 'image':
            ret = models.Image(data)
        elif model_type == 'resource_class':
            ret = models.ResourceClass(data)
        else:
            raise exception.InvalidParameterValue(
                _('The model_type value: %s is invalid.'), model_type)
        return ret
    except (ValueError, TypeError) as e:
        LOG.error(_LE("Error occurred while translating etcd result: %s"),
                  six.text_type(e))
        raise


@six.add_metaclass(singleton.Singleton)
class EtcdAPI(object):
    """etcd API."""

    def __init__(self, host, port):
        self.client = etcd.Client(host=host, port=port)

    @lockutils.synchronized('etcd-client')
    def clean_all_zun_data(self):
        try:
            for d in self.client.read('/').children:
                if d.key in ('/containers',):
                    self.client.delete(d.key, recursive=True)
        except etcd.EtcdKeyNotFound as e:
            LOG.error(_LE('Error occurred while cleaning zun data: %s'),
                      six.text_type(e))
            raise

    def _add_tenant_filters(self, context, filters):
        filters = filters or {}
        if context.is_admin and context.all_tenants:
            return filters

        if context.project_id:
            filters['project_id'] = context.project_id
        else:
            filters['user_id'] = context.user_id

        return filters

    def _filter_resources(self, resources, filters):
        for c in list(resources):
            for k, v in filters.items():
                if c.get(k) != v:
                    resources.remove(c)
                    break

        return resources

    def _process_list_result(self, res_list, limit=None, sort_key=None):
        if len(res_list) == 0:
            return []
        sorted_res_list = res_list
        if sort_key:
            if not hasattr(res_list[0], sort_key):
                raise exception.InvalidParameterValue(
                    err='Container has no attribute: %s' % sort_key)
            sorted_res_list = sorted(res_list, key=lambda k: k.get(sort_key))

        if limit:
            sorted_res_list = sorted_res_list[0:limit]

        return sorted_res_list

    def list_containers(self, context, filters=None, limit=None,
                        marker=None, sort_key=None, sort_dir=None):
        try:
            res = getattr(self.client.read('/containers'), 'children', None)
        except etcd.EtcdKeyNotFound:
            # Before the first container been created, path '/containers'
            # does not exist.
            return []
        except Exception as e:
            LOG.error(
                _LE("Error occurred while reading from etcd server: %s"),
                six.text_type(e))
            raise

        containers = []
        for c in res:
            if c.value is not None:
                containers.append(translate_etcd_result(c, 'container'))
        filters = self._add_tenant_filters(context, filters)
        filtered_containers = self._filter_resources(
            containers, filters)
        return self._process_list_result(filtered_containers,
                                         limit=limit, sort_key=sort_key)

    def _validate_unique_container_name(self, context, name):
        if not CONF.compute.unique_container_name_scope:
            return
        lowername = name.lower()
        filters = {'name': name}
        if CONF.compute.unique_container_name_scope == 'project':
            filters['project_id'] = context.project_id
        elif CONF.compute.unique_container_name_scope == 'global':
            pass
        else:
            return

        try:
            containers = self.list_containers(context, filters=filters)
        except etcd.EtcdKeyNotFound:
            return
        except Exception as e:
            LOG.error(_LE('Error occurred while retrieving container: %s'),
                      six.text_type(e))
            raise
        if len(containers) > 0:
            raise exception.ContainerAlreadyExists(field='name',
                                                   value=lowername)

    @lockutils.synchronized('etcd_container')
    def create_container(self, context, container_data):
        # ensure defaults are present for new containers
        if not container_data.get('uuid'):
            container_data['uuid'] = uuidutils.generate_uuid()

        if container_data.get('name'):
            self._validate_unique_container_name(context,
                                                 container_data['name'])

        container = models.Container(container_data)
        try:
            container.save()
        except Exception:
            raise

        return container

    def get_container_by_uuid(self, context, container_uuid):
        try:
            res = self.client.read('/containers/' + container_uuid)
            container = translate_etcd_result(res, 'container')
            filtered_containers = self._filter_resources(
                [container], self._add_tenant_filters(context, {}))
            if len(filtered_containers) > 0:
                return filtered_containers[0]
            else:
                raise exception.ContainerNotFound(container=container_uuid)
        except etcd.EtcdKeyNotFound:
            raise exception.ContainerNotFound(container=container_uuid)
        except Exception as e:
            LOG.error(_LE('Error occurred while retrieving container: %s'),
                      six.text_type(e))
            raise

    def get_container_by_name(self, context, container_name):
        try:
            filters = self._add_tenant_filters(
                context, {'name': container_name})
            containers = self.list_containers(context, filters=filters)
        except etcd.EtcdKeyNotFound:
            raise exception.ContainerNotFound(container=container_name)
        except Exception as e:
            LOG.error(_LE('Error occurred while retrieving container: %s'),
                      six.text_type(e))
            raise

        if len(containers) > 1:
            raise exception.Conflict('Multiple containers exist with same '
                                     'name. Please use the container uuid '
                                     'instead.')
        elif len(containers) == 0:
            raise exception.ContainerNotFound(container=container_name)

        return containers[0]

    @lockutils.synchronized('etcd_container')
    def destroy_container(self, context, container_uuid):
        container = self.get_container_by_uuid(context, container_uuid)
        self.client.delete('/containers/' + container.uuid)

    @lockutils.synchronized('etcd_container')
    def update_container(self, context, container_uuid, values):
        # NOTE(yuywz): Update would fail if any other client
        # write '/containers/$CONTAINER_UUID' in the meanwhile
        if 'uuid' in values:
            msg = _("Cannot overwrite UUID for an existing Container.")
            raise exception.InvalidParameterValue(err=msg)

        if 'name' in values:
            self._validate_unique_container_name(context, values['name'])

        try:
            target_uuid = self.get_container_by_uuid(
                context, container_uuid).uuid
            target = self.client.read('/containers/' + target_uuid)
            target_value = json.loads(target.value)
            target_value.update(values)
            target.value = json.dumps(target_value)
            self.client.update(target)
        except etcd.EtcdKeyNotFound:
            raise exception.ContainerNotFound(container=container_uuid)
        except Exception as e:
            LOG.error(_LE('Error occurred while updating container: %s'),
                      six.text_type(e))
            raise

        return translate_etcd_result(target, 'container')

    @lockutils.synchronized('etcd_zunservice')
    def create_zun_service(self, values):
        values['created_at'] = timeutils.isotime()
        zun_service = models.ZunService(values)
        zun_service.save()
        return zun_service

    def list_zun_services(self, filters=None, limit=None,
                          marker=None, sort_key=None, sort_dir=None):
        try:
            res = getattr(self.client.read('/zun_services'), 'children', None)
        except etcd.EtcdKeyNotFound:
            LOG.error(
                _LE("Path '/zun_services' does not exist, seems etcd server "
                    "was not been initialized appropriately for Zun."))
            raise
        except Exception as e:
            LOG.error(
                _LE("Error occurred while reading from etcd server: %s"),
                six.text_type(e))
            raise

        services = []
        for c in res:
            if c.value is not None:
                services.append(translate_etcd_result(c, 'zun_service'))
        if filters:
            services = self._filter_resources(services, filters)
        return self._process_list_result(
            services, limit=limit, sort_key=sort_key)

    def list_zun_services_by_binary(self, binary):
        services = self.list_zun_services(filters={'binary': binary})
        return self._process_list_result(services)

    def get_zun_service(self, host, binary):
        try:
            service = None
            res = self.client.read('/zun_services/' + host + '_' + binary)
            service = translate_etcd_result(res, 'zun_service')
        except etcd.EtcdKeyNotFound:
            raise exception.ZunServiceNotFound(host=host, binary=binary)
        except Exception as e:
            LOG.error(_LE('Error occurred while retrieving zun service: %s'),
                      six.text_type(e))
            raise
        finally:
            return service

    @lockutils.synchronized('etcd_zunservice')
    def destroy_zun_service(self, host, binary):
        try:
            self.client.delete('/zun_services/' + host + '_' + binary)
        except etcd.EtcdKeyNotFound:
            raise exception.ZunServiceNotFound(host=host, binary=binary)
        except Exception as e:
            LOG.error(_LE('Error occurred while destroying zun service: %s'),
                      six.text_type(e))
            raise

    @lockutils.synchronized('etcd_zunservice')
    def update_zun_service(self, host, binary, values):
        try:
            target = self.client.read('/zun_services/' + host + '_' + binary)
            target_value = json.loads(target.value)
            values['updated_at'] = timeutils.isotime()
            target_value.update(values)
            target.value = json.dumps(target_value)
            self.client.update(target)
        except etcd.EtcdKeyNotFound:
            raise exception.ZunServiceNotFound(host=host, binary=binary)
        except Exception as e:
            LOG.error(_LE('Error occurred while updating service: %s'),
                      six.text_type(e))
            raise

    @lockutils.synchronized('etcd_image')
    def pull_image(self, context, values):
        if not values.get('uuid'):
            values['uuid'] = uuidutils.generate_uuid()
        repo = values.get('repo')
        tag = values.get('tag')

        image = self.get_image_by_repo_and_tag(context, repo, tag)
        if image:
            raise exception.ImageAlreadyExists(repo=repo, tag=tag)

        image = models.Image(values)
        image.save()
        return image

    @lockutils.synchronized('etcd_image')
    def update_image(self, image_uuid, values):
        if 'uuid' in values:
            msg = _('Cannot overwrite UUID for an existing image.')
            raise exception.InvalidParameterValue(err=msg)

        try:
            target = self.client.read('/images/' + image_uuid)
            target_value = json.loads(target.value)
            target_value.update(values)
            target.value = json.dumps(target_value)
            self.client.update(target)
        except etcd.EtcdKeyNotFound:
            raise exception.ImageNotFound(image=image_uuid)
        except Exception as e:
            LOG.error(_LE('Error occurred while updating image: %s'),
                      six.text_type(e))
            raise

        return translate_etcd_result(target, 'image')

    def list_images(self, context, filters=None, limit=None, marker=None,
                    sort_key=None, sort_dir=None):
        try:
            res = getattr(self.client.read('/images'), 'children', None)
        except etcd.EtcdKeyNotFound:
            # Before the first image been pulled, path '/image' does
            # not exist.
            return []
        except Exception as e:
            LOG.error(
                _LE("Error occurred while reading from etcd server: %s"),
                six.text_type(e))
            raise

        images = []
        for i in res:
            if i.value is not None:
                images.append(translate_etcd_result(i, 'image'))
        filters = self._add_tenant_filters(context, filters)
        filtered_images = self._filter_resources(images, filters)

        return self._process_list_result(filtered_images,
                                         limit=limit, sort_key=sort_key)

    def get_image_by_uuid(self, context, image_uuid):
        try:
            res = self.client.read('/images/' + image_uuid)
            image = translate_etcd_result(res, 'image')
            filtered_images = self._filter_resources(
                [image], self._add_tenant_filters(context, {}))
            if len(filtered_images) > 0:
                return filtered_images[0]
            else:
                raise exception.ImageNotFound(image=image_uuid)
        except etcd.EtcdKeyNotFound:
            raise exception.ImageNotFound(image=image_uuid)
        except Exception as e:
            LOG.error(_LE('Error occurred while retrieving image: %s'),
                      six.text_type(e))
            raise

    def get_image_by_repo_and_tag(self, context, repo, tag):
        filters = {'repo': repo, 'tag': tag}
        images = self.list_images(context, filters=filters)
        if len(images) == 0:
            return None
        return images[0]

    def list_resource_classes(self, context, filters=None, limit=None,
                              marker=None, sort_key=None, sort_dir=None):
        try:
            res = getattr(self.client.read('/resource_classes'),
                          'children', None)
        except etcd.EtcdKeyNotFound:
            return []
        except Exception as e:
            LOG.error(
                _LE('Error occurred while reading from etcd server: %s'),
                six.text_type(e))
            raise

        resource_classes = []
        for r in res:
            if r.value is not None:
                resource_classes.append(
                    translate_etcd_result(r, 'resource_class'))

        if filters:
            resource_classes = self._filter_resources(
                resource_classes, filters)

        return self._process_list_result(
            resource_classes, limit=limit, sort_key=sort_key)

    @lockutils.synchronized('etcd_resource_class')
    def create_resource_class(self, context, values):
        resource_class = models.ResourceClass(values)
        resource_class.save()
        return resource_class

    def get_resource_class(self, context, ident):
        if uuidutils.is_uuid_like(ident):
            return self._get_resource_class_by_uuid(context, ident)
        else:
            return self._get_resource_class_by_name(context, ident)

    def _get_resource_class_by_uuid(self, context, uuid):
        try:
            resource_class = None
            res = self.client.read('/resource_classes/' + uuid)
            resource_class = translate_etcd_result(res, 'resource_class')
        except etcd.EtcdKeyNotFound:
            raise exception.ResourceClassNotFound(resource_class=uuid)
        except Exception as e:
            LOG.error(
                _LE('Error occurred while retriving resource class: %s'),
                six.text_type(e))
            raise
        return resource_class

    def _get_resource_class_by_name(self, context, name):
        try:
            rcs = self.list_resource_classes(
                context, filters={'name': name})
        except etcd.EtcdKeyNotFound:
            raise exception.ResourceClassNotFound(resource_class=name)
        except Exception as e:
            LOG.error(
                _LE('Error occurred while retriving resource class: %s'),
                six.text_type(e))
            raise

        if len(rcs) > 1:
            raise exception.Conflict('Multiple resource classes exist with '
                                     'same name. Please use uuid instead.')
        elif len(rcs) == 0:
            raise exception.ResourceClassNotFound(resource_class=name)

        return rcs[0]

    @lockutils.synchronized('etcd_resource_class')
    def destroy_resource_class(self, context, uuid):
        resource_class = self._get_resource_class_by_uuid(context, uuid)
        self.client.delete('/resource_classes/' + resource_class.uuid)

    @lockutils.synchronized('etcd_resource_class')
    def update_resource_class(self, context, uuid, values):
        if 'uuid' in values:
            msg = _("Cannot override UUID for an existing resource class.")
            raise exception.InvalidParameterValue(err=msg)
        try:
            target = self.client.read('/resource_classes/' + uuid)
            target_value = json.loads(target.value)
            target_value.update(values)
            target.value = json.dumps(target_value)
            self.client.update(target)
        except etcd.EtcdKeyNotFound:
            raise exception.ResourceClassNotFound(resource_class=uuid)
        except Exception as e:
            LOG.error(
                _LE('Error occurred while updating resource class: %s'),
                six.text_type(e))
            raise
        return translate_etcd_result(target, 'resource_class')
