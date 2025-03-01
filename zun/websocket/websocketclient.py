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

import socket
import ssl
import websocket

from zun.common import exception
import zun.conf


CONF = zun.conf.CONF


class WebSocketClient(object):

    def __init__(self, host_url, escape='~',
                 close_wait=0.5):
        self.escape = escape
        self.close_wait = close_wait
        self.host_url = host_url
        self.cs = None

    def connect(self):
        url = self.host_url
        sslopt = None
        if url.startswith('wss'):
            ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
            ssl_context.load_verify_locations(CONF.docker.ca_file)
            ssl_context.load_cert_chain(CONF.docker.cert_file,
                                        CONF.docker.key_file)
            sslopt = {'context': ssl_context}

        try:
            self.ws = websocket.create_connection(url,
                                                  sslopt=sslopt,
                                                  skip_utf8_validation=True)
        except socket.error as e:
            raise exception.ConnectionFailed(e)
        except websocket.WebSocketConnectionClosedException as e:
            raise exception.ConnectionFailed(e)
        except websocket.WebSocketBadStatusException as e:
            raise exception.ConnectionFailed(e)
