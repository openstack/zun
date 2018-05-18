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

import itertools

from zun.common.policies import availability_zone
from zun.common.policies import base
from zun.common.policies import capsule
from zun.common.policies import container
from zun.common.policies import container_action
from zun.common.policies import host
from zun.common.policies import image
from zun.common.policies import network
from zun.common.policies import quota
from zun.common.policies import quota_class
from zun.common.policies import zun_service


def list_rules():
    return itertools.chain(
        base.list_rules(),
        container.list_rules(),
        image.list_rules(),
        zun_service.list_rules(),
        host.list_rules(),
        capsule.list_rules(),
        network.list_rules(),
        container_action.list_rules(),
        availability_zone.list_rules(),
        quota.list_rules(),
        quota_class.list_rules()
    )
