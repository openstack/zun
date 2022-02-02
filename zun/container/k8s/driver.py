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
import time

from kubernetes import client, config, watch
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
    for dp_name in device_profiles:
        if dp_name not in resource_map:
            raise ValueError(
                "Missing mapping for device_profile '%s', ensure it has been added "
                "to device_profile_mappings.")
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

    node_selector_terms = [
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
        node_selector_terms.extend([
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
                            "requiredDuringSchedulingRequiredDuringExecution": {
                                "nodeSelectorTerms": node_selector_terms,
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


def is_exception_like(api_exc: client.ApiException, code=None, **kwargs):
    if code and api_exc.status != code:
        return False
    # Interpret keyword args as matchers/filters on the "details" part of the response
    details_matcher = kwargs
    if details_matcher:
        details = jsonutils.loads(api_exc.body).get("details", {})
        return all(details[k] == v for k, v in details_matcher.items())
    return True


def _pod_ips(pod):
    return [p.ip for p in pod.status.pod_i_ps]


class K8sDriver(driver.ContainerDriver, driver.BaseDriver):

    # There are no defined capabilities still... but this is required to exist.
    capabilities = {}

    def __init__(self):
        self.neutron = neutron.NeutronAPI(zun_context.get_admin_context())

        # Configs can be set in Configuration class directly or using helper utility
        config.load_kube_config(config_file=CONF.k8s.kubeconfig_file)
        # K8s APIs
        self.core_v1 = client.CoreV1Api()
        self.apps_v1 = client.AppsV1Api()
        self.custom = client.CustomObjectsApi()
        self.net_v1 = client.NetworkingV1Api()

    def periodic_sync(self, context):
        """Called by the compute manager periodically.

        Use this to perform cleanup in case state on K8s has diverged from desired.
        """
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
                        "name": f"default",
                    },
                    "spec": {
                        "ingress": [{
                            "from": [{
                                "namespaceSelector": {
                                    "matchLabels": {
                                        LABELS["project_id"]: project_id,
                                    },
                                }
                            }],
                        }],
                        "policyTypes": ["Ingress"],
                    },
                })
                LOG.info(f"Created default network policy for project {project_id}")
            except client.ApiException as exc:
                if not is_exception_like(exc, code=409):
                    raise

        if CONF.k8s.neutron_network:
            network = self.neutron.get_neutron_network(CONF.k8s.neutron_network)
            pod_port_map = {
                p["device_id"]: p
                for p in self.neutron.list_ports(device_owner="k8s:cni")["ports"]
            }
            pod_list = self.core_v1.list_pod_for_all_namespaces(
                label_selector=f"{LABELS['exposed']}=true")
            for pod in pod_list.items:
                container_uuid = pod.metadata.labels[LABELS["uuid"]]
                container = None
                try:
                    container = objects.Container.get_by_uuid(context, container_uuid)
                except exception.ContainerNotFound:
                    pass

                port = self._sync_neutron_port(
                    container, pod, network,
                    port=pod_port_map.get(container_uuid)
                )

                if container:
                    container.addresses = {
                        network["id"]: [
                            {
                                'addr': ip,
                                'version': 4,
                                'port': port['id'],
                                # 'subnet_id': fixed_ip['subnet_id'],
                                'preserve_on_delete': False
                            } for ip in _pod_ips(pod)
                        ]
                    }
                    container.save()

    def _sync_neutron_port(self, container, pod, network, port=None):
        if not container:
            if port:
                self.neutron.delete_port(port["id"])
                LOG.info(
                    f"Deleted dangling port {port['id']} for missing container")
            return None

        pod_ips = set(_pod_ips(pod))

        if port:
            port_ips = set(p["ip_address"] for p in port["fixed_ips"])
            if pod_ips != port_ips:
                self.neutron.update_port(port["id"], {
                    "port": {
                        "fixed_ips": [{"ip_address": ip} for ip in pod_ips],
                    }
                }, admin=True)
                LOG.info(
                    f"Updated port {port['id']} IP assignments for "
                    f"{container.uuid}")
        else:
            port = self.neutron.create_port({
                "port": {
                    "name": name_provider(container),
                    "network_id": network["id"],
                    "tenant_id": pod.metadata.labels[LABELS["project_id"]],
                    "device_id": container.uuid,
                    "device_owner": "k8s:cni",
                    "fixed_ips": [{"ip_address": ip} for ip in pod_ips],
                }
            }, admin=True)["port"]
            LOG.info(f"Created port {port['id']} for {container.uuid}")

        return port

    def create(self, context, container, image, requested_networks,
               requested_volumes, device_attachments=None):
        """Create a container."""

        def _create_deployment():
            return self.apps_v1.create_namespaced_deployment(
                container.project_id,
                deployment_provider(container, image)
            )

        try:
            _create_deployment()
        except client.ApiException as exc:
            if is_exception_like(exc, code=404, kind="namespaces"):
                LOG.debug("Auto-creating namespace %s", container.project_id)
                self.core_v1.create_namespace({
                    "metadata": {
                        "name": container.project_id,
                        "labels": {
                            LABELS["project_id"]: container.project_id,
                        },
                    }
                })
                _create_deployment()
            else:
                raise

        pod = None
        pod_watcher = watch.Watch()
        for event in pod_watcher.stream(
            self.core_v1.list_namespaced_pod,
            container.project_id,
            label_selector=label_selector_provider(container),
        ):
            # Should be only one
            pod = event["object"]
            self._populate_container(container, pod)
            pod_watcher.stop()
            break

        # K8s containers are always auto-removed
        container.auto_remove = True
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

        return container

    def _populate_container(self, container, pod):
        if not pod:
            container.status = consts.STOPPED
            return

        pod_status = pod.status
        phase_map = {
            "Failed": consts.ERROR,
            "Pending": consts.CREATING,
            "Running": consts.RUNNING,
            "Succeeded": consts.STOPPED,
        }
        if pod_status.phase in phase_map:
            container.status = phase_map[pod_status.phase]
        else:
            LOG.error(
                "Unknown pod phase '%s', interpreting as Error", pod_status.phase)
            container.status == consts.ERROR
        container.status_reason = pod_status.reason
        container.status_detail = pod_status.message

        container.hostname = pod.spec.hostname
        container.container_id = pod.metadata.name

        pod_container = pod.spec.containers[0]
        container.command = pod_container.command
        container.ports = [port.container_port for port in (pod_container.ports or [])]

    def commit(self, context, container, repository, tag):
        """Commit a container."""
        raise NotImplementedError("K8s does not support container snapshot currently")

    def delete(self, context, container, force):
        """Delete a container."""
        self.apps_v1.delete_namespaced_deployment(
            name_provider(container), container.project_id
        )

    def list(self, context):
        """List all containers."""
        deployment_list = self.apps_v1.list_deployment_for_all_namespaces(
            label_selector=LABELS['uuid'])
        uuid_to_deployment_map = {
            deployment.metadata.labels[LABELS["uuid"]]: deployment
            for deployment in deployment_list.items
        }

        pod_list = self.core_v1.list_pod_for_all_namespaces(
            label_selector=f"{LABELS['type']}=container")
        uuid_to_pod_map = {
            pod.metadata.labels[LABELS["uuid"]]: pod
            for pod in pod_list.items
        }

        # Then pull a list of all Zun containers for the host
        local_containers = objects.Container.list_by_host(context, CONF.host)
        non_existent_containers = []

        # Skip zun containers in creating|deleting|deleted
        for container in local_containers:
            if container.status in (consts.DELETED):
                # Nothing to do with already deleted containers.
                continue

            matching_deployment = uuid_to_deployment_map.get(container.uuid)

            # If container_id is not set the container did not finish creating.
            if not container.container_id or not matching_deployment:
                non_existent_containers.append(container)
                continue

            # N.B.: it's possible the deployment exists but there is no pod; this is the
            # case if the container was 'stopped' (setting replicas to 0).
            matching_pod = uuid_to_pod_map.get(container.uuid)

            # FIXME: this is a very strong side-effect, to update resources when
            # listing them. But it's how the docker driver does it, presumably b/c
            # this function is called from the UI or periodic tasks and it's a simple
            # way to ensure the container state is refreshed periodically.
            self._populate_container(container, matching_pod)

        return local_containers, non_existent_containers

    def _get_local_containers(self, context, uuids):
        host_containers = objects.Container.list_by_host(context, CONF.host)
        uuids = list(set(uuids) | set([c.uuid for c in host_containers]))
        containers = objects.Container.list(context,
                                            filters={'uuid': uuids})
        return containers

    # This function is almost exactly the same as the Docker driver implementation
    # but uses UUIDs instead of container_ids (and syncs container_ids, which can
    # change in K8s when a pod is rescheduled.)
    def update_containers_states(self, context, containers, manager):
        local_containers, non_existent_containers = self.list(context)
        if not local_containers:
            return

        uuid_to_local_container_map = {container.uuid: container
                                     for container in local_containers
                                     if container.container_id}
        uuid_to_container_map = {container.uuid: container
                               for container in containers
                               if container.container_id}

        for cid in (uuid_to_container_map.keys() &
                    uuid_to_local_container_map.keys()):
            container = uuid_to_container_map[cid]
            local_container = uuid_to_local_container_map[cid]

            def _sync_attr(attr, new_val):
                old_val = getattr(container, attr)
                if old_val != new_val:
                    setattr(container, attr, new_val)
                    container.save(context)
                    LOG.info('Container %s %s changed from %s to %s',
                             container.uuid, attr, old_val, new_val)

            _sync_attr("status", local_container.status)
            _sync_attr("host", CONF.host)
            _sync_attr("container_id", local_container.container_id)

        for container in non_existent_containers:
            if container.host == CONF.host:
                container.status = consts.DELETED
                container.save(context)
            else:
                # self.heal_with_rebuilding_container(context, container,
                #                                     manager)
                pass

    def show(self, context, container):
        """Show the details of a container."""
        # Not sure how this can happen, another thing stolen from Docker driver.
        if container.container_id is None:
            return container

        pod = self._pod_for_container(context, container)
        if pod:
            self._populate_container(container, pod)

        return container

    def _pod_for_container(self, context, container):
        pod_list = self.core_v1.list_namespaced_pod(
            container.project_id,
            label_selector=label_selector_provider(container)
        )
        pod = pod_list.items[0] if pod_list.items else None
        return pod

    def reboot(self, context, container):
        """Reboot a container."""
        self.stop(context, container, None)
        self.start(context, container)

    def stop(self, context, container, timeout):
        """Stop a container."""
        self._update_replicas(container, 0, timeout=int(timeout))

    def start(self, context, container):
        """Start a container."""
        self._update_replicas(container, 1)

    def _update_replicas(self, container, replicas, timeout=5):
        deployment_name = name_provider(container)
        self.apps_v1.patch_namespaced_deployment(
            deployment_name,
            container.project_id, {
                "spec": {
                    "replicas": replicas,
                }
            })

        start_time = time.time()
        deployment_watcher = watch.Watch()
        for event in deployment_watcher.stream(
            self.apps_v1.list_namespaced_deployment,
            container.project_id,
            field_selector=f"metadata.name={deployment_name}"
        ):
            deployment = event["object"]
            if deployment.status.replicas == replicas:
                container.status = consts.STOPPED if replicas == 0 else consts.RUNNING
                container.save()
                deployment_watcher.stop()
                break
            elif (time.time() - start_time) > timeout:
                LOG.debug("Exceeded timeout waiting for container stop")
                break

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
        return self.core_v1.read_namespaced_pod_log(
            name_provider(container),
            container.project_id,
            tail_lines=(tail if tail and tail != "all" else None),
            since_seconds=since
        )

    def execute_create(self, context, container, command, **kwargs):
        """Create an execute instance for running a command."""
        output = self.core_v1.connect_post_namespaced_pod_exec(
            name_provider(container),
            container.project_id,
            command=command
        )
        raise {"output": output, "exit_code": 0}

    def execute_run(self, exec_id):
        """Run the command specified by an execute instance."""
        # For k8s driver, exec_id is the exec response handle we returned in execute_create,
        # which already has all the info.
        return exec_id["output"], exec_id["exit_code"]

    def execute_resize(self, exec_id, height, width):
        """Resizes the tty session used by the exec."""
        raise NotImplementedError()

    def kill(self, context, container, signal):
        """Kill a container with specified signal."""
        raise NotImplementedError()

    def get_websocket_url(self, context, container):
        """Get websocket url of a container."""
        raise NotImplementedError()

    def resize(self, context, container, height, weight):
        """Resize tty of a container."""
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
        raise name_provider(container)

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
