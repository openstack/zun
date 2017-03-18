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

"""Handles all requests relating to compute resources (e.g. containers,
networking and storage of containers, and compute hosts on which they run)."""

from zun.common import profiler
from zun.compute import rpcapi
from zun.objects import fields
from zun.scheduler import client as scheduler_client


@profiler.trace_cls("rpc")
class API(object):
    """API for interacting with the compute manager."""

    def __init__(self, context):
        self.rpcapi = rpcapi.API(context=context)
        self.scheduler_client = scheduler_client.SchedulerClient()
        super(API, self).__init__()

    def container_create(self, context, new_container):
        try:
            self._schedule_container(context, new_container)
        except Exception as exc:
            new_container.status = fields.ContainerStatus.ERROR
            new_container.status_reason = str(exc)
            new_container.save(context)
            return

        self.rpcapi.container_create(context, new_container)

    def container_run(self, context, new_container):
        try:
            self._schedule_container(context, new_container)
        except Exception as exc:
            new_container.status = fields.ContainerStatus.ERROR
            new_container.status_reason = str(exc)
            new_container.save(context)
            return

        self.rpcapi.container_run(context, new_container)

    def _schedule_container(self, context, new_container):
        dests = self.scheduler_client.select_destinations(context,
                                                          [new_container])
        new_container.host = dests[0]['host']
        new_container.save(context)

    def container_delete(self, context, container, *args):
        return self.rpcapi.container_delete(context, container, *args)

    def container_show(self, context, container, *args):
        return self.rpcapi.container_show(context, container, *args)

    def container_reboot(self, context, container, *args):
        return self.rpcapi.container_reboot(context, container, *args)

    def container_stop(self, context, container, *args):
        return self.rpcapi.container_stop(context, container, *args)

    def container_start(self, context, container, *args):
        return self.rpcapi.container_start(context, container, *args)

    def container_pause(self, context, container, *args):
        return self.rpcapi.container_pause(context, container, *args)

    def container_unpause(self, context, container, *args):
        return self.rpcapi.container_unpause(context, container, *args)

    def container_logs(self, context, container, stdout, stderr,
                       timestamps, tail, since):
        return self.rpcapi.container_logs(context, container, stdout, stderr,
                                          timestamps, tail, since)

    def container_exec(self, context, container, *args):
        return self.rpcapi.container_exec(context, container, *args)

    def container_kill(self, context, container, *args):
        return self.rpcapi.container_kill(context, container, *args)

    def container_update(self, context, container, *args):
        return self.rpcapi.container_update(context, container, *args)

    def container_attach(self, context, container, *args):
        return self.rpcapi.container_attach(context, container, *args)

    def container_resize(self, context, container, *args):
        return self.rpcapi.container_resize(context, container, *args)

    def container_top(self, context, container, *args):
        return self.rpcapi.container_top(context, container, *args)

    def container_get_archive(self, context, container, *args):
        return self.rpcapi.container_get_archive(context, container, *args)

    def container_put_archive(self, context, container, *args):
        return self.rpcapi.container_put_archive(context, container, *args)

    def image_pull(self, context, image, *args):
        return self.rpcapi.image_pull(context, image, *args)

    def image_search(self, context, image, image_driver, *args):
        return self.rpcapi.image_search(context, image, image_driver, *args)
