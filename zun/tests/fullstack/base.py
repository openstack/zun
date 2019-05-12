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

import docker
from oslo_log import log as logging

import zun.conf
from zun.tests import base
from zun.tests.fullstack import utils


CONF = zun.conf.CONF
LOG = logging.getLogger(__name__)


class BaseFullStackTestCase(base.TestCase):

    def setUp(self):
        super(BaseFullStackTestCase, self).setUp()

        self.docker = docker.APIClient(base_url='tcp://0.0.0.0:2375')
        try:
            self.zun = utils.get_zun_client_from_env()
        except Exception as e:
            # We may missing or didn't source configured openrc file.
            message = ("Missing environment variable %s in your local."
                       "Please add it and also check other missing "
                       "environment variables. After that please source "
                       "the openrc file. "
                       "Trying credentials from DevStack cloud.yaml ...")
            LOG.warning(message, e.args[0])
            self.zun = utils.get_zun_client_from_creds()

    def ensure_container_deleted(self, container_id):
        def is_container_deleted():
            containers = self.zun.containers.list()
            container_ids = [c.uuid for c in containers]
            if container_id in container_ids:
                return False
            else:
                return True
        utils.wait_for_condition(is_container_deleted)

    def ensure_container_in_desired_state(self, container_id, status):
        def is_container_in_desired_state():
            c = self.zun.containers.get(container_id)
            if c.status == status:
                return True
            else:
                return False
        utils.wait_for_condition(is_container_in_desired_state, timeout=300)

    def _get_container_in_docker(self, container):
        return self.docker.inspect_container('zun-' + container.uuid)

    def _get_state_in_docker(self, container):
        container = self.docker.inspect_container('zun-' + container.uuid)
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
