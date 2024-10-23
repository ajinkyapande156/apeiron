"""
Copyright (c) 2024 Nutanix Inc. All rights reserved.

Author: rishabh.kumar@nutanix.com
"""
import time

from framework.lib.nulog import INFO, STEP
from libs.workflows.generic.wf_helpers \
  import WorkflowsHelper
from libs.workflows.generic.cluster.cluster_ops \
  import ClusterOps
import workflows.acropolis.mjolnir.workflows.generic.vm.lib.constants \
  as vm_constants
from libs.ahv.framework.exceptions.errors \
  import UnsupportedParamError

class LargeVMWorkflows:
  """
  LargeVMWorkflows class
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
    if kwargs.get("steps"):
      # Directly call the Workflows helper method
      steps = kwargs.pop("steps", "")
      steps = [step.strip() for step in steps.split(",")]
      for step in steps:
        STEP(f"Performing STEP: {step}")
        getattr(self.wf_helper, step)(**kwargs)
    else:
      step_name = kwargs.pop("step_name").strip()
      step_name_display = step_name
      if kwargs.get("step_name_suffix"):
        step_name_suffix = kwargs.pop("step_name_suffix")
        step_name_display = f"{step_name}_{step_name_suffix}"
      STEP(f"Performing STEP: {step_name_display}")
      getattr(self, step_name)(**kwargs)


  def create_vm_dynamic(self, **kwargs):
    """
    Create VM with dynamic params based on cluster etc.
    Args:
    Returns:
    Exceptions:
    """
    boot_type = kwargs.get("boot_type", "legacy")
    machine_type = "pc"
    if boot_type == "secure":
      machine_type = "q35"

    if kwargs.get("dynamic_cpu"):
      dynamic_cpu = kwargs.pop("dynamic_cpu")
      hosts_vcpu_info = self.cluster_ops.get_hosts_vcpu_info()
      if dynamic_cpu == "max":
        num_vcpus = min(hosts_vcpu_info["max_vcpu"],
                        vm_constants.MAX_VCPUS[machine_type])
      elif dynamic_cpu == "max_migrate":
        # Pick the second largest num_vcpus value
        hosts_vcpus_nums = hosts_vcpu_info["num_vcpus"]
        hosts_vcpus_nums.sort(reverse=True)
        num_vcpus = min(hosts_vcpus_nums[1],
                        vm_constants.MAX_VCPUS[machine_type])
      elif dynamic_cpu == "negative_case":
        # 1 vCPU more than max supported
        num_vcpus = vm_constants.MAX_VCPUS[machine_type] + 1
      else:
        raise UnsupportedParamError("%s: dynamic_cpu" % dynamic_cpu)

      kwargs.update({"vcpus": int(num_vcpus/kwargs.get("cores_per_vcpu", 1))})
      INFO("Params -> %s vcpus, %s cores_per_vcpu" \
           % (kwargs.get("vcpus"), kwargs.get("cores_per_vcpu")))

    if kwargs.get("dynamic_mem"):
      dynamic_mem = kwargs.pop("dynamic_mem")
      hosts_free_mem_info = self.cluster_ops.get_hosts_free_mem_info()
      if dynamic_mem == "max":
        mem_mb = min(int(0.9 * hosts_free_mem_info["max"]),
                     vm_constants.MAX_MEM_MB)
      elif dynamic_mem == "max_migrate":
        # Pick the second largest mem value
        host_mem_values = hosts_free_mem_info["values"]
        host_mem_values.sort(reverse=True)
        mem_mb = min(int(0.75 * host_mem_values[1]),
                     vm_constants.MAX_MEM_MB)
      elif dynamic_mem == "negative_case":
        mem_mb = vm_constants.MAX_MEM_MB + 1024 # 1G more than max supported
      else:
        raise UnsupportedParamError("%s: dynamic_mem" % dynamic_mem)

      kwargs.update({"memory": mem_mb})
      INFO("Params -> Memory(MB): %s" % kwargs.get("memory"))

    self.vm = self.wf_helper.create_vm(**kwargs)

  def start_vm_workloads(self, **kwargs):
    """
    Start Workloads on the VM
    """
    vm_info = self.vm.get()
    if kwargs.get("memory"):
      if kwargs["memory"].get("mem_to_dirty_percent"):
        mem_to_dirty_percent = kwargs["memory"].pop("mem_to_dirty_percent")
        mem_to_dirty = int((mem_to_dirty_percent * vm_info["memory_mb"])/100)
        kwargs["memory"].update({"mem_to_dirty": mem_to_dirty})
    self.wf_helper.start_workloads(**kwargs)
    time.sleep(kwargs.pop("sleep_time", 180))
