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

import six

from oslo_log import log as logging
from oslo_utils import excutils

from zun.common import exception
from zun.common.i18n import _LE
from zun.common import utils
from zun.common.utils import translate_exception
from zun.container import driver
from zun.image import driver as image_driver
from zun.objects import fields


LOG = logging.getLogger(__name__)


class Manager(object):
    '''Manages the running containers.'''

    def __init__(self, container_driver=None):
        super(Manager, self).__init__()
        self.driver = driver.load_container_driver(container_driver)

    def _fail_container(self, context, container, error):
        container.status = fields.ContainerStatus.ERROR
        container.status_reason = error
        container.task_state = None
        container.save(context)

    def container_create(self, context, container):
        utils.spawn_n(self._do_container_create, context, container)

    def container_run(self, context, container):
        utils.spawn_n(self._do_container_run, context, container)

    def _do_container_run(self, context, container):
        created_container = self._do_container_create(context,
                                                      container)
        if created_container:
            self._do_container_start(context, created_container)

    def _do_sandbox_cleanup(self, context, sandbox_id):
        try:
            self.driver.delete_sandbox(context, sandbox_id)
        except Exception as e:
            LOG.error(_LE("Error occurred while deleting sandbox: %s"),
                      six.text_type(e))

    def _do_container_create(self, context, container, reraise=False):
        LOG.debug('Creating container: %s', container.uuid)

        container.task_state = fields.TaskState.SANDBOX_CREATING
        container.save(context)
        sandbox_id = None
        sandbox_image = 'kubernetes/pause'
        repo, tag = utils.parse_image_name(sandbox_image)
        try:
            image = image_driver.pull_image(context, repo, tag, 'ifnotpresent')
            sandbox_id = self.driver.create_sandbox(context, container,
                                                    image=sandbox_image)
        except Exception as e:
            with excutils.save_and_reraise_exception(reraise=reraise):
                LOG.exception(_LE("Unexpected exception: %s"),
                              six.text_type(e))
                self._fail_container(context, container, six.text_type(e))
            return

        self.driver.set_sandbox_id(container, sandbox_id)
        container.task_state = fields.TaskState.IMAGE_PULLING
        container.save(context)
        repo, tag = utils.parse_image_name(container.image)
        image_pull_policy = utils.get_image_pull_policy(
            container.image_pull_policy, tag)
        try:
            image = image_driver.pull_image(context, repo,
                                            tag, image_pull_policy)
        except exception.ImageNotFound as e:
            with excutils.save_and_reraise_exception(reraise=reraise):
                LOG.error(six.text_type(e))
                self._do_sandbox_cleanup(context, sandbox_id)
                self._fail_container(context, container, six.text_type(e))
            return
        except exception.DockerError as e:
            with excutils.save_and_reraise_exception(reraise=reraise):
                LOG.error(_LE(
                    "Error occurred while calling Docker image API: %s"),
                    six.text_type(e))
                self._do_sandbox_cleanup(context, sandbox_id)
                self._fail_container(context, container, six.text_type(e))
            return
        except Exception as e:
            with excutils.save_and_reraise_exception(reraise=reraise):
                LOG.exception(_LE("Unexpected exception: %s"),
                              six.text_type(e))
                self._do_sandbox_cleanup(context, sandbox_id)
                self._fail_container(context, container, six.text_type(e))
            return

        container.task_state = fields.TaskState.CONTAINER_CREATING
        container.save(context)
        try:
            container = self.driver.create(context, container,
                                           sandbox_id, image)
            container.addresses = self._get_container_addresses(context,
                                                                container)
            container.task_state = None
            container.save(context)
            return container
        except exception.DockerError as e:
            with excutils.save_and_reraise_exception(reraise=reraise):
                LOG.error(_LE(
                    "Error occurred while calling Docker create API: %s"),
                    six.text_type(e))
                self._do_sandbox_cleanup(context, sandbox_id)
                self._fail_container(context, container, six.text_type(e))
            return
        except Exception as e:
            with excutils.save_and_reraise_exception(reraise=reraise):
                LOG.exception(_LE("Unexpected exception: %s"),
                              six.text_type(e))
                self._do_sandbox_cleanup(context, sandbox_id)
                self._fail_container(context, container, six.text_type(e))
            return

    def _do_container_start(self, context, container, reraise=False):
        LOG.debug('Starting container: %s', container.uuid)
        try:
            container = self.driver.start(container)
            container.save(context)
            return container
        except exception.DockerError as e:
            with excutils.save_and_reraise_exception(reraise=reraise):
                LOG.error(_LE(
                    "Error occurred while calling Docker start API: %s"),
                    six.text_type(e))
                self._fail_container(context, container, six.text_type(e))
        except Exception as e:
            with excutils.save_and_reraise_exception(reraise=reraise):
                LOG.exception(_LE("Unexpected exception: %s"),
                              six.text_type(e))
                self._fail_container(context, container, six.text_type(e))

    @translate_exception
    def container_delete(self, context, container, force):
        LOG.debug('Deleting container: %s', container.uuid)
        try:
            self.driver.delete(container, force)
        except exception.DockerError as e:
            LOG.error(_LE("Error occurred while calling Docker  "
                          "delete API: %s"), six.text_type(e))
            raise
        except Exception as e:
            LOG.exception(_LE("Unexpected exception: %s"), six.text_type(e))
            raise

        sandbox_id = self.driver.get_sandbox_id(container)
        if sandbox_id:
            try:
                self.driver.delete_sandbox(context, sandbox_id)
            except Exception as e:
                LOG.exception(_LE("Unexpected exception: %s"),
                              six.text_type(e))
                raise

        return container

    @translate_exception
    def container_list(self, context):
        LOG.debug('Listing container...')
        try:
            return self.driver.list()
        except exception.DockerError as e:
            LOG.error(_LE("Error occurred while calling Docker list API: %s"),
                      six.text_type(e))
            raise
        except Exception as e:
            LOG.exception(_LE("Unexpected exception: %s"), six.text_type(e))
            raise

    @translate_exception
    def container_show(self, context, container):
        LOG.debug('Showing container: %s', container.uuid)
        try:
            container = self.driver.show(container)
            container.save(context)
            return container
        except exception.DockerError as e:
            LOG.error(_LE("Error occurred while calling Docker show API: %s"),
                      six.text_type(e))
            raise
        except Exception as e:
            LOG.exception(_LE("Unexpected exception: %s"), six.text_type(e))
            raise

    def _do_container_reboot(self, context, container, timeout, reraise=False):
        LOG.debug('Rebooting container: %s', container.uuid)
        try:
            container = self.driver.reboot(container, timeout)
            container.save(context)
            return container
        except exception.DockerError as e:
            with excutils.save_and_reraise_exception(reraise=reraise):
                LOG.error(_LE("Error occurred while calling Docker reboot "
                              "API: %s"), six.text_type(e))
        except Exception as e:
            with excutils.save_and_reraise_exception(reraise=reraise):
                LOG.exception(_LE("Unexpected exception: %s"),
                              six.text_type(e))

    def container_reboot(self, context, container, timeout):
        utils.spawn_n(self._do_container_reboot, context, container, timeout)

    def _do_container_stop(self, context, container, timeout, reraise=False):
        LOG.debug('Stopping container: %s', container.uuid)
        try:
            container = self.driver.stop(container, timeout)
            container.save(context)
            return container
        except exception.DockerError as e:
            with excutils.save_and_reraise_exception(reraise=reraise):
                LOG.error(_LE(
                    "Error occurred while calling Docker stop API: %s"),
                    six.text_type(e))
        except Exception as e:
            with excutils.save_and_reraise_exception(reraise=reraise):
                LOG.exception(_LE("Unexpected exception: %s"),
                              six.text_type(e))

    def container_stop(self, context, container, timeout):
        utils.spawn_n(self._do_container_stop, context, container, timeout)

    def container_start(self, context, container):
        utils.spawn_n(self._do_container_start, context, container)

    def _do_container_pause(self, context, container, reraise=False):
        LOG.debug('Pausing container: %s', container.uuid)
        try:
            container = self.driver.pause(container)
            container.save(context)
            return container
        except exception.DockerError as e:
            with excutils.save_and_reraise_exception(reraise=reraise):
                LOG.error(_LE(
                    "Error occurred while calling Docker pause API: %s"),
                    six.text_type(e))
        except Exception as e:
            with excutils.save_and_reraise_exception(reraise=reraise):
                LOG.exception(_LE("Unexpected exception: %s,"),
                              six.text_type(e))

    def container_pause(self, context, container):
        utils.spawn_n(self._do_container_pause, context, container)

    def _do_container_unpause(self, context, container, reraise=False):
        LOG.debug('Unpausing container: %s', container.uuid)
        try:
            container = self.driver.unpause(container)
            container.save(context)
            return container
        except exception.DockerError as e:
            with excutils.save_and_reraise_exception(reraise=reraise):
                LOG.error(_LE(
                    "Error occurred while calling Docker unpause API: %s"),
                    six.text_type(e))
        except Exception as e:
            with excutils.save_and_reraise_exception(reraise=reraise):
                LOG.exception(_LE("Unexpected exception: %s"),
                              six.text_type(e))

    def container_unpause(self, context, container):
        utils.spawn_n(self._do_container_unpause, context, container)

    @translate_exception
    def container_logs(self, context, container):
        LOG.debug('Showing container logs: %s', container.uuid)
        try:
            return self.driver.show_logs(container)
        except exception.DockerError as e:
            LOG.error(_LE("Error occurred while calling Docker logs API: %s"),
                      six.text_type(e))
            raise
        except Exception as e:
            LOG.exception(_LE("Unexpected exception: %s"), six.text_type(e))
            raise

    @translate_exception
    def container_exec(self, context, container, command):
        # TODO(hongbin): support exec command interactively
        LOG.debug('Executing command in container: %s', container.uuid)
        try:
            return self.driver.execute(container, command)
        except exception.DockerError as e:
            LOG.error(_LE("Error occurred while calling Docker exec API: %s"),
                      six.text_type(e))
            raise
        except Exception as e:
            LOG.exception(_LE("Unexpected exception: %s"), six.text_type(e))
            raise

    def _do_container_kill(self, context, container, signal, reraise=False):
        LOG.debug('kill signal to container: %s', container.uuid)
        try:
            container = self.driver.kill(container, signal)
            container.save(context)
            return container
        except exception.DockerError as e:
            with excutils.save_and_reraise_exception(reraise=reraise):
                LOG.error(_LE(
                    "Error occurred while calling Docker kill API: %s"),
                    six.text_type(e))

    def container_kill(self, context, container, signal):
        utils.spawn_n(self._do_container_kill, context, container, signal)

    def image_pull(self, context, image):
        utils.spawn_n(self._do_image_pull, context, image)

    def _do_image_pull(self, context, image):
        LOG.debug('Creating image...')
        repo_tag = image.repo + ":" + image.tag
        try:
            pulled_image = image_driver.pull_image(context, image.repo,
                                                   image.tag)
            image_dict = self.driver.inspect_image(repo_tag,
                                                   pulled_image['path'])
            image.image_id = image_dict['Id']
            image.size = image_dict['Size']
            image.save()
        except exception.ImageNotFound as e:
            LOG.error(six.text_type(e))
            return
        except exception.DockerError as e:
            LOG.error(_LE("Error occurred while calling Docker image API: %s"),
                      six.text_type(e))
            raise
        except Exception as e:
            LOG.exception(_LE("Unexpected exception: %s"),
                          six.text_type(e))
            raise

    @translate_exception
    def image_show(self, context, image):
        LOG.debug('Listing image...')
        try:
            self.image.list()
            return image
        except Exception as e:
            LOG.exception(_LE("Unexpected exception: %s"), six.text_type(e))
            raise

    @translate_exception
    def image_search(self, context, image, exact_match):
        LOG.debug('Searching image...', image=image)
        try:
            return image_driver.search_image(context, image, exact_match)
        except Exception as e:
            LOG.exception(_LE("Unexpected exception while searching "
                              "image: %s"), six.text_type(e))
            raise

    def _get_container_addresses(self, context, container):
        LOG.debug('Showing container: %s IP addresses', container.uuid)
        try:
            return self.driver.get_addresses(context, container)
        except exception.DockerError as e:
            LOG.error(_LE("Error occurred while calling Docker API: %s"),
                      six.text_type(e))
            raise
        except Exception as e:
            LOG.exception(_LE("Unexpected exception: %s"),
                          six.text_type(e))
            raise
