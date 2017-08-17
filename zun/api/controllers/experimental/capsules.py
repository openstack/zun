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
from oslo_utils import uuidutils
import pecan

from zun.api.controllers import base
from zun.api.controllers.experimental import collection
from zun.api.controllers.experimental.schemas import capsules as schema
from zun.api.controllers.experimental.views import capsules_view as view
from zun.api.controllers import link
from zun.api import utils as api_utils
from zun.common import consts
from zun.common import exception
from zun.common import name_generator
from zun.common import policy
from zun.common import utils
from zun.common import validation
from zun import objects

LOG = logging.getLogger(__name__)


def _get_capsule(capsule_id):
    capsule = api_utils.get_resource('Capsule', capsule_id)
    if not capsule:
        pecan.abort(404, ('Not found; the container you requested '
                          'does not exist.'))
    return capsule


def _get_container(container_id):
    container = api_utils.get_resource('Container', container_id)
    if not container:
        pecan.abort(404, ('Not found; the container you requested '
                          'does not exist.'))
    return container


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
        collection = CapsuleCollection()
        collection.capsules = \
            [view.format_capsule(url, p) for p in rpc_capsules]
        collection.next = collection.get_next(limit, url=url, **kwargs)
        return collection


class CapsuleController(base.Controller):
    '''Controller for Capsules'''

    _custom_actions = {

    }

    @pecan.expose('json')
    @api_utils.enforce_content_types(['application/json'])
    @exception.wrap_pecan_controller_exception
    @validation.validated(schema.capsule_create)
    def post(self, **capsule_dict):
        """Create a new capsule.

        :param capsule: a capsule within the request body.
        """
        context = pecan.request.context
        compute_api = pecan.request.compute_api
        policy.enforce(context, "capsule:create",
                       action="capsule:create")
        capsule_dict['capsule_version'] = 'alpha'
        capsule_dict['kind'] = 'capsule'

        capsules_spec = capsule_dict['spec']
        containers_spec = utils.check_capsule_template(capsules_spec)
        capsule_dict['uuid'] = uuidutils.generate_uuid()
        new_capsule = objects.Capsule(context, **capsule_dict)
        new_capsule.project_id = context.project_id
        new_capsule.user_id = context.user_id
        new_capsule.create(context)
        new_capsule.containers = []
        new_capsule.containers_uuids = []
        new_capsule.volumes = []
        count = len(containers_spec)

        capsule_restart_policy = capsules_spec.get('restart_policy', 'always')

        metadata_info = capsules_spec.get('metadata', None)
        requested_networks = capsules_spec.get('nets', [])
        if metadata_info:
            new_capsule.meta_name = metadata_info.get('name', None)
            new_capsule.meta_labels = metadata_info.get('labels', None)

        # Generate Object for infra container
        sandbox_container = objects.Container(context)
        sandbox_container.project_id = context.project_id
        sandbox_container.user_id = context.user_id
        name = self._generate_name_for_capsule_sandbox(
            capsule_dict['uuid'])
        sandbox_container.name = name
        sandbox_container.create(context)
        new_capsule.containers.append(sandbox_container)
        new_capsule.containers_uuids.append(sandbox_container.uuid)

        for k in range(count):
            container_dict = containers_spec[k]
            container_dict['project_id'] = context.project_id
            container_dict['user_id'] = context.user_id
            name = self._generate_name_for_capsule_container(
                capsule_dict['uuid'])
            container_dict['name'] = name

            if container_dict.get('args') and container_dict.get('command'):
                container_dict = self._transfer_list_to_str(container_dict,
                                                            'command')
                container_dict = self._transfer_list_to_str(container_dict,
                                                            'args')
                container_dict['command'] = \
                    container_dict['command'] + ' ' + container_dict['args']
                container_dict.pop('args')
            elif container_dict.get('command'):
                container_dict = self._transfer_list_to_str(container_dict,
                                                            'command')
            elif container_dict.get('args'):
                container_dict = self._transfer_list_to_str(container_dict,
                                                            'args')
                container_dict['command'] = container_dict['args']
                container_dict.pop('args')

            # NOTE(kevinz): Don't support pod remapping, will find a
            # easy way to implement it.
            # if container need to open some port, just open it in container,
            # user can change the security group and getting access to port.
            if container_dict.get('ports'):
                container_dict.pop('ports')

            if container_dict.get('resources'):
                resources_list = container_dict.get('resources')
                allocation = resources_list.get('allocation')
                if allocation.get('cpu'):
                    container_dict['cpu'] = allocation.get('cpu')
                if allocation.get('memory'):
                    container_dict['memory'] = \
                        str(allocation['memory']) + 'M'
                container_dict.pop('resources')

            if capsule_restart_policy:
                container_dict['restart_policy'] = \
                    {"MaximumRetryCount": "0",
                     "Name": capsule_restart_policy}
                self._check_for_restart_policy(container_dict)

            container_dict['status'] = consts.CREATING
            container_dict['interactive'] = True
            new_container = objects.Container(context, **container_dict)
            new_container.create(context)
            new_capsule.containers.append(new_container)
            new_capsule.containers_uuids.append(new_container.uuid)

        new_capsule.save(context)
        compute_api.capsule_create(context, new_capsule, requested_networks)
        # Set the HTTP Location Header
        pecan.response.location = link.build_url('capsules',
                                                 new_capsule.uuid)

        pecan.response.status = 202
        return view.format_capsule(pecan.request.host_url, new_capsule)

    def _generate_name_for_capsule_container(self, capsule_uuid=None):
        '''Generate a random name like: zeta-22-container.'''
        name_gen = name_generator.NameGenerator()
        name = name_gen.generate()
        return 'capsule-' + capsule_uuid + '-' + name

    def _generate_name_for_capsule_sandbox(self, capsule_uuid=None):
        '''Generate sandbox name inside the capsule'''
        return 'capsule-' + capsule_uuid + '-' + 'sandbox'

    def _transfer_different_field(self, field_tpl,
                                  field_container, **container_dict):
        '''Transfer the template specified field to container_field'''
        if container_dict.get(field_tpl):
            container_dict[field_container] = api_utils.string_or_none(
                container_dict.get(field_tpl))
            container_dict.pop(field_tpl)
        return container_dict

    def _check_for_restart_policy(self, container_dict):
        '''Check for restart policy input'''
        restart_policy = container_dict.get('restart_policy')
        if not restart_policy:
            return

        name = restart_policy.get('Name')
        num = restart_policy.setdefault('MaximumRetryCount', '0')
        count = int(num)
        if name in ['unless-stopped', 'always']:
            if count != 0:
                raise exception.InvalidValue(("maximum retry "
                                              "count not valid "
                                              "with restart policy "
                                              "of %s") % name)
        elif name in ['no']:
            container_dict.get('restart_policy')['MaximumRetryCount'] = '0'

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
