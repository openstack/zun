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

from unittest import mock
from unittest.mock import patch

from oslo_utils import uuidutils
from webtest.app import AppError

from zun.api.controllers.v1 import capsules
from zun.common import exception
from zun import objects
from zun.tests.unit.api import base as api_base
from zun.tests.unit.db import utils


class TestCheckCapsuleTemplate(api_base.FunctionalTest):
    def test_check_capsule_template(self):
        with self.assertRaisesRegex(
            exception.InvalidCapsuleTemplate, "kind fields need to "
                                              "be set as capsule or Capsule"):
            params = ({"kind": "test", "metadata": {},
                       "spec": {"containers": []}})
            capsules.check_capsule_template(params)

        with self.assertRaisesRegex(
                exception.InvalidCapsuleTemplate, "No Spec found"):
            params = ({"kind": "capsule", "metadata": {}})
            capsules.check_capsule_template(params)

        with self.assertRaisesRegex(
                exception.InvalidCapsuleTemplate,
                "No valid containers field"):
            params = ({"kind": "capsule", "metadata": {}, "spec": {}})
            capsules.check_capsule_template(params)

        params = ({"kind": "capsule", "metadata": {}, "spec": {
            "containers": [{"image": "test1"}], "restartPolicy": "Always",
        }})
        spec_content, tpl_json = capsules.check_capsule_template(params)
        self.assertEqual(spec_content["restart_policy"], "always")

    def test_check_capsule_template_unicode(self):
        with self.assertRaisesRegex(
                exception.SchemaValidationError,
                "Invalid input for field 'kind'"):
            params = (u'{"kind": "test", "metadata": {}, '
                      '"spec": {"containers": []}}')
            capsules.check_capsule_template(params)

        with self.assertRaisesRegex(
                exception.SchemaValidationError,
                "'spec' is a required property"):
            params = (u'{"kind": "capsule", "metadata": {}}')
            capsules.check_capsule_template(params)

        with self.assertRaisesRegex(
                exception.SchemaValidationError,
                "Invalid input for field 'spec'"):
            params = (u'{"kind": "capsule", "spec": {}, "metadata": {}}')
            capsules.check_capsule_template(params)

        params = (u'{"kind": "capsule", "metadata": {}, "spec": {'
                  u'"containers": [{"image": "test1"}],'
                  u'"restartPolicy": "Always"}}')
        spec_content, tpl_json = capsules.check_capsule_template(params)
        self.assertEqual(spec_content["restart_policy"], "always")


