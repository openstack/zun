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

from oslo_utils import encodeutils
from tempest.lib import decorators

from zun.tests.tempest.api import clients
from zun.tests.tempest.api.common import datagen
from zun.tests.tempest import base
from zun.tests.tempest import utils


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
        cls.container_client = cls.os_primary.container_client
        cls.docker_client = clients.DockerClient()
        cls.images_client = cls.os_primary.images_client
        cls.ports_client = cls.os_primary.ports_client
        cls.sgs_client = cls.os_primary.sgs_client

    @classmethod
    def resource_setup(cls):
        super(TestContainer, cls).resource_setup()

    def setUp(self):
        super(TestContainer, self).setUp()
        self.containers = []

    def tearDown(self):
        hosts = []
        _, model = self.container_client.list_containers()
        for c in model.containers:
            if c['uuid'] in self.containers:
                if c['host'] not in hosts:
                    hosts.append(c['host'])
                self.container_client.delete_container(c['uuid'],
                                                       params={'force': True})

        # cleanup the network resources
        project_id = self.container_client.tenant_id
        for host in hosts:
            # NOTE(kiennt): Default docker remote url
            #               Remove networks in all hosts
            docker_base_url = self._get_docker_url(host)
            networks = self.docker_client.list_networks(project_id,
                                                        docker_base_url)
            for network in networks:
                self.docker_client.remove_network(network['Id'],
                                                  docker_base_url)

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
        self._delete_container(container.uuid, container.host)

    @decorators.idempotent_id('ef69c9e7-0ce0-4e14-b7ec-c1dc581a3927')
    def test_run_container(self):
        self._run_container()

    @decorators.idempotent_id('a2152d78-b6a6-4f47-8767-d83d29c6fb19')
    def test_run_container_with_minimal_params(self):
        gen_model = datagen.container_data({'image': 'nginx'})
        self._run_container(gen_model=gen_model)

    @decorators.idempotent_id('c32f93e3-da88-4c13-be38-25d2e662a28e')
    def test_run_container_with_image_driver_glance(self):
        image = None
        try:
            docker_base_url = self._get_docker_url()
            self.docker_client.pull_image(
                'cirros', docker_auth_url=docker_base_url)
            image_data = self.docker_client.get_image(
                'cirros', docker_base_url)
            image = self.images_client.create_image(
                name='cirros', disk_format='raw', container_format='docker')
            self.images_client.store_image_file(image['id'], image_data)
            # delete the local image that was previously pulled down
            self.docker_client.delete_image('cirros', docker_base_url)

            _, model = self._run_container(
                image='cirros', image_driver='glance')
        finally:
            if image:
                try:
                    self.images_client.delete_image(image['id'])
                except Exception:
                    pass

    @decorators.idempotent_id('b70bedbc-5ba2-400c-8f5f-0cf05ca17151')
    def test_run_container_with_environment(self):
        _, model = self._run_container(environment={
            'key1': 'env1', 'key2': 'env2'})

        container = self.docker_client.get_container(
            model.uuid,
            self._get_docker_url(model.host))
        env = container.get('Config').get('Env')
        self.assertTrue('key1=env1', env)
        self.assertTrue('key2=env2', env)

    @decorators.idempotent_id('0e59d549-58ff-440f-8704-10e223c31cbc')
    def test_run_container_with_labels(self):
        _, model = self._run_container(labels={
            'key1': 'label1', 'key2': 'label2'})

        container = self.docker_client.get_container(
            model.uuid,
            self._get_docker_url(model.host))
        labels = container.get('Config').get('Labels')
        self.assertTrue('key1=label1', labels)
        self.assertTrue('key2=label2', labels)

    @decorators.idempotent_id('9fc7fec0-e1a9-4f65-a5a6-dba425c1607c')
    def test_run_container_with_restart_policy(self):
        _, model = self._run_container(restart_policy={
            'Name': 'on-failure', 'MaximumRetryCount': 2})

        container = self.docker_client.get_container(
            model.uuid,
            self._get_docker_url(model.host))
        policy = container.get('HostConfig').get('RestartPolicy')
        self.assertEqual('on-failure', policy['Name'])
        self.assertTrue(2, policy['MaximumRetryCount'])

    @decorators.idempotent_id('58585a4f-cdce-4dbd-9741-4416d1098f94')
    def test_run_container_with_interactive(self):
        _, model = self._run_container(interactive=True)

        container = self.docker_client.get_container(
            model.uuid,
            self._get_docker_url(model.host))
        tty = container.get('Config').get('Tty')
        stdin_open = container.get('Config').get('OpenStdin')
        self.assertIs(True, tty)
        self.assertIs(True, stdin_open)

    @decorators.idempotent_id('f181eeda-a9d1-4b2e-9746-d6634ca81e2f')
    def test_run_container_without_security_groups(self):
        gen_model = datagen.container_data()
        delattr(gen_model, 'security_groups')
        _, model = self._run_container(gen_model=gen_model)
        sgs = self._get_all_security_groups(model)
        self.assertEqual(1, len(sgs))
        self.assertEqual('default', sgs[0])

    @decorators.idempotent_id('f181eeda-a9d1-4b2e-9746-d6634ca81e2f')
    def test_run_container_with_security_groups(self):
        sg_name = 'test_sg'
        self.sgs_client.create_security_group(name=sg_name)
        _, model = self._run_container(security_groups=[sg_name])
        sgs = self._get_all_security_groups(model)
        self.assertEqual(1, len(sgs))
        self.assertEqual(sg_name, sgs[0])

    @decorators.idempotent_id('c3f02fa0-fdfb-49fc-95e2-6e4dc982f9be')
    def test_commit_container(self):
        """Test container snapshot

        This test does the following:
        1. Create a container
        2. Create and write to a file inside the container
        3. Commit the container and upload the snapshot to Glance
        4. Create another container from the snapshot image
        5. Verify the pre-created file is there
        """
        # This command creates a file inside the container
        command = "/bin/sh -c 'echo hello > testfile;sleep 1000000'"
        _, model = self._run_container(command=command)

        try:
            resp, _ = self.container_client.commit_container(
                model.uuid, params={'repository': 'myrepo'})
            self.assertEqual(202, resp.status)
            self._ensure_image_active('myrepo')

            # This command outputs the content of pre-created file
            command = "/bin/sh -c 'cat testfile;sleep 1000000'"
            _, model = self._run_container(
                image="myrepo", image_driver="glance", command=command)
            resp, body = self.container_client.logs_container(model.uuid)
            self.assertEqual(200, resp.status)
            self.assertTrue('hello' in encodeutils.safe_decode(body))
        finally:
            try:
                response = self.images_client.list_images()
                for image in response['images']:
                    if (image['name'] == 'myrepo' and
                            image['container_format'] == 'docker'):
                        self.images_client.delete_image(image['id'])
            except Exception:
                pass

    def _ensure_image_active(self, image_name):
        def is_image_in_desired_state():
            response = self.images_client.list_images()
            for image in response['images']:
                if (image['name'] == image_name and
                        image['container_format'] == 'docker' and
                        image['status'] == 'active'):
                    return True

            return False

        utils.wait_for_condition(is_image_in_desired_state)

    @decorators.idempotent_id('3fa024ef-aba1-48fe-9682-0d6b7854faa3')
    def test_start_stop_container(self):
        _, model = self._run_container()

        resp, _ = self.container_client.stop_container(model.uuid)
        self.assertEqual(202, resp.status)
        self.container_client.ensure_container_in_desired_state(
            model.uuid, 'Stopped')
        self.assertEqual('Stopped',
                         self._get_container_state(model.uuid, model.host))

        resp, _ = self.container_client.start_container(model.uuid)
        self.assertEqual(202, resp.status)
        self.container_client.ensure_container_in_desired_state(
            model.uuid, 'Running')
        self.assertEqual('Running',
                         self._get_container_state(model.uuid, model.host))

    @decorators.idempotent_id('b5f39756-8898-4e0e-a48b-dda0a06b66b6')
    def test_pause_unpause_container(self):
        _, model = self._run_container()

        resp, _ = self.container_client.pause_container(model.uuid)
        self.assertEqual(202, resp.status)
        self.container_client.ensure_container_in_desired_state(
            model.uuid, 'Paused')
        self.assertEqual('Paused',
                         self._get_container_state(model.uuid, model.host))

        resp, _ = self.container_client.unpause_container(model.uuid)
        self.assertEqual(202, resp.status)
        self.container_client.ensure_container_in_desired_state(
            model.uuid, 'Running')
        self.assertEqual('Running',
                         self._get_container_state(model.uuid, model.host))

    @decorators.idempotent_id('6179a588-3d48-4372-9599-f228411d1449')
    def test_kill_container(self):
        _, model = self._run_container()

        resp, _ = self.container_client.kill_container(model.uuid)
        self.assertEqual(202, resp.status)
        self.container_client.ensure_container_in_desired_state(
            model.uuid, 'Stopped')
        self.assertEqual('Stopped',
                         self._get_container_state(model.uuid, model.host))

    @decorators.idempotent_id('c2e54321-0a70-4331-ba62-9dcaa75ac250')
    def test_reboot_container(self):
        _, model = self._run_container()
        docker_base_url = self._get_docker_url(model.host)
        container = self.docker_client.get_container(model.uuid,
                                                     docker_base_url)
        pid = container.get('State').get('Pid')

        resp, _ = self.container_client.reboot_container(model.uuid)
        self.assertEqual(202, resp.status)
        self.docker_client.ensure_container_pid_changed(model.uuid, pid,
                                                        docker_base_url)
        self.assertEqual('Running',
                         self._get_container_state(model.uuid, model.host))
        # assert pid is changed
        container = self.docker_client.get_container(model.uuid,
                                                     docker_base_url)
        self.assertNotEqual(pid, container.get('State').get('Pid'))

    @decorators.idempotent_id('8a591ff8-6793-427f-82a6-e3921d8b4f81')
    def test_exec_container(self):
        _, model = self._run_container()
        resp, body = self.container_client.exec_container(model.uuid,
                                                          command='echo hello')
        self.assertEqual(200, resp.status)
        self.assertTrue('hello' in encodeutils.safe_decode(body))

    @decorators.idempotent_id('a912ca23-14e7-442f-ab15-e05aaa315204')
    def test_logs_container(self):
        _, model = self._run_container(
            command="/bin/sh -c 'echo hello;sleep 1000000'")
        resp, body = self.container_client.logs_container(model.uuid)
        self.assertEqual(200, resp.status)
        self.assertTrue('hello' in encodeutils.safe_decode(body))

    @decorators.idempotent_id('d383f359-3ebd-40ef-9dc5-d36922790230')
    def test_update_container(self):
        _, model = self._run_container(cpu=0.1, memory=100)
        self.assertEqual('100M', model.memory)
        self.assertEqual(0.1, model.cpu)
        docker_base_url = self._get_docker_url(model.host)
        container = self.docker_client.get_container(model.uuid,
                                                     docker_base_url)
        self._assert_resource_constraints(container, cpu=0.1, memory=100)

        gen_model = datagen.container_patch_data(cpu=0.2, memory=200)
        resp, model = self.container_client.update_container(model.uuid,
                                                             gen_model)
        self.assertEqual(200, resp.status)
        self.assertEqual('200M', model.memory)
        self.assertEqual(0.2, model.cpu)
        container = self.docker_client.get_container(model.uuid,
                                                     docker_base_url)
        self._assert_resource_constraints(container, cpu=0.2, memory=200)

    @decorators.idempotent_id('b218bea7-f19b-499f-9819-c7021ffc59f4')
    def test_rename_container(self):
        _, model = self._run_container(name='container1')
        self.assertEqual('container1', model.name)
        gen_model = datagen.container_rename_data(name='container2')
        resp, model = self.container_client.rename_container(model.uuid,
                                                             gen_model)
        self.assertEqual(200, resp.status)
        self.assertEqual('container2', model.name)

    @decorators.idempotent_id('142b7716-0b21-41ed-b47d-a42fba75636b')
    def test_top_container(self):
        _, model = self._run_container(
            command="/bin/sh -c 'sleep 1000000'")
        resp, body = self.container_client.top_container(model.uuid)
        self.assertEqual(200, resp.status)
        self.assertTrue('sleep 1000000' in encodeutils.safe_decode(body))

    @decorators.idempotent_id('09638306-b501-4803-aafa-7e8025632cef')
    def test_stats_container(self):
        _, model = self._run_container()
        resp, body = self.container_client.stats_container(model.uuid)
        self.assertEqual(200, resp.status)
        self.assertTrue('NET I/O(B)' in encodeutils.safe_decode(body))
        self.assertTrue('CONTAINER' in encodeutils.safe_decode(body))
        self.assertTrue('MEM LIMIT(MiB)' in encodeutils.safe_decode(body))
        self.assertTrue('CPU %' in encodeutils.safe_decode(body))
        self.assertTrue('MEM USAGE(MiB)' in encodeutils.safe_decode(body))
        self.assertTrue('MEM %' in encodeutils.safe_decode(body))
        self.assertTrue('BLOCK I/O(B)' in encodeutils.safe_decode(body))

    @decorators.idempotent_id('b3b9cf17-82ad-4c1b-a4af-8210a778a33e')
    def test_add_sg_to_container(self):
        _, model = self._run_container()
        sgs = self._get_all_security_groups(model)
        self.assertEqual(1, len(sgs))
        self.assertEqual('default', sgs[0])

        sg_name = 'test_add_sg'
        self.sgs_client.create_security_group(name=sg_name)
        gen_model = datagen.container_add_sg_data(name=sg_name)
        resp, body = self.container_client.add_security_group(
            model.uuid, gen_model)
        self.assertEqual(202, resp.status)

        def assert_security_group_is_added():
            sgs = self._get_all_security_groups(model)
            if len(sgs) == 2:
                self.assertTrue('default' in sgs)
                self.assertTrue(sg_name in sgs)
                return True
            else:
                return False

        utils.wait_for_condition(assert_security_group_is_added)

    def _assert_resource_constraints(self, container, cpu=None, memory=None):
        if cpu is not None:
            cpu_quota = container.get('HostConfig').get('CpuQuota')
            self.assertEqual(int(cpu * 100000), cpu_quota)
            cpu_period = container.get('HostConfig').get('CpuPeriod')
            self.assertEqual(100000, cpu_period)
        if memory is not None:
            docker_memory = container.get('HostConfig').get('Memory')
            self.assertEqual(memory * 1024 * 1024, docker_memory)

    def _create_container(self, **kwargs):
        gen_model = datagen.container_data(**kwargs)
        resp, model = self.container_client.post_container(gen_model)
        self.containers.append(model.uuid)
        self.assertEqual(202, resp.status)
        # Wait for container to finish creation
        self.container_client.ensure_container_in_desired_state(
            model.uuid, 'Created')

        # Assert the container is created
        resp, model = self.container_client.get_container(model.uuid)
        self.assertEqual(200, resp.status)
        self.assertEqual('Created', model.status)
        self.assertEqual('Created', self._get_container_state(model.uuid,
                                                              model.host))
        return resp, model

    def _run_container(self, gen_model=None, **kwargs):
        if gen_model is None:
            gen_model = datagen.container_data(**kwargs)
        resp, model = self.container_client.run_container(gen_model)
        self.containers.append(model.uuid)
        self.assertEqual(202, resp.status)
        # Wait for container to started
        self.container_client.ensure_container_in_desired_state(
            model.uuid, 'Running')

        # Assert the container is started
        resp, model = self.container_client.get_container(model.uuid)
        self.assertEqual('Running', model.status)
        self.assertEqual('Running', self._get_container_state(model.uuid,
                                                              model.host))
        self.assertIsNotNone(model.host)
        return resp, model

    def _delete_container(self, container_id, container_host):
        resp, _ = self.container_client.delete_container(container_id)
        self.assertEqual(204, resp.status)
        container = self.docker_client.get_container(
            container_id, self._get_docker_url(container_host))
        self.assertIsNone(container)

    def _get_container_state(self, container_id, docker_host=None):
        if docker_host is not None:
            container = self.docker_client.get_container(
                container_id, self._get_docker_url(docker_host))
        else:
            container = self.docker_client.get_container(container_id)
        status = container.get('State')
        if status.get('Error') is True:
            return 'Error'
        elif status.get('Paused'):
            return 'Paused'
        elif status.get('Running'):
            return 'Running'
        elif status.get('Status') == 'created':
            return 'Created'
        else:
            return 'Stopped'

    def _get_all_security_groups(self, container):
        # find all neutron ports of this container
        port_ids = set()
        for addrs_list in container.addresses.values():
            for addr in addrs_list:
                port_id = addr['port']
                port_ids.add(port_id)

        # find all security groups of this container
        sg_ids = set()
        for port_id in port_ids:
            port = self.ports_client.show_port(port_id)
            for sg in port['port']['security_groups']:
                sg_ids.add(sg)

        sg_names = []
        for sg_id in sg_ids:
            sg = self.sgs_client.show_security_group(sg_id)
            sg_names.append(sg['security_group']['name'])

        return sg_names

    def _get_docker_url(self, host='localhost', protocol='tcp', port='2375'):
        # NOTE(kiennt): By default, devstack-plugin-container will
        #               set docker_api_url = {
        #                       "unix://$DOCKER_ENGINE_SOCKET_FILE",
        #                       "tcp://0.0.0.0:$DOCKER_ENGINE_PORT"
        #                   }
        base_url = '{}://{}:{}' . format(protocol, host, port)
        return base_url
