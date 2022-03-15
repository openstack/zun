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

from collections import defaultdict
from itertools import chain
from pathlib import Path
import shlex
import time

from kubernetes import client, config, stream, watch
from kubernetes.stream import stream
from kubernetes.stream.ws_client import WSClient
from oslo_log import log as logging
from oslo_serialization import jsonutils
from oslo_utils import units

from zun.common import consts
from zun.common import context as zun_context
from zun.common import exception
from zun.common import utils
import zun.conf
from zun.container import driver
from zun.network import neutron
from zun import objects

CONF = zun.conf.CONF
LOG = logging.getLogger(__name__)
LABEL_NAMESPACE = "zun.openstack.org"
LABELS = {
    "uuid": f"{LABEL_NAMESPACE}/uuid",
    "type": f"{LABEL_NAMESPACE}/type",
    "project_id": f"{LABEL_NAMESPACE}/project_id",
    "exposed": f"{LABEL_NAMESPACE}/exposed",
    "blazar_reservation_id": "blazar.openstack.org/reservation_id",
    "blazar_project_id": "blazar.openstack.org/project_id",
}
# A fake "network id" for when we want to keep track of container
# addresses but the driver is not configured to integrate w/ Neutron.
UNDEFINED_NETWORK = "undefined_network"

def resources_request_provider(container):
    if not container.annotations:
        return None

    device_profiles = container.annotations.get(utils.DEVICE_PROFILE_ANNOTATION)
    if not device_profiles:
        return None

    dp_mappings = CONF.k8s.device_profile_mappings
    if not dp_mappings:
        return None

    resource_map = {}
    for mapping in dp_mappings:
        dp_name, k8s_resources = mapping.split("=")
        # Convert <dp_name>=<k8s_resource>:<amount>[,<k8s_resource>:<amount>...]
        # to {<dp_name>: {<k8s_resource>: <amount>[, <k8s_resource>: <amount>...]}
        dp_resources = resource_map.setdefault(dp_name, {})
        for k8s_resource in k8s_resources.split(","):
            k8s_resource_name, k8s_resource_amount = k8s_resource.split(":")
            dp_resources[k8s_resource_name] = int(k8s_resource_amount)

    resources_request = {"limits": {}}
    for dp_name in device_profiles.split(","):
        if dp_name not in resource_map:
            raise ValueError(
                "Missing mapping for device_profile '%s', ensure it has been added "
                "to device_profile_mappings." % dp_name)
        resources_request["limits"].update(resource_map[dp_name])

    return resources_request


def pod_label_provider(container):
    pod_labels = container.labels or {}
    pod_labels[LABELS["type"]] = "container"
    pod_labels[LABELS["uuid"]] = container.uuid
    pod_labels[LABELS["project_id"]] = container.project_id
    pod_labels[LABELS["exposed"]] = "true" if container.exposed_ports else "false"
    return pod_labels


def container_env_provider(container):
    if not container.environment:
        return []
    return [
        {"name": name, "value": value}
        for name, value in container.environment.items()
    ]


def container_ports_provider(container):
    container_ports = []
    for port in (container.exposed_ports or []):
        port_spec = port.split("/")
        portnum = int(port_spec[0])
        if len(port_spec) > 1:
            protocol = port_spec[1].upper()
            # Should have been asserted in API layer, just double-check.
            assert protocol in ["TCP", "UDP"]
        else:
            protocol = "TCP"
        container_ports.append({"port": portnum, "protocol": protocol})
    return container_ports


def label_selector_provider(container):
    return f"{LABELS['uuid']}={container.uuid}"


def name_provider(container):
    return "zun-" + container.uuid


