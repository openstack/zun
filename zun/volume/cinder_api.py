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

import six

from cinderclient import exceptions as cinder_exception
from oslo_log import log as logging
from oslo_utils import excutils
from oslo_utils import uuidutils

from zun.common import clients
from zun.common import exception
from zun.common.i18n import _
import zun.conf


LOG = logging.getLogger(__name__)

CONF = zun.conf.CONF


class CinderAPI(object):

    def __init__(self, context):
        self.context = context
        self.cinder = clients.OpenStackClients(self.context).cinder()

    def __getattr__(self, key):
        return getattr(self.cinder, key)

    def get(self, volume_id):
        return self.cinder.volumes.get(volume_id)

    def search_volume(self, volume):
        if uuidutils.is_uuid_like(volume):
            try:
                volume = self.cinder.volumes.get(volume)
            except cinder_exception.NotFound:
                raise exception.VolumeNotFound(volume=volume)
        else:
            try:
                volume = self.cinder.volumes.find(name=volume)
            except cinder_exception.NotFound:
                raise exception.VolumeNotFound(volume=volume)
            except cinder_exception.NoUniqueMatch:
                raise exception.Conflict(_(
                    'Multiple cinder volumes exist with same name. '
                    'Please use the uuid instead.'))

        return volume

    def ensure_volume_usable(self, volume):
        # Make sure the container has access to the volume.
        if hasattr(volume, 'os-vol-tenant-attr:tenant_id'):
            project_id = self.context.project_id
            if getattr(volume, 'os-vol-tenant-attr:tenant_id') != project_id:
                raise exception.VolumeNotUsable(volume=volume.id)

        if volume.attachments and not volume.multiattach:
            raise exception.VolumeInUse(volume=volume.id)

    def reserve_volume(self, volume_id):
        return self.cinder.volumes.reserve(volume_id)

    def unreserve_volume(self, volume_id):
        return self.cinder.volumes.unreserve(volume_id)

    def initialize_connection(self, volume_id, connector):
        try:
            connection_info = self.cinder.volumes.initialize_connection(
                volume_id, connector)
            return connection_info
        except cinder_exception.ClientException as ex:
            with excutils.save_and_reraise_exception():
                LOG.error('Initialize connection failed for volume '
                          '%(vol)s on host %(host)s. Error: %(msg)s '
                          'Code: %(code)s. Attempting to terminate '
                          'connection.',
                          {'vol': volume_id,
                           'host': connector.get('host'),
                           'msg': six.text_type(ex),
                           'code': ex.code})
                try:
                    self.terminate_connection(volume_id, connector)
                except Exception as exc:
                    LOG.error('Connection between volume %(vol)s and host '
                              '%(host)s might have succeeded, but attempt '
                              'to terminate connection has failed. '
                              'Validate the connection and determine if '
                              'manual cleanup is needed. Error: %(msg)s '
                              'Code: %(code)s.',
                              {'vol': volume_id,
                               'host': connector.get('host'),
                               'msg': six.text_type(exc),
                               'code': (exc.code
                                        if hasattr(exc, 'code') else None)})

    def terminate_connection(self, volume_id, connector):
        return self.cinder.volumes.terminate_connection(volume_id, connector)

    def attach(self, volume_id, mountpoint, hostname):
        return self.cinder.volumes.attach(volume=volume_id,
                                          instance_uuid=None,
                                          mountpoint=mountpoint,
                                          host_name=hostname)

    def detach(self, volume_id):
        attachment_id = None
        volume = self.get(volume_id)
        attachments = volume.attachments or {}
        for am in attachments:
            if am['host_name'].lower() == CONF.host.lower():
                attachment_id = am['attachment_id']
                break

        if attachment_id is None and volume.multiattach:
            LOG.warning("attachment_id couldn't be retrieved for "
                        "volume %(volume_id)s. The volume has the "
                        "'multiattach' flag enabled, without the "
                        "attachment_id Cinder most probably "
                        "cannot perform the detach.",
                        {'volume_id': volume_id})

        return self.cinder.volumes.detach(volume_id, attachment_id)

    def begin_detaching(self, volume_id):
        self.cinder.volumes.begin_detaching(volume_id)

    def roll_detaching(self, volume_id):
        self.cinder.volumes.roll_detaching(volume_id)

    def create_volume(self, size):
        try:
            volume = self.cinder.volumes.create(size)
        except cinder_exception.ClientException as ex:
            LOG.error('Volume creation failed: %(ex)s', {'ex': ex})
            raise exception.VolumeCreateFailed(creation_failed=ex)

        return volume

    def delete_volume(self, volume_id):
        try:
            self.cinder.volumes.delete(volume_id)
        except cinder_exception.ClientException as ex:
            LOG.error('Volume deletion failed: %(ex)s',
                      {'ex': ex})
            raise exception.VolumeDeleteFailed(deletion_failed=ex)
