# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import functools
import six

from oslo_log import log
from oslo_service import periodic_task

from zun.common import context
from zun.container import driver
from zun import objects
from zun.objects import fields

LOG = log.getLogger(__name__)


def set_context(func):
    @functools.wraps(func)
    def handler(self, ctx):
        ctx = context.get_admin_context(all_tenants=True)
        func(self, ctx)
    return handler


class ContainerStatusSyncPeriodicJob(periodic_task.PeriodicTasks):
    def __init__(self, conf):
        self.host = conf.host
        self.driver = driver.load_container_driver(
            conf.container_driver)
        self.previous_state = {}
        super(ContainerStatusSyncPeriodicJob, self).__init__(conf)

    def _filter_containers_on_status_and_host(self, containers):
        statuses = [fields.ContainerStatus.CREATING]
        return filter(
            lambda container: container.status not in statuses and
            container.host == self.host, containers)

    def _find_changed_containers(self, current_state):
        new_containers = list(set(current_state) - set(self.previous_state))
        deleted_containers = list(set(self.previous_state) -
                                  set(current_state))
        changed_containers = [k for k in set(self.previous_state) &
                              set(current_state)
                              if current_state[k] != self.previous_state[k]]
        return new_containers + changed_containers, deleted_containers

    @periodic_task.periodic_task(run_immediately=True)
    @set_context
    def sync_container_status(self, ctx):
        LOG.debug('Update container status start')

        current_state = {container['Id']: container['State']
                         for container in self.driver.list()}

        changed_containers, deleted_containers = self._find_changed_containers(
            current_state)
        if not changed_containers and not deleted_containers:
            LOG.debug('No container status change from previous state')
            return

        self.previous_state = current_state
        all_containers = objects.Container.list(ctx)
        containers = self._filter_containers_on_status_and_host(all_containers)

        db_containers_map = {container.container_id: container
                             for container in containers}

        for container_id in changed_containers:
            if db_containers_map.get(container_id):
                old_status = db_containers_map.get(container_id).status
                try:
                    updated_container = self.driver.show(
                        db_containers_map.get(container_id))
                    if old_status != updated_container.status:
                        updated_container.save(ctx)
                        msg = 'Status of container %s changed from %s to %s'
                        LOG.info(msg % (updated_container.uuid, old_status,
                                        updated_container.status))
                except Exception as e:
                    LOG.exception("Unexpected exception: %s",
                                  six.text_type(e))

        for container_id in deleted_containers:
            if db_containers_map.get(container_id):
                try:
                    if ((db_containers_map.get(container_id).task_state !=
                         fields.TaskState.CONTAINER_DELETING or
                         db_containers_map.get(container_id).task_state !=
                         fields.TaskState.SANDBOX_DELETING)):
                        old_status = db_containers_map.get(container_id).status
                        updated_container = self.driver.show(
                            db_containers_map.get(container_id))
                        updated_container.save(ctx)
                        msg = 'Status of container %s changed from %s to %s'
                        LOG.info(msg % (updated_container.uuid, old_status,
                                        updated_container.status))
                except Exception as e:
                    LOG.exception("Unexpected exception: %s",
                                  six.text_type(e))

        LOG.debug('Update container status end')


def setup(conf, tg):
    pt = ContainerStatusSyncPeriodicJob(conf)
    tg.add_dynamic_timer(
        pt.run_periodic_tasks,
        periodic_interval_max=conf.periodic_interval_max,
        context=None)
