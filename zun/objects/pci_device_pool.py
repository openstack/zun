# Copyright (c) 2017 Hewlett-Packard Development Company, L.P.
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

import copy

from oslo_serialization import jsonutils
from oslo_versionedobjects import fields
import six

from zun.objects import base


@base.ZunObjectRegistry.register
class PciDevicePool(base.ZunObject):
    # Version 1.0: Initial version
    VERSION = '1.0'

    fields = {
        'product_id': fields.StringField(),
        'vendor_id': fields.StringField(),
        'numa_node': fields.IntegerField(nullable=True),
        'tags': fields.DictOfNullableStringsField(),
        'count': fields.IntegerField(),
        }

    # NOTE(pmurray): before this object existed the pci device pool data was
    # stored as a dict. For backward compatibility we need to be able to read
    # it in from a dict
    @classmethod
    def from_dict(cls, value):
        pool_dict = copy.copy(value)
        pool = cls()
        pool.vendor_id = pool_dict.pop("vendor_id")
        pool.product_id = pool_dict.pop("product_id")
        pool.numa_node = pool_dict.pop("numa_node", None)
        pool.count = pool_dict.pop("count")
        pool.tags = pool_dict
        return pool

    # NOTE(sbauza): Before using objects, pci stats was a list of
    # dictionaries not having tags. For compatibility with other modules, let's
    # create a reversible method
    def to_dict(self):
        pci_pool = base.obj_to_primitive(self)
        tags = pci_pool.pop('tags', {})
        for k, v in tags.items():
            pci_pool[k] = v
        return pci_pool


@base.ZunObjectRegistry.register
class PciDevicePoolList(base.ObjectListBase, base.ZunObject):
    # Version 1.0: Initial version
    VERSION = '1.0'
    fields = {'objects': fields.ListOfObjectsField('PciDevicePool'), }


def from_pci_stats(pci_stats):
    """Create and return a PciDevicePoolList from the data stored in the db,

    which can be either the serialized object, or, prior to the creation of the
    device pool objects, a simple dict or a list of such dicts.
    """
    pools = []
    if isinstance(pci_stats, six.string_types):
        try:
            pci_stats = jsonutils.loads(pci_stats)
        except (ValueError, TypeError):
            pci_stats = None
    if pci_stats:
        # Check for object-ness, or old-style storage format.
        if 'zun_object.namespace' in pci_stats:
            return PciDevicePoolList.obj_from_primitive(pci_stats)
        else:
            # This can be either a dict or a list of dicts
            if isinstance(pci_stats, list):
                pools = [PciDevicePool.from_dict(stat)
                         for stat in pci_stats]
            else:
                pools = [PciDevicePool.from_dict(pci_stats)]
    return PciDevicePoolList(objects=pools)
