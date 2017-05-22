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

import random
import socket
import string
import struct

from tempest.lib.common.utils import data_utils
from zun.tests.tempest.api.models import container_model


def random_int(min_int=1, max_int=100):
    return random.randrange(min_int, max_int)


def gen_random_port():
    return random_int(49152, 65535)


def gen_docker_volume_size(min_int=3, max_int=5):
    return random_int(min_int, max_int)


def gen_fake_ssh_pubkey():
    chars = "".join(
        random.choice(string.ascii_uppercase +
                      string.ascii_letters + string.digits + '/+=')
        for _ in range(372))
    return "ssh-rsa " + chars


def gen_random_ip():
    return socket.inet_ntoa(struct.pack('>I', random.randint(1, 0xffffffff)))


def gen_url(scheme="http", domain="example.com", port=80):
    return "%s://%s:%s" % (scheme, domain, port)


def container_data(**kwargs):
    data = {
        'name': data_utils.rand_name('container'),
        'image': 'cirros:latest',
        'command': 'sleep 10000',
        'memory': '100',
        'environment': {},
        'image_driver': 'docker'
    }

    data.update(kwargs)
    model = container_model.ContainerEntity.from_dict(data)

    return model


def container_patch_data(**kwargs):
    data = {
        'cpu': 0.2,
        'memory': '512',
    }

    data.update(kwargs)
    model = container_model.ContainerPatchEntity.from_dict(data)

    return model


def container_rename_data(**kwargs):
    data = {
        'name': 'new_name',
    }

    data.update(kwargs)
    model = container_model.ContainerPatchEntity.from_dict(data)

    return model
