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

from zun import objects
from zun.tests.unit.api import base as api_base
from zun.tests.unit.db import utils


class TestImageController(api_base.FunctionalTest):
    @patch('zun.compute.api.API.image_pull')
    def test_image_pull(self, mock_image_pull):
        mock_image_pull.side_effect = lambda x, y: y

        params = ('{"repo": "hello-world"}')
        response = self.app.post('/v1/images/',
                                 params=params,
                                 content_type='application/json')

        self.assertEqual(202, response.status_int)
        self.assertTrue(mock_image_pull.called)

        params = ('{"repo": "hello-world:test"}')
        response = self.app.post('/v1/images/',
                                 params=params,
                                 content_type='application/json')

        self.assertEqual(202, response.status_int)
        self.assertTrue(mock_image_pull.called)

    @patch('zun.compute.api.API.image_pull')
    def test_image_pull_with_no_repo(self, mock_image_pull):
        mock_image_pull.side_effect = lambda x, y: y

        self.assertRaises(AppError, self.app.post, '/v1/images/',
                          content_type='application/json')

        self.assertTrue(mock_image_pull.not_called)

    @patch('zun.compute.api.API.image_pull')
    def test_image_pull_conflict(self, mock_image_pull):
        mock_image_pull.side_effect = lambda x, y: y

        params = ('{"repo": "hello-world"}')
        response = self.app.post('/v1/images/',
                                 params=params,
                                 content_type='application/json')

        self.assertEqual(202, response.status_int)
        self.assertTrue(mock_image_pull.called)
        self.assertRaises(AppError, self.app.post, '/v1/images/',
                          params=params, content_type='application/json')
        self.assertTrue(mock_image_pull.not_called)

    @patch('zun.compute.api.API.image_pull')
    def test_pull_image_set_project_id_and_user_id(
            self, mock_image_pull):
        def _create_side_effect(cnxt, image):
            self.assertEqual(self.context.project_id, image.project_id)
            self.assertEqual(self.context.user_id, image.user_id)
            return image
        mock_image_pull.side_effect = _create_side_effect

        params = ('{"repo": "hello-world"}')
        self.app.post('/v1/images/',
                      params=params,
                      content_type='application/json')

    @patch('zun.compute.api.API.image_pull')
    def test_image_pull_with_tag(self, mock_image_pull):
        mock_image_pull.side_effect = lambda x, y: y

        params = ('{"repo": "hello-world:latest"}')
        response = self.app.post('/v1/images/',
                                 params=params,
                                 content_type='application/json')

        self.assertEqual(202, response.status_int)
        self.assertTrue(mock_image_pull.called)

    @patch('zun.compute.api.API.image_show')
    @patch('zun.objects.Image.list')
    def test_get_all_images(self, mock_image_list, mock_image_show):
        test_image = utils.get_test_image()
        images = [objects.Image(self.context, **test_image)]
        mock_image_list.return_value = images
        mock_image_show.return_value = images[0]

        response = self.app.get('/v1/images/')

        mock_image_list.assert_called_once_with(mock.ANY,
                                                1000, None, 'id', 'asc',
                                                filters=None)
        self.assertEqual(200, response.status_int)
        actual_images = response.json['images']
        self.assertEqual(1, len(actual_images))
        self.assertEqual(test_image['uuid'],
                         actual_images[0].get('uuid'))

    @patch('zun.compute.api.API.image_show')
    @patch('zun.objects.Image.list')
    def test_get_all_images_with_pagination_marker(self, mock_image_list,
                                                   mock_image_show):
        image_list = []
        for id_ in range(4):
            test_image = utils.create_test_image(
                id=id_,
                repo='testrepo' + str(id_),
                uuid=uuidutils.generate_uuid())
            image_list.append(objects.Image(self.context, **test_image))
        mock_image_list.return_value = image_list[-1:]
        mock_image_show.return_value = image_list[-1]
        response = self.app.get('/v1/images/?limit=3&marker=%s'
                                % image_list[2].uuid)

        self.assertEqual(200, response.status_int)
        actual_images = response.json['images']
        self.assertEqual(1, len(actual_images))
        self.assertEqual(image_list[-1].uuid,
                         actual_images[0].get('uuid'))

    @patch('zun.compute.api.API.image_show')
    @patch('zun.objects.Image.list')
    def test_get_all_images_with_exception(self, mock_image_list,
                                           mock_image_show):
        test_image = utils.get_test_image()
        images = [objects.Image(self.context, **test_image)]
        mock_image_list.return_value = images
        mock_image_show.side_effect = Exception

        response = self.app.get('/v1/images/')

        mock_image_list.assert_called_once_with(mock.ANY, 1000,
                                                None, 'id', 'asc',
                                                filters=None)
        self.assertEqual(200, response.status_int)
        actual_images = response.json['images']
        self.assertEqual(1, len(actual_images))
        self.assertEqual(test_image['uuid'],
                         actual_images[0].get('uuid'))


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
        params = ('{"repo": "foo"}')
        self._common_policy_check(
            'image:pull', self.app.post, '/v1/images/',
            params=params,
            content_type='application/json',
            expect_errors=True)
