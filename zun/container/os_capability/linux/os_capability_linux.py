# Copyright 2017 IBM Corp
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

from collections import defaultdict
import re
import six

from oslo_concurrency import processutils
from oslo_log import log as logging
from zun.common import exception
from zun.common.i18n import _LE
from zun.container.os_capability import host_capability


LOG = logging.getLogger(__name__)


class LinuxHost(host_capability.Host):

    def get_cpu_numa_info(self):
        # TODO(sbiswas7): rootwrap changes for zun required.
        old_lscpu = False
        try:
            output = processutils.execute('lscpu', '-p=socket,cpu,online')
        except processutils.ProcessExecutionError as e:
            LOG.exception(_LE("There was a problem while executing lscpu "
                          "-p=socket,cpu,online : %s"), six.text_type(e))
            # There is a possibility that an older version of lscpu is used
            # So let's try without the online column
            try:
                output = processutils.execute('lscpu', '-p=socket,cpu')
                old_lscpu = True
            except processutils.ProcessExecutionError as e:
                LOG.exception(_LE("There was a problem while executing lscpu "
                              "-p=socket,cpu : %s"), six.text_type(e))
                raise exception.CommandError(cmd="lscpu")
        if old_lscpu:
            cpu_sock_pair = re.findall("\d+(?:,\d+)?", str(output))
        else:
            cpu_sock_pair = re.findall("\d+(?:,\d+,[Y/N])?", str(output))
        sock_map = defaultdict(list)
        for value in cpu_sock_pair:
            val = value.split(",")
            if len(val) == 3 and val[2] == 'Y':
                sock_map[val[0]].append(int(val[1]))
            elif len(val) == 2 and old_lscpu:
                sock_map[val[0]].append(int(val[1]))
        return sock_map
