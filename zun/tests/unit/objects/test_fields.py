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

from oslo_versionedobjects.tests import test_fields

from zun.objects import fields


class TestContainerStatus(test_fields.TestField):
    def setUp(self):
        super(TestContainerStatus, self).setUp()
        self.field = fields.ContainerStatus()
        self.coerce_good_values = [
            ('Error', 'Error'),
            ('Running', 'Running'),
            ('Stopped', 'Stopped'),
            ('Paused', 'Paused'),
            ('Unknown', 'Unknown'),
            ('Creating', 'Creating'),
            ('Created', 'Created'),
            ('Deleting', 'Deleting'),
        ]
        self.coerce_bad_values = ['bad_value']
        self.to_primitive_values = self.coerce_good_values[0:1]
        self.from_primitive_values = self.coerce_good_values[0:1]

    def test_stringify(self):
        self.assertEqual("'Error'",
                         self.field.stringify('Error'))

    def test_stringify_invalid(self):
        self.assertRaises(ValueError, self.field.stringify, 'bad_value')


class TestTaskState(test_fields.TestField):
    def setUp(self):
        super(TestTaskState, self).setUp()
        self.field = fields.TaskState()
        self.coerce_good_values = [
            ('image_pulling', 'image_pulling'),
            ('container_creating', 'container_creating'),
            ('sandbox_creating', 'sandbox_creating'),
        ]
        self.coerce_bad_values = ['bad_value']
        self.to_primitive_values = self.coerce_good_values[0:1]
        self.from_primitive_values = self.coerce_good_values[0:1]

    def test_stringify(self):
        self.assertEqual("'image_pulling'",
                         self.field.stringify('image_pulling'))

    def test_stringify_invalid(self):
        self.assertRaises(ValueError, self.field.stringify, 'bad_value')


class TestResourceClass(test_fields.TestField):
    def setUp(self):
        super(TestResourceClass, self).setUp()
        self.field = fields.ResourceClass()
        self.coerce_good_values = [
            ('VCPU', 'VCPU'),
            ('MEMORY_MB', 'MEMORY_MB'),
            ('DISK_GB', 'DISK_GB'),
            ('PCI_DEVICE', 'PCI_DEVICE'),
            ('SRIOV_NET_VF', 'SRIOV_NET_VF'),
            ('NUMA_SOCKET', 'NUMA_SOCKET'),
            ('NUMA_CORE', 'NUMA_CORE'),
            ('NUMA_THREAD', 'NUMA_THREAD'),
            ('NUMA_MEMORY_MB', 'NUMA_MEMORY_MB'),
            ('IPV4_ADDRESS', 'IPV4_ADDRESS'),
        ]
        self.coerce_bad_values = ['bad_value']
        self.to_primitive_values = self.coerce_good_values[0:1]
        self.from_primitive_values = self.coerce_good_values[0:1]

    def test_stringify(self):
        self.assertEqual("'VCPU'",
                         self.field.stringify('VCPU'))

    def test_stringify_invalid(self):
        self.assertRaises(ValueError, self.field.stringify, 'bad_value')
