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

from zun.common.i18n import _


cni_daemon_group = cfg.OptGroup(name='cni_daemon',
                                title='Options for zun-cni-daemon')

daemon_opts = [
    cfg.PortOpt('cni_daemon_port',
                default=9036,
                help=_('The port for the CNI daemon.')),
    cfg.IPOpt('cni_daemon_host',
              default='127.0.0.1',
              help=_('Bind address for CNI daemon HTTP server. It is '
                     'recommened to allow only local connections.')),
    cfg.IntOpt('worker_num',
               help=_('Maximum number of processes that will be spawned to '
                      'process requests from CNI driver.'),
               default=30),
    cfg.IntOpt('vif_active_timeout',
               help=_('Time (in seconds) the CNI daemon will wait for VIF '
                      'to be active.'),
               default=60),
    cfg.IntOpt('pyroute2_timeout',
               help=_('Zun uses pyroute2 library to manipulate networking '
                      'interfaces. When processing a high number of Zun '
                      'requests in parallel, it may take kernel more time to '
                      'process all networking stack changes. This option '
                      'allows to tune internal pyroute2 timeout.'),
               default=10),
    cfg.BoolOpt('docker_mode',
                help=_('Set to True when you are running zun-cni-daemon '
                       'inside a Docker container. This mainly means that '
                       'zun-cni-daemon will look for network namespaces in '
                       '$netns_proc_dir instead of /proc.'),
                default=False),
    cfg.StrOpt('netns_proc_dir',
               help=_("When docker_mode is set to True, this config option "
                      "should be set to where host's /proc directory is "
                      "mounted. Please note that mounting it is necessary to "
                      "allow Zun to move host interfaces between "
                      "host network namespaces, which is essential for Zun "
                      "to work."),
               default=None),
    cfg.DictOpt('sriov_physnet_resource_mappings',
                help=_("A mapping of physnets for certain sriov dp "
                       "resource name in a form of "
                       "physnet-name:resource name. "
                       "Resource name is listed in sriov device plugin "
                       "configuation file."),
                default={}),
    cfg.DictOpt('sriov_resource_driver_mappings',
                help=_("A mappping driver names for certain resource "
                       "names. Expected that device of VIF related to "
                       "exact physnet should be binded on specified driver."),
                default={}),
    cfg.StrOpt('zun_cni_config_file',
               help=_("Path to the Zun CNI config file."),
               default='/etc/cni/net.d/10-zun-cni.conf'),
]

ALL_OPTS = (daemon_opts)


def register_opts(conf):
    conf.register_group(cni_daemon_group)
    conf.register_opts(ALL_OPTS, cni_daemon_group)


def list_opts():
    return {cni_daemon_group: ALL_OPTS}
