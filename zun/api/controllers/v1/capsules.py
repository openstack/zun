#    Copyright 2017 ARM Holdings.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

from oslo_log import log as logging

import pecan
import six

from zun.api.controllers import base
from zun.api.controllers import link
from zun.api.controllers.v1 import collection
from zun.api.controllers.v1.schemas import capsules as schema
from zun.api.controllers.v1.views import capsules_view as view
from zun.api import utils as api_utils
from zun.api import validation
from zun.common import consts
from zun.common import exception
from zun.common.i18n import _
from zun.common import name_generator
from zun.common import policy
from zun.common import utils
import zun.conf
from zun import objects
from zun.volume import cinder_api as cinder

CONF = zun.conf.CONF
LOG = logging.getLogger(__name__)


def _get_capsule(capsule_ident):
    """Get capsule by name or UUID"""
    capsule = api_utils.get_resource('Capsule', capsule_ident)
    if not capsule:
        pecan.abort(404, ('Not found; the capsule you requested '
                          'does not exist.'))
    return capsule


def check_policy_on_capsule(capsule, action):
    context = pecan.request.context
    policy.enforce(context, action, capsule, action=action)


class CapsuleCollection(collection.Collection):
    """API representation of a collection of Capsules."""

    fields = {
        'capsules',
        'next'
    }

    """A list containing capsules objects"""

    def __init__(self, **kwargs):
        self._type = 'capsules'

    @staticmethod
    def convert_with_links(rpc_capsules, limit, url=None,
                           expand=False, **kwargs):
        context = pecan.request.context
        collection = CapsuleCollection()
        collection.capsules = \
            [view.format_capsule(url, p, context) for p in rpc_capsules]
        collection.next = collection.get_next(limit, url=url, **kwargs)
        return collection


