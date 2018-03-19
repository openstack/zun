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
    """Fake driver for testing."""
    capabilities = {
        "support_sandbox": True,
        "support_standalone": True,
    }

    def __init__(self):
        super(FakeDriver, self).__init__()

    def load_image(self, image, image_path=None):
        pass

    def inspect_image(self, image):
        pass

    def get_image(self, name):
        pass

    def delete_image(self, img_id):
        pass

    def images(self, repo, **kwargs):
        pass

    def pull_image(self, context, repo, tag, **kwargs):
        pass

    def create_image(self, context, image_name, image_driver):
        pass

    def upload_image_data(self, context, image, image_tag, image_data,
                          image_driver):
        pass

    def create(self, container):
        pass

    def delete(self, container, force):
        pass

    def list(self):
        pass

    def show(self, context, container):
        pass

    @check_container_id
    def reboot(self, context, container):
        pass

    @check_container_id
    def stop(self, context, container):
        pass

    @check_container_id
    def start(self, context, container):
        pass

    @check_container_id
    def pause(self, context, container):
        pass

    @check_container_id
    def unpause(self, context, container):
        pass

    @check_container_id
    def show_logs(self, context, container):
        pass

    @check_container_id
    def execute(self, context, container, command):
        pass

    @check_container_id
    def kill(self, context, container, signal=None):
        pass

    @check_container_id
    def get_websocket_url(self, context, container):
        pass

    @check_container_id
    def resize(self, context, container, height, weight):
        pass

    def create_sandbox(self, context, name, **kwargs):
        pass

    def delete_sandbox(self, context, id):
        pass

    def get_addresses(self, context, container):
        pass

    @check_container_id
    def update(self, context, container):
        pass

    @check_container_id
    def commit(self, context, container, repository, tag):
        pass

    def read_tar_image(self, image):
        return image.get('repo'), image.get('tag')

    def check_container_exist(self, context):
        pass

    def node_support_disk_quota(self):
        return True

    def get_host_default_base_size(self):
        return None
