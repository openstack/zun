# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# It's based on oslo.i18n usage in OpenStack Keystone project and
# recommendations from
# https://docs.openstack.org/oslo.i18n/latest/user/usage.html

"""Utilities and helper functions."""
import eventlet
import functools
import inspect
import json
import mimetypes

from oslo_concurrency import lockutils
from oslo_concurrency import processutils
from oslo_context import context as common_context
from oslo_log import log as logging
from oslo_utils import excutils
from oslo_utils import strutils
import pecan
import six

from zun.api import utils as api_utils
from zun.common import clients
from zun.common import consts
from zun.common import exception
from zun.common.i18n import _
from zun.common import privileged
import zun.conf
from zun.network import neutron
from zun import objects

CONF = zun.conf.CONF
LOG = logging.getLogger(__name__)
NETWORK_ATTACH_EXTERNAL = 'network:attach_external_network'

synchronized = lockutils.synchronized_with_prefix(consts.NAME_PREFIX)

VALID_STATES = {
    'commit': [consts.RUNNING, consts.STOPPED, consts.PAUSED],
    'delete': [consts.CREATED, consts.ERROR, consts.STOPPED, consts.DELETED,
               consts.DEAD],
    'delete_force': [consts.CREATED, consts.CREATING, consts.ERROR,
                     consts.RUNNING, consts.STOPPED, consts.UNKNOWN,
                     consts.DELETED, consts.DEAD, consts.RESTARTING,
                     consts.REBUILDING],
    'delete_after_stop': [consts.RUNNING, consts.CREATED, consts.ERROR,
                          consts.STOPPED, consts.DELETED, consts.DEAD],
    'start': [consts.CREATED, consts.STOPPED, consts.ERROR],
    'stop': [consts.RUNNING],
    'reboot': [consts.CREATED, consts.RUNNING, consts.STOPPED, consts.ERROR],
    'rebuild': [consts.CREATED, consts.RUNNING, consts.STOPPED, consts.ERROR],
    'pause': [consts.RUNNING],
    'unpause': [consts.PAUSED],
    'kill': [consts.RUNNING],
    'execute': [consts.RUNNING],
    'execute_resize': [consts.RUNNING],
    'update': [consts.CREATED, consts.RUNNING, consts.STOPPED, consts.PAUSED],
    'attach': [consts.RUNNING],
    'resize': [consts.RUNNING],
    'top': [consts.RUNNING],
    'get_archive': [consts.CREATED, consts.PAUSED, consts.RUNNING,
                    consts.STOPPED],
    'put_archive': [consts.CREATED, consts.PAUSED, consts.RUNNING,
                    consts.STOPPED],
    'logs': [consts.CREATED, consts.ERROR, consts.PAUSED, consts.RUNNING,
             consts.STOPPED, consts.UNKNOWN],
    'stats': [consts.RUNNING],
    'add_security_group': [consts.CREATED, consts.RUNNING, consts.STOPPED,
                           consts.PAUSED],
    'remove_security_group': [consts.CREATED, consts.RUNNING, consts.STOPPED,
                              consts.PAUSED],
    'resize_container': [consts.CREATED, consts.RUNNING, consts.STOPPED,
                         consts.PAUSED]
}

VALID_CONTAINER_FILED = {
    'image': 'image',
    'command': 'command',
    'args': 'args',
    'resources': 'resources',
    'ports': 'ports',
    'volumeMounts': 'volumeMounts',
    'env': 'environment',
    'workDir': 'workdir',
    'imagePullPolicy': 'image_pull_policy',
}

VALID_CAPSULE_FIELD = {
    'restartPolicy': 'restart_policy',
}

VALID_CAPSULE_RESTART_POLICY = {
    'Never': 'no',
    'Always': 'always',
    'OnFailure': 'on-failure',
}


def validate_container_state(container, action):
    if container.status not in VALID_STATES[action]:
        raise exception.InvalidStateException(
            id=container.uuid,
            action=action,
            actual_state=container.status)


def validate_image_driver(image_driver):
    if image_driver not in CONF.image_driver_list:
        detail = _("Invalid input for image_driver, "
                   "it should be within the image drivers list")
        raise exception.ValidationError(detail=detail)


def safe_rstrip(value, chars=None):
    """Removes trailing characters from a string if that does not make it empty

    :param value: A string value that will be stripped.
    :param chars: Characters to remove.
    :return: Stripped value.

    """
    if not isinstance(value, six.string_types):
        LOG.warning(
            "Failed to remove trailing character. Returning original object. "
            "Supplied object is not a string: %s.", value)
        return value

    return value.rstrip(chars) or value


