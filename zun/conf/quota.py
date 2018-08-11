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

from oslo_config import cfg

quota_group = cfg.OptGroup(
    name='quota',
    title='Quota Options',
    help="""
Quota options allow to manage quotas in openstack zun deployment.
""")

quota_opts = [
    cfg.IntOpt(
        'containers',
        min=-1,
        default=40,
        help="""
The number of containers allowed per project.

Possible values

* A positive integer or 0.
* -1 to disable the quota.
"""),
    cfg.IntOpt(
        'memory',
        min=-1,
        default=50 * 1024,
        help="""
The number of megabytes of container RAM allowed per project.

Possible values:

* A positive integer or 0.
* -1 to disable the quota.
"""
    ),
    cfg.IntOpt(
        'cpu',
        min=-1,
        default=20,
        help="""
The number of container cores or vCPUs allowed per project.

Possitive values:

* A positive integer or 0.
* -1 to disable the quota.
"""
    ),
    cfg.IntOpt(
        'disk',
        min=-1,
        default=100,
        help="""
The number of gigabytes of container Disk allowed per project.

Possitive values:

* A possitive integer or 0.
* -1 to disable the quota.
"""
    ),
    cfg.StrOpt('driver',
               default='zun.common.quota.DbQuotaDriver',
               choices=('zun.common.quota.DbQuotaDriver',
                        'zun.common.quota.NoopQuotaDriver'),
               help="""
Provides abstraction for quota checks. Users can configure a specific
driver to use for quota checks.

Possible values:

* zun.common.quota.DbQuotaDriver: Stores quota limit information
  in the database and relies on te quota_* configuration options for default
  quota limit values. Counts quota usage on-demand.
* zun.common.quota.NoopQuotaDriver: Ignores quota and treats all resources as
  unlimited.
""")
]


def register_opts(conf):
    conf.register_group(quota_group)
    conf.register_opts(quota_opts, group=quota_group)


def list_opts():
    return {quota_group: quota_opts}
