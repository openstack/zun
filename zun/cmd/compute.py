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

import os
import sys

from oslo_log import log as logging
from oslo_service import service

from zun.common.i18n import _LI
from zun.common import rpc_service
from zun.common import service as zun_service
from zun.compute import manager as compute_manager
import zun.conf

CONF = zun.conf.CONF
LOG = logging.getLogger(__name__)


def main():
    zun_service.prepare_service(sys.argv)

    LOG.info(_LI('Starting server in PID %s'), os.getpid())
    CONF.log_opt_values(LOG, logging.DEBUG)

    CONF.import_opt('topic', 'zun.conf.compute', group='compute')

    endpoints = [
        compute_manager.Manager(),
    ]

    server = rpc_service.Service.create(CONF.compute.topic, CONF.host,
                                        endpoints, binary='zun-compute')
    launcher = service.launch(CONF, server)
    launcher.wait()
