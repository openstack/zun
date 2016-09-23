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

from zun.common import exception
from zun.common.i18n import _LE
from zun.common import utils
from zun.common.utils import translate_exception
from zun.container import driver
from zun.objects import fields


LOG = logging.getLogger(__name__)

VALID_STATES = {
    'delete': ['Stopped', 'Error'],
    'start': ['Stopped'],
    'stop': ['Running'],
    'reboot': ['Running'],
    'pause': ['Running'],
    'unpause': ['Paused'],
}


class Manager(object):
    '''Manages the running containers.'''

    def __init__(self, container_driver=None):
        super(Manager, self).__init__()
        self.driver = driver.load_container_driver(container_driver)

    def _fail_container(self, container):
        container.status = fields.ContainerStatus.ERROR
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

    def _do_container_create(self, context, container):
        LOG.debug('Creating container...', context=context,
                  container=container)

        container.task_state = fields.TaskState.IMAGE_PULLING
        container.save()
        try:
            self.driver.pull_image(container.image)
        except exception.DockerError as e:
            LOG.error(_LE("Error occured while calling docker API: %s"),
                      six.text_type(e))
            self._fail_container(container)
            return
        except Exception as e:
            LOG.exception(_LE("Unexpected exception: %s"), str(e))
            self._fail_container(container)
            return

        container.task_state = fields.TaskState.CONTAINER_CREATING
        container.save()
        try:
            container = self.driver.create(container)
        except exception.DockerError as e:
            LOG.error(_LE("Error occured while calling docker API: %s"),
                      six.text_type(e))
            container.status = fields.ContainerStatus.ERROR
        except Exception as e:
            LOG.exception(_LE("Unexpected exception: %s"), str(e))
            container.status = fields.ContainerStatus.ERROR
        finally:
            container.task_state = None
            container.save()

    @translate_exception
    def container_delete(self, context, container, force):
        LOG.debug('Deleting container...', context=context,
                  container=container.uuid)
        try:
            if not force:
                self._validate_container_state(container, 'delete')
            self.driver.delete(container, force)
            return container
        except exception.DockerError as e:
            LOG.error(_LE("Error occured while calling docker API: %s"),
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
            LOG.error(_LE("Error occured while calling docker API: %s"),
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
            LOG.error(_LE("Error occured while calling docker API: %s"),
                      six.text_type(e))
            raise
        except Exception as e:
            LOG.exception(_LE("Unexpected exception: %s"), str(e))
            raise e

    @translate_exception
    def container_reboot(self, context, container):
        LOG.debug('Rebooting container...', context=context,
                  container=container)
        try:
            self._validate_container_state(container, 'reboot')
            container = self.driver.reboot(container)
            container.save()
            return container
        except exception.DockerError as e:
            LOG.error(_LE("Error occured while calling docker API: %s"),
                      six.text_type(e))
            raise
        except Exception as e:
            LOG.exception(_LE("Unexpected exception: %s"), str(e))
            raise e

    @translate_exception
    def container_stop(self, context, container):
        LOG.debug('Stopping container...', context=context,
                  container=container)
        try:
            self._validate_container_state(container, 'stop')
            container = self.driver.stop(container)
            container.save()
            return container
        except exception.DockerError as e:
            LOG.error(_LE("Error occured while calling docker API: %s"),
                      six.text_type(e))
            raise
        except Exception as e:
            LOG.exception(_LE("Unexpected exception: %s"), str(e))
            raise e

    @translate_exception
    def container_start(self, context, container):
        LOG.debug('Starting container...', context=context,
                  container=container.uuid)
        try:
            self._validate_container_state(container, 'start')
            container = self.driver.start(container)
            container.save()
            return container
        except exception.DockerError as e:
            LOG.error(_LE("Error occured while calling docker API: %s"),
                      six.text_type(e))
            raise
        except Exception as e:
            LOG.exception(_LE("Unexpected exception: %s"), str(e))
            raise e

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
            LOG.error(_LE("Error occured while calling docker API: %s"),
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
            LOG.error(_LE("Error occured while calling docker API: %s"),
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
            LOG.error(_LE("Error occured while calling docker API: %s"),
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
            LOG.error(_LE("Error occured while calling docker API: %s"),
                      six.text_type(e))
            raise
        except Exception as e:
            LOG.exception(_LE("Unexpected exception: %s"), str(e))
            raise e
