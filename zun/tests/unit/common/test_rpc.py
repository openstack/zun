# Copyright 2017 OpenStack Foundation
# All Rights Reserved.
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
from oslo_serialization import jsonutils as json

from zun.common import context
from zun.common import rpc
from zun.tests import base


class TestRpc(base.TestCase):

    def test_add_extra_exmods(self):
        rpc.EXTRA_EXMODS = []

        rpc.add_extra_exmods('foo', 'bar')

        self.assertEqual(['foo', 'bar'], rpc.EXTRA_EXMODS)

    def test_clear_extra_exmods(self):
        rpc.EXTRA_EXMODS = ['foo', 'bar']

        rpc.clear_extra_exmods()

        self.assertEqual(0, len(rpc.EXTRA_EXMODS))

    def test_serialize_entity(self):
        with mock.patch.object(json, 'to_primitive') as mock_prim:
            rpc.JsonPayloadSerializer.serialize_entity('context', 'entity')

        mock_prim.assert_called_once_with('entity', convert_instances=True)


class TestRequestContextSerializer(base.TestCase):
    def setUp(self):
        super(TestRequestContextSerializer, self).setUp()
        self.mock_base = mock.Mock()
        self.ser = rpc.RequestContextSerializer(self.mock_base)
        self.ser_null = rpc.RequestContextSerializer(None)

    def test_serialize_entity(self):
        self.mock_base.serialize_entity.return_value = 'foo'

        ser_ent = self.ser.serialize_entity('context', 'entity')

        self.mock_base.serialize_entity.assert_called_once_with('context',
                                                                'entity')
        self.assertEqual('foo', ser_ent)

    def test_serialize_entity_null_base(self):
        ser_ent = self.ser_null.serialize_entity('context', 'entity')

        self.assertEqual('entity', ser_ent)

    def test_deserialize_entity(self):
        self.mock_base.deserialize_entity.return_value = 'foo'

        deser_ent = self.ser.deserialize_entity('context', 'entity')

        self.mock_base.deserialize_entity.assert_called_once_with('context',
                                                                  'entity')
        self.assertEqual('foo', deser_ent)

    def test_deserialize_entity_null_base(self):
        deser_ent = self.ser_null.deserialize_entity('context', 'entity')

        self.assertEqual('entity', deser_ent)

    def test_serialize_context(self):
        context = mock.Mock()

        self.ser.serialize_context(context)

        context.to_dict.assert_called_once_with()

    @mock.patch.object(context, 'RequestContext')
    def test_deserialize_context(self, mock_req):
        self.ser.deserialize_context('context')

        mock_req.from_dict.assert_called_once_with('context')


class TestProfilerRequestContextSerializer(base.TestCase):
    def setUp(self):
        super(TestProfilerRequestContextSerializer, self).setUp()
        self.ser = rpc.ProfilerRequestContextSerializer(mock.Mock())

    @mock.patch('zun.common.rpc.profiler')
    def test_serialize_context(self, mock_profiler):
        prof = mock_profiler.get.return_value
        prof.hmac_key = 'swordfish'
        prof.get_base_id.return_value = 'baseid'
        prof.get_id.return_value = 'parentid'

        context = mock.Mock()
        context.to_dict.return_value = {'project_id': 'test'}

        self.assertEqual({
            'project_id': 'test',
            'trace_info': {
                'hmac_key': 'swordfish',
                'base_id': 'baseid',
                'parent_id': 'parentid'
            }
        }, self.ser.serialize_context(context))

    @mock.patch('zun.common.rpc.profiler')
    def test_deserialize_context(self, mock_profiler):
        serialized = {'project_id': 'test',
                      'trace_info': {
                          'hmac_key': 'swordfish',
                          'base_id': 'baseid',
                          'parent_id': 'parentid'}}

        context = self.ser.deserialize_context(serialized)

        self.assertEqual('test', context.project_id)
        mock_profiler.init.assert_called_once_with(
            hmac_key='swordfish', base_id='baseid', parent_id='parentid')
