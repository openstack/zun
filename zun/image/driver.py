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

import os
import sys

from oslo_log import log as logging
from oslo_utils import importutils

from zun.common import exception
from zun.common.i18n import _
from zun.common.i18n import _LE
from zun.common.i18n import _LI
import zun.conf
from zun.image.glance import utils

CONF = zun.conf.CONF
LOG = logging.getLogger(__name__)


def load_image_driver(image_driver=None):
    """Load a image driver module.

    Load the container image driver module specified by the image_driver
    configuration option or, if supplied, the driver name supplied as an
    argument.
    :param image_driver: container image driver name to override config opt
    :returns: a ContainerImageDriver instance
    """
    if not image_driver:
        LOG.error(_LE("Container image driver option required, "
                      "but not specified"))
        sys.exit(1)

    LOG.info(_LI("Loading container image driver '%s'"), image_driver)
    try:
        driver = importutils.import_object(
            'zun.image.%s' % image_driver)
        if not isinstance(driver, ContainerImageDriver):
            raise Exception(_('Expected driver of type: %s') %
                            str(ContainerImageDriver))

        return driver
    except ImportError:
        LOG.exception(_LE("Unable to load the container image driver"))
        sys.exit(1)


def search_image_on_host(context, image_name):
    LOG.debug('Searching for image %s locally' % image_name)
    CONF.import_opt('images_directory', 'zun.image.glance.driver',
                    group='glance')
    images_directory = CONF.glance.images_directory
    try:
        # TODO(mkrai): Change this to search image entry in zun db
        #              after the image endpoint is merged.
        image_meta = utils.find_image(context, image_name)
    except exception.ImageNotFound:
        return None
    if image_meta:
        out_path = os.path.join(images_directory, image_meta.id + '.tar')
        if os.path.isfile(out_path):
            return {'image': image_name, 'path': out_path}
        else:
            return None


def pull_image(context, image_name):
    image = search_image_on_host(context, image_name)
    if image:
        LOG.debug('Found image %s locally.' % image_name)
        return image
    image_driver_list = CONF.image_driver_list
    for driver in image_driver_list:
        try:
            image_driver = load_image_driver(driver)
            image = image_driver.pull_image(context, image_name)
            if image:
                break
        except exception.ImageNotFound:
            image = None
        except Exception as e:
            LOG.exception(_LE('Unknown exception occured while loading'
                              ' image : %s'), str(e))
            raise exception.ZunException(str(e))
    if not image:
        raise exception.ImageNotFound("Image %s not found" % image_name)
    return image


class ContainerImageDriver(object):
    '''Base class for container image driver.'''

    def pull_image(self, context, image):
        """Create an image."""
        raise NotImplementedError()
