# Copyright 2013 UnitedStack Inc.
# All Rights Reserved.
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

import shlex

from neutronclient.common import exceptions as n_exc
from oslo_log import log as logging
from oslo_utils import strutils
from oslo_utils import uuidutils
import pecan
import six

from zun.api.controllers import base
from zun.api.controllers import link
from zun.api.controllers.v1 import collection
from zun.api.controllers.v1.schemas import containers as schema
from zun.api.controllers.v1.views import containers_view as view
from zun.api import utils as api_utils
from zun.api import validation
from zun.common import consts
from zun.common import context as zun_context
from zun.common import exception
from zun.common.i18n import _
from zun.common import name_generator
from zun.common.policies import container as policies
from zun.common import policy
from zun.common import utils
import zun.conf
from zun.network import model as network_model
from zun.network import neutron
from zun import objects
from zun.pci import request as pci_request
from zun.volume import cinder_api as cinder

CONF = zun.conf.CONF
LOG = logging.getLogger(__name__)


def check_policy_on_container(container, action):
    context = pecan.request.context
    policy.enforce(context, action, container, action=action)


class ContainerCollection(collection.Collection):
    """API representation of a collection of containers."""

    fields = {
        'containers',
        'next'
    }

    """A list containing containers objects"""

    def __init__(self, **kwargs):
        super(ContainerCollection, self).__init__(**kwargs)
        self._type = 'containers'

    @staticmethod
    def convert_with_links(rpc_containers, limit, url=None,
                           expand=False, **kwargs):
        context = pecan.request.context
        collection = ContainerCollection()
        collection.containers = \
            [view.format_container(context, url, p.as_dict())
             for p in rpc_containers]
        collection.next = collection.get_next(limit, url=url, **kwargs)
        return collection


class ContainersActionsController(base.Controller):
    """Controller for Container Actions."""

    def __init__(self):
        super(ContainersActionsController, self).__init__()
        self._action_keys = ['action', 'container_uuid', 'request_id',
                             'user_id', 'project_id', 'start_time',
                             'message']
        self._event_keys = ['event', 'start_time', 'finish_time', 'result',
                            'traceback']

    def _format_action(self, action_raw):
        action = {}
        action_dict = action_raw.as_dict()
        for key in self._action_keys:
            action[key] = action_dict.get(key)
        return action

    def _format_event(self, event_raw, show_traceback=False):
        event = {}
        event_dict = event_raw.as_dict()
        for key in self._event_keys:
            # By default, non-admins are not allowed to see traceback details.
            if key == 'traceback' and not show_traceback:
                event['traceback'] = None
                continue
            event[key] = event_dict.get(key)
        return event

    @pecan.expose('json')
    @exception.wrap_pecan_controller_exception
    def get_all(self, container_ident, **kwargs):
        """Retrieve a list of container actions."""
        context = pecan.request.context
        policy.enforce(context, "container:actions",
                       action="container:actions")
        container = utils.get_container(container_ident)
        actions_raw = objects.ContainerAction.get_by_container_uuid(
            context, container.uuid)
        actions = [self._format_action(action) for action in actions_raw]

        return {"containerActions": actions}

    @pecan.expose('json')
    @exception.wrap_pecan_controller_exception
    def get_one(self, container_ident, request_ident, **kwargs):
        """Retrieve information about the action."""

        context = pecan.request.context
        policy.enforce(context, "container:actions",
                       action="container:actions")
        container = utils.get_container(container_ident)
        action = objects.ContainerAction.get_by_request_id(
            context, container.uuid, request_ident)

        if action is None:
            raise exception.ResourceNotFound(name="Action", id=request_ident)

        action_id = action.id
        if CONF.database.backend == 'etcd':
            # etcd using action.uuid get the unique action instead of action.id
            action_id = action.uuid

        action = self._format_action(action)
        show_traceback = False
        if policy.enforce(context, "container:action:events",
                          do_raise=False, action="container:action:events"):
            show_traceback = True

        events_raw = objects.ContainerActionEvent.get_by_action(context,
                                                                action_id)
        action['events'] = [self._format_event(evt, show_traceback)
                            for evt in events_raw]
        return action


