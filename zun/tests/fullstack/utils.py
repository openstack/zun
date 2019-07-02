# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import os
import time

from keystoneauth1 import identity
from keystoneauth1 import session as ks
import os_client_config
from zunclient import client


ZUN_API_VERSION = '1.30'


def get_zun_client_from_env():
    # We should catch KeyError exception with the purpose of
    # source or configure openrc file.
    auth_url = os.environ['OS_AUTH_URL']
    username = os.environ['OS_USERNAME']
    password = os.environ['OS_PASSWORD']
    project_name = os.environ['OS_PROJECT_NAME']

    # Either project(user)_domain_name or project(user)_domain_id
    # would be acceptable.
    project_domain_name = os.environ.get("OS_PROJECT_DOMAIN_NAME")
    project_domain_id = os.environ.get("OS_PROJECT_DOMAIN_ID")
    user_domain_name = os.environ.get("OS_USER_DOMAIN_NAME")
    user_domain_id = os.environ.get("OS_USER_DOMAIN_ID")

    auth = identity.Password(auth_url=auth_url,
                             username=username,
                             password=password,
                             project_name=project_name,
                             project_domain_id=project_domain_id,
                             project_domain_name=project_domain_name,
                             user_domain_id=user_domain_id,
                             user_domain_name=user_domain_name)
    session = ks.Session(auth=auth)
    return client.Client(ZUN_API_VERSION, session=session)


def _get_cloud_config_auth_data(cloud='devstack-admin'):
    """Retrieves Keystone auth data to run tests

    Credentials are either read via os-client-config from the environment
    or from a config file ('clouds.yaml'). Environment variables override
    those from the config file.
    devstack produces a clouds.yaml with two named clouds - one named
    'devstack' which has user privs and one named 'devstack-admin' which
    has admin privs. This function will default to getting the devstack-admin
    cloud as that is the current expected behavior.
    """
    cloud_config = os_client_config.OpenStackConfig().get_one_cloud(cloud)
    return cloud_config.get_auth(), cloud_config.get_session()


def get_zun_client_from_creds():
    auth_plugin, session = _get_cloud_config_auth_data()
    return client.Client(ZUN_API_VERSION, session=session, auth=auth_plugin)


def wait_for_condition(condition, interval=2, timeout=60):
    start_time = time.time()
    end_time = time.time() + timeout
    while time.time() < end_time:
        result = condition()
        if result:
            return result
        time.sleep(interval)
    raise Exception(("Timed out after %s seconds.  Started on %s and ended "
                     "on %s") % (timeout, start_time, end_time))
