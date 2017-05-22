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


class TestZunServiceObject(base.DbTestCase):

    def setUp(self):
        super(TestZunServiceObject, self).setUp()
        self.fake_zun_service = utils.get_test_zun_service()

    def test_get_by_host_and_binary(self):
        with mock.patch.object(self.dbapi,
                               'get_zun_service',
                               autospec=True) as mock_get_zun_service:
            mock_get_zun_service.return_value = self.fake_zun_service
            ms = objects.ZunService.get_by_host_and_binary(self.context,
                                                           'fake-host',
                                                           'fake-bin')
            mock_get_zun_service.assert_called_once_with('fake-host',
                                                         'fake-bin')
            self.assertEqual(self.context, ms._context)

    def test_get_by_host_and_binary_no_service(self):
        with mock.patch.object(self.dbapi, 'create_zun_service',
                               autospec=True) as mock_get_zun_service:
            mock_get_zun_service.return_value = None
            ms = objects.ZunService.get_by_host_and_binary(self.context,
                                                           'fake-host',
                                                           'fake-bin')

            self.assertIsNone(ms)

    def test_list(self):
        with mock.patch.object(self.dbapi, 'list_zun_services',
                               autospec=True) as mock_get_list:
            mock_get_list.return_value = [self.fake_zun_service]
            services = objects.ZunService.list(self.context)
            self.assertEqual(1, mock_get_list.call_count)
            self.assertThat(services, HasLength(1))
            self.assertIsInstance(services[0], objects.ZunService)
            self.assertEqual(self.context, services[0]._context)

    def test_list_by_binary(self):
        with mock.patch.object(self.dbapi, 'list_zun_services_by_binary',
                               autospec=True) as mock_service_list:
            mock_service_list.return_value = [self.fake_zun_service]
            services = objects.ZunService.list_by_binary(self.context, 'bin')
            self.assertEqual(1, mock_service_list.call_count)
            self.assertThat(services, HasLength(1))
            self.assertIsInstance(services[0], objects.ZunService)
            self.assertEqual(self.context, services[0]._context)

    def test_create(self):
        with mock.patch.object(self.dbapi, 'create_zun_service',
                               autospec=True) as mock_create_zun_service:
            mock_create_zun_service.return_value = self.fake_zun_service
            ms_dict = {'host': 'fakehost', 'binary': 'fake-bin'}
            ms = objects.ZunService(self.context, **ms_dict)
            ms.create(self.context)
            mock_create_zun_service.assert_called_once_with(ms_dict)

    def test_destroy(self):
        with mock.patch.object(self.dbapi,
                               'get_zun_service',
                               autospec=True) as mock_get_zun_service:
            mock_get_zun_service.return_value = self.fake_zun_service
            with mock.patch.object(self.dbapi,
                                   'destroy_zun_service',
                                   autospec=True) as mock_destroy_ms:
                ms = objects.ZunService.get_by_host_and_binary(
                    self.context, 'fake-host', 'fake-bin')
                ms.destroy()
                mock_get_zun_service.assert_called_once_with(
                    'fake-host', 'fake-bin')
                mock_destroy_ms.assert_called_once_with(
                    self.fake_zun_service['host'],
                    self.fake_zun_service['binary'])
                self.assertEqual(self.context, ms._context)

    def test_save(self):
        with mock.patch.object(self.dbapi,
                               'get_zun_service',
                               autospec=True) as mock_get_zun_service:
            mock_get_zun_service.return_value = self.fake_zun_service
            with mock.patch.object(self.dbapi,
                                   'update_zun_service',
                                   autospec=True) as mock_update_ms:
                ms = objects.ZunService.get_by_host_and_binary(
                    self.context, 'fake-host', 'fake-bin')
                ms.disabled = True
                ms.save()
                mock_get_zun_service.assert_called_once_with(
                    'fake-host', 'fake-bin')
                mock_update_ms.assert_called_once_with(
                    self.fake_zun_service['host'],
                    self.fake_zun_service['binary'],
                    {'disabled': True})
                self.assertEqual(self.context, ms._context)

    def test_report_state_up(self):
        with mock.patch.object(self.dbapi,
                               'get_zun_service',
                               autospec=True) as mock_get_zun_service:
            mock_get_zun_service.return_value = self.fake_zun_service
            with mock.patch.object(self.dbapi,
                                   'update_zun_service',
                                   autospec=True) as mock_update_ms:
                ms = objects.ZunService.get_by_host_and_binary(
                    self.context, 'fake-host', 'fake-bin')
                last_report_count = self.fake_zun_service['report_count']
                ms.report_state_up()
                mock_get_zun_service.assert_called_once_with(
                    'fake-host', 'fake-bin')
                self.assertEqual(self.context, ms._context)
                mock_update_ms.assert_called_once_with(
                    self.fake_zun_service['host'],
                    self.fake_zun_service['binary'],
                    {'report_count': last_report_count + 1})

    def test_update(self):
        with mock.patch.object(self.dbapi,
                               'get_zun_service',
                               autospec=True) as mock_get_zun_service:
            mock_get_zun_service.return_value = self.fake_zun_service
            with mock.patch.object(self.dbapi,
                                   'update_zun_service',
                                   autospec=True) as mock_update_ms:
                ms = objects.ZunService.get_by_host_and_binary(
                    self.context, 'fake-host', 'fake-bin')
                kw = {'disabled': True, 'disabled_reason': 'abc'}
                ms.update(self.context, kw)
                mock_get_zun_service.assert_called_once_with(
                    'fake-host', 'fake-bin')
                mock_update_ms.assert_called_once_with(
                    self.fake_zun_service['host'],
                    self.fake_zun_service['binary'],
                    {'disabled': True,
                     'disabled_reason': 'abc'})
                self.assertEqual(self.context, ms._context)
