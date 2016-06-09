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

from oslo_config import cfg
from oslo_log import log as logging
from oslo_service import service

from higgins.common import rpc_service
from higgins.common import service as higgins_service
from higgins.common import short_id
from higgins.compute import manager as compute_manager
from higgins.i18n import _LI

LOG = logging.getLogger(__name__)


def main():
    higgins_service.prepare_service(sys.argv)

    LOG.info(_LI('Starting server in PID %s'), os.getpid())
    cfg.CONF.log_opt_values(LOG, logging.DEBUG)

    cfg.CONF.import_opt('topic', 'higgins.compute.config', group='compute')

    compute_id = short_id.generate_id()
    endpoints = [
        compute_manager.Manager(),
    ]

    server = rpc_service.Service.create(cfg.CONF.compute.topic, compute_id,
                                        endpoints, binary='higgins-compute')
    launcher = service.launch(cfg.CONF, server)
    launcher.wait()
