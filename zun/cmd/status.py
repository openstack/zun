# Copyright (c) 2018 NEC, Corp.
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
import shutil
import sys

from oslo_upgradecheck import common_checks
from oslo_upgradecheck import upgradecheck

from zun.common.i18n import _
import zun.conf

CONF = zun.conf.CONF


class Checks(upgradecheck.UpgradeCommands):

    """Contains upgrade checks

    Various upgrade checks should be added as separate methods in this class
    and added to _upgrade_checks tuple.
    """

    def _cmd_exists(self, cmd):
        try:
            return shutil.which(cmd) is not None
        except AttributeError:
            # shutil.which is not available in python 2.x so try an
            # alternative approach
            return any(
                os.access(os.path.join(path, cmd), os.X_OK)
                for path in os.environ["PATH"].split(os.pathsep)
            )

    def _numactl_check(self):
        """This is a check for existence of numactl binary

        It needs to be removed after adding any real upgrade check
        """
        if self._cmd_exists('numactl'):
            return upgradecheck.Result(upgradecheck.Code.SUCCESS)
        else:
            msg = _("The program 'numactl' is currently not installed.")
            return upgradecheck.Result(upgradecheck.Code.FAILURE, msg)

    _upgrade_checks = (
        (_('Numactl Check'), _numactl_check),
        (_('Policy File JSON to YAML Migration'),
         (common_checks.check_policy_json, {'conf': CONF})),
    )


def main():
    return upgradecheck.main(
        CONF, project='zun', upgrade_command=Checks())


if __name__ == '__main__':
    sys.exit(main())
