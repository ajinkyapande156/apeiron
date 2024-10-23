"""
Copyright (c) 2024 Nutanix Inc. All rights reserved.

Author: rishabh.kumar@nutanix.com
"""
#pylint:disable=too-many-locals, no-self-use, broad-except, too-many-statements
#pylint:disable=protected-access
import copy
import time

from framework.lib.nulog import INFO, STEP, ERROR
from framework.exceptions.entity_error import NuTestError
from framework.lib.parallel_executor import ParallelExecutor
from libs.framework import mjolnir_entities as entities
from workflows.acropolis.ahv.ahv_uvm_resource import AHVUVMResource
from workflows.acropolis.ahv.acro_image_utility import AcroImageUtil
from libs.workflows.generic.wf_helpers \
  import WorkflowsHelper
from libs.ahv.workflows.gos_qual.configs \
  import constants
import workflows.acropolis.mjolnir.workflows.generic.vm.lib.constants \
  as vm_constants
from libs.workflows.generic.cluster.cluster_ops \
  import ClusterOps


class LargeHostWorkflows:
  """
  LargeHostWorkflows class
  """
  def __init__(self, cluster, **kwargs):
    """
    Initialize object
    Args:
      cluster(object): Nutest cluster object
    """
    self.cluster = cluster
    self.wf_helper = WorkflowsHelper(cluster=self.cluster, **kwargs)
    self.cluster_ops = ClusterOps(cluster=self.cluster)

  def step(self, **kwargs):
    """
    This method will invoke individual steps
    Args:
    Returns:
    Raises:
    """
    step_name = kwargs.pop("step_name").strip()
    step_name_display = step_name
    if kwargs.get("step_name_suffix"):
      step_name_suffix = kwargs.pop("step_name_suffix")
      step_name_display = f"{step_name}_{step_name_suffix}"
    STEP(f"Performing STEP: {step_name_display}")
    getattr(self, step_name)(**kwargs)

  def vm_create_parallel(self, **kwargs):
    """
    Create VMs on the cluster parallely
    Args:
    Returns:
    Exceptions:
    """
    pool_size = kwargs.pop("pool_size", 10)
    skip_boot_disk = kwargs.pop("skip_boot_disk", False)
    vm_create_executor = ParallelExecutor(pool_size=pool_size)
    add_boot_disk_executor = ParallelExecutor(pool_size=pool_size)
    add_nic_executor = ParallelExecutor(pool_size=pool_size)
    power_on_executor = ParallelExecutor(pool_size=pool_size)

    cluster_cpu_load = self.cluster_ops.get_cpu_usage()
    cluster_mem_load = self.cluster_ops.get_mem_usage()

    self.max_cpu_load = kwargs.pop("max_cpu_load", 60)
    self.max_mem_load = kwargs.pop("max_mem_load", 70)
    self.num_nodes = self.cluster._metadata["nodes_cache"]["nodes_count"]
    self.max_supported_vms = vm_constants.MAX_VM_PER_HOST * self.num_nodes

    num_vms = self._calc_num_vms(vm_config=kwargs.get("vm_configs"),
                                 max_mem_load=self.max_mem_load,
                                 user_max_vms=kwargs.pop(
                                   "num_vms", self.max_supported_vms)
                                )

    self.vm_count = 0
    num_vm_configs = len(kwargs.get("vm_configs"))
    vm_count_per_config = [0 for _ in range(num_vm_configs)]

    INFO("\nUpload all the images on the cluster\n")
    self._upload_images(vm_configs=kwargs.get("vm_configs", []))

    self._get_cluster_vm_stats()
    num_iteration = 0
    batch_num = 0
    while (cluster_cpu_load < self.max_cpu_load and
           cluster_mem_load < self.max_mem_load
           and self.vm_count < num_vms):
      num_iteration += 1
      vm_config_index = self.vm_count % num_vm_configs
      vm_config_count = vm_count_per_config[vm_config_index]

      params = copy.deepcopy(kwargs["vm_configs"][vm_config_index])
      vm_name = "%s_%s" % (params.get("name"), vm_config_count)
      vm_count_per_config[vm_config_index] = vm_config_count + 1

      params.update({"name": vm_name})
      vm_create_executor.add_task(
        target=getattr(self.wf_helper, "create_vm"), kwargs=params,
        thread_name=vm_name
      )

      if not skip_boot_disk:
        boot_disk_param = copy.deepcopy(
          kwargs["vm_configs"][vm_config_index].get("boot_disk_param", {})
        )
        boot_disk_param.update({"vm_name": params.get("name")})
        boot_disk_thread_name = "%s_add_boot_disk" % params.get("name")
        add_boot_disk_executor.add_task(
          target=getattr(self.wf_helper, "add_boot_disk"),
          kwargs=boot_disk_param, thread_name=boot_disk_thread_name
        )
        del boot_disk_param

      add_nic_param = {"vm_name": params.get("name")}
      add_nic_thread_name = "%s_add_nic" % params.get("name")
      add_nic_executor.add_task(
        target=getattr(self.wf_helper, "add_nic"), kwargs=add_nic_param,
        thread_name=add_nic_thread_name
      )

      power_on_param = copy.deepcopy(
        kwargs["vm_configs"][vm_config_index].get("power_on_param", {})
      )
      power_on_param.update({"vm_name": params.get("name")})
      power_on_param.update({
        "verify_vm_boot": kwargs.get("verify_vm_boot", True),
        "wait_for_ip": kwargs.get("wait_for_ip", True)
      })
      power_on_thread_name = "%s_power_on" % params.get("name")
      power_on_executor.add_task(
        target=getattr(self.wf_helper, "power_on"), kwargs=power_on_param,
        thread_name=power_on_thread_name
      )

      if num_iteration % pool_size == 0 or num_iteration == num_vms:
        # Create VM, add boot disk, add nic, power on.
        try:
          batch_num += 1
          STEP("Starting batch: %s for VM create and power on" % batch_num)
          vm_create_executor.run()
          add_boot_disk_executor.run()
          add_nic_executor.run()
          power_on_executor.run()
        except Exception as ex:
          ERROR(ex)

        # Re-initialize the parallel executors
        vm_create_executor = ParallelExecutor(pool_size=pool_size)
        add_boot_disk_executor = ParallelExecutor(pool_size=pool_size)
        add_nic_executor = ParallelExecutor(pool_size=pool_size)
        power_on_executor = ParallelExecutor(pool_size=pool_size)

        cluster_cpu_load = self.cluster_ops.get_cpu_usage()
        cluster_mem_load = self.cluster_ops.get_mem_usage()

        if (cluster_cpu_load >= self.max_cpu_load or
            cluster_mem_load >= self.max_mem_load):
          sleep_time = 180
          INFO("Wait for %ss and check CPU and mem load again" % sleep_time)
          # When performing parallel operations, the cpu and memory load
          # shoots up and takes some time to stabilize, so adding some
          # buffer to fetch the cpu and mem usage stats on cluster
          time.sleep(sleep_time)
          cluster_cpu_load = self.cluster_ops.get_cpu_usage()
          cluster_mem_load = self.cluster_ops.get_mem_usage()

      self.vm_count += 1
      del params
      del add_nic_param
      del power_on_param

    self._get_cluster_vm_stats()

  def start_vm_workloads(self, **kwargs):
    """
    Start workloads on the VMs
    """
    vm_uuid_list = constants.VM_CACHE["vm_list"]
    vm = entities.ENTITIES.get("rest_vm")(cluster=self.cluster,
                                          interface_type="REST")
    vm_list = vm.list(cluster=self.cluster, json=True)
    vm_name_list = []
    for vm_info in vm_list:
      if vm_info["uuid"] in vm_uuid_list:
        vm_name_list.append(vm_info["name"])

    # Wait for some time before starting workloads, so that CPU utilization
    # value stabilizes a bit.
    time.sleep(300)
    cluster_cpu_load = self.cluster_ops.get_cpu_usage()
    total_vms = len(vm_uuid_list)
    num_vms = 0

    while num_vms < total_vms and cluster_cpu_load < self.max_cpu_load:
      cpu_load_diff = self.max_cpu_load - cluster_cpu_load
      pool_size = 1
      if cpu_load_diff >= 30:
        pool_size = min(20, max(1, total_vms//20))
      elif cpu_load_diff >= 20:
        pool_size = min(10, max(1, total_vms//30))
      elif cpu_load_diff >= 10:
        pool_size = min(5, max(1, total_vms//40))
      else:
        pool_size = 1

      INFO("Pool size selected: %s" % pool_size)
      workloads_executor = ParallelExecutor(pool_size=pool_size)
      for vm_index in range(num_vms, num_vms + pool_size):
        if vm_index >= total_vms:
          break
        params = {
          "vm_name": vm_name_list[vm_index],
          "workload_types": kwargs.get("workload_types", ["io", "mem"])
        }
        thread_name = "%s_start_workloads" % params["vm_name"]
        workloads_executor.add_task(
          target=getattr(self.wf_helper, "start_workloads"), kwargs=params,
          thread_name=thread_name
        )
        num_vms += pool_size
      workloads_executor.run()

      if pool_size >= 5:
        time.sleep(60)
      cluster_cpu_load = self.cluster_ops.get_cpu_usage()

  def bulk_ops_all_vms(self, **kwargs):
    """
    Perform parallel operations on all the VMs
    """
    self.wf_helper.bulk_ops(**kwargs)

  def bulk_ops_random_vms(self, **kwargs):
    """
    Perform bulk ops on some random VMs
    """
    if kwargs.get("num_vm_percent"):
      num_random_vms = int((kwargs.pop("num_vm_percent") * self.vm_count)/100)
      kwargs.update({"num_random_vms": num_random_vms})
    self.wf_helper.bulk_ops(**kwargs)

  def _upload_images(self, vm_configs):
    """
    Upload all the images on the cluster
    Args:
      vm_configs(list): List of VM configs
    """
    images = {}
    for vm_config in vm_configs:
      guest_os = vm_config.get("guest_os", "")
      if len(guest_os) > 0:
        disk_image_type = vm_config.get("boot_disk_param", {}).get(
          "disk_image_type", "disk_image"
        )
        if guest_os in images.keys():
          if disk_image_type not in images[guest_os]:
            images[guest_os].append(disk_image_type)
        else:
          images.update({guest_os: [disk_image_type]})

    executor = ParallelExecutor(pool_size=8)
    ahv_uvm_resource = AHVUVMResource(self.cluster)
    for guest_os, disk_image_types in images.items():
      for disk_image_type in disk_image_types:
        image_name, image_url = ahv_uvm_resource.get_disk_image(
          guest_os=guest_os, disk_image_type=disk_image_type
        )
        params = {
          "image_name": image_name,
          "image_url": image_url
        }
        thread_name = "Image_upload_%s" % image_name
        executor.add_task(target=self._upload_image, kwargs=params,
                          thread_name=thread_name)

    results = executor.run()
    self._check_thread_results(results=results, operation="Image Upload")

  def _upload_image(self, image_name, image_url):
    """
    Upload an image on the cluster
    Args:
      image_name(string): Image name
      image_url(string): Image url
    """
    img_util = AcroImageUtil(self.cluster)
    img_util.upload_image(image_name, image_url, 'DISK_IMAGE')

  def _calc_num_vms(self, vm_config, max_mem_load, user_max_vms):
    """
    Calculate the number of VMs that can be created on the cluster
    Args:
      vm_config(list): List of VM config dict
      max_mem_load(int): Max cluster mem percentage
      user_max_vms(int): Provided in test args
    Returns:
      num_vms(int): Number of VMs
    """
    cluster_mem_mb = self.cluster_ops.get_total_memory_in_mb()
    cluster_mem_load = self.cluster_ops.get_mem_usage()

    vm_vcpus = vm_config[0]["vcpus"] * vm_config[0]["cores_per_vcpu"]
    vm_mem_mb = vm_config[0]["memory"]

    avl_host_mem = max(0, max_mem_load-cluster_mem_load) * cluster_mem_mb / 100

    num_vms_mem_limit = int(avl_host_mem/vm_mem_mb)
    hosts_vcpu_info = self.cluster_ops.get_hosts_vcpu_info()
    num_vms_vcpu_limit = int(hosts_vcpu_info["total_available_vcpus"]/vm_vcpus)

    INFO("Number of VMs possible as per free memory: %s" % num_vms_mem_limit)
    INFO("Number of VMs possible as per free cpus: %s" % num_vms_vcpu_limit)
    INFO("Number of VMs possible as per test config: %s" % user_max_vms)

    num_vms = min(user_max_vms, min(num_vms_mem_limit, num_vms_vcpu_limit))
    INFO("Max possible VMs: %s" % num_vms)
    return num_vms

  def _check_thread_results(self, results, operation=""):
    """
    Check the results of the threads
    Args:
      results(list): List of threads and their results
      operation(string): Operation name
    Raises:
      NuTestError(Exception): If any of the threads failed with an exception
    """
    failure_count = 0
    total_count = 0
    for result in results:
      if 'exception' in result:
        failure_count += 1
      total_count += 1

    if failure_count == 0:
      INFO("Operation: %s completed with no failures" % operation)
    else:
      raise NuTestError("%s/%s failures in operation: %s"
                        % (failure_count, total_count, operation))

  def _get_cluster_vm_stats(self):
    """
    Display the number of powered on VM's, their total memory and
    cluster cpu and memory usage
    """
    # Get the total powered on VMs and their memory(MB)
    power_on_vms_memory_mb = 0
    power_on_vms = 0

    rest_vm_obj = entities.ENTITIES.get("rest_vm")(
      cluster=self.cluster, interface_type="REST"
    )
    vm_list = rest_vm_obj.list(self.cluster, json=True)
    for vm in vm_list:
      if vm["power_state"] == "on":
        power_on_vms += 1
        power_on_vms_memory_mb += vm["memory_mb"]

    cluster_vm_stats = {
      "cluster_cpu_usage": self.cluster_ops.get_cpu_usage(),
      "cluster_mem_usage": self.cluster_ops.get_mem_usage(),
      "power_on_vms_memory_mb": power_on_vms_memory_mb,
      "power_on_vms": power_on_vms
    }
    STEP(cluster_vm_stats)
