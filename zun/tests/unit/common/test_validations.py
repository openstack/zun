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
        'image_pull_policy': parameter_types.image_pull_policy,
        'labels': parameter_types.labels,
        'environment': parameter_types.environment,
        'restart_policy': parameter_types.restart_policy
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
                               'image_pull_policy': 'never',
                               'labels': {'abc': 12, 'bcd': 'xyz'},
                               'environment': {'xyz': 'pqr', 'pqr': 2},
                               'restart_policy': {'Name': 'no',
                                                  'MaximumRetryCount': '0'}}
        self.schema_validator.validate(request_to_validate)

    def test_create_schema_with_all_parameters_none(self):
        request_to_validate = {'name': None, 'image': 'nginx',
                               'command': None, 'cpu': None,
                               'memory': None, 'workdir': None,
                               'image_pull_policy': None,
                               'labels': None,
                               'environment': None,
                               'restart_policy': None
                               }
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

    def test_create_schema_restart_policy_name(self):
        valid_name = ['no', 'on-failure', 'unless-stopped', 'always']
        invalid_name = ['12a', 'abc', '5', 'dd', "", "   "]
        for value in valid_name:
            restart_policy = {'Name': value, 'MaximumRetryCount': '0'}
            request_to_validate = {'name': 'test1', 'image': 'nginx',
                                   'restart_policy': restart_policy}
            self.schema_validator.validate(request_to_validate)
        for value in invalid_name:
            restart_policy = {'Name': value, 'MaximumRetryCount': '0'}
            request_to_validate = {'name': 'test1', 'image': 'nginx',
                                   'restart_policy': restart_policy}
            with self.assertRaisesRegexp(exception.SchemaValidationError,
                                         "Invalid input for field 'Name'"):
                self.schema_validator.validate(request_to_validate)

    def test_create_schema_restart_policy_maxiumretrycount(self):
        valid_retry = ['0', '1', 15, '100']
        invalid_retry = ['12a', 'abc', '-1', "", "   "]
        for value in valid_retry:
            restart_policy = {'Name': 'no', 'MaximumRetryCount': value}
            request_to_validate = {'name': 'test1', 'image': 'nginx',
                                   'restart_policy': restart_policy}
            self.schema_validator.validate(request_to_validate)
        for value in invalid_retry:
            restart_policy = {'Name': 'no', 'MaximumRetryCount': value}
            request_to_validate = {'name': 'test1', 'image': 'nginx',
                                   'restart_policy': restart_policy}
            with self.assertRaisesRegexp(exception.SchemaValidationError,
                                         "Invalid input for field "
                                         "'MaximumRetryCount'"):
                self.schema_validator.validate(request_to_validate)

    def test_create_schema_restart_policy(self):
        restart_policy = {'Name': 'no'}
        request_to_validate = {'name': 'test1', 'image': 'nginx',
                               'restart_policy': restart_policy}
        self.schema_validator.validate(request_to_validate)
        restart_policy = {'MaximumRetryCount': 5}
        request_to_validate = {'name': 'test1', 'image': 'nginx',
                               'restart_policy': restart_policy}
        with self.assertRaisesRegexp(exception.SchemaValidationError,
                                     "'Name' is a required property"):
            self.schema_validator.validate(request_to_validate)
