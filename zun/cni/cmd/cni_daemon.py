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

import shlex
import sys

import os_vif
from oslo_privsep import priv_context

from zun.cni.daemon import service
from zun.common import config
from zun.common import service as zun_service
from zun.common import utils


def main():
    priv_context.init(root_helper=shlex.split(utils.get_root_helper()))
    zun_service.prepare_service(sys.argv)
    config.parse_args(sys.argv)

    # Initialize o.vo registry.
    os_vif.initialize()

    service.CNIDaemonServiceManager().run()


if __name__ == '__main__':
    sys.exit(main())