def _do_allow_certain_content_types(func, content_types_list):
    # Allows you to bypass pecan's content-type restrictions
    cfg = pecan.util._cfg(func)
    cfg.setdefault('content_types', {})
    cfg['content_types'].update((value, '')
                                for value in content_types_list)
    return func


def allow_certain_content_types(*content_types_list):
    def _wrapper(func):
        return _do_allow_certain_content_types(func, content_types_list)
    return _wrapper


def allow_all_content_types(f):
    return _do_allow_certain_content_types(f, mimetypes.types_map.values())


def parse_image_name(image, driver=None):
    image_parts = image.split(':', 1)

    image_repo = image_parts[0]
    if driver is None:
        driver = CONF.default_image_driver
    if driver == 'glance':
        image_tag = ''
    else:
        image_tag = 'latest'

    if len(image_parts) > 1:
        image_tag = image_parts[1]

    return image_repo, image_tag


def spawn_n(func, *args, **kwargs):
    """Passthrough method for eventlet.spawn_n.

    This utility exists so that it can be stubbed for testing without
    interfering with the service spawns.

    It will also grab the context from the threadlocal store and add it to
    the store on the new thread.  This allows for continuity in logging the
    context when using this method to spawn a new thread.
    """
    _context = common_context.get_current()

    @functools.wraps(func)
    def context_wrapper(*args, **kwargs):
        # NOTE: If update_store is not called after spawn_n it won't be
        # available for the logger to pull from threadlocal storage.
        if _context is not None:
            _context.update_store()
        func(*args, **kwargs)

    eventlet.spawn_n(context_wrapper, *args, **kwargs)


def translate_exception(function):
    """Wraps a method to catch exceptions.

    If the exception is not an instance of ZunException,
    translate it into one.
    """

    @functools.wraps(function)
    def decorated_function(self, context, *args, **kwargs):
        try:
            return function(self, context, *args, **kwargs)
        except Exception as e:
            if not isinstance(e, exception.ZunException):
                LOG.exception("Unexpected error: %s", six.text_type(e))
                e = exception.ZunException("Unexpected error: %s"
                                           % six.text_type(e))
                raise e
            raise

    return decorated_function


def check_container_id(function):
    """Check container_id property of given container instance."""

    @functools.wraps(function)
    def decorated_function(*args, **kwargs):
        container = args[2]
        if getattr(container, 'container_id', None) is None:
            msg = _("Cannot operate an uncreated container.")
            raise exception.Invalid(message=msg)
        return function(*args, **kwargs)

    return decorated_function


def get_image_pull_policy(image_pull_policy, image_tag):
    if not image_pull_policy:
        if image_tag == 'latest' or not image_tag:
            image_pull_policy = 'always'
        else:
            image_pull_policy = 'ifnotpresent'
    return image_pull_policy


def should_pull_image(image_pull_policy, present):
    if image_pull_policy == 'never':
        return False
    if (image_pull_policy == 'always' or
            (image_pull_policy == 'ifnotpresent' and not present)):
        return True
    return False


def get_floating_cpu_set():
    """Parse floating_cpu_set config.

    :returns: a set of pcpu ids can be used by containers
    """

    if not CONF.floating_cpu_set:
        return None

    cpuset_ids = parse_floating_cpu(CONF.floating_cpu_set)
    if not cpuset_ids:
        raise exception.Invalid(_("No CPUs available after parsing %r") %
                                CONF.floating_cpu_set)
    return cpuset_ids


def parse_floating_cpu(spec):
    """Parse a CPU set specification.

    Each element in the list is either a single CPU number, a range of
    CPU numbers.

    :param spec: cpu set string eg "1-4,6"
    :returns: a set of CPU indexes

    """

    cpuset_ids = set()
    for rule in spec.split(','):
        range_part = rule.strip().split("-", 1)
        if len(range_part) > 1:
            try:
                start, end = [int(p.strip()) for p in range_part]
            except ValueError:
                raise exception.Invalid()
            if start < end:
                cpuset_ids |= set(range(start, end + 1))
            else:
                raise exception.Invalid()
        else:
            try:
                cpuset_ids.add(int(rule))
            except ValueError:
                raise exception.Invalid()

    return cpuset_ids


def get_security_group_ids(context, security_groups, **kwargs):
    if not security_groups:
        return None
    else:
        neutron = clients.OpenStackClients(context).neutron()
        search_opts = {'tenant_id': context.project_id}
        security_groups_list = neutron.list_security_groups(
            **search_opts).get('security_groups', [])
        security_group_ids = [item['id'] for item in security_groups_list
                              if item['name'] in security_groups
                              or item['id'] in security_groups]
        if len(security_group_ids) >= len(security_groups):
            return security_group_ids
        else:
            raise exception.ZunException(_(
                "Any of the security group in %s is not found ") %
                security_groups)


