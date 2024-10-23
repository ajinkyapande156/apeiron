"""
Base VM class contains methods common to two or more interfaces

Copyright (c) 2023 Nutanix Inc. All rights reserved.
Author: rishabh.kumar@nutanix.com
"""
#pylint: disable=no-member, unused-argument, no-else-return, protected-access
import random

from framework.lib.nulog import INFO, STEP, WARN
from workflows.acropolis.guest_os_cert.guest_os_cert_wf import \
  GuestOSCertWorkFlow
from workflows.acropolis.ahv.wsl.wsl_common import WSLCommonWorkFlow
from libs.framework import mjolnir_entities as entities
from libs.ahv.framework.exceptions.errors \
  import VMVerificationError
from libs.ahv.workflows.gos_qual.configs \
  import constants
from libs.ahv.workflows.gos_qual.lib.base.utilities \
  import get_os_instance
from libs.workflows.generic.vm.lib.operations \
  import VMOps
from libs.workflows.generic.vm.lib.verifications \
  import VMVerifications


class BaseVm:
  """
  Base VM Class, this class contains methods which are common across
  two or more interfaces - ACLI, v2, v3.
  """
  def __init__(self, cluster, interface_type, **kwargs):
    """
    Instantiate the object
    Args:
      cluster(object): NuTest cluster object
      interface_type(str): Interface type
      kwargs(dict): Keyword args
    """
    self.cluster = cluster
    self.interface_type = interface_type
    self.vm = kwargs.get("vm_obj", None)
    self.acro_vm_util = kwargs.get("acro_vm_util_obj", None)
    self.guest_os = kwargs.get("guest_os", None)
    # One out of legacy, uefi, secure boot
    self.boot_type = kwargs.get("boot_type", None)
    # vTPM, credential guard, hardware_virtualization etc.
    self.features = kwargs.get("features", "")
    self.acli_cls = kwargs.get("acli_cls", None)
    self.running_workloads = []
    if interface_type in ["REST", "ACLI"]:
      self.guest_os_cert = GuestOSCertWorkFlow(self.cluster,
                                               self.interface_type)

  def __getattr__(self, name):
    """
    getattr
    Args:
      name(str): Name of attr
    Returns:
    """
    # if not hasattr(self, name):
    return getattr(self.vm, name)

  def setup_rpc(self, guest_os):
    """
    Setup RPC
    Args:
      guest_os(str): Guest OS
    """
    self.guest_os = guest_os
    if guest_os.startswith("win"):
      # Replace win with windows/windowsserver to match the os format present
      # in mjolnir operating systems dir
      try:
        guest_os_temp = guest_os.replace("win", "windows")
        guest_os_instance = get_os_instance(guest_os_temp)
      except KeyError:
        guest_os_temp = guest_os.replace("win", "windowsserver")
        guest_os_instance = get_os_instance(guest_os_temp)
    else:
      guest_os_instance = get_os_instance(guest_os)

    self.guest = guest_os_instance(
      conn_provider=entities.ENTITIES.get("rpc_vm")(self.vm)
    )

  def add_boot_disk(self, **kwargs):
    """
    Add boot disk to VM
    Args:
    Returns:
    """
    bus_type_list = kwargs.pop("bus_type", "SCSI, SATA")
    disk_image_type = kwargs.pop("disk_image_type", "disk_image")
    bus_type_list = [bus_type.strip() for bus_type in bus_type_list.split(",")]
    bus_type = random.choice(bus_type_list)
    INFO("Using bus type: %s for boot disk" % bus_type)

    self.acro_vm_util.add_boot_disk(
      vm=self.vm, guest_os=self.guest_os, bus_type=bus_type,
      disk_image_type=disk_image_type
    )

  def add_disk(self, **kwargs):
    """
    Add disk to VM
    """
    self.acro_vm_util.add_empty_disk(vm=self.vm, **kwargs)

  def add_empty_cdrom(self, **kwargs):
    """
    Add cdrom with ISO to VM
    """
    self.acro_vm_util.add_empty_cdrom(vm=self.vm, **kwargs)

  def run_io_integrity(self, **kwargs):
    """
    Run IO intergrity inside guest
    """
    self.guest.install_fio()
    drives = self.guest.get_disk_drives()
    self.guest.set_disk_online()
    for drive in drives:
      if "PHYSICALDRIVE0" not in drive:
        self.guest.run_io_integrity(
          vdisk_file=drive, file_size_gb=kwargs.get("file_size_gb", 1),
          time_limit_secs=kwargs.get("time_limit_secs", 120)
        )

  def add_nic(self, **kwargs):
    """
    Add NIC to the VM
    """
    self.acro_vm_util.add_vnic(vm=self.vm, **kwargs)

  def power_on(self, **kwargs):
    """
    Power on the VM
    """
    verify_vm_boot = kwargs.pop("verify_vm_boot", True)
    self.vm.power_on(**kwargs)
    if verify_vm_boot:
      self.setup_rpc(self.guest_os)
      power_on_args = {}
      if kwargs.get("target_host"):
        power_on_args.update({"target_host": kwargs.get("target_host")})
      self.guest.verify_os_boot_post_reboot(self.vm, **power_on_args)

  def power_off(self, **kwargs):
    """
    Power off the VM
    """
    self.vm.power_off(**kwargs)

  def power_reset(self, **kwargs):
    """
    Power reset the VM
    """
    self.vm.power_reset(**kwargs)
    self.setup_rpc(self.guest_os)
    self.guest.verify_os_boot_post_reboot(self.vm)

  def power_cycle(self, **kwargs):
    """
    Power cycle the VM
    """
    self.vm.power_cycle(**kwargs)
    self.setup_rpc(self.guest_os)
    self.guest.verify_os_boot_post_reboot(self.vm)

  def reboot(self, **kwargs):
    """
    Reboot VM
    """
    self.vm.reboot(**kwargs)
    self.guest.verify_os_boot_post_reboot(self.vm)

  def guest_reboot(self, **kwargs):
    """
    Reboot VM from inside the guest
    """
    self.guest.reboot()
    self.guest.verify_os_boot_post_reboot(self.vm)

  def shutdown(self, **kwargs):
    """
    Shutdown VM
    """
    self.vm.shutdown(timeout=kwargs.get("timeout", 600))

  def guest_shutdown(self, **kwargs):
    """
    Shutdown the VM from inside the guest
    """
    self.guest.shutdown()

  def validate_boot_type(self, **kwargs):
    """
    Validate the boot type of the VM - UEFI, Secure boot etc.
    """
    boot_type = kwargs.get("boot_type", self.boot_type.lower())
    INFO("Validate %s boot type" % boot_type)
    if "uefi" in boot_type:
      self.guest.verify_uefi_boot()
    elif "secure" in boot_type:
      self.guest.verify_secure_boot()
    else:
      INFO("No validation needed for %s boot type" % self.boot_type)

  def validate_features(self, **kwargs):
    """
    Validate the VM features - vTPM, Credential Guard etc.
    """
    features = kwargs.get("features", self.features.lower())
    features = [feature.strip() for feature in features.split(",")]
    for feature in features:
      INFO("Validate %s feature" % feature)
      if "vtpm" in feature:
        self.guest.verify_vtpm_boot()
      elif "credential_guard" in feature:
        self.guest.verify_cg_boot()
      else:
        INFO("No validation for %s feature" % feature)

  def clone(self, **kwargs):
    """
    Clone VM
    Args:
    Returns:
      vm_clone_factory(object): VM factory object
    Raises:
    """
    clone_vm_name = self.vm.name + "_clone"
    vm_clone = self.vm.clone(name=clone_vm_name)
    constants.VM_CACHE["vm_list"].append(vm_clone.uuid)

    # pylint:disable=import-outside-toplevel
    from libs.workflows.generic.vm.vm_factory \
      import VmFactory
    # Create a VmFactory object for the cloned VM
    vm_clone_factory = VmFactory(
      cluster=self.cluster,
      interface_type=self.interface_type, vm_obj=vm_clone,
      acro_vm_util_obj=self.acro_vm_util, guest_os=self.guest_os,
      boot_type=self.boot_type, features=self.features
    )
    vm_clone_factory.setup_rpc(guest_os=self.guest_os)

    clone_vm_ops = kwargs.pop("clone_vm_ops", None)
    if clone_vm_ops:
      clone_vm_ops = [op.strip() for op in clone_vm_ops.split(",")]
      for clone_vm_op in clone_vm_ops:
        STEP("Perform step: %s on cloned VM: %s" % (clone_vm_op, vm_clone.name))
        getattr(vm_clone_factory, clone_vm_op)(**kwargs)
    return vm_clone_factory

  def snapshot(self, **kwargs):
    """
    Take snapshot of VM
    """
    if self.interface_type in ["REST", "ACLI"]:
      ss_name = "%s_snapshot" % self.vm.name
      snapshot = self.acro_vm_util.take_vm_snapshot(vm=self.vm, ss_name=ss_name)
      INFO("VM Snapshot successful")
      snapshot.remove()
      INFO("Snaphot deleted successfully")

  def remove(self, **kwargs):
    """
    Delete/remove the VM
    """
    self.vm.remove(**kwargs)
    while (constants.VM_CACHE.get("vm_list") and
           self.vm.uuid in constants.VM_CACHE["vm_list"]):
      constants.VM_CACHE["vm_list"].remove(self.vm.uuid)

  def virtual_device_tests(self, **kwargs):
    """
    Perform virtual device tests
    """
    vm_ops = VMOps(cluster=self.cluster, vm_name=self.vm.name,
                   features=self.features, guest=self.guest)
    tests = kwargs.pop("tests", [])
    for test in tests:
      for op, op_params in test.items():
        op_type = op_params.pop("op_type", "hot") # hot/cold
        getattr(vm_ops, op)(op_type=op_type, **op_params)

  def add_remove_vcpu(self, **kwargs):
    """
    Add remove cpus from the VM
    """
    vm_info = self.vm.get()
    if self.interface_type == "ACLI":
      vm_info = vm_info["config"]
    curr_vcpus = vm_info["num_vcpus"]
    curr_cores = vm_info["num_cores_per_vcpu"]

    expected_num_vcpu = curr_vcpus + kwargs.pop("vcpus_to_add", 1)
    expected_cores = curr_cores + kwargs.pop("cores_to_add", 1)

    vm_power_state = self.vm.get_power_state()
    if vm_power_state == 0:
      self.guest_shutdown()

    self.guest_os_cert.test_add_remove_vcpu(
      uvm=self.vm, guest_os=self.guest_os,
      expected_num_vcpu=expected_num_vcpu, expected_cores=expected_cores,
      **kwargs
    )

  def add_remove_mem(self, **kwargs):
    """
    Add remove memory from the VM
    """
    vm_info = self.vm.get()
    if self.interface_type == "ACLI":
      vm_info = vm_info["config"]
    curr_mem_mb = vm_info["memory_mb"]

    expected_me_size_mb = curr_mem_mb + kwargs.pop("memory_mb_to_add", 2048)

    # Hot plug of memory is not allowed in CG enabled VMs
    credential_guard = False
    if "credential_guard" in self.features:
      credential_guard = True
    if credential_guard:
      INFO("Hot plug memory is not allowed on CG VMs")

    vm_power_state = self.vm.get_power_state()
    if vm_power_state == 0:
      self.guest_shutdown()

    self.guest_os_cert.test_add_remove_memory(
      uvm=self.vm, guest_os=self.guest_os,
      expected_me_size_mb=expected_me_size_mb,
      **kwargs
    )

  def add_remove_vdisk(self, **kwargs):
    """
    Add remove virtual disk from the VM
    """
    num_vdisks = kwargs.pop("num_vdisks", 1)
    bus_type = kwargs.pop("bus_type", "SCSI")
    disk_size = kwargs.pop("disk_size", 2048)

    vm_power_state = self.vm.get_power_state()
    if vm_power_state == 0:
      self.guest_shutdown()

    self.guest_os_cert.test_add_remove_vdisks(
      uvm=self.vm, guest_os=self.guest_os, num_vdisks=num_vdisks,
      bus_type=bus_type, disk_size=disk_size, **kwargs
    )

  def add_remove_vnic(self, **kwargs):
    """
    Add remove virtual nic from the VM
    """
    sb_status = False
    if "secure" in self.boot_type.lower():
      sb_status = True
    num_vnics = kwargs.pop("num_vnics", 1)

    vm_power_state = self.vm.get_power_state()
    if vm_power_state == 0:
      self.guest_shutdown()

    self.guest_os_cert.test_add_remove_vnic(
      uvm=self.vm, guest_os=self.guest_os, num_vnics=num_vnics,
      secure_boot=sb_status, **kwargs
    )

  def enable_guest_features(self, **kwargs):
    """
    Enable features inside the guest
    Args:
    Returns:

    """
    guest_features = kwargs.pop("guest_features", [])
    for guest_feature in guest_features:

      if guest_feature == "wsl" and "hardware_virtualization" in self.features:
        wsl_wf = WSLCommonWorkFlow(cluster=self.cluster, interface_type="REST")

        INFO(f"Enable WSL in VM: {self.vm.name}")
        wsl_wf.install_wsl(self.vm)
        INFO(f"WSL successfully installed on VM: {self.vm.name}")

        INFO(f"Verify WSL in VM: {self.vm.name}")
        wsl_wf.verify_wsl(self.vm, reverify=False)
        INFO(f"Successfully verified that WSL is running on VM: {self.vm.name}")

  def verify_guest_features(self, **kwargs):
    """
    Verify features inside the guest
    Args:
    Returns:
    """
    exp_power_state = "on"
    if kwargs.get("expected_power_state"):
      expected_power_state = kwargs.get("expected_power_state")
      if isinstance(expected_power_state, dict):
        exp_power_state = expected_power_state[self.vm.name]
      else:
        exp_power_state = expected_power_state

    guest_features = kwargs.pop("guest_features", [])
    for guest_feature in guest_features:
      if guest_feature == "wsl" and "hardware_virtualization" in self.features:
        wsl_wf = WSLCommonWorkFlow(cluster=self.cluster, interface_type="REST")

        INFO(f"Verify WSL in VM: {self.vm.name}")
        reverify = True
        # If the VM was turned off during upgrade/or some other workflow
        # after starting WSL, then we need to set reverify parameter to False
        if exp_power_state == "off":
          reverify = False

        wsl_wf.verify_wsl(self.vm, reverify=reverify)
        INFO(f"Successfully verified that WSL is running on VM: {self.vm.name}")

  def start_workloads(self, **kwargs):
    """
    Start workloads inside the VM
    Args:
    Returns:
    """
    if kwargs.pop("power_off_non_migratable_vms", False):
      vm_info = self.vm.get()
      if self.interface_type == "ACLI":
        vm_info = vm_info["config"]
      if not vm_info["allow_live_migrate"]:
        INFO("VM: %s is not live migratable, power off the VM" % self.vm.name)
        self.vm.power_off()
        return

    if kwargs.pop("upgrade_test", False):
      if self.cluster._metadata["nodes_cache"]["nodes_count"] == 1:
        INFO("Cluster has only 1 node, power off the VM")
        self.vm.power_off()
        return

    INFO("Start workloads on VM")
    workload_types = kwargs.pop("workload_types", ["io"])
    for workload_type in workload_types:
      if workload_type == "io":
        self.guest.run_fio(**kwargs.get("io", {}))
        self.running_workloads.append("io")
      elif workload_type in ("mem", "memory"):
        if "win" not in self.guest_os:
          self.guest.run_dirty_harry(**kwargs.get("memory", {}))
          self.running_workloads.append("mem")
      else:
        WARN("Workload type: %s not supported" % workload_type)

  def verify_workloads(self, **kwargs):
    """
    Verify if workloads are running inside the VM
    Args:
    Returns:
    """
    vm_power_state = self.vm.get_power_state()
    if kwargs.get("expected_power_state"):
      expected_power_state = kwargs.get("expected_power_state")
      if isinstance(expected_power_state, dict):
        exp_power_state = expected_power_state[self.vm.name]
      else:
        exp_power_state = expected_power_state

      if exp_power_state == "off":
        INFO("VM: %s expected power state is OFF, skip verifying workload" \
             % self.vm.name)
        self.power_on()
        return
      elif exp_power_state == "on" and vm_power_state != 0:
        raise Exception("VM : %s was expected to be in power on state for " \
                        "verifying workloads" % self.vm.name)

    workload_types = kwargs.pop("workload_types", [])
    if len(workload_types) == 0:
      workload_types = self.running_workloads
    if len(workload_types) == 0:
      INFO("No workloads to verify")
      return

    INFO("Verify %s workloads on VM" % workload_types)
    for workload_type in workload_types:
      if workload_type == "io":
        self.guest.verify_process(process_name="fio")
      elif workload_type in ("mem", "memory"):
        if "win" not in self.guest_os:
          self.guest.verify_process(process_name="harry")
      else:
        WARN("Workload type: %s not supported" % workload_type)

  def vm_verifications(self, **kwargs):
    """
    Run verifications on VM
    Args:
      kwargs(dict): Keyword args
        verifications(list): List of verification methods, for method name see
                             mjolnir/workflows/generic/vm/lib/verifications.py
    Returns:
      None
    """
    verification_obj = VMVerifications(cluster=self.cluster, guest=self.guest, \
                                       vm_name=self.vm.name)
    verifications = kwargs.pop("verifications", "")
    verifications = [verification.strip() for verification in \
                     verifications.split(",")]
    for verification in verifications:
      STEP(f"Run {verification} on VM: {self.vm.name}")
      try:
        getattr(verification_obj, verification)(**kwargs)
      except Exception as ex:
        raise VMVerificationError("%s failed on VM: %s with error: %s" \
                                  % (verification, self.vm.name, ex))
