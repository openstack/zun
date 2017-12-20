# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import hashlib
import os
import six

from oslo_log import log as logging
from oslo_utils import fileutils

from zun.common import exception
from zun.common.i18n import _
from zun.common import utils as common_utils
import zun.conf
from zun.image import driver
from zun.image.glance import utils

CONF = zun.conf.CONF

LOG = logging.getLogger(__name__)


class GlanceDriver(driver.ContainerImageDriver):

    def __init__(self):
        super(GlanceDriver, self).__init__()

    def _search_image_on_host(self, context, repo):
        LOG.debug('Searching for image %s locally', repo)
        images_directory = CONF.glance.images_directory
        try:
            # TODO(mkrai): Change this to search image entry in zun db
            #              after the image endpoint is merged.
            image_meta = utils.find_image(context, repo)
        except exception.ImageNotFound:
            return None
        if image_meta:
            out_path = os.path.join(images_directory,
                                    image_meta.id + '.tar')
            if os.path.isfile(out_path):
                return {
                    'image': repo,
                    'path': out_path,
                    'checksum': image_meta.checksum}
            else:
                return None

    def pull_image(self, context, repo, tag, image_pull_policy):
        # TODO(shubhams): glance driver does not handle tags
        #              once metadata is stored in db then handle tags
        image_loaded = False
        image = self._search_image_on_host(context, repo)
        if image:
            image_path = image['path']
            image_checksum = image['checksum']
            md5sum = hashlib.md5()
            with open(image_path, 'rb') as fd:
                while True:
                    # read 10MB of data each time
                    data = fd.read(10 * 1024 * 1024)
                    if not data:
                        break
                    md5sum.update(data)
            md5sum = md5sum.hexdigest()
            if md5sum == image_checksum:
                image_loaded = True
                return image, image_loaded

        if not common_utils.should_pull_image(image_pull_policy, bool(image)):
            if image:
                LOG.debug('Image  %s present locally', repo)
                image_loaded = True
                return image, image_loaded
            else:
                message = _('Image %s not present with pull policy of Never'
                            ) % repo
                raise exception.ImageNotFound(message)

        LOG.debug('Pulling image from glance %s', repo)
        try:
            image_meta = utils.find_image(context, repo)
            LOG.debug('Image %s was found in glance, downloading now...', repo)
            image_chunks = utils.download_image_in_chunks(context,
                                                          image_meta.id)
        except exception.ImageNotFound:
            LOG.error('Image %s was not found in glance', repo)
            raise
        except Exception as e:
            msg = _('Cannot download image from glance: {0}')
            raise exception.ZunException(msg.format(e))
        try:
            images_directory = CONF.glance.images_directory
            fileutils.ensure_tree(images_directory)
            out_path = os.path.join(images_directory, image_meta.id + '.tar')
            with open(out_path, 'wb') as fd:
                for chunk in image_chunks:
                    fd.write(chunk)
        except Exception as e:
            msg = _('Error occurred while writing image: {0}')
            raise exception.ZunException(msg.format(e))
        LOG.debug('Image %(repo)s was downloaded to path : %(path)s',
                  {'repo': repo, 'path': out_path})
        return {'image': repo, 'path': out_path}, image_loaded

    def search_image(self, context, repo, tag, exact_match):
        # TODO(mkrai): glance driver does not handle tags
        #       once metadata is stored in db then handle tags
        LOG.debug('Searching image in glance %s', repo)
        try:
            # TODO(hongbin): find image by both repo and tag
            return utils.find_images(context, repo, exact_match)
        except Exception as e:
            raise exception.ZunException(six.text_type(e))

    def create_image(self, context, image_name):
        """Create an image."""
        LOG.debug('Creating a new image in glance %s', image_name)
        try:
            # Return a created image
            return utils.create_image(context, image_name)
        except Exception as e:
            raise exception.ZunException(six.text_type(e))

    def update_image(self, context, img_id, disk_format='qcow2',
                     container_format='docker', tag=None):
        """Update an image."""
        LOG.debug('Updating an image %s in glance', img_id)
        try:
            # NOTE(kiennt): Tags will be an empty list if no tag is defined.
            tags = [tag] if tag else []
            # Return the updated image
            return utils.update_image(context, img_id, disk_format,
                                      container_format, tags=tags)
        except Exception as e:
            raise exception.ZunException(six.text_type(e))

    def upload_image_data(self, context, img_id, data):
        """Upload an image."""
        LOG.debug('Uploading an image to glance %s', img_id)
        try:
            return utils.upload_image_data(context, img_id, data)
        except Exception as e:
            raise exception.ZunException(six.text_type(e))

    def delete_image(self, context, img_id):
        """Delete an image."""
        LOG.debug('Delete an image %s in glance', img_id)
        try:
            return utils.delete_image(context, img_id)
        except Exception as e:
            LOG.exception('Unknown exception occurred while deleting '
                          'image %s in glance: %s',
                          img_id,
                          six.text_type(e))
            raise exception.ZunException(six.text_type(e))