def custom_execute(*cmd, **kwargs):
    try:
        return processutils.execute(*cmd, **kwargs)
    except processutils.ProcessExecutionError as e:
        sanitized_cmd = strutils.mask_password(' '.join(cmd))
        raise exception.CommandError(cmd=sanitized_cmd,
                                     error=six.text_type(e))


def get_root_helper():
    return 'sudo zun-rootwrap %s' % CONF.rootwrap_config


@privileged.default.entrypoint
def execute_root(*cmd, **kwargs):
    # NOTE(kiennt): Set run_as_root=False because if it is set to True, the
    #               command is prefixed by the command specified in the
    #               root_helper kwargs [1]. But we use oslo.privsep instead
    #               of rootwrap so set run_as_root=False.
    # [1] https://github.com/openstack/oslo.concurrency/blob/master/oslo_concurrency/processutils.py#L218 # noqa
    return custom_execute(*cmd, shell=False, run_as_root=False, **kwargs)


def execute(*cmd, **kwargs):
    run_as_root = kwargs.pop('run_as_root', False)
    # NOTE(kiennt): Root_helper is unnecessary when use privsep,
    #               therefore pop it!
    kwargs.pop('root_helper', None)
    if run_as_root:
        return execute_root(*cmd, **kwargs)
    else:
        return custom_execute(*cmd, **kwargs)


def check_capsule_template(tpl):
    # TODO(kevinz): add volume spec check
    tpl_json = tpl
    if isinstance(tpl, six.string_types):
        try:
            tpl_json = json.loads(tpl)
        except Exception as e:
            raise exception.FailedParseStringToJson(e)

    kind_field = tpl_json.get('kind')
    if kind_field not in ['capsule', 'Capsule']:
        raise exception.InvalidCapsuleTemplate("kind fields need to be "
                                               "set as capsule or Capsule")

    spec_field = tpl_json.get('spec')
    if spec_field is None:
        raise exception.InvalidCapsuleTemplate("No Spec found")
    # Align the Capsule restartPolicy with container restart_policy
    # Also change the template filed name from Kubernetes type to OpenStack
    # type.
    if 'restartPolicy' in spec_field.keys():
        spec_field['restartPolicy'] = \
            VALID_CAPSULE_RESTART_POLICY[spec_field['restartPolicy']]
        spec_field[VALID_CAPSULE_FIELD['restartPolicy']] = \
            spec_field.pop('restartPolicy')
    if spec_field.get('containers') is None:
        raise exception.InvalidCapsuleTemplate("No valid containers field")
    return spec_field, tpl_json


def capsule_get_container_spec(spec_field):
    containers_spec = spec_field.get('containers')
    containers_num = len(containers_spec)
    if containers_num == 0:
        raise exception.InvalidCapsuleTemplate("Capsule need to have one "
                                               "container at least")

    for i in range(0, containers_num):
        container_spec = containers_spec[i]
        if 'image' not in container_spec.keys():
            raise exception.InvalidCapsuleTemplate("Container "
                                                   "image is needed")
        # Remap the Capsule's container fields to native Zun container fields.
        for key in list(container_spec.keys()):
            container_spec[VALID_CONTAINER_FILED[key]] = \
                container_spec.pop(key)

    return containers_spec


def capsule_get_volume_spec(spec_field):
    volumes_spec = spec_field.get('volumes')
    if not volumes_spec:
        return []
    volumes_num = len(volumes_spec)

    for i in range(volumes_num):
        volume_name = volumes_spec[i].get('name')
        if volume_name is None:
            raise exception.InvalidCapsuleTemplate("Volume name "
                                                   "is needed")
        if volumes_spec[i].get('cinder'):
            cinder_spec = volumes_spec[i].get('cinder')
            volume_uuid = cinder_spec.get('volumeID')
            volume_size = cinder_spec.get('size')
            if not volume_uuid:
                if volume_size is None:
                    raise exception.InvalidCapsuleTemplate("Volume size "
                                                           "is needed")
            elif volume_uuid and volume_size:
                raise exception.InvalidCapsuleTemplate("Volume size and uuid "
                                                       "could not be set at "
                                                       "the same time")
        else:
            raise exception.InvalidCapsuleTemplate("Zun now Only support "
                                                   "Cinder volume driver")

    return volumes_spec


def is_all_projects(search_opts):
    all_projects = search_opts.get('all_projects')
    if all_projects:
        try:
            all_projects = strutils.bool_from_string(all_projects, True)
        except ValueError as err:
            raise exception.InvalidValue(six.text_type(err))
    else:
        all_projects = False
    return all_projects


def get_container(container_ident):
    container = api_utils.get_resource('Container', container_ident)
    if not container:
        pecan.abort(404, ('Not found; the container you requested '
                          'does not exist.'))

    return container


