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

    @classmethod
    def resource_setup(cls):

        super(TestContainer, cls).resource_setup()

    def _create_container(self, **kwargs):

        model = datagen.contaienr_data(**kwargs)
        return self.container_client.post_container(model)

    def _delete_container(self, container_id):

        self.container_client.delete_container(container_id)

    @decorators.idempotent_id('a04f61f2-15ae-4200-83b7-1f311b101f35')
    def test_container_create_list_delete(self):

        resp, container = self._create_container()
        self.assertEqual(202, resp.status)

        resp, model = self.container_client.list_containers()
        self.assertEqual(200, resp.status)
        self.assertGreater(len(model.containers), 0)

        self._delete_container(container.uuid)

        resp, model = self.container_client.list_containers()
        self.assertEqual(200, resp.status)
        self.assertEqual(len(model.containers), 0)