class ContainersController(base.Controller):
    """Controller for Containers."""

    _custom_actions = {
        'start': ['POST'],
        'stop': ['POST'],
        'reboot': ['POST'],
        'rebuild': ['POST'],
        'pause': ['POST'],
        'unpause': ['POST'],
        'logs': ['GET'],
        'execute': ['POST'],
        'execute_resize': ['POST'],
        'kill': ['POST'],
        'rename': ['POST'],
        'attach': ['GET'],
        'resize': ['POST'],
        'resize_container': ['POST'],
        'top': ['GET'],
        'get_archive': ['GET'],
        'put_archive': ['POST'],
        'stats': ['GET'],
        'commit': ['POST'],
        'add_security_group': ['POST'],
        'network_detach': ['POST'],
        'network_attach': ['POST'],
        'network_list': ['GET'],
        'remove_security_group': ['POST']
    }

    container_actions = ContainersActionsController()

    @pecan.expose('json')
    @exception.wrap_pecan_controller_exception
    def get_all(self, **kwargs):
        """Retrieve a list of containers.

        """
        context = pecan.request.context
        policy.enforce(context, "container:get_all",
                       action="container:get_all")
        return self._get_containers_collection(**kwargs)

    def _get_containers_collection(self, **kwargs):
        context = pecan.request.context
        if utils.is_all_projects(kwargs):
            policy.enforce(context, "container:get_all_all_projects",
                           action="container:get_all_all_projects")
            context.all_projects = True
        kwargs.pop('all_projects', None)
        limit = api_utils.validate_limit(kwargs.pop('limit', None))
        sort_dir = api_utils.validate_sort_dir(kwargs.pop('sort_dir', 'asc'))
        sort_key = kwargs.pop('sort_key', 'id')
        resource_url = kwargs.pop('resource_url', None)
        expand = kwargs.pop('expand', None)

        container_allowed_filters = ['name', 'image', 'project_id', 'user_id',
                                     'memory', 'host', 'task_state', 'status',
                                     'auto_remove']
        filters = {}
        for filter_key in container_allowed_filters:
            if filter_key in kwargs:
                policy_action = policies.CONTAINER % ('get_one:' + filter_key)
                context.can(policy_action, might_not_exist=True)
                filter_value = kwargs.pop(filter_key)
                filters[filter_key] = filter_value
        marker_obj = None
        marker = kwargs.pop('marker', None)
        if marker:
            marker_obj = objects.Container.get_by_uuid(context,
                                                       marker)
        if kwargs:
            unknown_params = [str(k) for k in kwargs]
            msg = _("Unknown parameters: %s") % ", ".join(unknown_params)
            raise exception.InvalidValue(msg)

        containers = objects.Container.list(context,
                                            limit,
                                            marker_obj,
                                            sort_key,
                                            sort_dir,
                                            filters=filters)
        return ContainerCollection.convert_with_links(containers, limit,
                                                      url=resource_url,
                                                      expand=expand,
                                                      sort_key=sort_key,
                                                      sort_dir=sort_dir)

    @pecan.expose('json')
    @exception.wrap_pecan_controller_exception
    def get_one(self, container_ident, **kwargs):
        """Retrieve information about the given container.

        :param container_ident: UUID or name of a container.
        """
        context = pecan.request.context
        if utils.is_all_projects(kwargs):
            policy.enforce(context, "container:get_one_all_projects",
                           action="container:get_one_all_projects")
            context.all_projects = True
        container = utils.get_container(container_ident)
        check_policy_on_container(container.as_dict(), "container:get_one")
        if container.host:
            compute_api = pecan.request.compute_api
            try:
                container = compute_api.container_show(context, container)
            except exception.ContainerHostNotUp:
                raise exception.ServerNotUsable

        return view.format_container(context, pecan.request.host_url,
                                     container.as_dict())

    def _generate_name_for_container(self):
        """Generate a random name like: zeta-22-container."""
        name_gen = name_generator.NameGenerator()
        name = name_gen.generate()
        return name + '-container'

    @base.Controller.api_version("1.1", "1.19")
    @pecan.expose('json')
    @api_utils.enforce_content_types(['application/json'])
    @exception.wrap_pecan_controller_exception
    @validation.validate_query_param(pecan.request, schema.query_param_create)
    @validation.validated(schema.legacy_container_create)
    def post(self, run=False, **container_dict):
        # NOTE(hongbin): We convert the representation of 'command' from
        # string to list. For example:
        # '"nginx" "-g" "daemon off;"' -> ["nginx", "-g", "daemon off;"]
        command = container_dict.pop('command', None)
        if command is not None:
            if isinstance(command, six.string_types):
                command = shlex.split(command)
            container_dict['command'] = command

        return self._do_post(run, **container_dict)

    @base.Controller.api_version("1.20")  # noqa
    @pecan.expose('json')
    @api_utils.enforce_content_types(['application/json'])
    @exception.wrap_pecan_controller_exception
    @validation.validate_query_param(pecan.request, schema.query_param_create)
    @validation.validated(schema.container_create)
    def post(self, run=False, **container_dict):
        return self._do_post(run, **container_dict)

    def _do_post(self, run=False, **container_dict):
        """Create or run a new container.

        :param run: if true, starts the container
        :param container_dict: a container within the request body.
        """
        context = pecan.request.context
        compute_api = pecan.request.compute_api
        policy.enforce(context, "container:create",
                       action="container:create")

        if container_dict.get('security_groups'):
            # remove duplicate security_groups from list
            container_dict['security_groups'] = list(set(
                container_dict.get('security_groups')))
            for index, sg in enumerate(container_dict['security_groups']):
                security_group_id = self._check_security_group(context,
                                                               {'name': sg})
                container_dict['security_groups'][index] = security_group_id

        try:
            run = strutils.bool_from_string(run, strict=True)
            container_dict['interactive'] = strutils.bool_from_string(
                container_dict.get('interactive', False), strict=True)
        except ValueError:
            raise exception.InvalidValue(_('Valid run or interactive values '
                                           'are: true, false, True, False'))

        auto_remove = container_dict.pop('auto_remove', None)
        if auto_remove is not None:
            api_utils.version_check('auto_remove', '1.3')
            try:
                container_dict['auto_remove'] = strutils.bool_from_string(
                    auto_remove, strict=True)
            except ValueError:
                raise exception.InvalidValue(_('Auto_remove values are: '
                                               'true, false, True, False'))

        runtime = container_dict.pop('runtime', None)
        if runtime is not None:
            api_utils.version_check('runtime', '1.5')
            policy.enforce(context, "container:create:runtime",
                           action="container:create:runtime")
            container_dict['runtime'] = runtime

        hostname = container_dict.pop('hostname', None)
        if hostname is not None:
            api_utils.version_check('hostname', '1.9')
            container_dict['hostname'] = hostname

        nets = container_dict.get('nets', [])
        requested_networks = utils.build_requested_networks(context, nets)
        pci_req = self._create_pci_requests_for_sriov_ports(context,
                                                            requested_networks)

        mounts = container_dict.pop('mounts', [])
        if mounts:
            api_utils.version_check('mounts', '1.11')

        requested_volumes = self._build_requested_volumes(context, mounts)

        # Valiadtion accepts 'None' so need to convert it to None
        if container_dict.get('image_driver'):
            container_dict['image_driver'] = api_utils.string_or_none(
                container_dict.get('image_driver'))

        container_dict['project_id'] = context.project_id
        container_dict['user_id'] = context.user_id
        name = container_dict.get('name') or \
            self._generate_name_for_container()
        container_dict['name'] = name
        self._set_default_resource_limit(container_dict)
        if container_dict.get('restart_policy'):
            utils.check_for_restart_policy(container_dict)

        container_dict['status'] = consts.CREATING
        extra_spec = {}
        extra_spec['hints'] = container_dict.get('hints', None)
        extra_spec['pci_requests'] = pci_req
        extra_spec['availability_zone'] = container_dict.get(
            'availability_zone')
        new_container = objects.Container(context, **container_dict)
        new_container.create(context)

        kwargs = {}
        kwargs['extra_spec'] = extra_spec
        kwargs['requested_networks'] = requested_networks
        kwargs['requested_volumes'] = requested_volumes
        if pci_req.requests:
            kwargs['pci_requests'] = pci_req
        kwargs['run'] = run
        compute_api.container_create(context, new_container, **kwargs)
        # Set the HTTP Location Header
        pecan.response.location = link.build_url('containers',
                                                 new_container.uuid)
        pecan.response.status = 202
        return view.format_container(context, pecan.request.host_url,
                                     new_container.as_dict())

    def _set_default_resource_limit(self, container_dict):
        # NOTE(kiennt): Default disk size will be set later.
        container_dict['disk'] = container_dict.get('disk')
        container_dict['memory'] = container_dict.get(
            'memory', CONF.default_memory)
        container_dict['memory'] = str(container_dict['memory'])
        container_dict['cpu'] = container_dict.get(
            'cpu', CONF.default_cpu)

    def _create_pci_requests_for_sriov_ports(self, context,
                                             requested_networks):
        pci_requests = objects.ContainerPCIRequests(requests=[])
        if not requested_networks:
            return pci_requests

        neutron_api = neutron.NeutronAPI(context)
        for request_net in requested_networks:
            phynet_name = None
            vnic_type = network_model.VNIC_TYPE_NORMAL

            if request_net.get('port'):
                vnic_type, phynet_name = self._get_port_vnic_info(
                    context, neutron_api, request_net['port'])
            pci_request_id = None
            if vnic_type in network_model.VNIC_TYPES_SRIOV:
                spec = {pci_request.PCI_NET_TAG: phynet_name}
                dev_type = pci_request.DEVICE_TYPE_FOR_VNIC_TYPE.get(vnic_type)
                if dev_type:
                    spec[pci_request.PCI_DEVICE_TYPE_TAG] = dev_type
                request = objects.ContainerPCIRequest(
                    count=1,
                    spec=[spec],
                    request_id=uuidutils.generate_uuid())
                pci_requests.requests.append(request)
                pci_request_id = request.request_id
            request_net['pci_request_id'] = pci_request_id
        return pci_requests

    def _get_port_vnic_info(self, context, neutron, port_id):
        """Retrieve port vnic info

        Invoked with a valid port_id.
        Return vnic type and the attached physical network name.
        """
        phynet_name = None
        port = self._show_port(context, port_id, neutron_client=neutron,
                               fields=['binding:vnic_type', 'network_id'])
        vnic_type = port.get('binding:vnic_type',
                             network_model.VNIC_TYPE_NORMAL)
        if vnic_type in network_model.VNIC_TYPES_SRIOV:
            net_id = port['network_id']
            phynet_name = self._get_phynet_info(context, net_id)
        return vnic_type, phynet_name

    def _show_port(self, context, port_id, neutron_client=None, fields=None):
        """Return the port for the client given the port id.

        :param context: Request context.
        :param port_id: The id of port to be queried.
        :param neutron_client: A neutron client.
        :param fields: The condition fields to query port data.
        :returns: A dict of port data.
                  e.g. {'port_id': 'abcd', 'fixed_ip_address': '1.2.3.4'}
        """
        if not neutron_client:
            neutron_client = neutron.NeutronAPI(context)
        if fields:
            result = neutron_client.show_port(port_id, fields=fields)
        else:
            result = neutron_client.show_port(port_id)
        return result.get('port')

    def _get_phynet_info(self, context, net_id):
        # NOTE(hongbin): Use admin context here because non-admin users are
        # unable to retrieve provider:* attributes.
        admin_context = zun_context.get_admin_context()
        neutron_api = neutron.NeutronAPI(admin_context)
        network = neutron_api.show_network(
            net_id, fields='provider:physical_network')
        net = network.get('network')
        phynet_name = net.get('provider:physical_network')
        return phynet_name

    def _build_requested_volumes(self, context, mounts):
        # NOTE(hongbin): We assume cinder is the only volume provider here.
        # The logic needs to be re-visited if a second volume provider
        # (i.e. Manila) is introduced.
        cinder_api = cinder.CinderAPI(context)
        requested_volumes = []
        for mount in mounts:
            if mount.get('source'):
                volume = cinder_api.search_volume(mount['source'])
                auto_remove = False
            else:
                volume = cinder_api.create_volume(mount['size'])
                auto_remove = True
            cinder_api.ensure_volume_usable(volume)
            volmapp = objects.VolumeMapping(
                context,
                volume_id=volume.id, volume_provider='cinder',
                container_path=mount['destination'],
                user_id=context.user_id,
                project_id=context.project_id,
                auto_remove=auto_remove)
            requested_volumes.append(volmapp)

        return requested_volumes

    def _check_security_group(self, context, security_group):
        neutron_api = neutron.NeutronAPI(context)
        try:
            return neutron_api.find_resourceid_by_name_or_id(
                'security_group', security_group['name'], context.project_id)
        except n_exc.NeutronClientNoUniqueMatch as e:
            msg = _("Multiple security group matches found for name "
                    "%(name)s, use an ID to be more specific.") % {
                'name': security_group['name']}
            raise exception.Conflict(msg)
        except n_exc.NeutronClientException as e:
            if e.status_code == 404:
                msg = _("Security group %(name)s not found.") % {
                    'name': security_group['name']}
                raise exception.InvalidValue(msg)
            else:
                raise

    @base.Controller.api_version("1.1", "1.14")
    @pecan.expose('json')
    @exception.wrap_pecan_controller_exception
    @validation.validated(schema.add_security_group)
    def add_security_group(self, container_ident, **security_group):
        """Add security group to an existing container.

        :param container_ident: UUID or Name of a container.
        :param security_group: security_group to be added to container.
        """

        container = utils.get_container(container_ident)
        check_policy_on_container(
            container.as_dict(), "container:add_security_group")
        utils.validate_container_state(container, 'add_security_group')

        # check if security group already presnt in container
        context = pecan.request.context
        compute_api = pecan.request.compute_api
        security_group_id = self._check_security_group(context, security_group)
        if security_group_id in container.security_groups:
            msg = _("Security group %(id)s has been added to container.") % {
                'id': security_group_id}
            raise exception.InvalidValue(msg)
        compute_api.add_security_group(context, container,
                                       security_group_id)
        pecan.response.status = 202

    @base.Controller.api_version("1.1", "1.14")
    @pecan.expose('json')
    @exception.wrap_pecan_controller_exception
    @validation.validated(schema.remove_security_group)
    def remove_security_group(self, container_ident, **security_group):
        """Remove security group from an existing container.

        :param container_ident: UUID or Name of a container.
        :param security_group: security_group to be removed from container.
        """
        container = utils.get_container(container_ident)
        check_policy_on_container(
            container.as_dict(), "container:remove_security_group")
        utils.validate_container_state(container, 'remove_security_group')

        context = pecan.request.context
        compute_api = pecan.request.compute_api
        security_group_id = self._check_security_group(context, security_group)
        if security_group_id not in container.security_groups:
            msg = _("Security group %(id)s was not added to container.") % {
                'id': security_group_id}
            raise exception.InvalidValue(msg)
        compute_api.remove_security_group(context, container,
                                          security_group_id)
        pecan.response.status = 202

    @pecan.expose('json')
    @exception.wrap_pecan_controller_exception
    @validation.validated(schema.container_update)
    def patch(self, container_ident, **patch):
        """Update an existing container.

        :param container_ident: UUID or name of a container.
        :param patch: a json PATCH document to apply to this container.
        """
        container = utils.get_container(container_ident)
        check_policy_on_container(container.as_dict(), "container:update")
        utils.validate_container_state(container, 'update')
        if 'memory' in patch:
            patch['memory'] = str(patch['memory'])
        if 'cpu' in patch:
            patch['cpu'] = float(patch['cpu'])
        if 'name' in patch:
            patch['name'] = str(patch['name'])
        context = pecan.request.context
        compute_api = pecan.request.compute_api
        container = compute_api.container_update(context, container, patch)
        return view.format_container(context, pecan.request.host_url,
                                     container.as_dict())

    @base.Controller.api_version("1.1", "1.13")
    @pecan.expose('json')
    @exception.wrap_pecan_controller_exception
    @validation.validate_query_param(pecan.request, schema.query_param_rename)
    def rename(self, container_ident, name):
        """Rename an existing container.

        :param container_ident: UUID or Name of a container.
        :param name: a new name for this container.
        """
        container = utils.get_container(container_ident)
        check_policy_on_container(container.as_dict(), "container:rename")
        if container.name == name:
            raise exception.Conflict('The new name for the container is the '
                                     'same as the old name.')
        container.name = name
        context = pecan.request.context
        container.save(context)
        return view.format_container(context, pecan.request.host_url,
                                     container.as_dict())

    @base.Controller.api_version("1.19")
    @pecan.expose('json')
    @exception.wrap_pecan_controller_exception
    @validation.validated(schema.container_update)
    def resize_container(self, container_ident, **kwargs):
        """Resize an existing container.

        :param container_ident: UUID or name of a container.
        :param kwargs: cpu/memory to be updated.
        """
        container = utils.get_container(container_ident)
        check_policy_on_container(container.as_dict(),
                                  "container:resize_container")
        utils.validate_container_state(container, 'resize_container')
        if 'memory' in kwargs:
            kwargs['memory'] = str(kwargs['memory'])
        if 'cpu' in kwargs:
            kwargs['cpu'] = float(kwargs['cpu'])
        context = pecan.request.context
        compute_api = pecan.request.compute_api
        compute_api.resize_container(context, container, kwargs)
        pecan.response.status = 202
        return view.format_container(context, pecan.request.host_url,
                                     container.as_dict())

    @pecan.expose('json')
    @exception.wrap_pecan_controller_exception
    @validation.validate_query_param(pecan.request, schema.query_param_delete)
    def delete(self, container_ident, force=False, **kwargs):
        """Delete a container.

        :param container_ident: UUID or Name of a container.
        :param force: If True, allow to force delete the container.
        """
        context = pecan.request.context
        if utils.is_all_projects(kwargs):
            policy.enforce(context, "container:delete_all_projects",
                           action="container:delete_all_projects")
            context.all_projects = True
        container = utils.get_container(container_ident)
        check_policy_on_container(container.as_dict(), "container:delete")
        try:
            force = strutils.bool_from_string(force, strict=True)
        except ValueError:
            bools = ', '.join(strutils.TRUE_STRINGS + strutils.FALSE_STRINGS)
            raise exception.InvalidValue(_('Valid force values are: %s')
                                         % bools)
        stop = kwargs.pop('stop', False)
        try:
            stop = strutils.bool_from_string(stop, strict=True)
        except ValueError:
            bools = ', '.join(strutils.TRUE_STRINGS + strutils.FALSE_STRINGS)
            raise exception.InvalidValue(_('Valid stop values are: %s')
                                         % bools)
        compute_api = pecan.request.compute_api
        if not force and not stop:
            utils.validate_container_state(container, 'delete')
        elif force and not stop:
            api_utils.version_check('force', '1.7')
            policy.enforce(context, "container:delete_force",
                           action="container:delete_force")
            utils.validate_container_state(container, 'delete_force')
        elif stop:
            api_utils.version_check('stop', '1.12')
            check_policy_on_container(container.as_dict(),
                                      "container:stop")
            utils.validate_container_state(container,
                                           'delete_after_stop')
            if container.status == consts.RUNNING:
                LOG.debug('Calling compute.container_stop with %s '
                          'before delete',
                          container.uuid)
                compute_api.container_stop(context, container, 10)
        container.status = consts.DELETING
        if container.host:
            compute_api.container_delete(context, container, force)
        else:
            container.destroy(context)
        pecan.response.status = 204

    @pecan.expose('json')
    @exception.wrap_pecan_controller_exception
    def rebuild(self, container_ident, **kwargs):
        """Rebuild container.

        :param container_ident: UUID or Name of a container.
        """
        container = utils.get_container(container_ident)
        check_policy_on_container(container.as_dict(), "container:rebuild")
        utils.validate_container_state(container, 'rebuild')
        if kwargs.get('image'):
            container.image = kwargs.get('image')
        if kwargs.get('image_driver'):
            utils.validate_image_driver(kwargs.get('image_driver'))
            container.image_driver = kwargs.get('image_driver')
        LOG.debug('Calling compute.container_rebuild with %s',
                  container.uuid)
        context = pecan.request.context
        compute_api = pecan.request.compute_api
        compute_api.container_rebuild(context, container)
        pecan.response.status = 202

    @pecan.expose('json')
    @exception.wrap_pecan_controller_exception
    def start(self, container_ident, **kwargs):
        """Start container.

        :param container_ident: UUID or Name of a container.
        """
        container = utils.get_container(container_ident)
        check_policy_on_container(container.as_dict(), "container:start")
        utils.validate_container_state(container, 'start')
        LOG.debug('Calling compute.container_start with %s',
                  container.uuid)
        context = pecan.request.context
        compute_api = pecan.request.compute_api
        compute_api.container_start(context, container)
        pecan.response.status = 202

    @pecan.expose('json')
    @exception.wrap_pecan_controller_exception
    @validation.validate_query_param(pecan.request, schema.query_param_stop)
    def stop(self, container_ident, timeout=None, **kwargs):
        """Stop container.

        :param container_ident: UUID or Name of a container.
        """
        container = utils.get_container(container_ident)
        check_policy_on_container(container.as_dict(), "container:stop")
        utils.validate_container_state(container, 'stop')
        LOG.debug('Calling compute.container_stop with %s',
                  container.uuid)
        context = pecan.request.context
        compute_api = pecan.request.compute_api
        compute_api.container_stop(context, container, timeout)
        pecan.response.status = 202

    @pecan.expose('json')
    @exception.wrap_pecan_controller_exception
    @validation.validate_query_param(pecan.request, schema.query_param_reboot)
    def reboot(self, container_ident, timeout=None, **kwargs):
        """Reboot container.

        :param container_ident: UUID or Name of a container.
        """
        container = utils.get_container(container_ident)
        check_policy_on_container(container.as_dict(), "container:reboot")
        utils.validate_container_state(container, 'reboot')
        LOG.debug('Calling compute.container_reboot with %s',
                  container.uuid)
        context = pecan.request.context
        container.status = consts.RESTARTING
        container.save(context)
        compute_api = pecan.request.compute_api
        compute_api.container_reboot(context, container, timeout)
        pecan.response.status = 202

    @pecan.expose('json')
    @exception.wrap_pecan_controller_exception
    def pause(self, container_ident, **kwargs):
        """Pause container.

        :param container_ident: UUID or Name of a container.
        """
        container = utils.get_container(container_ident)
        check_policy_on_container(container.as_dict(), "container:pause")
        utils.validate_container_state(container, 'pause')
        LOG.debug('Calling compute.container_pause with %s',
                  container.uuid)
        context = pecan.request.context
        compute_api = pecan.request.compute_api
        compute_api.container_pause(context, container)
        pecan.response.status = 202

    @pecan.expose('json')
    @exception.wrap_pecan_controller_exception
    def unpause(self, container_ident, **kwargs):
        """Unpause container.

        :param container_ident: UUID or Name of a container.
        """
        container = utils.get_container(container_ident)
        check_policy_on_container(container.as_dict(), "container:unpause")
        utils.validate_container_state(container, 'unpause')
        LOG.debug('Calling compute.container_unpause with %s',
                  container.uuid)
        context = pecan.request.context
        compute_api = pecan.request.compute_api
        compute_api.container_unpause(context, container)
        pecan.response.status = 202

    @pecan.expose('json')
    @exception.wrap_pecan_controller_exception
    @validation.validate_query_param(pecan.request, schema.query_param_logs)
    def logs(self, container_ident, stdout=True, stderr=True,
             timestamps=False, tail='all', since=None):
        """Get logs of the given container.

        :param container_ident: UUID or Name of a container.
        :param stdout: Get standard output if True.
        :param stderr: Get standard error if True.
        :param timestamps: Show timestamps.
        :param tail: Number of lines to show from the end of the logs.
                     (default: get all logs)
        :param since: Show logs since a given datetime or
                     integer epoch (in seconds).
        """
        container = utils.get_container(container_ident)
        check_policy_on_container(container.as_dict(), "container:logs")
        utils.validate_container_state(container, 'logs')
        try:
            stdout = strutils.bool_from_string(stdout, strict=True)
            stderr = strutils.bool_from_string(stderr, strict=True)
            timestamps = strutils.bool_from_string(timestamps, strict=True)
        except ValueError:
            bools = ', '.join(strutils.TRUE_STRINGS + strutils.FALSE_STRINGS)
            raise exception.InvalidValue(_('Valid stdout, stderr and '
                                           'timestamps values are: %s')
                                         % bools)
        LOG.debug('Calling compute.container_logs with %s', container.uuid)
        context = pecan.request.context
        compute_api = pecan.request.compute_api
        return compute_api.container_logs(context, container, stdout, stderr,
                                          timestamps, tail, since)

    @pecan.expose('json')
    @exception.wrap_pecan_controller_exception
    @validation.validate_query_param(pecan.request,
                                     schema.query_param_execute_command)
    def execute(self, container_ident, run=True, interactive=False, **kwargs):
        """Execute command in a running container.

        :param container_ident: UUID or Name of a container.
        :param run: If True, execute run.
        :param interactive: Keep STDIN open and allocate a
                            pseudo-TTY for interactive.
        """
        container = utils.get_container(container_ident)
        check_policy_on_container(container.as_dict(), "container:execute")
        utils.validate_container_state(container, 'execute')
        try:
            run = strutils.bool_from_string(run, strict=True)
            interactive = strutils.bool_from_string(interactive, strict=True)
        except ValueError:
            bools = ', '.join(strutils.TRUE_STRINGS + strutils.FALSE_STRINGS)
            raise exception.InvalidValue(_('Valid run or interactive '
                                           'values are: %s') % bools)
        LOG.debug('Calling compute.container_exec with %(uuid)s command '
                  '%(command)s',
                  {'uuid': container.uuid, 'command': kwargs['command']})
        context = pecan.request.context
        compute_api = pecan.request.compute_api
        return compute_api.container_exec(context, container,
                                          kwargs['command'],
                                          run, interactive)

    @pecan.expose('json')
    @exception.wrap_pecan_controller_exception
    @validation.validate_query_param(pecan.request,
                                     schema.query_param_execute_resize)
    def execute_resize(self, container_ident, exec_id, **kwargs):
        """Resize the tty session used by the exec

        :param container_ident: UUID or Name of a container.
        :param exec_id: ID of a exec.
        """
        container = utils.get_container(container_ident)
        check_policy_on_container(container.as_dict(),
                                  "container:execute_resize")
        utils.validate_container_state(container, 'execute_resize')
        LOG.debug('Calling tty resize used by exec %s', exec_id)
        context = pecan.request.context
        compute_api = pecan.request.compute_api
        return compute_api.container_exec_resize(
            context, container, exec_id, kwargs.get('h', None),
            kwargs.get('w', None))

    @pecan.expose('json')
    @exception.wrap_pecan_controller_exception
    @validation.validated(schema.query_param_signal)
    def kill(self, container_ident, **kwargs):
        """Kill a running container.

        :param container_ident: UUID or Name of a container.
        """
        container = utils.get_container(container_ident)
        check_policy_on_container(container.as_dict(), "container:kill")
        utils.validate_container_state(container, 'kill')
        LOG.debug('Calling compute.container_kill with %(uuid)s '
                  'signal %(signal)s',
                  {'uuid': container.uuid,
                   'signal': kwargs.get('signal')})
        context = pecan.request.context
        compute_api = pecan.request.compute_api
        compute_api.container_kill(context, container, kwargs.get('signal'))
        pecan.response.status = 202

    @pecan.expose('json')
    @exception.wrap_pecan_controller_exception
    def attach(self, container_ident):
        """Attach to a running container.

        :param container_ident: UUID or Name of a container.
        """
        container = utils.get_container(container_ident)
        check_policy_on_container(container.as_dict(), "container:attach")
        utils.validate_container_state(container, 'attach')
        LOG.debug('Checking the status for attach with %s', container.uuid)
        if container.interactive:
            context = pecan.request.context
            compute_api = pecan.request.compute_api
            url = compute_api.container_attach(context, container)
            return url
        msg = _("Container doesn't support to be attached, "
                "please check the interactive set properly")
        raise exception.NoInteractiveFlag(msg=msg)

    @pecan.expose('json')
    @exception.wrap_pecan_controller_exception
    @validation.validate_query_param(pecan.request, schema.query_param_resize)
    def resize(self, container_ident, **kwargs):
        """Resize container.

        :param container_ident: UUID or Name of a container.
        """
        container = utils.get_container(container_ident)
        check_policy_on_container(container.as_dict(), "container:resize")
        utils.validate_container_state(container, 'resize')
        LOG.debug('Calling tty resize with %s ', container.uuid)
        context = pecan.request.context
        compute_api = pecan.request.compute_api
        compute_api.container_resize(context, container, kwargs.get('h', None),
                                     kwargs.get('w', None))

    @pecan.expose('json')
    @exception.wrap_pecan_controller_exception
    @validation.validate_query_param(pecan.request, schema.query_param_top)
    def top(self, container_ident, ps_args=None):
        """Display the running processes inside the container.

        :param container_ident: UUID or Name of a container.
        :param ps_args: The args of the ps command.
        """
        container = utils.get_container(container_ident)
        check_policy_on_container(container.as_dict(), "container:top")
        utils.validate_container_state(container, 'top')
        LOG.debug('Calling compute.container_top with %s', container.uuid)
        context = pecan.request.context
        compute_api = pecan.request.compute_api
        return compute_api.container_top(context, container, ps_args)

    @pecan.expose('json')
    @exception.wrap_pecan_controller_exception
    def get_archive(self, container_ident, **kwargs):
        """Retrieve a file/folder from a container

        Retrieve a file or folder from a container in the
        form of a tar archive.
        :param container_ident: UUID or Name of a container.
        """
        container = utils.get_container(container_ident)
        check_policy_on_container(container.as_dict(), "container:get_archive")
        utils.validate_container_state(container, 'get_archive')
        LOG.debug('Calling compute.container_get_archive with %(uuid)s '
                  'path %(path)s',
                  {'uuid': container.uuid, 'path': kwargs['path']})
        context = pecan.request.context
        compute_api = pecan.request.compute_api
        data, stat = compute_api.container_get_archive(
            context, container, kwargs['path'])
        return {"data": data, "stat": stat}

    @pecan.expose('json')
    @exception.wrap_pecan_controller_exception
    def put_archive(self, container_ident, **kwargs):
        """Insert a file/folder to container.

        Insert a file or folder to an existing container using
        a tar archive as source.
        :param container_ident: UUID or Name of a container.
        """
        container = utils.get_container(container_ident)
        check_policy_on_container(container.as_dict(), "container:put_archive")
        utils.validate_container_state(container, 'put_archive')
        LOG.debug('Calling compute.container_put_archive with %(uuid)s '
                  'path %(path)s',
                  {'uuid': container.uuid, 'path': kwargs['path']})
        context = pecan.request.context
        compute_api = pecan.request.compute_api
        compute_api.container_put_archive(context, container,
                                          kwargs['path'], kwargs['data'])

    @pecan.expose('json')
    @exception.wrap_pecan_controller_exception
    def stats(self, container_ident):
        """Display stats snapshot of the container.

        :param container_ident: UUID or Name of a container.
        """
        container = utils.get_container(container_ident)
        check_policy_on_container(container.as_dict(), "container:stats")
        utils.validate_container_state(container, 'stats')
        LOG.debug('Calling compute.container_stats with %s', container.uuid)
        context = pecan.request.context
        compute_api = pecan.request.compute_api
        return compute_api.container_stats(context, container)

    @pecan.expose('json')
    @exception.wrap_pecan_controller_exception
    @validation.validate_query_param(pecan.request, schema.query_param_commit)
    def commit(self, container_ident, **kwargs):
        """Create a new image from a container's changes.

        :param container_ident: UUID or Name of a container.
        """
        container = utils.get_container(container_ident)
        check_policy_on_container(container.as_dict(), "container:commit")
        utils.validate_container_state(container, 'commit')
        LOG.debug('Calling compute.container_commit %s ', container.uuid)
        context = pecan.request.context
        compute_api = pecan.request.compute_api
        pecan.response.status = 202
        return compute_api.container_commit(context, container,
                                            kwargs.get('repository', None),
                                            kwargs.get('tag', None))

    @base.Controller.api_version("1.6")
    @pecan.expose('json')
    @exception.wrap_pecan_controller_exception
    @validation.validate_query_param(pecan.request, schema.network_detach)
    def network_detach(self, container_ident, **kwargs):
        """Detach a network from the container.

        :param container_ident: UUID or Name of a container.
        """
        container = utils.get_container(container_ident)
        check_policy_on_container(container.as_dict(),
                                  "container:network_detach")
        context = pecan.request.context
        compute_api = pecan.request.compute_api
        neutron_api = neutron.NeutronAPI(context)
        if kwargs.get('port'):
            port = neutron_api.get_neutron_port(kwargs['port'])
            net_id = port['network_id']
        else:
            network = neutron_api.get_neutron_network(kwargs.get('network'))
            net_id = network['id']
        compute_api.network_detach(context, container, net_id)
        pecan.response.status = 202

    @base.Controller.api_version("1.8")
    @pecan.expose('json')
    @exception.wrap_pecan_controller_exception
    @validation.validate_query_param(pecan.request, schema.network_attach)
    def network_attach(self, container_ident, **kwargs):
        """Attach a network to the container.

        :param container_ident: UUID or Name of a container.
        """
        container = utils.get_container(container_ident)
        check_policy_on_container(container.as_dict(),
                                  "container:network_attach")
        context = pecan.request.context
        compute_api = pecan.request.compute_api
        requested_networks = utils.build_requested_networks(context, [kwargs])
        compute_api.network_attach(context, container, requested_networks[0])

    @base.Controller.api_version("1.13", "1.17")
    @pecan.expose('json')
    @exception.wrap_pecan_controller_exception
    def network_list(self, container_ident):
        """Retrieve a list of networks of the container.

        :param container_ident: UUID or Name of a container.
        """
        container = utils.get_container(container_ident)
        container_networks = self._get_container_networks_legacy(container)
        return {'networks': container_networks}

    def _get_container_networks_legacy(self, container):
        container_networks = []
        for net_id, net_infos in container.addresses.items():
            for net_info in net_infos:
                container_networks.append({
                    'net_id': net_id,
                    'subnet_id': net_info.get("subnet_id"),
                    'port_id': net_info.get("port"),
                    'version': net_info.get("version"),
                    'ip_address': net_info.get("addr")
                })
        return container_networks

    @base.Controller.api_version("1.18")  # noqa
    @pecan.expose('json')
    @exception.wrap_pecan_controller_exception
    def network_list(self, container_ident):
        """Retrieve a list of networks of the container.

        :param container_ident: UUID or Name of a container.
        """
        container = utils.get_container(container_ident)
        container_networks = self._get_container_networks(container)
        return {'networks': container_networks}

    def _get_container_networks(self, container):
        container_networks = []
        for net_id, net_infos in container.addresses.items():
            addresses = {}
            for net_info in net_infos:
                port_id = net_info["port"]
                addresses.setdefault(port_id, [])
                addresses[port_id].append({
                    'subnet_id': net_info.get("subnet_id"),
                    'version': net_info.get("version"),
                    'ip_address': net_info.get("addr")
                })
            for port_id, fixed_ips in addresses.items():
                container_networks.append({
                    'net_id': net_id,
                    'port_id': port_id,
                    'fixed_ips': fixed_ips,
                })
        return container_networks
