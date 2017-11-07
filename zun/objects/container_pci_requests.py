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

from oslo_serialization import jsonutils
from oslo_utils import versionutils
from oslo_versionedobjects import fields

from zun.objects import base


@base.ZunObjectRegistry.register
class ContainerPCIRequest(base.ZunPersistentObject, base.ZunObject):
    # Version 1.0: Add request_id
    VERSION = '1.0'

    fields = {
        'count': fields.IntegerField(),
        'spec': fields.ListOfDictOfNullableStringsField(),
        'alias_name': fields.StringField(nullable=True),
        # Note(moshele): is_new is deprecated and should be removed
        # on major version bump
        'is_new': fields.BooleanField(default=False),
        'request_id': fields.UUIDField(nullable=True),
    }

    def obj_load_attr(self, attr):
        setattr(self, attr, None)

    def obj_make_compatible(self, primitive, target_version):
        target_version = versionutils.convert_version_to_tuple(target_version)
        if target_version < (1, 1) and 'request_id' in primitive:
            del primitive['request_id']


@base.ZunObjectRegistry.register
class ContainerPCIRequests(base.ZunPersistentObject, base.ZunObject):
    # Version 1.0: Initial version
    VERSION = '1.0'

    fields = {
        'container_uuid': fields.UUIDField(),
        'requests': fields.ListOfObjectsField('ContainerPCIRequest'),
    }

    def to_json(self):
        blob = [{'count': x.count,
                 'spec': x.spec,
                 'alias_name': x.alias_name,
                 'is_new': x.is_new,
                 'request_id': x.request_id} for x in self.requests]
        return jsonutils.dumps(blob)

    @classmethod
    def from_request_spec_container_props(cls, pci_requests):
        objs = [ContainerPCIRequest(**request)
                for request in pci_requests['requests']]
        return cls(requests=objs,
                   container_uuid=pci_requests['container_uuid'])
