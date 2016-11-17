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
from oslo_log import log
from oslo_utils import strutils
from oslo_utils import uuidutils
import six

from zun.common import exception
from zun.common.i18n import _
from zun.common.i18n import _LE
from zun.common import singleton
import zun.conf
from zun.db.etcd import models


LOG = log.getLogger(__name__)


def get_connection():
    connection = EtcdAPI(host=zun.conf.CONF.etcd.etcd_host,
                         port=zun.conf.CONF.etcd.etcd_port)
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
            for k, v in six.iteritems(filters):
                if c.get(k) != v:
                    resources.remove(c)
                    break

        return resources

    def _process_list_result(self, res_list, limit=None, sort_key=None):
        sorted_res_list = res_list
        if sort_key:
            if not hasattr(res_list[0], sort_key):
                raise exception.InvalidParameterValue(
                    err='Container has no attribute: %s' % sort_key)
            sorted_res_list = sorted(res_list, key=lambda k: k.get(sort_key))

        if limit:
            sorted_res_list = sorted_res_list[0:limit]

        return sorted_res_list

    def list_container(self, context, filters=None, limit=None,
                       marker=None, sort_key=None, sort_dir=None):
        try:
            res = getattr(self.client.read('/containers'), 'children', None)
        except etcd.EtcdKeyNotFound:
            LOG.error(
                _LE("Path '/containers' does not exist, seems etcd server "
                    "was not been initialized appropriately for Zun."))
            raise
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

    def create_container(self, context, container_data):
        # ensure defaults are present for new containers
        # TODO(pksingh): need to add validation for same container
        # name validation in project and global scope
        if not container_data.get('uuid'):
            container_data['uuid'] = uuidutils.generate_uuid()

        container = models.Container(container_data)
        try:
            container.save()
        except Exception:
            raise

        return container

    def get_container_by_id(self, context, container_id):
        try:
            filters = self._add_tenant_filters(
                context, {'id': container_id})
            containers = self.list_container(context, filters=filters)
        except etcd.EtcdKeyNotFound:
            raise exception.ContainerNotFound(container=container_id)
        except Exception as e:
            LOG.error(_LE('Error occurred while retrieving container: %s'),
                      six.text_type(e))
            raise

        if len(containers) == 0:
            raise exception.ContainerNotFound(container=container_id)

        return containers[0]

    def get_container_by_uuid(self, context, container_uuid):
        try:
            res = self.client.read('/containers/' + container_uuid)
            container = translate_etcd_result(res, 'container')
            if container.get('project_id') == context.project_id or \
               container.get('user_id') == context.user_id:
                return container
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
            containers = self.list_container(context, filters=filters)
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

    def _get_container_by_ident(self, context, container_ident):
        if strutils.is_int_like(container_ident):
            container = self.get_container_by_id(context, container_ident)
        elif uuidutils.is_uuid_like(container_ident):
            container = self.get_container_by_uuid(context, container_ident)
        else:
            raise exception.InvalidIdentity(identity=container_ident)

        return container

    def destroy_container(self, context, container_ident):
        container = self._get_container_by_ident(context, container_ident)
        self.client.delete('/containers/' + container.uuid)

    def update_container(self, context, container_ident, values):
        # NOTE(yuywz): Update would fail if any other client
        # write '/containers/$CONTAINER_UUID' in the meanwhile
        if 'uuid' in values:
            msg = _("Cannot overwrite UUID for an existing Container.")
            raise exception.InvalidParameterValue(err=msg)

        try:
            target_uuid = self._get_container_by_ident(
                context, container_ident).uuid
            target = self.client.read('/containers/' + target_uuid)
            target_value = json.loads(target.value)
            target_value.update(values)
            target.value = json.dumps(target_value)
            self.client.update(target)
        except etcd.EtcdKeyNotFound:
            raise exception.ContainerNotFound(container=container_ident)
        except Exception as e:
            LOG.error(_LE('Error occurred while updating container: %s'),
                      six.text_type(e))
            raise

        return translate_etcd_result(target, 'container')

    def create_zun_service(self, values):
        zun_service = models.ZunService(values)
        zun_service.save()
        return zun_service

    def get_zun_service_list(self, disabled=None, limit=None,
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
        if disabled:
            filters = {'disabled': disabled}
            services = self._filter_resources(services, filters)
        return self._process_list_result(
            services, limit=limit, sort_key=sort_key)

    def get_zun_service(self, host, binary):
        try:
            res = self.client.read('/zun_services/' + host + '_' + binary)
            service = translate_etcd_result(res, 'zun_service')
        except etcd.EtcdKeyNotFound:
            raise exception.ZunServiceNotFound(host=host, binary=binary)
        except Exception as e:
            LOG.error(_LE('Error occurred while retrieving zun service: %s'),
                      six.text_type(e))
            raise

        return service

    def destroy_zun_service(self, host, binary):
        try:
            self.client.delete('/zun_services/' + host + '_' + binary)
        except etcd.EtcdKeyNotFound:
            raise exception.ZunServiceNotFound(host=host, binary=binary)
        except Exception as e:
            LOG.error(_LE('Error occurred while destroying zun service: %s'),
                      six.text_type(e))
            raise

    def update_zun_service(self, host, binary, values):
        try:
            target = self.client.read('/zun_services/' + host + '_' + binary)
            target_value = json.loads(target.value)
            target_value.update(values)
            target.value = json.dumps(target_value)
            self.client.update(target)
        except etcd.EtcdKeyNotFound:
            raise exception.ZunServiceNotFound(host=host, binary=binary)
        except Exception as e:
            LOG.error(_LE('Error occurred while updating service: %s'),
                      six.text_type(e))
            raise
