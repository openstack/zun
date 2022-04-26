import typing

from kubernetes import client
from oslo_log import log as logging

from zun.container.k8s import mapping
from zun.volume.driver import validate_volume_provider, VolumeDriver

LOG = logging.getLogger(__name__)


class K8sConfigMap(VolumeDriver):
    # "local" provider == bind mounts. We allow end-users to specify bind mounts
    # but transparently we are converting them to a ConfigMap.
    supported_providers = ['local']

    def __init__(self, k8s_core_v1: "client.CoreV1Api"):
        self.k8s_core_v1 = k8s_core_v1

    @validate_volume_provider(supported_providers)
    def attach(self, context, volmap):
        LOG.debug("Creating configmap for volumes %s", volmap)
        namespace = volmap.volume.project_id
        config_map = mapping.config_map(volmap)
        LOG.debug(config_map)
        try:
            self.k8s_core_v1.create_namespaced_config_map(namespace, config_map)
            LOG.info("Created configmap for volume %s", volmap.volume.uuid)
        except client.ApiException as exc:
            LOG.exception("failed")
            if exc.status == 409:
                self.k8s_core_v1.replace_namespaced_config_map(namespace, config_map)
                LOG.info("Updated configmap for volume %s", volmap.volume.uuid)
            else:
                raise
        except Exception as other:
            LOG.exception('other error')
            raise

    @validate_volume_provider(supported_providers)
    def detach(self, context, volmap):
        name = mapping.config_map_name(volmap)
        namespace = volmap.volume.project_id
        try:
            self.k8s_core_v1.delete_namespaced_config_map(name, namespace)
            LOG.info("Deleted configmap for volume %s", volmap.volume.uuid)
        except client.ApiException as exc:
            if exc.status == 404:
                LOG.warning("Configmap %s no longer exists in K8s at detach time", name)
            else:
                raise

    @validate_volume_provider(supported_providers)
    def delete(self, context, volmap):
        # There is no difference b/w detach and delete for this type of mount
        return self.detach(context, volmap)

    @validate_volume_provider(supported_providers)
    def bind_mount(self, context, volmap):
        raise NotImplementedError("K8s ConfigMap volumes cannot be bind-mounted")

    def is_volume_available(self, context, volmap):
        # This function is mostly used to know if, after attaching, the volume is ready.
        # For k8s, that is always true; once the ConfigMap exists, it's ready.
        return True, False

    def is_volume_deleted(self, context, volmap):
        return True, False
