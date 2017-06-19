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
from oslo_utils import uuidutils

from zun.common import consts
from zun.common import exception
from zun.common import utils
from zun.common.utils import translate_exception
from zun.compute import compute_node_tracker
import zun.conf
from zun.container import driver
from zun.image import driver as image_driver
from zun.image.glance import driver as glance

CONF = zun.conf.CONF
LOG = logging.getLogger(__name__)


class Manager(object):
    '''Manages the running containers.'''

    def __init__(self, container_driver=None):
        super(Manager, self).__init__()
        self.driver = driver.load_container_driver(container_driver)
        self.host = CONF.host
        self._resource_tracker = None

    def _fail_container(self, context, container, error, unset_host=False):
        container.status = consts.ERROR
        container.status_reason = error
        container.task_state = None
        if unset_host:
            container.host = None
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
            LOG.error("Error occurred while deleting sandbox: %s",
                      six.text_type(e))

    def _do_container_create(self, context, container, reraise=False):
        LOG.debug('Creating container: %s', container.uuid)

        # check if container driver is NovaDockerDriver and
        # security_groups is non empty, then return by setting
        # the error message in database
        if ('NovaDockerDriver' in CONF.container_driver and
                container.security_groups):
            msg = "security_groups can not be provided with NovaDockerDriver"
            self._fail_container(self, context, container, msg)
            return

        container.task_state = consts.SANDBOX_CREATING
        container.save(context)
        sandbox_id = None
        sandbox_image = CONF.sandbox_image
        sandbox_image_driver = CONF.sandbox_image_driver
        sandbox_image_pull_policy = CONF.sandbox_image_pull_policy
        repo, tag = utils.parse_image_name(sandbox_image)
        try:
            image, image_loaded = image_driver.pull_image(
                context, repo, tag, sandbox_image_pull_policy,
                sandbox_image_driver)
            if not image_loaded:
                self.driver.load_image(image['path'])
            sandbox_id = self.driver.create_sandbox(context, container,
                                                    image=sandbox_image)
        except Exception as e:
            with excutils.save_and_reraise_exception(reraise=reraise):
                LOG.exception("Unexpected exception: %s",
                              six.text_type(e))
                self._fail_container(context, container, six.text_type(e))
            return

        self.driver.set_sandbox_id(container, sandbox_id)
        container.task_state = consts.IMAGE_PULLING
        container.save(context)
        repo, tag = utils.parse_image_name(container.image)
        image_pull_policy = utils.get_image_pull_policy(
            container.image_pull_policy, tag)
        image_driver_name = container.image_driver
        try:
            image, image_loaded = image_driver.pull_image(
                context, repo, tag, image_pull_policy, image_driver_name)
            if not image_loaded:
                self.driver.load_image(image['path'])
        except exception.ImageNotFound as e:
            with excutils.save_and_reraise_exception(reraise=reraise):
                LOG.error(six.text_type(e))
                self._do_sandbox_cleanup(context, sandbox_id)
                self._fail_container(context, container, six.text_type(e))
            return
        except exception.DockerError as e:
            with excutils.save_and_reraise_exception(reraise=reraise):
                LOG.error("Error occurred while calling Docker image API: %s",
                          six.text_type(e))
                self._do_sandbox_cleanup(context, sandbox_id)
                self._fail_container(context, container, six.text_type(e))
            return
        except Exception as e:
            with excutils.save_and_reraise_exception(reraise=reraise):
                LOG.exception("Unexpected exception: %s",
                              six.text_type(e))
                self._do_sandbox_cleanup(context, sandbox_id)
                self._fail_container(context, container, six.text_type(e))
            return

        container.task_state = consts.CONTAINER_CREATING
        container.image_driver = image.get('driver')
        container.save(context)
        try:
            # TODO(Shunli): No limits now, claim just update compute usage.
            limits = None
            rt = self._get_resource_tracker()
            with rt.container_claim(context, container, container.host,
                                    limits):
                container = self.driver.create(context, container,
                                               sandbox_id, image)
                container.task_state = None
                container.save(context)
                return container
        except exception.DockerError as e:
            with excutils.save_and_reraise_exception(reraise=reraise):
                LOG.error("Error occurred while calling Docker create API: %s",
                          six.text_type(e))
                self._do_sandbox_cleanup(context, sandbox_id)
                self._fail_container(context, container, six.text_type(e),
                                     unset_host=True)
            return
        except Exception as e:
            with excutils.save_and_reraise_exception(reraise=reraise):
                LOG.exception("Unexpected exception: %s",
                              six.text_type(e))
                self._do_sandbox_cleanup(context, sandbox_id)
                self._fail_container(context, container, six.text_type(e),
                                     unset_host=True)
            return

    def _do_container_start(self, context, container, reraise=False):
        LOG.debug('Starting container: %s', container.uuid)
        container.task_state = consts.CONTAINER_STARTING
        container.save(context)
        try:
            container = self.driver.start(container)
            container.task_state = None
            container.save(context)
            return container
        except exception.DockerError as e:
            with excutils.save_and_reraise_exception(reraise=reraise):
                LOG.error("Error occurred while calling Docker start API: %s",
                          six.text_type(e))
                self._fail_container(context, container, six.text_type(e))
        except Exception as e:
            with excutils.save_and_reraise_exception(reraise=reraise):
                LOG.exception("Unexpected exception: %s",
                              six.text_type(e))
                self._fail_container(context, container, six.text_type(e))

    @translate_exception
    def container_delete(self, context, container, force):
        LOG.debug('Deleting container: %s', container.uuid)
        container.task_state = consts.CONTAINER_DELETING
        container.save(context)
        reraise = not force
        try:
            self.driver.delete(container, force)
        except exception.DockerError as e:
            with excutils.save_and_reraise_exception(reraise=reraise):
                LOG.error(("Error occurred while calling Docker  "
                           "delete API: %s"), six.text_type(e))
                self._fail_container(context, container, six.text_type(e))
        except Exception as e:
            with excutils.save_and_reraise_exception(reraise=reraise):
                LOG.exception("Unexpected exception: %s", six.text_type(e))
                self._fail_container(context, container, six.text_type(e))

        sandbox_id = self.driver.get_sandbox_id(container)
        if sandbox_id:
            container.task_state = consts.SANDBOX_DELETING
            container.save(context)
            try:
                self.driver.delete_sandbox(context, sandbox_id)
            except Exception as e:
                with excutils.save_and_reraise_exception(reraise=reraise):
                    LOG.exception("Unexpected exception: %s",
                                  six.text_type(e))
                    self._fail_container(context, container, six.text_type(e))
        container.task_state = None
        container.save(context)
        container.destroy(context)
        self._get_resource_tracker()

        # Remove the claimed resource
        rt = self._get_resource_tracker()
        rt.remove_usage_from_container(context, container, True)
        return container

    def add_security_group(self, context, container, security_group):
        utils.spawn_n(self._add_security_group, context, container,
                      security_group)

    def _add_security_group(self, context, container, security_group):
        LOG.debug('Adding security_group to container: %s', container.uuid)
        try:
            sandbox_id = self.driver.get_sandbox_id(container)
            self.driver.add_security_group(context, sandbox_id,
                                           security_group)
            container.security_groups += [security_group]
            container.save(context)
        except Exception as e:
            with excutils.save_and_reraise_exception(reraise=False):
                LOG.exception("Unexpected exception: %s", six.text_type(e))

    @translate_exception
    def container_list(self, context):
        LOG.debug('Listing container...')
        try:
            return self.driver.list()
        except exception.DockerError as e:
            LOG.error("Error occurred while calling Docker list API: %s",
                      six.text_type(e))
            raise
        except Exception as e:
            LOG.exception("Unexpected exception: %s", six.text_type(e))
            raise

    @translate_exception
    def container_show(self, context, container):
        LOG.debug('Showing container: %s', container.uuid)
        try:
            container = self.driver.show(container)
            if container.obj_what_changed():
                container.save(context)
            return container
        except exception.DockerError as e:
            LOG.error("Error occurred while calling Docker show API: %s",
                      six.text_type(e))
            raise
        except Exception as e:
            LOG.exception("Unexpected exception: %s", six.text_type(e))
            raise

    def _do_container_reboot(self, context, container, timeout, reraise=False):
        LOG.debug('Rebooting container: %s', container.uuid)
        container.task_state = consts.CONTAINER_REBOOTING
        container.save(context)
        try:
            container = self.driver.reboot(container, timeout)
            container.task_state = None
            container.save(context)
            return container
        except exception.DockerError as e:
            with excutils.save_and_reraise_exception(reraise=reraise):
                LOG.error(("Error occurred while calling Docker reboot "
                           "API: %s"), six.text_type(e))
                self._fail_container(context, container, six.text_type(e))
        except Exception as e:
            with excutils.save_and_reraise_exception(reraise=reraise):
                LOG.exception("Unexpected exception: %s",
                              six.text_type(e))
                self._fail_container(context, container, six.text_type(e))

    def container_reboot(self, context, container, timeout):
        utils.spawn_n(self._do_container_reboot, context, container, timeout)

    def _do_container_stop(self, context, container, timeout, reraise=False):
        LOG.debug('Stopping container: %s', container.uuid)
        container.task_state = consts.CONTAINER_STOPPING
        container.save(context)
        try:
            container = self.driver.stop(container, timeout)
            container.task_state = None
            container.save(context)
            return container
        except exception.DockerError as e:
            with excutils.save_and_reraise_exception(reraise=reraise):
                LOG.error("Error occurred while calling Docker stop API: %s",
                          six.text_type(e))
                self._fail_container(context, container, six.text_type(e))
        except Exception as e:
            with excutils.save_and_reraise_exception(reraise=reraise):
                LOG.exception("Unexpected exception: %s",
                              six.text_type(e))
                self._fail_container(context, container, six.text_type(e))

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
                LOG.error("Error occurred while calling Docker pause API: %s",
                          six.text_type(e))
                self._fail_container(context, container, six.text_type(e))
        except Exception as e:
            with excutils.save_and_reraise_exception(reraise=reraise):
                LOG.exception("Unexpected exception: %s,",
                              six.text_type(e))
                self._fail_container(context, container, six.text_type(e))

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
                LOG.error(
                    "Error occurred while calling Docker unpause API: %s",
                    six.text_type(e))
                self._fail_container(context, container, six.text_type(e))
        except Exception as e:
            with excutils.save_and_reraise_exception(reraise=reraise):
                LOG.exception("Unexpected exception: %s",
                              six.text_type(e))
                self._fail_container(context, container, six.text_type(e))

    def container_unpause(self, context, container):
        utils.spawn_n(self._do_container_unpause, context, container)

    @translate_exception
    def container_logs(self, context, container, stdout, stderr,
                       timestamps, tail, since):
        LOG.debug('Showing container logs: %s', container.uuid)
        try:
            return self.driver.show_logs(container,
                                         stdout=stdout, stderr=stderr,
                                         timestamps=timestamps, tail=tail,
                                         since=since)
        except exception.DockerError as e:
            LOG.error("Error occurred while calling Docker logs API: %s",
                      six.text_type(e))
            raise
        except Exception as e:
            LOG.exception("Unexpected exception: %s", six.text_type(e))
            raise

    @translate_exception
    def container_exec(self, context, container, command, run, interactive):
        LOG.debug('Executing command in container: %s', container.uuid)
        try:
            exec_id = self.driver.execute_create(container, command,
                                                 interactive)
            if run:
                return self.driver.execute_run(exec_id, command)
            else:
                return {'exec_id': exec_id,
                        'url': CONF.docker.docker_remote_api_url}
        except exception.DockerError as e:
            LOG.error("Error occurred while calling Docker exec API: %s",
                      six.text_type(e))
            raise
        except Exception as e:
            LOG.exception("Unexpected exception: %s", six.text_type(e))
            raise

    @translate_exception
    def container_exec_resize(self, context, exec_id, height, width):
        LOG.debug('Resizing the tty session used by the exec: %s', exec_id)
        try:
            return self.driver.execute_resize(exec_id, height, width)
        except exception.DockerError as e:
            LOG.error("Error occurred while calling Docker exec API: %s",
                      six.text_type(e))
            raise
        except Exception as e:
            LOG.exception("Unexpected exception: %s", six.text_type(e))
            raise

    def _do_container_kill(self, context, container, signal, reraise=False):
        LOG.debug('kill signal to container: %s', container.uuid)
        try:
            container = self.driver.kill(container, signal)
            container.save(context)
            return container
        except exception.DockerError as e:
            with excutils.save_and_reraise_exception(reraise=reraise):
                LOG.error("Error occurred while calling Docker kill API: %s",
                          six.text_type(e))
                self._fail_container(context, container, six.text_type(e))

    def container_kill(self, context, container, signal):
        utils.spawn_n(self._do_container_kill, context, container, signal)

    @translate_exception
    def container_update(self, context, container, patch):
        LOG.debug('Updating a container...', container=container)
        # Update only the fields that have changed
        for field, patch_val in patch.items():
            if getattr(container, field) != patch_val:
                setattr(container, field, patch_val)

        try:
            self.driver.update(container)
            container.save(context)
            return container
        except exception.DockerError as e:
            LOG.error("Error occurred while calling docker API: %s",
                      six.text_type(e))
            raise

    @translate_exception
    def container_attach(self, context, container):
        LOG.debug('Get websocket url from the container: %s', container.uuid)
        try:
            url = self.driver.get_websocket_url(container)
            token = uuidutils.generate_uuid()
            access_url = '%s?token=%s&uuid=%s' % (
                CONF.websocket_proxy.base_url, token, container.uuid)
            container.websocket_url = url
            container.websocket_token = token
            container.save(context)
            return access_url
        except Exception as e:
            LOG.error(("Error occurred while calling "
                       "get websocket url function: %s"),
                      six.text_type(e))
            raise

    @translate_exception
    def container_resize(self, context, container, height, width):
        LOG.debug('Resize tty to the container: %s', container.uuid)
        try:
            container = self.driver.resize(container, height, width)
            return container
        except exception.DockerError as e:
            LOG.error(("Error occurred while calling docker "
                       "resize API: %s"),
                      six.text_type(e))
            raise

    @translate_exception
    def container_top(self, context, container, ps_args):
        LOG.debug('Displaying the running processes inside the container: %s',
                  container.uuid)
        try:
            return self.driver.top(container, ps_args)
        except exception.DockerError as e:
            LOG.error("Error occurred while calling Docker top API: %s",
                      six.text_type(e))
            raise
        except Exception as e:
            LOG.exception("Unexpected exception: %s", six.text_type(e))
            raise

    @translate_exception
    def container_get_archive(self, context, container, path):
        LOG.debug('Copy resource from the container: %s', container.uuid)
        try:
            return self.driver.get_archive(container, path)
        except exception.DockerError as e:
            LOG.error(
                "Error occurred while calling Docker get_archive API: %s",
                six.text_type(e))
            raise
        except Exception as e:
            LOG.exception("Unexpected exception: %s", six.text_type(e))
            raise

    @translate_exception
    def container_put_archive(self, context, container, path, data):
        LOG.debug('Copy resource to the container: %s', container.uuid)
        try:
            return self.driver.put_archive(container, path, data)
        except exception.DockerError as e:
            LOG.error(
                "Error occurred while calling Docker put_archive API: %s",
                six.text_type(e))
            raise
        except Exception as e:
            LOG.exception("Unexpected exception: %s", six.text_type(e))
            raise

    @translate_exception
    def container_stats(self, context, container):
        LOG.debug('Displaying stats of the container: %s', container.uuid)
        try:
            return self.driver.stats(container)
        except exception.DockerError as e:
            LOG.error("Error occurred while calling Docker stats API: %s",
                      six.text_type(e))
            raise
        except Exception as e:
            LOG.exception("Unexpected exception: %s", six.text_type(e))
            raise

    @translate_exception
    def container_commit(self, context, container, repository, tag=None):
        LOG.debug('Commit the container: %s', container.uuid)
        snapshot_image = None
        try:
            # NOTE(miaohb): Glance is the only driver that support image
            # uploading in the current version, so we have hard-coded here.
            # https://bugs.launchpad.net/zun/+bug/1697342
            snapshot_image = image_driver.create_image(context, repository,
                                                       glance.GlanceDriver())
        except exception.DockerError as e:
            LOG.error("Error occurred while calling glance "
                      "create_image API: %s",
                      six.text_type(e))
        utils.spawn_n(self._do_container_commit, context, snapshot_image,
                      container, repository, tag)
        return snapshot_image.id

    def _do_container_image_upload(self, context, snapshot_image, data, tag):
        try:
            image_driver.upload_image_data(context, snapshot_image,
                                           tag, data, glance.GlanceDriver())
        except Exception as e:
            LOG.exception("Unexpected exception while uploading image: %s",
                          six.text_type(e))
            raise

    def _do_container_commit(self, context, snapshot_image, container,
                             repository, tag=None):
        LOG.debug('Creating image...')
        container_image = None
        container_image_id = None
        if tag is None:
            tag = 'latest'

        try:
            container_image_id = self.driver.commit(container,
                                                    repository, tag)
            container_image = self.driver.get_image(repository + ':' + tag)
        except exception.DockerError as e:
            LOG.error("Error occurred while calling docker commit API: %s",
                      six.text_type(e))
            raise
        LOG.debug('Upload image %s to glance' % container_image_id)
        self._do_container_image_upload(context, snapshot_image,
                                        container_image, tag)

    def image_pull(self, context, image):
        utils.spawn_n(self._do_image_pull, context, image)

    def _do_image_pull(self, context, image):
        LOG.debug('Creating image...')
        repo_tag = image.repo + ":" + image.tag
        try:
            pulled_image, image_loaded = image_driver.pull_image(
                context, image.repo, image.tag)
            if not image_loaded:
                self.driver.load_image(pulled_image['path'])
            image_dict = self.driver.inspect_image(repo_tag)
            image.image_id = image_dict['Id']
            image.size = image_dict['Size']
            image.save()
        except exception.ImageNotFound as e:
            LOG.error(six.text_type(e))
            return
        except exception.DockerError as e:
            LOG.error("Error occurred while calling Docker image API: %s",
                      six.text_type(e))
            raise
        except Exception as e:
            LOG.exception("Unexpected exception: %s",
                          six.text_type(e))
            raise

    @translate_exception
    def image_search(self, context, image, image_driver_name, exact_match):
        LOG.debug('Searching image...', image=image)
        try:
            return image_driver.search_image(context, image,
                                             image_driver_name, exact_match)
        except Exception as e:
            LOG.exception("Unexpected exception while searching image: %s",
                          six.text_type(e))
            raise

    def _get_resource_tracker(self):
        if not self._resource_tracker:
            rt = compute_node_tracker.ComputeNodeTracker(self.host,
                                                         self.driver)
            self._resource_tracker = rt
        return self._resource_tracker