class CapsuleController(base.Controller):
    """Controller for Capsules"""

    _custom_actions = {

    }

    @pecan.expose('json')
    @exception.wrap_pecan_controller_exception
    def get_all(self, **kwargs):
        '''Retrieve a list of capsules.'''
        context = pecan.request.context
        policy.enforce(context, "capsule:get_all",
                       action="capsule:get_all")
        return self._get_capsules_collection(**kwargs)

    def _get_capsules_collection(self, **kwargs):
        context = pecan.request.context
        if utils.is_all_projects(kwargs):
            context.all_projects = True
        limit = api_utils.validate_limit(kwargs.get('limit'))
        sort_dir = api_utils.validate_sort_dir(kwargs.get('sort_dir', 'asc'))
        sort_key = kwargs.get('sort_key', 'id')
        resource_url = kwargs.get('resource_url')
        expand = kwargs.get('expand')
        filters = None
        marker_obj = None
        marker = kwargs.get('marker')
        if marker:
            marker_obj = objects.Capsule.get_by_uuid(context,
                                                     marker)
        capsules = objects.Capsule.list(context,
                                        limit,
                                        marker_obj,
                                        sort_key,
                                        sort_dir,
                                        filters=filters)

        return CapsuleCollection.convert_with_links(capsules, limit,
                                                    url=resource_url,
                                                    expand=expand,
                                                    sort_key=sort_key,
                                                    sort_dir=sort_dir)

    @pecan.expose('json')
    @api_utils.enforce_content_types(['application/json'])
    @exception.wrap_pecan_controller_exception
    @validation.validated(schema.capsule_create)
    def post(self, **capsule_dict):
        """Create a new capsule.

        :param capsule_dict: a capsule within the request body.
        """
        context = pecan.request.context
        compute_api = pecan.request.compute_api
        policy.enforce(context, "capsule:create",
                       action="capsule:create")

        # Abstract the capsule specification
        capsules_template = capsule_dict.get('template')

        spec_content, template_json = \
            utils.check_capsule_template(capsules_template)

        containers_spec = utils.capsule_get_container_spec(spec_content)
        volumes_spec = utils.capsule_get_volume_spec(spec_content)

        # Create the capsule Object
        new_capsule = objects.Capsule(context, **capsule_dict)
        new_capsule.project_id = context.project_id
        new_capsule.user_id = context.user_id
        new_capsule.status = consts.PENDING
        new_capsule.create(context)
        new_capsule.volumes = []
        capsule_need_cpu = 0
        capsule_need_memory = 0
        container_volume_requests = []

        if spec_content.get('restart_policy'):
            capsule_restart_policy = spec_content.get('restart_policy')
        else:
            # NOTE(hongbin): this is deprecated but we need to maintain
            # backward-compatibility. Will remove this branch in the future.
            capsule_restart_policy = template_json.get('restart_policy',
                                                       'always')
        container_restart_policy = {"MaximumRetryCount": "0",
                                    "Name": capsule_restart_policy}
        new_capsule.restart_policy = capsule_restart_policy

        metadata_info = template_json.get('metadata', None)
        requested_networks_info = template_json.get('nets', [])
        requested_networks = \
            utils.build_requested_networks(context, requested_networks_info)

        if metadata_info:
            new_capsule.meta_name = metadata_info.get('name', None)
            new_capsule.meta_labels = metadata_info.get('labels', None)

        # create the capsule in DB so that it generates a 'id'
        new_capsule.save()

        extra_spec = {}
        az_info = template_json.get('availabilityZone')
        if az_info:
            extra_spec['availability_zone'] = az_info

        # Generate Object for infra container
        sandbox_container = objects.Container(context)
        sandbox_container.project_id = context.project_id
        sandbox_container.user_id = context.user_id
        name = self._generate_name_for_capsule_sandbox(new_capsule)
        sandbox_container.name = name
        sandbox_container.capsule_id = new_capsule.id
        sandbox_container.image = CONF.sandbox_image
        sandbox_container.image_driver = CONF.sandbox_image_driver
        sandbox_container.image_pull_policy = \
            CONF.sandbox_image_pull_policy
        sandbox_container.status = consts.CREATING
        sandbox_container.create(context)
        new_capsule.containers_uuids = [sandbox_container.uuid]

        for container_spec in containers_spec:
            container_dict = container_spec
            container_dict['project_id'] = context.project_id
            container_dict['user_id'] = context.user_id
            name = self._generate_name_for_capsule_container(new_capsule)
            container_dict['name'] = name

            if container_dict.get('args') and container_dict.get('command'):
                container_dict['command'] = \
                    container_dict['command'] + container_dict['args']
                container_dict.pop('args')
            elif container_dict.get('args'):
                container_dict['command'] = container_dict['args']
                container_dict.pop('args')

            # NOTE(kevinz): Don't support port remapping, will find a
            # easy way to implement it.
            # if container need to open some port, just open it in container,
            # user can change the security group and getting access to port.
            if container_dict.get('ports'):
                container_dict.pop('ports')

            if container_dict.get('resources'):
                resources_list = container_dict.get('resources')
                allocation = resources_list.get('requests')
                if allocation.get('cpu'):
                    capsule_need_cpu += allocation.get('cpu')
                    container_dict['cpu'] = allocation.get('cpu')
                if allocation.get('memory'):
                    capsule_need_memory += allocation.get('memory')
                    container_dict['memory'] = str(allocation['memory'])
                container_dict.pop('resources')

            container_dict['restart_policy'] = container_restart_policy
            utils.check_for_restart_policy(container_dict)

            if container_dict.get('volumeMounts'):
                for volume in container_dict['volumeMounts']:
                    volume['container_name'] = name
                    container_volume_requests.append(volume)

            container_dict['status'] = consts.CREATING
            container_dict['interactive'] = True
            container_dict['capsule_id'] = new_capsule.id
            new_container = objects.Container(context, **container_dict)
            new_container.create(context)
            new_capsule.containers_uuids.append(new_container.uuid)

        # Deal with the volume support
        requested_volumes = \
            self._build_requested_volumes(context,
                                          volumes_spec,
                                          container_volume_requests,
                                          new_capsule)
        new_capsule.cpu = capsule_need_cpu
        new_capsule.memory = str(capsule_need_memory)
        new_capsule.save(context)
        compute_api.capsule_create(context, new_capsule, requested_networks,
                                   requested_volumes, extra_spec)
        # Set the HTTP Location Header
        pecan.response.location = link.build_url('capsules',
                                                 new_capsule.uuid)

        pecan.response.status = 202
        return view.format_capsule(pecan.request.host_url, new_capsule,
                                   context)

    @pecan.expose('json')
    @exception.wrap_pecan_controller_exception
    def get_one(self, capsule_ident):
        """Retrieve information about the given capsule.

        :param capsule_ident: UUID or name of a capsule.
        """
        context = pecan.request.context
        capsule = _get_capsule(capsule_ident)
        check_policy_on_capsule(capsule.as_dict(), "capsule:get")
        return view.format_capsule(pecan.request.host_url, capsule, context)

    @pecan.expose('json')
    @exception.wrap_pecan_controller_exception
    def delete(self, capsule_ident, **kwargs):
        """Delete a capsule.

        :param capsule_ident: UUID or Name of a capsule.
        """
        context = pecan.request.context
        if utils.is_all_projects(kwargs):
            policy.enforce(context, "capsule:delete_all_projects",
                           action="capsule:delete_all_projects")
            context.all_projects = True
        capsule = _get_capsule(capsule_ident)
        check_policy_on_capsule(capsule.as_dict(), "capsule:delete")
        compute_api = pecan.request.compute_api
        capsule.task_state = consts.CONTAINER_DELETING
        capsule.save(context)
        compute_api.capsule_delete(context, capsule)
        pecan.response.status = 204

    def _generate_name_for_capsule_container(self, new_capsule):
        """Generate a random name like: zeta-22-container."""
        name_gen = name_generator.NameGenerator()
        name = name_gen.generate()
        if new_capsule.meta_name is None:
            return 'capsule-' + new_capsule.uuid + '-' + name
        else:
            return 'capsule-' + new_capsule.meta_name + '-' + name

    def _generate_name_for_capsule_sandbox(self, new_capsule):
        """Generate sandbox name inside the capsule"""
        if new_capsule.meta_name is None:
            return 'capsule-' + new_capsule.uuid + '-' + 'sandbox'
        else:
            return 'capsule-' + new_capsule.meta_name + '-' + 'sandbox'

    def _transfer_different_field(self, field_tpl,
                                  field_container, **container_dict):
        """Transfer the template specified field to container_field"""
        if container_dict.get(field_tpl):
            container_dict[field_container] = api_utils.string_or_none(
                container_dict.get(field_tpl))
            container_dict.pop(field_tpl)
        return container_dict

    def _transfer_list_to_str(self, container_dict, field):
        if container_dict[field]:
            dict = None
            for k in range(0, len(container_dict[field])):
                if dict:
                    dict = dict + ' ' + container_dict[field][k]
                else:
                    dict = container_dict[field][k]
            container_dict[field] = dict
        return container_dict

    def _build_requested_volumes(self, context, volume_spec,
                                 volume_mounts, capsule):
        # NOTE(hongbin): We assume cinder is the only volume provider here.
        # The logic needs to be re-visited if a second volume provider
        # (i.e. Manila) is introduced.
        # NOTE(kevinz): We assume the volume_mounts has been pretreated,
        # there won't occur that volume multiple attach and no untapped
        # volume.
        cinder_api = cinder.CinderAPI(context)
        volume_driver = "cinder"
        requested_volumes = []
        volume_created = []
        try:
            for mount in volume_spec:
                mount_driver = mount[volume_driver]
                auto_remove = False
                if mount_driver.get("volumeID"):
                    uuid = mount_driver.get("volumeID")
                    volume = cinder_api.search_volume(uuid)
                    cinder_api.ensure_volume_usable(volume)
                else:
                    size = mount_driver.get("size")
                    volume = cinder_api.create_volume(size)
                    volume_created.append(volume)
                    if "autoRemove" in mount_driver.keys() \
                            and mount_driver.get("autoRemove", False):
                        auto_remove = True

                mount_destination = None
                container_name = None

                for item in volume_mounts:
                    if item['name'] == mount['name']:
                        mount_destination = item['mountPath']
                        container_name = item['container_name']
                        break

                if mount_destination and container_name:
                    volmapp = objects.VolumeMapping(
                        context,
                        volume_id=volume.id, volume_provider=volume_driver,
                        container_path=mount_destination,
                        user_id=context.user_id,
                        project_id=context.project_id,
                        auto_remove=auto_remove)
                    requested_volumes.append({container_name: volmapp})
                else:
                    msg = _("volume mount parameters is invalid.")
                    raise exception.Invalid(msg)
        except Exception as e:
            # if volume search or created failed, will remove all
            # the created volume. The existed volume will remain.
            for volume in volume_created:
                try:
                    cinder_api.delete_volume(volume.id)
                except Exception as exc:
                    LOG.error('Error on deleting volume "%s": %s.',
                              volume.id, six.text_type(exc))

            # Since the container and capsule database model has been created,
            # we need to delete them here due to the volume create failed.
            for container in capsule.containers:
                try:
                    container.destroy(context)
                except Exception as exc:
                    LOG.warning('fail to delete the container %s: %s',
                                container.uuid, exc)

            capsule.destroy(context)

            raise e

        return requested_volumes
