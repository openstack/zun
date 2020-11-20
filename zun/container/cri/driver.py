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

import grpc
from oslo_log import log as logging
import tenacity

from zun.common import consts
from zun.common import context as zun_context
from zun.common import exception
from zun.common.i18n import _
from zun.common import utils
import zun.conf
from zun.container import driver
from zun.criapi import api_pb2
from zun.criapi import api_pb2_grpc
from zun.network import neutron
from zun.network import os_vif_util
from zun import objects


CONF = zun.conf.CONF
LOG = logging.getLogger(__name__)


class CriDriver(driver.BaseDriver, driver.CapsuleDriver):
    """Implementation of container drivers for CRI runtime."""

    # TODO(hongbin): define a list of capabilities of this driver.
    capabilities = {}

    def __init__(self):
        super(CriDriver, self).__init__()
        channel = grpc.insecure_channel(
            'unix:///run/containerd/containerd.sock')
        self.runtime_stub = api_pb2_grpc.RuntimeServiceStub(channel)
        self.image_stub = api_pb2_grpc.ImageServiceStub(channel)

    def create_capsule(self, context, capsule, image, requested_networks,
                       requested_volumes):

        self._create_pod_sandbox(context, capsule, requested_networks)

        # TODO(hongbin): handle init containers
        for container in capsule.init_containers:
            self._create_container(context, capsule, container,
                                   requested_networks,
                                   requested_volumes)
            self._wait_for_init_container(context, container)
            container.save(context)

        for container in capsule.containers:
            self._create_container(context, capsule, container,
                                   requested_networks,
                                   requested_volumes)
            container.status = consts.RUNNING
            container.save(context)

        capsule.status = consts.RUNNING
        return capsule

    def _create_pod_sandbox(self, context, capsule, requested_networks):
        sandbox_config = self._get_sandbox_config(capsule)
        runtime = capsule.runtime or CONF.container_runtime
        if runtime == "runc":
            # pass "" to specify the default runtime which is runc
            runtime = ""

        self._write_cni_metadata(context, capsule, requested_networks)
        sandbox_resp = self.runtime_stub.RunPodSandbox(
            api_pb2.RunPodSandboxRequest(
                config=sandbox_config,
                runtime_handler=runtime,
            )
        )
        LOG.debug("podsandbox is created: %s", sandbox_resp)
        capsule.container_id = sandbox_resp.pod_sandbox_id

    def _get_sandbox_config(self, capsule):
        return api_pb2.PodSandboxConfig(
            metadata=api_pb2.PodSandboxMetadata(
                name=capsule.uuid, namespace="default", uid=capsule.uuid
            )
        )

    def _write_cni_metadata(self, context, capsule, requested_networks):
        neutron_api = neutron.NeutronAPI(context)
        security_group_ids = utils.get_security_group_ids(
            context, capsule.security_groups)
        # TODO(hongbin): handle multiple nics
        requested_network = requested_networks[0]
        network_id = requested_network['network']
        addresses, port = neutron_api.create_or_update_port(
            capsule, network_id, requested_network, consts.DEVICE_OWNER_ZUN,
            security_group_ids, set_binding_host=True)
        capsule.addresses = {network_id: addresses}

        neutron_api = neutron.NeutronAPI(zun_context.get_admin_context())
        network = neutron_api.show_network(port['network_id'])['network']
        subnets = {}
        for fixed_ip in port['fixed_ips']:
            subnet_id = fixed_ip['subnet_id']
            subnets[subnet_id] = neutron_api.show_subnet(subnet_id)['subnet']
        vif_plugin = port.get('binding:vif_type')
        vif_obj = os_vif_util.neutron_to_osvif_vif(vif_plugin, port, network,
                                                   subnets)
        state = objects.vif.VIFState(default_vif=vif_obj)
        state_dict = state.obj_to_primitive()
        capsule.cni_metadata = {consts.CNI_METADATA_VIF: state_dict}
        capsule.save(context)

    def _create_container(self, context, capsule, container,
                          requested_networks, requested_volumes):
        # pull image
        self._pull_image(context, container)

        sandbox_config = self._get_sandbox_config(capsule)
        container_config = self._get_container_config(context, container,
                                                      requested_volumes)
        response = self.runtime_stub.CreateContainer(
            api_pb2.CreateContainerRequest(
                pod_sandbox_id=capsule.container_id,
                config=container_config,
                sandbox_config=sandbox_config,
            )
        )

        LOG.debug("container is created: %s", response)
        container.container_id = response.container_id
        container.save(context)

        response = self.runtime_stub.StartContainer(
            api_pb2.StartContainerRequest(
                container_id=container.container_id
            )
        )
        LOG.debug("container is started: %s", response)

    def _get_container_config(self, context, container, requested_volumes):
        args = []
        if container.command:
            args = [str(c) for c in container.command]
        envs = []
        if container.environment:
            envs = [api_pb2.KeyValue(key=str(k), value=str(v))
                    for k, v in container.environment.items()]
        mounts = []
        if container.uuid in requested_volumes:
            req_volume = requested_volumes[container.uuid]
            mounts = self._get_mounts(context, req_volume)
        working_dir = container.workdir or ""
        labels = container.labels or []

        cpu = 0
        if container.cpu is not None:
            cpu = int(1024 * container.cpu)
        memory = 0
        if container.memory is not None:
            memory = int(container.memory) * 1024 * 1024
        linux_config = api_pb2.LinuxContainerConfig(
            security_context=api_pb2.LinuxContainerSecurityContext(
                privileged=container.privileged
            ),
            resources={
                'cpu_shares': cpu,
                'memory_limit_in_bytes': memory,
            }
        )

        # TODO(hongbin): add support for entrypoint
        return api_pb2.ContainerConfig(
            metadata=api_pb2.ContainerMetadata(name=container.name),
            image=api_pb2.ImageSpec(image=container.image),
            tty=container.tty,
            stdin=container.interactive,
            args=args,
            envs=envs,
            working_dir=working_dir,
            labels=labels,
            mounts=mounts,
            linux=linux_config,
        )

    def _pull_image(self, context, container):
        # TODO(hongbin): add support for private registry
        response = self.image_stub.PullImage(
            api_pb2.PullImageRequest(
                image=api_pb2.ImageSpec(image=container.image)
            )
        )
        LOG.debug("image is pulled: %s", response)

    def _get_mounts(self, context, volmaps):
        mounts = []
        for volume in volmaps:
            volume_driver = self._get_volume_driver(volume)
            source, destination = volume_driver.bind_mount(context, volume)
            mounts.append(api_pb2.Mount(container_path=destination,
                                        host_path=source))
        return mounts

    def _wait_for_init_container(self, context, container, timeout=3600):
        def retry_if_result_is_false(result):
            return result is False

        def check_init_container_stopped():
            status = self._show_container(context, container).status
            if status == consts.STOPPED:
                return True
            elif status == consts.RUNNING:
                return False
            else:
                raise exception.ZunException(
                    _("Container has unexpected status: %s") % status)

        r = tenacity.Retrying(
            stop=tenacity.stop_after_delay(timeout),
            wait=tenacity.wait_exponential(),
            retry=tenacity.retry_if_result(retry_if_result_is_false))
        r.call(check_init_container_stopped)

    def _show_container(self, context, container):
        container_id = container.container_id
        if not container_id:
            return

        response = self.runtime_stub.ListContainers(
            api_pb2.ListContainersRequest(
                filter={'id': container_id}
            )
        )
        if not response.containers:
            raise exception.ZunException(
                "Container %s is not found in runtime" % container_id)

        container_response = response.containers[0]
        self._populate_container(container, container_response)
        return container

    def _populate_container(self, container, response):
        self._populate_container_state(container, response)

    def _populate_container_state(self, container, response):
        state = response.state
        if state == api_pb2.ContainerState.CONTAINER_CREATED:
            container.status = consts.CREATED
        elif state == api_pb2.ContainerState.CONTAINER_RUNNING:
            container.status = consts.RUNNING
        elif state == api_pb2.ContainerState.CONTAINER_EXITED:
            container.status = consts.STOPPED
        elif state == api_pb2.ContainerState.CONTAINER_UNKNOWN:
            LOG.debug('State is unknown, status: %s', state)
            container.status = consts.UNKNOWN
        else:
            LOG.warning('Receive unexpected state from CRI runtime: %s', state)
            container.status = consts.UNKNOWN
            container.status_reason = "container state unknown"

    def delete_capsule(self, context, capsule, force):
        pod_id = capsule.container_id
        if not pod_id:
            return

        try:
            response = self.runtime_stub.StopPodSandbox(
                api_pb2.StopPodSandboxRequest(
                    pod_sandbox_id=capsule.container_id,
                )
            )
            LOG.debug("podsandbox is stopped: %s", response)
            response = self.runtime_stub.RemovePodSandbox(
                api_pb2.RemovePodSandboxRequest(
                    pod_sandbox_id=capsule.container_id,
                )
            )
            LOG.debug("podsandbox is removed: %s", response)
        except exception.CommandError as e:
            if 'error occurred when try to find sandbox' in str(e):
                LOG.error("cannot find pod sandbox in runtime")
                pass
            else:
                raise

        self._delete_neutron_ports(context, capsule)

    def _delete_neutron_ports(self, context, capsule):
        if not capsule.addresses:
            return

        neutron_ports = set()
        all_ports = set()
        for net_uuid, addrs_list in capsule.addresses.items():
            for addr in addrs_list:
                all_ports.add(addr['port'])
                if not addr['preserve_on_delete']:
                    port_id = addr['port']
                    neutron_ports.add(port_id)

        neutron_api = neutron.NeutronAPI(context)
        neutron_api.delete_or_unbind_ports(all_ports, neutron_ports)