class TestCapsuleController(api_base.FunctionalTest):
    @patch('zun.compute.api.API.container_create')
    @patch('zun.network.neutron.NeutronAPI.get_available_network')
    def test_create_capsule(self, mock_neutron_get_network,
                            mock_container_create):
        params = ('{'
                  '"template": '
                  '{"kind": "capsule",'
                  ' "spec": {'
                  '  "containers":'
                  '  [{"env": {"ROOT_PASSWORD": "foo0"}, '
                  '    "name": "test-container", '
                  '    "image": "test",'
                  '    "resources": '
                  '    {"requests": {"cpu": 1, "memory": 1024}}'
                  '  }]'
                  ' }, '
                  ' "metadata": {"labels": {"foo0": "bar0", "foo1": "bar1"},'
                  '              "name": "capsule-example"}'
                  ' }'
                  '}')
        response = self.post('/v1/capsules/',
                             params=params,
                             content_type='application/json')
        return_value = response.json
        expected_meta_name = "capsule-example"
        expected_meta_labels = {"foo0": "bar0", "foo1": "bar1"}
        expected_memory = '1024'
        expected_cpu = 1.0
        self.assertEqual(return_value["name"], expected_meta_name)
        self.assertEqual(return_value["labels"], expected_meta_labels)
        self.assertEqual(return_value["memory"], expected_memory)
        self.assertEqual(return_value["cpu"], expected_cpu)
        self.assertEqual(202, response.status_int)
        self.assertTrue(mock_container_create.called)
        self.assertTrue(mock_neutron_get_network.called)

    @patch('zun.compute.api.API.container_create')
    @patch('zun.network.neutron.NeutronAPI.get_available_network')
    def test_create_capsule_two_containers(self, mock_neutron_get_network,
                                           mock_container_create):
        params = ('{'
                  '"template": '
                  '{"kind": "capsule",'
                  ' "spec": {'
                  '  "containers":'
                  '  [{"image": "test", "resources": '
                  '    {"requests": {"cpu": 1, "memory": 1024}}}, '
                  '   {"image": "test1", "resources": '
                  '    {"requests": {"cpu": 1, "memory": 1024}}}]'
                  ' }, '
                  ' "metadata": {"labels": {"foo0": "bar0"},'
                  '              "name": "capsule-example"}'
                  ' }'
                  '}')
        response = self.post('/v1/capsules/',
                             params=params,
                             content_type='application/json')
        return_value = response.json
        expected_meta_name = "capsule-example"
        expected_meta_labels = {"foo0": "bar0"}
        expected_memory = '2048'
        expected_cpu = 2.0
        self.assertEqual(return_value["name"],
                         expected_meta_name)
        self.assertEqual(return_value["labels"],
                         expected_meta_labels)
        self.assertEqual(return_value["memory"], expected_memory)
        self.assertEqual(return_value["cpu"], expected_cpu)
        self.assertEqual(202, response.status_int)
        self.assertTrue(mock_container_create.called)
        self.assertTrue(mock_neutron_get_network.called)

    @patch('zun.compute.api.API.container_create')
    @patch('zun.api.controllers.v1.capsules.check_capsule_template')
    def test_create_capsule_wrong_kind_set(self, mock_check_template,
                                           mock_container_create):
        params = ('{"template": {"kind": "test",'
                  '"spec": {"containers":'
                  '[{"environment": {"ROOT_PASSWORD": "foo0"}, '
                  '"image": "test1", "resources": '
                  '{"requests": {"cpu": 1, "memory": 1024}}}]}, '
                  '"metadata": {"labels": {"foo0": "bar0"}, '
                  '"name": "capsule-example"}}}')
        mock_check_template.side_effect = exception.InvalidCapsuleTemplate(
            "kind fields need to be set as capsule or Capsule")
        response = self.post_json('/capsules/', params, expect_errors=True)
        self.assertEqual(400, response.status_int)
        self.assertFalse(mock_container_create.called)

    @patch('zun.compute.api.API.container_create')
    @patch('zun.api.controllers.v1.capsules.check_capsule_template')
    def test_create_capsule_less_than_one_container(self, mock_check_template,
                                                    mock_container_create):
        params = ('{"template": {"kind": "capsule",'
                  '"spec": {container:[]}, '
                  '"metadata": {"labels": {"foo0": "bar0"}, '
                  '"name": "capsule-example"}}}')
        mock_check_template.side_effect = exception.InvalidCapsuleTemplate(
            "Capsule need to have one container at least")
        response = self.post_json('/capsules/', params, expect_errors=True)
        self.assertEqual(400, response.status_int)
        self.assertFalse(mock_container_create.called)

    @patch('zun.compute.api.API.container_create')
    @patch('zun.api.controllers.v1.capsules.check_capsule_template')
    def test_create_capsule_no_container_field(self, mock_check_template,
                                               mock_container_create):
        params = ('{"template": {"kind": "capsule",'
                  '"spec": {}, '
                  '"metadata": {"labels": {"foo0": "bar0"}, '
                  '"name": "capsule-example"}}}')
        mock_check_template.side_effect = exception.InvalidCapsuleTemplate(
            "Capsule need to have one container at least")
        self.assertRaises(AppError, self.post, '/capsules/',
                          params=params, content_type='application/json')
        self.assertFalse(mock_container_create.called)

    @patch('zun.compute.api.API.container_create')
    @patch('zun.api.controllers.v1.capsules.check_capsule_template')
    def test_create_capsule_no_container_image(self, mock_check_template,
                                               mock_container_create):
        params = ('{"template": {"kind": "capsule",'
                  '"spec": {container:[{"env": '
                  '{"ROOT_PASSWORD": "foo1"}]}, '
                  '"metadata": {"labels": {"foo0": "bar0"}, '
                  '"name": "capsule-example"}}}')
        mock_check_template.side_effect = exception.InvalidCapsuleTemplate(
            "Container image is needed")
        self.assertRaises(AppError, self.post, '/v1/capsules/',
                          params=params, content_type='application/json')
        self.assertFalse(mock_container_create.called)

    @patch('zun.compute.api.API.container_create')
    @patch('zun.network.neutron.NeutronAPI.get_available_network')
    def test_create_capsule_with_init_containers(self,
                                                 mock_neutron_get_network,
                                                 mock_container_create):
        params = ('{'
                  '"template": '
                  '{"kind": "capsule",'
                  ' "spec": {'
                  '  "initContainers":'
                  '  [{"image": "test-init", "resources": '
                  '    {"requests": {"cpu": 1, "memory": 1024}}}],'
                  '  "containers":'
                  '  [{"image": "test", "resources": '
                  '    {"requests": {"cpu": 1, "memory": 1024}}}, '
                  '   {"image": "test1", "resources": '
                  '    {"requests": {"cpu": 1, "memory": 1024}}}]'
                  ' }, '
                  ' "metadata": {"labels": {"foo0": "bar0"},'
                  '              "name": "capsule-example"}'
                  ' }'
                  '}')
        response = self.post('/v1/capsules/',
                             params=params,
                             content_type='application/json')
        return_value = response.json
        expected_meta_name = "capsule-example"
        expected_meta_labels = {"foo0": "bar0"}
        expected_memory = '2048'
        expected_cpu = 2.0

        self.assertEqual(return_value["name"],
                         expected_meta_name)
        self.assertEqual(return_value["labels"],
                         expected_meta_labels)
        self.assertEqual(return_value["memory"], expected_memory)
        self.assertEqual(return_value["cpu"], expected_cpu)
        self.assertEqual(202, response.status_int)
        self.assertTrue(mock_container_create.called)
        self.assertTrue(mock_neutron_get_network.called)

    @patch('zun.compute.api.API.container_create')
    @patch('zun.network.neutron.NeutronAPI.get_available_network')
    def test_create_capsule_with_two_init_containers(self,
                                                     mock_neutron_get_network,
                                                     mock_container_create):
        params = ('{'
                  '"template": '
                  '{"kind": "capsule",'
                  ' "spec": {'
                  '  "containers":'
                  '  [{"image": "test", "resources": '
                  '    {"requests": {"cpu": 1, "memory": 1024}}}],'
                  '  "initContainers":'
                  '  [{"image": "init-test", "resources": '
                  '    {"requests": {"cpu": 1, "memory": 1024}}}, '
                  '   {"image": "init-test1", "resources": '
                  '    {"requests": {"cpu": 1, "memory": 1024}}}]'
                  ' }, '
                  ' "metadata": {"labels": {"foo0": "bar0"},'
                  '              "name": "capsule-example"}'
                  ' }'
                  '}')
        response = self.post('/v1/capsules/',
                             params=params,
                             content_type='application/json')
        return_value = response.json
        expected_meta_name = "capsule-example"
        expected_meta_labels = {"foo0": "bar0"}
        expected_memory = '1024'
        expected_cpu = 1.0
        self.assertEqual(return_value["name"],
                         expected_meta_name)
        self.assertEqual(return_value["labels"],
                         expected_meta_labels)
        self.assertEqual(return_value["memory"], expected_memory)
        self.assertEqual(return_value["cpu"], expected_cpu)
        self.assertEqual(202, response.status_int)
        self.assertTrue(mock_container_create.called)
        self.assertTrue(mock_neutron_get_network.called)

    @patch('zun.volume.cinder_api.CinderAPI.ensure_volume_usable')
    @patch('zun.volume.cinder_api.CinderAPI.create_volume')
    @patch('zun.compute.api.API.container_create')
    @patch('zun.network.neutron.NeutronAPI.get_available_network')
    def test_create_capsule_with_create_new_volume(self,
                                                   mock_neutron_get_network,
                                                   mock_container_create,
                                                   mock_create_volume,
                                                   mock_ensure_volume_usable):
        fake_volume_id = '3259309d-659c-4e20-b354-ee712e64b3b2'
        fake_volume = mock.Mock(id=fake_volume_id)
        mock_create_volume.return_value = fake_volume
        params = ('{'
                  '"template":'
                  '{"kind": "capsule",'
                  ' "spec":'
                  ' {"containers":'
                  '  [{"env": {"ROOT_PASSWORD": "foo0"}, '
                  '    "image": "test", "resources": '
                  '    {"requests": {"cpu": 1, "memory": 1024}},'
                  '     "volumeMounts": [{"name": "volume1", '
                  '                       "mountPath": "/data1"}]'
                  '   }'
                  '  ],'
                  '  "volumes":'
                  '  [{"name": "volume1",'
                  '    "cinder": {"size": 3, "autoRemove": "True"}'
                  '  }]'
                  ' }, '
                  ' "metadata": {"labels": '
                  '             {"foo0": "bar0", "foo1": "bar1"},'
                  '              "name": "capsule-example"}'
                  ' }'
                  '}')
        response = self.post('/v1/capsules/',
                             params=params,
                             content_type='application/json')
        return_value = response.json
        expected_meta_name = "capsule-example"
        expected_meta_labels = {"foo0": "bar0", "foo1": "bar1"}
        expected_memory = '1024'
        expected_cpu = 1.0
        self.assertEqual(return_value["name"], expected_meta_name)
        self.assertEqual(return_value["labels"], expected_meta_labels)
        self.assertEqual(return_value["memory"], expected_memory)
        self.assertEqual(return_value["cpu"], expected_cpu)
        self.assertEqual(202, response.status_int)
        self.assertTrue(mock_container_create.called)
        self.assertTrue(mock_neutron_get_network.called)
        self.assertTrue(mock_create_volume.called)

    @patch('zun.volume.cinder_api.CinderAPI.ensure_volume_usable')
    @patch('zun.volume.cinder_api.CinderAPI.search_volume')
    @patch('zun.compute.api.API.container_create')
    @patch('zun.network.neutron.NeutronAPI.get_available_network')
    def test_create_capsule_with_existed_volume(self, mock_neutron_get_network,
                                                mock_container_create,
                                                mock_search_volume,
                                                mock_ensure_volume_usable):
        fake_volume_id = '3259309d-659c-4e20-b354-ee712e64b3b2'
        fake_volume = mock.Mock(id=fake_volume_id)
        mock_search_volume.return_value = fake_volume
        params = ('{'
                  '"template":'
                  '{"kind": "capsule",'
                  ' "spec":'
                  ' {"containers":'
                  '  [{"env": {"ROOT_PASSWORD": "foo0"}, '
                  '    "image": "test", "resources": '
                  '    {"requests": {"cpu": 1, "memory": 1024}},'
                  '     "volumeMounts": [{"name": "volume1", '
                  '                       "mountPath": "/data1"}]'
                  '   }'
                  '  ],'
                  '  "volumes":'
                  '  [{"name": "volume1",'
                  '    "cinder": {"volumeID": '
                  '    "3259309d-659c-4e20-b354-ee712e64b3b2"}'
                  '  }]'
                  ' }, '
                  ' "metadata": {"labels": '
                  '              {"foo0": "bar0", "foo1": "bar1"},'
                  '              "name": "capsule-example"}'
                  ' }'
                  '}')
        response = self.post('/v1/capsules/',
                             params=params,
                             content_type='application/json')
        return_value = response.json
        expected_meta_name = "capsule-example"
        expected_meta_labels = {"foo0": "bar0", "foo1": "bar1"}
        expected_memory = '1024'
        expected_cpu = 1.0
        self.assertEqual(return_value["name"], expected_meta_name)
        self.assertEqual(return_value["labels"], expected_meta_labels)
        self.assertEqual(return_value["memory"], expected_memory)
        self.assertEqual(return_value["cpu"], expected_cpu)
        self.assertEqual(202, response.status_int)
        self.assertTrue(mock_container_create.called)
        self.assertTrue(mock_neutron_get_network.called)
        self.assertTrue(mock_ensure_volume_usable.called)
        self.assertTrue(mock_search_volume.called)

    @patch('zun.volume.cinder_api.CinderAPI.create_volume')
    @patch('zun.volume.cinder_api.CinderAPI.ensure_volume_usable')
    @patch('zun.volume.cinder_api.CinderAPI.search_volume')
    @patch('zun.compute.api.API.container_create')
    @patch('zun.network.neutron.NeutronAPI.get_available_network')
    def test_create_capsule_with_two_volumes(self, mock_neutron_get_network,
                                             mock_container_create,
                                             mock_search_volume,
                                             mock_ensure_volume_usable,
                                             mock_create_volume):
        fake_volume_id1 = '3259309d-659c-4e20-b354-ee712e64b3b2'
        fake_volume = mock.Mock(id=fake_volume_id1)
        mock_search_volume.return_value = fake_volume
        fake_volume_id2 = 'ef770cfb-349a-483a-97f6-b86e46e344b8'
        fake_volume = mock.Mock(id=fake_volume_id2)
        mock_create_volume.return_value = fake_volume
        params = ('{'
                  '"template":'
                  '{"kind": "capsule",'
                  ' "spec":'
                  ' {"containers":'
                  '  [{"env": {"ROOT_PASSWORD": "foo0"}, '
                  '    "image": "test", "resources": '
                  '    {"requests": {"cpu": 1, "memory": 1024}},'
                  '     "volumeMounts": [{"name": "volume1", '
                  '                       "mountPath": "/data1"},'
                  '                       {"name": "volume2", '
                  '                       "mountPath": "/data2"}]'
                  '   }'
                  '  ],'
                  '  "volumes":'
                  '  [{"name": "volume1",'
                  '    "cinder": {"volumeID": '
                  '    "3259309d-659c-4e20-b354-ee712e64b3b2"}},'
                  '   {"name": "volume2",'
                  '    "cinder": {"size": 3, "autoRemove": "True"}'
                  '  }]'
                  ' }, '
                  ' "metadata": {"labels": {"foo0": "bar0", "foo1": "bar1"},'
                  '              "name": "capsule-example"}'
                  ' }'
                  '}')
        response = self.post('/v1/capsules/',
                             params=params,
                             content_type='application/json')
        return_value = response.json
        expected_meta_name = "capsule-example"
        expected_meta_labels = {"foo0": "bar0", "foo1": "bar1"}
        expected_memory = '1024'
        expected_cpu = 1.0
        self.assertEqual(return_value["name"], expected_meta_name)
        self.assertEqual(return_value["labels"], expected_meta_labels)
        self.assertEqual(return_value["memory"], expected_memory)
        self.assertEqual(return_value["cpu"], expected_cpu)
        self.assertEqual(202, response.status_int)
        self.assertTrue(mock_container_create.called)
        self.assertTrue(mock_neutron_get_network.called)
        self.assertTrue(mock_ensure_volume_usable.called)
        self.assertTrue(mock_search_volume.called)
        self.assertTrue(mock_create_volume.called)

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

        test_capsule = utils.create_test_container(context=self.context)
        test_capsule_obj = objects.Capsule(self.context, **test_capsule)
        mock_capsule_get_by_uuid.return_value = test_capsule_obj

        response = self.get('/v1/capsules/%s/' % test_capsule['uuid'])

        context = mock_capsule_get_by_uuid.call_args[0][0]
        self.assertIs(False, context.all_projects)
        self.assertEqual(200, response.status_int)
        self.assertEqual(test_capsule['uuid'],
                         response.json['uuid'])

    @patch('zun.compute.api.API.container_show')
    @patch('zun.objects.Capsule.get_by_uuid')
    @patch('zun.objects.Container.get_by_uuid')
    def test_get_one_by_uuid_all_projects(self, mock_container_get_by_uuid,
                                          mock_capsule_get_by_uuid,
                                          mock_container_show):
        test_container = utils.get_test_container()
        test_container_obj = objects.Container(self.context, **test_container)
        mock_container_get_by_uuid.return_value = test_container_obj
        mock_container_show.return_value = test_container_obj

        test_capsule = utils.create_test_container(context=self.context)
        test_capsule_obj = objects.Capsule(self.context, **test_capsule)
        mock_capsule_get_by_uuid.return_value = test_capsule_obj

        response = self.get('/capsules/%s/?all_projects=1' %
                            test_capsule['uuid'])

        context = mock_capsule_get_by_uuid.call_args[0][0]
        self.assertIs(False, context.all_projects)
        self.assertEqual(200, response.status_int)
        self.assertEqual(test_capsule['uuid'],
                         response.json['uuid'])

    @patch('zun.compute.api.API.container_delete')
    @patch('zun.objects.Capsule.get_by_uuid')
    @patch('zun.objects.Capsule.save')
    def test_delete_capsule_by_uuid(self, mock_capsule_save,
                                    mock_capsule_get_by_uuid,
                                    mock_capsule_delete):
        test_capsule = utils.create_test_container(context=self.context)
        test_capsule_obj = objects.Capsule(self.context,
                                           **test_capsule)
        mock_capsule_get_by_uuid.return_value = test_capsule_obj
        mock_capsule_save.return_value = True
        mock_capsule_delete.return_value = True

        capsule_uuid = test_capsule.get('uuid')
        response = self.app.delete('/v1/capsules/%s' % capsule_uuid)

        self.assertTrue(mock_capsule_delete.called)
        self.assertEqual(204, response.status_int)
        context = mock_capsule_save.call_args[0][0]
        self.assertIs(False, context.all_projects)

    @patch('zun.common.policy.enforce')
    @patch('zun.compute.api.API.container_delete')
    @patch('zun.objects.Capsule.get_by_uuid')
    @patch('zun.objects.Capsule.save')
    def test_delete_capsule_by_uuid_all_projects(self,
                                                 mock_capsule_save,
                                                 mock_capsule_get_by_uuid,
                                                 mock_capsule_delete,
                                                 mock_policy):
        mock_policy.return_value = True
        test_capsule = utils.create_test_container(context=self.context)
        test_capsule_obj = objects.Capsule(self.context,
                                           **test_capsule)
        mock_capsule_get_by_uuid.return_value = test_capsule_obj
        mock_capsule_save.return_value = True
        mock_capsule_delete.return_value = True

        capsule_uuid = test_capsule.get('uuid')
        response = self.app.delete(
            '/v1/capsules/%s/?all_projects=1' % capsule_uuid)

        self.assertTrue(mock_capsule_delete.called)
        self.assertEqual(204, response.status_int)
        context = mock_capsule_save.call_args[0][0]
        self.assertIs(True, context.all_projects)

    def test_delete_capsule_with_uuid_not_found(self):
        uuid = uuidutils.generate_uuid()
        self.assertRaises(AppError, self.app.delete,
                          '/capsules/%s' % uuid)

    @patch('zun.compute.api.API.container_delete')
    @patch('zun.objects.Capsule.get_by_name')
    @patch('zun.objects.Capsule.save')
    def test_delete_capsule_by_name(self, mock_capsule_save,
                                    mock_capsule_get_by_name,
                                    mock_capsule_delete):
        test_capsule = utils.create_test_container(context=self.context)
        test_capsule_obj = objects.Capsule(self.context,
                                           **test_capsule)
        mock_capsule_get_by_name.return_value = test_capsule_obj
        mock_capsule_save.return_value = True
        mock_capsule_delete.return_value = True

        capsule_name = test_capsule.get('name')
        response = self.app.delete('/v1/capsules/%s/' %
                                   capsule_name)

        self.assertTrue(mock_capsule_delete.called)
        self.assertEqual(204, response.status_int)
        context = mock_capsule_save.call_args[0][0]
        self.assertIs(False, context.all_projects)

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

        test_capsule = utils.create_test_container(context=self.context)
        test_capsule_obj = objects.Capsule(self.context, **test_capsule)
        mock_capsule_list.return_value = [test_capsule_obj]
        mock_container_show.return_value = test_container_obj

        response = self.app.get('/v1/capsules/')

        mock_capsule_list.assert_called_once_with(mock.ANY,
                                                  1000, None, 'id', 'asc',
                                                  filters=None)
        context = mock_capsule_list.call_args[0][0]
        self.assertIs(False, context.all_projects)
        self.assertEqual(200, response.status_int)
        actual_capsules = response.json['capsules']
        self.assertEqual(1, len(actual_capsules))
        self.assertEqual(test_capsule['uuid'],
                         actual_capsules[0].get('uuid'))

    @patch('zun.compute.api.API.container_show')
    @patch('zun.objects.Capsule.list')
    @patch('zun.objects.Container.get_by_uuid')
    def test_get_all_capsules_all_projects(self,
                                           mock_container_get_by_uuid,
                                           mock_capsule_list,
                                           mock_container_show):
        test_container = utils.get_test_container()
        test_container_obj = objects.Container(self.context,
                                               **test_container)
        mock_container_get_by_uuid.return_value = test_container_obj

        test_capsule = utils.create_test_container(context=self.context)
        test_capsule_obj = objects.Capsule(self.context, **test_capsule)
        mock_capsule_list.return_value = [test_capsule_obj]
        mock_container_show.return_value = test_container_obj

        response = self.app.get('/v1/capsules/?all_projects=1')

        mock_capsule_list.assert_called_once_with(mock.ANY,
                                                  1000, None, 'id', 'asc',
                                                  filters=None)
        context = mock_capsule_list.call_args[0][0]
        self.assertIs(True, context.all_projects)
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

        test_capsule = utils.create_test_container(context=self.context)
        test_capsule_obj = objects.Capsule(self.context, **test_capsule)
        mock_capsule_list.return_value = [test_capsule_obj]

        response = self.app.get('/v1/capsules/')

        mock_capsule_list.assert_called_once_with(mock.ANY,
                                                  1000, None, 'id', 'asc',
                                                  filters=None)
        context = mock_capsule_list.call_args[0][0]
        self.assertIs(False, context.all_projects)
        self.assertEqual(200, response.status_int)
        actual_capsules = response.json['capsules']
        self.assertEqual(1, len(actual_capsules))
        self.assertEqual(test_capsule['uuid'],
                         actual_capsules[0].get('uuid'))

    @patch('zun.compute.api.API.container_show')
    @patch('zun.objects.Capsule.list')
    @patch('zun.objects.Capsule.save')
    @patch('zun.objects.Capsule.get_by_uuid')
    def test_get_all_capsules_with_pagination_marker(
            self,
            mock_container_get_by_uuid,
            mock_capsule_save,
            mock_capsule_list,
            mock_capsule_show):
        test_container = utils.get_test_container()
        test_container_obj = objects.Container(self.context,
                                               **test_container)
        mock_container_get_by_uuid.return_value = test_container_obj
        capsule_list = []
        for id_ in range(4):
            test_capsule = utils.create_test_container(
                id=id_, uuid=uuidutils.generate_uuid(),
                name='capsule' + str(id_), context=self.context)
            capsule_list.append(objects.Capsule(self.context,
                                                **test_capsule))
        mock_capsule_list.return_value = capsule_list[-1:]
        mock_capsule_show.return_value = capsule_list[-1]
        mock_capsule_save.return_value = True

        response = self.app.get('/v1/capsules/?limit=3&marker=%s'
                                % capsule_list[2].uuid)

        self.assertEqual(200, response.status_int)
        actual_capsules = response.json['capsules']

        self.assertEqual(1, len(actual_capsules))
        self.assertEqual(actual_capsules[-1].get('uuid'),
                         actual_capsules[0].get('uuid'))
