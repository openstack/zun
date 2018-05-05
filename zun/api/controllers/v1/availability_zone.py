# Copyright (c) 2018 NEC, Corp.
#
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
from zun.api.controllers.v1 import collection
from zun.api.controllers.v1.views import availability_zone_view as view
from zun.api import utils as api_utils
from zun.common import exception
from zun.common import policy
import zun.conf
from zun import objects


CONF = zun.conf.CONF


def check_policy_on_availability_zones(availability_zone, action):
    context = pecan.request.context
    policy.enforce(context, action, availability_zone, action=action)


class AvailabilityZoneCollection(collection.Collection):
    """API representation of a collection of availability zones."""

    fields = {
        'availability_zones',
        'next'
    }

    """A list containing availability zone objects"""

    def __init__(self, **kwargs):
        super(AvailabilityZoneCollection, self).__init__(**kwargs)
        self._type = 'availability_zones'

    @staticmethod
    def convert_with_links(zones, limit, url=None,
                           expand=False, **kwargs):
        collection = AvailabilityZoneCollection()
        collection.availability_zones = [
            view.format_a_zone(url, p) for p in zones]
        collection.next = collection.get_next(limit, url=url, **kwargs)
        return collection


class AvailabilityZoneController(base.Controller):
    """Availability Zone info controller"""

    @pecan.expose('json')
    @exception.wrap_pecan_controller_exception
    def get_all(self, **kwargs):
        """Retrieve a list of availability zones"""

        context = pecan.request.context
        context.all_projects = True

        policy.enforce(context, "availability_zones:get_all",
                       action="availability_zones:get_all")
        return self._get_host_collection(**kwargs)

    def _get_host_collection(self, **kwargs):
        context = pecan.request.context
        limit = api_utils.validate_limit(kwargs.get('limit'))

        sort_dir = api_utils.validate_sort_dir(kwargs.get('sort_dir', 'asc'))
        sort_key = kwargs.get('sort_key', 'availability_zone')
        expand = kwargs.get('expand')
        marker_obj = None
        resource_url = kwargs.get('resource_url')
        marker = kwargs.get('marker')
        if marker:
            marker_obj = objects.ZunService.get_by_uuid(context, marker)
        services = objects.ZunService.list(context,
                                           limit,
                                           marker_obj,
                                           sort_key,
                                           sort_dir)
        zones = {}
        for service in services:
            zones[service.availability_zone] = service
        return AvailabilityZoneCollection.convert_with_links(zones.values(),
                                                             limit,
                                                             url=resource_url,
                                                             expand=expand,
                                                             sort_key=sort_key,
                                                             sort_dir=sort_dir)
