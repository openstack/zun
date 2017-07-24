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

from oslo_log import log as logging
from oslo_utils import strutils
import pecan
import six

from zun.api.controllers import base
from zun.api.controllers import link
from zun.api.controllers.v1 import collection
from zun.api.controllers.v1.schemas import containers as schema
from zun.api.controllers.v1.views import containers_view as view
from zun.api.controllers import versions
from zun.api import utils as api_utils
from zun.common import consts
from zun.common import exception
from zun.common.i18n import _
from zun.common import name_generator
from zun.common import policy
from zun.common import utils
from zun.common import validation
from zun import objects

LOG = logging.getLogger(__name__)


def _get_container(container_id):
    container = api_utils.get_resource('Container', container_id)
    if not container:
        pecan.abort(404, ('Not found; the container you requested '
                          'does not exist.'))

    return container


def check_policy_on_container(container, action):
    context = pecan.request.context
    policy.enforce(context, action, container, action=action)


def is_all_tenants(search_opts):
    all_tenants = search_opts.get('all_tenants')
    if all_tenants:
        try:
            all_tenants = strutils.bool_from_string(all_tenants, True)
        except ValueError as err:
            raise exception.InvalidInput(six.text_type(err))
    else:
        all_tenants = False
    return all_tenants


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
        collection = ContainerCollection()
        collection.containers = \
            [view.format_container(url, p) for p in rpc_containers]
        collection.next = collection.get_next(limit, url=url, **kwargs)
        return collection


