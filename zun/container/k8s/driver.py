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
import io
import json
import shlex
import time
from collections import defaultdict
from pathlib import Path

from kubernetes import client, config, stream, watch
from kubernetes.stream import stream
from kubernetes.stream.ws_client import WSClient
from oslo_log import log as logging
from oslo_serialization import jsonutils
from oslo_utils import units

import zun.conf
from zun import objects
from zun.common import consts
from zun.common import context as zun_context
from zun.common import exception, utils
from zun.common.docker_image import reference as docker_image
from zun.container import driver
from zun.container.k8s import exception as k8s_exc, host, mapping, network, volume

CONF = zun.conf.CONF
LOG = logging.getLogger(__name__)

# A fake "network id" for when we want to keep track of container
# addresses but the driver is not configured to integrate w/ Neutron.
UNDEFINED_NETWORK = "undefined_network"


def is_exception_like(api_exc: client.ApiException, code=None, message_like=None, **kwargs):
    if code and api_exc.status != code:
        return False
    exc_json = jsonutils.loads(api_exc.body)
    if message_like and message_like not in exc_json.get("message", ""):
        return False
    # Interpret keyword args as matchers/filters on the "details" part of the response
    details_matcher = kwargs
    if details_matcher:
        details = exc_json.get("details", {})
        return all(details[k] == v for k, v in details_matcher.items())
    return True


def _pod_ips(pod):
    if not pod.status.pod_i_ps:
        return []
    return [p.ip for p in pod.status.pod_i_ps]


