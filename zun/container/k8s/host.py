import itertools

from oslo_utils import units


def to_num_bytes(size_spec: str):
    for unit in ["Gi", "G", "Mi", "M", "Ki", "K"]:
        if size_spec.endswith(unit):
            return int(size_spec.rstrip(unit)) * getattr(units, unit)
    return int(size_spec)


def to_cpu_units(cpu_usage_spec: str):
    scale_map = {"u": 1 / units.T, "n": 1 / units.G, "m": 1 / units.M}
    for unit, scale in scale_map.items():
        if cpu_usage_spec.endswith(unit):
            return int(cpu_usage_spec.rstrip(unit)) * scale
    return int(cpu_usage_spec)


class K8sClusterMetrics(object):
    def __init__(self, metrics_dict):
        self._metrics = metrics_dict

    def cpus(self):
        total_cpu = 0
        used_cpu = 0.0
        for node in self._metrics["nodes"].values():
            total_cpu += int(node["capacity"]["cpu"])
            # Usage is measured in nanocores or microcores
            used_cpu += to_cpu_units(node["usage"]["cpu"])
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
        return len(list(itertools.chain(*self._metrics["pods"].values())))
