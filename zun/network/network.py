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

from stevedore import driver as stevedore_driver

import zun.conf


CONF = zun.conf.CONF


def driver(*args, **kwargs):
    driver_name = CONF.network.driver
    network_driver = stevedore_driver.DriverManager(
        "zun.network.driver",
        driver_name,
        invoke_on_load=True).driver

    network_driver.init(*args, **kwargs)
    return network_driver


class Network(object, metaclass=abc.ABCMeta):
    """The base class that all Network classes should inherit from."""

    def init(self, context, *args, **kwargs):
        raise NotImplementedError()

    def get_or_create_network(self, *args, **kwargs):
        raise NotImplementedError()

    def create_network(self, *args, **kwargs):
        raise NotImplementedError()

    def remove_network(self, network_name, **kwargs):
        raise NotImplementedError()

    def process_networking_config(self, *args, **kwargs):
        raise NotImplementedError()

    def connect_container_to_network(self, container, network_name, **kwargs):
        raise NotImplementedError()

    def disconnect_container_from_network(self, *args, **kwargs):
        raise NotImplementedError()

    def add_security_groups_to_ports(self, *args, **kwargs):
        raise NotImplementedError()

    def remove_security_groups_from_ports(self, container, security_group_ids,
                                          **kwargs):
        raise NotImplementedError()

    def on_container_started(self, container):
        raise NotImplementedError()

    def on_container_stopped(self, container):
        raise NotImplementedError()
