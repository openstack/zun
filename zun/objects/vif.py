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

from os_vif.objects import vif as obj_osvif
from oslo_versionedobjects import fields as obj_fields

from zun.common import consts
from zun.objects import base
from zun.objects import fields as zun_fields


@base.ZunObjectRegistry.register
class VIFState(base.ZunObject):
    # Version 1.0: Initial version
    VERSION = '1.0'

    # FIXME(dulek): I know it's an ugly hack, but turns out you cannot
    #               serialize-deserialize objects containing objects from
    #               different namespaces, so we need 'os_vif' namespace here.
    OBJ_PROJECT_NAMESPACE = 'os_vif'
    OBJ_SERIAL_NAMESPACE = 'versioned_object'

    fields = {
        'default_vif': obj_fields.ObjectField(obj_osvif.VIFBase.__name__,
                                              subclasses=True, nullable=False),
        'additional_vifs': zun_fields.DictOfVIFsField(default={}),
    }

    @property
    def vifs(self):
        d = {
            consts.DEFAULT_IFNAME: self.default_vif,
        }
        if self.obj_attr_is_set('additional_vifs'):
            d.update(self.additional_vifs)
        return d
