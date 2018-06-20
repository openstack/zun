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

from datetime import datetime
import etcd
from oslo_concurrency import lockutils
from oslo_log import log
from oslo_serialization import jsonutils as json
from oslo_utils import strutils
from oslo_utils import timeutils
from oslo_utils import uuidutils
import six

from zun.common import consts
from zun.common import exception
from zun.common.i18n import _
from zun.common import singleton
import zun.conf
from zun.db.etcd import models

LOG = log.getLogger(__name__)
CONF = zun.conf.CONF


def get_backend():
    connection = EtcdAPI(host=CONF.etcd.etcd_host,
                         port=CONF.etcd.etcd_port)
    return connection


def clean_all_data():
    conn = get_backend()
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
        elif model_type == 'compute_node':
            ret = models.ComputeNode(data)
        elif model_type == 'capsule':
            ret = models.Capsule(data)
        elif model_type == 'pcidevice':
            ret = models.PciDevice(data)
        elif model_type == 'volume_mapping':
            ret = models.VolumeMapping(data)
        elif model_type == 'container_action':
            ret = models.ContainerAction(data)
        elif model_type == 'container_action_event':
            ret = models.ContainerActionEvent(data)
        elif model_type == 'quota':
            ret = models.Quota(data)
        elif model_type == 'quota_class':
            ret = models.QuotaClass(data)
        elif model_type == 'quota_usage':
            ret = models.QuotaUsage(data)
        else:
            raise exception.InvalidParameterValue(
                _('The model_type value: %s is invalid.'), model_type)
        return ret
    except (ValueError, TypeError) as e:
        LOG.error("Error occurred while translating etcd result: %s",
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
            LOG.error('Error occurred while cleaning zun data: %s',
                      six.text_type(e))
            raise

    def _add_project_filters(self, context, filters):
        filters = filters or {}
        if context.is_admin and context.all_projects:
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
                "Error occurred while reading from etcd server: %s",
                six.text_type(e))
            raise

        containers = []
        for c in res:
            if c.value is not None:
                containers.append(translate_etcd_result(c, 'container'))
        filters = self._add_project_filters(context, filters)
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
            LOG.error('Error occurred while retrieving container: %s',
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
                [container], self._add_project_filters(context, {}))
            if len(filtered_containers) > 0:
                return filtered_containers[0]
            else:
                raise exception.ContainerNotFound(container=container_uuid)
        except etcd.EtcdKeyNotFound:
            raise exception.ContainerNotFound(container=container_uuid)
        except Exception as e:
            LOG.error('Error occurred while retrieving container: %s',
                      six.text_type(e))
            raise

    def get_container_by_name(self, context, container_name):
        try:
            filters = self._add_project_filters(
                context, {'name': container_name})
            containers = self.list_containers(context, filters=filters)
        except etcd.EtcdKeyNotFound:
            raise exception.ContainerNotFound(container=container_name)
        except Exception as e:
            LOG.error('Error occurred while retrieving container: %s',
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
            target.value = json.dump_as_bytes(target_value)
            self.client.update(target)
        except etcd.EtcdKeyNotFound:
            raise exception.ContainerNotFound(container=container_uuid)
        except Exception as e:
            LOG.error('Error occurred while updating container: %s',
                      six.text_type(e))
            raise

        return translate_etcd_result(target, 'container')

    @lockutils.synchronized('etcd_zunservice')
    def create_zun_service(self, values):
        values['created_at'] = datetime.isoformat(timeutils.utcnow())
        zun_service = models.ZunService(values)
        zun_service.save()
        return zun_service

    def list_zun_services(self, filters=None, limit=None,
                          marker=None, sort_key=None, sort_dir=None):
        try:
            res = getattr(self.client.read('/zun_services'), 'children', None)
        except etcd.EtcdKeyNotFound:
            LOG.error(
                ("Path '/zun_services' does not exist, seems etcd server "
                 "was not been initialized appropriately for Zun."))
            raise
        except Exception as e:
            LOG.error(
                "Error occurred while reading from etcd server: %s",
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
            LOG.error('Error occurred while retrieving zun service: %s',
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
            LOG.error('Error occurred while destroying zun service: %s',
                      six.text_type(e))
            raise

    @lockutils.synchronized('etcd_zunservice')
    def update_zun_service(self, host, binary, values):
        try:
            target = self.client.read('/zun_services/' + host + '_' + binary)
            target_value = json.loads(target.value)
            values['updated_at'] = datetime.isoformat(timeutils.utcnow())
            target_value.update(values)
            target.value = json.dump_as_bytes(target_value)
            self.client.update(target)
        except etcd.EtcdKeyNotFound:
            raise exception.ZunServiceNotFound(host=host, binary=binary)
        except Exception as e:
            LOG.error('Error occurred while updating service: %s',
                      six.text_type(e))
            raise

    @lockutils.synchronized('etcd_image')
    def destroy_image(self, context, img_id):
        try:
            self.client.delete('/images/' + img_id)
        except etcd.EtcdKeyNotFound:
            raise exception.ImageNotFound(image=img_id)
        except Exception as e:
            LOG.error('Error occurred while deleting image: %s',
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
            target.value = json.dump_as_bytes(target_value)
            self.client.update(target)
        except etcd.EtcdKeyNotFound:
            raise exception.ImageNotFound(image=image_uuid)
        except Exception as e:
            LOG.error('Error occurred while updating image: %s',
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
                "Error occurred while reading from etcd server: %s",
                six.text_type(e))
            raise

        images = []
        for i in res:
            if i.value is not None:
                images.append(translate_etcd_result(i, 'image'))
        filters = self._add_project_filters(context, filters)
        filtered_images = self._filter_resources(images, filters)

        return self._process_list_result(filtered_images,
                                         limit=limit, sort_key=sort_key)

    def get_image_by_uuid(self, context, image_uuid):
        try:
            res = self.client.read('/images/' + image_uuid)
            image = translate_etcd_result(res, 'image')
            filtered_images = self._filter_resources(
                [image], self._add_project_filters(context, {}))
            if len(filtered_images) > 0:
                return filtered_images[0]
            else:
                raise exception.ImageNotFound(image=image_uuid)
        except etcd.EtcdKeyNotFound:
            raise exception.ImageNotFound(image=image_uuid)
        except Exception as e:
            LOG.error('Error occurred while retrieving image: %s',
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
                'Error occurred while reading from etcd server: %s',
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
                'Error occurred while retriving resource class: %s',
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
                'Error occurred while retriving resource class: %s',
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
            target.value = json.dump_as_bytes(target_value)
            self.client.update(target)
        except etcd.EtcdKeyNotFound:
            raise exception.ResourceClassNotFound(resource_class=uuid)
        except Exception as e:
            LOG.error(
                'Error occurred while updating resource class: %s',
                six.text_type(e))
            raise
        return translate_etcd_result(target, 'resource_class')

    def get_compute_node_by_hostname(self, context, hostname):
        """Return a compute node.

        :param context: The security context
        :param hostname: The hostname of a compute node.
        :returns: A compute node.
        """
        try:
            compute_nodes = self.list_compute_nodes(
                context, filters={'hostname': hostname})
            if compute_nodes:
                return compute_nodes[0]
            else:
                raise exception.ComputeNodeNotFound(compute_node=hostname)
        except Exception as e:
            LOG.error('Error occurred while retrieving compute node: %s',
                      six.text_type(e))
            raise

    def _get_compute_node_by_uuid(self, context, uuid):
        try:
            compute_node = None
            res = self.client.read('/compute_nodes/' + uuid)
            compute_node = translate_etcd_result(res, 'compute_node')
        except etcd.EtcdKeyNotFound:
            raise exception.ComputeNodeNotFound(compute_node=uuid)
        except Exception as e:
            LOG.error(
                'Error occurred while retriving compute node: %s',
                six.text_type(e))
            raise
        return compute_node

    def get_compute_node(self, context, node_uuid):
        try:
            node = None
            res = self.client.read('/compute_nodes/' + node_uuid)
            node = translate_etcd_result(res, 'compute_node')
        except etcd.EtcdKeyNotFound:
            raise exception.ComputeNodeNotFound(compute_node=node_uuid)
        except Exception as e:
            LOG.error('Error occurred while retrieving zun compute nodes: %s',
                      six.text_type(e))
            raise
        return node

    @lockutils.synchronized('etcd_computenode')
    def update_compute_node(self, context, node_uuid, values):
        if 'uuid' in values:
            msg = _('Cannot overwrite UUID for an existing node.')
            raise exception.InvalidParameterValue(err=msg)

        try:
            target = self.client.read('/compute_nodes/' + node_uuid)
            target_value = json.loads(target.value)
            target_value.update(values)
            target.value = json.dumps(target_value)
            self.client.update(target)
        except etcd.EtcdKeyNotFound:
            raise exception.ComputeNodeNotFound(compute_node=node_uuid)
        except Exception as e:
            LOG.error(
                'Error occurred while updating compute node: %s',
                six.text_type(e))
            raise
        return translate_etcd_result(target, 'compute_node')

    @lockutils.synchronized('etcd_computenode')
    def create_compute_node(self, context, values):
        values['created_at'] = datetime.isoformat(timeutils.utcnow())
        if not values.get('uuid'):
            values['uuid'] = uuidutils.generate_uuid()
        compute_node = models.ComputeNode(values)
        compute_node.save()
        return compute_node

    @lockutils.synchronized('etcd_compute_node')
    def destroy_compute_node(self, context, node_uuid):
        compute_node = self._get_compute_node_by_uuid(context, node_uuid)
        self.client.delete('/compute_nodes/' + compute_node.uuid)

    def list_compute_nodes(self, context, filters=None, limit=None,
                           marker=None, sort_key=None, sort_dir=None):
        try:
            res = getattr(self.client.read('/compute_nodes'), 'children', None)
        except etcd.EtcdKeyNotFound:
            return []
        except Exception as e:
            LOG.error(
                "Error occurred while reading from etcd server: %s",
                six.text_type(e))
            raise

        compute_nodes = []
        for c in res:
            if c.value is not None:
                compute_nodes.append(translate_etcd_result(c, 'compute_node'))
        if filters:
            compute_nodes = self._filter_resources(compute_nodes, filters)
        return self._process_list_result(compute_nodes, limit=limit,
                                         sort_key=sort_key)

    def list_capsules(self, context, filters=None, limit=None,
                      marker=None, sort_key=None, sort_dir=None):
        try:
            res = getattr(self.client.read('/capsules'), 'children', None)
        except etcd.EtcdKeyNotFound:
            # Before the first container been created, path '/capsules'
            # does not exist.
            return []
        except Exception as e:
            LOG.error(
                "Error occurred while reading from etcd server: %s",
                six.text_type(e))
            raise

        capsules = []
        for c in res:
            if c.value is not None:
                capsules.append(translate_etcd_result(c, 'capsule'))
        filters = self._add_project_filters(context, filters)
        filtered_capsules = self._filter_resources(
            capsules, filters)
        return self._process_list_result(filtered_capsules,
                                         limit=limit, sort_key=sort_key)

    @lockutils.synchronized('etcd_capsule')
    def create_capsule(self, context, values):
        # ensure defaults are present for new capsules
        if not values.get('uuid'):
            values['uuid'] = uuidutils.generate_uuid()

        capsule = models.Capsule(values)
        try:
            capsule.save()
        except Exception:
            raise

        return capsule

    def get_capsule_by_uuid(self, context, capsule_uuid):
        try:
            res = self.client.read('/capsules/' + capsule_uuid)
            capsule = translate_etcd_result(res, 'capsule')
            filtered_capsules = self._filter_resources(
                [capsule], self._add_project_filters(context, {}))
            if len(filtered_capsules) > 0:
                return filtered_capsules[0]
            else:
                raise exception.CapsuleNotFound(capsule=capsule_uuid)
        except etcd.EtcdKeyNotFound:
            raise exception.CapsuleNotFound(capsule=capsule_uuid)
        except Exception as e:
            LOG.error('Error occurred while retrieving capsule: %s',
                      six.text_type(e))
            raise

    def get_capsule_by_meta_name(self, context, capsule_meta_name):
        try:
            filters = self._add_project_filters(
                context, {'meta_name': capsule_meta_name})
            capsules = self.list_capsules(context, filters=filters)
        except etcd.EtcdKeyNotFound:
            raise exception.CapsuleNotFound(capsule=capsule_meta_name)
        except Exception as e:
            LOG.error('Error occurred while retrieving capsule: %s',
                      six.text_type(e))
            raise

        if len(capsules) > 1:
            raise exception.Conflict('Multiple capsules exist with same '
                                     'meta name. Please use the capsule uuid '
                                     'instead.')
        elif len(capsules) == 0:
            raise exception.CapsuleNotFound(capsule=capsule_meta_name)

        return capsules[0]

    @lockutils.synchronized('etcd_capsule')
    def destroy_capsule(self, context, capsule_id):
        capsule = self.get_capsule_by_uuid(context, capsule_id)
        self.client.delete('/capsules/' + capsule.uuid)

    @lockutils.synchronized('etcd_capsule')
    def update_capsule(self, context, capsule_id, values):
        if 'uuid' in values:
            msg = _("Cannot overwrite UUID for an existing Capsule.")
            raise exception.InvalidParameterValue(err=msg)

        try:
            target_uuid = self.get_capsule_by_uuid(
                context, capsule_id).uuid
            target = self.client.read('/capsules/' + target_uuid)
            target_value = json.loads(target.value)
            target_value.update(values)
            target.value = json.dump_as_bytes(target_value)
            self.client.update(target)
        except etcd.EtcdKeyNotFound:
            raise exception.CapsuleNotFound(capsule=capsule_id)
        except Exception as e:
            LOG.error('Error occurred while updating capsule: %s',
                      six.text_type(e))
            raise

        return translate_etcd_result(target, 'capsule')

    def get_pci_device_by_addr(self, node_id, dev_addr):
        try:
            filters = {'compute_node_uuid': node_id,
                       'address': dev_addr}
            pcis = self.list_pci_devices(filters=filters)
        except etcd.EtcdKeyNotFound:
            raise exception.PciDeviceNotFound(node_id=node_id, address=None)
        except Exception as e:
            LOG.error('Error occurred while retrieving pci device: %s',
                      six.text_type(e))
            raise

        if len(pcis) == 0:
            raise exception.PciDeviceNotFound(node_id=node_id, address=None)
        return pcis

    def get_pci_device_by_id(self, id):
        try:
            filters = {'id': id}
            pcis = self.list_pci_devices(filters=filters)
        except etcd.EtcdKeyNotFound:
            raise exception.PciDeviceNotFoundById(id=id)
        except Exception as e:
            LOG.error('Error occurred while retrieving pci device: %s',
                      six.text_type(e))
            raise

        if len(pcis) == 0:
            raise exception.PciDeviceNotFoundById(id=id)
        return pcis

    def list_pci_devices(self, filters=None, limit=None, marker=None,
                         sort_key=None, sort_dir=None):
        try:
            res = getattr(self.client.read('/pcidevices'), 'children', None)
        except etcd.EtcdKeyNotFound:
            return []
        except Exception as e:
            LOG.error(
                "Error occurred while reading from etcd server: %s",
                six.text_type(e))
            raise

        pcis = []
        for p in res:
            if p.value is not None:
                pcis.append(translate_etcd_result(p, 'pcidevice'))
        filtered_pcis = self._filter_resources(pcis, filters)
        return self._process_list_result(filtered_pcis, limit=limit,
                                         sort_key=sort_key)

    def get_all_pci_device_by_node(self, node_id):
        try:
            filters = {'compute_node_uuid': node_id}
            return self.list_pci_devices(filters=filters)
        except Exception as e:
            LOG.error('Error occurred while retrieving pci device: %s',
                      six.text_type(e))
            raise

    def get_all_pci_device_by_parent_addr(self, node_id, parent_addr):
        try:
            filters = {'compute_node_uuid': node_id,
                       'parent_addr': parent_addr}
            return self.list_pci_devices(filters=filters)
        except Exception as e:
            LOG.error('Error occurred while retrieving pci device: %s',
                      six.text_type(e))
            raise

    def get_all_pci_device_by_container_uuid(self, container_uuid):
        try:
            filters = {'container_uuid': container_uuid}
            return self.list_pci_devices(filters=filters)
        except Exception as e:
            LOG.error('Error occurred while retrieving pci device: %s',
                      six.text_type(e))
            raise

    @lockutils.synchronized('etcd_pcidevice')
    def destroy_pci_device(self, node_id, address):
        pci_device = self.get_pci_device_by_addr(node_id, address)
        self.client.delete('/pcidevices/' + pci_device.uuid)

    def _create_pci_device(self, pci_device_data):
        if not pci_device_data.get('uuid'):
            pci_device_data['uuid'] = uuidutils.generate_uuid()

        pci_device = models.PciDevice(pci_device_data)
        try:
            pci_device.save()
        except Exception:
            raise

        return pci_device

    @lockutils.synchronized('etcd_pcidevice')
    def update_pci_device(self, node_id, address, values):
        try:
            pci_device = self.get_pci_device_by_addr(node_id, address)
            target = self.client.read('/pcidevices/' + pci_device.uuid)
            target_value = json.loads(target.value)
            target_value.update(values)
            target.value = json.dump_as_bytes(target_value)
            self.client.update(target)
        except exception.PciDeviceNotFound:
            values.update({'compute_node_uuid': node_id,
                           'address': address})
            return self._create_pci_device(values)
        except Exception as e:
            LOG.error('Error occurred while updating pci device: %s',
                      six.text_type(e))
            raise

        return translate_etcd_result(target, 'pcidevice')

    def list_volume_mappings(self, context, filters=None, limit=None,
                             marker=None, sort_key=None, sort_dir=None):
        try:
            res = getattr(self.client.read(
                '/volume_mappings'), 'children', None)
        except etcd.EtcdKeyNotFound:
            return []
        except Exception as e:
            LOG.error(
                "Error occurred while reading from etcd server: %s",
                six.text_type(e))
            raise

        volume_mappings = []
        for vm in res:
            if vm.value is not None:
                volume_mappings.append(
                    translate_etcd_result(vm, 'volume_mapping'))
        filters = self._add_project_filters(context, filters)
        filtered_vms = self._filter_resources(volume_mappings, filters)
        return self._process_list_result(filtered_vms, limit=limit,
                                         sort_key=sort_key)

    def create_volume_mapping(self, context, volume_mapping_data):
        if not volume_mapping_data.get('uuid'):
            volume_mapping_data['uuid'] = uuidutils.generate_uuid()

        volume_mapping = models.VolumeMapping(volume_mapping_data)
        try:
            volume_mapping.save()
        except Exception as e:
            LOG.error('Error occurred while creating volume mapping: %s',
                      six.text_type(e))
            raise

        return volume_mapping

    def get_volume_mapping_by_uuid(self, context, volume_mapping_uuid):
        try:
            res = self.client.read('/volume_mappings/' + volume_mapping_uuid)
            volume_mapping = translate_etcd_result(res, 'volume_mapping')
            filtered_vms = self._filter_resources(
                [volume_mapping], self._add_project_filters(context, {}))
            if filtered_vms:
                return filtered_vms[0]
            else:
                raise exception.VolumeMappingNotFound(
                    volume_mapping=volume_mapping_uuid)
        except etcd.EtcdKeyNotFound:
            raise exception.VolumeMappingNotFound(
                volume_mapping=volume_mapping_uuid)
        except Exception as e:
            LOG.error('Error occurred while retrieving volume mapping: %s',
                      six.text_type(e))
            raise

    def destroy_volume_mapping(self, context, volume_mapping_uuid):
        volume_mapping = self.get_volume_mapping_by_uuid(
            context, volume_mapping_uuid)
        self.client.delete('/volume_mappings/' + volume_mapping.uuid)

    def update_volume_mapping(self, context, volume_mapping_uuid, values):
        if 'uuid' in values:
            msg = _('Cannot overwrite UUID for an existing VolumeMapping.')
            raise exception.InvalidParameterValue(err=msg)

        try:
            target_uuid = self.get_volume_mapping_by_uuid(
                context, volume_mapping_uuid).uuid
            target = self.client.read('/volume_mapping/' + target_uuid)
            target_value = json.loads(target.value)
            target_value.update(values)
            target.value = json.dump_as_bytes(target_value)
            self.client.update(target)
        except etcd.EtcdKeyNotFound:
            raise exception.VolumeMappingNotFound(
                volume_mapping=volume_mapping_uuid)
        except Exception as e:
            LOG.error('Error occurred while updating volume mappping: %s',
                      six.text_type(e))
            raise

        return translate_etcd_result(target, 'volume_mapping')

    @lockutils.synchronized('etcd_action')
    def action_start(self, context, values):
        values['created_at'] = datetime.isoformat(timeutils.utcnow())
        if not values.get('uuid'):
            values['uuid'] = uuidutils.generate_uuid()

        action = models.ContainerAction(values)
        try:
            action.save()
        except Exception:
            raise
        return action

    def _actions_get(self, context, container_uuid, filters=None):
        action_path = '/container_actions/' + container_uuid

        try:
            res = getattr(self.client.read(action_path), 'children', None)
        except etcd.EtcdKeyNotFound:
            return []
        except Exception as e:
            LOG.error(
                "Error occurred while reading from etcd server: %s",
                six.text_type(e))
            raise

        actions = []
        for c in res:
            if c.value is not None:
                actions.append(translate_etcd_result(c, 'container_action'))
        filters = self._add_project_filters(context, filters)
        filtered_actions = self._filter_resources(actions, filters)
        sorted_actions = self._process_list_result(filtered_actions,
                                                   sort_key='created_at')
        # Actions need descending order of created_at.
        sorted_actions.reverse()
        return sorted_actions

    def actions_get(self, context, container_uuid):
        return self._actions_get(context, container_uuid)

    def _action_get_by_request_id(self, context, container_uuid, request_id):
        filters = {'request_id': request_id}
        actions = self._actions_get(context, container_uuid, filters=filters)
        if not actions:
            return None
        return actions[0]

    def action_get_by_request_id(self, context, container_uuid, request_id):
        return self._action_get_by_request_id(context, container_uuid,
                                              request_id)

    @lockutils.synchronized('etcd_action')
    def action_event_start(self, context, values):
        """Start an event on a container action."""
        action = self._action_get_by_request_id(context,
                                                values['container_uuid'],
                                                values['request_id'])

        # When zun-compute restarts, the request_id was different with
        # request_id recorded in ContainerAction, so we can't get the original
        # recode according to request_id. Try to get the last created action
        # so that init_container can continue to finish the recovery action.
        if not action and not context.project_id:
            actions = self._actions_get(context, values['container_uuid'])
            if not actions:
                action = actions[0]

        if not action:
            raise exception.ContainerActionNotFound(
                request_id=values['request_id'],
                container_uuid=values['container_uuid'])

        values['action_id'] = action['id']
        values['action_uuid'] = action['uuid']

        values['created_at'] = datetime.isoformat(timeutils.utcnow())
        if not values.get('uuid'):
            values['uuid'] = uuidutils.generate_uuid()

        event = models.ContainerActionEvent(values)
        try:
            event.save()
        except Exception:
            raise
        return event

    def _action_events_get(self, context, action_uuid, filters=None):
        event_path = '/container_actions_events/' + action_uuid

        try:
            res = getattr(self.client.read(event_path), 'children', None)
        except etcd.EtcdKeyNotFound:
            return []
        except Exception as e:
            LOG.error(
                "Error occurred while reading from etcd server: %s",
                six.text_type(e))
            raise

        events = []
        for c in res:
            if c.value is not None:
                events.append(translate_etcd_result(
                    c, 'container_action_event'))

        filters = filters or {}
        filtered_events = self._filter_resources(events, filters)
        sorted_events = self._process_list_result(filtered_events,
                                                  sort_key='created_at')
        # Events need descending order of created_at.
        sorted_events.reverse()
        return sorted_events

    def _get_event_by_name(self, context, action_uuid, event_name):
        filters = {'event': event_name}
        events = self._action_events_get(context, action_uuid, filters)
        if not events:
            return None
        return events[0]

    @lockutils.synchronized('etcd_action')
    def action_event_finish(self, context, values):
        """Finish an event on a container action."""
        action = self._action_get_by_request_id(context,
                                                values['container_uuid'],
                                                values['request_id'])

        # When zun-compute restarts, the request_id was different with
        # request_id recorded in ContainerAction, so we can't get the original
        # recode according to request_id. Try to get the last created action
        # so that init_container can continue to finish the recovery action.
        if not action and not context.project_id:
            actions = self._actions_get(context, values['container_uuid'])
            if not actions:
                action = actions[0]

        if not action:
            raise exception.ContainerActionNotFound(
                request_id=values['request_id'],
                container_uuid=values['container_uuid'])

        event = self._get_event_by_name(context, action['uuid'],
                                        values['event'])

        if not event:
            raise exception.ContainerActionEventNotFound(
                action_id=action['uuid'], event=values['event'])

        try:
            target_path = '/container_actions_events/{0}/{1}'.\
                format(action['uuid'], event['uuid'])
            target = self.client.read(target_path)
            target_values = json.loads(target.value)
            target_values.update(values)
            target.value = json.dump_as_bytes(target_values)
            self.client.update(target)
        except etcd.EtcdKeyNotFound:
            raise exception.ContainerActionEventNotFound(
                action_id=action['uuid'], event=values['event'])
        except Exception as e:
            LOG.error('Error occurred while updating action event: %s',
                      six.text_type(e))
            raise

        if values['result'].lower() == 'error':
            try:
                target_path = '/container_actions/{0}/{1}'.\
                    format(action['container_uuid'], action['uuid'])
                target = self.client.read(target_path)
                target_values = json.loads(target.value)
                target_values.update({'message': 'Error'})
                target.value = json.dump_as_bytes(target_values)
                self.client.update(target)
            except etcd.EtcdKeyNotFound:
                raise exception.ContainerActionNotFound(
                    request_id=action['request_id'],
                    container_uuid=action['container_uuid'])
            except Exception as e:
                LOG.error('Error occurred while updating action : %s',
                          six.text_type(e))
                raise

        return event

    def action_events_get(self, context, action_id):
        events = self._action_events_get(context, action_id)
        return events

    def quota_get(self, context, project_id, resource):
        try:
            res = self.client.read(
                '/quotas/{}/{}'. format(project_id, resource))
            if res.value is not None:
                return translate_etcd_result(res, 'quota')
            else:
                raise exception.QuotaNotFound()
        except etcd.EtcdKeyNotFound:
            raise exception.QuotaNotFound()
        except Exception as e:
            LOG.error('Error occurred while retrieving quota: %s',
                      six.text_type(e))
            raise

    def quota_get_all_by_project(self, context, project_id):
        try:
            res = getattr(self.client.read('/quotas/{}'. format(project_id)),
                          'children', None)
            quotas = []
            for q in res:
                if q.value is not None:
                    quotas.append(translate_etcd_result(q, 'quota'))
            return quotas
        except etcd.EtcdKeyNotFound:
            return []
        except Exception as e:
            LOG.error('Error occurred while retrieving quota: %s',
                      six.text_type(e))
            raise

    @lockutils.synchronized('etcd_quota')
    def quota_create(self, context, project_id, resource, limit):
        quota_data = {
            'project_id': project_id,
            'resource': resource,
            'hard_limit': limit,
            'created_at': datetime.isoformat(timeutils.utcnow()),
            'uuid': uuidutils.generate_uuid()
        }

        quota = models.Quota(quota_data)
        try:
            quota.save()
        except Exception:
            raise

        return quota

    @lockutils.synchronized('etcd_quota')
    def quota_update(self, context, project_id, resource, limit):
        quota_data = {
            'project_id': project_id,
            'resource': resource,
            'hard_limit': limit,
        }
        try:
            target = self.client.read(
                '/quotas/{}/{}' . format(project_id, resource))
            target_value = json.loads(target.value)
            quota_data['updated_at'] = datetime.isoformat(timeutils.utcnow())
            target_value.update(quota_data)
            target.value = json.dump_as_bytes(target_value)
            self.client.update(target)
        except etcd.EtcdKeyNotFound:
            raise exception.QuotaNotFound()
        except Exception as e:
            LOG.error('Error occurred while updating quota: %s',
                      six.text_type(e))
            raise

    @lockutils.synchronized('etcd_quota')
    def quota_destroy(self, context, project_id, resource):
        self.client.delete('/quotas/{}/{}' . format(project_id, resource))

    @lockutils.synchronized('etcd_quota')
    def quota_destroy_all_by_project(self, context, project_id):
        self.client.delete('/quotas/{}' . format(project_id))
        self.client.delete('/quota_usages/{}' . format(project_id))

    def quota_class_create(self, context, class_name, resource, limit):
        quota_class_data = {
            'class_name': class_name,
            'resource': resource,
            'hard_limit': limit,
            'created_at': datetime.isoformat(timeutils.utcnow()),
            'uuid': uuidutils.generate_uuid()
        }

        quota_class = models.QuotaClass(quota_class_data)
        try:
            quota_class.save()
        except Exception:
            raise

        return quota_class

    def quota_class_get(self, context, class_name, resource):
        try:
            res = self.client.read(
                '/quota_classes/{}/{}'. format(class_name,
                                               resource))
            if res.value is not None:
                return translate_etcd_result(res, 'quota_class')
            else:
                raise exception.QuotaClassNotFound()
        except etcd.EtcdKeyNotFound:
            raise exception.QuotaClassNotFound()
        except Exception as e:
            LOG.error('Error occurred while retrieving quota class: %s',
                      six.text_type(e))
            raise

    def _quota_class_get_all_by_name(self, context, class_name=None):
        if class_name is None or class_name == 'default':
            class_name = consts.DEFAULT_QUOTA_CLASS_NAME

        try:
            res = getattr(self.client.read(
                '/quota_classes/{}' . format(class_name)),
                'children', None)
            quota_classes = []
            for qc in res:
                if qc.value is not None:
                    quota_classes.append(translate_etcd_result(
                        qc, 'quota_class'))
            return quota_classes
        except etcd.EtcdKeyNotFound:
            return []
        except Exception as e:
            LOG.error('Error occurred while retrieving quota class: %s',
                      six.text_type(e))
            raise

    def quota_class_get_default(self, context):
        return self._quota_class_get_all_by_name(context)

    def quota_class_get_all_by_name(self, context, class_name):
        return self._quota_class_get_all_by_name(
            context, class_name=class_name)

    def quota_class_update(self, context, class_name, resource, limit):
        quota_class_data = {
            'class_name': class_name,
            'resource': resource,
            'hard_limit': limit,
        }
        try:
            target = self.client.read(
                '/quota_classes/{}/{}' . format(class_name, resource))
            target_value = json.loads(target.value)
            quota_class_data['updated_at'] = datetime.isoformat(
                timeutils.utcnow())
            target_value.update(quota_class_data)
            target.value = json.dump_as_bytes(target_value)
            self.client.update(target)
        except etcd.EtcdKeyNotFound:
            raise exception.QuotaClassNotFound()
        except Exception as e:
            LOG.error('Error occurred while updating quota class: %s',
                      six.text_type(e))
            raise

    def quota_usage_get_all_by_project(self, context, project_id):
        try:
            res = getattr(
                self.client.read('/quota_usages/{}' . format(project_id)),
                'children', None)
            if res.value is not None:
                return translate_etcd_result(res, 'quota_usage')
            else:
                raise exception.QuotaUsageNotFound()
        except etcd.EtcdKeyNotFound:
            raise exception.QuotaUsageNotFound()
        except Exception as e:
            LOG.error('Error occurred while retrieving quota usage: %s',
                      six.text_type(e))

    @lockutils.synchronized('etcd_network')
    def create_network(self, context, network_value):
        if not network_value.get('uuid'):
            network_value['uuid'] = uuidutils.generate_uuid()
        if network_value.get('name'):
            self._validate_unique_container_name(context,
                                                 network_value['name'])
        network = models.Network(network_value)
        try:
            network.save()
        except Exception:
            raise
        return network
