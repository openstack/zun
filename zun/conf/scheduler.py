# Copyright 2015 OpenStack Foundation
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

from oslo_config import cfg


scheduler_group = cfg.OptGroup(name="scheduler",
                               title="Scheduler configuration")

scheduler_opts = [
    cfg.StrOpt("driver",
               default="chance_scheduler",
               choices=("chance_scheduler", "fake_scheduler"),
               help="""
The class of the driver used by the scheduler.

The options are chosen from the entry points under the namespace
'zun.scheduler.driver' in 'setup.cfg'.

Possible values:

* A string, where the string corresponds to the class name of a scheduler
  driver. There are a number of options available:
** 'chance_scheduler', which simply picks a host at random
** A custom scheduler driver. In this case, you will be responsible for
   creating and maintaining the entry point in your 'setup.cfg' file
"""),
]


def register_opts(conf):
    conf.register_group(scheduler_group)
    conf.register_opts(scheduler_opts, group=scheduler_group)


def list_opts():
    return {scheduler_group: scheduler_opts}
