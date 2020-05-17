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

import docker
from tempest.lib import decorators

from zun.tests.fullstack import base
from zun.tests.fullstack import utils


class TestContainer(base.BaseFullStackTestCase):

    def setUp(self):
        super(TestContainer, self).setUp()
        self.containers = []

    def tearDown(self):
        containers = self.zun.containers.list()
        for c in containers:
            if c.uuid in self.containers:
                self.zun.containers.delete(c.uuid, stop=True)
                self.ensure_container_deleted(c.uuid)

        super(TestContainer, self).tearDown()

    @decorators.idempotent_id('039fc590-7711-4b87-86bf-fe9048c3feb9')
    def test_run_container(self):
        self._run_container()

    def _run_container(self, **kwargs):
        if not kwargs.get('image'):
            kwargs['image'] = 'cirros:latest'
            kwargs['command'] = ['sleep', '100000']

        kwargs.setdefault('cpu', 0.1)
        kwargs.setdefault('memory', 128)

        container = self.zun.containers.run(**kwargs)
        self.containers.append(container.uuid)
        # Wait for container to started
        self.ensure_container_in_desired_state(container.uuid, 'Running')

        # Assert the container is started
        container = self.zun.containers.get(container.uuid)
        self.assertEqual('Running', container.status)
        self.assertEqual('Running', self._get_state_in_docker(container))
        return container

    def _create_container(self, **kwargs):
        if not kwargs.get('image'):
            kwargs['image'] = 'cirros:latest'
            kwargs['command'] = ['sleep', '100000']

        kwargs.setdefault('cpu', 0.1)
        kwargs.setdefault('memory', 128)

        container = self.zun.containers.create(**kwargs)
        self.containers.append(container.uuid)
        # Wait for container to finish creation
        self.ensure_container_in_desired_state(container.uuid, 'Created')

        # Assert the container is created
        container = self.zun.containers.get(container.uuid)
        self.assertEqual('Created', container.status)
        self.assertEqual('Created', self._get_state_in_docker(container))
        return container

    @decorators.idempotent_id('8c6f0844-1a5c-4bf4-81d5-38dccb2c2b25')
    def test_delete_container(self):
        container = self._create_container()
        self.zun.containers.delete(container.uuid)
        self.ensure_container_deleted(container.uuid)
        self.assertRaises(docker.errors.NotFound,
                          self._get_container_in_docker, container)

    @decorators.idempotent_id('6f7a4d0f-273a-4321-ba14-246c6ea387a1')
    def test_run_container_with_environment(self):
        container = self._run_container(
            environment={'key1': 'env1', 'key2': 'env2'})

        docker_container = self._get_container_in_docker(container)
        env = docker_container['Config']['Env']
        self.assertTrue('key1=env1' in env)
        self.assertTrue('key2=env2' in env)

    @decorators.idempotent_id('25e19899-d450-4d6b-9dbd-160f9c557877')
    def test_run_container_with_labels(self):
        container = self._run_container(
            labels={'key1': 'label1', 'key2': 'label2'})

        docker_container = self._get_container_in_docker(container)
        labels = docker_container['Config']['Labels']
        self.assertEqual({'key1': 'label1', 'key2': 'label2'}, labels)

    @decorators.idempotent_id('8a920b08-32df-448e-ab53-b640611ac769')
    def test_run_container_with_restart_policy(self):
        container = self._run_container(restart_policy={
            'Name': 'on-failure', 'MaximumRetryCount': 2})

        docker_container = self._get_container_in_docker(container)
        policy = docker_container['HostConfig']['RestartPolicy']
        self.assertEqual('on-failure', policy['Name'])
        self.assertEqual(2, policy['MaximumRetryCount'])

    @decorators.idempotent_id('6b3229af-c8c8-4a11-8b22-981e2ff63b51')
    def test_run_container_with_interactive(self):
        container = self._run_container(interactive=True)

        docker_container = self._get_container_in_docker(container)
        tty = docker_container['Config']['Tty']
        stdin_open = docker_container['Config']['OpenStdin']
        self.assertIs(True, tty)
        self.assertIs(True, stdin_open)

    @decorators.idempotent_id('98c6d770-ccd5-48b8-895b-adb00ed9ce53')
    def test_run_container_with_volume(self):
        container = self._run_container(
            mounts=[{'size': '1', 'destination': '/data', 'type': 'volume'}])

        docker_container = self._get_container_in_docker(container)
        mounts = docker_container['Mounts']
        self.assertEqual(1, len(mounts))
        self.assertEqual('/data', mounts[0]['Destination'])

    @decorators.idempotent_id('1258e2a2-f7bb-4e66-a4d9-6deb2358e2e2')
    def test_run_container_with_multiple_volumes(self):
        container = self._run_container(
            mounts=[{'size': '1', 'destination': '/data', 'type': 'volume'},
                    {'size': '1', 'destination': '/data2', 'type': 'volume'}])

        docker_container = self._get_container_in_docker(container)
        mounts = docker_container['Mounts']
        self.assertEqual(2, len(mounts))
        self.assertTrue(mounts[0]['Destination'] in ['/data', '/data2'])
        self.assertTrue(mounts[1]['Destination'] in ['/data', '/data2'])

    @decorators.idempotent_id('f189624c-c9b8-4181-9485-2b5cacb633bc')
    def test_reboot_container(self):
        container = self._run_container()
        docker_container = self._get_container_in_docker(container)
        pid = docker_container['State']['Pid']

        self.zun.containers.restart(container.uuid, timeout=10)
        self._ensure_container_pid_changed(container, pid)
        self.assertEqual('Running', self._get_state_in_docker(container))
        # assert pid is changed
        docker_container = self._get_container_in_docker(container)
        self.assertNotEqual(pid, docker_container['State']['Pid'])

    def _ensure_container_pid_changed(self, container, pid):
        def is_pid_changed():
            docker_container = self._get_container_in_docker(container)
            new_pid = docker_container['State']['Pid']
            if pid != new_pid:
                return True
            else:
                return False
        utils.wait_for_condition(is_pid_changed)

    @decorators.idempotent_id('44e28cdc-6b33-4394-b7cb-3b2f36a2839a')
    def test_update_container(self):
        container = self._run_container(cpu=0.1, memory=100)
        self.assertEqual('100', container.memory)
        self.assertEqual(0.1, container.cpu)
        docker_container = self._get_container_in_docker(container)
        self._assert_resource_constraints(docker_container, cpu=0.1,
                                          memory=100)

        container = self.zun.containers.update(container.uuid, cpu=0.2,
                                               memory=200)
        self.assertEqual('200', container.memory)
        self.assertEqual(0.2, container.cpu)
        docker_container = self._get_container_in_docker(container)
        self._assert_resource_constraints(docker_container, cpu=0.2,
                                          memory=200)

    def _assert_resource_constraints(self, docker_container, cpu, memory):
        cpu_shares = docker_container['HostConfig']['CpuShares']
        self.assertEqual(int(cpu * 1024), cpu_shares)
        docker_memory = docker_container['HostConfig']['Memory']
        self.assertEqual(memory * 1024 * 1024, docker_memory)
