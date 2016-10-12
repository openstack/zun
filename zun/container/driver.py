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

import sys

from oslo_config import cfg
from oslo_log import log as logging
from oslo_utils import importutils

from zun.common.i18n import _LE
from zun.common.i18n import _LI


LOG = logging.getLogger(__name__)

driver_opts = [
    cfg.StrOpt('container_driver',
               default='docker.driver.DockerDriver',
               help="""Defines which driver to use for controlling container.

Possible values:

* ``docker.driver.DockerDriver``

Services which consume this:

* ``zun-compute``

Interdependencies to other options:

* None
""")
]
CONF = cfg.CONF
CONF.register_opts(driver_opts)


def load_container_driver(container_driver=None):
    """Load a container driver module.

    Load the container driver module specified by the container_driver
    configuration option or, if supplied, the driver name supplied as an
    argument.
    :param container_driver: a container driver name to override the config opt
    :returns: a ContainerDriver instance
    """
    if not container_driver:
        container_driver = CONF.container_driver

    if not container_driver:
        LOG.error(_LE("Container driver option required, but not specified"))
        sys.exit(1)

    LOG.info(_LI("Loading container driver '%s'"), container_driver)
    try:
        driver = importutils.import_object(
            'zun.container.%s' % container_driver)
        if not isinstance(driver, ContainerDriver):
            raise Exception(_('Expected driver of type: %s') %
                            str(ContainerDriver))

        return driver
    except ImportError:
        LOG.exception(_LE("Unable to load the container driver"))
        sys.exit(1)


class ContainerDriver(object):
    '''Base class for container drivers.'''

    def create(self, container):
        """Create a container."""
        raise NotImplementedError()

    def delete(self, container, force):
        """Delete a container."""
        raise NotImplementedError()

    def list(self):
        """List all containers."""
        raise NotImplementedError()

    def show(self, container):
        """Show the details of a container."""
        raise NotImplementedError()

    def reboot(self, container):
        """Reboot a container."""
        raise NotImplementedError()

    def stop(self, container):
        """Stop a container."""
        raise NotImplementedError()

    def start(self, container):
        """Start a container."""
        raise NotImplementedError()

    def pause(self, container):
        """Pause a container."""
        raise NotImplementedError()

    def unpause(self, container):
        """Pause a container."""
        raise NotImplementedError()

    def show_logs(self, container):
        """Show logs of a container."""
        raise NotImplementedError()

    def execute(self, container, command):
        """Execute a command in a running container."""
        raise NotImplementedError()

    def kill(self, container, signal):
        """kill signal to a container."""
        raise NotImplementedError()