def deployment_provider(container, image):
    resources_request = resources_request_provider(container)
    pod_labels = pod_label_provider(container)
    container_env = container_env_provider(container)
    liveness_probe = restart_policy = None

    if image['tag']:
        image_repo = image['repo'] + ":" + image['tag']
    else:
        image_repo = image['repo']

    if container.restart_policy:
        restart_policy = container.restart_policy["Name"]

    # The time unit in docker of heath checking is us, and the unit
    # of interval and timeout is seconds.
    if container.healthcheck:
        liveness_probe = {
            "exec": container.healthcheck.get("test", ""),
            "failureThreshold": int(container.healthcheck.get('retries', 3)),
            "periodSeconds": int(container.healthcheck.get("interval", 10)),
            "timeoutSeconds": int(container.healthcheck.get('timeout', 0)),
        }

    deployment_labels = {
        LABELS["uuid"]: container.uuid,
        LABELS["project_id"]: container.project_id,
    }

    # Ensure user pods are never scheduled onto control plane infra
    node_selector_expressions = [
        {
            "key": "node-role.kubernetes.io/control-plane",
            "operator": "NotIn",
            "values": ["true"]
        },
    ]

    reservation_id = container.annotations.get(utils.RESERVATION_ANNOTATION)
    if reservation_id:
        # Add the reservation ID to the deployment labels; this enables the reservation
        # system to find the deployments tied to the reservation for cleanup.
        deployment_labels[LABELS["blazar_reservation_id"]] = reservation_id
        # Ensure the deployment lands on a reserved kubelet.
        node_selector_expressions.extend([
            {
                "key": LABELS["blazar_project_id"],
                "operator": "In",
                "values": [container.project_id],
            },
            {
                "key": LABELS["blazar_reservation_id"],
                "operator": "In",
                "values": [reservation_id],
            }
        ])

    return {
        "metadata": {
            "name": name_provider(container),
            "labels": deployment_labels,
        },
        "spec": {
            "replicas": 1,
            "selector": {
                "matchLabels": pod_labels,
            },
            "template": {
                "metadata": {
                    "labels": pod_labels,
                },
                "spec": {
                    "affinity": {
                        "nodeAffinity": {
                            "requiredDuringSchedulingIgnoredDuringExecution": {
                                "nodeSelectorTerms": [
                                    {
                                        "matchExpressions": node_selector_expressions,
                                    },
                                ],
                            },
                        },
                    },
                    "containers": [
                        {
                            "args": container.command,
                            "command": container.entrypoint,
                            "env": container_env,
                            "image": image_repo,
                            "imagePullPolicy": "",
                            "name": container.name,
                            "ports": [
                                {
                                    "containerPort": port_spec["port"],
                                    "protocol": port_spec["protocol"]
                                } for port_spec in container_ports_provider(container)
                            ],
                            "stdin": container.interactive,
                            "tty": container.tty,
                            "volumeDevices": [],
                            "volumeMounts": [],
                            "workingDir": container.workdir,
                            "resources": resources_request,
                            "livenessProbe": liveness_probe,
                        }
                    ],
                    "hostname": container.hostname,
                    "nodeName": None, # Could be a specific node
                    "volumes": [],
                    "restartPolicy": restart_policy,
                    "privileged": container.privileged,
                }
            },
        },
    }


