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

import abc
import six

from stevedore import driver

import zun.conf


CONF = zun.conf.CONF


def api(*args, **kwargs):
    network_driver = CONF.network.driver
    network_api = driver.DriverManager(
        "zun.network.driver",
        network_driver,
        invoke_on_load=True).driver

    network_api.init(*args, **kwargs)
    return network_api


@six.add_metaclass(abc.ABCMeta)
class Network(object):
    """The base class that all Network classes should inherit from."""

    def init(self, context, *args, **kwargs):
        raise NotImplementedError()

    def create_network(self, *args, **kwargs):
        raise NotImplementedError()

    def remove_network(self, network_name, **kwargs):
        raise NotImplementedError()

    def inspect_network(self, network_name, **kwargs):
        raise NotImplementedError()

    def list_networks(self, **kwargs):
        raise NotImplementedError()

    def connect_container_to_network(self, container, network_name, **kwargs):
        raise NotImplementedError()

    def disconnect_container_from_network(self, container, network_name,
                                          **kwargs):
        raise NotImplementedError()

    def add_security_groups_to_ports(self, container, security_group_ids,
                                     **kwargs):
        raise NotImplementedError()

    def remove_security_groups_from_ports(self, container, security_group_ids,
                                          **kwargs):
        raise NotImplementedError()
