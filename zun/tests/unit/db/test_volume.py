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

from zun.common import exception
import zun.conf
from zun.db import api as dbapi
from zun.tests.unit.db import base
from zun.tests.unit.db import utils

CONF = zun.conf.CONF


class DbVolumeTestCase(base.DbTestCase):

    def setUp(self):
        super(DbVolumeTestCase, self).setUp()

    def test_create_volume(self):
        utils.create_test_volume(context=self.context)

    def test_create_volume_already_exists(self):
        utils.create_test_volume(context=self.context,
                                 uuid='123')
        with self.assertRaisesRegex(exception.VolumeAlreadyExists,
                                    'A volume with UUID 123.*'):
            utils.create_test_volume(context=self.context,
                                     uuid='123')

    def test_get_volume_by_id(self):
        volume = utils.create_test_volume(context=self.context)
        res = dbapi.get_volume_by_id(self.context, volume.id)
        self.assertEqual(volume.id, res.id)
        self.assertEqual(volume.uuid, res.uuid)

    def test_get_volume_that_does_not_exist(self):
        self.assertRaises(exception.VolumeNotFound,
                          dbapi.get_volume_by_id,
                          self.context,
                          134251)

    def test_destroy_volume(self):
        volume = utils.create_test_volume(context=self.context)
        dbapi.destroy_volume(self.context, volume.id)
        self.assertRaises(exception.VolumeNotFound,
                          dbapi.get_volume_by_id,
                          self.context, volume.id)

    def test_destroy_volume_that_does_not_exist(self):
        self.assertRaises(exception.VolumeNotFound,
                          dbapi.destroy_volume, self.context,
                          134251)

    def test_update_volume(self):
        volume = utils.create_test_volume(context=self.context)
        old_conn_info = volume.connection_info
        new_conn_info = 'new-conn-info'
        self.assertNotEqual(old_conn_info, new_conn_info)

        res = dbapi.update_volume(self.context, volume.id,
                                  {'connection_info': new_conn_info})
        self.assertEqual(new_conn_info, res.connection_info)

    def test_update_volume_not_found(self):
        new_conn_info = 'new-conn-info'
        self.assertRaises(exception.VolumeNotFound,
                          dbapi.update_volume, self.context,
                          134251,
                          {'connection_info': new_conn_info})

    def test_update_volume_uuid(self):
        volume = utils.create_test_volume(context=self.context)
        self.assertRaises(exception.InvalidParameterValue,
                          dbapi.update_volume, self.context,
                          volume.id, {'uuid': ''})
