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

from oslo_config import cfg

from zun.conf import api
from zun.conf import compute
from zun.conf import container_driver
from zun.conf import database
from zun.conf import docker
from zun.conf import glance_client
from zun.conf import image_driver
from zun.conf import nova_client
from zun.conf import path
from zun.conf import scheduler
from zun.conf import services
from zun.conf import ssl
from zun.conf import zun_client

CONF = cfg.CONF

api.register_opts(CONF)
compute.register_opts(CONF)
container_driver.register_opts(CONF)
database.register_opts(CONF)
docker.register_opts(CONF)
glance_client.register_opts(CONF)
image_driver.register_opts(CONF)
nova_client.register_opts(CONF)
path.register_opts(CONF)
scheduler.register_opts(CONF)
services.register_opts(CONF)
zun_client.register_opts(CONF)
ssl.register_opts(CONF)
