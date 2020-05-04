# Copyright 2016 Intel.
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

from docker import errors
from oslo_log import log as logging
from oslo_utils import excutils

from zun.common.docker_image import reference as docker_image
from zun.common import exception
from zun.common.i18n import _
from zun.common import utils
import zun.conf
from zun.container.docker import utils as docker_utils
from zun.image import driver


CONF = zun.conf.CONF

LOG = logging.getLogger(__name__)


class DockerDriver(driver.ContainerImageDriver):
    def __init__(self):
        super(DockerDriver, self).__init__()

    def delete_image(self, context, img_id):
        LOG.debug('Delete an image %s in docker', img_id)
        with docker_utils.docker_client() as docker:
            try:
                docker.remove_image(img_id)
            except errors.ImageNotFound:
                return
            except errors.APIError as api_error:
                raise exception.ZunException(str(api_error))
            except Exception as e:
                LOG.exception('Unknown exception occurred while deleting '
                              'image %s in glance:%s',
                              img_id,
                              str(e))
                raise exception.ZunException(str(e))

    def _search_image_on_host(self, repo, tag):
        with docker_utils.docker_client() as docker:
            image = repo + ":" + tag
            LOG.debug('Inspecting image locally %s', image)
            try:
                image_dict = docker.inspect_image(image)
                if image_dict:
                    return {'image': repo, 'path': None}
            except errors.NotFound:
                LOG.debug('Image %s not found locally', image)
                return None

    def _pull_image(self, repo, tag, registry):
        auth_config = None
        image_ref = docker_image.Reference.parse(repo)
        registry_domain, remainder = image_ref.split_hostname()
        if registry and registry.username:
            auth_config = {'username': registry.username,
                           'password': registry.password}
        elif (registry_domain and
                registry_domain == CONF.docker.default_registry and
                CONF.docker.default_registry_username):
            auth_config = {'username': CONF.docker.default_registry_username,
                           'password': CONF.docker.default_registry_password}

        with docker_utils.docker_client() as docker:
            try:
                docker.pull(repo, tag=tag, auth_config=auth_config)
            except errors.NotFound as e:
                raise exception.ImageNotFound(message=str(e))
            except errors.APIError:
                LOG.exception('Error on pulling image')
                message = _('Error on pulling image: %(repo)s:%(tag)s') % {
                    'repo': repo, 'tag': tag}
                raise exception.ZunException(message)

    def pull_image(self, context, repo, tag, image_pull_policy, registry):
        image_loaded = True
        image = self._search_image_on_host(repo, tag)
        if not utils.should_pull_image(image_pull_policy, bool(image)):
            if image:
                LOG.debug('Image  %s present locally', repo)
                return image, image_loaded
            else:
                message = _('Image %s not present with pull policy of Never'
                            ) % repo
                raise exception.ImageNotFound(message)

        try:
            LOG.debug('Pulling image from docker %(repo)s,'
                      ' context %(context)s',
                      {'repo': repo, 'context': context})
            self._pull_image(repo, tag, registry)
            return {'image': repo, 'path': None}, image_loaded
        except exception.ImageNotFound:
            with excutils.save_and_reraise_exception():
                LOG.error('Image %s was not found in docker repo', repo)
        except exception.DockerError:
            with excutils.save_and_reraise_exception():
                LOG.error('Docker API error occurred during downloading '
                          'image %s', repo)
        except Exception as e:
            msg = _('Cannot download image from docker: {0}')
            raise exception.ZunException(msg.format(e))

    def search_image(self, context, repo, tag, exact_match):
        image_ref = docker_image.Reference.parse(repo)
        registry, image_name = image_ref.split_hostname()
        if registry and registry != 'docker.io':
            # Images searching is only supported in DockerHub
            msg = _('Image searching is not supported in registry: {0}')
            raise exception.OperationNotSupported(msg.format(registry))

        with docker_utils.docker_client() as docker:
            try:
                # TODO(hongbin): search image by both name and tag
                images = docker.search(image_name)
            except errors.APIError as api_error:
                raise exception.ZunException(str(api_error))
            except Exception as e:
                msg = _('Cannot search image in docker: {0}')
                raise exception.ZunException(msg.format(e))

        if exact_match:
            images = [i for i in images if i['name'] == image_name]

        for image in images:
            image['metadata'] = {}
            for key in ('is_official', 'star_count'):
                value = image.pop(key, None)
                if value is not None:
                    image['metadata'][key] = value

        # TODO(hongbin): convert images to a list of Zun Image object
        return images