def to_num_bytes(size_spec: str):
    for unit in ["Gi", "G", "Mi", "M", "Ki", "K"]:
        if size_spec.endswith(unit):
            return int(size_spec.rstrip(unit)) * getattr(units, unit)
    return int(size_spec)


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

        if CONF.k8s.neutron_network:
            self.neutron = neutron.NeutronAPI(admin_context)
            self.neutron_network_id = (
                self.neutron.get_neutron_network(CONF.k8s.neutron_network)["id"])
        else:
            self.neutron = self.neutron_network_id = None

        # Configs can be set in Configuration class directly or using helper utility
        config.load_kube_config(config_file=CONF.k8s.kubeconfig_file)
        # K8s APIs
        self.core_v1 = client.CoreV1Api()
        self.apps_v1 = client.AppsV1Api()
        self.custom = client.CustomObjectsApi()
        self.net_v1 = client.NetworkingV1Api()

        utils.spawn_n(self._watch_pods, admin_context)

    def _watch_pods(self, context):
        def _do_watch():
            watcher = watch.Watch()
            for event in watcher.stream(
                self.core_v1.list_pod_for_all_namespaces,
                label_selector=f"{LABELS['type']}=container"):
                pod = event["object"]
                event_type = event["type"]
                container_uuid = pod.metadata.labels[LABELS["uuid"]]
                try:
                    container = objects.Container.get_by_uuid(context, container_uuid)
                    self._sync_container(container, pod, pod_event=event_type)
                    container.save()
                    LOG.info(
                        f"Synced {container_uuid} to k8s state after {event_type} event")
                except exception.ContainerNotFound:
                    # Just skip this pod, it should be cleaned up on the periodic sync
                    LOG.info(f"Skipping update on missing container '{container_uuid}'")
                    LOG.exception("help")

        backoff, max_backoff = 0.0, 128.0
        def _get_backoff(current, maximum):
            return min(max(current * 2, 1.0), maximum)

        while True:
            try:
                if backoff:
                    time.sleep(backoff)
                _do_watch()
            except client.ApiException as exc:
                if is_exception_like(exc, code=410):
                    LOG.debug("Pod watcher has expired and will be reconnected")
                else:
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

        # Ensure all namespaces have a default network policy
        ns_list = self.core_v1.list_namespace(
            label_selector=LABELS["project_id"])
        for ns in ns_list.items:
            project_id = ns.metadata.labels[LABELS["project_id"]]
            try:
                # Create a default policy that allows pods within the same namespace
                # to communicate directly with eachother.
                self.net_v1.create_namespaced_network_policy(ns.metadata.name, {
                    "metadata": {
                        "name": "default",
                    },
                    "spec": {
                        # Only allow ingress from pods in same namespace
                        "ingress": [{
                            "from": [{
                                "namespaceSelector": {
                                    "matchLabels": {
                                        LABELS["project_id"]: project_id,
                                    },
                                }
                            }],
                        }],
                        # Allow all egress
                        "egress": [{}],
                        "policyTypes": ["Ingress", "Egress"],
                    },
                })
                LOG.info(f"Created default network policy for project {project_id}")
            except client.ApiException as exc:
                if not is_exception_like(exc, code=409):
                    raise

    def _sync_addresses(self, container, pod):
        pod_ips = set(_pod_ips(pod))
        network_id = self.neutron_network_id or UNDEFINED_NETWORK
        port_id = None
        container_ips = set()
        # Extract the current list of container addresses and associated ports.
        # We keep a single port for each container and adjust its addresses if they
        # change on the pod. This prevents disruptions to floating IP bindings.
        for addr in container.addresses.get(network_id) or []:
            container_ips.add(addr["addr"])
            # FIXME(jason): this assumes the port_id will be the same for all addresses.
            # This is currently the case, but maybe not in the future (??)
            port_id = addr["port"]

        if pod_ips == container_ips:
            return

        if self.neutron_network_id:
            if port_id:
                self.neutron.update_port(port_id, {
                    "port": {
                        "fixed_ips": [{"ip_address": ip} for ip in pod_ips],
                    }
                }, admin=True)
                LOG.info(
                    f"Updated port {port_id} IP assignments for "
                    f"{container.uuid}")
            else:
                port = self.neutron.create_port({
                    "port": {
                        "name": name_provider(container),
                        "network_id": network_id,
                        "tenant_id": pod.metadata.labels[LABELS["project_id"]],
                        "device_id": container.uuid,
                        "device_owner": "k8s:cni",
                        "fixed_ips": [{"ip_address": ip} for ip in pod_ips],
                    }
                }, admin=True)["port"]
                port_id = port["id"]
                LOG.info(f"Created port {port_id} for {container.uuid}")

        container.addresses = {
            network_id: [
                {
                    'addr': ip,
                    'version': 4,
                    'port': port_id
                } for ip in pod_ips
            ]
        }

    def create(self, context, container, image, requested_networks,
               requested_volumes, device_attachments=None):
        """Create a container."""

        def _create_deployment():
            self.apps_v1.create_namespaced_deployment(
                container.project_id,
                deployment_provider(container, image)
            )
            LOG.info("Created deployment for %s in %s", container.uuid,
                container.project_id)

        try:
            _create_deployment()
        except client.ApiException as exc:
            # The first time we create a deployment for a project there will not yet
            # be a namespace; handle this and create namespace in this case.
            if is_exception_like(exc, code=404, kind="namespaces"):
                self.core_v1.create_namespace({
                    "metadata": {
                        "name": container.project_id,
                        "labels": {
                            LABELS["project_id"]: container.project_id,
                        },
                    }
                })
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
            self.net_v1.create_namespaced_network_policy(container.project_id, {
                "metadata": {
                    "name": f"expose-{container.uuid}",
                    "labels": {
                        LABELS["uuid"]: container.uuid,
                    },
                },
                "spec": {
                    "podSelector": {
                        "matchLabels": {
                            LABELS["uuid"]: container.uuid,
                        },
                    },
                    "ingress": [
                        # Allow from all IPs
                        {
                            "ports": [
                                {
                                    "port": port_spec["port"],
                                    "protocol": port_spec["protocol"]
                                } for port_spec in container_ports_provider(container)
                            ],
                        },
                    ],
                },
            })
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
        phase_map = {
            "Failed": consts.ERROR,
            "Pending": consts.CREATING,
            "Running": consts.RUNNING,
            "Succeeded": consts.STOPPED,
        }

        # Special case, when the pod is pending but has a Unschedulable condition,
        # it means there was no node it could be scheduled on. Fail quickly in this
        # case to match behavior w/ the filter scheduler.
        if pod_status.phase == "Pending":
            unschedulable_condition = next(iter([
                c for c in (pod_status.conditions or []) if c.reason == "Unschedulable"
            ]), None)
            if unschedulable_condition:
                container.status = consts.ERROR
                container.task_state = None
                container.status_reason = unschedulable_condition.message
                container.status_detail = unschedulable_condition.reason
                return

        if pod_status.phase not in phase_map:
            LOG.error(
                "Unknown pod phase '%s', interpreting as Error", pod_status.phase)
            container.status = consts.ERROR
            container.task_state = None
        elif container.status != phase_map[pod_status.phase]:
            container.status = phase_map[pod_status.phase]
            # Also clear task state; most container status changes happen async and
            # we need to tell Zun that the transition is finished.
            container.task_state = None

        container.status_reason = pod_status.reason
        container.status_detail = pod_status.message

        container.hostname = pod.spec.hostname
        container.container_id = pod.metadata.name

        pod_container = pod.spec.containers[0]
        container.command = pod_container.command
        container.ports = [port.container_port for port in (pod_container.ports or [])]

        self._sync_addresses(container, pod)

    def commit(self, context, container, repository, tag):
        """Commit a container."""
        raise NotImplementedError("K8s does not support container snapshot currently")

    def delete(self, context, container, force):
        """Delete a container."""
        name = name_provider(container)
        self.apps_v1.delete_namespaced_deployment(name, container.project_id)
        LOG.info(f"Deleted deployment {name} in {container.project_id}")

    def list(self, context):
        """List all containers."""
        deployment_list = self.apps_v1.list_deployment_for_all_namespaces(
            label_selector=LABELS['uuid'])
        uuid_to_deployment_map = {
            deployment.metadata.labels[LABELS["uuid"]]: deployment
            for deployment in deployment_list.items
        }

        # Then pull a list of all Zun containers for the host
        local_containers = objects.Container.list_by_host(context, CONF.host)
        non_existent_containers = []

        # Skip zun containers in creating|deleting|deleted
        for container in local_containers:
            matching_deployment = uuid_to_deployment_map.get(container.uuid)

            if container.status in (consts.DELETED):
                if matching_deployment:
                    # Clean up the orphan deployment
                    self.apps_v1.delete_namespaced_deployment(
                        matching_deployment.metadata.name, container.project_id)
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
        local_containers, non_existent_containers = self.list(context)

        pod_map = {
            pod.metadata.labels[LABELS["uuid"]]: pod
            for pod in self.core_v1.list_pod_for_all_namespaces(
                label_selector=f"{LABELS['type']}=container"
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
            label_selector=label_selector_provider(container)
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
        deployment_name = name_provider(container)
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

    def execute_create(self, context, container, command, interactive):
        """Create an execute instance for running a command."""
        pod = self._pod_for_container(context, container)
        if not pod:
            raise exception.ContainerNotFound()
        # The get/post exec command expect a websocket interface; the 'stream' helper
        # library helps wrapping up such requests in a websocket and proxying/buffering
        # the response output.
        ws_client: "WSClient" = stream(
            self.core_v1.connect_get_namespaced_pod_exec,
            pod.metadata.name,
            container.project_id,
            command=shlex.split(command),
            stderr=True, stdin=False,
            stdout=True, tty=False,
            _preload_content=False,
        )

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

    def get_archive(self, context, container, path):
        """Copy resource from a container."""
        raise NotImplementedError()

    def put_archive(self, context, container, path, data):
        """Copy resource to a container."""
        raise NotImplementedError()

    def stats(self, context, container):
        """Display stats of the container."""
        raise NotImplementedError()

    def get_container_name(self, container):
        """Retrieve container name."""
        return name_provider(container)

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
            label_selector=f"{LABELS['type']}=container"
        )
        pod_statuses = defaultdict(list)
        for pod in pod_list.items:
            pod_statuses[pod.status.phase].append({
                "name": pod.metadata.name,
                "node": pod.spec.node_name,
            })

        return K8sClusterMetrics({
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

    def attach_volume(self, context, volume_mapping):
        raise NotImplementedError()

    def detach_volume(self, context, volume_mapping):
        raise NotImplementedError()

    def delete_volume(self, context, volume_mapping):
        raise NotImplementedError()

    def is_volume_available(self, context, volume_mapping):
        raise NotImplementedError()

    def is_volume_deleted(self, context, volume_mapping):
        raise NotImplementedError()

    def add_security_group(self, context, container, security_group, **kwargs):
        raise NotImplementedError()

    def remove_security_group(self, context, container, security_group, **kwargs):
        raise NotImplementedError()

    def get_available_nodes(self):
        # Get a list of all nodes?
        return [CONF.host]

    def network_detach(self, context, container, network):
        raise NotImplementedError()

    def network_attach(self, context, container, requested_network):
        raise NotImplementedError()

    def create_network(self, context, network):
        raise NotImplementedError()

    def delete_network(self, context, network):
        raise NotImplementedError()

    def inspect_network(self, network):
        raise NotImplementedError()

    def node_support_disk_quota(self):
        # TODO: might want to set this to true if we can allocate disk quotas on k8s.
        return False

    def get_host_default_base_size(self):
        return None

    def pull_image(self, context, repo, tag, image_pull_policy, image_driver_name, **kwargs):
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

    def create_capsule(self, context, capsule, **kwargs):
        raise NotImplementedError()

    def delete_capsule(self, context, capsule, **kwargs):
        raise NotImplementedError()


class K8sClusterMetrics(object):
    def __init__(self, metrics_dict):
        self._metrics = metrics_dict

    def cpus(self):
        total_cpu = 0
        used_cpu = 0.0
        for node in self._metrics["nodes"].values():
            total_cpu += int(node["capacity"]["cpu"])
            # Usage is measured in nanocores
            used_cpu += int(node["usage"]["cpu"].rstrip("n")) / 1000000000
        return total_cpu, used_cpu

    def memory(self):
        total_mem = 0
        free_mem = 0
        avail_mem = 0
        used_mem = 0
        for node in self._metrics["nodes"].values():
            node_cap = to_num_bytes(node["capacity"]["memory"])
            node_used = to_num_bytes(node["usage"]["memory"])
            node_alloc = to_num_bytes(node["allocatable"]["memory"])
            total_mem += node_cap
            free_mem += node_cap - (node_used + node_alloc)
            avail_mem += node_alloc
            used_mem += node_used
        return total_mem, free_mem, avail_mem, used_mem

    def disk(self):
        total_disk = 0
        used_disk = 0
        for node in self._metrics["nodes"].values():
            node_cap = to_num_bytes(node["capacity"]["ephemeral-storage"]) // units.Gi
            node_alloc = (
                to_num_bytes(node["allocatable"]["ephemeral-storage"]) // units.Gi)
            total_disk += node_cap
            used_disk += node_cap - node_alloc
        return total_disk, used_disk

    def running_containers(self):
        return len(self._metrics["pods"]["Running"])

    def stopped_containers(self):
        return len(self._metrics["pods"]["Succeeded"])

    def total_containers(self):
        return len(list(chain(*self._metrics["pods"].values())))
