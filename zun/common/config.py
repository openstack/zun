# Copyright 2010 United States Government as represented by the
# Administrator of the National Aeronautics and Space Administration.
# All Rights Reserved.
# Copyright 2012 Red Hat, Inc.
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

from oslo_middleware import cors
from oslo_policy import opts

from zun.common import rpc
import zun.conf
from zun import version


def init(args, **kwargs):
    zun.conf.CONF(args,
                  project='zun',
                  version=version.version_info.release_string(),
                  **kwargs)


def parse_args(argv, default_config_files=None):
    rpc.set_defaults(control_exchange='zun')
    init(argv[1:], default_config_files=default_config_files)
    rpc.init(zun.conf.CONF)


def set_config_defaults():
    """This method updates all configuration default values."""
    set_cors_middleware_defaults()

    # TODO(gmann): Remove setting the default value of config policy_file
    # once oslo_policy change the default value to 'policy.yaml'.
    # https://github.com/openstack/oslo.policy/blob/a626ad12fe5a3abd49d70e3e5b95589d279ab578/oslo_policy/opts.py#L49
    opts.set_defaults(zun.conf.CONF, 'policy.yaml')


def set_cors_middleware_defaults():
    """Update default configuration options for oslo.middleware."""
    cors.set_defaults(
        allow_headers=['X-Auth-Token',
                       'X-Identity-Status',
                       'X-Roles',
                       'X-Service-Catalog',
                       'X-User-Id',
                       'X-Project-Id',
                       'X-OpenStack-Request-ID',
                       'X-Server-Management-Url'],
        expose_headers=['X-Auth-Token',
                        'X-Subject-Token',
                        'X-Service-Token',
                        'X-OpenStack-Request-ID',
                        'X-Server-Management-Url'],
        allow_methods=['GET',
                       'PUT',
                       'POST',
                       'DELETE',
                       'PATCH'])
