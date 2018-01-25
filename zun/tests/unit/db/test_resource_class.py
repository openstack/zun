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

"""Tests for manipulating resource classes via the DB API"""
import mock

import etcd
from etcd import Client as etcd_client
from oslo_config import cfg
from oslo_serialization import jsonutils as json
from oslo_utils import uuidutils
import six

from zun.common import exception
import zun.conf
from zun.db import api as dbapi
from zun.db.etcd import api as etcd_api
from zun.tests.unit.db import base
from zun.tests.unit.db import utils
from zun.tests.unit.db.utils import FakeEtcdMultipleResult
from zun.tests.unit.db.utils import FakeEtcdResult

CONF = zun.conf.CONF


class DbResourceClassTestCase(base.DbTestCase):

    def setUp(self):
        super(DbResourceClassTestCase, self).setUp()

    def test_create_resource_class(self):
        utils.create_test_resource_class(context=self.context)

    def test_create_resource_class_already_exists(self):
        utils.create_test_resource_class(
            context=self.context, uuid='123')
        with self.assertRaisesRegex(exception.ResourceClassAlreadyExists,
                                    'A resource class with uuid 123.*'):
            utils.create_test_resource_class(
                context=self.context, uuid='123')

    def test_get_resource_class_by_uuid(self):
        resource = utils.create_test_resource_class(context=self.context)
        res = dbapi.get_resource_class(self.context, resource.uuid)
        self.assertEqual(resource.uuid, res.uuid)
        self.assertEqual(resource.name, res.name)

    def test_get_resource_class_by_name(self):
        resource = utils.create_test_resource_class(context=self.context)
        res = dbapi.get_resource_class(self.context, resource.name)
        self.assertEqual(resource.id, res.id)
        self.assertEqual(resource.name, res.name)

    def test_get_resource_class_that_does_not_exist(self):
        self.assertRaises(exception.ResourceClassNotFound,
                          dbapi.get_resource_class,
                          self.context, uuidutils.generate_uuid())

    def test_list_resource_classes(self):
        names = []
        for i in range(1, 6):
            resource = utils.create_test_resource_class(
                context=self.context,
                uuid=uuidutils.generate_uuid(),
                name='class' + str(i))
            names.append(six.text_type(resource['name']))
        res = dbapi.list_resource_classes(self.context)
        res_names = [r.name for r in res]
        self.assertEqual(sorted(names), sorted(res_names))

    def test_list_resource_classes_sorted(self):
        names = []
        for i in range(5):
            resource = utils.create_test_resource_class(
                context=self.context,
                uuid=uuidutils.generate_uuid(),
                name='class' + str(i))
            names.append(six.text_type(resource.name))
        res = dbapi.list_resource_classes(self.context, sort_key='name')
        res_names = [r.name for r in res]
        self.assertEqual(sorted(names), res_names)

        self.assertRaises(exception.InvalidParameterValue,
                          dbapi.list_resource_classes,
                          self.context,
                          sort_key='foo')

    def test_destroy_resource_class(self):
        resource = utils.create_test_resource_class(context=self.context)
        dbapi.destroy_resource_class(self.context, resource.id)
        self.assertRaises(exception.ResourceClassNotFound,
                          dbapi.get_resource_class,
                          self.context, resource.id)

    def test_destroy_resource_class_that_does_not_exist(self):
        bad_id = 1111111
        self.assertRaises(exception.ResourceClassNotFound,
                          dbapi.destroy_resource_class, self.context,
                          bad_id)

    def test_update_resource_class(self):
        resource = utils.create_test_resource_class(context=self.context)
        old_name = resource.name
        new_name = 'new-name'
        self.assertNotEqual(old_name, new_name)

        res = dbapi.update_resource_class(
            self.context, resource.id, {'name': new_name})
        self.assertEqual(new_name, res.name)

    def test_update_resource_class_not_found(self):
        bad_id = 1111111
        new_name = 'new-name'
        self.assertRaises(exception.ResourceClassNotFound,
                          dbapi.update_resource_class, self.context,
                          bad_id, {'name': new_name})


