"""
ACLI VM

Copyright (c) 2023 Nutanix Inc. All rights reserved.
Author: rishabh.kumar@nutanix.com
"""
#pylint: disable=no-member, unused-argument, no-else-return, protected-access
from framework.lib.nulog import INFO
from framework.exceptions.interface_error import NuTestError
from workflows.acropolis.ahv.acro_vm_utility import AcroVMUtil
from libs.framework import mjolnir_entities as entities
from libs.workflows.generic.vm.base_vm import BaseVm
import workflows.acropolis.mjolnir.workflows.generic.vm.vm_checks as VmChecks


class AcliVm(BaseVm):
  """
  Acli VM class, this class contains method specific to ACLI
  """
  def __init__(self, cluster, interface_type="ACLI", **kwargs):
    """
    Instantiate the object
    Args:
      cluster(object): NuTest cluster object
      interface_type(str): Interface type
      kwargs(dict): Keyword args
    """
    super(AcliVm, self).__init__(cluster, interface_type, **kwargs)
    self.vm_cls = entities.ENTITIES.get("rest_vm")(
      cluster=cluster, interface_type=interface_type
    )

  def create(self, **kwargs):
    """
    Create VM
    Args:
    Returns:
      vm(object): VM object
    """
    self.boot_type = kwargs.pop("boot_type", "legacy").lower()
    self.features = kwargs.pop("features", "")
    features = [feature.strip() for feature in self.features.split(",")]
    _spec_matcher = {
      "legacy": "legacy",
      "uefi": "uefi_boot",
      "secure": "secure_boot",
      "credential_guard": "windows_credential_guard",
      "vtpm": "virtual_tpm",
      "hardware_virtualizaion": "hardware_virtualization",
      "mem_oc": "memory_overcommit",
      "cpu_passthru": "cpu_passthrough"
    }

    # Prepare the payload based on boot type - Legacy, UEFI, Secure boot
    for key, val in _spec_matcher.items():
      if key in self.boot_type:
        kwargs.update({val: True})
        if key == "secure":
          kwargs.update({"machine_type": "q35"})

    # Prepare the payload based on vm features - Credential Guard, vTPM, WSL etc
    for key, val in _spec_matcher.items():
      for feature in features:
        if key in feature:
          kwargs.update({val: True})
          # Extra handling if someone doesn't pass secure_boot as boot type
          if key == "credential_guard":
            kwargs.update({_spec_matcher["secure"]: True})


    # Set the acro_vm_util object
    self.acro_vm_util = AcroVMUtil(cluster=self.cluster,
                                   interface_type=self.interface_type)
    INFO("kwargs: %s" % kwargs)
    self.vm = self.acro_vm_util.create_vm_without_disk(
      vm_name=kwargs.pop("name"), num_of_vcpus=kwargs.pop("vcpus", 2),
      mem_mb=kwargs.pop("memory", 2048),
      num_of_vnics=kwargs.pop("num_of_vnics", 0),
      cores_per_vcpu=kwargs.pop("cores_per_vcpu", 1),
      bind=kwargs.pop("bind", True),
      **kwargs
    )

    # cpu_passthru is not support in vm.create call. if provided in features,
    # vm.update will be used to add cpu_passthru to vm
    if "cpu_passthru" in features:
      INFO("Updating VM for cpu_passthru feature as vm.create "
           "does not provide that option")
      self.vm.edit(**{"cpu_passthrough": True})

    return self.vm

  def update(self, **kwargs):
    """
    Update the VM
    """
    power_off_vm = kwargs.pop("power_off_vm", True)
    if power_off_vm:
      self.guest_shutdown()
      self.vm.power_off()
    self.acro_vm_util.update_vm(self.vm, **kwargs)
    self.power_on()

  def migrate(self, **kwargs):
    """
    Migrate VM
    Args:
    Returns:
    Raises:
      NuTestError: If VM migration fails
    """
    prechecks = kwargs.pop("prechecks", True)
    if prechecks:
      is_migration_supported = VmChecks.is_lm_supported(
        cluster=self.cluster, features=self.features, boot_type=self.boot_type
      )
      if not is_migration_supported:
        return

    cmd = "acli vm.migrate %s" % self.vm.uuid
    res = self.cluster.execute(cmd, timeout=kwargs.get("timeout", 3600))
    if "complete" not in res["stdout"].lower():
      raise NuTestError("VM: %s migration failed, reason: %s"
                        % (self.vm.name, res["stdout"]))

  def get_vm_present(self, name):
    """
    get vm present status
    Args:
      name (string) : name of the guest to be checked
    Returns:
      vm(object): VM object
    Raises:
      Nothing
    """
    self.acro_vm_util = AcroVMUtil(cluster=self.cluster,
                                   interface_type="ACLI")
    return self.acro_vm_util.get_vm_by_name(name)

  def bind_vm_present(self, name):
    """
    bind to an existing VM
    Args:
      name (string) : name of the VM to bind
    Returns:
      vm(object): VM object
    Raises:
      Nothing
    """
    self.acro_vm_util = AcroVMUtil(cluster=self.cluster,
                                   interface_type="ACLI")
    return self.acro_vm_util.bind_vm_by_name(name)

  def assign_pcie_device(self, group_uuid, **kwargs):
    """
    assign a pci device with given group_id to the VM
    Args:
      group_uuid (string) : uuid of the hsm device group
    Returns:
    """
    cmd = "acli vm.assign_pcie_device %s group_uuid=%s" % (self.vm.uuid,
                                                           group_uuid)

    res = self.cluster.execute(cmd, timeout=kwargs.get("timeout", 300))
    return res

  def deassign_pcie_device(self, config_uuid, **kwargs):
    """
    Deassign a pci device from VM
    Args:
      config_uuid(str): pcie_device_info uuid
    Returns:
    """
    cmd = ("acli vm.deassign_pcie_device %s config_uuid=%s"
           % (self.vm.uuid, config_uuid))

    res = self.cluster.execute(cmd, timeout=kwargs.get("timeout", 300))
    return res
