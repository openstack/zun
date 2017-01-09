# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from tempest.lib import decorators

from zun.tests.tempest.api import clients
from zun.tests.tempest.api.common import datagen
from zun.tests.tempest import base


class TestContainer(base.BaseZunTest):

    @classmethod
    def get_client_manager(cls, credential_type=None, roles=None,
                           force_new=None):
        manager = super(TestContainer, cls).get_client_manager(
            credential_type=credential_type,
            roles=roles,
            force_new=force_new
        )
        return clients.Manager(manager.credentials)

    @classmethod
    def setup_clients(cls):
        super(TestContainer, cls).setup_clients()
        cls.container_client = cls.os.container_client
        cls.docker_client = clients.DockerClient()

    @classmethod
    def resource_setup(cls):
        super(TestContainer, cls).resource_setup()

    def tearDown(self):
        _, model = self.container_client.list_containers()
        for c in model.containers:
            self.container_client.delete_container(c['uuid'],
                                                   params={'force': True})

        super(TestContainer, self).tearDown()

    @decorators.idempotent_id('b8946b8c-57d5-4fdc-a09a-001d6b552725')
    def test_create_container(self):
        self._create_container()

    @decorators.idempotent_id('b3e307d4-844b-4a57-8c60-8fb3f57aea7c')
    def test_list_containers(self):
        _, container = self._create_container()
        resp, model = self.container_client.list_containers()
        self.assertEqual(200, resp.status)
        self.assertGreater(len(model.containers), 0)
        self.assertIn(
            container.uuid,
            list([c['uuid'] for c in model.containers]))

    @decorators.idempotent_id('0dd13c28-c5ff-4b9e-b73b-61185b410de4')
    def test_get_container(self):
        _, container = self._create_container()
        resp, model = self.container_client.get_container(container.uuid)
        self.assertEqual(200, resp.status)
        self.assertEqual(container.uuid, model.uuid)

    @decorators.idempotent_id('cef53a56-22b7-4808-b01c-06b2b7126115')
    def test_delete_container(self):
        _, container = self._create_container()
        self._delete_container(container.uuid)

    @decorators.idempotent_id('ef69c9e7-0ce0-4e14-b7ec-c1dc581a3927')
    def test_run_container(self):
        self._run_container()

    @decorators.idempotent_id('3fa024ef-aba1-48fe-9682-0d6b7854faa3')
    def test_start_stop_container(self):
        _, model = self._run_container()

        resp, _ = self.container_client.stop_container(model.uuid)
        self.assertEqual(202, resp.status)
        self.container_client.ensure_container_in_desired_state(
            model.uuid, 'Stopped')
        self.assertEqual('Stopped', self._get_container_state(model.uuid))

        resp, _ = self.container_client.start_container(model.uuid)
        self.assertEqual(202, resp.status)
        self.container_client.ensure_container_in_desired_state(
            model.uuid, 'Running')
        self.assertEqual('Running', self._get_container_state(model.uuid))

    @decorators.idempotent_id('b5f39756-8898-4e0e-a48b-dda0a06b66b6')
    def test_pause_unpause_container(self):
        _, model = self._run_container()

        resp, _ = self.container_client.pause_container(model.uuid)
        self.assertEqual(202, resp.status)
        self.container_client.ensure_container_in_desired_state(
            model.uuid, 'Paused')
        self.assertEqual('Paused', self._get_container_state(model.uuid))

        resp, _ = self.container_client.unpause_container(model.uuid)
        self.assertEqual(202, resp.status)
        self.container_client.ensure_container_in_desired_state(
            model.uuid, 'Running')
        self.assertEqual('Running', self._get_container_state(model.uuid))

    @decorators.idempotent_id('6179a588-3d48-4372-9599-f228411d1449')
    def test_kill_container(self):
        _, model = self._run_container()

        resp, _ = self.container_client.kill_container(model.uuid)
        self.assertEqual(202, resp.status)
        self.container_client.ensure_container_in_desired_state(
            model.uuid, 'Stopped')
        self.assertEqual('Stopped', self._get_container_state(model.uuid))

    @decorators.idempotent_id('c2e54321-0a70-4331-ba62-9dcaa75ac250')
    def test_reboot_container(self):
        _, model = self._run_container()
        container = self.docker_client.get_container(model.uuid)
        pid = container.get('State').get('Pid')

        resp, _ = self.container_client.reboot_container(model.uuid)
        self.assertEqual(202, resp.status)
        self.docker_client.ensure_container_pid_changed(model.uuid, pid)
        self.assertEqual('Running', self._get_container_state(model.uuid))
        # assert pid is changed
        container = self.docker_client.get_container(model.uuid)
        self.assertNotEqual(pid, container.get('State').get('Pid'))

    @decorators.idempotent_id('8a591ff8-6793-427f-82a6-e3921d8b4f81')
    def test_exec_container(self):
        _, model = self._run_container()
        resp, body = self.container_client.exec_container(model.uuid,
                                                          command='echo hello')
        self.assertEqual(200, resp.status)
        self.assertTrue('hello' in body)

    @decorators.idempotent_id('a912ca23-14e7-442f-ab15-e05aaa315204')
    def test_logs_container(self):
        _, model = self._run_container(
            command="/bin/sh -c 'echo hello;sleep 1000000'")
        resp, body = self.container_client.logs_container(model.uuid)
        self.assertEqual(200, resp.status)
        self.assertTrue('hello' in body)

    def _create_container(self, **kwargs):
        gen_model = datagen.container_data(**kwargs)
        resp, model = self.container_client.post_container(gen_model)
        self.assertEqual(202, resp.status)
        # Wait for container to finish creation
        self.container_client.ensure_container_in_desired_state(
            model.uuid, 'Stopped')

        # Assert the container is created
        resp, model = self.container_client.get_container(model.uuid)
        self.assertEqual(200, resp.status)
        self.assertEqual('Stopped', model.status)
        self.assertEqual('Stopped', self._get_container_state(model.uuid))
        return resp, model

    def _run_container(self, **kwargs):
        gen_model = datagen.container_data(**kwargs)
        resp, model = self.container_client.run_container(gen_model)
        self.assertEqual(202, resp.status)
        # Wait for container to started
        self.container_client.ensure_container_in_desired_state(
            model.uuid, 'Running')

        # Assert the container is started
        resp, model = self.container_client.get_container(model.uuid)
        self.assertEqual('Running', model.status)
        self.assertEqual('Running', self._get_container_state(model.uuid))
        return resp, model

    def _delete_container(self, container_id):
        resp, _ = self.container_client.delete_container(container_id)
        self.assertEqual(204, resp.status)
        container = self.docker_client.get_container(container_id)
        self.assertIsNone(container)

    def _get_container_state(self, container_id):
        container = self.docker_client.get_container(container_id)
        status = container.get('State')
        if status.get('Error') is True:
            return 'Error'
        elif status.get('Paused'):
            return 'Paused'
        elif status.get('Running'):
            return 'Running'
        else:
            return 'Stopped'
