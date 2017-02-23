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


from zun.common import rpc_service
import zun.conf


class API(rpc_service.API):
    '''Client side of the container compute rpc API.

    API version history:

        * 1.0 - Initial version.
        * 1.1 - Add image endpoints.
    '''

    def __init__(self, transport=None, context=None, topic=None):
        if topic is None:
            zun.conf.CONF.import_opt(
                'topic', 'zun.conf.compute', group='compute')

        super(API, self).__init__(
            transport, context, topic=zun.conf.CONF.compute.topic)

    def container_create(self, context, container):
        self._cast(container.host, 'container_create', container=container)

    def container_run(self, context, container):
        self._cast(container.host, 'container_run', container=container)

    def container_delete(self, context, container, force):
        return self._call(container.host, 'container_delete',
                          container=container, force=force)

    def container_show(self, context, container):
        return self._call(container.host, 'container_show',
                          container=container)

    def container_reboot(self, context, container, timeout):
        self._cast(container.host, 'container_reboot', container=container,
                   timeout=timeout)

    def container_stop(self, context, container, timeout):
        self._cast(container.host, 'container_stop', container=container,
                   timeout=timeout)

    def container_start(self, context, container):
        host = container.host
        self._cast(host, 'container_start', container=container)

    def container_pause(self, context, container):
        self._cast(container.host, 'container_pause', container=container)

    def container_unpause(self, context, container):
        self._cast(container.host, 'container_unpause', container=container)

    def container_logs(self, context, container, stdout, stderr):
        host = container.host
        return self._call(host, 'container_logs', container=container,
                          stdout=stdout, stderr=stderr)

    def container_exec(self, context, container, command):
        return self._call(container.host, 'container_exec',
                          container=container, command=command)

    def container_kill(self, context, container, signal):
        self._cast(container.host, 'container_kill', container=container,
                   signal=signal)

    def container_update(self, context, container, patch):
        return self._call(container.host, 'container_update',
                          container=container, patch=patch)

    def container_attach(self, context, container):
        return self._call(container.host, 'container_attach',
                          container=container)

    def container_resize(self, context, container, height, width):
        return self._call(container.host, 'container_resize',
                          container=container, height=height, width=width)

    def container_top(self, context, container, ps_args):
        return self._call(container.host, 'container_top',
                          container=container, ps_args=ps_args)

    def image_pull(self, context, image):
        # NOTE(hongbin): Image API doesn't support multiple compute nodes
        # scenario yet, so we temporarily set host to None and rpc will
        # choose an arbitrary host.
        host = None
        self._cast(host, 'image_pull', image=image)

    def image_search(self, context, image, image_driver, exact_match):
        # NOTE(hongbin): Image API doesn't support multiple compute nodes
        # scenario yet, so we temporarily set host to None and rpc will
        # choose an arbitrary host.
        host = None
        return self._call(host, 'image_search', image=image,
                          image_driver_name=image_driver,
                          exact_match=exact_match)
