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
from pecan import rest
import six

from zun.api.controllers import link
from zun.api.controllers.v1 import collection
from zun.api.controllers.v1.schemas import containers as schema
from zun.api.controllers.v1.views import containers_view as view
from zun.api import utils as api_utils
from zun.common import exception
from zun.common.i18n import _
from zun.common.i18n import _LE
from zun.common import name_generator
from zun.common import policy
from zun.common import utils
from zun.common import validation
import zun.conf
from zun import objects
from zun.objects import fields


CONF = zun.conf.CONF
LOG = logging.getLogger(__name__)


def _get_container(container_id):
    container = api_utils.get_resource('Container', container_id)
    if not container:
        pecan.abort(404, _LE('Not found; the container you requested '
                             'does not exist.'))

    return container


def check_policy_on_container(container, action):
    context = pecan.request.context
    policy.enforce(context, action, container, action=action)


class ContainerCollection(collection.Collection):
    """API representation of a collection of containers."""

    fields = {
        'containers'
    }

    """A list containing containers objects"""

    def __init__(self, **kwargs):
        self._type = 'containers'

    @staticmethod
    def convert_with_links(rpc_containers, limit, url=None,
                           expand=False, **kwargs):
        collection = ContainerCollection()
        collection.containers = \
            [view.format_container(url, p) for p in rpc_containers]
        collection.next = collection.get_next(limit, url=url, **kwargs)
        return collection


