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

import functools

import copy
from oslo_context import context
from oslo_utils import timeutils
import six

from zun.common import exception
from zun.common import policy


class RequestContext(context.RequestContext):
    """Extends security contexts from the OpenStack common library."""

    def __init__(self, auth_token=None, domain_id=None,
                 domain_name=None, user_name=None, user_id=None,
                 user_domain_name=None, user_domain_id=None,
                 project_name=None, project_id=None, roles=None,
                 is_admin=None, read_only=False, show_deleted=False,
                 request_id=None, trust_id=None, auth_token_info=None,
                 all_projects=False, password=None, timestamp=None, **kwargs):
        """Stores several additional request parameters:

        :param domain_id: The ID of the domain.
        :param domain_name: The name of the domain.
        :param user_domain_id: The ID of the domain to
                               authenticate a user against.
        :param user_domain_name: The name of the domain to
                                 authenticate a user against.

        """
        super(RequestContext, self).__init__(auth_token=auth_token,
                                             user_id=user_name,
                                             project_id=project_name,
                                             is_admin=is_admin,
                                             read_only=read_only,
                                             show_deleted=show_deleted,
                                             request_id=request_id,
                                             roles=roles)

        self.user_name = user_name
        self.user_id = user_id
        self.project_name = project_name
        self.project_id = project_id
        self.domain_id = domain_id
        self.domain_name = domain_name
        self.user_domain_id = user_domain_id
        self.user_domain_name = user_domain_name
        self.auth_token_info = auth_token_info
        self.trust_id = trust_id
        self.all_projects = all_projects
        self.password = password
        if is_admin is None:
            self.is_admin = policy.check_is_admin(self)
        else:
            self.is_admin = is_admin

        if not timestamp:
            timestamp = timeutils.utcnow()
        if isinstance(timestamp, six.string_types):
            timestamp = timeutils.parse_strtime(timestamp)
        self.timestamp = timestamp

    def to_dict(self):
        value = super(RequestContext, self).to_dict()
        value.update({'auth_token': self.auth_token,
                      'domain_id': self.domain_id,
                      'domain_name': self.domain_name,
                      'user_domain_id': self.user_domain_id,
                      'user_domain_name': self.user_domain_name,
                      'user_name': self.user_name,
                      'user_id': self.user_id,
                      'project_name': self.project_name,
                      'project_id': self.project_id,
                      'is_admin': self.is_admin,
                      'read_only': self.read_only,
                      'roles': self.roles,
                      'show_deleted': self.show_deleted,
                      'request_id': self.request_id,
                      'trust_id': self.trust_id,
                      'auth_token_info': self.auth_token_info,
                      'password': self.password,
                      'all_projects': self.all_projects,
                      'timestamp': timeutils.strtime(self.timestamp) if
                      hasattr(self, 'timestamp') else None
                      })
        return value

    def to_policy_values(self):
        policy = super(RequestContext, self).to_policy_values()
        policy['is_admin'] = self.is_admin
        return policy

    @classmethod
    def from_dict(cls, values):
        return cls(**values)

    def elevated(self):
        """Return a version of this context with admin flag set."""
        context = copy.copy(self)
        # context.roles must be deepcopied to leave original roles
        # without changes
        context.roles = copy.deepcopy(self.roles)
        context.is_admin = True

        if 'admin' not in context.roles:
            context.roles.append('admin')

        return context

    def can(self, action, target=None, fatal=True, might_not_exist=False):
        """Verifies that the given action is valid on the target in this context.

        :param action: string representing the action to be checked.
        :param target: dictionary representing the object of the action
            for object creation this should be a dictionary representing the
            location of the object e.g. ``{'project_id': context.project_id}``.
            If None, then this default target will be considered:
            {'project_id': self.project_id, 'user_id': self.user_id}
        :param fatal: if False, will return False when an
            exception.NotAuthorized occurs.
        :param might_not_exist: If True the policy check is skipped (and the
            function returns True) if the specified policy does not exist.
            Defaults to false.

        :raises zun.common.exception.NotAuthorized: if verification fails and
            fatal is True.

        :return: returns a non-False value (not necessarily "True") if
            authorized and False if not authorized and fatal is False.
        """
        if target is None:
            target = {'project_id': self.project_id,
                      'user_id': self.user_id}

        try:
            return policy.authorize(self, action, target,
                                    might_not_exist=might_not_exist)
        except exception.NotAuthorized:
            if fatal:
                raise
            return False


def make_context(*args, **kwargs):
    return RequestContext(*args, **kwargs)


def get_admin_context(show_deleted=False, all_projects=False):
    """Create an administrator context.

    :param show_deleted: if True, will show deleted items when query db
    """
    context = RequestContext(user_id=None,
                             project=None,
                             is_admin=True,
                             show_deleted=show_deleted,
                             all_projects=all_projects)
    return context


def set_context(func):
    @functools.wraps(func)
    def handler(self, ctx):
        if ctx is None:
            ctx = get_admin_context(all_projects=True)
        func(self, ctx)
    return handler
