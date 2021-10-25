# Copyright 2021 University of Chicago
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import copy
from zun.tests.unit.scheduler.fake_loadables.fake_loadable1 import FakeLoadableSubClass1

# The possible sets for capabilities, from the manual
# https://man7.org/linux/man-pages/man7/capabilities.7.html
CAP_SETS = ["bounding", "permitted", "inheritable", "effective", "ambient"]

def merge_oci_runtime_config(parent, *cfgs):
    merged = copy.deepcopy(parent)
    env = merged.setdefault('process', {}).setdefault('env', [])
    mounts = merged.setdefault('mounts', [])
    devices = merged.setdefault('linux', {}).setdefault('devices', [])
    capabilities = merged.setdefault('capabilities', {})
    for group in CAP_SETS:
        capabilities.setdefault(group, [])
    for cfg in cfgs:
        cfg_env = cfg.get('process', {}).get('env')
        if cfg_env is not None:
            env.extend(cfg_env)
        cfg_mounts = cfg.get('mounts')
        if cfg_mounts is not None:
            mounts.extend(cfg_mounts)
        cfg_devices = cfg.get('linux', {}).get('devices')
        if cfg_devices is not None:
            devices.extend(cfg_devices)
        cfg_capabilities = cfg.get('linux', {}).get('capabilities')
        if cfg_capabilities is not None:
            for group in CAP_SETS:
                caps = cfg_capabilities.get(group, [])
                for cap in caps:
                    if cap not in capabilities[group]:
                        capabilities[group].append(cap)
            capabilities.update(cfg_capabilities)
    return merged


def from_dot_notation(cfg):
    parsed_cfg = {}

    def _peek(parts, i):
        return parts[i] if len(parts) > i else None

    def _next_value(next_part, default):
        if not next_part:
            return default
        try:
            int(next_part)
            return []
        except ValueError:
            return {}

    for key, value in cfg.items():
        node = parsed_cfg
        parts = key.split(".")
        for i, _key in enumerate(parts):
            next_part = _peek(parts, i+1)
            next_value = _next_value(next_part, value)
            if isinstance(node, list):
                idx = int(_key)
                if idx == len(node):
                    node.append(next_value)
                node = node[idx]
            else:
                node = node.setdefault(_key, next_value)
    return parsed_cfg