def get_image(image_id):
    image = api_utils.get_resource('Image', image_id)
    if not image:
        pecan.abort(404, ('Not found; the image you requested '
                          'does not exist.'))

    return image


def check_for_restart_policy(container_dict):
    """Check for restart policy input

    :param container_dict: a container within the request body.
    """
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


def build_requested_networks(context, nets):
    """Build requested networks by calling neutron client

    :param nets: The special network uuid when create container
                 if none, will call neutron to create new network.
    :returns: available network and ports
    """
    neutron_api = neutron.NeutronAPI(context)
    requested_networks = []
    for net in nets:
        if net.get('port'):
            port = neutron_api.get_neutron_port(net['port'])
            neutron_api.ensure_neutron_port_usable(port)
            network = neutron_api.get_neutron_network(port['network_id'])
            requested_networks.append({'network': port['network_id'],
                                       'port': port['id'],
                                       'router:external':
                                           network.get('router:external'),
                                       'shared': network.get('shared'),
                                       'fixed_ip': '',
                                       'preserve_on_delete': True})
        elif net.get('network'):
            network = neutron_api.get_neutron_network(net['network'])
            requested_networks.append({'network': network['id'],
                                       'port': '',
                                       'router:external':
                                           network.get('router:external'),
                                       'shared': network.get('shared'),
                                       'fixed_ip':
                                           net.get('fixed_ip') or
                                           net.get('v4-fixed-ip', '') or
                                           net.get('v6-fixed-ip', ''),
                                       'preserve_on_delete': False})
    if not requested_networks:
        # Find an available neutron net and create docker network by
        # wrapping the neutron net.
        neutron_net = neutron_api.get_available_network()
        requested_networks.append({'network': neutron_net['id'],
                                   'port': '',
                                   'fixed_ip': '',
                                   'preserve_on_delete': False})

    check_external_network_attach(context, requested_networks)
    return requested_networks


def check_external_network_attach(context, nets):
    """Check if attaching to external network is permitted."""
    if not context.can(NETWORK_ATTACH_EXTERNAL,
                       fatal=False):
        for net in nets:
            if net.get('router:external') and not net.get('shared'):
                raise exception.ExternalNetworkAttachForbidden(
                    network_uuid=net['network'])


class EventReporter(object):
    """Context manager to report container action events."""

    def __init__(self, context, event_name, *container_uuids):
        self.context = context
        self.event_name = event_name
        self.container_uuids = container_uuids

    def __enter__(self):
        for uuid in self.container_uuids:
            objects.ContainerActionEvent.event_start(
                self.context, uuid, self.event_name, want_result=False)

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        for uuid in self.container_uuids:
            objects.ContainerActionEvent.event_finish(
                self.context, uuid, self.event_name, exc_val=exc_val,
                exc_tb=exc_tb, want_result=False)
        return False


def get_wrapped_function(function):
    """Get the method at the bottom of a stack of decorators."""
    if not hasattr(function, '__closure__') or not function.__closure__:
        return function

    def _get_wrapped_function(function):
        if not hasattr(function, '__closure__') or not function.__closure__:
            return None

        for closure in function.__closure__:
            func = closure.cell_contents

            deeper_func = _get_wrapped_function(func)
            if deeper_func:
                return deeper_func
            elif hasattr(closure.cell_contents, '__call__'):
                return closure.cell_contents

        return function

    return _get_wrapped_function(function)


def wrap_container_event(prefix):
    """Warps a method to log the event taken on the container, and result.

    This decorator wraps a method to log the start and result of an event, as
    part of an action taken on a container.
    """
    def helper(function):

        @functools.wraps(function)
        def decorated_function(self, context, *args, **kwargs):
            wrapped_func = get_wrapped_function(function)
            keyed_args = inspect.getcallargs(wrapped_func, self, context,
                                             *args, **kwargs)
            container_uuid = keyed_args['container'].uuid

            event_name = '{0}_{1}'.format(prefix, function.__name__)
            with EventReporter(context, event_name, container_uuid):
                return function(self, context, *args, **kwargs)
        return decorated_function
    return helper


def wrap_exception():
    def helper(function):

        @functools.wraps(function)
        def decorated_function(self, context, container, *args, **kwargs):
            try:
                return function(self, context, container, *args, **kwargs)
            except exception.DockerError as e:
                with excutils.save_and_reraise_exception(reraise=False):
                    LOG.error("Error occurred while calling Docker API: %s",
                              six.text_type(e))
            except Exception as e:
                with excutils.save_and_reraise_exception(reraise=False):
                    LOG.exception("Unexpected exception: %s", six.text_type(e))
        return decorated_function
    return helper
