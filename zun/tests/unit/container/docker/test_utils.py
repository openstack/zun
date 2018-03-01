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

import mock

from oslo_serialization import jsonutils

from zun.container.docker import utils as docker_utils
from zun.tests.unit.container import base


class TestDockerHTTPClient(base.DriverTestCase):

    def setUp(self):
        super(TestDockerHTTPClient, self).setUp()
        self.client = docker_utils.DockerHTTPClient()

    @mock.patch('tarfile.open')
    def test_read_tar_image(self, mock_open):
        fake_image = {'path': 'fake-path'}
        mock_context_manager = mock.MagicMock()
        mock_open.return_value = mock_context_manager
        mock_file = mock.MagicMock()
        mock_context_manager.__enter__.return_value = mock_file
        mock_data = [{"Config": "fake_config",
                      "RepoTags": ["cirros:latest"],
                      "Layers": ["fake_layer", "fake_layer2"]}]
        mock_file.extractfile.return_value.read.return_value = \
            jsonutils.dumps(mock_data, separators=(',', ':'))

        self.client.read_tar_image(fake_image)
        self.assertEqual('cirros', fake_image['repo'])
        self.assertEqual('latest', fake_image['tag'])

    @mock.patch('tarfile.open')
    def test_read_tar_image_multi_tags(self, mock_open):
        fake_image = {'path': 'fake-path'}
        mock_context_manager = mock.MagicMock()
        mock_open.return_value = mock_context_manager
        mock_file = mock.MagicMock()
        mock_context_manager.__enter__.return_value = mock_file
        mock_data = [{"Config": "fake_config",
                      "RepoTags": ["cirros:latest", "cirros:0.3.4"],
                      "Layers": ["fake_layer", "fake_layer2"]}]
        mock_file.extractfile.return_value.read.return_value = \
            jsonutils.dumps(mock_data, separators=(',', ':'))

        self.client.read_tar_image(fake_image)
        self.assertEqual('cirros', fake_image['repo'])
        self.assertEqual('latest', fake_image['tag'])

    @mock.patch('tarfile.open')
    def test_read_tar_image_no_repotag(self, mock_open):
        fake_image = {'path': 'fake-path'}
        mock_context_manager = mock.MagicMock()
        mock_open.return_value = mock_context_manager
        mock_file = mock.MagicMock()
        mock_context_manager.__enter__.return_value = mock_file
        mock_data = [{"Config": "fake_config",
                      "RepoTags": "",
                      "Layers": ["fake_layer", "fake_layer2"]}]
        mock_file.extractfile.return_value.read.return_value = \
            jsonutils.dumps(mock_data, separators=(',', ':'))

        self.client.read_tar_image(fake_image)
        self.assertEqual('fake_config', fake_image['repo'])
        self.assertEqual('', fake_image['tag'])
