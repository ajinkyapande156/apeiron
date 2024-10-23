"""
Copyright (c) 2023 Nutanix Inc. All rights reserved.

Author: rishabh.kumar@nutanix.com
"""
#pylint:disable=invalid-name
import math
from framework.lib.nulog import INFO

from framework.interfaces.rest.prism_client import PrismClient
from framework.interfaces.rest.prism_client import PrismRestVersion

class ClusterOps:
  """
  Class to get cluster related info
  """
  def __init__(self, cluster):
    """
    Instantiate class
    Args:
      cluster(object): NuTest cluster object
    """
    self.cluster = cluster
    self.prism_client = PrismClient(cluster=self.cluster,
                                    version=PrismRestVersion.V2_0)
    self.prism_client_v1 = PrismClient(cluster=self.cluster,
                                       version=PrismRestVersion.V1)
    self.CLUSTER_STATS_URL = "/cluster/stats"
    self.AVL_VCPU_MULTIPLIER = 12

  def get_mem_usage(self):
    """
    Get cluster memory usage percent
    Returns:
      mem_usage(int): Cluster memory usage
    """
    params = {
      "metrics": "aggregate_hypervisor_memory_usage_ppm"
    }
    cluster_stats = self.prism_client_v1.get(url=self.CLUSTER_STATS_URL,
                                             params=params)
    mem_usage_ppm = cluster_stats["statsSpecificResponses"][0]["values"][0]
    mem_usage = mem_usage_ppm / 10000
    INFO("Hypervisor memory usage: %s%%" % mem_usage)

    hosts_info = self.get_hosts_info()
    total_memory_bytes = 0
    for host_info in hosts_info:
      total_memory_bytes += int(host_info["memory_capacity_in_bytes"])

    params = {
      "metrics": "ha_memory_reserved_bytes"
    }
    ha_mem_data = self.prism_client_v1.get(url=self.CLUSTER_STATS_URL,
                                           params=params)
    ha_reserved_bytes = ha_mem_data["statsSpecificResponses"][0]["values"][0]
    ha_mem_perc = (ha_reserved_bytes * 100) / total_memory_bytes
    INFO("HA Reserved memory percentage: %s%%" % ha_mem_perc)
    mem_usage += ha_mem_perc

    mem_usage = math.ceil(mem_usage)
    INFO("Cluster memory usage: %s%%" % mem_usage)
    return mem_usage

  def get_total_memory_in_mb(self):
    """
    Get total memory on cluster
    Returns:
      total_memory(int): Cluster memory in MB
    """
    hosts_info = self.get_hosts_info()
    total_memory = 0
    for host_info in hosts_info:
      host_mem = host_info["memory_capacity_in_bytes"] / (1024 * 1024)
      total_memory += math.floor(host_mem)
    INFO("Cluster memory: %s MB" % total_memory)
    return total_memory

  def get_hosts_free_mem_info(self):
    """
    Get hosts free memory info
    Returns:
      hosts_free_mem_info(dict): Hosts free memory info
    """
    hosts_info = self.get_hosts_info()
    hosts_free_mem_info = {
      "max": 0,
      "min": 10000000000,
      "values": []
    }
    for host_info in hosts_info:
      total_mem_mb = int(host_info["memory_capacity_in_bytes"]/(1024 * 1024))
      mem_usage_perc = \
        int(int(host_info["stats"]["hypervisor_memory_usage_ppm"])/10000)
      mem_free_mb = int(((100 - mem_usage_perc) * total_mem_mb)/100)
      hosts_free_mem_info["values"].append(mem_free_mb)
      hosts_free_mem_info["max"] = max(hosts_free_mem_info["max"], mem_free_mb)
      hosts_free_mem_info["min"] = min(hosts_free_mem_info["min"], mem_free_mb)

    INFO("Hosts free mem info: %s" % hosts_free_mem_info)
    return hosts_free_mem_info

  def get_cpu_usage(self):
    """
    Get cluster cpu usage percent
    Returns:
      cpu_usage(int): Cpu usage of the cluster
    """
    params = {
      "metrics": "hypervisor_cpu_usage_ppm"
    }
    cluster_stats = self.prism_client_v1.get(url=self.CLUSTER_STATS_URL,
                                             params=params)
    cpu_usage_ppm = cluster_stats["statsSpecificResponses"][0]["values"][0]
    cpu_usage = cpu_usage_ppm/10000
    cpu_usage = math.ceil(cpu_usage)
    INFO("Cluster CPU usage: %s%%" % cpu_usage)
    return cpu_usage

  def get_hosts_vcpu_info(self):
    """
    Get the hosts vcpu info
    Returns:
      hosts_vcpu_info(dict): Hosts vCPU info
    """
    hosts_vcpu_info = {
      "max_vcpu": 0,
      "min_vcpu": 0,
      "num_vcpus": [],
      "total_available_vcpus": 0,
    }
    hosts_info = self.get_hosts_info()
    for host_info in hosts_info:
      hosts_vcpu_info["num_vcpus"].append(host_info["num_cpu_threads"])
      hosts_vcpu_info["total_available_vcpus"] += \
        (host_info["num_cpu_threads"] * self.AVL_VCPU_MULTIPLIER)

    # Max vCPU a VM can have on a host, if we want to perform migrations
    # then min_vcpus is feasible, otherwise max_vcpus.
    hosts_vcpu_info["max_vcpu"] = max(hosts_vcpu_info["num_vcpus"])
    hosts_vcpu_info["min_vcpu"] = min(hosts_vcpu_info["num_vcpus"])

    INFO("Hosts vcpu info: %s" % hosts_vcpu_info)
    return hosts_vcpu_info

  def get_hosts_info(self):
    """
    Get hosts info
    Returns:
      hosts_info(dict): Hosts info
    """
    hosts_info = self.prism_client.get(url="/hosts")
    return hosts_info["entities"]
