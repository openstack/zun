# Copyright (c) 2014 Red Hat, Inc.
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

from stevedore import driver
import zun.conf

CONF = zun.conf.CONF


class SchedulerClient(object):
    """Client library for placing calls to the scheduler."""

    def __init__(self):
        scheduler_driver = CONF.scheduler.driver
        self.driver = driver.DriverManager(
            "zun.scheduler.driver",
            scheduler_driver,
            invoke_on_load=True).driver

    def select_destinations(self, context, containers, extra_spec):
        return self.driver.select_destinations(context, containers, extra_spec)

    def update_resource(self, node):
        node.save()
        # TODO(Shunli): Update the inventory here
