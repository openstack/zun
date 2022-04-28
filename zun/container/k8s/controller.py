from oslo_log import log as logging
import pecan

from zun.api.controllers import base
from zun.common import exception
from zun.container.k8s import mapping

LOG = logging.getLogger(__name__)


class K8sController(base.Controller):
    _custom_actions = {
        'device_profiles': ['GET'],
    }

    @pecan.expose('json')
    @exception.wrap_pecan_controller_exception
    def device_profiles(self):
        """Display configured device profiles and what K8s resources they map to.
        """
        return mapping.device_profile_resources()
