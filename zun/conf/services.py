# -*- encoding: utf-8 -*-
#
# Copyright © 2012 eNovance <licensing@enovance.com>
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from oslo_config import cfg


periodic_opts = [
    cfg.IntOpt('periodic_interval_max',
               default=60,
               help='Max interval size between periodic tasks execution in '
                    'seconds.'),
    cfg.IntOpt('service_down_time',
               default=180,
               help='Max interval size between periodic tasks execution in '
                    'seconds.'),
    cfg.IntOpt('sync_container_state_interval',
               default=60,
               help="""
Interval to sync container states between the database and the docker.

The interval that Zun checks the actual container state and
the state that Zun has recorded in its database. If they are inconsistent,
Zun will update the database according to the actual container state.

Possible values:
* 0: Will run at the default periodic interval.
* Any value < 0: Disables the option.
* Any positive integer in seconds.

"""),
]


ALL_OPTS = (periodic_opts)


def register_opts(conf):
    conf.register_opts(ALL_OPTS)


def list_opts():
    return {"DEFAULT": ALL_OPTS}
