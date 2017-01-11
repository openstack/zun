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
from oslo_utils import timeutils
import pecan
from pecan import rest

from zun.api.controllers import base
from zun.api.controllers import link
from zun.api.controllers import types
from zun.api.controllers.v1 import collection
from zun.api.controllers.v1.schemas import containers as schema
from zun.api import utils as api_utils
from zun.common import exception
from zun.common.i18n import _LE
from zun.common import name_generator
from zun.common import policy
from zun.common import utils
from zun.common import validation
from zun import objects
from zun.objects import fields


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


class Container(base.APIBase):
    """API representation of a container.

    This class enforces type checking and value constraints, and converts
    between the internal object model and the API representation of a
    container.
    """

    fields = {
        'uuid',
        'name',
        'image',
        'links',
        'command',
        'status',
        'status_reason',
        'task_state',
        'cpu',
        'memory',
        'environment',
        'workdir',
        'ports',
        'hostname',
        'labels',
        'addresses',
        'image_pull_policy',
        'host',
    }

    def __init__(self, **kwargs):
        super(Container, self).__init__(**kwargs)

    @staticmethod
    def _convert_with_links(container, url, expand=True):
        if not expand:
            container.unset_fields_except([
                'uuid', 'name', 'image', 'command', 'status', 'cpu', 'memory',
                'environment', 'task_state', 'workdir', 'ports', 'hostname',
                'labels', 'addresses', 'image_pull_policy', 'status_reason',
                'host'])

        container.links = [link.Link.make_link(
            'self', url,
            'containers', container.uuid),
            link.Link.make_link(
                'bookmark', url,
                'containers', container.uuid,
                bookmark=True)]
        return container

    @classmethod
    def convert_with_links(cls, rpc_container, expand=True):
        container = Container(**rpc_container)

        return cls._convert_with_links(container, pecan.request.host_url,
                                       expand)

    @classmethod
    def sample(cls, expand=True):
        sample = cls(uuid='27e3153e-d5bf-4b7e-b517-fb518e17f34c',
                     name='example',
                     image='ubuntu',
                     command='env',
                     status='Running',
                     status_reason='',
                     cpu=1.0,
                     memory='512m',
                     environment={'key1': 'val1', 'key2': 'val2'},
                     workdir='/home/ubuntu',
                     ports=[80, 443],
                     hostname='testhost',
                     host='localhost',
                     labels={'key1': 'val1', 'key2': 'val2'},
                     addresses={
                         'private': [
                             {'OS-EXT-IPS-MAC:mac_addr': 'fa:16:3e:04:da:76',
                              'version': 4,
                              'addr': '10.0.0.12',
                              'OS-EXT-IPS:type': 'fixed'},
                         ],
                     },
                     created_at=timeutils.utcnow(),
                     updated_at=timeutils.utcnow())
        return cls._convert_with_links(sample, 'http://localhost:9517', expand)


class ContainerCollection(collection.Collection):
    """API representation of a collection of containers."""

    fields = {
        'containers': {
            'validate': types.List(types.Custom(Container)).validate,
        },
    }

    """A list containing containers objects"""

    def __init__(self, **kwargs):
        self._type = 'containers'

    @staticmethod
    def convert_with_links(rpc_containers, limit, url=None,
                           expand=False, **kwargs):
        collection = ContainerCollection()
        collection.containers = \
            [Container.convert_with_links(p.as_dict(), expand)
             for p in rpc_containers]
        collection.next = collection.get_next(limit, url=url, **kwargs)
        return collection

    @classmethod
    def sample(cls):
        sample = cls()
        sample.containers = [Container.sample(expand=False)]
        return sample


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
        'kill': ['POST']
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
        return Container.convert_with_links(container.as_dict())

    def _generate_name_for_container(self):
        '''Generate a random name like: zeta-22-bay.'''
        name_gen = name_generator.NameGenerator()
        name = name_gen.generate()
        return name + '-container'

    @pecan.expose('json')
    @api_utils.enforce_content_types(['application/json'])
    @exception.wrap_pecan_controller_exception
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
        # NOTE(mkrai): Intent here is to check the existence of image
        # before proceeding to create container. If image is not found,
        # container create will fail with 400 status.
        images = compute_api.image_search(context, container_dict['image'],
                                          True)
        if not images:
            raise exception.ImageNotFound(container_dict['image'])
        container_dict['project_id'] = context.project_id
        container_dict['user_id'] = context.user_id
        name = container_dict.get('name') or \
            self._generate_name_for_container()
        container_dict['name'] = name
        if container_dict.get('memory'):
            container_dict['memory'] = \
                str(container_dict['memory']) + 'M'
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
        return Container.convert_with_links(new_container.as_dict())

    @pecan.expose('json')
    @exception.wrap_pecan_controller_exception
    def patch(self, container_id, **kwargs):
        """Update an existing container.

        :param patch: a json PATCH document to apply to this container.
        """
        context = pecan.request.context
        container = _get_container(container_id)
        check_policy_on_container(container.as_dict(), "container:update")
        try:
            patch = kwargs.get('patch')
            container_dict = container.as_dict()
            new_container = Container(**api_utils.apply_jsonpatch(
                container_dict, patch))
        except api_utils.JSONPATCH_EXCEPTIONS as e:
            raise exception.PatchError(patch=patch, reason=e)

        # Update only the fields that have changed
        for field in objects.Container.fields:
            try:
                patch_val = getattr(new_container, field)
            except AttributeError:
                # Ignore fields that aren't exposed in the API
                continue
            if getattr(container, field) != patch_val:
                setattr(container, field, patch_val)

        container.save(context)
        return Container.convert_with_links(container.as_dict())

    @pecan.expose('json')
    @exception.wrap_pecan_controller_exception
    def delete(self, container_id, force=False):
        """Delete a container.

        :param container_ident: UUID or Name of a container.
        """
        container = _get_container(container_id)
        check_policy_on_container(container.as_dict(), "container:delete")
        force = strutils.bool_from_string(force, strict=True)
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
    def logs(self, container_id):
        container = _get_container(container_id)
        check_policy_on_container(container.as_dict(), "container:logs")
        LOG.debug('Calling compute.container_logs with %s' %
                  container.uuid)
        context = pecan.request.context
        compute_api = pecan.request.compute_api
        return compute_api.container_logs(context, container)

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
