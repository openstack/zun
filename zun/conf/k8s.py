# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from oslo_config import cfg

k8s_group = cfg.OptGroup(name='k8s',
                         title='Options for k8s')

k8s_opts = [
    cfg.StrOpt('kubeconfig_file', help='Kubeconfig file to use for calls to k8s'),
    cfg.MultiStrOpt('device_profile_mappings',
                    help=('Mappings from device_profile names to k8s Device Plugin '
                          'resource annotations. Format should be '
                          '<device_plugin>=<k8s_resource>:<num>, e.g.: '
                          'nvidia_gpu=nvidia.com/gpu:1, where <num> is the number '
                          'of resources to request.')),
    cfg.StrOpt('neutron_network',
               help=('The Neutron network that corresponds to the k8s cluster network. '
                     'This should be a flat provider network with at least one subnet '
                     'that partially covers the k8s cluster IP space. Ideally it has '
                     'full coverage, e.g., if the k8s cluster is using 10.11.0.0/16, '
                     'the Neutron network should have a subnet with that CIDR. This '
                     'configuration is required if Floating IPs or connectivity '
                     'between Neutron and the k8s pods is desired. This can be an ID '
                     'or name of a network.')),
    cfg.IntOpt('execute_timeout',
               default=5,
               help='Timeout in seconds for executing a command in a k8s pod.'),
    cfg.IntOpt('archive_timeout',
               default=120,
               help=(
                'Timeout in seconds for archive commands. Larger values make it '
                'possible to upload/download larger sections of the file system, but '
                'will lock up the K8s worker in the process.'
               )),
]

ALL_OPTS = (k8s_opts)


def register_opts(conf):
    conf.register_group(k8s_group)
    conf.register_opts(ALL_OPTS, k8s_group)


def list_opts():
    return {k8s_group: ALL_OPTS}
