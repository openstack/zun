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


class TempException(Exception):
    pass


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

    @mock.patch.object(driver.DockerDriver,
                       '_search_image_on_host')
    @mock.patch('zun.common.utils.should_pull_image')
    def test_pull_image_should_pull_no_image_not_present_locally(
            self, mock_should_pull_image, mock_search):
        mock_should_pull_image.return_value = False
        mock_search.return_value = None
        self.assertRaises(exception.ImageNotFound, self.driver.pull_image,
                          None, 'nonexisting', 'tag', 'never')

    @mock.patch.object(driver.DockerDriver,
                       '_search_image_on_host')
    @mock.patch('zun.common.utils.should_pull_image')
    def test_pull_image_should_pull_no_image_present_locally(
            self, mock_should_pull_image, mock_search):
        mock_should_pull_image.return_value = False
        mock_search.return_value = {'image': 'nginx', 'path': 'xyz'}
        self.assertEqual(({'image': 'nginx', 'path': 'xyz'}, True),
                         self.driver.pull_image(None, 'nonexisting',
                                                'tag', 'never'))

    @mock.patch.object(driver.DockerDriver,
                       '_search_image_on_host')
    @mock.patch('zun.common.utils.should_pull_image')
    def test_pull_image_success(self, mock_should_pull_image, mock_search):
        mock_should_pull_image.return_value = True
        mock_search.return_value = {'image': 'nginx', 'path': 'xyz'}
        ret = self.driver.pull_image(None, 'test_image', 'latest', 'always')
        self.assertEqual(({'image': 'test_image', 'path': None}, True), ret)
        self.mock_docker.pull.assert_called_once_with(
            'test_image',
            tag='latest')

    @mock.patch('zun.common.utils.parse_image_name')
    @mock.patch.object(driver.DockerDriver,
                       '_search_image_on_host')
    @mock.patch('zun.common.utils.should_pull_image')
    def test_pull_image_raises_API_error(self, mock_should_pull_image,
                                         mock_search, mock_parse_image):
        mock_should_pull_image.return_value = True
        mock_search.return_value = {'image': 'nginx', 'path': 'xyz'}
        mock_parse_image.return_value = ('repo', 'tag')
        with mock.patch.object(errors.APIError, '__str__',
                               return_value='404 Not Found') as mock_init:
            self.mock_docker.pull = mock.Mock(
                side_effect=errors.APIError('Error', '', ''))
            self.assertRaises(exception.ZunException, self.driver.pull_image,
                              None, 'repo', 'tag', 'always')
            self.mock_docker.pull.assert_called_once_with(
                'repo',
                tag='tag')
            self.assertEqual(1, mock_init.call_count)

    @mock.patch('zun.common.utils.parse_image_name')
    @mock.patch.object(driver.DockerDriver,
                       '_search_image_on_host')
    @mock.patch('zun.common.utils.should_pull_image')
    def test_pull_image_not_found(self, mock_should_pull_image,
                                  mock_search, mock_parse_image):
        mock_should_pull_image.return_value = True
        mock_search.return_value = {'image': 'nginx', 'path': 'xyz'}
        mock_parse_image.return_value = ('repo', 'tag')

        with mock.patch.object(self.mock_docker, 'pull',
                               side_effect=exception.ImageNotFound('Error')
                               ) as mock_pull:
            self.assertRaises(exception.ImageNotFound, self.driver.pull_image,
                              None, 'repo', 'tag', 'always')
            self.mock_docker.pull.assert_called_once_with(
                'repo',
                tag='tag')
            self.assertEqual(1, mock_pull.call_count)

    @mock.patch('zun.common.utils.parse_image_name')
    @mock.patch.object(driver.DockerDriver,
                       '_search_image_on_host')
    @mock.patch('zun.common.utils.should_pull_image')
    def test_pull_image_raises_docker_error(self, mock_should_pull_image,
                                            mock_search, mock_parse_image):
        mock_should_pull_image.return_value = True
        mock_search.return_value = {'image': 'nginx', 'path': 'xyz'}
        mock_parse_image.return_value = ('repo', 'tag')

        with mock.patch.object(self.mock_docker, 'pull',
                               side_effect=exception.DockerError('Error')
                               ) as mock_pull:
            self.assertRaises(exception.DockerError, self.driver.pull_image,
                              None, 'repo', 'tag', 'always')
            self.mock_docker.pull.assert_called_once_with(
                'repo',
                tag='tag')
            self.assertEqual(1, mock_pull.call_count)

    @mock.patch('zun.common.utils.parse_image_name')
    @mock.patch.object(driver.DockerDriver,
                       '_search_image_on_host')
    @mock.patch('zun.common.utils.should_pull_image')
    def test_pull_image_exception(self, mock_should_pull_image,
                                  mock_search, mock_parse_image):
        mock_should_pull_image.return_value = True
        mock_search.return_value = {'image': 'nginx', 'path': 'xyz'}
        mock_parse_image.return_value = ('repo', 'tag')

        with mock.patch.object(TempException, '__str__',
                               return_value='hit error') as mock_init:
            self.mock_docker.pull = mock.Mock(
                side_effect=TempException('Error'))
            self.assertRaises(exception.ZunException, self.driver.pull_image,
                              None, 'repo', 'tag', 'always')
            self.mock_docker.pull.assert_called_once_with(
                'repo',
                tag='tag')
            self.assertEqual(1, mock_init.call_count)

    def test_search_image_success(self):
        search_ret_val = [{'name': 'test_image', 'star_count': 3,
                          'is_official': True}]
        with mock.patch.object(self.mock_docker, 'search',
                               return_value=search_ret_val) as mock_search:
            ret = self.driver.search_image(None, 'image', 'test', False)
            self.assertEqual(1, len(ret))
            self.assertEqual('test_image', ret[0]['name'])
            self.mock_docker.search.assert_called_once_with('image')
            self.assertEqual(1, mock_search.call_count)

    def test_search_image_not_found_success(self):
        search_ret_val = [{'name': 'test_image', 'star_count': 3,
                          'is_official': True}]
        with mock.patch.object(self.mock_docker, 'search',
                               return_value=search_ret_val) as mock_search:
            ret = self.driver.search_image(None, 'image1', 'test', False)
            self.assertEqual(1, len(ret))
            self.assertEqual('test_image', ret[0]['name'])
            self.mock_docker.search.assert_called_once_with('image1')
            self.assertEqual(1, mock_search.call_count)

    def test_search_image_exact_match_success(self):
        search_ret_val = [{'name': 'test_image', 'star_count': 3,
                          'is_official': True}]
        with mock.patch.object(self.mock_docker, 'search',
                               return_value=search_ret_val) as mock_search:
            ret = self.driver.search_image(None, 'test_image', 'test', True)
            self.assertEqual(1, len(ret))
            self.assertEqual('test_image', ret[0]['name'])
            self.mock_docker.search.assert_called_once_with('test_image')
            self.assertEqual(1, mock_search.call_count)

    def test_search_image_not_found_exact_match_success(self):
        search_ret_val = [{'name': 'test_image', 'star_count': 3,
                          'is_official': True}]
        with mock.patch.object(self.mock_docker, 'search',
                               return_value=search_ret_val) as mock_search:
            ret = self.driver.search_image(None, 'image', 'test', True)
            self.assertEqual(0, len(ret))
            self.mock_docker.search.assert_called_once_with('image')
            self.assertEqual(1, mock_search.call_count)

    def test_search_image_apierror(self):
        with mock.patch.object(errors.APIError, '__str__',
                               return_value='hit error') as mock_init:
            self.mock_docker.search = mock.Mock(
                side_effect=errors.APIError('Error', '', ''))
            self.assertRaises(exception.ZunException, self.driver.search_image,
                              None, 'test_image', None, False)
            self.mock_docker.search.assert_called_once_with('test_image')
            self.assertEqual(1, mock_init.call_count)

    def test_search_image_exception(self):
        with mock.patch.object(self.mock_docker, 'search',
                               side_effect=Exception) as mock_search:
            self.assertRaises(exception.ZunException, self.driver.search_image,
                              None, 'test_image', None, False)
            self.mock_docker.search.assert_called_once_with('test_image')
            self.assertEqual(1, mock_search.call_count)
