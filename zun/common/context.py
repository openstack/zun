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

from oslo_context import context


class RequestContext(context.RequestContext):
    """Extends security contexts from the OpenStack common library."""

    def __init__(self, auth_token=None, user=None, project=None,
                 domain=None, user_id=None, project_id=None,
                 user_domain=None, project_domain=None, is_admin=False,
                 read_only=False, show_deleted=False, request_id=None,
                 resource_uuid=None, overwrite=True, roles=None,
                 auth_token_info=None):
        """Stores several additional request parameters:

        :param auth_token_info: Keystone token info.
        """
        super(RequestContext, self).__init__(
            auth_token=auth_token, user=user, tenant=project, domain=domain,
            user_domain=user_domain, project_domain=project_domain,
            is_admin=is_admin, read_only=read_only, show_deleted=show_deleted,
            request_id=request_id, resource_uuid=resource_uuid,
            overwrite=overwrite, roles=roles
        )

        self.project = project
        self.auth_token_info = auth_token_info
        self.user_id = user_id
        self.project_id = project_id

    def to_dict(self):
        value = super(RequestContext, self).to_dict()
        value.update({
            'project': self.project,
            'auth_token_info': self.auth_token_info,
        })
        return value

    @classmethod
    def from_dict(cls, values):
        return cls(**values)


def make_context(*args, **kwargs):
    return RequestContext(*args, **kwargs)


def get_admin_context(show_deleted=False):
    """Create an administrator context."""
    context = RequestContext(None,
                             project=None,
                             is_admin=True,
                             show_deleted=show_deleted,
                             overwrite=False)
    return context


def get_current():
    return context.get_current()
