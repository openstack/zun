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

"""Tests for manipulating Containers via the DB API"""
import json
import mock

import etcd
from etcd import Client as etcd_client
from oslo_config import cfg
from oslo_utils import uuidutils
import six

from zun.common import exception
import zun.conf
from zun.db import api as dbapi
from zun.db.etcd.api import EtcdAPI as etcd_api
from zun.tests.unit.db import base
from zun.tests.unit.db import utils

CONF = zun.conf.CONF


class DbContainerTestCase(base.DbTestCase):

    def setUp(self):
        cfg.CONF.set_override('db_type', 'sql')
        super(DbContainerTestCase, self).setUp()

    def test_create_container(self):
        utils.create_test_container(context=self.context)

    def test_create_container_already_exists(self):
        CONF.set_override("unique_container_name_scope", "",
                          group="compute",
                          enforce_type=True)
        utils.create_test_container(context=self.context,
                                    uuid='123')
        with self.assertRaisesRegexp(exception.ContainerAlreadyExists,
                                     'A container with UUID 123.*'):
            utils.create_test_container(context=self.context,
                                        uuid='123')

    def test_get_container_by_id(self):
        container = utils.create_test_container(context=self.context)
        res = dbapi.Connection.get_container_by_id(self.context, container.id)
        self.assertEqual(container.id, res.id)
        self.assertEqual(container.uuid, res.uuid)

    def test_create_container_already_exists_in_project_name_space(self):
        CONF.set_override("unique_container_name_scope", "project",
                          group="compute",
                          enforce_type=True)
        utils.create_test_container(context=self.context, name='cont1')
        with self.assertRaisesRegexp(exception.ContainerAlreadyExists,
                                     'A container with name.*'):
            utils.create_test_container(uuid=uuidutils.generate_uuid(),
                                        context=self.context,
                                        name='cont1')
        utils.create_test_container(context=self.context,
                                    name='abc',
                                    uuid=uuidutils.generate_uuid())

    def test_create_container_already_exists_in_global_name_space(self):
        CONF.set_override("unique_container_name_scope", "global",
                          group="compute",
                          enforce_type=True)
        utils.create_test_container(context=self.context, name='cont1')
        self.context.project_id = 'fake_project_1'
        self.context.user_id = 'fake_user_1'
        with self.assertRaisesRegexp(exception.ContainerAlreadyExists,
                                     'A container with name.*'):
            utils.create_test_container(uuid=uuidutils.generate_uuid(),
                                        context=self.context,
                                        name='cont1')
        utils.create_test_container(context=self.context,
                                    name='abc',
                                    uuid=uuidutils.generate_uuid())

    def test_create_container_already_exists_in_default_name_space(self):
        CONF.set_override("unique_container_name_scope", "",
                          group="compute",
                          enforce_type=True)
        utils.create_test_container(context=self.context,
                                    name='cont1',
                                    uuid=uuidutils.generate_uuid())
        self.context.project_id = 'fake_project_1'
        self.context.user_id = 'fake_user_1'
        utils.create_test_container(context=self.context,
                                    name='cont1',
                                    uuid=uuidutils.generate_uuid())
        utils.create_test_container(context=self.context,
                                    name='abc',
                                    uuid=uuidutils.generate_uuid())

    def test_get_container_by_uuid(self):
        container = utils.create_test_container(context=self.context)
        res = dbapi.Connection.get_container_by_uuid(self.context,
                                                     container.uuid)
        self.assertEqual(container.id, res.id)
        self.assertEqual(container.uuid, res.uuid)

    def test_get_container_by_name(self):
        container = utils.create_test_container(context=self.context)
        res = dbapi.Connection.get_container_by_name(
            self.context, container.name)
        self.assertEqual(container.id, res.id)
        self.assertEqual(container.uuid, res.uuid)

    def test_get_container_that_does_not_exist(self):
        self.assertRaises(exception.ContainerNotFound,
                          dbapi.Connection.get_container_by_id,
                          self.context, 99)
        self.assertRaises(exception.ContainerNotFound,
                          dbapi.Connection.get_container_by_uuid,
                          self.context,
                          uuidutils.generate_uuid())

    def test_list_container(self):
        uuids = []
        for i in range(1, 6):
            container = utils.create_test_container(
                uuid=uuidutils.generate_uuid(),
                context=self.context,
                name='container'+str(i))
            uuids.append(six.text_type(container['uuid']))
        res = dbapi.Connection.list_container(self.context)
        res_uuids = [r.uuid for r in res]
        self.assertEqual(sorted(uuids), sorted(res_uuids))

    def test_list_container_sorted(self):
        uuids = []
        for i in range(5):
            container = utils.create_test_container(
                uuid=uuidutils.generate_uuid(),
                context=self.context,
                name='container'+str(i))
            uuids.append(six.text_type(container.uuid))
        res = dbapi.Connection.list_container(self.context, sort_key='uuid')
        res_uuids = [r.uuid for r in res]
        self.assertEqual(sorted(uuids), res_uuids)

        self.assertRaises(exception.InvalidParameterValue,
                          dbapi.Connection.list_container,
                          self.context,
                          sort_key='foo')

    def test_list_container_with_filters(self):
        container1 = utils.create_test_container(
            name='container-one',
            uuid=uuidutils.generate_uuid(),
            context=self.context)
        container2 = utils.create_test_container(
            name='container-two',
            uuid=uuidutils.generate_uuid(),
            context=self.context)

        res = dbapi.Connection.list_container(
            self.context, filters={'name': 'container-one'})
        self.assertEqual([container1.id], [r.id for r in res])

        res = dbapi.Connection.list_container(
            self.context, filters={'name': 'container-two'})
        self.assertEqual([container2.id], [r.id for r in res])

        res = dbapi.Connection.list_container(
            self.context, filters={'name': 'bad-container'})
        self.assertEqual([], [r.id for r in res])

        res = dbapi.Connection.list_container(
            self.context,
            filters={'name': container1.name})
        self.assertEqual([container1.id], [r.id for r in res])

    def test_destroy_container(self):
        container = utils.create_test_container(context=self.context)
        dbapi.Connection.destroy_container(self.context, container.id)
        self.assertRaises(exception.ContainerNotFound,
                          dbapi.Connection.get_container_by_id,
                          self.context, container.id)

    def test_destroy_container_by_uuid(self):
        container = utils.create_test_container(context=self.context)
        dbapi.Connection.destroy_container(self.context, container.uuid)
        self.assertRaises(exception.ContainerNotFound,
                          dbapi.Connection.get_container_by_uuid,
                          self.context, container.uuid)

    def test_destroy_container_that_does_not_exist(self):
        self.assertRaises(exception.ContainerNotFound,
                          dbapi.Connection.destroy_container, self.context,
                          uuidutils.generate_uuid())

    def test_update_container(self):
        container = utils.create_test_container(context=self.context)
        old_image = container.image
        new_image = 'new-image'
        self.assertNotEqual(old_image, new_image)

        res = dbapi.Connection.update_container(self.context, container.id,
                                                {'image': new_image})
        self.assertEqual(new_image, res.image)

    def test_update_container_with_the_same_name(self):
        container1 = utils.create_test_container(
            name='container-one',
            uuid=uuidutils.generate_uuid(),
            context=self.context)
        container2 = utils.create_test_container(
            name='container-two',
            uuid=uuidutils.generate_uuid(),
            context=self.context)
        new_name = 'new_name'
        dbapi.Connection.update_container(self.context, container1.id,
                                          {'name': new_name})
        self.assertRaises(exception.ContainerAlreadyExists,
                          dbapi.Connection.update_container, self.context,
                          container2.id, {'name': new_name})

    def test_update_container_not_found(self):
        container_uuid = uuidutils.generate_uuid()
        new_image = 'new-image'
        self.assertRaises(exception.ContainerNotFound,
                          dbapi.Connection.update_container, self.context,
                          container_uuid, {'image': new_image})

    def test_update_container_uuid(self):
        container = utils.create_test_container(context=self.context)
        self.assertRaises(exception.InvalidParameterValue,
                          dbapi.Connection.update_container, self.context,
                          container.id, {'uuid': ''})


