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
from oslo_utils import strutils

from zun.common import exception
from zun.common.i18n import _LE
from zun.common import utils
from zun.common.utils import translate_exception
from zun.container import driver
from zun.image import driver as image_driver
from zun.objects import fields


LOG = logging.getLogger(__name__)

VALID_STATES = {
    'delete': ['Stopped', 'Error'],
    'start': ['Stopped'],
    'stop': ['Running'],
    'reboot': ['Running'],
    'pause': ['Running'],
    'unpause': ['Paused'],
    'kill': ['Running'],
}


class Manager(object):
    '''Manages the running containers.'''

    def __init__(self, container_driver=None):
        super(Manager, self).__init__()
        self.driver = driver.load_container_driver(container_driver)

    def _fail_container(self, container, error):
        container.status = fields.ContainerStatus.ERROR
        container.status_reason = error
        container.task_state = None
        container.save()

    def _validate_container_state(self, container, action):
        if container.status not in VALID_STATES[action]:
            raise exception.InvalidStateException(
                id=container.container_id,
                action=action,
                actual_state=container.status)

    def container_create(self, context, container):
        utils.spawn_n(self._do_container_create, context, container)

    @translate_exception
    def container_run(self, context, container):
        return self._do_container_run(context, container)

    def _do_container_run(self, context, container):
        created_container = self._do_container_create(context,
                                                      container,
                                                      reraise=True)
        return self._do_container_start(context, created_container)

    def _do_container_create(self, context, container, reraise=False):
        LOG.debug('Creating container...', context=context,
                  container=container)

        container.task_state = fields.TaskState.IMAGE_PULLING
        container.save()
        repo, tag = utils.parse_image_name(container.image)
        image_pull_policy = utils.get_image_pull_policy(
            container.image_pull_policy, tag)
        try:
            image = image_driver.pull_image(context, repo,
                                            tag, image_pull_policy)
        except exception.ImageNotFound as e:
            with excutils.save_and_reraise_exception(reraise=reraise):
                LOG.error(six.text_type(e))
                self._fail_container(container, six.text_type(e))
            return
        except exception.DockerError as e:
            with excutils.save_and_reraise_exception(reraise=reraise):
                LOG.error(_LE(
                    "Error occured while calling docker image API: %s"),
                    six.text_type(e))
                self._fail_container(container, six.text_type(e))
            return
        except Exception as e:
            with excutils.save_and_reraise_exception(reraise=reraise):
                LOG.exception(_LE("Unexpected exception: %s"),
                              six.text_type(e))
                self._fail_container(container, six.text_type(e))
            return

        container.task_state = fields.TaskState.CONTAINER_CREATING
        container.save()
        try:
            container = self.driver.create(container, image)
            container.task_state = None
            container.save()
            return container
        except exception.DockerError as e:
            with excutils.save_and_reraise_exception(reraise=reraise):
                LOG.error(_LE(
                    "Error occured while calling docker create API: %s"),
                    six.text_type(e))
                self._fail_container(container, six.text_type(e))
            return
        except Exception as e:
            with excutils.save_and_reraise_exception(reraise=reraise):
                LOG.exception(_LE("Unexpected exception: %s"),
                              six.text_type(e))
                self._fail_container(container, six.text_type(e))
            return

    def _do_container_start(self, context, container):
        LOG.debug('Starting container...', context=context,
                  container=container.uuid)
        try:
            # Although we dont need this validation, but i still
            # keep it for extra surity
            self._validate_container_state(container, 'start')
            container = self.driver.start(container)
            container.save()
            return container
        except exception.DockerError as e:
            LOG.error(_LE("Error occured while calling docker start API: %s"),
                      six.text_type(e))
            self._fail_container(container, six.text_type(e))
            raise
        except Exception as e:
            LOG.exception(_LE("Unexpected exception: %s"), str(e))
            self._fail_container(container, six.text_type(e))
            raise

    @translate_exception
    def container_delete(self, context, container, force):
        LOG.debug('Deleting container...', context=context,
                  container=container.uuid)
        try:
            force = strutils.bool_from_string(force, strict=True)
            if not force:
                self._validate_container_state(container, 'delete')
            self.driver.delete(container, force)
            return container
        except exception.DockerError as e:
            LOG.error(_LE("Error occured while calling docker delete API: %s"),
                      six.text_type(e))
            raise
        except Exception as e:
            LOG.exception(_LE("Unexpected exception: %s"), str(e))
            raise e

    @translate_exception
    def container_list(self, context):
        LOG.debug('Listing container...', context=context)
        try:
            return self.driver.list()
        except exception.DockerError as e:
            LOG.error(_LE("Error occured while calling docker list API: %s"),
                      six.text_type(e))
            raise
        except Exception as e:
            LOG.exception(_LE("Unexpected exception: %s"), str(e))
            raise e

    @translate_exception
    def container_show(self, context, container):
        LOG.debug('Showing container...', context=context,
                  container=container.uuid)
        try:
            container = self.driver.show(container)
            container.save()
            return container
        except exception.DockerError as e:
            LOG.error(_LE("Error occured while calling docker show API: %s"),
                      six.text_type(e))
            raise
        except Exception as e:
            LOG.exception(_LE("Unexpected exception: %s"), str(e))
            raise e

    @translate_exception
    def container_reboot(self, context, container, timeout):
        LOG.debug('Rebooting container...', context=context,
                  container=container)
        try:
            self._validate_container_state(container, 'reboot')
            container = self.driver.reboot(container, timeout)
            container.save()
            return container
        except exception.DockerError as e:
            LOG.error(_LE("Error occured while calling docker reboot API: %s"),
                      six.text_type(e))
            raise
        except Exception as e:
            LOG.exception(_LE("Unexpected exception: %s"), str(e))
            raise e

    @translate_exception
    def container_stop(self, context, container, timeout):
        LOG.debug('Stopping container...', context=context,
                  container=container)
        try:
            self._validate_container_state(container, 'stop')
            container = self.driver.stop(container, timeout)
            container.save()
            return container
        except exception.DockerError as e:
            LOG.error(_LE("Error occured while calling docker stop API: %s"),
                      six.text_type(e))
            raise
        except Exception as e:
            LOG.exception(_LE("Unexpected exception: %s"), str(e))
            raise e

    @translate_exception
    def container_start(self, context, container):
        return self._do_container_start(context, container)

    @translate_exception
    def container_pause(self, context, container):
        LOG.debug('Pausing container...', context=context,
                  container=container)
        try:
            self._validate_container_state(container, 'pause')
            container = self.driver.pause(container)
            container.save()
            return container
        except exception.DockerError as e:
            LOG.error(_LE("Error occured while calling docker pause API: %s"),
                      six.text_type(e))
            raise
        except Exception as e:
            LOG.exception(_LE("Unexpected exception: %s,"), str(e))
            raise e

    @translate_exception
    def container_unpause(self, context, container):
        LOG.debug('Unpausing container...', context=context,
                  container=container)
        try:
            self._validate_container_state(container, 'unpause')
            container = self.driver.unpause(container)
            container.save()
            return container
        except exception.DockerError as e:
            LOG.error(_LE("Error occured while calling docker unpause "
                          "API: %s"),
                      six.text_type(e))
            raise
        except Exception as e:
            LOG.exception(_LE("Unexpected exception: %s"), str(e))
            raise e

    @translate_exception
    def container_logs(self, context, container):
        LOG.debug('Showing container logs...', context=context,
                  container=container)
        try:
            return self.driver.show_logs(container)
        except exception.DockerError as e:
            LOG.error(_LE("Error occured while calling docker logs API: %s"),
                      six.text_type(e))
            raise
        except Exception as e:
            LOG.exception(_LE("Unexpected exception: %s"), str(e))
            raise e

    @translate_exception
    def container_exec(self, context, container, command):
        # TODO(hongbin): support exec command interactively
        LOG.debug('Executing command in container...', context=context,
                  container=container)
        try:
            return self.driver.execute(container, command)
        except exception.DockerError as e:
            LOG.error(_LE("Error occured while calling docker exec API: %s"),
                      six.text_type(e))
            raise
        except Exception as e:
            LOG.exception(_LE("Unexpected exception: %s"), str(e))
            raise e

    @translate_exception
    def container_kill(self, context, container, signal):
        LOG.debug('kill signal to container...', context=context,
                  container=container)
        try:
            self._validate_container_state(container, 'kill')
            container = self.driver.kill(container, signal)
            container.save()
            return container
        except exception.DockerError as e:
            LOG.error(_LE("Error occured while calling docker kill API: %s"),
                      six.text_type(e))
            raise

    def image_create(self, context, image):
        utils.spawn_n(self._do_image_create, context, image)

    def _do_image_create(self, context, image):
        LOG.debug('Creating image...', context=context,
                  image=image)
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
            LOG.error(_LE("Error occured while calling docker image API: %s"),
                      six.text_type(e))
            raise e
        except Exception as e:
            LOG.exception(_LE("Unexpected exception: %s"),
                          six.text_type(e))
            raise e

    @translate_exception
    def image_show(self, context, image):
        LOG.debug('Listing image...', context=context)
        try:
            self.image.list()
            return image
        except Exception as e:
            LOG.exception(_LE("Unexpected exception: %s"), str(e))
            raise e
