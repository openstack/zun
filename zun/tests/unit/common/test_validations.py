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
from zun.common.validation import parameter_types
from zun.common.validation import validators
from zun.tests import base


CONTAINER_CREATE = {
    'type': 'object',
    'properties': {
        'name': parameter_types.container_name,
        'image': parameter_types.image_name,
        'command': parameter_types.command,
        'cpu': parameter_types.cpu,
        'memory': parameter_types.memory,
        'workdir': parameter_types.workdir,
        'hostname': parameter_types.hostname,
        'image_pull_policy': parameter_types.image_pull_policy,
        'ports': parameter_types.ports,
        'labels': parameter_types.labels,
        'environment': parameter_types.environment
    },
    'required': ['image'],
    'additionalProperties': False,
}


class TestSchemaValidations(base.BaseTestCase):
    def setUp(self):
        super(TestSchemaValidations, self).setUp()
        self.schema_validator = validators.SchemaValidator(CONTAINER_CREATE)

    def test_create_schema_with_all_valid_parameters(self):
        request_to_validate = {'name': 'test1', 'image': 'nginx',
                               'command': '/bin/sh', 'cpu': 1.0,
                               'memory': '5', 'workdir': '/workdir',
                               'hostname': 'container1',
                               'image_pull_policy': 'never',
                               'ports': ['123', '1', 1, '65535', 65535, 123],
                               'labels': {'abc': 12, 'bcd': 'xyz'},
                               'environment': {'xyz': 'pqr', 'pqr': 2}}
        self.schema_validator.validate(request_to_validate)

    def test_create_schema_with_all_parameters_none(self):
        request_to_validate = {'name': None, 'image': 'nginx',
                               'command': None, 'cpu': None,
                               'memory': None, 'workdir': None,
                               'hostname': None,
                               'image_pull_policy': None,
                               'ports': None,
                               'labels': None,
                               'environment': None}
        self.schema_validator.validate(request_to_validate)

    def test_create_schema_image_missing(self):
        request_to_validate = {'name': 'test1'}
        with self.assertRaisesRegexp(exception.SchemaValidationError,
                                     "'image' is a required property"):
            self.schema_validator.validate(request_to_validate)

    def test_create_schema_invalid_name(self):
        invalid_names = ['a@', 'a', "", '*' * 265, " ", "     ", "a b", 'ab@']
        for value in invalid_names:
            request_to_validate = {'name': value, 'image': 'nginx'}
            with self.assertRaisesRegexp(exception.SchemaValidationError,
                                         "Invalid input for field 'name'"):
                self.schema_validator.validate(request_to_validate)

    def test_create_schema_invalid_memory(self):
        invalid_memory = ['2KG', 2.2, '0', 0, '2', 2]
        for value in invalid_memory:
            request_to_validate = {'memory': value, 'image': 'nginx'}
            with self.assertRaisesRegexp(exception.SchemaValidationError,
                                         "Invalid input for field 'memory'"):
                self.schema_validator.validate(request_to_validate)

    def test_create_schema_invalid_image_pull_policy(self):
        request_to_validate = {'name': 'test1', 'image': 'nginx',
                               'image_pull_policy': 'xyz'}
        with self.assertRaisesRegexp(exception.SchemaValidationError,
                                     "Invalid input for field "
                                     "'image_pull_policy'"):
            self.schema_validator.validate(request_to_validate)

    def test_create_schema_valid_memory(self):
        valid_memory = [4, 5, '4', '5', None]
        for value in valid_memory:
            request_to_validate = {'memory': value, 'image': 'nginx'}
            self.schema_validator.validate(request_to_validate)

    def test_create_schema_invalid_ports(self):
        invalid_ports = [56, 0, 1, 65535, "", [0, '0', 65536, '65536',
                         "", 'x', "  "]]
        for value in invalid_ports:
            request_to_validate = {'image': 'nginx', 'ports': value}
            # TODO(pksingh): if value inside port array is not valid,
            # message like below is raised:
            # 'Invalid input for field '2'. Value: '65536'.
            # 65536 is greater than the maximum of 65535'
            # I think field '2' in message is not informative.
            with self.assertRaisesRegexp(exception.SchemaValidationError,
                                         "Invalid input for field"):
                self.schema_validator.validate(request_to_validate)

    def test_create_schema_cpu(self):
        valid_cpu = [4, 5, '4', '5', '0.5', '123.50', 0.5, 123.50, None]
        invalid_cpu = ['12a', 'abc', '0.a', 'a.90', "", "   ", " 0.9 "]
        for value in valid_cpu:
            request_to_validate = {'cpu': value, 'image': 'nginx'}
            self.schema_validator.validate(request_to_validate)
        for value in invalid_cpu:
            request_to_validate = {'cpu': value, 'image': 'nginx'}
            with self.assertRaisesRegexp(exception.SchemaValidationError,
                                         "Invalid input for field 'cpu'"):
                self.schema_validator.validate(request_to_validate)
