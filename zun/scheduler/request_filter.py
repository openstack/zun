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

from oslo_log import log as logging

from zun.common import consts
import zun.conf


CONF = zun.conf.CONF
LOG = logging.getLogger(__name__)


def compute_status_filter(ctxt, extra_specs):
    """Pre-filter node resource providers using ZUN_COMPUTE_STATUS_DISABLED

    The ComputeFilter filters out hosts for compute services that are
    disabled. Compute node resource providers managed by a disabled compute
    service should have the ZUN_COMPUTE_STATUS_DISABLED trait set and be
    excluded by this mandatory pre-filter.
    """
    trait_name = consts.ZUN_COMPUTE_STATUS_DISABLED
    extra_specs['trait:%s' % trait_name] = 'forbidden'
    LOG.debug('compute_status_filter request filter added forbidden '
              'trait %s', trait_name)
    return True


ALL_REQUEST_FILTERS = [
    compute_status_filter,
]


def process_reqspec(ctxt, extra_specs):
    """Process an objects.ReqestSpec before calling placement."""
    for filter in ALL_REQUEST_FILTERS:
        filter(ctxt, extra_specs)
