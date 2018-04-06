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

import functools

from zun.api import servicegroup
from zun.common import exception
from zun.common import profiler
from zun.common import rpc_service
import zun.conf
from zun import objects


def check_container_host(func):
    """Verify the state of container host"""
    @functools.wraps(func)
    def wrap(self, context, container, *args, **kwargs):
        services = objects.ZunService.list_by_binary(context, 'zun-compute')
        api_servicegroup = servicegroup.ServiceGroup()
        up_hosts = [service.host for service in services
                    if api_servicegroup.service_is_up(service)]
        if container.host is not None and container.host not in up_hosts:
            raise exception.ContainerHostNotUp(container=container.uuid,
                                               host=container.host)
        return func(self, context, container, *args, **kwargs)
    return wrap


@profiler.trace_cls("rpc")
class API(rpc_service.API):
    """Client side of the container compute rpc API.

    API version history:

        * 1.0 - Initial version.
        * 1.1 - Add image endpoints.
    """

    def __init__(self, transport=None, context=None, topic=None):
        if topic is None:
            zun.conf.CONF.import_opt(
                'topic', 'zun.conf.compute', group='compute')

        super(API, self).__init__(
            transport, context, topic=zun.conf.CONF.compute.topic)

    def container_create(self, context, host, container, limits,
                         requested_networks, requested_volumes, run,
                         pci_requests):
        self._cast(host, 'container_create', limits=limits,
                   requested_networks=requested_networks,
                   requested_volumes=requested_volumes,
                   container=container,
                   run=run,
                   pci_requests=pci_requests)

    @check_container_host
    def container_delete(self, context, container, force):
        return self._cast(container.host, 'container_delete',
                          container=container, force=force)

    @check_container_host
    def container_show(self, context, container):
        return self._call(container.host, 'container_show',
                          container=container)

    def container_rebuild(self, context, container):
        self._cast(container.host, 'container_rebuild', container=container)

    def container_reboot(self, context, container, timeout):
        self._cast(container.host, 'container_reboot', container=container,
                   timeout=timeout)

    def container_stop(self, context, container, timeout):
        self._cast(container.host, 'container_stop', container=container,
                   timeout=timeout)

    def container_start(self, context, container):
        self._cast(container.host, 'container_start', container=container)

    def container_pause(self, context, container):
        self._cast(container.host, 'container_pause', container=container)

    def container_unpause(self, context, container):
        self._cast(container.host, 'container_unpause', container=container)

    @check_container_host
    def container_logs(self, context, container, stdout, stderr,
                       timestamps, tail, since):
        return self._call(container.host, 'container_logs',
                          container=container, stdout=stdout, stderr=stderr,
                          timestamps=timestamps, tail=tail, since=since)

    @check_container_host
    def container_exec(self, context, container, command, run, interactive):
        return self._call(container.host, 'container_exec',
                          container=container, command=command, run=run,
                          interactive=interactive)

    @check_container_host
    def container_exec_resize(self, context, container, exec_id, height,
                              width):
        return self._call(container.host, 'container_exec_resize',
                          exec_id=exec_id, height=height, width=width)

    def container_kill(self, context, container, signal):
        self._cast(container.host, 'container_kill', container=container,
                   signal=signal)

    @check_container_host
    def container_update(self, context, container, patch):
        return self._call(container.host, 'container_update',
                          container=container, patch=patch)

    def resize_container(self, context, container, patch):
        self._cast(container.host, 'resize_container',
                   container=container, patch=patch)

    @check_container_host
    def container_attach(self, context, container):
        return self._call(container.host, 'container_attach',
                          container=container)

    @check_container_host
    def container_resize(self, context, container, height, width):
        return self._call(container.host, 'container_resize',
                          container=container, height=height, width=width)

    @check_container_host
    def container_top(self, context, container, ps_args):
        return self._call(container.host, 'container_top',
                          container=container, ps_args=ps_args)

    @check_container_host
    def container_get_archive(self, context, container, path):
        return self._call(container.host, 'container_get_archive',
                          container=container, path=path)

    @check_container_host
    def container_put_archive(self, context, container, path, data):
        return self._call(container.host, 'container_put_archive',
                          container=container, path=path, data=data)

    @check_container_host
    def container_stats(self, context, container):
        return self._call(container.host, 'container_stats',
                          container=container)

    @check_container_host
    def container_commit(self, context, container, repository, tag):
        return self._call(container.host, 'container_commit',
                          container=container, repository=repository, tag=tag)

    def add_security_group(self, context, container, security_group):
        return self._cast(container.host, 'add_security_group',
                          container=container, security_group=security_group)

    def remove_security_group(self, context, container, security_group):
        return self._cast(container.host, 'remove_security_group',
                          container=container, security_group=security_group)

    def image_delete(self, context, image, host):
        self._cast(host, 'image_delete', image=image)

    def image_pull(self, context, image, host):
        self._cast(host, 'image_pull', image=image)

    def image_search(self, context, image, image_driver, exact_match,
                     host=None):
        return self._call(host, 'image_search', image=image,
                          image_driver_name=image_driver,
                          exact_match=exact_match)

    def capsule_create(self, context, host, capsule,
                       requested_networks, requested_volumes, limits):
        self._cast(host, 'capsule_create',
                   capsule=capsule,
                   requested_networks=requested_networks,
                   requested_volumes=requested_volumes,
                   limits=limits)

    def capsule_delete(self, context, capsule):
        return self._call(capsule.host, 'capsule_delete',
                          capsule=capsule)

    def network_detach(self, context, container, network):
        self._cast(container.host, 'network_detach',
                   container=container, network=network)

    def network_attach(self, context, container, requested_network):
        self._cast(container.host, 'network_attach',
                   container=container,
                   requested_network=requested_network)

    def network_create(self, context, new_network):
        host = None
        return self._call(host, 'network_create', network=new_network)
