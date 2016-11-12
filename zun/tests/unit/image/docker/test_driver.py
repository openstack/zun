# Copyright 2016 Intel.
#
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

from docker import errors

from zun.common import exception
from zun.container.docker import utils
from zun.image.docker import driver
from zun.tests import base


class TestDriver(base.BaseTestCase):
    def setUp(self):
        super(TestDriver, self).setUp()
        self.driver = driver.DockerDriver()
        dfc_patcher = mock.patch.object(utils,
                                        'docker_client')
        docker_client = dfc_patcher.start()
        self.dfc_context_manager = docker_client.return_value
        self.mock_docker = mock.MagicMock()
        self.dfc_context_manager.__enter__.return_value = self.mock_docker
        self.addCleanup(dfc_patcher.stop)

    def test_pull_image_success(self):
        ret = self.driver.pull_image(None, 'test_image', 'latest')
        self.assertEqual({'image': 'test_image', 'path': None}, ret)
        self.mock_docker.pull.assert_called_once_with(
            'test_image',
            tag='latest',
            stream=True)

    @mock.patch('zun.common.utils.parse_image_name')
    def test_pull_image_raises_API_error(self, mock_parse_image):
        mock_parse_image.return_value = ('repo', 'tag')
        with mock.patch.object(errors.APIError, '__str__',
                               return_value='404 Not Found') as mock_init:
            self.mock_docker.pull = mock.Mock(
                side_effect=errors.APIError('Error', '', ''))
            self.assertRaises(exception.ZunException, self.driver.pull_image,
                              None, 'repo', 'tag')
            self.mock_docker.pull.assert_called_once_with(
                'repo',
                tag='tag',
                stream=True)
            self.assertEqual(1, mock_init.call_count)

    @mock.patch('zun.common.utils.parse_image_name')
    def test_pull_image_not_found(self, mock_parse_image):
        mock_parse_image.return_value = ('repo', 'tag')
        pull_return_value = '{"errorDetail":{"message":'\
                            '"Error: image library/repo not found"},'\
                            '"error":"Error: image library/repo not found"}'

        with mock.patch.object(self.mock_docker, 'pull',
                               return_value=[pull_return_value]) as mock_init:
            self.assertRaises(exception.ImageNotFound, self.driver.pull_image,
                              None, 'repo', 'tag')
            self.mock_docker.pull.assert_called_once_with(
                'repo',
                tag='tag',
                stream=True)
            self.assertEqual(1, mock_init.call_count)

    @mock.patch('zun.common.utils.parse_image_name')
    def test_pull_image_raises_docker_error(self, mock_parse_image):
        mock_parse_image.return_value = ('repo', 'tag')
        pull_return_value = '{"errorDetail":{"message":'\
                            '"Error: image library/repo not"},'\
                            '"error":"Error: image library/repo"}'

        with mock.patch.object(self.mock_docker, 'pull',
                               return_value=[pull_return_value]) as mock_init:
            self.assertRaises(exception.DockerError, self.driver.pull_image,
                              None, 'repo', 'tag')
            self.mock_docker.pull.assert_called_once_with(
                'repo',
                tag='tag',
                stream=True)
            self.assertEqual(1, mock_init.call_count)

    @mock.patch('zun.common.utils.parse_image_name')
    def test_pull_image_exception(self, mock_parse_image):
        mock_parse_image.return_value = ('repo', 'tag')
        with mock.patch.object(errors.APIError, '__str__',
                               return_value='hit error') as mock_init:
            self.mock_docker.pull = mock.Mock(
                side_effect=errors.APIError('Error', '', ''))
            self.assertRaises(exception.ZunException, self.driver.pull_image,
                              None, 'repo', 'tag')
            self.mock_docker.pull.assert_called_once_with(
                'repo',
                tag='tag',
                stream=True)
            self.assertEqual(1, mock_init.call_count)
