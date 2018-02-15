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

from oslo_utils import strutils
import pecan
import six

from zun.api.controllers import base
from zun.api.controllers.v1 import collection
from zun.api.controllers.v1.schemas import services as schema
from zun.api import servicegroup as svcgrp_api
from zun.api import validation
from zun.common import exception
from zun.common import policy
import zun.conf
from zun import objects


CONF = zun.conf.CONF


class ZunServiceCollection(collection.Collection):

    fields = {
        'services',
        'next'
    }

    def __init__(self, **kwargs):
        super(ZunServiceCollection, self).__init__()
        self._type = 'services'

    @staticmethod
    def convert_db_rec_list_to_collection(servicegroup_api,
                                          rpc_hsvcs, **kwargs):
        collection = ZunServiceCollection()
        collection.services = []
        for p in rpc_hsvcs:
            service = p.as_dict()
            alive = servicegroup_api.service_is_up(p)
            state = 'up' if alive else 'down'
            service['state'] = state
            collection.services.append(service)
            if not service['availability_zone']:
                service['availability_zone'] = CONF.default_availability_zone
        next = collection.get_next(limit=None, url=None, **kwargs)
        if next is not None:
            collection.next = next
        return collection


class ZunServiceController(base.Controller):
    """REST controller for zun-services."""

    _custom_actions = {
        'enable': ['PUT'],
        'disable': ['PUT'],
        'force_down': ['PUT'],
    }

    def __init__(self, **kwargs):
        super(ZunServiceController, self).__init__()
        self.servicegroup_api = svcgrp_api.ServiceGroup()

    def _update(self, context, host, binary, payload):
        """Do the actual update"""
        svc = objects.ZunService.get_by_host_and_binary(
            context, host, binary)
        if svc is None:
            raise exception.ZunServiceNotFound(
                binary=binary, host=host)
        else:
            return svc.update(context, payload)

    def _enable_or_disable(self, context, body, params_to_update):
        """Enable/Disable scheduling for a service."""
        self._update(context, body['host'], body['binary'],
                     params_to_update)
        res = {
            'service': {
                'host': body['host'],
                'binary': body['binary'],
                'disabled': params_to_update['disabled'],
                'disabled_reason': params_to_update['disabled_reason']
            },
        }
        return res

    def _enable(self, context, body):
        """Enable scheduling for a service."""
        return self._enable_or_disable(context, body,
                                       {'disabled': False,
                                        'disabled_reason': None})

    def _disable(self, context, body, reason=None):
        """Disable scheduling for a service with optional log."""
        return self._enable_or_disable(context, body,
                                       {'disabled': True,
                                        'disabled_reason': reason})

    def _update_forced_down(self, context, body):
        """Set or unset forced_down flag for the service"""
        try:
            forced_down = strutils.bool_from_string(body['forced_down'], True)
        except ValueError as err:
            raise exception.InvalidValue(six.text_type(err))
        self._update(context, body['host'], body['binary'],
                     {"forced_down": forced_down})
        res = {
            'service': {
                'host': body['host'],
                'binary': body['binary'],
                'forced_down': forced_down
            },
        }
        return res

    @pecan.expose('json')
    @exception.wrap_pecan_controller_exception
    def get_all(self, **kwargs):
        """Retrieve a list of zun-services.

        """
        context = pecan.request.context
        policy.enforce(context, "zun-service:get_all",
                       action="zun-service:get_all")
        hsvcs = objects.ZunService.list(context,
                                        limit=None,
                                        marker=None,
                                        sort_key='id',
                                        sort_dir='asc')
        return ZunServiceCollection.convert_db_rec_list_to_collection(
            self.servicegroup_api, hsvcs)

    @pecan.expose('json')
    @exception.wrap_pecan_controller_exception
    def delete(self, host, binary):
        """Delete the specified service.

        :param host: The host on which the binary is running.
        :param binary: The name of the binary.
        """
        context = pecan.request.context
        policy.enforce(context, "zun-service:delete",
                       action="zun-service:delete")
        svc = objects.ZunService.get_by_host_and_binary(
            context, host, binary)
        if svc is None:
            raise exception.ZunServiceNotFound(
                binary=binary, host=host)
        else:
            svc.destroy(context)

    @pecan.expose('json')
    @exception.wrap_pecan_controller_exception
    @validation.validate_query_param(pecan.request,
                                     schema.query_param_enable)
    def enable(self, **kwargs):
        context = pecan.request.context
        policy.enforce(context, "zun-service:enable",
                       action="zun-service:enable")
        return self._enable(context, kwargs)

    @pecan.expose('json')
    @exception.wrap_pecan_controller_exception
    @validation.validate_query_param(pecan.request,
                                     schema.query_param_disable)
    def disable(self, **kwargs):
        context = pecan.request.context
        policy.enforce(context, "zun-service:disable",
                       action="zun-service:disable")
        if 'disabled_reason' in kwargs:
            reason = kwargs['disabled_reason']
        else:
            reason = None
        return self._disable(context, kwargs, reason)

    @pecan.expose('json')
    @exception.wrap_pecan_controller_exception
    @validation.validate_query_param(pecan.request,
                                     schema.query_param_force_down)
    def force_down(self, **kwargs):
        context = pecan.request.context
        policy.enforce(context, "zun-service:force_down",
                       action="zun-service:force_down")
        return self._update_forced_down(context, kwargs)
