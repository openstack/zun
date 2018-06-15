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

from zun.api.controllers.v1.schemas import parameter_types
from zun.api.validation import validators
from zun.common import exception
from zun.tests import base


CONTAINER_CREATE = {
    'type': 'object',
    'properties': {
        'name': parameter_types.container_name,
        'image': parameter_types.image_name,
        'command': parameter_types.command_list,
        'cpu': parameter_types.cpu,
        'memory': parameter_types.memory,
        'workdir': parameter_types.workdir,
        'image_pull_policy': parameter_types.image_pull_policy,
        'labels': parameter_types.labels,
        'environment': parameter_types.environment,
        'restart_policy': parameter_types.restart_policy,
        'image_driver': parameter_types.image_driver,
        'security_groups': parameter_types.security_groups,
        'runtime': parameter_types.runtime,
        'auto_heal': parameter_types.auto_heal
    },
    'required': ['image'],
    'additionalProperties': False,
}

CAPSULE_CREATE = {
    'type': 'object',
    'properties': {
        'template': parameter_types.capsule_template
    },
    'required': ['template'],
    'additionalProperties': False
}


class TestSchemaValidations(base.BaseTestCase):
    def setUp(self):
        super(TestSchemaValidations, self).setUp()
        self.schema_validator = validators.SchemaValidator(CONTAINER_CREATE)

    def test_create_schema_with_all_valid_parameters(self):
        request_to_validate = {'name': 'test1', 'image': 'nginx',
                               'command': ["/bin/sh"],
                               'cpu': 1.0,
                               'memory': '5', 'workdir': '/workdir',
                               'image_pull_policy': 'never',
                               'labels': {'abc': 12, 'bcd': 'xyz'},
                               'environment': {'xyz': 'pqr', 'pqr': '2'},
                               'restart_policy': {'Name': 'no',
                                                  'MaximumRetryCount': '0'},
                               'image_driver': 'docker',
                               'security_groups': ['abc'],
                               'runtime': 'runc',
                               'auto_heal': False}
        self.schema_validator.validate(request_to_validate)

    def test_create_schema_with_all_parameters_none(self):
        request_to_validate = {'name': None, 'image': 'nginx',
                               'command': None, 'cpu': None,
                               'memory': None, 'workdir': None,
                               'image_pull_policy': None,
                               'labels': None,
                               'environment': None,
                               'restart_policy': None,
                               'image_driver': None,
                               'security_groups': None,
                               'runtime': None,
                               'auto_heal': False
                               }
        self.schema_validator.validate(request_to_validate)

    def test_create_schema_image_missing(self):
        request_to_validate = {'name': 'test1'}
        with self.assertRaisesRegex(exception.SchemaValidationError,
                                    "'image' is a required property"):
            self.schema_validator.validate(request_to_validate)

    def test_create_schema_invalid_security_groups(self):
        invalid_security_groups = [[''], ['1' * 260], 'x']
        for value in invalid_security_groups:
            request_to_validate = {'security_groups': value, 'image': 'nginx'}
            with self.assertRaisesRegex(exception.SchemaValidationError,
                                        "Invalid input for field"):
                self.schema_validator.validate(request_to_validate)

    def test_create_schema_invalid_name(self):
        invalid_names = ['a@', 'a', "", '*' * 265, " ", "     ", "a b", 'ab@']
        for value in invalid_names:
            request_to_validate = {'name': value, 'image': 'nginx'}
            with self.assertRaisesRegex(exception.SchemaValidationError,
                                        "Invalid input for field 'name'"):
                self.schema_validator.validate(request_to_validate)

    def test_create_schema_invalid_memory(self):
        invalid_memory = ['2KG', 2.2, '0', 0, '2', 2]
        for value in invalid_memory:
            request_to_validate = {'memory': value, 'image': 'nginx'}
            with self.assertRaisesRegex(exception.SchemaValidationError,
                                        "Invalid input for field 'memory'"):
                self.schema_validator.validate(request_to_validate)

    def test_create_schema_invalid_image_pull_policy(self):
        request_to_validate = {'name': 'test1', 'image': 'nginx',
                               'image_pull_policy': 'xyz'}
        with self.assertRaisesRegex(exception.SchemaValidationError,
                                    "Invalid input for field "
                                    "'image_pull_policy'"):
            self.schema_validator.validate(request_to_validate)

    def test_create_schema_valid_memory(self):
        valid_memory = [4, 5, '4', '5', None]
        for value in valid_memory:
            request_to_validate = {'memory': value, 'image': 'nginx'}
            self.schema_validator.validate(request_to_validate)

    def test_create_schema_cpu(self):
        valid_cpu = [4, 5, '4', '5', '1', '12.5', 1, 12.5, None]
        invalid_cpu = ['12a', 'abc', '0.a', 'a.90', "", "   ", " 0.9 "]
        for value in valid_cpu:
            request_to_validate = {'cpu': value, 'image': 'nginx'}
            self.schema_validator.validate(request_to_validate)
        for value in invalid_cpu:
            request_to_validate = {'cpu': value, 'image': 'nginx'}
            with self.assertRaisesRegex(exception.SchemaValidationError,
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
            with self.assertRaisesRegex(exception.SchemaValidationError,
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
            with self.assertRaisesRegex(exception.SchemaValidationError,
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
        with self.assertRaisesRegex(exception.SchemaValidationError,
                                    "'Name' is a required property"):
            self.schema_validator.validate(request_to_validate)

    def test_create_schema_wrong_image_driver(self):
        request_to_validate = {'image_driver': 'xyz', 'image': 'nginx'}
        with self.assertRaisesRegex(exception.SchemaValidationError,
                                    "Invalid input for field"
                                    " 'image_driver'"):
            self.schema_validator.validate(request_to_validate)

    def test_create_schema_wrong_environment(self):
        request_to_validate = {'image': 'nginx',
                               'environment': {'xyz': 'pqr', 'pqr': None}}
        with self.assertRaisesRegex(exception.SchemaValidationError,
                                    "Invalid input for field"
                                    " 'pqr'"):
            self.schema_validator.validate(request_to_validate)

    def test_create_schema_wrong_runtime(self):
        request_to_validate = {'image': 'nginx',
                               'runtime': 123}
        with self.assertRaisesRegex(exception.SchemaValidationError,
                                    "Invalid input for field"
                                    " 'runtime'"):
            self.schema_validator.validate(request_to_validate)


class TestCapsuleSchemaValidations(base.BaseTestCase):
    def setUp(self):
        super(TestCapsuleSchemaValidations, self).setUp()
        self.schema_validator = validators.SchemaValidator(CAPSULE_CREATE)

    def test_create_schema_with_all_valid_parameters(self):
        request_to_validate = \
            {"template":
                {"kind": "capsule",
                 "capsuleVersion": "beta",
                 "metadata": {
                     "labels": {"app": "web"},
                     "name": "template"},

                 "spec": {
                     "restartPolicy": "Always",
                     "containers": [
                         {"workDir": "/root", "image": "ubuntu",
                          "volumeMounts": [{"readOnly": True,
                                            "mountPath": "/data1",
                                            "name": "volume1"}],
                          "command": ["/bin/bash"],
                          "env": {"ENV2": "/usr/bin"},
                          "imagePullPolicy": "ifnotpresent",
                          "ports": [{"containerPort": 80,
                                     "protocol": "TCP",
                                     "name": "nginx-port",
                                     "hostPort": 80}],
                          "resources": {"requests": {"cpu": 1,
                                                     "memory": 1024}}}],
                     "volumes": [
                         {"cinder": {"autoRemove": True, "size": 5},
                          "name": "volume1"},
                     ]}}}
        self.schema_validator.validate(request_to_validate)

    def test_create_schema_kind_missing(self):
        request_to_validate = \
            {"template":
                {"capsuleVersion": "beta",
                 "metadata": {
                     "labels": {"app": "web"},
                     "name": "template"},
                 "spec": {"containers": [{"image": "test"}]}
                 }}
        with self.assertRaisesRegex(exception.SchemaValidationError,
                                    "'kind' is a required property"):
            self.schema_validator.validate(request_to_validate)

    def test_create_schema_metadata_missing(self):
        request_to_validate = \
            {"template":
                {"capsuleVersion": "beta",
                 "kind": "capsule",
                 "spec": {"containers": [{"image": "test"}]}
                 }}
        with self.assertRaisesRegex(exception.SchemaValidationError,
                                    "'metadata' is a required property"):
            self.schema_validator.validate(request_to_validate)

    def test_create_schema_spec_missing(self):
        request_to_validate = \
            {"template":
                {"capsuleVersion": "beta",
                 "kind": "capsule",
                 "metadata": {
                     "labels": {"app": "web"},
                     "name": "template"},
                 }}
        with self.assertRaisesRegex(exception.SchemaValidationError,
                                    "'spec' is a required property"):
            self.schema_validator.validate(request_to_validate)

    def test_create_schema_with_all_essential_params(self):
        request_to_validate = \
            {"template":
                {"kind": "capsule",
                 "capsuleVersion": "beta",
                 "metadata": {
                     "labels": {},
                     "name": "test-essential"},
                 "spec": {
                     "containers": [
                         {"image": "test"}]
                 }}}
        self.schema_validator.validate(request_to_validate)

    def test_create_schema_capsule_restart_policy(self):
        valid_restart_policy = ["Always", "OnFailure", "Never"]
        invalid_restart_policy = ["always", "4", "onfailure", "never"]
        for restart_policy in valid_restart_policy:
            request_to_validate = \
                {"template":
                    {"capsuleVersion": "beta",
                     "kind": "capsule",
                     "metadata": {
                         "labels": {"app": "web"},
                         "name": "template"},
                     "spec": {"containers": [{"image": "test"}],
                              "restartPolicy": restart_policy}
                     }}
            self.schema_validator.validate(request_to_validate)
        for restart_policy in invalid_restart_policy:
            request_to_validate = \
                {"template":
                    {"capsuleVersion": "beta",
                     "kind": "capsule",
                     "metadata": {
                         "labels": {"app": "web"},
                         "name": "template"},
                     "spec": {"restartPolicy": restart_policy,
                              "containers": [{"image": "test"}]}
                     }}
            with self.assertRaisesRegex(exception.SchemaValidationError,
                                        "Invalid input for field "
                                        "'restartPolicy'."):
                self.schema_validator.validate(request_to_validate)

    def test_create_schema_capsule_existed_volume_mounts(self):
        request_to_validate = {
            "template": {
                "kind": "capsule",
                "metadata": {},
                "spec": {
                    "containers": [
                        {"image": "test",
                         "volumeMounts": [{
                             "name": "volume1",
                             "mountPath": "/data"}]
                         }],
                    "volumes": [
                        {"name": "volume1",
                         "cinder": {
                             "volumeID":
                                 "d2a28af0-e243-4525-adf9-2d091466e43d"}
                         }
                    ]
                }
            }
        }
        self.schema_validator.validate(request_to_validate)

    def test_create_schema_capsule_new_volume_mounts(self):
        request_to_validate = {
            "template": {
                "kind": "capsule",
                "metadata": {},
                "spec": {
                    "containers": [
                        {"image": "test",
                         "volumeMounts": [{
                             "name": "volume1",
                             "mountPath": "/data"}]
                         }],
                    "volumes": [
                        {"name": "volume1",
                         "cinder": {
                             "size": 5,
                             "autoRemove": True}
                         }
                    ]
                }
            }
        }
        self.schema_validator.validate(request_to_validate)

    def test_create_schema_capsule_volume_no_cinder(self):
        request_to_validate = {
            "template": {
                "kind": "capsule",
                "metadata": {},
                "spec": {
                    "containers": [
                        {"image": "test"}],
                    "volumes": [
                        {"name": "volume1",
                         "no-cinder-driver": {
                             "size": 5,
                             "autoRemove": True}
                         }
                    ]
                }
            }
        }
        with self.assertRaisesRegex(exception.SchemaValidationError,
                                    "'cinder' is a required property"):
            self.schema_validator.validate(request_to_validate)

    def test_create_schema_capsule_volume_no_name(self):
        request_to_validate = {
            "template": {
                "kind": "capsule",
                "metadata": {},
                "spec": {
                    "containers": [
                        {"image": "test"}],
                    "volumes": [
                        {
                            "cinder": {
                                "size": 5,
                                "autoRemove": True}
                        }
                    ]
                }
            }
        }
        with self.assertRaisesRegex(exception.SchemaValidationError,
                                    "'name' is a required property"):
            self.schema_validator.validate(request_to_validate)
