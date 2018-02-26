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
from zun.db.etcd import api as etcdapi
from zun.db.etcd.api import EtcdAPI as etcd_api
from zun.tests.unit.db import base
from zun.tests.unit.db import utils
from zun.tests.unit.db.utils import FakeEtcdMultipleResult
from zun.tests.unit.db.utils import FakeEtcdResult

CONF = zun.conf.CONF


class DbContainerTestCase(base.DbTestCase):

    def setUp(self):
        super(DbContainerTestCase, self).setUp()

    def test_create_container(self):
        utils.create_test_container(context=self.context)

    def test_create_container_already_exists(self):
        CONF.set_override("unique_container_name_scope", "",
                          group="compute")
        utils.create_test_container(context=self.context,
                                    uuid='123')
        with self.assertRaisesRegex(exception.ContainerAlreadyExists,
                                    'A container with UUID 123.*'):
            utils.create_test_container(context=self.context,
                                        uuid='123')

    def test_create_container_already_exists_in_project_name_space(self):
        CONF.set_override("unique_container_name_scope", "project",
                          group="compute")
        utils.create_test_container(context=self.context, name='cont1')
        with self.assertRaisesRegex(exception.ContainerAlreadyExists,
                                    'A container with name.*'):
            utils.create_test_container(uuid=uuidutils.generate_uuid(),
                                        context=self.context,
                                        name='cont1')
        utils.create_test_container(context=self.context,
                                    name='abc',
                                    uuid=uuidutils.generate_uuid())

    def test_create_container_already_exists_in_global_name_space(self):
        CONF.set_override("unique_container_name_scope", "global",
                          group="compute")
        utils.create_test_container(context=self.context, name='cont1')
        self.context.project_id = 'fake_project_1'
        self.context.user_id = 'fake_user_1'
        with self.assertRaisesRegex(exception.ContainerAlreadyExists,
                                    'A container with name.*'):
            utils.create_test_container(uuid=uuidutils.generate_uuid(),
                                        context=self.context,
                                        name='cont1')
        utils.create_test_container(context=self.context,
                                    name='abc',
                                    uuid=uuidutils.generate_uuid())

    def test_create_container_already_exists_in_default_name_space(self):
        CONF.set_override("unique_container_name_scope", "",
                          group="compute")
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
        res = dbapi.get_container_by_uuid(self.context,
                                          container.uuid)
        self.assertEqual(container.id, res.id)
        self.assertEqual(container.uuid, res.uuid)

    def test_get_container_by_name(self):
        container = utils.create_test_container(context=self.context)
        res = dbapi.get_container_by_name(
            self.context, container.name)
        self.assertEqual(container.id, res.id)
        self.assertEqual(container.uuid, res.uuid)

    def test_get_container_that_does_not_exist(self):
        self.assertRaises(exception.ContainerNotFound,
                          dbapi.get_container_by_uuid,
                          self.context,
                          uuidutils.generate_uuid())

    def test_list_containers(self):
        uuids = []
        for i in range(1, 6):
            container = utils.create_test_container(
                uuid=uuidutils.generate_uuid(),
                context=self.context,
                name='container' + str(i))
            uuids.append(six.text_type(container['uuid']))
        res = dbapi.list_containers(self.context)
        res_uuids = [r.uuid for r in res]
        self.assertEqual(sorted(uuids), sorted(res_uuids))

    def test_list_containers_sorted(self):
        uuids = []
        for i in range(5):
            container = utils.create_test_container(
                uuid=uuidutils.generate_uuid(),
                context=self.context,
                name='container' + str(i))
            uuids.append(six.text_type(container.uuid))
        res = dbapi.list_containers(self.context, sort_key='uuid')
        res_uuids = [r.uuid for r in res]
        self.assertEqual(sorted(uuids), res_uuids)

        self.assertRaises(exception.InvalidParameterValue,
                          dbapi.list_containers,
                          self.context,
                          sort_key='foo')

    def test_list_containers_with_filters(self):
        container1 = utils.create_test_container(
            name='container-one',
            uuid=uuidutils.generate_uuid(),
            context=self.context)
        container2 = utils.create_test_container(
            name='container-two',
            uuid=uuidutils.generate_uuid(),
            context=self.context)

        res = dbapi.list_containers(
            self.context, filters={'name': 'container-one'})
        self.assertEqual([container1.id], [r.id for r in res])

        res = dbapi.list_containers(
            self.context, filters={'name': 'container-two'})
        self.assertEqual([container2.id], [r.id for r in res])

        res = dbapi.list_containers(
            self.context, filters={'name': 'bad-container'})
        self.assertEqual([], [r.id for r in res])

        res = dbapi.list_containers(
            self.context,
            filters={'name': container1.name})
        self.assertEqual([container1.id], [r.id for r in res])

    def test_list_containers_with_list_filters(self):
        container1 = utils.create_test_container(
            name='container-one',
            uuid=uuidutils.generate_uuid(),
            context=self.context)
        container2 = utils.create_test_container(
            name='container-two',
            uuid=uuidutils.generate_uuid(),
            context=self.context)

        res = dbapi.list_containers(
            self.context, filters={'name': ['container-one', 'container-two']})
        uuids = sorted([container1.uuid, container2.uuid])
        self.assertEqual(uuids, sorted([r.uuid for r in res]))

    def test_destroy_container(self):
        container = utils.create_test_container(context=self.context)
        dbapi.destroy_container(self.context, container.id)
        self.assertRaises(exception.ContainerNotFound,
                          dbapi.get_container_by_uuid,
                          self.context, container.uuid)

    def test_destroy_container_by_uuid(self):
        container = utils.create_test_container(context=self.context)
        dbapi.destroy_container(self.context, container.uuid)
        self.assertRaises(exception.ContainerNotFound,
                          dbapi.get_container_by_uuid,
                          self.context, container.uuid)

    def test_destroy_container_that_does_not_exist(self):
        self.assertRaises(exception.ContainerNotFound,
                          dbapi.destroy_container, self.context,
                          uuidutils.generate_uuid())

    def test_update_container(self):
        container = utils.create_test_container(context=self.context)
        old_image = container.image
        new_image = 'new-image'
        self.assertNotEqual(old_image, new_image)

        res = dbapi.update_container(self.context, container.id,
                                     {'image': new_image})
        self.assertEqual(new_image, res.image)

    def test_update_container_with_the_same_name(self):
        CONF.set_override("unique_container_name_scope", "project",
                          group="compute")
        container1 = utils.create_test_container(
            name='container-one',
            uuid=uuidutils.generate_uuid(),
            context=self.context)
        container2 = utils.create_test_container(
            name='container-two',
            uuid=uuidutils.generate_uuid(),
            context=self.context)
        new_name = 'new_name'
        dbapi.update_container(self.context, container1.id,
                               {'name': new_name})
        self.assertRaises(exception.ContainerAlreadyExists,
                          dbapi.update_container, self.context,
                          container2.id, {'name': new_name})

    def test_update_container_not_found(self):
        container_uuid = uuidutils.generate_uuid()
        new_image = 'new-image'
        self.assertRaises(exception.ContainerNotFound,
                          dbapi.update_container, self.context,
                          container_uuid, {'image': new_image})

    def test_update_container_uuid(self):
        container = utils.create_test_container(context=self.context)
        self.assertRaises(exception.InvalidParameterValue,
                          dbapi.update_container, self.context,
                          container.id, {'uuid': ''})


