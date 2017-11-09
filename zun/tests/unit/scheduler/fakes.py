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

from zun.scheduler import driver
from zun.scheduler import host_state


class FakeScheduler(driver.Scheduler):

    def select_destinations(self, context, containers):
        return []


class FakeHostState(host_state.HostState):
    def __init__(self, host, attribute_dict=None):
        super(FakeHostState, self).__init__(host)
        if attribute_dict:
            for (key, val) in attribute_dict.items():
                setattr(self, key, val)


class FakeService(object):

    def __init__(self, name, host, disabled=False):
        self.name = name
        self.host = host
        self.disabled = disabled