class ContainersController(rest.RestController):
    """Controller for Containers."""

    _custom_actions = {
        'start': ['POST'],
        'stop': ['POST'],
        'reboot': ['POST'],
        'pause': ['POST'],
        'unpause': ['POST'],
        'logs': ['GET'],
        'execute': ['POST'],
        'kill': ['POST'],
        'rename': ['POST'],
        'attach': ['GET'],
        'resize': ['POST'],
        'top': ['GET'],
        'get_archive': ['GET'],
        'put_archive': ['POST'],
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
        all_tenants = kwargs.get('all_tenants')
        if all_tenants:
            try:
                all_tenants = strutils.bool_from_string(all_tenants, True)
            except ValueError as err:
                raise exception.InvalidInput(six.text_type(err))
        else:
            # If no value, it's considered to disable all_tenants
            all_tenants = False
        if all_tenants:
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
                LOG.exception(_LE("Error while list container %(uuid)s: "
                                  "%(e)s."),
                              {'uuid': c.uuid, 'e': e})
                containers[i].status = fields.ContainerStatus.UNKNOWN

        return ContainerCollection.convert_with_links(containers, limit,
                                                      url=resource_url,
                                                      expand=expand,
                                                      sort_key=sort_key,
                                                      sort_dir=sort_dir)

    @pecan.expose('json')
    @exception.wrap_pecan_controller_exception
    def get_one(self, container_id):
        """Retrieve information about the given container.

        :param container_ident: UUID or name of a container.
        """
        container = _get_container(container_id)
        check_policy_on_container(container.as_dict(), "container:get")
        context = pecan.request.context
        compute_api = pecan.request.compute_api
        container = compute_api.container_show(context, container)
        return view.format_container(pecan.request.host_url, container)

    def _generate_name_for_container(self):
        '''Generate a random name like: zeta-22-container.'''
        name_gen = name_generator.NameGenerator()
        name = name_gen.generate()
        return name + '-container'

    def _check_for_restart_policy(self, container_dict):
        '''Check for restart policy input'''
        name = container_dict.get('restart_policy').get('Name')
        num = container_dict.get('restart_policy').get('MaximumRetryCount',
                                                       '0')
        count = int(num)
        if name in ['unless-stopped', 'always']:
            if count != 0:
                raise exception.InvalidValue(_LE("maximum retry "
                                                 "count not valid "
                                                 "with restart policy "
                                                 "of %s") % name)
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
        :param container: a container within the request body.
        """
        context = pecan.request.context
        compute_api = pecan.request.compute_api
        policy.enforce(context, "container:create",
                       action="container:create")

        try:
            run = strutils.bool_from_string(run, strict=True)
        except ValueError:
            msg = _('Valid run values are true, false, 0, 1, yes and no')
            raise exception.InvalidValue(msg)
        try:
            container_dict['tty'] = strutils.bool_from_string(
                container_dict.get('tty', False), strict=True)
            container_dict['stdin_open'] = strutils.bool_from_string(
                container_dict.get('stdin_open', False), strict=True)
        except ValueError:
            msg = _('Valid tty and stdin_open values are ''true'', '
                    '"false", True, False, "True" and "False"')
            raise exception.InvalidValue(msg)

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
        container_dict['status'] = fields.ContainerStatus.CREATING
        new_container = objects.Container(context, **container_dict)
        new_container.create(context)

        if run:
            compute_api.container_run(context, new_container)
        else:
            compute_api.container_create(context, new_container)
        # Set the HTTP Location Header
        pecan.response.location = link.build_url('containers',
                                                 new_container.uuid)
        pecan.response.status = 202
        return view.format_container(pecan.request.host_url, new_container)

    @pecan.expose('json')
    @exception.wrap_pecan_controller_exception
    @validation.validated(schema.container_update)
    def patch(self, container_id, **patch):
        """Update an existing container.

        :param patch: a json PATCH document to apply to this container.
        """
        context = pecan.request.context
        container = _get_container(container_id)
        check_policy_on_container(container.as_dict(), "container:update")
        utils.validate_container_state(container, 'update')
        if 'memory' in patch:
            patch['memory'] = str(patch['memory']) + 'M'
        if 'cpu' in patch:
            patch['cpu'] = float(patch['cpu'])
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
        context = pecan.request.context
        container = _get_container(container_id)
        check_policy_on_container(container.as_dict(), "container:rename")

        if container.name == name:
            raise exception.Conflict('The new name for the container is the '
                                     'same as the old name.')
        container.name = name
        container.save(context)
        return view.format_container(pecan.request.host_url, container)

    @pecan.expose('json')
    @exception.wrap_pecan_controller_exception
    @validation.validate_query_param(pecan.request, schema.query_param_delete)
    def delete(self, container_id, force=False):
        """Delete a container.

        :param container_ident: UUID or Name of a container.
        """
        container = _get_container(container_id)
        check_policy_on_container(container.as_dict(), "container:delete")
        try:
            force = strutils.bool_from_string(force, strict=True)
        except ValueError:
            msg = _('Valid force values are true, false, 0, 1, yes and no')
            raise exception.InvalidValue(msg)
        if not force:
            utils.validate_container_state(container, 'delete')
        context = pecan.request.context
        compute_api = pecan.request.compute_api
        compute_api.container_delete(context, container, force)
        container.destroy(context)
        pecan.response.status = 204

    @pecan.expose('json')
    @exception.wrap_pecan_controller_exception
    def start(self, container_id, **kw):
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
    def stop(self, container_id, timeout=None, **kw):
        container = _get_container(container_id)
        check_policy_on_container(container.as_dict(), "container:stop")
        utils.validate_container_state(container, 'stop')
        LOG.debug('Calling compute.container_stop with %s' %
                  container.uuid)
        context = pecan.request.context
        compute_api = pecan.request.compute_api
        compute_api.container_stop(context, container, timeout)
        pecan.response.status = 202

    @pecan.expose('json')
    @exception.wrap_pecan_controller_exception
    @validation.validate_query_param(pecan.request, schema.query_param_reboot)
    def reboot(self, container_id, timeout=None, **kw):
        container = _get_container(container_id)
        check_policy_on_container(container.as_dict(), "container:reboot")
        utils.validate_container_state(container, 'reboot')
        LOG.debug('Calling compute.container_reboot with %s' %
                  container.uuid)
        context = pecan.request.context
        compute_api = pecan.request.compute_api
        compute_api.container_reboot(context, container, timeout)
        pecan.response.status = 202

    @pecan.expose('json')
    @exception.wrap_pecan_controller_exception
    def pause(self, container_id, **kw):
        container = _get_container(container_id)
        check_policy_on_container(container.as_dict(), "container:pause")
        utils.validate_container_state(container, 'pause')
        LOG.debug('Calling compute.container_pause with %s' %
                  container.uuid)
        context = pecan.request.context
        compute_api = pecan.request.compute_api
        compute_api.container_pause(context, container)
        pecan.response.status = 202

    @pecan.expose('json')
    @exception.wrap_pecan_controller_exception
    def unpause(self, container_id, **kw):
        container = _get_container(container_id)
        check_policy_on_container(container.as_dict(), "container:unpause")
        utils.validate_container_state(container, 'unpause')
        LOG.debug('Calling compute.container_unpause with %s' %
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
        try:
            stdout = strutils.bool_from_string(stdout, strict=True)
            stderr = strutils.bool_from_string(stderr, strict=True)
            timestamps = strutils.bool_from_string(timestamps, strict=True)
        except ValueError:
            msg = _('Valid stdout, stderr and timestamps values are ''true'', '
                    '"false", True, False, 0 and 1, yes and no')
            raise exception.InvalidValue(msg)
        LOG.debug('Calling compute.container_logs with %s' %
                  container.uuid)
        context = pecan.request.context
        compute_api = pecan.request.compute_api
        return compute_api.container_logs(context, container, stdout, stderr,
                                          timestamps, tail, since)

    @pecan.expose('json')
    @exception.wrap_pecan_controller_exception
    def execute(self, container_id, **kw):
        container = _get_container(container_id)
        check_policy_on_container(container.as_dict(), "container:execute")
        utils.validate_container_state(container, 'execute')
        LOG.debug('Calling compute.container_exec with %s command %s'
                  % (container.uuid, kw['command']))
        context = pecan.request.context
        compute_api = pecan.request.compute_api
        return compute_api.container_exec(context, container, kw['command'])

    @pecan.expose('json')
    @exception.wrap_pecan_controller_exception
    def kill(self, container_id, **kw):
        container = _get_container(container_id)
        check_policy_on_container(container.as_dict(), "container:kill")
        utils.validate_container_state(container, 'kill')
        LOG.debug('Calling compute.container_kill with %s signal %s'
                  % (container.uuid, kw.get('signal', kw.get('signal'))))
        context = pecan.request.context
        compute_api = pecan.request.compute_api
        compute_api.container_kill(context, container, kw.get('signal'))
        pecan.response.status = 202

    @pecan.expose('json')
    @exception.wrap_pecan_controller_exception
    def attach(self, container_id):
        container = _get_container(container_id)
        check_policy_on_container(container.as_dict(), "container:attach")
        utils.validate_container_state(container, 'attach')
        context = pecan.request.context

        LOG.debug('Checking the status for attach with %s' %
                  container.uuid)
        if container.tty and container.stdin_open:
            context = pecan.request.context
            compute_api = pecan.request.compute_api
            url = compute_api.container_attach(context, container)
            return url
        msg = _("Container doesn't support to be attached, "
                "please check the tty and stdin_open set properly")
        raise exception.NoInteractiveFlag(msg=msg)

    @pecan.expose('json')
    @exception.wrap_pecan_controller_exception
    @validation.validate_query_param(pecan.request, schema.query_param_resize)
    def resize(self, container_id, **kw):
        container = _get_container(container_id)
        check_policy_on_container(container.as_dict(), "container:resize")
        utils.validate_container_state(container, 'resize')
        LOG.debug('Calling tty resize with %s ' % (container.uuid))
        context = pecan.request.context
        compute_api = pecan.request.compute_api
        compute_api.container_resize(context, container, kw.get('h', None),
                                     kw.get('w', None))

    @pecan.expose('json')
    @exception.wrap_pecan_controller_exception
    @validation.validate_query_param(pecan.request, schema.query_param_top)
    def top(self, container_id, ps_args=None):
        container = _get_container(container_id)
        check_policy_on_container(container.as_dict(), "container:top")
        utils.validate_container_state(container, 'top')
        LOG.debug('Calling compute.container_top with %s' %
                  container.uuid)
        context = pecan.request.context
        compute_api = pecan.request.compute_api
        return compute_api.container_top(context, container, ps_args)

    @pecan.expose('json')
    @exception.wrap_pecan_controller_exception
    def get_archive(self, container_id, **kw):
        container = _get_container(container_id)
        check_policy_on_container(container.as_dict(), "container:get_archive")
        utils.validate_container_state(container, 'get_archive')
        LOG.debug('Calling compute.container_get_archive with %s path %s'
                  % (container.uuid, kw['path']))
        context = pecan.request.context
        compute_api = pecan.request.compute_api
        data, stat = compute_api.container_get_archive(
            context, container, kw['path'])
        return {"data": data, "stat": stat}

    @pecan.expose('json')
    @exception.wrap_pecan_controller_exception
    def put_archive(self, container_id, **kw):
        container = _get_container(container_id)
        check_policy_on_container(container.as_dict(), "container:put_archive")
        utils.validate_container_state(container, 'put_archive')
        LOG.debug('Calling compute.container_put_archive with %s path %s'
                  % (container.uuid, kw['path']))
        context = pecan.request.context
        compute_api = pecan.request.compute_api
        compute_api.container_put_archive(context, container,
                                          kw['path'], kw['data'])
