# Copyright 2012 New Dream Network, LLC (DreamHost)
#
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


from oslo_config import cfg
from pecan import hooks

from higgins.common import context

CONF = cfg.CONF
CONF.import_opt('auth_uri', 'keystonemiddleware.auth_token',
                group='keystone_authtoken')


class ContextHook(hooks.PecanHook):
    """Configures a request context and attaches it to the request.

    The following HTTP request headers are used:

    X-Domain-Id:
        Used for context.domain.

    X-User-Id:
        Used for context.user.

    X-User-Domain-Id:
        Used for context.user_domain.

    X-Project-Id:
        Used for context.project.

    X-Project-Domain-Id:
        Used for context.project_domain.

    X-Auth-Token:
        Used for context.auth_token.

    X-Roles:
        Used for context.roles.
    """

    def before(self, state):
        headers = state.request.headers
        domain_id = headers.get('X-Domain-Id')
        user_id = headers.get('X-User-Id')
        user_domain_id = headers.get('X-User-Domain-Id')
        project_id = headers.get('X-Project-Id')
        project_domain_id = headers.get('X-Project-Domain-Id')
        auth_token = headers.get('X-Auth-Token')
        auth_token_info = state.request.environ.get('keystone.token_info')
        roles = headers.get('X-Roles', '').split(',')

        state.request.context = context.make_context(
            auth_token=auth_token,
            auth_token_info=auth_token_info,
            user=user_id,
            project=project_id,
            domain=domain_id,
            user_domain=user_domain_id,
            project_domain=project_domain_id,
            roles=roles,
        )


# NOTE(madhuri): Add RPCHook after conductor is implemented.
class NoExceptionTracebackHook(hooks.PecanHook):
    """Workaround rpc.common: deserialize_remote_exception.

    deserialize_remote_exception builds rpc exception traceback into error
    message which is then sent to the client. Such behavior is a security
    concern so this hook is aimed to cut-off traceback from the error message.
    """
    # NOTE(max_lobur): 'after' hook used instead of 'on_error' because
    # 'on_error' never fired for wsme+pecan pair. wsme @wsexpose decorator
    # catches and handles all the errors, so 'on_error' dedicated for unhandled
    # exceptions never fired.
    def after(self, state):
        # Omit empty body. Some errors may not have body at this level yet.
        if not state.response.body:
            return

        # Do nothing if there is no error.
        if 200 <= state.response.status_int < 400:
            return

        json_body = state.response.json
        # Do not remove traceback when server in debug mode (except 'Server'
        # errors when 'debuginfo' will be used for traces).
        if cfg.CONF.debug and json_body.get('faultcode') != 'Server':
            return

        faultsting = json_body.get('faultstring')
        traceback_marker = 'Traceback (most recent call last):'
        if faultsting and (traceback_marker in faultsting):
            # Cut-off traceback.
            faultsting = faultsting.split(traceback_marker, 1)[0]
            # Remove trailing newlines and spaces if any.
            json_body['faultstring'] = faultsting.rstrip()
            # Replace the whole json. Cannot change original one beacause it's
            # generated on the fly.
            state.response.json = json_body
