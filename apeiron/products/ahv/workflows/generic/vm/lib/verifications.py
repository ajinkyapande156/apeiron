"""
VM Verifications

Copyright (c) 2024 Nutanix Inc. All rights reserved.
Author: rishabh.kumar@nutanix.com
"""
#pylint: disable=unused-argument, no-else-raise
import math

from framework.lib.nulog import INFO
from libs.ahv.framework.exceptions.errors \
  import EntityNotFoundError, VMVerificationError
from libs.framework import mjolnir_entities as entities
import workflows.acropolis.ahv.acro_host_helper as AcroHostHelper

class VMVerifications:
  """
  VM Verifications class
  """
  def __init__(self, cluster, guest, vm_name, **kwargs):
    """
    Instantiate
    Args:
      cluster(object): NuTest Cluster object
      guest(object): GOS object
      vm_name(string): VM name
    Raises:
      EntityNotFoundError(Exception): If VM is not found on the cluster
    """
    self.cluster = cluster
    self.guest = guest
    vm_list = entities.ENTITIES.get("rest_vm")(
      cluster=self.cluster, interface_type="REST"
    ).list(cluster=self.cluster)
    self.vm = None
    for vm in vm_list:
      if vm.name == vm_name:
        self.vm = vm
        break
    if self.vm is None:
      raise EntityNotFoundError(f"VM: {vm_name} not found on cluster")

  def verify_vcpus(self, **kwargs):
    """
    Verify the guest has same number of vCPUs as present in VM spec
    """
    INFO(f"Verify vCPUs on VM: {self.vm.name}")
    vm_config = self.vm.get()
    vm_spec_vcpus = vm_config["num_vcpus"] * vm_config["num_cores_per_vcpu"]
    guest_vcpus = self.guest.get_guest_cpu().strip()
    assert int(vm_spec_vcpus) == int(guest_vcpus), \
      f"VM vCPUS: {vm_spec_vcpus} != Guest vCPUs: {guest_vcpus}"

  def verify_mem(self, **kwargs):
    """
    Verify the memory present in guest is same as that in VM spec
    """
    INFO(f"Verify memory on VM: {self.vm.name}")
    vm_config = self.vm.get()
    vm_mem_gb = math.ceil(float(vm_config["memory_mb"]) / float(1024))
    guest_mem_mb = self.guest.get_guest_memory().strip()
    guest_mem_gb = math.ceil(float(guest_mem_mb) / float(1024))

    permissible_error_perc = kwargs.get("permissible_error", 5)
    guest_mem_diff_perc = (abs(vm_mem_gb-guest_mem_gb) * 100) / vm_mem_gb
    assert int(guest_mem_diff_perc) <= int(permissible_error_perc), \
      ("VM Memory: %sG, Guest Memory: %sG. Difference: %s%% is more than "\
      "permissible differnce: %s%%" % (vm_mem_gb, guest_mem_gb, \
      guest_mem_diff_perc, permissible_error_perc))

  def verify_vm_host(self, **kwargs):
    """
    Verify if the VM is powered on the expected host
    Raises:
      VMVerificationError(Exception): On VM verification failure
    Returns:
    """
    vm_info = self.vm.get()
    if vm_info['power_state'] != "on":
      raise VMVerificationError(f"VM: {self.vm.name} is expected to be in "
                                f"power on state for this check, but VM power "
                                f"state: {vm_info['power_state']}")

    if kwargs.get("node_type"):
      node_type = kwargs.get("node_type")
      # Get the host_uuid on which VM is powered on
      vm_host_uuid = vm_info['host_uuid']
      INFO(f"VM is powered on host: {vm_host_uuid}")
      if node_type == "co":
        co_hosts = AcroHostHelper.get_co_hosts(self.cluster)
        for co_host in co_hosts:
          if co_host.uuid == vm_host_uuid:
            INFO(f"VM is powered on CO Host(UUID: {co_host.uuid}) as expected")
            return
        raise VMVerificationError(f"VM is on host(UUID:{vm_host_uuid}) which "
                                  f"is not CO node")
      elif node_type == "hc":
        hc_hosts = AcroHostHelper.get_hc_hosts(self.cluster)
        for hc_host in hc_hosts:
          if hc_host.uuid == vm_host_uuid:
            INFO(f"VM is powered on HC Host(UUID: {hc_host.uuid}) as expected")
            return
        raise VMVerificationError(f"VM is on host(UUID:{vm_host_uuid}) which "
                                  f"is not HC node")
