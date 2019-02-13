# Copyright 2016 IBM, Corp.
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

from zun.common import exception
from zun.tests.unit.db import base
from zun.tests.unit.db import utils


class DbZunServiceTestCase(base.DbTestCase):

    def setUp(self):
        super(DbZunServiceTestCase, self).setUp()

    def test_create_zun_service(self):
        utils.create_test_zun_service()

    def test_create_zun_service_failure_for_dup(self):
        utils.create_test_zun_service()
        self.assertRaises(exception.ZunServiceAlreadyExists,
                          utils.create_test_zun_service)

    def test_get_zun_service(self):
        ms = utils.create_test_zun_service()
        res = self.dbapi.get_zun_service(
            ms['host'], ms['binary'])
        self.assertEqual(ms.id, res.id)

    def test_get_zun_service_failure(self):
        utils.create_test_zun_service()
        res = self.dbapi.get_zun_service(
            'fakehost1', 'fake-bin1')
        self.assertIsNone(res)

    def test_update_zun_service(self):
        ms = utils.create_test_zun_service()
        d2 = True
        update = {'disabled': d2}
        ms1 = self.dbapi.update_zun_service(ms['host'], ms['binary'], update)
        self.assertEqual(ms['id'], ms1['id'])
        self.assertEqual(d2, ms1['disabled'])
        res = self.dbapi.get_zun_service(
            'fakehost', 'fake-bin')
        self.assertEqual(ms1['id'], res['id'])
        self.assertEqual(d2, res['disabled'])

    def test_update_zun_service_failure(self):
        fake_update = {'fake_field': 'fake_value'}
        self.assertRaises(exception.ZunServiceNotFound,
                          self.dbapi.update_zun_service,
                          'fakehost1', 'fake-bin1', fake_update)

    def test_destroy_zun_service(self):
        ms = utils.create_test_zun_service()
        res = self.dbapi.get_zun_service(
            'fakehost', 'fake-bin')
        self.assertEqual(res['id'], ms['id'])
        self.dbapi.destroy_zun_service(ms['host'], ms['binary'])
        res = self.dbapi.get_zun_service(
            'fakehost', 'fake-bin')
        self.assertIsNone(res)

    def test_destroy_zun_service_failure(self):
        self.assertRaises(exception.ZunServiceNotFound,
                          self.dbapi.destroy_zun_service,
                          'fakehostsssss', 'fakessss-bin1')

    def test_list_zun_services(self):
        fake_ms_params = {
            'report_count': 1010,
            'host': 'FakeHost',
            'binary': 'FakeBin',
            'disabled': False,
            'disabled_reason': 'FakeReason'
        }
        utils.create_test_zun_service(**fake_ms_params)
        res = self.dbapi.list_zun_services()
        self.assertEqual(1, len(res))
        res = res[0]
        for k, v in fake_ms_params.items():
            self.assertEqual(res[k], v)

        fake_ms_params['binary'] = 'FakeBin1'
        fake_ms_params['disabled'] = True
        utils.create_test_zun_service(**fake_ms_params)
        res = self.dbapi.list_zun_services(filters={'disabled': True})
        self.assertEqual(1, len(res))
        res = res[0]
        for k, v in fake_ms_params.items():
            self.assertEqual(res[k], v)

    def test_list_zun_services_by_binary(self):
        fake_ms_params = {
            'report_count': 1010,
            'host': 'FakeHost',
            'binary': 'FakeBin',
            'disabled': False,
            'disabled_reason': 'FakeReason'
        }
        utils.create_test_zun_service(**fake_ms_params)
        res = self.dbapi.list_zun_services_by_binary(
            binary=fake_ms_params['binary'])
        self.assertEqual(1, len(res))
        res = res[0]
        for k, v in fake_ms_params.items():
            self.assertEqual(res[k], v)

        res = self.dbapi.list_zun_services_by_binary(binary='none')
        self.assertEqual(0, len(res))
