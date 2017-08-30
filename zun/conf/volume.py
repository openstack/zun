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


volume_group = cfg.OptGroup(name='volume',
                            title='Options for the container volume')

volume_opts = [
    cfg.StrOpt('driver',
               default='cinder',
               help='Defines which driver to use for container volume.'),
    cfg.StrOpt('volume_dir',
               default='$state_path/mnt',
               help='At which the docker volume will create.'),
    cfg.StrOpt('fstype',
               default='ext4',
               help='Default filesystem type for volume.'),
    cfg.BoolOpt('use_multipath',
                default=False,
                help="""
Use multipath connection of volume

Volumes can be connected as multipath devices. This will provide high
availability and fault tolerance.
"""),
]


ALL_OPTS = (volume_opts)


def register_opts(conf):
    conf.register_group(volume_group)
    conf.register_opts(ALL_OPTS, group=volume_group)


def list_opts():
    return {volume_group: ALL_OPTS}
