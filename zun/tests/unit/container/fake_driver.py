#    Copyright 2016 IBM Corp.
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

from zun.common.utils import check_container_id
from zun.container import driver


class FakeDriver(driver.ContainerDriver):
    '''Fake driver for testing.'''

    def __init__(self):
        super(FakeDriver, self).__init__()

    def pull_image(self, image):
        pass

    def create(self, container):
        pass

    def delete(self, container, force):
        pass

    def list(self):
        pass

    def show(self, container):
        pass

    @check_container_id
    def reboot(self, container):
        pass

    @check_container_id
    def stop(self, container):
        pass

    @check_container_id
    def start(self, container):
        pass

    @check_container_id
    def pause(self, container):
        pass

    @check_container_id
    def unpause(self, container):
        pass

    @check_container_id
    def show_logs(self, container):
        pass

    @check_container_id
    def execute(self, container, command):
        pass

    @check_container_id
    def kill(self, container, signal=None):
        pass

    def create_sandbox(self, context, name, **kwargs):
        pass

    def delete_sandbox(self, context, id):
        pass

    def get_sandbox_id(self, container):
        pass

    def set_sandbox_id(self, container, id):
        pass

    def get_addresses(self, context, container):
        pass
