#    Copyright 2017 Arm Limited.
#
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

import mock

from testtools.matchers import HasLength
from zun import objects
from zun.tests.unit.db import base
from zun.tests.unit.db import utils


class TestCapsuleObject(base.DbTestCase):

    def setUp(self):
        super(TestCapsuleObject, self).setUp()
        self.fake_capsule = utils.get_test_capsule()

    def test_get_by_uuid(self):
        uuid = self.fake_capsule['uuid']
        with mock.patch.object(self.dbapi, 'get_capsule_by_uuid',
                               autospec=True) as mock_get_capsule:
            mock_get_capsule.return_value = self.fake_capsule
            capsule = objects.Capsule.get_by_uuid(self.context, uuid)
            mock_get_capsule.assert_called_once_with(self.context, uuid)
            self.assertEqual(self.context, capsule._context)

    def test_list(self):
        with mock.patch.object(self.dbapi, 'list_capsules',
                               autospec=True) as mock_get_list:
            mock_get_list.return_value = [self.fake_capsule]
            capsules = objects.Capsule.list(self.context)
            self.assertEqual(1, mock_get_list.call_count)
            self.assertThat(capsules, HasLength(1))
            self.assertIsInstance(capsules[0], objects.Capsule)
            self.assertEqual(self.context, capsules[0]._context)

    def test_list_with_filters(self):
        with mock.patch.object(self.dbapi, 'list_capsules',
                               autospec=True) as mock_get_list:
            mock_get_list.return_value = [self.fake_capsule]
            filt = {'status': 'Running'}
            capsules = objects.Capsule.list(self.context,
                                            filters=filt)
            self.assertEqual(1, mock_get_list.call_count)
            self.assertThat(capsules, HasLength(1))
            self.assertIsInstance(capsules[0], objects.Capsule)
            self.assertEqual(self.context, capsules[0]._context)
            mock_get_list.assert_called_once_with(self.context,
                                                  filters=filt,
                                                  limit=None, marker=None,
                                                  sort_key=None, sort_dir=None)

    def test_create(self):
        with mock.patch.object(self.dbapi, 'create_capsule',
                               autospec=True) as mock_create_capsule:
            self.fake_capsule.pop('containers')
            mock_create_capsule.return_value = self.fake_capsule
            capsule = objects.Capsule(self.context, **self.fake_capsule)
            capsule.create(self.context)
            mock_create_capsule.assert_called_once_with(self.context,
                                                        self.fake_capsule)
            self.assertEqual(self.context, capsule._context)

    def test_status_reason_in_fields(self):
        with mock.patch.object(self.dbapi, 'create_capsule',
                               autospec=True) as mock_create_capsule:
            self.fake_capsule.pop('containers')
            mock_create_capsule.return_value = self.fake_capsule
            capsule = objects.Capsule(self.context, **self.fake_capsule)
            self.assertTrue(hasattr(capsule, 'status_reason'))
            capsule.status_reason = "Docker Error happened"
            capsule.create(self.context)
            self.assertEqual(
                "Docker Error happened",
                mock_create_capsule.call_args_list[0][0][1]['status_reason'])

    def test_destroy(self):
        uuid = self.fake_capsule['uuid']
        with mock.patch.object(self.dbapi, 'get_capsule_by_uuid',
                               autospec=True) as mock_get_capsule:
            mock_get_capsule.return_value = self.fake_capsule
            with mock.patch.object(self.dbapi, 'destroy_capsule',
                                   autospec=True) as mock_destroy_capsule:
                capsule = objects.Capsule.get_by_uuid(self.context, uuid)
                capsule.destroy()
                mock_get_capsule.assert_called_once_with(self.context, uuid)
                mock_destroy_capsule.assert_called_once_with(None, uuid)
                self.assertEqual(self.context, capsule._context)

    def test_save(self):
        uuid = self.fake_capsule['uuid']
        with mock.patch.object(self.dbapi, 'get_capsule_by_uuid',
                               autospec=True) as mock_get_capsule:
            mock_get_capsule.return_value = self.fake_capsule
            with mock.patch.object(self.dbapi, 'update_capsule',
                                   autospec=True) as mock_update_capsule:
                capsule = objects.Capsule.get_by_uuid(self.context, uuid)
                capsule.meta_name = 'fake-meta-name-new'
                capsule.meta_labels = {'key3': 'val3', 'key4': 'val4'}
                capsule.save()
                mock_get_capsule.assert_called_once_with(self.context, uuid)
                mock_update_capsule.assert_called_once_with(
                    None, uuid,
                    {'meta_name': 'fake-meta-name-new',
                     'meta_labels': {'key3': 'val3', 'key4': 'val4'}})
                self.assertEqual(self.context, capsule._context)