class K8sDriver(driver.ContainerDriver, driver.BaseDriver):

    async_tasks = True

    # There are no defined capabilities still... but this is required to exist.
    capabilities = {}

    def __init__(self):
        admin_context = zun_context.get_admin_context()
        # This is a Zun-specific attribute that is used in various DB calls to
        # filter the result.
        admin_context.all_projects = True

        # Configs can be set in Configuration class directly or using helper utility
        config.load_kube_config(config_file=CONF.k8s.kubeconfig_file)
        # K8s APIs
        self.core_v1 = client.CoreV1Api()
        self.apps_v1 = client.AppsV1Api()
        self.custom = client.CustomObjectsApi()
        self.net_v1 = client.NetworkingV1Api()

        # self.network_api = zun_network.api(admin_context, self.net_v1)
        k8s_network = network.K8sNetwork()
        k8s_network.init(admin_context, self.net_v1)
        self.network_driver = k8s_network

        self.volume_driver = volume.K8sConfigMap(self.core_v1)

        utils.spawn_n(self._watch_pods, admin_context)

    def _watch_pods(self, context):
        def _do_watch():
            watcher = watch.Watch()
            for event in watcher.stream(
                self.core_v1.list_pod_for_all_namespaces,
                label_selector=f"{mapping.LABELS['type']}=container"):
                pod = event["object"]
                event_type = event["type"]
                container_uuid = pod.metadata.labels[mapping.LABELS["uuid"]]
                try:
                    container = objects.Container.get_by_uuid(context, container_uuid)
                    self._sync_container(container, pod, pod_event=event_type)
                    container.save()
                    LOG.info(
                        f"Synced {container_uuid} to k8s state after {event_type} event")
                except exception.ContainerNotFound:
                    # Just skip this pod, it should be cleaned up on the periodic sync
                    LOG.info(f"Skipping update on missing container '{container_uuid}'")

        backoff, max_backoff = 0.0, 128.0
        def _get_backoff(current, maximum):
            return min(max(current * 2, 1.0), maximum)

        while True:
            try:
                if backoff:
                    time.sleep(backoff)
                _do_watch()
            except client.ApiException as exc:
                LOG.error(f"Unexpected K8s API error: {exc}")
                backoff = _get_backoff(backoff, max_backoff)
            except Exception as exc:
                # This indicates a business logic failure; our code is wrong. Keep
                # the loop going but log the exception; possibly future watch events
                # will not always trigger this error and we can keep the cluster from
                # getting too far out of sync.
                LOG.exception("Unexpected error watching pods")
                backoff = _get_backoff(backoff, max_backoff)

    def periodic_sync(self, context):
        """Called by the compute manager periodically.

        Use this to perform cleanup in case state on K8s has diverged from desired.
        """
        # TODO(jason): delete dangling neutron ports
        # TODO(jason): delete dangling expose net policies

        ns_list = self.core_v1.list_namespace(
            label_selector=mapping.LABELS["project_id"])
        network_policy_list = self.net_v1.list_network_policy_for_all_namespaces()
        network_policy_map = defaultdict(list)
        for netpolicy in network_policy_list.items:
            network_policy_map[netpolicy.metadata.namespace].append(netpolicy)

        for ns in ns_list.items:
            ns_name = ns.metadata.name
            project_id = ns.metadata.labels[mapping.LABELS["project_id"]]
            network_policies = network_policy_map[ns_name]

            default_network_policy = mapping.default_network_policy(project_id)
            if not any(
                np.metadata.name == default_network_policy["metadata"]["name"]
                for np in network_policies
            ):
                # Create a default policy that allows pods within the same namespace
                # to communicate directly with eachother.
                self.net_v1.create_namespaced_network_policy(
                    ns_name, default_network_policy)
                LOG.info(f"Created default network policy for project {project_id}")

    def create(self, context, container, image, requested_networks,
               requested_volumes):
        """Create a container."""
        if requested_networks:
            LOG.warning((
                "K8s containers cannot be attached to Neutron networks, ignoring "
                "requested_networks = %s"), requested_networks)

        def _create_deployment():
            secret_info_list = self._get_secrets_for_image(image["image"], context)
            self.apps_v1.create_namespaced_deployment(
                container.project_id,
                mapping.deployment(
                    container, image, requested_volumes=requested_volumes,
                    image_pull_secrets=[s["name"] for s in secret_info_list if s["secret"]])
            )
            LOG.info("Created deployment for %s in %s", container.uuid,
                container.project_id)

        try:
            _create_deployment()
        except client.ApiException as exc:
            # The first time we create a deployment for a project there will not yet
            # be a namespace; handle this and create namespace in this case.
            if is_exception_like(exc, code=404, kind="namespaces"):
                self.core_v1.create_namespace(mapping.namespace(container))
                LOG.info("Auto-created namespace %s", container.project_id)
                _create_deployment()
            else:
                raise

        container.host = CONF.host
        # K8s containers are always auto-removed
        container.auto_remove = True
        # Also mark them as interactive to fool the Horizon dashboard so that it will
        # allow rendering the console, which we will be wiring up separately.
        container.interactive = container.tty = True
        container.save()

        # Note: requested_networks are effectively ignored. On K8s all pods are on
        # the same network. However, we will create "shadow" ports in Neutron so that
        # we can route Floating IP traffic to Pod IP addresses, once we know what
        # they are.
        if container.exposed_ports:
            self.net_v1.create_namespaced_network_policy(
                container.project_id, mapping.exposed_port_network_policy(container))
            LOG.info("Created port expose networkpolicy for %s", container.uuid)

        return container

    def _sync_container(self, container, pod, pod_event=None):
        if container.status == consts.DELETED:
            return

        if not pod or pod_event == "DELETED":
            container.status = consts.STOPPED
            # Also clear task state; most container status changes happen async and
            # we need to tell Zun that the transition is finished.
            container.task_state = None
            return

        pod_status = pod.status

        def get_condition(condition_type):
            return next(iter([
                c for c in (pod_status.conditions or []) if c.type == condition_type
            ]), None)

        def fail_due_to_condition(condition):
            container.status = consts.ERROR
            container.task_state = None
            container.status_reason = condition.message
            container.status_detail = condition.reason

        def transition_status(to_status):
            if container.status != to_status:
                container.status = to_status
                # Also clear task state to indicate we are done.
                container.task_state = None

        if pod_status.phase == "Pending":
            # Pending = the pod is still in the process of creating/starting.
            schedule_condition = get_condition("PodScheduled")
            # Special case, when the pod is pending but has a Unschedulable condition,
            # it means there was no node it could be scheduled on. Fail quickly in this
            # case to match behavior w/ the filter scheduler.
            if (schedule_condition and
                schedule_condition.status != "True" and
                schedule_condition.reason == "Unschedulable"):
                fail_due_to_condition(schedule_condition)
                return
            else:
                transition_status(consts.CREATING)
        elif pod_status.phase == "Running":
            # The pod has been created. The container under the pod may however still
            # be having trouble starting.
            ready_condition = get_condition("Ready")
            if ready_condition and ready_condition.status != "True":
                container_status = pod_status.container_statuses[0]
                # Give it 2 restarts to reduce reporting of transient failures
                if container_status.restart_count > 2:
                    fail_due_to_condition(ready_condition)
                    return
                else:
                    # The container is still starting for the first time
                    transition_status(consts.CREATED)
                    container.task_state = consts.CONTAINER_STARTING
            else:
                transition_status(consts.RUNNING)
        elif pod_status.phase == "Succeeded":
            # The pod has exited; this means the container stopped with code 0.
            transition_status(consts.STOPPED)
        elif pod_status.phase == "Failed":
            transition_status(consts.ERROR)
        else:
            LOG.error(
                "Unknown pod phase '%s', interpreting as Error", pod_status.phase)
            transition_status(consts.ERROR)

        container.status_reason = pod_status.reason
        container.status_detail = pod_status.message

        container.hostname = pod.spec.hostname
        container.container_id = pod.metadata.name

        pod_container = pod.spec.containers[0]
        container.command = pod_container.command
        container.ports = [port.container_port for port in (pod_container.ports or [])]

        requested_fixed_ips = set(_pod_ips(pod))
        container.addresses = (
            self.network_driver.connect_container_to_network(
                container, None, requested_fixed_ips))

    def commit(self, context, container, repository, tag):
        """Commit a container."""
        raise NotImplementedError("K8s does not support container snapshot currently")

    def delete(self, context, container, force):
        """Delete a container."""
        name = mapping.name(container)
        try:
            self.apps_v1.delete_namespaced_deployment(name, container.project_id)
            LOG.info(f"Deleted deployment {name} in {container.project_id}")
        except client.ApiException as exc:
            if not is_exception_like(exc, code=404):
                # 404 will be raised of the deployment was already deleted or never
                # was created in the first place.
                raise
        self.network_driver.disconnect_container_from_network(container, None)

    def list(self, context):
        """List all containers."""
        deployment_list = self.apps_v1.list_deployment_for_all_namespaces(
            label_selector=mapping.LABELS['uuid'])
        uuid_to_deployment_map = {
            deployment.metadata.labels[mapping.LABELS["uuid"]]: deployment
            for deployment in deployment_list.items
        }

        # Then pull a list of all Zun containers for the host
        local_containers = objects.Container.list_by_host(context, CONF.host)
        non_existent_containers = []

        for container in local_containers:
            matching_deployment = uuid_to_deployment_map.get(container.uuid)

            if container.status in (consts.DELETED):
                if matching_deployment:
                    # Clean up the orphan deployment
                    self.apps_v1.delete_namespaced_deployment(
                        matching_deployment.metadata.name, container.project_id)
                continue
            elif container.task_state is not None:
                # Skip zun containers in some other state transition, otherwise
                # they could get marked as DELETED due to the container not having
                # container_id set (b/c it is still pending)
                continue

            # If container_id is not set the container did not finish creating.
            if not container.container_id or not matching_deployment:
                non_existent_containers.append(container)

        return local_containers, non_existent_containers

    def _get_local_containers(self, context, uuids):
        host_containers = objects.Container.list_by_host(context, CONF.host)
        uuids = list(set(uuids) | set([c.uuid for c in host_containers]))
        containers = objects.Container.list(context,
                                            filters={'uuid': uuids})
        return containers

    def update_containers_states(self, context, all_containers, manager):
        # TODO(jason): sync security group net policies (?)

        local_containers, non_existent_containers = self.list(context)

        pod_map = {
            pod.metadata.labels[mapping.LABELS["uuid"]]: pod
            for pod in self.core_v1.list_pod_for_all_namespaces(
                label_selector=f"{mapping.LABELS['type']}=container"
            ).items
        }

        for container in local_containers:
            if container.task_state is not None:
                # Container is in the middle of an operation; let it finish (the watcher
                # should be handling updates for it).
                continue
            pod = pod_map.get(container.uuid)
            self._sync_container(container, pod)
            container.save(context)

        for container in non_existent_containers:
            if container.host == CONF.host:
                container.status = consts.DELETED
                container.save(context)

    def show(self, context, container):
        """Show the details of a container."""
        return container

    def _pod_for_container(self, context, container):
        pod_list = self.core_v1.list_namespaced_pod(
            container.project_id,
            label_selector=mapping.label_selector(container)
        )
        pod = pod_list.items[0] if pod_list.items else None
        return pod

    def reboot(self, context, container, timeout):
        """Reboot a container."""
        self.stop(context, container, timeout)
        self.start(context, container)

    def stop(self, context, container, timeout):
        """Stop a container."""
        self._update_replicas(container, 0)
        return container

    def start(self, context, container):
        """Start a container."""
        self._update_replicas(container, 1)
        return container

    def _update_replicas(self, container, replicas):
        deployment_name = mapping.name(container)
        self.apps_v1.patch_namespaced_deployment(
            deployment_name,
            container.project_id, {
                "spec": {
                    "replicas": replicas,
                }
            })
        LOG.info("Patched deployment %s to %s replicas", deployment_name, replicas)

    def pause(self, context, container):
        """Pause a container."""
        raise NotImplementedError()

    def unpause(self, context, container):
        """Unpause a container."""
        raise NotImplementedError()

    def show_logs(
        self,
        context,
        container,
        stdout=True,
        stderr=True,
        timestamps=False,
        tail="all",
        since=None,
    ):
        """Show logs of a container."""
        pod = self._pod_for_container(context, container)
        if not pod:
            return None
        try:
            return self.core_v1.read_namespaced_pod_log(
                pod.metadata.name,
                container.project_id,
                tail_lines=(tail if tail and tail != "all" else None),
                timestamps=timestamps,
                since_seconds=since
            )
        except client.ApiException as exc:
            if not is_exception_like(exc, code=400, message_like="ContainerCreating"):
                raise

    def _connect_pod_exec(self, context, container, command: "list[str]", stdin: "bool"=False) -> "WSClient":
        pod = self._pod_for_container(context, container)
        if not pod:
            raise exception.ContainerNotFound()

        pod_name = pod.metadata.name

        LOG.info(f"Connecting to pod {pod_name} for: {command}")

        # The get/post exec command expect a websocket interface; the 'stream' helper
        # library helps wrapping up such requests in a websocket and proxying/buffering
        # the response output.
        ws_client: "WSClient" = stream(
            self.core_v1.connect_get_namespaced_pod_exec,
            pod_name,
            container.project_id,
            command=shlex.split(command),
            stderr=True, stdin=stdin,
            stdout=True, tty=False,
            _preload_content=False,
        )

        return ws_client

    def execute_create(self, context, container, command, interactive):
        """Create an execute instance for running a command."""
        ws_client = self._connect_pod_exec(context, container, command, stdin=False)
        ws_client.run_forever(timeout=CONF.k8s.execute_timeout)

        try:
            # NOTE(jason): it's important to call this before `read_all`, which clears all
            # channels, including the "error" channel which carries the exit status info.
            # This is likely a bug in the python k8s client.
            exit_code = ws_client.returncode
            output = ws_client.read_all()
        except ValueError:
            # This can happen if the returncode on k8s response is not castable
            # to an integer. Namely, this will happen if the command could not be found
            # at all, causing an error at execution create time, rather than runtime.
            output = "Malformed command, or binary not found in container"
            exit_code = -1

        return {"output": output, "exit_code": exit_code}

    def execute_run(self, exec_id, command):
        """Run the command specified by an execute instance."""
        # For k8s driver, exec_id is the exec response handle we returned in execute_create,
        # which already has all the info.
        return exec_id["output"], exec_id["exit_code"]

    def execute_resize(self, exec_id, height, width):
        """Resizes the tty session used by the exec."""
        # Write to the websocket open for the exec
        raise NotImplementedError()

    def kill(self, context, container, signal):
        """Kill a container with specified signal."""
        raise NotImplementedError()

    def get_websocket_url(self, context, container):
        """Get websocket url of a container."""
        host = self.core_v1.api_client.configuration.host.replace("https:", "wss:")
        namespace = context.project_id
        pod = self._pod_for_container(context, container)
        if not pod:
            raise exception.ContainerNotFound()

        name = pod.metadata.name
        query = "command=/bin/sh&stderr=true&stdout=true&stdin=true&tty=true"
        return f"{host}/api/v1/namespaces/{namespace}/pods/{name}/exec?{query}"

    def get_websocket_opts(self, context, container):
        config = self.core_v1.api_client.configuration
        certfile, keyfile, cafile = (
            config.cert_file, config.key_file, config.ssl_ca_cert)
        cert = Path(certfile).read_text()
        key = Path(keyfile).read_text()
        ca = Path(cafile).read_text()

        return {
            "cert": cert,
            "key": key,
            "ca": ca,
            "channels": {
                "stdin": 0,
                "stdout": 1,
                "stderr": 2,
                "error": 3,
                "resize": 4,
            }
        }

    def resize(self, context, container, height, width):
        """Resize tty of a container."""
        height = int(height)
        width = int(width)
        if container.websocket_url:
            pass
        # Really this only affects the TTY of an open exec process (e.g., the attach handle)
        raise NotImplementedError()

    def top(self, context, container, ps_args):
        """Display the running processes inside the container."""
        raise NotImplementedError()

    @utils.check_container_id
    def get_archive(self, context, container, path):
        """Copy resource from a container."""
        ws_client = self._connect_pod_exec(
            context, container, f"tar cf - -C {path} .", stdin=False)

        start = time.time()
        tar_bytes = io.BytesIO()
        while ws_client.is_open():
            if time.time() - start > CONF.k8s.archive_timeout:
                ws_client.close()
                raise k8s_exc.K8sException("Timed out reading pod archive")

            chunk: str = ws_client.read_stdout()
            if chunk:
                # It seems that the k8s client uses ascii encoding when dealing with
                # binary data or output.
                tar_bytes.write(chunk.encode("ascii"))

        try:
            exit_code = ws_client.returncode
        except ValueError:
            exit_code = -1

        if exit_code < 0:
            raise k8s_exc.K8sException("Failed tar invocation during get_archive")

        tar_size = tar_bytes.tell()
        tar_bytes.seek(0)
        tar_contents = tar_bytes.read()

        return tar_contents, {"name": f"{path}.tar", "size": tar_size}

    @utils.check_container_id
    def put_archive(self, context, container, path, data):
        """Copy resource to a container."""
        ws_client = self._connect_pod_exec(
            context, container, f"tar xmf - -C {path}", stdin=True)

        ws_client.write_stdin(data)
        ws_client.run_forever(timeout=CONF.k8s.archive_timeout)
        try:
            exit_code = ws_client.returncode
        except ValueError:
            exit_code = -1

        if exit_code < 0:
            raise k8s_exc.K8sException("Failed tar invocation during put_archive")

    def stats(self, context, container):
        """Display stats of the container."""
        pod_metric_list = self.custom.list_namespaced_custom_object(
            'metrics.k8s.io', 'v1beta1', container.project_id, 'pods')

        for pod_metrics in pod_metric_list["items"]:
            if pod_metrics["metadata"]["labels"][mapping.LABELS["uuid"]] == container.uuid:
                return pod_metrics["containers"][0]["usage"]
        return None

    def get_container_name(self, container):
        """Retrieve container name."""
        return mapping.name(container)

    def get_addresses(self, context, container):
        """Retrieve IP addresses of the container."""
        pod = self._pod_for_container(context, container)
        return _pod_ips(pod) if pod else []

    def update(self, context, container):
        """Update a container."""
        # In the Docker driver, this allows updating mostly CPU and memory claims.
        # We could support this in the future by patching the Deployment resource.
        raise NotImplementedError(
            "K8s driver does not yet support updating resource limits")

    def _get_cluster_metrics(self):
        node_list = self.core_v1.list_node()
        metrics_by_node_name = {
            node.metadata.name: {
                "capacity": node.status.capacity,
                "allocatable": node.status.allocatable,
                # Put defaults here; down nodes won't be reporting usage metrics
                "usage": {"cpu": "0n", "memory": "0Ki"},
            }
            for node in node_list.items
        }

        node_metrics_list = self.custom.list_cluster_custom_object(
            'metrics.k8s.io', 'v1beta1', 'nodes')
        # Because this is a custom resource, it's not wrapped in a nice object.
        for node_metric in node_metrics_list["items"]:
            metrics_by_node_name[node_metric["metadata"]["name"]]["usage"] = (
                node_metric["usage"])

        pod_list = self.core_v1.list_pod_for_all_namespaces(
            label_selector=f"{mapping.LABELS['type']}=container"
        )
        pod_statuses = defaultdict(list)
        for pod in pod_list.items:
            pod_statuses[pod.status.phase].append({
                "name": pod.metadata.name,
                "node": pod.spec.node_name,
            })

        return host.K8sClusterMetrics({
            "nodes": metrics_by_node_name,
            "pods": pod_statuses,
        })

    def get_host_info(self, cluster_metrics=None):
        if not cluster_metrics:
            cluster_metrics = self._get_cluster_metrics()

        running = cluster_metrics.running_containers()
        stopped = cluster_metrics.stopped_containers()
        paused = 0  # K8s has no concept of paused containers
        total = cluster_metrics.total_containers()

        total_cpus, _ = cluster_metrics.cpus()

        architecture = os_type = os = kernel_version = docker_root_dir = "n/a"
        enable_cpu_pinning = False

        labels = {
            # This is used in the K8sFilter for scheduling
            "container_driver": "k8s",
        }
        runtimes = []

        return {'total_containers': total,
                'running_containers': running,
                'paused_containers': paused,
                'stopped_containers': stopped,
                'cpus': total_cpus,
                'architecture': architecture,
                'os_type': os_type,
                'os': os,
                'kernel_version': kernel_version,
                'labels': labels,
                'runtimes': runtimes,
                'docker_root_dir': docker_root_dir,
                'enable_cpu_pinning': enable_cpu_pinning}

    # This is NOT in the base implementation but it needs to be! It's required.
    # And again... nothing driver specific here. But, it should be updated to access
    # all of this information in a single function; it's expensive in K8s land to split
    # it up b/c there's not a straightforward way to share the results of the common
    # API response (from metrics-server) that provides this.
    def get_available_resources(self):
        cluster_metrics = self._get_cluster_metrics()

        data = {}

        numa_topo_obj = self.get_host_numa_topology(cluster_metrics=cluster_metrics)
        data['numa_topology'] = numa_topo_obj

        meminfo = self.get_host_mem(cluster_metrics=cluster_metrics)
        (mem_total, mem_free, mem_ava, mem_used) = meminfo
        data['mem_total'] = mem_total // units.Ki
        data['mem_free'] = mem_free // units.Ki
        data['mem_available'] = mem_ava // units.Ki
        data['mem_used'] = mem_used // units.Ki

        info = self.get_host_info(cluster_metrics=cluster_metrics)
        data['total_containers'] = info['total_containers']
        data['running_containers'] = info['running_containers']
        data['paused_containers'] = info['paused_containers']
        data['stopped_containers'] = info['stopped_containers']
        data['cpus'] = info['cpus']
        data['architecture'] = info['architecture']
        data['os_type'] = info['os_type']
        data['os'] = info['os']
        data['kernel_version'] = info['kernel_version']
        data['labels'] = info['labels']
        data['runtimes'] = info['runtimes']
        data['enable_cpu_pinning'] = info['enable_cpu_pinning']

        disk_total, disk_reserved = self.get_total_disk_for_container(cluster_metrics=cluster_metrics)
        data['disk_total'] = disk_total - disk_reserved

        disk_quota_supported = self.node_support_disk_quota()
        data['disk_quota_supported'] = disk_quota_supported

        return data

    def get_host_mem(self, cluster_metrics=None):
        if not cluster_metrics:
            cluster_metrics = self._get_cluster_metrics()

        return cluster_metrics.memory()

    def get_pci_resources(self):
        pci_info = []
        return jsonutils.dumps(pci_info)

    def get_host_numa_topology(self, cluster_metrics=None):
        if not cluster_metrics:
            cluster_metrics = self._get_cluster_metrics()

        numa_node = objects.NUMANode()
        numa_node.id = "0"
        numa_node.cpuset = set(["0"])
        numa_node.pinned_cpus = set([])
        mem_total, _, mem_avail, _ = cluster_metrics.memory()
        numa_node.mem_total = mem_total
        numa_node.mem_available = mem_avail

        numa_topology = objects.NUMATopology()
        numa_topology.nodes = [numa_node]

        return numa_topology

    def get_total_disk_for_container(self, cluster_metrics=None):
        if not cluster_metrics:
            cluster_metrics = self._get_cluster_metrics()

        return cluster_metrics.disk()

    def get_available_nodes(self):
        # TODO: what would be the impact of surfacing all the K8s nodes in the cluster
        # here? How would we deal with failures? Potentially if we surfaced all nodes
        # here we would be able to use the Zun scheduler more directly.
        return [CONF.host]

    def node_support_disk_quota(self):
        # TODO: might want to set this to true if we can allocate disk quotas on k8s.
        return False

    def get_host_default_base_size(self):
        return None

    #
    # Volume (bind mount) management
    # K8s does not support cinder mounts at the moment, but this could be possible
    # at some point with PersistentVolume claims.
    #

    def attach_volume(self, context, volume_mapping):
        return self.volume_driver.attach(context, volume_mapping)

    def detach_volume(self, context, volume_mapping):
        return self.volume_driver.detach(context, volume_mapping)

    def delete_volume(self, context, volume_mapping):
        return self.volume_driver.delete(context, volume_mapping)

    def is_volume_available(self, context, volume_mapping):
        return self.volume_driver.is_volume_available(context, volume_mapping)

    def is_volume_deleted(self, context, volume_mapping):
        return self.volume_driver.is_volume_deleted(context, volume_mapping)

    #
    # Security group management
    #

    def add_security_group(self, context, container, security_group_id, **kwargs):
        return self.network_driver.add_security_groups_to_ports(
            container, [security_group_id])

    def remove_security_group(self, context, container, security_group_id, **kwargs):
        return self.network_driver.remove_security_groups_from_ports(
            container, [security_group_id])

    #
    # Network management
    #

    def network_detach(self, context, container, network):
        # this is not supported in k8s
        raise NotImplementedError()

    def network_attach(self, context, container, requested_network):
        # not supported in k8s
        raise NotImplementedError()

    #
    # (Unused?) Network lifecycle independent of container. This seems to be
    # analagous to `docker network ...` commands but appears unused.
    #

    def create_network(self, context, network):
        raise NotImplementedError()

    def delete_network(self, context, network):
        raise NotImplementedError()

    def inspect_network(self, network):
        raise NotImplementedError()

    #
    # Image management
    #

    def pull_image(self, context, repo, tag, image_pull_policy, image_driver_name, **kwargs):
        for secret_info in self._get_secrets_for_image(repo, context):
            # Create a new secret for an existing registry
            if secret_info["registry"] and not secret_info["secret"]:
                LOG.info(f"Creating new secret {secret_info['name']}")
                secret = client.V1Secret()
                secret.metadata = client.V1ObjectMeta(name=secret_info["name"])
                secret.type = "kubernetes.io/dockerconfigjson"
                username = secret_info['registry'].username
                password = secret_info['registry'].password
                auth = utils.encode_file_data(f"{username}:{password}".encode("utf-8"))
                data = {
                    "auths": {
                        secret_info["registry"].domain: {
                            "auth": auth,
                        }
                    }
                }
                secret.data = {
                    ".dockerconfigjson": utils.encode_file_data(json.dumps(data).encode("utf-8"))
                }
                self.core_v1.create_namespaced_secret(namespace=str(context.project_id), body=secret)
        if image_driver_name == 'docker':
            # K8s will actually load the image, just tell Zun it is done.
            image_loaded = True
            return {'image': repo, 'path': None, 'driver': image_driver_name}, image_loaded
        else:
            raise NotImplementedError()

    def search_image(self, context, repo, tag, driver_name, exact_match):
        raise NotImplementedError()

    def create_image(self, context, image_name, image_driver):
        raise NotImplementedError()

    def upload_image_data(self, context, image, image_tag, image_data, image_driver):
        raise NotImplementedError()

    def delete_committed_image(self, context, img_id, image_driver):
        raise NotImplementedError()

    def delete_image(self, context, img_id, image_driver):
        raise NotImplementedError()

    #
    # Capsule management - a 'capsule' is really a pod, and we could attempt to
    # translate them to k8s pods here.
    #

    def create_capsule(self, context, capsule, **kwargs):
        raise NotImplementedError()

    def delete_capsule(self, context, capsule, **kwargs):
        raise NotImplementedError()

    def _get_secrets_for_image(self, image, context):
        image_parts = docker_image.Reference.parse(image)
        domain, _ = image_parts.split_hostname()
        secrets = []
        for registry in objects.Registry.list(context):
            if registry.domain == domain:
                # NOTE this assumes (domain, username) is unique per project
                name = str(registry.uuid)
                secret = None
                try:
                    secret = self.core_v1.read_namespaced_secret(name, context.project_id)
                except client.exceptions.ApiException as e:
                    if e.status != 404:
                        raise
                secrets.append({
                    "name": name,
                    "secret": secret,
                    "registry": registry,
                })
        return secrets
