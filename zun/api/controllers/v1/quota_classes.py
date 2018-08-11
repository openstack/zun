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

import pecan

from zun.api.controllers import base
from zun.api.controllers.v1.schemas import quota_classes as schema
from zun.api import validation
from zun.common import exception
from zun.common import policy
from zun.common import quota
from zun import objects

QUOTAS = quota.QUOTAS


class QuotaClassController(base.Controller):
    """Controller for QuotaClass"""

    def _get_quotas(self, context, quota_class):
        return QUOTAS.get_class_quotas(context, quota_class)

    @pecan.expose('json')
    @exception.wrap_pecan_controller_exception
    @validation.validate_query_param(pecan.request, schema.query_param_update)
    @validation.validated(schema.query_param_update)
    def put(self, quota_class_name, **quota_classes_dict):
        context = pecan.request.context
        policy.enforce(context, 'quota_class:update',
                       action='quota_class:update')
        for key, value in quota_classes_dict.items():
            value = int(value)
            quota_class = objects.QuotaClass(
                context, class_name=quota_class_name,
                resource=key, hard_limit=value)
            try:
                quota_class.update(context)
            except exception.QuotaClassNotFound:
                quota_class.create(context)
        return self._get_quotas(context, quota_class_name)

    @pecan.expose('json')
    @exception.wrap_pecan_controller_exception
    def get(self, quota_class_name):
        context = pecan.request.context
        policy.enforce(context, 'quota_class:get',
                       action='quota_class:get')
        return self._get_quotas(context, quota_class_name)
