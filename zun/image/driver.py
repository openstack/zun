# Copyright 2016 Intel.
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

import six
import sys

from oslo_log import log as logging
import stevedore

from zun.common.i18n import _
import zun.conf

CONF = zun.conf.CONF
LOG = logging.getLogger(__name__)


def load_image_driver(image_driver=None):
    """Load an image driver module.

    Load the container image driver module specified by the image_driver
    configuration option or, if supplied, the driver name supplied as an
    argument.
    :param image_driver: container image driver name to override config opt
    :returns: a ContainerImageDriver instance
    """
    if not image_driver:
        image_driver = CONF.default_image_driver
    if not image_driver:
        LOG.error("Container image driver option required, "
                  "but not specified")
        sys.exit(1)

    LOG.info("Loading container image driver '%s'", image_driver)
    try:
        driver = stevedore.driver.DriverManager(
            "zun.image.driver",
            image_driver,
            invoke_on_load=True).driver

        if not isinstance(driver, ContainerImageDriver):
            raise Exception(_('Expected driver of type: %s') %
                            six.text_type(ContainerImageDriver))

        return driver
    except Exception:
        LOG.exception("Unable to load the container image driver")
        sys.exit(1)


class ContainerImageDriver(object):
    """Base class for container image driver."""

    def pull_image(self, context, repo, tag, image_pull_policy):
        """Pull an image."""
        raise NotImplementedError()

    def search_image(self, context, repo, tag, exact_match):
        """Search an image."""
        raise NotImplementedError()

    def create_image(self, context, image_name):
        """Create an image."""
        raise NotImplementedError()

    def update_image(self, context, img_id, container_fmt=None,
                     disk_fmt=None, tag=None):
        """Update an image."""
        raise NotImplementedError()

    def upload_image_data(self, context, img_id, data):
        """Upload an image."""
        raise NotImplementedError()

    def delete_image(self, context, img_id):
        """Delete an image."""
        raise NotImplementedError()

    def delete_committed_image(self, context, img_id, image_driver):
        """Delete a committed image."""
        raise NotImplementedError()

    def delete_image_tar(self, context, image):
        """Delete an image."""
        raise NotImplementedError()
