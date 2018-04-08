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

"""Zun Service Layer"""

from oslo_log import log
from oslo_service import periodic_task

from zun.common import context
from zun import objects


LOG = log.getLogger(__name__)


class ZunServicePeriodicTasks(periodic_task.PeriodicTasks):
    """Zun periodic Task class

    Any periodic task job need to be added into this class
    """

    def __init__(self, conf, binary):
        self.zun_service_ref = None
        self.host = conf.host
        self.binary = binary
        self.availability_zone = conf.default_availability_zone
        super(ZunServicePeriodicTasks, self).__init__(conf)

    @periodic_task.periodic_task(run_immediately=True)
    @context.set_context
    def update_zun_service(self, ctx):
        LOG.debug('Update zun_service')
        if self.zun_service_ref is None:
            self.zun_service_ref = \
                objects.ZunService.get_by_host_and_binary(
                    ctx, self.host, self.binary)
            if self.zun_service_ref is None:
                zun_service_dict = {
                    'host': self.host,
                    'binary': self.binary
                }
                self.zun_service_ref = objects.ZunService(
                    ctx, **zun_service_dict)
                self.zun_service_ref.create()
        self.zun_service_ref.availability_zone = self.availability_zone
        self.zun_service_ref.report_state_up()


def setup(conf, binary, tg):
    pt = ZunServicePeriodicTasks(conf, binary)
    tg.add_dynamic_timer(
        pt.run_periodic_tasks,
        periodic_interval_max=conf.periodic_interval_max,
        context=None)
