#    Copyright 2014 Red Hat Inc.
#    Copyright 2017 IBM Corp
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

from oslo_versionedobjects import fields

from zun.common import exception
from zun.objects import base


@base.ZunObjectRegistry.register
class NUMANode(base.ZunObject):
    # Version 1.0: Initial version
    VERSION = '1.0'

    fields = {
        'id': fields.IntegerField(read_only=True),
        'cpuset': fields.SetOfIntegersField(),
        'pinned_cpus': fields.SetOfIntegersField(),
        }

    @property
    def free_cpus(self):
        return self.cpuset - self.pinned_cpus or set()

    @property
    def avail_cpus(self):
        return len(self.free_cpus)

    def pin_cpus(self, cpus):
        if cpus - self.cpuset:
            raise exception.CPUPinningUnknown(requested=list(cpus),
                                              cpuset=list(self.pinned_cpus))
        if self.pinned_cpus & cpus:
            raise exception.CPUPinningInvalid(requested=list(cpus),
                                              free=list(self.cpuset -
                                                        self.pinned_cpus))
        self.pinned_cpus |= cpus

    def unpin_cpus(self, cpus):
        if cpus - self.cpuset:
            raise exception.CPUUnpinningUnknown(requested=list(cpus),
                                                cpuset=list(self.pinned_cpus))
        if (self.pinned_cpus & cpus) != cpus:
            raise exception.CPUUnpinningInvalid(requested=list(cpus),
                                                pinned=list(self.pinned_cpus))
        self.pinned_cpus -= cpus

    def _to_dict(self):
        return {
            'id': self.id,
            'cpuset': list(self.cpuset),
            'pinned_cpus': list(self.pinned_cpus)
            }

    @classmethod
    def _from_dict(cls, data_dict):
        cpuset = set(data_dict.get('cpuset', ''))
        node_id = data_dict.get('id')
        pinned_cpus = set(data_dict.get('pinned_cpus'))
        return cls(id=node_id, cpuset=cpuset,
                   pinned_cpus=pinned_cpus)


@base.ZunObjectRegistry.register
class NUMATopology(base.ZunObject):
    # Version 1.0: Initial version
    VERSION = '1.0'

    fields = {
        'nodes': fields.ListOfObjectsField('NUMANode'),
        }

    @classmethod
    def _from_dict(cls, data_dict):
        return cls(nodes=[
            NUMANode._from_dict(node_dict)
            for node_dict in data_dict.get('nodes', [])])

    def _to_dict(self):
        return {
            'nodes': [n._to_dict() for n in self.nodes],
        }

    def to_list(self):
        return [n._to_dict() for n in self.nodes]
