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
import types

from oslo_log import log as logging
from oslo_utils import fileutils
import six

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

    def _search_image_on_host(self, context, repo, tag):
        LOG.debug('Searching for image %s locally', repo)
        images_directory = CONF.glance.images_directory
        try:
            # TODO(mkrai): Change this to search image entry in zun db
            #              after the image endpoint is merged.
            image_meta = utils.find_image(context, repo, tag)
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

    def _verify_md5sum_for_image(self, image):
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
            return True
        return False

    def pull_image(self, context, repo, tag, image_pull_policy):
        image_loaded = False
        image = self._search_image_on_host(context, repo, tag)

        if not common_utils.should_pull_image(image_pull_policy, bool(image)):
            if image:
                if self._verify_md5sum_for_image(image):
                    image_loaded = True
                    return image, image_loaded
            else:
                message = _('Image %s not present with pull policy of Never'
                            ) % repo
                raise exception.ImageNotFound(message)

        LOG.debug('Pulling image from glance %s', repo)
        try:
            image_meta = utils.find_image(context, repo, tag)
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
        LOG.debug('Searching image in glance %s', repo)
        try:
            return utils.find_images(context, repo, tag, exact_match)
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
            if isinstance(data, types.GeneratorType):
                # NOTE(kiennt): In Docker-py 3.1.0, get_image
                #               returns generator - related bugs [1].
                #               These lines makes image_data readable.
                # [1] https://bugs.launchpad.net/zun/+bug/1753080
                data = six.b('').join(data)
                data = six.BytesIO(data)

            return utils.upload_image_data(context, img_id, data)
        except Exception as e:
            raise exception.ZunException(six.text_type(e))

    def delete_committed_image(self, context, img_id):
        """Delete a committed image."""
        LOG.debug('Delete the committed image %s in glance', img_id)
        try:
            return utils.delete_image(context, img_id)
        except Exception as e:
            LOG.exception('Unknown exception occurred while deleting '
                          'image %s in glance: %s',
                          img_id,
                          six.text_type(e))
            raise exception.ZunException(six.text_type(e))

    def delete_image_tar(self, context, image):
        """Delete image tar file that pull from glance"""
        repo = image.split(':')[0]
        tag = image.split(':')[1]
        image = self._search_image_on_host(context, repo, tag)
        if image:
            if self._verify_md5sum_for_image(image):
                tarfile = image.get('path')
                try:
                    os.unlink(tarfile)
                except Exception as e:
                    LOG.exception('Cannot delete tar file %s', tarfile)
                    raise exception.ZunException(six.text_type(e))
