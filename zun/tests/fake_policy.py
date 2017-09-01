# Copyright (c) 2012 OpenStack Foundation
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


policy_data = """
{
    "context_is_admin":  "role:admin",
    "admin_or_owner":  "is_admin:True or project_id:%(project_id)s",
    "default": "rule:admin_or_owner",
    "admin_api": "rule:context_is_admin",

    "container:create": "",
    "container:delete": "",
    "container:delete_all_tenants": "",
    "container:delete_force": "",
    "container:get_one": "",
    "container:get_one_all_tenants": "",
    "container:get_all": "",
    "container:get_all_all_tenants": "",
    "container:update": "",
    "container:start": "",
    "container:stop": "",
    "container:reboot": "",
    "container:pause": "",
    "container:unpause": "",
    "container:logs": "",
    "container:execute": "",
    "container:execute_resize": "",
    "container:kill": "",
    "container:rename": "",
    "container:attach": "",
    "container:resize": "",
    "container:top": "",
    "container:get_archive": "",
    "container:put_archive": "",
    "container:stats": "",
    "container:commit": "",
    "container:add_security_group": "",

    "image:pull": "",
    "image:get_all": "",
    "image:search": "",

    "zun-service:delete": "",
    "zun-service:disable": "",
    "zun-service:enable": "",
    "zun-service:force_down": "",
    "zun-service:get_all": ""
}
"""
