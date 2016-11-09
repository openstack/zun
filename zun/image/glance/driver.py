
#
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

import os

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
        LOG.debug('Searching for image %s locally' % repo)
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
                return {'image': repo, 'path': out_path}
            else:
                return None

    def pull_image(self, context, repo, tag, image_pull_policy):
        # TODO(shubhams): glance driver does not handle tags
        #              once metadata is stored in db then handle tags
        image = self._search_image_on_host(context, repo)
        if not common_utils.should_pull_image(image_pull_policy, bool(image)):
            if image:
                LOG.debug('Image  %s present locally' % repo)
                return image
            else:
                message = _('Image %s not present with pull policy of Never'
                            ) % repo
                raise exception.ImageNotFound(message)

        LOG.debug('Pulling image from glance %s' % repo)
        try:
            glance = utils.create_glanceclient(context)
            image_meta = utils.find_image(context, repo)
            LOG.debug('Image %s was found in glance, downloading now...'
                      % repo)
            image_chunks = glance.images.data(image_meta.id)
        except exception.ImageNotFound:
            LOG.error('Image %s was not found in glance' % repo)
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
            msg = _('Error occured while writing image: {0}')
            raise exception.ZunException(msg.format(e))
        LOG.debug('Image %s was downloaded to path : %s'
                  % (repo, out_path))
        return {'image': repo, 'path': out_path}

    def search_image(self, context, repo, tag, exact_match):
        # TODO(mkrai): glance driver does not handle tags
        #       once metadata is stored in db then handle tags
        LOG.debug('Searching image in glance %s' % repo)
        try:
            # TODO(hongbin): find image by both repo and tag
            images = utils.find_images(context, repo, exact_match)
            LOG.debug('Image %s was found in glance' % repo)
            return images
        except Exception as e:
            raise exception.ZunException(str(e))
