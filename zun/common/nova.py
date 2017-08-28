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

import requests
import six

from novaclient import exceptions
from oslo_log import log as logging
from oslo_utils import excutils
from oslo_utils import uuidutils

from zun.common import clients
from zun.common import exception
from zun.common.i18n import _


LOG = logging.getLogger(__name__)


def retry_if_connection_err(exception):
    return isinstance(exception, requests.ConnectionError)


class NovaClient(object):

    deferred_server_statuses = ['BUILD',
                                'HARD_REBOOT',
                                'PASSWORD',
                                'REBOOT',
                                'RESCUE',
                                'RESIZE',
                                'REVERT_RESIZE',
                                'SHUTOFF',
                                'SUSPENDED',
                                'VERIFY_RESIZE']

    def __init__(self, context):
        self.context = context
        self._client = None

    def client(self):
        if not self._client:
            self._client = clients.OpenStackClients(self.context).nova()
        return self._client

    def is_not_found(self, ex):
        return isinstance(ex, exceptions.NotFound)

    def create_server(self, name, image, flavor, **kwargs):
        image = self.get_image_by_name_or_id(image)
        flavor = self.get_flavor_by_name_or_id(flavor)
        return self.client().servers.create(name, image, flavor, **kwargs)

    def get_image_by_name_or_id(self, image_ident):
        """Get an image by name or ID."""
        try:
            return self.client().glance.find_image(image_ident)
        except exceptions.NotFound as e:
            raise exception.ImageNotFound(six.text_type(e))
        except exceptions.NoUniqueMatch as e:
            raise exception.Conflict(six.text_type(e))

    def get_flavor_by_name_or_id(self, flavor_ident):
        """Get the flavor object for the specified flavor name or id.

        :param flavor_identifier: the name or id of the flavor to find
        :returns: a flavor object with name or id :flavor:
        """
        try:
            flavor = self.client().flavors.get(flavor_ident)
        except exceptions.NotFound:
            flavor = self.client().flavors.find(name=flavor_ident)

        return flavor

    def fetch_server(self, server_id):
        """Fetch fresh server object from Nova.

        Log warnings and return None for non-critical API errors.
        Use this method in various ``check_*_complete`` resource methods,
        where intermittent errors can be tolerated.
        """
        server = None
        try:
            server = self.client().servers.get(server_id)
        except exceptions.OverLimit as exc:
            LOG.warning("Received an OverLimit response when "
                        "fetching server (%(id)s) : %(exception)s",
                        {'id': server_id,
                         'exception': exc})
        except exceptions.ClientException as exc:
            if ((getattr(exc, 'http_status', getattr(exc, 'code', None)) in
                 (500, 503))):
                LOG.warning("Received the following exception when "
                            "fetching server (%(id)s) : %(exception)s",
                            {'id': server_id,
                             'exception': exc})
            else:
                raise
        return server

    def refresh_server(self, server):
        """Refresh server's attributes.

        Also log warnings for non-critical API errors.
        """
        try:
            server.get()
        except exceptions.OverLimit as exc:
            LOG.warning("Server %(name)s (%(id)s) received an OverLimit "
                        "response during server.get(): %(exception)s",
                        {'name': server.name,
                         'id': server.id,
                         'exception': exc})
        except exceptions.ClientException as exc:
            if ((getattr(exc, 'http_status', getattr(exc, 'code', None)) in
                 (500, 503))):
                LOG.warning('Server "%(name)s" (%(id)s) received the '
                            'following exception during server.get(): '
                            '%(exception)s',
                            {'name': server.name,
                             'id': server.id,
                             'exception': exc})
            else:
                raise

    def get_status(self, server):
        """Return the server's status.

        :param server: server object
        :returns: status as a string
        """
        # Some clouds append extra (STATUS) strings to the status, strip it
        return server.status.split('(')[0]

    def check_active(self, server):
        """Check server status.

        Accepts both server IDs and server objects.
        Returns True if server is ACTIVE,
        raises errors when server has an ERROR or unknown to Zun status,
        returns False otherwise.

        """
        # not checking with is_uuid_like as most tests use strings e.g. '1234'
        if isinstance(server, six.string_types):
            server = self.fetch_server(server)
            if server is None:
                return False
            else:
                status = self.get_status(server)
        else:
            status = self.get_status(server)
            if status != 'ACTIVE':
                self.refresh_server(server)
                status = self.get_status(server)

        if status in self.deferred_server_statuses:
            return False
        elif status == 'ACTIVE':
            return True
        elif status == 'ERROR':
            fault = getattr(server, 'fault', {})
            raise exception.ServerInError(
                resource_status=status,
                status_reason=_("Message: %(message)s, Code: %(code)s") % {
                    'message': fault.get('message', _('Unknown')),
                    'code': fault.get('code', _('Unknown'))
                })
        else:
            raise exception.ServerUnknownStatus(
                resource_status=server.status,
                status_reason=_('Unknown'),
                result=_('Server is not active'))

    def delete_server(self, server):
        server_id = self.get_server_id(server, raise_on_error=False)
        if server_id:
            self.client().servers.delete(server_id)
            return server_id

    def stop_server(self, server):
        server_id = self.get_server_id(server, raise_on_error=False)
        if server_id:
            self.client().servers.stop(server_id)
            return server_id

    def check_delete_server_complete(self, server_id):
        """Wait for server to disappear from Nova."""
        try:
            server = self.fetch_server(server_id)
        except Exception as exc:
            self.ignore_not_found(exc)
            return True
        if not server:
            return False
        task_state_in_nova = getattr(server, 'OS-EXT-STS:task_state', None)
        # the status of server won't change until the delete task has done
        if task_state_in_nova == 'deleting':
            return False

        status = self.get_status(server)
        if status in ("DELETED", "SOFT_DELETED"):
            return True
        if status == 'ERROR':
            fault = getattr(server, 'fault', {})
            message = fault.get('message', 'Unknown')
            code = fault.get('code')
            errmsg = _("Server %(name)s delete failed: (%(code)s) "
                       "%(message)s") % dict(name=server.name,
                                             code=code,
                                             message=message)
            raise exception.ServerInError(resource_status=status,
                                          status_reason=errmsg)
        return False

    @excutils.exception_filter
    def ignore_not_found(self, ex):
        """Raises the exception unless it is a not-found."""
        return self.is_not_found(ex)

    def get_addresses(self, server):
        """Return the server's IP address, fetching it from Nova."""
        try:
            server_id = self.get_server_id(server)
            server = self.client().servers.get(server_id)
        except exceptions.NotFound as ex:
            LOG.warning('Instance (%(server)s) not found: %(ex)s',
                        {'server': server, 'ex': ex})
        else:
            return server.addresses

    def get_server_id(self, server, raise_on_error=True):
        if uuidutils.is_uuid_like(server):
            return server
        elif isinstance(server, six.string_types):
            servers = self.client().servers.list(search_opts={'name': server})
            if len(servers) == 1:
                return servers[0].id

            if raise_on_error:
                raise exception.ZunException(_(
                    "Unable to get server id with name %s") % server)
        else:
            raise exception.ZunException(_("Unexpected server type"))
