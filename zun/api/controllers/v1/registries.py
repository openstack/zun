# All Rights Reserved.
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

from oslo_log import log as logging
import pecan

from zun.api.controllers import base
from zun.api.controllers import link
from zun.api.controllers.v1 import collection
from zun.api.controllers.v1.schemas import registries as schema
from zun.api.controllers.v1.views import registries_view as view
from zun.api import utils as api_utils
from zun.api import validation
from zun.common import exception
from zun.common.i18n import _
from zun.common.policies import registry as policies
from zun.common import policy
from zun.common import utils
import zun.conf
from zun import objects


CONF = zun.conf.CONF

LOG = logging.getLogger(__name__)

RESOURCE_NAME = 'registry'
COLLECTION_NAME = 'registries'


def check_policy_on_registry(registry, action):
    context = pecan.request.context
    policy.enforce(context, action, registry, action=action)


class RegistryCollection(collection.Collection):
    """API representation of a collection of registries."""

    fields = {
        COLLECTION_NAME,
        'next'
    }

    """A list containing registries objects"""

    def __init__(self, **kwargs):
        super(RegistryCollection, self).__init__(**kwargs)
        self._type = COLLECTION_NAME

    @staticmethod
    def convert_with_links(rpc_registries, limit, url=None,
                           **kwargs):
        context = pecan.request.context
        collection = RegistryCollection()
        collection.registries = \
            [view.format_registry(context, url, r.as_dict())
             for r in rpc_registries]
        collection.next = collection.get_next(limit, url=url, **kwargs)
        return collection


class RegistryItem(collection.Item):
    """API representation of an registry."""

    fields = {
        RESOURCE_NAME,
    }

    @staticmethod
    def render_response(rpc_registry):
        context = pecan.request.context
        url = pecan.request.host_url
        item = RegistryItem()
        item.registry = view.format_registry(context, url,
                                             rpc_registry.as_dict())
        return item


class RegistryController(base.Controller):
    """Controller for Registries."""

    @pecan.expose('json')
    @exception.wrap_pecan_controller_exception
    def get_all(self, **kwargs):
        """Retrieve a list of registries.

        """
        context = pecan.request.context
        policy_action = policies.REGISTRY % 'get_all'
        policy.enforce(context, policy_action, action=policy_action)
        return self._get_registries_collection(**kwargs)

    def _get_registries_collection(self, **kwargs):
        context = pecan.request.context
        if utils.is_all_projects(kwargs):
            policy_action = policies.REGISTRY % 'get_all_all_projects'
            policy.enforce(context, policy_action, action=policy_action)
            context.all_projects = True
        kwargs.pop('all_projects', None)
        limit = api_utils.validate_limit(kwargs.pop('limit', None))
        sort_dir = api_utils.validate_sort_dir(kwargs.pop('sort_dir', 'asc'))
        sort_key = kwargs.pop('sort_key', 'id')
        resource_url = kwargs.pop('resource_url', None)

        registry_allowed_filters = ['name', 'domain', 'username',
                                    'project_id', 'user_id']
        filters = {}
        for filter_key in registry_allowed_filters:
            if filter_key in kwargs:
                policy_action = policies.REGISTRY % ('get_one:' + filter_key)
                context.can(policy_action, might_not_exist=True)
                filter_value = kwargs.pop(filter_key)
                filters[filter_key] = filter_value
        marker_obj = None
        marker = kwargs.pop('marker', None)
        if marker:
            marker_obj = objects.Registry.get_by_uuid(context, marker)
        if kwargs:
            unknown_params = [str(k) for k in kwargs]
            msg = _("Unknown parameters: %s") % ", ".join(unknown_params)
            raise exception.InvalidValue(msg)

        registries = objects.Registry.list(context,
                                           limit,
                                           marker_obj,
                                           sort_key,
                                           sort_dir,
                                           filters=filters)
        return RegistryCollection.convert_with_links(registries, limit,
                                                     url=resource_url,
                                                     sort_key=sort_key,
                                                     sort_dir=sort_dir)

    @pecan.expose('json')
    @exception.wrap_pecan_controller_exception
    def get_one(self, registry_ident, **kwargs):
        """Retrieve information about the given registry.

        :param registry_ident: UUID or name of a registry.
        """
        context = pecan.request.context
        if context.is_admin:
            context.all_projects = True
        registry = utils.get_registry(registry_ident)
        policy_action = policies.REGISTRY % 'get_one'
        check_policy_on_registry(registry.as_dict(), policy_action)
        return RegistryItem.render_response(registry)

    @pecan.expose('json')
    @api_utils.enforce_content_types(['application/json'])
    @exception.wrap_pecan_controller_exception
    @validation.validated(schema.registry_create)
    def post(self, run=False, **registry_dict):
        context = pecan.request.context
        policy_action = policies.REGISTRY % 'create'
        policy.enforce(context, policy_action, action=policy_action)
        registry_dict = registry_dict.get(RESOURCE_NAME)
        registry_dict['project_id'] = context.project_id
        registry_dict['user_id'] = context.user_id
        new_registry = objects.Registry(context, **registry_dict)
        new_registry.create(context)
        # Set the HTTP Location Header
        pecan.response.location = link.build_url(COLLECTION_NAME,
                                                 new_registry.uuid)
        pecan.response.status = 201
        return RegistryItem.render_response(new_registry)

    @pecan.expose('json')
    @exception.wrap_pecan_controller_exception
    @validation.validated(schema.registry_update)
    def patch(self, registry_ident, **registry_dict):
        """Update an existing registry.

        :param registry_ident: UUID or name of a registry.
        :param registry_dict: a json document to apply to this registry.
        """
        registry = utils.get_registry(registry_ident)
        context = pecan.request.context
        policy_action = policies.REGISTRY % 'update'
        check_policy_on_registry(registry.as_dict(), policy_action)
        registry_dict = registry_dict.get(RESOURCE_NAME)
        if 'name' in registry_dict:
            registry.name = registry_dict['name']
        if 'domain' in registry_dict:
            registry.domain = registry_dict['domain']
        if 'username' in registry_dict:
            registry.username = registry_dict['username']
        if 'password' in registry_dict:
            registry.password = registry_dict['password']
        registry.save(context)
        return RegistryItem.render_response(registry)

    @pecan.expose('json')
    @exception.wrap_pecan_controller_exception
    def delete(self, registry_ident, **kwargs):
        """Delete a registry.

        :param registry_ident: UUID or Name of a registry.
        :param force: If True, allow to force delete the registry.
        """
        context = pecan.request.context
        if context.is_admin:
            context.all_projects = True
        registry = utils.get_registry(registry_ident)
        policy_action = policies.REGISTRY % 'delete'
        check_policy_on_registry(registry.as_dict(), policy_action)
        registry.destroy(context)
        pecan.response.status = 204
