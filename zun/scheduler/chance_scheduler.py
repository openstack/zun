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
Chance (Random) Scheduler implementation
"""

import random

from zun.common import exception
from zun.common.i18n import _
from zun.scheduler import driver


class ChanceScheduler(driver.Scheduler):
    """Implements Scheduler as a random node selector."""

    def _schedule(self, context):
        """Picks a host that is up at random."""
        hosts = self.hosts_up(context)
        if not hosts:
            msg = _("Is the appropriate service running?")
            raise exception.NoValidHost(reason=msg)

        return random.choice(hosts)

    def select_destinations(self, context, containers, extra_spec):
        """Selects random destinations."""
        dests = []
        for container in containers:
            host = self._schedule(context)
            host_state = dict(host=host, nodename=None, limits=None)
            dests.append(host_state)

        if len(dests) < 1:
            reason = _('There are not enough hosts available.')
            raise exception.NoValidHost(reason=reason)

        return dests
