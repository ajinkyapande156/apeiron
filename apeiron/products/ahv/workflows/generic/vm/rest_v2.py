"""
REST v2 VM

Copyright (c) 2023 Nutanix Inc. All rights reserved.
Author: rishabh.kumar@nutanix.com
"""
#pylint: disable=no-member, unused-argument, no-else-return, protected-access
from framework.lib.nulog import INFO
from workflows.acropolis.ahv.acro_vm_utility import AcroVMUtil
from libs.framework import mjolnir_entities as entities
from libs.workflows.generic.vm.base_vm import BaseVm
from libs.workflows.generic.vm.lib.operations \
  import VMOps
import workflows.acropolis.mjolnir.workflows.generic.vm.vm_checks as VmChecks


class RestVmV2(BaseVm):
  """
  Rest VM class. This class contains methods specific to REST v2 API
  """
  def __init__(self, cluster, interface_type="REST", **kwargs):
    """
    Instantiate the object
    Args:
      cluster(object): NuTest cluster object
      interface_type(str): Interface type
      kwargs(dict): Keyword args
    """
    super(RestVmV2, self).__init__(cluster, interface_type, **kwargs)
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
    # Prepare the payload based on boot type
    kwargs.update({"boot": {}})

    if "uefi" in self.boot_type:
      kwargs.update({'uefi_boot': True})
    elif "secure" in self.boot_type:
      kwargs.update({'uefi_boot': True})
      kwargs.update({'secure_boot': True})
      kwargs.update({"machine_type": "q35"})

    kwargs["boot"].update({"boot_device_order": ["CDROM", "DISK", "NIC"]})

    # Prepare the payload based on features
    for feature in features:
      if "hardware_virtualization" in feature or "credential_guard" in feature:
        kwargs.update({'hardware_virtualization': True})

    # Set the acro_vm_util object
    self.acro_vm_util = AcroVMUtil(cluster=self.cluster,
                                   interface_type=self.interface_type)

    INFO("Kwargs: %s" % kwargs)
    self.vm = self.acro_vm_util.create_vm_without_disk(
      vm_name=kwargs.pop("name"), num_of_vcpus=kwargs.pop("vcpus", 2),
      mem_mb=kwargs.pop("memory", 2048),
      num_of_vnics=kwargs.pop("num_of_vnics", 0),
      cores_per_vcpu=kwargs.pop("cores_per_vcpu", 1),
      bind=kwargs.pop("bind", True),
      **kwargs
    )

    # Set ACLI object
    self.acli_cls = entities.ENTITIES.get("acli_vm")(
      interface_type="ACLI", name=self.vm.name
    )
    # Some features need to be enabled post VM creation - like vTPM
    for feature in features:
      if "vtpm" in feature:
        cmd = "update %s virtual_tpm=true" % self.vm.uuid
        self.acli_cls.execute(entity="vm", cmd=cmd)
      if "mem_oc" in feature:
        cmd = "update %s memory_overcommit=true" % self.vm.uuid
        self.acli_cls.execute(entity="vm", cmd=cmd)
      if "cpu_passthru" in feature:
        cmd = "update %s cpu_passthrough=true" % self.vm.uuid
        self.acli_cls.execute(entity="vm", cmd=cmd)

    return self.vm

  def update(self, **kwargs):
    """
    Update the VM
    """
    power_off_vm = kwargs.pop("power_off_vm", True)
    if power_off_vm:
      self.guest_shutdown()
      self.vm.power_off()

    vm_spec = self.vm.get()
    for key, val in kwargs.items():
      if key == "windows_credential_guard":
        key = "hardware_virtualization"
      if key in ["hardware_virtualization", "uefi_boot", "secure_boot"]:
        vm_spec["boot"].update({key:val})
      else:
        vm_spec.update({key:val})

    self.acro_vm_util.update_vm_by_rest_v2(self.vm, **vm_spec)
    self.power_on()

  def migrate(self, **kwargs):
    """
    Migrate VM
    Args:
    Returns:
    """
    prechecks = kwargs.pop("prechecks", True)
    if prechecks:
      is_migration_supported = VmChecks.is_lm_supported(
        cluster=self.cluster, features=self.features, boot_type=self.boot_type
      )
      if not is_migration_supported:
        return

    migrate_across_node_types = kwargs.get("migrate_across_node_types")
    if migrate_across_node_types:
      vm_ops = VMOps(cluster=self.cluster, vm_name=self.vm.name,
                     features=self.features, guest=self.guest)
      vm_ops.migrate_vm_across_node_type()
    else:
      self.vm.migrate(**kwargs)