class ContainersController(base.Controller):
    """Controller for Containers."""

    _custom_actions = {
        'start': ['POST'],
        'stop': ['POST'],
        'reboot': ['POST'],
        'pause': ['POST'],
        'unpause': ['POST'],
        'logs': ['GET'],
        'execute': ['POST'],
        'execute_resize': ['POST'],
        'kill': ['POST'],
        'rename': ['POST'],
        'attach': ['GET'],
        'resize': ['POST'],
        'top': ['GET'],
        'get_archive': ['GET'],
        'put_archive': ['POST'],
        'stats': ['GET'],
        'commit': ['POST'],
        'add_security_group': ['POST']
    }

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
        if is_all_tenants(kwargs):
            policy.enforce(context, "container:get_all_all_tenants",
                           action="container:get_all_all_tenants")
            context.all_tenants = True
        compute_api = pecan.request.compute_api
        limit = api_utils.validate_limit(kwargs.get('limit'))
        sort_dir = api_utils.validate_sort_dir(kwargs.get('sort_dir', 'asc'))
        sort_key = kwargs.get('sort_key', 'id')
        resource_url = kwargs.get('resource_url')
        expand = kwargs.get('expand')

        filters = None
        marker_obj = None
        marker = kwargs.get('marker')
        if marker:
            marker_obj = objects.Container.get_by_uuid(context,
                                                       marker)
        containers = objects.Container.list(context,
                                            limit,
                                            marker_obj,
                                            sort_key,
                                            sort_dir,
                                            filters=filters)

        for i, c in enumerate(containers):
            try:
                containers[i] = compute_api.container_show(context, c)
            except Exception as e:
                LOG.exception(("Error while list container %(uuid)s: "
                               "%(e)s."),
                              {'uuid': c.uuid, 'e': e})
                containers[i].status = consts.UNKNOWN

        return ContainerCollection.convert_with_links(containers, limit,
                                                      url=resource_url,
                                                      expand=expand,
                                                      sort_key=sort_key,
                                                      sort_dir=sort_dir)

    @pecan.expose('json')
    @exception.wrap_pecan_controller_exception
    def get_one(self, container_id, **kwargs):
        """Retrieve information about the given container.

        :param container_ident: UUID or name of a container.
        """
        context = pecan.request.context
        if is_all_tenants(kwargs):
            policy.enforce(context, "container:get_one_all_tenants",
                           action="container:get_one_all_tenants")
            context.all_tenants = True
        container = _get_container(container_id)
        check_policy_on_container(container.as_dict(), "container:get_one")
        compute_api = pecan.request.compute_api
        container = compute_api.container_show(context, container)
        return view.format_container(pecan.request.host_url, container)

    def _generate_name_for_container(self):
        """Generate a random name like: zeta-22-container."""
        name_gen = name_generator.NameGenerator()
        name = name_gen.generate()
        return name + '-container'

    def _check_for_restart_policy(self, container_dict):
        """Check for restart policy input"""
        restart_policy = container_dict.get('restart_policy')
        if not restart_policy:
            return

        name = restart_policy.get('Name')
        num = restart_policy.setdefault('MaximumRetryCount', '0')
        count = int(num)
        if name in ['unless-stopped', 'always']:
            if count != 0:
                msg = _("maximum retry count not valid with restart "
                        "policy of %s") % name
                raise exception.InvalidValue(msg)
        elif name in ['no']:
            container_dict.get('restart_policy')['MaximumRetryCount'] = '0'

    @pecan.expose('json')
    @api_utils.enforce_content_types(['application/json'])
    @exception.wrap_pecan_controller_exception
    @validation.validate_query_param(pecan.request, schema.query_param_create)
    @validation.validated(schema.container_create)
    def post(self, run=False, **container_dict):
        """Create a new container.

        :param run: if true, starts the container
        :param container_dict: a container within the request body.
        """
        context = pecan.request.context
        compute_api = pecan.request.compute_api
        policy.enforce(context, "container:create",
                       action="container:create")

        # remove duplicate security_groups from list
        if container_dict.get('security_groups'):
            container_dict['security_groups'] = list(
                set(container_dict.get('security_groups')))
        try:
            run = strutils.bool_from_string(run, strict=True)
            container_dict['interactive'] = strutils.bool_from_string(
                container_dict.get('interactive', False), strict=True)
        except ValueError:
            msg = _('Valid run or interactive value is ''true'', '
                    '"false", True, False, "True" and "False"')
            raise exception.InvalidValue(msg)

        requested_networks = container_dict.get('nets', [])

        # Valiadtion accepts 'None' so need to convert it to None
        if container_dict.get('image_driver'):
            container_dict['image_driver'] = api_utils.string_or_none(
                container_dict.get('image_driver'))

        # NOTE(mkrai): Intent here is to check the existence of image
        # before proceeding to create container. If image is not found,
        # container create will fail with 400 status.
        images = compute_api.image_search(context, container_dict['image'],
                                          container_dict.get('image_driver'),
                                          True)
        if not images:
            raise exception.ImageNotFound(image=container_dict['image'])
        container_dict['project_id'] = context.project_id
        container_dict['user_id'] = context.user_id
        name = container_dict.get('name') or \
            self._generate_name_for_container()
        container_dict['name'] = name
        if container_dict.get('memory'):
            container_dict['memory'] = \
                str(container_dict['memory']) + 'M'
        if container_dict.get('restart_policy'):
            self._check_for_restart_policy(container_dict)

        auto_remove = container_dict.pop('auto_remove', None)
        if auto_remove is not None:
            req_version = pecan.request.version
            min_version = versions.Version('', '', '', '1.3')
            if req_version >= min_version:
                try:
                    container_dict['auto_remove'] = strutils.bool_from_string(
                        auto_remove, strict=True)
                except ValueError:
                    msg = _('Auto_remove value are true or false')
                    raise exception.InvalidValue(msg)
            else:
                msg = _('Invalid param auto_remove because current request '
                        'version is %(req_version)s. Auto_remove is only '
                        'supported from version %(min_version)s') % \
                    {'req_version': req_version,
                     'min_version': min_version}
                raise exception.InvalidParam(msg)

        container_dict['status'] = consts.CREATING
        extra_spec = container_dict.get('hints', None)
        new_container = objects.Container(context, **container_dict)
        new_container.create(context)

        if run:
            compute_api.container_run(context, new_container, extra_spec,
                                      requested_networks)
        else:
            compute_api.container_create(context, new_container, extra_spec,
                                         requested_networks)
        # Set the HTTP Location Header
        pecan.response.location = link.build_url('containers',
                                                 new_container.uuid)
        pecan.response.status = 202
        return view.format_container(pecan.request.host_url, new_container)

    @pecan.expose('json')
    @exception.wrap_pecan_controller_exception
    @validation.validated(schema.add_security_group)
    def add_security_group(self, container_id, **security_group):
        """Add security group to an existing container.

        :param security_group: security_group to be added to container.
        """

        container = _get_container(container_id)
        check_policy_on_container(
            container.as_dict(), "container:add_security_group")
        utils.validate_container_state(container, 'add_security_group')

        # check if security group already presnt in container
        if security_group['name'] in container.security_groups:
            msg = _("security_group %s already present in container") % \
                security_group['name']
            raise exception.InvalidValue(msg)

        context = pecan.request.context
        compute_api = pecan.request.compute_api
        compute_api.add_security_group(context, container,
                                       security_group['name'])
        pecan.response.status = 202

    @pecan.expose('json')
    @exception.wrap_pecan_controller_exception
    @validation.validated(schema.container_update)
    def patch(self, container_id, **patch):
        """Update an existing container.

        :param patch: a json PATCH document to apply to this container.
        """
        container = _get_container(container_id)
        check_policy_on_container(container.as_dict(), "container:update")
        utils.validate_container_state(container, 'update')
        if 'memory' in patch:
            patch['memory'] = str(patch['memory']) + 'M'
        if 'cpu' in patch:
            patch['cpu'] = float(patch['cpu'])
        context = pecan.request.context
        compute_api = pecan.request.compute_api
        container = compute_api.container_update(context, container, patch)
        return view.format_container(pecan.request.host_url, container)

    @pecan.expose('json')
    @exception.wrap_pecan_controller_exception
    @validation.validate_query_param(pecan.request, schema.query_param_rename)
    def rename(self, container_id, name):
        """rename an existing container.

        :param patch: a json PATCH document to apply to this container.
        """
        container = _get_container(container_id)
        check_policy_on_container(container.as_dict(), "container:rename")
        if container.name == name:
            raise exception.Conflict('The new name for the container is the '
                                     'same as the old name.')
        container.name = name
        context = pecan.request.context
        container.save(context)
        return view.format_container(pecan.request.host_url, container)

    @pecan.expose('json')
    @exception.wrap_pecan_controller_exception
    @validation.validate_query_param(pecan.request, schema.query_param_delete)
    def delete(self, container_id, force=False, **kwargs):
        """Delete a container.

        :param container_ident: UUID or Name of a container.
        """
        context = pecan.request.context
        if is_all_tenants(kwargs):
            policy.enforce(context, "container:delete_all_tenants",
                           action="container:delete_all_tenants")
            context.all_tenants = True
        container = _get_container(container_id)
        check_policy_on_container(container.as_dict(), "container:delete")
        try:
            force = strutils.bool_from_string(force, strict=True)
        except ValueError:
            msg = _('Valid force values are true, false, 0, 1, yes and no')
            raise exception.InvalidValue(msg)
        if not force:
            utils.validate_container_state(container, 'delete')
        else:
            utils.validate_container_state(container, 'delete_force')
        compute_api = pecan.request.compute_api
        compute_api.container_delete(context, container, force)
        pecan.response.status = 204

    @pecan.expose('json')
    @exception.wrap_pecan_controller_exception
    def start(self, container_id, **kwargs):
        container = _get_container(container_id)
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
    def stop(self, container_id, timeout=None, **kwargs):
        container = _get_container(container_id)
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
    def reboot(self, container_id, timeout=None, **kwargs):
        container = _get_container(container_id)
        check_policy_on_container(container.as_dict(), "container:reboot")
        utils.validate_container_state(container, 'reboot')
        LOG.debug('Calling compute.container_reboot with %s',
                  container.uuid)
        context = pecan.request.context
        compute_api = pecan.request.compute_api
        compute_api.container_reboot(context, container, timeout)
        pecan.response.status = 202

    @pecan.expose('json')
    @exception.wrap_pecan_controller_exception
    def pause(self, container_id, **kwargs):
        container = _get_container(container_id)
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
    def unpause(self, container_id, **kwargs):
        container = _get_container(container_id)
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
    def logs(self, container_id, stdout=True, stderr=True,
             timestamps=False, tail='all', since=None):
        container = _get_container(container_id)
        check_policy_on_container(container.as_dict(), "container:logs")
        utils.validate_container_state(container, 'logs')
        try:
            stdout = strutils.bool_from_string(stdout, strict=True)
            stderr = strutils.bool_from_string(stderr, strict=True)
            timestamps = strutils.bool_from_string(timestamps, strict=True)
        except ValueError:
            msg = _('Valid stdout, stderr and timestamps values are ''true'', '
                    '"false", True, False, 0 and 1, yes and no')
            raise exception.InvalidValue(msg)
        LOG.debug('Calling compute.container_logs with %s', container.uuid)
        context = pecan.request.context
        compute_api = pecan.request.compute_api
        return compute_api.container_logs(context, container, stdout, stderr,
                                          timestamps, tail, since)

    @pecan.expose('json')
    @exception.wrap_pecan_controller_exception
    @validation.validate_query_param(pecan.request,
                                     schema.query_param_execute_command)
    def execute(self, container_id, run=True, interactive=False, **kwargs):
        container = _get_container(container_id)
        check_policy_on_container(container.as_dict(), "container:execute")
        utils.validate_container_state(container, 'execute')
        try:
            run = strutils.bool_from_string(run, strict=True)
            interactive = strutils.bool_from_string(interactive, strict=True)
        except ValueError:
            msg = _('Valid run values are true, false, 0, 1, yes and no')
            raise exception.InvalidValue(msg)
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
    def execute_resize(self, container_id, exec_id, **kwargs):
        container = _get_container(container_id)
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
    def kill(self, container_id, **kwargs):
        container = _get_container(container_id)
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
    def attach(self, container_id):
        container = _get_container(container_id)
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
    def resize(self, container_id, **kwargs):
        container = _get_container(container_id)
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
    def top(self, container_id, ps_args=None):
        container = _get_container(container_id)
        check_policy_on_container(container.as_dict(), "container:top")
        utils.validate_container_state(container, 'top')
        LOG.debug('Calling compute.container_top with %s', container.uuid)
        context = pecan.request.context
        compute_api = pecan.request.compute_api
        return compute_api.container_top(context, container, ps_args)

    @pecan.expose('json')
    @exception.wrap_pecan_controller_exception
    def get_archive(self, container_id, **kwargs):
        container = _get_container(container_id)
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
    def put_archive(self, container_id, **kwargs):
        container = _get_container(container_id)
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
    def stats(self, container_id):
        container = _get_container(container_id)
        check_policy_on_container(container.as_dict(), "container:stats")
        utils.validate_container_state(container, 'stats')
        LOG.debug('Calling compute.container_stats with %s', container.uuid)
        context = pecan.request.context
        compute_api = pecan.request.compute_api
        return compute_api.container_stats(context, container)

    @pecan.expose('json')
    @exception.wrap_pecan_controller_exception
    @validation.validate_query_param(pecan.request, schema.query_param_commit)
    def commit(self, container_id, **kwargs):
        container = _get_container(container_id)
        check_policy_on_container(container.as_dict(), "container:commit")
        utils.validate_container_state(container, 'commit')
        LOG.debug('Calling compute.container_commit %s ', container.uuid)
        context = pecan.request.context
        compute_api = pecan.request.compute_api
        pecan.response.status = 202
        return compute_api.container_commit(context, container,
                                            kwargs.get('repository', None),
                                            kwargs.get('tag', None))
