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

from zun.common import exception
from zun.common.i18n import _
from zun.common.utils import parse_image_name
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
                            str(ContainerImageDriver))

        return driver
    except Exception:
        LOG.exception("Unable to load the container image driver")
        sys.exit(1)


def pull_image(context, repo, tag, image_pull_policy='always',
               image_driver=None):
    if image_driver:
        image_driver_list = [image_driver.lower()]
    else:
        image_driver_list = CONF.image_driver_list

    for driver in image_driver_list:
        try:
            image_driver = load_image_driver(driver)
            image, image_loaded = image_driver.pull_image(
                context, repo, tag, image_pull_policy)
            if image:
                image['driver'] = driver.split('.')[0]
                break
        except exception.ImageNotFound:
            image = None
        except Exception as e:
            LOG.exception('Unknown exception occurred while loading '
                          'image: %s', six.text_type(e))
            raise exception.ZunException(six.text_type(e))
    if not image:
        raise exception.ImageNotFound("Image %s not found" % repo)
    return image, image_loaded


def search_image(context, image_name, image_driver, exact_match):
    images = []
    repo, tag = parse_image_name(image_name)
    if image_driver:
        image_driver_list = [image_driver.lower()]
    else:
        image_driver_list = CONF.image_driver_list
    for driver in image_driver_list:
        try:
            image_driver = load_image_driver(driver)
            imgs = image_driver.search_image(context, repo, tag,
                                             exact_match)
            images.extend(imgs)
        except Exception as e:
            LOG.exception('Unknown exception occurred while searching '
                          'for image: %s', six.text_type(e))
            raise exception.ZunException(six.text_type(e))
    return images


def create_image(context, image_name, image_driver):
    img = None
    try:
        img = image_driver.create_image(context, image_name)
    except Exception as e:
        LOG.exception('Unknown exception occurred while creating image: %s',
                      six.text_type(e))
        raise exception.ZunException(six.text_type(e))
    return img


def upload_image_data(context, image, image_tag, image_data,
                      image_driver):
    img = None
    try:
        img = image_driver.update_image(context,
                                        image.id,
                                        tag=image_tag)
        # Image data has to match the image format.
        # contain format defaults to 'docker';
        # disk format defaults to 'qcow2'.
        img = image_driver.upload_image_data(context,
                                             image.id,
                                             image_data)
    except Exception as e:
        LOG.exception('Unknown exception occurred while uploading image: %s',
                      six.text_type(e))
        raise exception.ZunException(six.text_type(e))
    return img


def delete_image(context, img_id, image_driver):
    try:
        image_driver.delete_image(context, img_id)
    except Exception as e:
        LOG.exception('Unknown exception occurred while deleting image %s: %s',
                      img_id,
                      six.text_type(e))
        raise exception.ZunException(six.text_type(e))


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