class FakeEtcdMutlipleResult(object):

    def __init__(self, value):
        self.children = []
        for v in value:
            res = mock.MagicMock()
            res.value = json.dumps(v)
            self.children.append(res)


class FakeEtcdResult(object):

    def __init__(self, value):
        self.value = json.dumps(value)


class EtcdDbContainerTestCase(base.DbTestCase):

    def setUp(self):
        cfg.CONF.set_override('db_type', 'etcd')
        super(EtcdDbContainerTestCase, self).setUp()

    @mock.patch.object(etcd_client, 'read')
    @mock.patch.object(etcd_client, 'write')
    def test_create_container(self, mock_write, mock_read):
        mock_read.side_effect = etcd.EtcdKeyNotFound
        utils.create_test_container(context=self.context)

    @mock.patch.object(etcd_client, 'read')
    @mock.patch.object(etcd_client, 'write')
    def test_create_container_already_exists(self, mock_write, mock_read):
        CONF.set_override("unique_container_name_scope", "",
                          group="compute",
                          enforce_type=True)
        mock_read.side_effect = etcd.EtcdKeyNotFound
        utils.create_test_container(context=self.context)
        mock_read.side_effect = lambda *args: None
        self.assertRaises(exception.ResourceExists,
                          utils.create_test_container,
                          context=self.context)

    @mock.patch.object(etcd_client, 'read')
    @mock.patch.object(etcd_client, 'write')
    def test_get_container_by_id(self, mock_write, mock_read):
        mock_read.side_effect = etcd.EtcdKeyNotFound
        container = utils.create_test_container(context=self.context)
        mock_read.side_effect = lambda *args: FakeEtcdMutlipleResult(
            [container.as_dict()])
        res = dbapi.Connection.get_container_by_id(self.context, container.id)
        self.assertEqual(container.id, res.id)
        self.assertEqual(container.uuid, res.uuid)

    @mock.patch.object(etcd_client, 'read')
    @mock.patch.object(etcd_client, 'write')
    def test_get_container_by_uuid(self, mock_write, mock_read):
        mock_read.side_effect = etcd.EtcdKeyNotFound
        container = utils.create_test_container(context=self.context)
        mock_read.side_effect = lambda *args: FakeEtcdResult(
            container.as_dict())
        res = dbapi.Connection.get_container_by_uuid(self.context,
                                                     container.uuid)
        self.assertEqual(container.id, res.id)
        self.assertEqual(container.uuid, res.uuid)

    @mock.patch.object(etcd_client, 'read')
    @mock.patch.object(etcd_client, 'write')
    def test_get_container_by_name(self, mock_write, mock_read):
        mock_read.side_effect = etcd.EtcdKeyNotFound
        container = utils.create_test_container(context=self.context)
        mock_read.side_effect = lambda *args: FakeEtcdMutlipleResult(
            [container.as_dict()])
        res = dbapi.Connection.get_container_by_name(
            self.context, container.name)
        self.assertEqual(container.id, res.id)
        self.assertEqual(container.uuid, res.uuid)

    @mock.patch.object(etcd_client, 'read')
    def test_get_container_that_does_not_exist(self, mock_read):
        mock_read.side_effect = etcd.EtcdKeyNotFound
        self.assertRaises(exception.ContainerNotFound,
                          dbapi.Connection.get_container_by_id,
                          self.context, 99)
        self.assertRaises(exception.ContainerNotFound,
                          dbapi.Connection.get_container_by_uuid,
                          self.context,
                          uuidutils.generate_uuid())

    @mock.patch.object(etcd_client, 'read')
    @mock.patch.object(etcd_client, 'write')
    def test_list_container(self, mock_write, mock_read):
        uuids = []
        containers = []
        mock_read.side_effect = etcd.EtcdKeyNotFound
        for i in range(1, 6):
            container = utils.create_test_container(
                uuid=uuidutils.generate_uuid(),
                context=self.context,
                name='cont' + str(i))
            containers.append(container.as_dict())
            uuids.append(six.text_type(container['uuid']))
        mock_read.side_effect = lambda *args: FakeEtcdMutlipleResult(
            containers)
        res = dbapi.Connection.list_container(self.context)
        res_uuids = [r.uuid for r in res]
        self.assertEqual(sorted(uuids), sorted(res_uuids))

    @mock.patch.object(etcd_client, 'read')
    @mock.patch.object(etcd_client, 'write')
    def test_list_container_sorted(self, mock_write, mock_read):
        uuids = []
        containers = []
        mock_read.side_effect = etcd.EtcdKeyNotFound
        for i in range(5):
            container = utils.create_test_container(
                uuid=uuidutils.generate_uuid(),
                context=self.context,
                name='cont' + str(i))
            containers.append(container.as_dict())
            uuids.append(six.text_type(container.uuid))
        mock_read.side_effect = lambda *args: FakeEtcdMutlipleResult(
            containers)
        res = dbapi.Connection.list_container(self.context, sort_key='uuid')
        res_uuids = [r.uuid for r in res]
        self.assertEqual(sorted(uuids), res_uuids)

        self.assertRaises(exception.InvalidParameterValue,
                          dbapi.Connection.list_container,
                          self.context,
                          sort_key='foo')

    @mock.patch.object(etcd_client, 'read')
    @mock.patch.object(etcd_client, 'write')
    def test_list_container_with_filters(self, mock_write, mock_read):
        mock_read.side_effect = etcd.EtcdKeyNotFound

        container1 = utils.create_test_container(
            name='container-one',
            uuid=uuidutils.generate_uuid(),
            context=self.context)
        container2 = utils.create_test_container(
            name='container-two',
            uuid=uuidutils.generate_uuid(),
            context=self.context)

        mock_read.side_effect = lambda *args: FakeEtcdMutlipleResult(
            [container1.as_dict(), container2.as_dict()])

        res = dbapi.Connection.list_container(
            self.context, filters={'name': 'container-one'})
        self.assertEqual([container1.id], [r.id for r in res])

        res = dbapi.Connection.list_container(
            self.context, filters={'name': 'container-two'})
        self.assertEqual([container2.id], [r.id for r in res])

        res = dbapi.Connection.list_container(
            self.context, filters={'name': 'container-three'})
        self.assertEqual([], [r.id for r in res])

        res = dbapi.Connection.list_container(
            self.context,
            filters={'name': container1.name})
        self.assertEqual([container1.id], [r.id for r in res])

    @mock.patch.object(etcd_client, 'read')
    @mock.patch.object(etcd_client, 'write')
    @mock.patch.object(etcd_client, 'delete')
    def test_destroy_container(self, mock_delete, mock_write, mock_read):
        mock_read.side_effect = etcd.EtcdKeyNotFound
        container = utils.create_test_container(context=self.context)
        mock_read.side_effect = lambda *args: FakeEtcdMutlipleResult(
            [container.as_dict()])
        dbapi.Connection.destroy_container(self.context, container.id)
        mock_delete.assert_called_once_with('/containers/%s' % container.uuid)

    @mock.patch.object(etcd_client, 'read')
    @mock.patch.object(etcd_client, 'write')
    @mock.patch.object(etcd_client, 'delete')
    def test_destroy_container_by_uuid(self, mock_delete,
                                       mock_write, mock_read):
        mock_read.side_effect = etcd.EtcdKeyNotFound
        container = utils.create_test_container(context=self.context)
        mock_read.side_effect = lambda *args: FakeEtcdResult(
            container.as_dict())
        dbapi.Connection.destroy_container(self.context, container.uuid)
        mock_delete.assert_called_once_with('/containers/%s' % container.uuid)

    @mock.patch.object(etcd_client, 'read')
    def test_destroy_container_that_does_not_exist(self, mock_read):
        mock_read.side_effect = etcd.EtcdKeyNotFound
        self.assertRaises(exception.ContainerNotFound,
                          dbapi.Connection.destroy_container, self.context,
                          uuidutils.generate_uuid())

    @mock.patch.object(etcd_client, 'read')
    @mock.patch.object(etcd_client, 'write')
    @mock.patch.object(etcd_client, 'update')
    def test_update_container(self, mock_update, mock_write, mock_read):
        mock_read.side_effect = etcd.EtcdKeyNotFound
        container = utils.create_test_container(context=self.context)
        new_image = 'new-image'

        mock_read.side_effect = lambda *args: FakeEtcdResult(
            container.as_dict())
        dbapi.Connection.update_container(self.context, container.uuid,
                                          {'image': new_image})
        self.assertEqual(new_image, json.loads(
            mock_update.call_args_list[0][0][0].value)['image'])

    @mock.patch.object(etcd_client, 'read')
    @mock.patch.object(etcd_client, 'write')
    @mock.patch.object(etcd_client, 'update')
    def test_update_container_with_the_same_name(self, mock_update,
                                                 mock_write, mock_read):
        mock_read.side_effect = etcd.EtcdKeyNotFound
        container1 = utils.create_test_container(
            name='container-one',
            uuid=uuidutils.generate_uuid(),
            context=self.context)
        container2 = utils.create_test_container(
            name='container-two',
            uuid=uuidutils.generate_uuid(),
            context=self.context)

        mock_read.side_effect = lambda *args: FakeEtcdMutlipleResult(
            [container1.as_dict(), container2.as_dict()])
        self.assertRaises(exception.ContainerAlreadyExists,
                          dbapi.Connection.update_container, self.context,
                          container2.uuid, {'name': 'container-one'})

    @mock.patch.object(etcd_client, 'read')
    def test_update_container_not_found(self, mock_read):
        container_uuid = uuidutils.generate_uuid()
        new_image = 'new-image'
        mock_read.side_effect = etcd.EtcdKeyNotFound
        self.assertRaises(exception.ContainerNotFound,
                          dbapi.Connection.update_container, self.context,
                          container_uuid, {'image': new_image})

    @mock.patch.object(etcd_client, 'read')
    @mock.patch.object(etcd_client, 'write')
    def test_update_container_uuid(self, mock_write, mock_read):
        mock_read.side_effect = etcd.EtcdKeyNotFound
        container = utils.create_test_container(context=self.context)
        self.assertRaises(exception.InvalidParameterValue,
                          dbapi.Connection.update_container, self.context,
                          container.id, {'uuid': ''})

    @mock.patch.object(etcd_client, 'read')
    @mock.patch.object(etcd_client, 'write')
    @mock.patch.object(etcd_api, 'list_container')
    def test_create_container_already_exists_in_project_name_space(
            self, mock_list_container, mock_write, mock_read):
        mock_read.side_effect = etcd.EtcdKeyNotFound
        mock_list_container.return_value = []
        CONF.set_override("unique_container_name_scope", "project",
                          group="compute",
                          enforce_type=True)
        container1 = utils.create_test_container(
            context=self.context, name='cont1')
        mock_list_container.return_value = [container1]
        with self.assertRaisesRegexp(exception.ContainerAlreadyExists,
                                     'A container with name.*'):
            utils.create_test_container(uuid=uuidutils.generate_uuid(),
                                        context=self.context,
                                        name='cont1')

    @mock.patch.object(etcd_client, 'read')
    @mock.patch.object(etcd_client, 'write')
    @mock.patch.object(etcd_api, 'list_container')
    def test_create_container_already_exists_in_global_name_space(
            self, mock_list_container, mock_write, mock_read):
        mock_read.side_effect = etcd.EtcdKeyNotFound
        mock_list_container.return_value = []
        CONF.set_override("unique_container_name_scope", "global",
                          group="compute",
                          enforce_type=True)
        container1 = utils.create_test_container(
            context=self.context, name='cont1')
        self.context.project_id = 'fake_project_1'
        self.context.user_id = 'fake_user_1'
        mock_list_container.return_value = [container1]
        with self.assertRaisesRegexp(exception.ContainerAlreadyExists,
                                     'A container with name.*'):
            utils.create_test_container(uuid=uuidutils.generate_uuid(),
                                        context=self.context,
                                        name='cont1')

    @mock.patch.object(etcd_client, 'read')
    @mock.patch.object(etcd_client, 'write')
    @mock.patch.object(etcd_api, 'list_container')
    def test_create_container_already_exists_in_default_name_space(
            self, mock_list_container, mock_write, mock_read):
        mock_read.side_effect = etcd.EtcdKeyNotFound
        mock_list_container.return_value = []
        CONF.set_override("unique_container_name_scope", "",
                          group="compute",
                          enforce_type=True)
        container1 = utils.create_test_container(
            context=self.context, name='cont1',
            uuid=uuidutils.generate_uuid())
        mock_list_container.return_value = [container1]
        self.context.project_id = 'fake_project_1'
        self.context.user_id = 'fake_user_1'
        utils.create_test_container(
            context=self.context, name='cont1', uuid=uuidutils.generate_uuid())
