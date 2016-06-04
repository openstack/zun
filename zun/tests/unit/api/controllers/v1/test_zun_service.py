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

from zun.api.controllers.v1 import zun_services as zservice
from zun.tests import base
from zun.tests.unit.api import utils as apiutils


class TestZunServiceObject(base.BaseTestCase):

    def setUp(self):
        super(TestZunServiceObject, self).setUp()
        self.rpc_dict = apiutils.zservice_get_data()

    def test_msvc_obj_fields_filtering(self):
        """Test that it does filtering fields """
        self.rpc_dict['fake-key'] = 'fake-value'
        msvco = zservice.ZunService("up", **self.rpc_dict)
        self.assertNotIn('fake-key', msvco.fields)


class db_rec(object):

    def __init__(self, d):
        self.rec_as_dict = d

    def as_dict(self):
        return self.rec_as_dict


# TODO(hongbin): Enable the tests below
# class TestZunServiceController(api_base.FunctionalTest):

#    def setUp(self):
#        super(TestZunServiceController, self).setUp()

#    def test_empty(self):
#        response = self.get_json('/hservices')
#        self.assertEqual([], response['hservices'])

#    def _rpc_api_reply(self, count=1):
#        reclist = []
#        for i in range(count):
#            elem = apiutils.zservice_get_data()
#            elem['id'] = i + 1
#            rec = db_rec(elem)
#            reclist.append(rec)
#        return reclist

#    @mock.patch.object(objects.ZunService, 'list')
#    @mock.patch.object(servicegroup.ServiceGroup, 'service_is_up')
#    def test_get_one(self, svc_up, mock_list):
#        mock_list.return_value = self._rpc_api_reply()
#        svc_up.return_value = "up"

#        response = self.get_json('/hservices')
#        self.assertEqual(len(response['hservices']), 1)
#        self.assertEqual(response['hservices'][0]['id'], 1)

#    @mock.patch.object(objects.ZunService, 'list')
#    @mock.patch.object(servicegroup.ServiceGroup, 'service_is_up')
#    def test_get_many(self, svc_up, mock_list):
#        svc_num = 5
#        mock_list.return_value = self._rpc_api_reply(svc_num)
#        svc_up.return_value = "up"

#        response = self.get_json('/hservices')
#        self.assertEqual(len(response['hservices']), svc_num)
#        for i in range(svc_num):
#            elem = response['hservices'][i]
#            self.assertEqual(elem['id'], i + 1)
