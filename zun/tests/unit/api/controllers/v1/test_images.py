# Licensed under the Apache License, Version 2.0 (the "License");
#    you may not use this file except in compliance with the License.
#    You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS,
#    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    See the License for the specific language governing permissions and
#    limitations under the License.

import mock
from mock import patch
from webtest.app import AppError

from oslo_utils import uuidutils

from zun.common import exception
from zun import objects
from zun.tests.unit.api import base as api_base
from zun.tests.unit.db import utils


class TestImageController(api_base.FunctionalTest):
    @mock.patch('zun.common.policy.enforce', return_value=True)
    @patch('zun.compute.api.API.image_pull')
    @patch('zun.objects.ComputeNode.get_by_name')
    def test_image_pull(self, mock_get, mock_image_pull, mock_policy_enforce):
        mock_image_pull.side_effect = lambda x, y, z: y
        mock_get.return_value = mock.Mock(hostname='fake-host')

        params = ('{"repo": "hello-world", "host": "fake-host"}')
        response = self.post('/v1/images/',
                             params=params,
                             content_type='application/json')

        self.assertEqual(202, response.status_int)
        self.assertTrue(mock_image_pull.called)

        params = ('{"repo": "hello-world:test", "host": "fake-host"}')
        response = self.post('/v1/images/',
                             params=params,
                             content_type='application/json')

        self.assertEqual(202, response.status_int)
        self.assertTrue(mock_image_pull.called)

    @patch('zun.compute.api.API.image_pull')
    def test_image_pull_with_no_repo(self, mock_image_pull):
        params = {}
        with self.assertRaisesRegex(AppError,
                                    "is a required property"):
            self.post('/v1/images/',
                      params=params,
                      content_type='application/json')
        self.assertTrue(mock_image_pull.not_called)

    @mock.patch('zun.common.policy.enforce', return_value=True)
    @patch('zun.compute.api.API.image_pull')
    @patch('zun.objects.ComputeNode.get_by_name')
    def test_image_pull_conflict(
            self, mock_get, mock_image_pull, mock_policy_enforce):
        mock_image_pull.side_effect = lambda x, y, z: y
        mock_get.return_value = mock.Mock(hostname='fake-host')

        params = ('{"repo": "hello-world", "host": "fake-host"}')
        response = self.post('/v1/images/',
                             params=params,
                             content_type='application/json')

        self.assertEqual(202, response.status_int)
        self.assertTrue(mock_image_pull.called)
        self.assertRaises(AppError, self.post, '/v1/images/',
                          params=params, content_type='application/json')
        self.assertTrue(mock_image_pull.not_called)

    @mock.patch('zun.common.policy.enforce', return_value=True)
    @patch('zun.compute.api.API.image_pull')
    @patch('zun.objects.ComputeNode.get_by_name')
    def test_pull_image_set_project_id_and_user_id(
            self, mock_get, mock_image_pull, mock_policy_enforce):
        def _create_side_effect(cnxt, image, host):
            self.assertEqual(self.context.project_id, image.project_id)
            self.assertEqual(self.context.user_id, image.user_id)
            self.assertEqual('fake-host', host)
            return image
        mock_image_pull.side_effect = _create_side_effect
        mock_get.return_value = mock.Mock(hostname='fake-host')

        params = ('{"repo": "hello-world", "host": "foo"}')
        self.post('/v1/images/',
                  params=params,
                  content_type='application/json')

    @mock.patch('zun.common.policy.enforce', return_value=True)
    @patch('zun.compute.api.API.image_pull')
    @patch('zun.objects.ComputeNode.get_by_name')
    def test_image_pull_with_tag(
            self, mock_get, mock_image_pull, mock_policy_enforce):
        mock_image_pull.side_effect = lambda x, y, z: y
        mock_get.return_value = mock.Mock(hostname='fake-host')

        params = ('{"repo": "hello-world:latest", "host": "fake-host"}')
        response = self.post('/v1/images/',
                             params=params,
                             content_type='application/json')

        self.assertEqual(202, response.status_int)
        self.assertTrue(mock_image_pull.called)

    @mock.patch('zun.common.policy.enforce', return_value=True)
    @patch('zun.objects.Image.list')
    def test_get_all_images(self, mock_image_list, mock_policy_enforce):
        test_image = utils.get_test_image()
        images = [objects.Image(self.context, **test_image)]
        mock_image_list.return_value = images

        response = self.get('/v1/images/')

        mock_image_list.assert_called_once_with(mock.ANY,
                                                1000, None, 'id', 'asc',
                                                filters=None)
        self.assertEqual(200, response.status_int)
        actual_images = response.json['images']
        self.assertEqual(1, len(actual_images))
        self.assertEqual(test_image['uuid'],
                         actual_images[0].get('uuid'))

    @patch('zun.common.policy.enforce')
    @patch('zun.objects.Image.get_by_uuid')
    def test_get_one_image_by_uuid(self, mock_image_get_by_uuid, mock_policy):
        mock_policy.return_value = True
        test_image = utils.get_test_image()
        test_image_obj = objects.Image(self.context, **test_image)
        mock_image_get_by_uuid.return_value = test_image_obj

        response = self.get('/v1/images/%s/' % test_image['uuid'])
        mock_image_get_by_uuid.assert_called_once_with(
            mock.ANY,
            test_image['uuid'])
        self.assertEqual(200, response.status_int)
        self.assertEqual(test_image['uuid'],
                         response.json['uuid'])

    @mock.patch('zun.common.policy.enforce', return_value=True)
    @patch('zun.objects.Image.list')
    def test_get_all_images_with_pagination_marker(
            self, mock_image_list, mock_policy_enforce):
        image_list = []
        for id_ in range(4):
            test_image = utils.create_test_image(
                context=self.context,
                id=id_,
                repo='testrepo' + str(id_),
                uuid=uuidutils.generate_uuid())
            image_list.append(objects.Image(self.context, **test_image))
        mock_image_list.return_value = image_list[-1:]
        response = self.get('/v1/images/?limit=3&marker=%s'
                            % image_list[2].uuid)

        self.assertEqual(200, response.status_int)
        actual_images = response.json['images']
        self.assertEqual(1, len(actual_images))
        self.assertEqual(image_list[-1].uuid,
                         actual_images[0].get('uuid'))

    @patch('zun.compute.api.API.image_search')
    def test_search_image(self, mock_image_search):
        mock_image_search.return_value = {'name': 'redis', 'stars': 2000}
        response = self.get('/v1/images/redis/search/')
        self.assertEqual(200, response.status_int)
        mock_image_search.assert_called_once_with(
            mock.ANY, 'redis', None, False)

    @patch('zun.compute.api.API.image_search')
    def test_search_image_with_tag(self, mock_image_search):
        mock_image_search.return_value = {'name': 'redis', 'stars': 2000}
        response = self.get('/v1/images/redis:test/search/')
        self.assertEqual(200, response.status_int)
        mock_image_search.assert_called_once_with(
            mock.ANY, 'redis:test', None, False)

    @patch('zun.compute.api.API.image_search')
    def test_search_image_not_found(self, mock_image_search):
        mock_image_search.side_effect = exception.ImageNotFound
        self.assertRaises(AppError, self.get, '/v1/images/redis/search/')
        mock_image_search.assert_called_once_with(
            mock.ANY, 'redis', None, False)

    @patch('zun.compute.rpcapi.API.image_search')
    def test_search_image_with_exact_match_true(self, mock_image_search):
        mock_image_search.return_value = {'name': 'redis', 'stars': 2000}
        response = self.get(
            '/v1/images/redis/search?exact_match=true&image_driver=docker')
        self.assertEqual(200, response.status_int)
        mock_image_search.assert_called_once_with(
            mock.ANY, 'redis', 'docker', True)

    @patch('zun.compute.rpcapi.API.image_search')
    def test_search_image_with_exact_match_false(self, mock_image_search):
        mock_image_search.return_value = {'name': 'redis', 'stars': 2000}
        response = self.get(
            '/v1/images/redis/search?exact_match=false&image_driver=glance')
        self.assertEqual(200, response.status_int)
        mock_image_search.assert_called_once_with(
            mock.ANY, 'redis', 'glance', False)

    @patch('zun.compute.api.API.image_search')
    def test_search_image_with_exact_match_wrong(self, mock_image_search):
        mock_image_search.side_effect = exception.InvalidValue
        with self.assertRaisesRegex(AppError,
                                    "Invalid input for query parameters"):
            self.get('/v1/images/redis/search?exact_match=wrong')

    @patch('zun.compute.api.API.image_search')
    def test_search_image_with_image_driver_wrong(self, mock_image_search):
        mock_image_search.side_effect = exception.InvalidValue
        with self.assertRaisesRegex(AppError,
                                    "Invalid input for query parameters"):
            self.get('/v1/images/redis/search?image_driver=wrong')


class TestImageEnforcement(api_base.FunctionalTest):

    def _common_policy_check(self, rule, func, *arg, **kwarg):
        self.policy.set_rules({rule: 'project_id:non_fake'})
        response = func(*arg, **kwarg)
        self.assertEqual(403, response.status_int)
        self.assertEqual('application/json', response.content_type)
        self.assertTrue(
            "Policy doesn't allow %s to be performed." % rule,
            response.json['errors'][0]['detail'])

    def test_policy_disallow_get_all(self):
        self._common_policy_check(
            'image:get_all', self.get_json, '/images/',
            expect_errors=True)

    def test_policy_disallow_create(self):
        params = ('{"repo": "foo", "host": "foo"}')
        self._common_policy_check(
            'image:pull', self.post, '/v1/images/',
            params=params,
            content_type='application/json',
            expect_errors=True)
