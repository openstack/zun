#    Copyright 2016 IBM Corp.
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

from oslo_config import cfg

from zun.common import rpc_service


class API(rpc_service.API):
    '''Client side of the container compute rpc API.

    API version history:

        * 1.0 - Initial version.
    '''

    def __init__(self, transport=None, context=None, topic=None):
        if topic is None:
            cfg.CONF.import_opt(
                'topic', 'zun.compute.config', group='compute')

        super(API, self).__init__(
            transport, context, topic=cfg.CONF.compute.topic)

    def container_create(self, context, container):
        return self._call('container_create', container=container)

    def container_delete(self, context, container):
        return self._call('container_delete', container=container)

    def container_show(self, context, container):
        return self._call('container_show', container=container)

    def container_reboot(self, context, container):
        return self._call('container_reboot', container=container)

    def container_stop(self, context, container):
        return self._call('container_stop', container=container)

    def container_start(self, context, container):
        return self._call('container_start', container=container)

    def container_pause(self, context, container):
        return self._call('container_pause', container=container)

    def container_unpause(self, context, container):
        return self._call('container_unpause', container=container)

    def container_logs(self, context, container):
        return self._call('container_logs', container=container)

    def container_exec(self, context, container, command):
        return self._call('container_exec', container=container)
