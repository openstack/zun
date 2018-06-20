#    Copyright 2017 ARM Holdings.
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

"""
Websocket proxy that is compatible with OpenStack Zun.
Leverages websockify.py by Joel Martin
"""

import errno
import select
import socket
import sys
import time

import docker
from oslo_log import log as logging
from oslo_utils import uuidutils
import six.moves.urllib.parse as urlparse
import websockify

from zun.common import context
from zun.common import exception
from zun.common.i18n import _
import zun.conf
from zun import objects
from zun.websocket.websocketclient import WebSocketClient

LOG = logging.getLogger(__name__)
CONF = zun.conf.CONF


class ZunProxyRequestHandlerBase(object):
    def verify_origin_proto(self, access_url, origin_proto):
        if not access_url:
            detail = _("No access_url available."
                       "Cannot validate protocol")
            raise exception.ValidationError(detail=detail)
        expected_protos = [urlparse.urlparse(access_url).scheme]
        # NOTE: For serial consoles the expected protocol could be ws or
        # wss which correspond to http and https respectively in terms of
        # security.
        if 'ws' in expected_protos:
            expected_protos.append('http')
        if 'wss' in expected_protos:
            expected_protos.append('https')

        return origin_proto in expected_protos

    def _send_buffer(self, buff, target, send_all=False):
        size = len(buff)
        tosend = size
        already_sent = 0

        while tosend > 0:
            try:
                # i should be able to send a bytearray
                sent = target.send(buff[already_sent:])
                if sent == 0:
                    raise RuntimeError('socket connection broken')

                already_sent += sent
                tosend -= sent

            except socket.error as e:
                # if full buffers then wait for them to drain and try again
                if e.errno in [errno.EAGAIN, errno.EWOULDBLOCK]:
                    if send_all:
                        continue
                    return buff[already_sent:]
                else:
                    raise exception.SocketException(str(e))
        return None

    def _handle_ins_outs(self, target, ins, outs):
        """Handle the select file ins and outs

        Handle the operation ins and outs from select
        """
        if self.request in outs:
            # Send queued target data to the client
            self.c_pend = self.send_frames(self.cqueue)
            self.cqueue = []

        if self.request in ins:
            # Receive client data, decode it, and queue for target
            bufs, closed = self.recv_frames()
            self.tqueue.extend(bufs)
            if closed:
                self.msg(_("Client closed connection:"
                           "%(host)s:%(port)s") % {
                    'host': self.server.target_host,
                    'port': self.server.target_port})
                raise self.CClose(closed['code'], closed['reason'])

        if target in outs:
            while self.tqueue:
                payload = self.tqueue.pop(0)
                remaining = self._send_buffer(payload, target)
                if remaining is not None:
                    self.tqueue.appendleft(remaining)
                    break

        if target in ins:
            # Receive target data, encode it and queue for client
            buf = target.recv()
            if len(buf) == 0:
                self.msg(_("Client closed connection:"
                           "%(host)s:%(port)s") % {
                    'host': self.server.target_host,
                    'port': self.server.target_port})
                raise self.CClose(1000, "Target closed")
            self.cqueue.append(buf)

    def do_websocket_proxy(self, target):
        """Proxy websocket link

        Proxy client WebSocket to normal target socket.
        """
        self.cqueue = []
        self.tqueue = []
        self.c_pend = 0
        rlist = [self.request, target]

        if self.server.heartbeat:
            now = time.time()
            self.heartbeat = now + self.server.heartbeat
        else:
            self.heartbeat = None

        while True:
            wlist = []

            if self.heartbeat is not None:
                now = time.time()
                if now > self.heartbeat:
                    self.heartbeat = now + self.server.heartbeat
                    self.send_ping()

            if self.tqueue:
                wlist.append(target)
            if self.cqueue or self.c_pend:
                wlist.append(self.request)
            try:
                ins, outs, excepts = select.select(rlist, wlist, [], 1)
            except (select.error, OSError):
                exc = sys.exc_info()[1]
                if hasattr(exc, 'errno'):
                    err = exc.errno
                else:
                    err = exc[0]
                if err != errno.EINTR:
                    raise
                else:
                    continue

            if excepts:
                raise exception.SocketException()

            self._handle_ins_outs(target, ins, outs)

    def new_websocket_client(self):
        """Called after a new WebSocket connection has been established."""
        # Reopen the eventlet hub to make sure we don't share an epoll
        # fd with parent and/or siblings, which would be bad
        from eventlet import hubs
        hubs.use_hub()

        # The zun expected behavior is to have token
        # passed to the method GET of the request
        parse = urlparse.urlparse(self.path)
        if parse.scheme not in ('http', 'https'):
            # From a bug in urlparse in Python < 2.7.4 we cannot support
            # special schemes (cf: https://bugs.python.org/issue9374)
            if sys.version_info < (2, 7, 4):
                raise exception.ZunException(
                    _("We do not support scheme '%s' under Python < 2.7.4, "
                      "please use http or https") % parse.scheme)

        query = parse.query
        token = urlparse.parse_qs(query).get("token", [""]).pop()
        uuid = urlparse.parse_qs(query).get("uuid", [""]).pop()
        exec_id = urlparse.parse_qs(query).get("exec_id", [""]).pop()

        ctx = context.get_admin_context(all_projects=True)

        if uuidutils.is_uuid_like(uuid):
            container = objects.Container.get_by_uuid(ctx, uuid)
        else:
            container = objects.Container.get_by_name(ctx, uuid)

        if exec_id:
            self._new_exec_client(container, token, uuid, exec_id)
        else:
            self._new_websocket_client(container, token, uuid)

    def _new_websocket_client(self, container, token, uuid):
        if token != container.websocket_token:
            raise exception.InvalidWebsocketToken(token)

        access_url = '%s?token=%s&uuid=%s' % (CONF.websocket_proxy.base_url,
                                              token, uuid)

        self._verify_origin(access_url)

        if container.websocket_url:
            target_url = container.websocket_url
            escape = "~"
            close_wait = 0.5
            wscls = WebSocketClient(host_url=target_url, escape=escape,
                                    close_wait=close_wait)
            wscls.connect()
            self.target = wscls
        else:
            raise exception.InvalidWebsocketUrl()

        # Start proxying
        try:
            self.do_websocket_proxy(self.target.ws)
        except Exception:
            if self.target.ws:
                self.target.ws.close()
                self.vmsg(_("Websocket client or target closed"))
            raise

    def _new_exec_client(self, container, token, uuid, exec_id):
        exec_instance = None
        for e in container.exec_instances:
            if token == e.token and exec_id == e.exec_id:
                exec_instance = e

        if not exec_instance:
            raise exception.InvalidWebsocketToken(token)

        access_url = '%s?token=%s&uuid=%s' % (CONF.websocket_proxy.base_url,
                                              token, uuid)

        self._verify_origin(access_url)

        client = docker.APIClient(base_url=exec_instance.url)
        tsock = client.exec_start(exec_id, socket=True, tty=True)

        try:
            self.do_proxy(tsock)
        finally:
            if tsock:
                tsock.shutdown(socket.SHUT_RDWR)
                tsock.close()
                self.vmsg(_("%s: Closed target") % exec_instance.url)

    def _verify_origin(self, access_url):
        # Verify Origin
        expected_origin_hostname = self.headers.get('Host')
        if ':' in expected_origin_hostname:
            e = expected_origin_hostname
            if '[' in e and ']' in e:
                expected_origin_hostname = e.split(']')[0][1:]
            else:
                expected_origin_hostname = e.split(':')[0]
        expected_origin_hostnames = CONF.websocket_proxy.allowed_origins
        expected_origin_hostnames.append(expected_origin_hostname)
        origin_url = self.headers.get('Origin')

        # missing origin header indicates non-browser client which is OK
        if origin_url is not None:
            origin = urlparse.urlparse(origin_url)
            origin_hostname = origin.hostname
            origin_scheme = origin.scheme
            if origin_hostname == '' or origin_scheme == '':
                detail = _("Origin header not valid.")
                raise exception.ValidationError(detail)
            if origin_hostname not in expected_origin_hostnames:
                detail = _("Origin header does not match this host.")
                raise exception.ValidationError(detail)
            if not self.verify_origin_proto(access_url, origin_scheme):
                detail = _("Origin header protocol does not match this host.")
                raise exception.ValidationError(detail)


class ZunProxyRequestHandler(ZunProxyRequestHandlerBase,
                             websockify.ProxyRequestHandler):
    def __init__(self, *args, **kwargs):
        websockify.ProxyRequestHandler.__init__(self, *args, **kwargs)

    def socket(self, *args, **kwargs):
        return websockify.WebSocketServer.socket(*args, **kwargs)


class ZunWebSocketProxy(websockify.WebSocketProxy):
    @staticmethod
    def get_logger():
        return LOG
