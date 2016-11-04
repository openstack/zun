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
from pecan import rest

from zun.api.controllers import base
from zun.api.controllers import types
from zun.api.controllers.v1 import collection
from zun.api import servicegroup as svcgrp_api
from zun.common import exception
from zun.common import policy
from zun import objects


class ZunService(base.APIBase):

    fields = {
        'host': {
            'validate': types.String.validate,
            'validate_args': {
                'min_length': 1,
                'max_length': 255,
            },
        },
        'binary': {
            'validate': types.String.validate,
            'validate_args': {
                'min_length': 1,
                'max_length': 255,
            },
        },
        'state': {
            'validate': types.String.validate,
            'validate_args': {
                'min_length': 1,
                'max_length': 255,
            },
        },
        'id': {
            'validate': types.Integer.validate,
            'validate_args': {
                'minimum': 1,
            },
        },
        'report_count': {
            'validate': types.Integer.validate,
            'validate_args': {
                'minimum': 0,
            },
        },
        'disabled': {
            'validate': types.Bool.validate,
            'validate_args': {
                'default': False,
            },
        },
        'disabled_reason': {
            'validate': types.String.validate,
            'validate_args': {
                'min_length': 0,
                'max_length': 255,
            },
        },
        'created_at': {
            'validate': types.DateTime.validate,
        },
        'updated_at': {
            'validate': types.DateTime.validate,
        },
    }

    def __init__(self, state, **kwargs):
        super(ZunService, self).__init__(**kwargs)
        setattr(self, 'state', state)


class ZunServiceCollection(collection.Collection):

    fields = {
        'services': {
            'validate': types.List(types.Custom(ZunService)).validate,
        },
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
            alive = servicegroup_api.service_is_up(p)
            state = 'up' if alive else 'down'
            hsvc = ZunService(state, **p.as_dict())
            collection.services.append(hsvc)
        next = collection.get_next(limit=None, url=None, **kwargs)
        if next is not None:
            collection.next = next
        return collection


class ZunServiceController(rest.RestController):
    """REST controller for zun-services."""

    def __init__(self, **kwargs):
        super(ZunServiceController, self).__init__()
        self.servicegroup_api = svcgrp_api.ServiceGroup()

    @pecan.expose('json')
    @exception.wrap_pecan_controller_exception
    def get_all(self, **kwargs):
        """Retrieve a list of zun-services.

        """
        context = pecan.request.context
        policy.enforce(context, "zun-service:get_all",
                       action="zun-service:get_all")
        hsvcs = objects.ZunService.list(pecan.request.context,
                                        limit=None,
                                        marker=None,
                                        sort_key='id',
                                        sort_dir='asc')
        return ZunServiceCollection.convert_db_rec_list_to_collection(
            self.servicegroup_api, hsvcs)
