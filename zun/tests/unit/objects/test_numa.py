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

from zun.common import exception
from zun import objects
from zun.tests import base


class TestNUMA(base.BaseTestCase):
    def test_free_cpus_numa(self):
        obj = objects.NUMATopology(cells=[
            objects.NUMANode(
                id=0, cpuset=set([1, 2]),
                pinned_cpus=set([1])),
            objects.NUMANode(
                id=1, cpuset=set([3, 4]),
                pinned_cpus=set([]))
            ]
        )
        self.assertEqual(set([2]), obj.cells[0].free_cpus)
        self.assertEqual(set([3, 4]), obj.cells[1].free_cpus)

    def test_pinning_logic(self):
        numacell = objects.NUMANode(id=0, cpuset=set([1, 2, 3, 4]),
                                    pinned_cpus=set([1]))
        numacell.pin_cpus(set([2, 3]))
        self.assertEqual(set([4]), numacell.free_cpus)
        self.assertRaises(exception.CPUUnpinningUnknown,
                          numacell.unpin_cpus, set([1, 55]))
        self.assertRaises(exception.CPUPinningInvalid,
                          numacell.pin_cpus, set([1, 4]))
        self.assertRaises(exception.CPUUnpinningInvalid,
                          numacell.unpin_cpus, set([1, 4]))
        numacell.unpin_cpus(set([1, 2, 3]))
        self.assertEqual(set([1, 2, 3, 4]), numacell.free_cpus)