class EtcdDbResourceClassTestCase(base.DbTestCase):

    def setUp(self):
        cfg.CONF.set_override('backend', 'etcd', 'database')
        super(EtcdDbResourceClassTestCase, self).setUp()

    @mock.patch.object(etcd_client, 'read')
    @mock.patch.object(etcd_client, 'write')
    def test_create_resource_class(self, mock_write, mock_read):
        mock_read.side_effect = etcd.EtcdKeyNotFound
        utils.create_test_resource_class(context=self.context)

    @mock.patch.object(etcd_client, 'read')
    @mock.patch.object(etcd_client, 'write')
    def test_create_resource_class_already_exists(self, mock_write,
                                                  mock_read):
        mock_read.side_effect = etcd.EtcdKeyNotFound
        utils.create_test_resource_class(context=self.context, name='123')
        mock_read.side_effect = lambda *args: None
        self.assertRaises(exception.ResourceExists,
                          utils.create_test_resource_class,
                          context=self.context, name='123')

    @mock.patch.object(etcd_client, 'read')
    @mock.patch.object(etcd_client, 'write')
    @mock.patch.object(dbapi, "_get_dbdriver_instance")
    def test_get_resource_class_by_uuid(self, mock_db_inst,
                                        mock_write, mock_read):
        mock_db_inst.return_value = etcd_api.get_backend()
        mock_read.side_effect = etcd.EtcdKeyNotFound
        resource_class = utils.create_test_resource_class(
            context=self.context)
        mock_read.side_effect = lambda *args: FakeEtcdResult(
            resource_class.as_dict())
        res = dbapi.get_resource_class(self.context, resource_class.uuid)
        self.assertEqual(resource_class.uuid, res.uuid)
        self.assertEqual(resource_class.name, res.name)

    @mock.patch.object(etcd_client, 'read')
    @mock.patch.object(etcd_client, 'write')
    @mock.patch.object(dbapi, "_get_dbdriver_instance")
    def test_get_resource_class_by_name(self, mock_db_inst,
                                        mock_write, mock_read):
        mock_db_inst.return_value = etcd_api.get_backend()
        mock_read.side_effect = etcd.EtcdKeyNotFound
        rcs = utils.create_test_resource_class(context=self.context)
        mock_read.side_effect = lambda *args: FakeEtcdMultipleResult(
            [rcs.as_dict()])
        res = dbapi.get_resource_class(self.context, rcs.name)
        self.assertEqual(rcs.uuid, res.uuid)

    @mock.patch.object(etcd_client, 'read')
    def test_get_resource_class_that_does_not_exist(self, mock_read):
        mock_read.side_effect = etcd.EtcdKeyNotFound
        self.assertRaises(exception.ResourceClassNotFound,
                          dbapi.get_resource_class,
                          self.context, 'fake-ident')

    @mock.patch.object(etcd_client, 'read')
    @mock.patch.object(etcd_client, 'write')
    @mock.patch.object(dbapi, "_get_dbdriver_instance")
    def test_list_resource_classes(self, mock_ins, mock_write, mock_read):
        names = []
        resource_classes = []
        mock_ins.return_value = etcd_api.get_backend()
        mock_read.side_effect = etcd.EtcdKeyNotFound
        for i in range(1, 6):
            res_class = utils.create_test_resource_class(
                context=self.context, name='class' + str(i))
            resource_classes.append(res_class.as_dict())
            names.append(six.text_type(res_class['name']))
        mock_read.side_effect = lambda *args: FakeEtcdMultipleResult(
            resource_classes)
        res = dbapi.list_resource_classes(self.context)
        res_names = [r.name for r in res]
        self.assertEqual(sorted(names), sorted(res_names))

    @mock.patch.object(etcd_client, 'read')
    @mock.patch.object(etcd_client, 'write')
    @mock.patch.object(dbapi, "_get_dbdriver_instance")
    def test_list_resource_classes_sorted(self, mock_ins,
                                          mock_write, mock_read):
        names = []
        resource_classes = []
        mock_ins.return_value = etcd_api.get_backend()
        mock_read.side_effect = etcd.EtcdKeyNotFound
        for i in range(1, 6):
            res_class = utils.create_test_resource_class(
                context=self.context, name='class' + str(i))
            resource_classes.append(res_class.as_dict())
            names.append(six.text_type(res_class['name']))
        mock_read.side_effect = lambda *args: FakeEtcdMultipleResult(
            resource_classes)
        res = dbapi.list_resource_classes(self.context, sort_key='name')
        res_names = [r.name for r in res]
        self.assertEqual(sorted(names), res_names)

    @mock.patch.object(etcd_client, 'read')
    @mock.patch.object(etcd_client, 'write')
    @mock.patch.object(etcd_client, 'delete')
    @mock.patch.object(dbapi, "_get_dbdriver_instance")
    def test_destroy_resource_class(self, mock_ins, mock_delete,
                                    mock_write, mock_read):
        mock_ins.return_value = etcd_api.get_backend()
        mock_read.side_effect = etcd.EtcdKeyNotFound
        resource_class = utils.create_test_resource_class(
            context=self.context)
        mock_read.side_effect = lambda *args: FakeEtcdResult(
            resource_class.as_dict())
        dbapi.destroy_resource_class(self.context, resource_class.uuid)
        mock_delete.assert_called_once_with(
            '/resource_classes/%s' % resource_class.uuid)

    @mock.patch.object(etcd_client, 'read')
    def test_destroy_resource_class_that_does_not_exist(self, mock_read):
        mock_read.side_effect = etcd.EtcdKeyNotFound
        self.assertRaises(exception.ResourceClassNotFound,
                          dbapi.destroy_resource_class,
                          self.context,
                          'ca3e2a25-2901-438d-8157-de7ffd68d535')

    @mock.patch.object(etcd_client, 'read')
    @mock.patch.object(etcd_client, 'write')
    @mock.patch.object(etcd_client, 'update')
    @mock.patch.object(dbapi, "_get_dbdriver_instance")
    def test_update_resource_class(self, mock_ins, mock_update,
                                   mock_write, mock_read):
        mock_ins.return_value = etcd_api.get_backend()
        mock_read.side_effect = etcd.EtcdKeyNotFound
        resource_class = utils.create_test_resource_class(
            context=self.context)
        old_name = resource_class.name
        new_name = 'new-name'
        self.assertNotEqual(old_name, new_name)
        mock_read.side_effect = lambda *args: FakeEtcdResult(
            resource_class.as_dict())
        dbapi.update_resource_class(
            self.context, resource_class.uuid, {'name': new_name})
        self.assertEqual(new_name, json.loads(
            mock_update.call_args_list[0][0][0].value)['name'])

    @mock.patch.object(etcd_client, 'read')
    def test_update_resource_class_not_found(self, mock_read):
        mock_read.side_effect = etcd.EtcdKeyNotFound
        new_name = 'new-name'
        self.assertRaises(exception.ResourceClassNotFound,
                          dbapi.update_resource_class,
                          self.context,
                          'ca3e2a25-2901-438d-8157-de7ffd68d535',
                          {'name': new_name})

    @mock.patch.object(etcd_client, 'read')
    @mock.patch.object(etcd_client, 'write')
    @mock.patch.object(dbapi, "_get_dbdriver_instance")
    def test_update_resource_class_uuid(self, mock_ins, mock_write, mock_read):
        mock_ins.return_value = etcd_api.get_backend()
        mock_read.side_effect = etcd.EtcdKeyNotFound
        resource_class = utils.create_test_resource_class(
            context=self.context)
        self.assertRaises(exception.InvalidParameterValue,
                          dbapi.update_resource_class,
                          self.context, resource_class.uuid,
                          {'uuid': ''})
