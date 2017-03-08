# Copyright 2014 - Rackspace Hosting
#
#    Licensed under the Apache License, Version 2.0 (the "License");
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

"""Common RPC service and API tools for Zun."""

import eventlet
import oslo_messaging as messaging
from oslo_service import service

from zun.common import rpc
import zun.conf
from zun.objects import base as objects_base
from zun.servicegroup import zun_service_periodic as servicegroup

# NOTE(paulczar):
# Ubuntu 14.04 forces librabbitmq when kombu is used
# Unfortunately it forces a version that has a crash
# bug.  Calling eventlet.monkey_patch() tells kombu
# to use libamqp instead.
eventlet.monkey_patch()

CONF = zun.conf.CONF


class Service(service.Service):

    def __init__(self, topic, server, handlers, binary):
        super(Service, self).__init__()
        serializer = rpc.RequestContextSerializer(
            objects_base.ZunObjectSerializer())
        transport = messaging.get_transport(CONF)
        # TODO(asalkeld) add support for version='x.y'
        target = messaging.Target(topic=topic, server=server)
        self._server = messaging.get_rpc_server(transport, target, handlers,
                                                serializer=serializer)
        self.binary = binary

    def start(self):
        servicegroup.setup(CONF, self.binary, self.tg)
        self._server.start()

    def stop(self):
        if self._server:
            self._server.stop()
            self._server.wait()
        super(Service, self).stop()

    @classmethod
    def create(cls, topic, server, handlers, binary):
        service_obj = cls(topic, server, handlers, binary)
        return service_obj


class API(object):
    def __init__(self, transport=None, context=None, topic=None, server=None,
                 timeout=None):
        serializer = rpc.RequestContextSerializer(
            objects_base.ZunObjectSerializer())
        if transport is None:
            exmods = rpc.get_allowed_exmods()
            transport = messaging.get_transport(CONF,
                                                allowed_remote_exmods=exmods)
        self._context = context
        if topic is None:
            topic = ''
        target = messaging.Target(topic=topic, server=server)
        self._client = messaging.RPCClient(transport, target,
                                           serializer=serializer,
                                           timeout=timeout)

    def _call(self, server, method, *args, **kwargs):
        cctxt = self._client.prepare(server=server)
        return cctxt.call(self._context, method, *args, **kwargs)

    def _cast(self, server, method, *args, **kwargs):
        cctxt = self._client.prepare(server=server)
        return cctxt.cast(self._context, method, *args, **kwargs)

    def echo(self, message):
        self._cast('echo', message=message)
