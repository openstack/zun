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

from oslo_versionedobjects import fields

from zun.objects import base
from zun.objects import fields as zun_fields


@base.ZunObjectRegistry.register
class RequestGroup(base.ZunPersistentObject, base.ZunObject):
    # Version 1.0: Initial version
    VERSION = '1.0'

    fields = {
        'use_same_provider': fields.BooleanField(default=True),
        'resources': fields.DictOfIntegersField(default={}),
        'required_traits': zun_fields.SetOfStringsField(default=set()),
        'forbidden_traits': zun_fields.SetOfStringsField(default=set()),
        # The aggregates field has a form of
        #     [[aggregate_UUID1],
        #      [aggregate_UUID2, aggregate_UUID3]]
        # meaning that the request should be fulfilled from an RP that is a
        # member of the aggregate aggregate_UUID1 and member of the aggregate
        # aggregate_UUID2 or aggregate_UUID3 .
        'aggregates': zun_fields.ListOfListsOfStringsField(default=[]),
        # The entity the request is coming from (e.g. the Neutron port uuid)
        # which may not always be a UUID.
        'requester_id': fields.StringField(nullable=True, default=None),
        # The resource provider UUIDs that together fulfill the request
        # NOTE(gibi): this can be more than one if this is the unnumbered
        # request group (i.e. use_same_provider=False)
        'provider_uuids': fields.ListOfUUIDField(default=[]),
        'in_tree': fields.UUIDField(nullable=True, default=None),
    }

    def __init__(self, context=None, **kwargs):
        super(RequestGroup, self).__init__(context=context, **kwargs)
        self.obj_set_defaults()
