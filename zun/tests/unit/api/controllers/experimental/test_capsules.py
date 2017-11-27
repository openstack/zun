#    Copyright 2017 Arm Limited
#
#    Licensed under the Apache License, Version 2.0 (the "License");
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
from oslo_utils import uuidutils
from webtest.app import AppError
from zun.common import exception
from zun import objects
from zun.tests.unit.api import base as api_base
from zun.tests.unit.db import utils


class TestCapsuleController(api_base.FunctionalTest):
    @patch('zun.compute.api.API.capsule_create')
    def test_create_capsule(self, mock_capsule_create):
        params = ('{"spec": {"kind": "capsule",'
                  '"spec": {"containers":'
                  '[{"environment": {"ROOT_PASSWORD": "foo0"}, '
                  '"image": "test", "labels": {"app": "web"}, '
                  '"image_driver": "docker", "resources": '
                  '{"allocation": {"cpu": 1, "memory": 1024}}}], '
                  '"volumes": [{"name": "volume1", '
                  '"image": "test", "drivers": "cinder", "volumeType": '
                  '"type1", "driverOptions": "options", '
                  '"size": "5GB"}]}, '
                  '"metadata": {"labels": {"foo0": "bar0", "foo1": "bar1"}, '
                  '"name": "capsule-example"}}}')
        response = self.post('/capsules/',
                             params=params,
                             content_type='application/json')
        return_value = response.json
        expected_meta_name = "capsule-example"
        expected_meta_labels = {"foo0": "bar0", "foo1": "bar1"}
        expected_memory = '1024M'
        expected_cpu = 1.0
        expected_container_num = 2
        self.assertEqual(len(return_value["containers_uuids"]),
                         expected_container_num)
        self.assertEqual(return_value["meta_name"], expected_meta_name)
        self.assertEqual(return_value["meta_labels"], expected_meta_labels)
        self.assertEqual(return_value["memory"], expected_memory)
        self.assertEqual(return_value["cpu"], expected_cpu)
        self.assertEqual(202, response.status_int)
        self.assertTrue(mock_capsule_create.called)

    @patch('zun.compute.api.API.capsule_create')
    def test_create_capsule_two_containers(self, mock_capsule_create):
        params = ('{"spec": {"kind": "capsule",'
                  '"spec": {"containers":'
                  '[{"environment": {"ROOT_PASSWORD": "foo0"}, '
                  '"image": "test1", "labels": {"app0": "web0"}, '
                  '"image_driver": "docker", "resources": '
                  '{"allocation": {"cpu": 1, "memory": 1024}}}, '
                  '{"environment": {"ROOT_PASSWORD": "foo1"}, '
                  '"image": "test1", "labels": {"app1": "web1"}, '
                  '"image_driver": "docker", "resources": '
                  '{"allocation": {"cpu": 1, "memory": 1024}}}]}, '
                  '"metadata": {"labels": {"foo0": "bar0", "foo1": "bar1"}, '
                  '"name": "capsule-example"}}}')
        response = self.post('/capsules/',
                             params=params,
                             content_type='application/json')
        return_value = response.json
        expected_meta_name = "capsule-example"
        expected_meta_labels = {"foo0": "bar0", "foo1": "bar1"}
        expected_memory = '2048M'
        expected_cpu = 2.0
        expected_container_num = 3
        self.assertEqual(len(return_value["containers_uuids"]),
                         expected_container_num)
        self.assertEqual(return_value["meta_name"],
                         expected_meta_name)
        self.assertEqual(return_value["meta_labels"],
                         expected_meta_labels)
        self.assertEqual(return_value["memory"], expected_memory)
        self.assertEqual(return_value["cpu"], expected_cpu)
        self.assertEqual(202, response.status_int)
        self.assertTrue(mock_capsule_create.called)

    @patch('zun.compute.api.API.capsule_create')
    @patch('zun.common.utils.check_capsule_template')
    def test_create_capsule_wrong_kind_set(self, mock_check_template,
                                           mock_capsule_create):
        params = ('{"spec": {"kind": "test",'
                  '"spec": {"containers":'
                  '[{"environment": {"ROOT_PASSWORD": "foo0"}, '
                  '"image": "test1", "labels": {"app0": "web0"}, '
                  '"image_driver": "docker", "resources": '
                  '{"allocation": {"cpu": 1, "memory": 1024}}}]}, '
                  '"metadata": {"labels": {"foo0": "bar0"}, '
                  '"name": "capsule-example"}}}')
        mock_check_template.side_effect = exception.InvalidCapsuleTemplate(
            "kind fields need to be set as capsule or Capsule")
        response = self.post_json('/capsules/', params, expect_errors=True)
        self.assertEqual(400, response.status_int)
        self.assertFalse(mock_capsule_create.called)

    @patch('zun.compute.api.API.capsule_create')
    @patch('zun.common.utils.check_capsule_template')
    def test_create_capsule_less_than_one_container(self, mock_check_template,
                                                    mock_capsule_create):
        params = ('{"spec": {"kind": "capsule",'
                  '"spec": {container:[]}, '
                  '"metadata": {"labels": {"foo0": "bar0"}, '
                  '"name": "capsule-example"}}}')
        mock_check_template.side_effect = exception.InvalidCapsuleTemplate(
            "Capsule need to have one container at least")
        response = self.post_json('/capsules/', params, expect_errors=True)
        self.assertEqual(400, response.status_int)
        self.assertFalse(mock_capsule_create.called)

    @patch('zun.compute.api.API.capsule_create')
    @patch('zun.common.utils.check_capsule_template')
    def test_create_capsule_no_container_field(self, mock_check_template,
                                               mock_capsule_create):
        params = ('{"spec": {"kind": "capsule",'
                  '"spec": {}, '
                  '"metadata": {"labels": {"foo0": "bar0"}, '
                  '"name": "capsule-example"}}}')
        mock_check_template.side_effect = exception.InvalidCapsuleTemplate(
            "Capsule need to have one container at least")
        self.assertRaises(AppError, self.post, '/capsules/',
                          params=params, content_type='application/json')
        self.assertFalse(mock_capsule_create.called)

    @patch('zun.compute.api.API.capsule_create')
    @patch('zun.common.utils.check_capsule_template')
    def test_create_capsule_no_container_image(self, mock_check_template,
                                               mock_capsule_create):
        params = ('{"spec": {"kind": "capsule",'
                  '"spec": {container:[{"environment": '
                  '{"ROOT_PASSWORD": "foo1"}]}, '
                  '"metadata": {"labels": {"foo0": "bar0"}, '
                  '"name": "capsule-example"}}}')
        mock_check_template.side_effect = exception.InvalidCapsuleTemplate(
            "Container image is needed")
        self.assertRaises(AppError, self.post, '/capsules/',
                          params=params, content_type='application/json')
        self.assertFalse(mock_capsule_create.called)

    @patch('zun.compute.api.API.container_show')
    @patch('zun.objects.Capsule.get_by_uuid')
    @patch('zun.objects.Container.get_by_uuid')
    def test_get_one_by_uuid(self, mock_container_get_by_uuid,
                             mock_capsule_get_by_uuid,
                             mock_container_show):
        test_container = utils.get_test_container()
        test_container_obj = objects.Container(self.context, **test_container)
        mock_container_get_by_uuid.return_value = test_container_obj
        mock_container_show.return_value = test_container_obj

        test_capsule = utils.get_test_capsule()
        test_capsule_obj = objects.Capsule(self.context, **test_capsule)
        mock_capsule_get_by_uuid.return_value = test_capsule_obj

        response = self.get('/capsules/%s/' % test_capsule['uuid'])

        context = mock_capsule_get_by_uuid.call_args[0][0]
        self.assertIs(False, context.all_tenants)
        self.assertEqual(200, response.status_int)
        self.assertEqual(test_capsule['uuid'],
                         response.json['uuid'])

    @patch('zun.compute.api.API.container_show')
    @patch('zun.objects.Capsule.get_by_uuid')
    @patch('zun.objects.Container.get_by_uuid')
    def test_get_one_by_uuid_all_tenants(self, mock_container_get_by_uuid,
                                         mock_capsule_get_by_uuid,
                                         mock_container_show):
        test_container = utils.get_test_container()
        test_container_obj = objects.Container(self.context, **test_container)
        mock_container_get_by_uuid.return_value = test_container_obj
        mock_container_show.return_value = test_container_obj

        test_capsule = utils.get_test_capsule()
        test_capsule_obj = objects.Capsule(self.context, **test_capsule)
        mock_capsule_get_by_uuid.return_value = test_capsule_obj

        response = self.get('/capsules/%s/?all_tenants=1' %
                            test_capsule['uuid'])

        context = mock_capsule_get_by_uuid.call_args[0][0]
        self.assertIs(False, context.all_tenants)
        self.assertEqual(200, response.status_int)
        self.assertEqual(test_capsule['uuid'],
                         response.json['uuid'])

    @patch('zun.compute.api.API.capsule_delete')
    @patch('zun.objects.Capsule.get_by_uuid')
    @patch('zun.objects.Container.get_by_uuid')
    @patch('zun.objects.Capsule.save')
    def test_delete_capsule_by_uuid(self, mock_capsule_save,
                                    mock_container_get_by_uuid,
                                    mock_capsule_get_by_uuid,
                                    mock_capsule_delete):
        test_container = utils.get_test_container()
        test_container_obj = objects.Container(self.context, **test_container)
        mock_container_get_by_uuid.return_value = test_container_obj

        test_capsule = utils.get_test_capsule()
        test_capsule_obj = objects.Capsule(self.context,
                                           **test_capsule)
        mock_capsule_get_by_uuid.return_value = test_capsule_obj
        mock_capsule_save.return_value = True
        mock_capsule_delete.return_value = True

        capsule_uuid = test_capsule.get('uuid')
        response = self.app.delete('/capsules/%s' % capsule_uuid)

        self.assertTrue(mock_capsule_delete.called)
        self.assertEqual(204, response.status_int)
        context = mock_capsule_save.call_args[0][0]
        self.assertIs(False, context.all_tenants)

    @patch('zun.common.policy.enforce')
    @patch('zun.compute.api.API.capsule_delete')
    @patch('zun.objects.Capsule.get_by_uuid')
    @patch('zun.objects.Container.get_by_uuid')
    @patch('zun.objects.Capsule.save')
    def test_delete_capsule_by_uuid_all_tenants(self,
                                                mock_capsule_save,
                                                mock_container_get_by_uuid,
                                                mock_capsule_get_by_uuid,
                                                mock_capsule_delete,
                                                mock_policy):
        mock_policy.return_value = True
        test_container = utils.get_test_container()
        test_container_obj = objects.Container(self.context, **test_container)
        mock_container_get_by_uuid.return_value = test_container_obj

        test_capsule = utils.get_test_capsule()
        test_capsule_obj = objects.Capsule(self.context,
                                           **test_capsule)
        mock_capsule_get_by_uuid.return_value = test_capsule_obj
        mock_capsule_save.return_value = True
        mock_capsule_delete.return_value = True

        capsule_uuid = test_capsule.get('uuid')
        response = self.app.delete(
            '/capsules/%s/?all_tenants=1' % capsule_uuid)

        self.assertTrue(mock_capsule_delete.called)
        self.assertEqual(204, response.status_int)
        context = mock_capsule_save.call_args[0][0]
        self.assertIs(True, context.all_tenants)

    def test_delete_capsule_with_uuid_not_found(self):
        uuid = uuidutils.generate_uuid()
        self.assertRaises(AppError, self.app.delete,
                          '/capsules/%s' % uuid)

    @patch('zun.compute.api.API.capsule_delete')
    @patch('zun.objects.Capsule.get_by_name')
    @patch('zun.objects.Container.get_by_uuid')
    @patch('zun.objects.Capsule.save')
    def test_delete_capsule_by_name(self, mock_capsule_save,
                                    mock_container_get_by_name,
                                    mock_capsule_get_by_uuid,
                                    mock_capsule_delete):
        test_container = utils.get_test_container()
        test_container_obj = objects.Container(self.context, **test_container)
        mock_container_get_by_name.return_value = test_container_obj

        test_capsule = utils.get_test_capsule()
        test_capsule_obj = objects.Capsule(self.context,
                                           **test_capsule)
        mock_capsule_get_by_uuid.return_value = test_capsule_obj
        mock_capsule_save.return_value = True
        mock_capsule_delete.return_value = True

        capsule_name = test_capsule.get('meta_name')
        response = self.app.delete('/capsules/%s/' %
                                   capsule_name)

        self.assertTrue(mock_capsule_delete.called)
        self.assertEqual(204, response.status_int)
        context = mock_capsule_save.call_args[0][0]
        self.assertIs(False, context.all_tenants)

    @patch('zun.compute.api.API.container_show')
    @patch('zun.objects.Capsule.list')
    @patch('zun.objects.Container.get_by_uuid')
    def test_get_all_capsules(self, mock_container_get_by_uuid,
                              mock_capsule_list,
                              mock_container_show):
        test_container = utils.get_test_container()
        test_container_obj = objects.Container(self.context,
                                               **test_container)
        mock_container_get_by_uuid.return_value = test_container_obj

        test_capsule = utils.get_test_capsule()
        test_capsule_obj = objects.Capsule(self.context, **test_capsule)
        mock_capsule_list.return_value = [test_capsule_obj]
        mock_container_show.return_value = test_container_obj

        response = self.app.get('/capsules/')

        mock_capsule_list.assert_called_once_with(mock.ANY,
                                                  1000, None, 'id', 'asc',
                                                  filters=None)
        context = mock_capsule_list.call_args[0][0]
        self.assertIs(False, context.all_tenants)
        self.assertEqual(200, response.status_int)
        actual_capsules = response.json['capsules']
        self.assertEqual(1, len(actual_capsules))
        self.assertEqual(test_capsule['uuid'],
                         actual_capsules[0].get('uuid'))

    @patch('zun.compute.api.API.container_show')
    @patch('zun.objects.Capsule.list')
    @patch('zun.objects.Container.get_by_uuid')
    def test_get_all_capsules_all_tenants(self,
                                          mock_container_get_by_uuid,
                                          mock_capsule_list,
                                          mock_container_show):
        test_container = utils.get_test_container()
        test_container_obj = objects.Container(self.context,
                                               **test_container)
        mock_container_get_by_uuid.return_value = test_container_obj

        test_capsule = utils.get_test_capsule()
        test_capsule_obj = objects.Capsule(self.context, **test_capsule)
        mock_capsule_list.return_value = [test_capsule_obj]
        mock_container_show.return_value = test_container_obj

        response = self.app.get('/capsules/?all_tenants=1')

        mock_capsule_list.assert_called_once_with(mock.ANY,
                                                  1000, None, 'id', 'asc',
                                                  filters=None)
        context = mock_capsule_list.call_args[0][0]
        self.assertIs(True, context.all_tenants)
        self.assertEqual(200, response.status_int)
        actual_capsules = response.json['capsules']
        self.assertEqual(1, len(actual_capsules))
        self.assertEqual(test_capsule['uuid'],
                         actual_capsules[0].get('uuid'))

    @patch('zun.objects.Capsule.list')
    @patch('zun.objects.Container.get_by_uuid')
    def test_get_all_capsules_with_exception(self,
                                             mock_container_get_by_uuid,
                                             mock_capsule_list):
        test_container = utils.get_test_container()
        test_container_obj = objects.Container(self.context,
                                               **test_container)
        mock_container_get_by_uuid.return_value = test_container_obj

        test_capsule = utils.get_test_capsule()
        test_capsule_obj = objects.Capsule(self.context, **test_capsule)
        mock_capsule_list.return_value = [test_capsule_obj]

        response = self.app.get('/capsules/')

        mock_capsule_list.assert_called_once_with(mock.ANY,
                                                  1000, None, 'id', 'asc',
                                                  filters=None)
        context = mock_capsule_list.call_args[0][0]
        self.assertIs(False, context.all_tenants)
        self.assertEqual(200, response.status_int)
        actual_capsules = response.json['capsules']
        self.assertEqual(1, len(actual_capsules))
        self.assertEqual(test_capsule['uuid'],
                         actual_capsules[0].get('uuid'))

    @patch('zun.compute.api.API.container_show')
    @patch('zun.objects.Capsule.list')
    @patch('zun.objects.Capsule.save')
    @patch('zun.objects.Container.get_by_uuid')
    def test_get_all_capsules_with_pagination_marker(
            self,
            mock_container_get_by_uuid,
            mock_capsule_save,
            mock_capsule_list,
            mock_container_show):
        test_container = utils.get_test_container()
        test_container_obj = objects.Container(self.context,
                                               **test_container)
        mock_container_get_by_uuid.return_value = test_container_obj
        capsule_list = []
        for id_ in range(4):
            test_capsule = utils.create_test_capsule(
                id=id_, uuid=uuidutils.generate_uuid(),
                name='capsule' + str(id_), context=self.context)
            capsule_list.append(objects.Capsule(self.context,
                                                **test_capsule))
        mock_capsule_list.return_value = capsule_list[-1:]
        mock_container_show.return_value = capsule_list[-1]
        mock_capsule_save.return_value = True

        response = self.app.get('/capsules/?limit=3&marker=%s'
                                % capsule_list[2].uuid)

        self.assertEqual(200, response.status_int)
        actual_capsules = response.json['capsules']

        self.assertEqual(1, len(actual_capsules))
        self.assertEqual(actual_capsules[-1].get('uuid'),
                         actual_capsules[0].get('uuid'))