class EtcdDbContainerTestCase(base.DbTestCase):

    def setUp(self):
        cfg.CONF.set_override('backend', 'etcd', 'database')
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
                          group="compute")
        mock_read.side_effect = etcd.EtcdKeyNotFound
        utils.create_test_container(context=self.context)
        mock_read.side_effect = lambda *args: None
        self.assertRaises(exception.ResourceExists,
                          utils.create_test_container,
                          context=self.context)

    @mock.patch.object(etcd_client, 'read')
    @mock.patch.object(etcd_client, 'write')
    @mock.patch.object(dbapi, "_get_dbdriver_instance")
    def test_get_container_by_uuid(self, mock_inst, mock_write, mock_read):
        mock_inst.return_value = etcdapi.get_backend()
        mock_read.side_effect = etcd.EtcdKeyNotFound
        container = utils.create_test_container(context=self.context)
        mock_read.side_effect = lambda *args: FakeEtcdResult(
            container.as_dict())
        res = dbapi.get_container_by_uuid(self.context,
                                          container.uuid)
        self.assertEqual(container.id, res.id)
        self.assertEqual(container.uuid, res.uuid)

    @mock.patch.object(etcd_client, 'read')
    @mock.patch.object(etcd_client, 'write')
    @mock.patch.object(dbapi, "_get_dbdriver_instance")
    def test_get_container_by_name(self, mock_inst, mock_write, mock_read):
        mock_inst.return_value = etcdapi.get_backend()
        mock_read.side_effect = etcd.EtcdKeyNotFound
        container = utils.create_test_container(context=self.context)
        mock_read.side_effect = lambda *args: FakeEtcdMultipleResult(
            [container.as_dict()])
        res = dbapi.get_container_by_name(
            self.context, container.name)
        self.assertEqual(container.id, res.id)
        self.assertEqual(container.uuid, res.uuid)

    @mock.patch.object(etcd_client, 'read')
    @mock.patch.object(dbapi, "_get_dbdriver_instance")
    def test_get_container_that_does_not_exist(self, mock_inst, mock_read):
        mock_inst.return_value = etcdapi.get_backend()
        mock_read.side_effect = etcd.EtcdKeyNotFound
        self.assertRaises(exception.ContainerNotFound,
                          dbapi.get_container_by_uuid,
                          self.context,
                          uuidutils.generate_uuid())

    @mock.patch.object(etcd_client, 'read')
    @mock.patch.object(etcd_client, 'write')
    @mock.patch.object(dbapi, "_get_dbdriver_instance")
    def test_list_containers(self, mock_inst, mock_write, mock_read):
        uuids = []
        containers = []
        mock_inst.return_value = etcdapi.get_backend()
        mock_read.side_effect = etcd.EtcdKeyNotFound
        for i in range(1, 6):
            container = utils.create_test_container(
                uuid=uuidutils.generate_uuid(),
                context=self.context,
                name='cont' + str(i))
            containers.append(container.as_dict())
            uuids.append(six.text_type(container['uuid']))
        mock_read.side_effect = lambda *args: FakeEtcdMultipleResult(
            containers)
        res = dbapi.list_containers(self.context)
        res_uuids = [r.uuid for r in res]
        self.assertEqual(sorted(uuids), sorted(res_uuids))

    @mock.patch.object(etcd_client, 'read')
    @mock.patch.object(etcd_client, 'write')
    @mock.patch.object(dbapi, "_get_dbdriver_instance")
    def test_list_containers_sorted(self, mock_inst, mock_write, mock_read):
        uuids = []
        containers = []
        mock_inst.return_value = etcdapi.get_backend()
        mock_read.side_effect = etcd.EtcdKeyNotFound
        for i in range(5):
            container = utils.create_test_container(
                uuid=uuidutils.generate_uuid(),
                context=self.context,
                name='cont' + str(i))
            containers.append(container.as_dict())
            uuids.append(six.text_type(container.uuid))
        mock_read.side_effect = lambda *args: FakeEtcdMultipleResult(
            containers)
        res = dbapi.list_containers(self.context, sort_key='uuid')
        res_uuids = [r.uuid for r in res]
        self.assertEqual(sorted(uuids), res_uuids)

        self.assertRaises(exception.InvalidParameterValue,
                          dbapi.list_containers,
                          self.context,
                          sort_key='foo')

    @mock.patch.object(etcd_client, 'read')
    @mock.patch.object(etcd_client, 'write')
    @mock.patch.object(dbapi, "_get_dbdriver_instance")
    def test_list_containers_with_filters(self, mock_db_inst,
                                          mock_write, mock_read):
        mock_db_inst.return_value = etcdapi.get_backend()
        mock_read.side_effect = etcd.EtcdKeyNotFound

        container1 = utils.create_test_container(
            name='container-one',
            uuid=uuidutils.generate_uuid(),
            context=self.context)
        container2 = utils.create_test_container(
            name='container-two',
            uuid=uuidutils.generate_uuid(),
            context=self.context)

        mock_read.side_effect = lambda *args: FakeEtcdMultipleResult(
            [container1.as_dict(), container2.as_dict()])

        res = dbapi.list_containers(
            self.context, filters={'name': 'container-one'})
        self.assertEqual([container1.id], [r.id for r in res])

        res = dbapi.list_containers(
            self.context, filters={'name': 'container-two'})
        self.assertEqual([container2.id], [r.id for r in res])

        res = dbapi.list_containers(
            self.context, filters={'name': 'container-three'})
        self.assertEqual([], [r.id for r in res])

        res = dbapi.list_containers(
            self.context,
            filters={'name': container1.name})
        self.assertEqual([container1.id], [r.id for r in res])

    @mock.patch.object(etcd_client, 'read')
    @mock.patch.object(etcd_client, 'write')
    @mock.patch.object(etcd_client, 'delete')
    @mock.patch.object(dbapi, "_get_dbdriver_instance")
    def test_destroy_container(self, mock_inst, mock_delete,
                               mock_write, mock_read):
        mock_inst.return_value = etcdapi.get_backend()
        mock_read.side_effect = etcd.EtcdKeyNotFound
        container = utils.create_test_container(context=self.context)
        mock_read.side_effect = lambda *args: FakeEtcdResult(
            container.as_dict())
        dbapi.destroy_container(self.context, container.uuid)
        mock_delete.assert_called_once_with('/containers/%s' % container.uuid)

    @mock.patch.object(etcd_client, 'read')
    @mock.patch.object(etcd_client, 'write')
    @mock.patch.object(etcd_client, 'delete')
    @mock.patch.object(dbapi, "_get_dbdriver_instance")
    def test_destroy_container_by_uuid(self, mock_inst, mock_delete,
                                       mock_write, mock_read):
        mock_inst.return_value = etcdapi.get_backend()
        mock_read.side_effect = etcd.EtcdKeyNotFound
        container = utils.create_test_container(context=self.context)
        mock_read.side_effect = lambda *args: FakeEtcdResult(
            container.as_dict())
        dbapi.destroy_container(self.context, container.uuid)
        mock_delete.assert_called_once_with('/containers/%s' % container.uuid)

    @mock.patch.object(etcd_client, 'read')
    def test_destroy_container_that_does_not_exist(self, mock_read):
        mock_read.side_effect = etcd.EtcdKeyNotFound
        self.assertRaises(exception.ContainerNotFound,
                          dbapi.destroy_container, self.context,
                          uuidutils.generate_uuid())

    @mock.patch.object(etcd_client, 'read')
    @mock.patch.object(etcd_client, 'write')
    @mock.patch.object(etcd_client, 'update')
    @mock.patch.object(dbapi, "_get_dbdriver_instance")
    def test_update_container(self, mock_inst, mock_update,
                              mock_write, mock_read):
        mock_inst.return_value = etcdapi.get_backend()
        mock_read.side_effect = etcd.EtcdKeyNotFound
        container = utils.create_test_container(context=self.context)
        new_image = 'new-image'

        mock_read.side_effect = lambda *args: FakeEtcdResult(
            container.as_dict())
        dbapi.update_container(self.context, container.uuid,
                               {'image': new_image})
        self.assertEqual(new_image, json.loads(
            mock_update.call_args_list[0][0][0].value)['image'])

    @mock.patch.object(etcd_client, 'read')
    @mock.patch.object(etcd_client, 'write')
    @mock.patch.object(etcd_client, 'update')
    @mock.patch.object(dbapi, "_get_dbdriver_instance")
    def test_update_container_with_the_same_name(self, mock_inst, mock_update,
                                                 mock_write, mock_read):
        CONF.set_override("unique_container_name_scope", "project",
                          group="compute")
        mock_inst.return_value = etcdapi.get_backend()
        mock_read.side_effect = etcd.EtcdKeyNotFound
        container1 = utils.create_test_container(
            name='container-one',
            uuid=uuidutils.generate_uuid(),
            context=self.context)
        container2 = utils.create_test_container(
            name='container-two',
            uuid=uuidutils.generate_uuid(),
            context=self.context)

        mock_read.side_effect = lambda *args: FakeEtcdMultipleResult(
            [container1.as_dict(), container2.as_dict()])
        self.assertRaises(exception.ContainerAlreadyExists,
                          dbapi.update_container, self.context,
                          container2.uuid, {'name': 'container-one'})

    @mock.patch.object(etcd_client, 'read')
    def test_update_container_not_found(self, mock_read):
        container_uuid = uuidutils.generate_uuid()
        new_image = 'new-image'
        mock_read.side_effect = etcd.EtcdKeyNotFound
        self.assertRaises(exception.ContainerNotFound,
                          dbapi.update_container, self.context,
                          container_uuid, {'image': new_image})

    @mock.patch.object(etcd_client, 'read')
    @mock.patch.object(etcd_client, 'write')
    def test_update_container_uuid(self, mock_write, mock_read):
        mock_read.side_effect = etcd.EtcdKeyNotFound
        container = utils.create_test_container(context=self.context)
        self.assertRaises(exception.InvalidParameterValue,
                          dbapi.update_container, self.context,
                          container.id, {'uuid': ''})

    @mock.patch.object(etcd_client, 'read')
    @mock.patch.object(etcd_client, 'write')
    @mock.patch.object(etcd_api, 'list_containers')
    @mock.patch.object(dbapi, "_get_dbdriver_instance")
    def test_create_container_already_exists_in_project_name_space(
            self, mock_db_inst, mock_list_containers, mock_write, mock_read):
        mock_db_inst.return_value = etcdapi.get_backend()
        mock_read.side_effect = etcd.EtcdKeyNotFound
        mock_list_containers.return_value = []
        CONF.set_override("unique_container_name_scope", "project",
                          group="compute")
        container1 = utils.create_test_container(
            context=self.context, name='cont1')
        mock_list_containers.return_value = [container1]
        with self.assertRaisesRegex(exception.ContainerAlreadyExists,
                                    'A container with name.*'):
            utils.create_test_container(uuid=uuidutils.generate_uuid(),
                                        context=self.context,
                                        name='cont1')

    @mock.patch.object(etcd_client, 'read')
    @mock.patch.object(etcd_client, 'write')
    @mock.patch.object(etcd_api, 'list_containers')
    def test_create_container_already_exists_in_global_name_space(
            self, mock_list_containers, mock_write, mock_read):
        mock_read.side_effect = etcd.EtcdKeyNotFound
        mock_list_containers.return_value = []
        CONF.set_override("unique_container_name_scope", "global",
                          group="compute")
        container1 = utils.create_test_container(
            context=self.context, name='cont1')
        self.context.project_id = 'fake_project_1'
        self.context.user_id = 'fake_user_1'
        mock_list_containers.return_value = [container1]
        with self.assertRaisesRegex(exception.ContainerAlreadyExists,
                                    'A container with name.*'):
            utils.create_test_container(uuid=uuidutils.generate_uuid(),
                                        context=self.context,
                                        name='cont1')

    @mock.patch.object(etcd_client, 'read')
    @mock.patch.object(etcd_client, 'write')
    @mock.patch.object(etcd_api, 'list_containers')
    def test_create_container_already_exists_in_default_name_space(
            self, mock_list_containers, mock_write, mock_read):
        mock_read.side_effect = etcd.EtcdKeyNotFound
        mock_list_containers.return_value = []
        CONF.set_override("unique_container_name_scope", "",
                          group="compute")
        container1 = utils.create_test_container(
            context=self.context, name='cont1',
            uuid=uuidutils.generate_uuid())
        mock_list_containers.return_value = [container1]
        self.context.project_id = 'fake_project_1'
        self.context.user_id = 'fake_user_1'
        utils.create_test_container(
            context=self.context, name='cont1', uuid=uuidutils.generate_uuid())
