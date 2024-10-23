"""
REST v3 VM

Copyright (c) 2023 Nutanix Inc. All rights reserved.
Author: rishabh.kumar@nutanix.com
"""
#pylint: disable=no-member, unused-argument, no-else-return, protected-access
#pylint: disable=too-many-branches, arguments-differ, no-self-use, bare-except
import random

from framework.lib.nulog import INFO, WARN, ERROR
from framework.exceptions.entity_error import NuTestEntityValidationError
from workflows.acropolis.ahv.acro_vm_utility_v3 import AcroVMUtilV3
from libs.framework import mjolnir_entities as entities
from libs.ahv.workflows.gos_qual.configs \
  import constants
from libs.ahv.workflows.gos_qual.lib.base.utilities \
  import get_os_instance
from libs.workflows.generic.vm.base_vm import BaseVm
import workflows.acropolis.mjolnir.workflows.generic.vm.vm_checks as VmChecks
from libs.framework.mjolnir_executor import \
  use_executor


class RestVmV3(BaseVm):
  """
  Rest VM v3 class. This class contains methods specific to REST v3 API
  """
  def __init__(self, cluster, interface_type, **kwargs):
    """
    Instantiate the object
    Args:
      cluster(object): NuTest cluster object
      interface_type(str): Interface type
      kwargs(dict): Keyword args
    """
    super(RestVmV3, self).__init__(cluster, interface_type, **kwargs)
    self.pc = entities.ENTITIES.get("pc")
    self.pe = entities.ENTITIES.get("pe")

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

    if kwargs.pop("bind", True):
      vm_spec = self.discover_vm_by_name(vm_name=kwargs.get("name"))
      if vm_spec is False:
        INFO("Create a new VM, could not bind to existing VMs")
      else:
        self.vm_spec = vm_spec
        self.acro_vm_util = AcroVMUtilV3(ip=self.cluster.pcvms[0].ip)
        try:
          vm_info = self.acro_vm_util.get_vm(self.vm_spec["uuid"],
                                             complete_response=True)
          self.ip = self._get_vm_ip(vm_info['status']['resources'])
          INFO("VM IP: %s, UUID: %s" % (self.ip, self.vm_spec["uuid"]))
        except:
          INFO("No IP found")
        return self.vm_spec

    # Prepare the vm_spec
    vm_spec = entities.ENTITIES.get("restv3_vm").get_sample_spec(
      name=kwargs.get("name"), cluster_uuid=self.pe.uuid
    )
    if kwargs.get("memory"):
      vm_spec.update({"memory_size": kwargs.get("memory")})
    if kwargs.get("vcpus"):
      vm_spec.update({"num_sockets": kwargs.get("vcpus")})
    if kwargs.get("cores_per_vcpu"):
      vm_spec.update({"num_vcpus_per_socket": kwargs.get("cores_per_vcpu")})
    if kwargs.get("cpu_passthru"):
      vm_spec.update({"enable_cpu_passthrough": True})
    if kwargs.get("apc_config"):
      vm_spec.update({"apc_config": kwargs.get("apc_config")})
    if kwargs.get("vnuma_nodes") and kwargs.get("vnuma_nodes") > 1:
      entities.ENTITIES.get("restv3_vm"). \
        update_num_vnuma_nodes_in_vm_spec(vm_spec, kwargs.get("vnuma_nodes"))
    if kwargs.get("num_threads_per_core") and \
      kwargs.get("num_threads_per_core") > 1:
      entities.ENTITIES.get("restv3_vm"). \
        update_num_threads_in_vm_spec(vm_spec,
                                      kwargs.get("num_threads_per_core"))

    # Boot type
    if "uefi" in self.boot_type:
      vm_spec.update({
        'boot_config': {
          'boot_type': 'UEFI'
        }
      })
    if "secure" in self.boot_type:
      vm_spec.update({
        'boot_config': {
          'boot_type': 'SECURE_BOOT'
        },
        'machine_type': 'Q35'
      })

    # Features
    for feature in features:
      if "vtpm" in feature:
        vm_spec.update({
          "vtpm_config": {
            "vtpm_enabled": True
          }
        })
      if "mem_oc" in feature:
        vm_spec.update({
          "memory_overcommit": True
        })
      if "hardware_virtualization" in feature or "credential_guard" in feature:
        vm_spec.update({
          "hardware_virtualization_enabled": True,
        })
      if "cpu_passthru" in feature:
        vm_spec.update({"enable_cpu_passthrough": True})

    self.vm_spec = entities.ENTITIES.get("restv3_vm").create_vm(
      self.pc, vm_spec=vm_spec
    )

    self.acro_vm_util = AcroVMUtilV3(ip=self.cluster.pcvms[0].ip)
    return self.vm_spec

  def discover_vm_by_name(self, **kwargs):
    """
    Discover any existing VM on setup by name
    Args:
    Returns: vm_spec if VM is found, False otherwise
    Raises:
    """
    vm_name = kwargs.get("vm_name")
    vm_list = entities.ENTITIES.get("restv3_vm").get_list(self.pc)
    for vm_spec in vm_list:
      if vm_spec["vm_name"] == vm_name.strip():
        INFO("Found the VM to bind: %s" % vm_spec)
        return vm_spec
    INFO("VM with name: %s not present on the cluster" % vm_name)
    return False

  def setup_rpc(self, guest_os):
    """
    Setup RPC
    Args:
      guest_os(str): Guest OS
    Returns:
    Raises:
      Exception: When we can't connect to the test agent inside guest
    """
    self.guest_os = guest_os
    if not hasattr(self, "ip"):
      return

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

    guest = guest_os_instance(
      conn_provider=entities.ENTITIES.get("rpc")(self.ip)
    )
    try:
      guest.verify_os_boot()
      self.guest = guest
    except:
      raise Exception("Could not connect to guest via IP: %s" % self.ip)

  def add_boot_disk(self, **kwargs):
    """
    Add boot disk to VM
    Args:
    Returns:
    """
    bus_type_list = kwargs.pop("bus_type", "SCSI, SATA")
    bus_type_list = [bus_type.strip() for bus_type in bus_type_list.split(",")]
    bus_type = random.choice(bus_type_list)
    INFO("Using bus type: %s for boot disk" % bus_type)

    self.acro_vm_util.add_boot_disk(vm_spec=self.vm_spec,
                                    image_name=self.guest_os,
                                    adapter_type=bus_type)

  def add_disk(self, **kwargs):
    """
    Add disk to VM
    """
    bus_type = kwargs.pop("bus_type", "SCSI")
    disk_size_mb = kwargs.pop("disk_size_mb", 1024)
    hotplug = kwargs.pop("hotplug", False)
    self.acro_vm_util.add_disk(
      vm_spec=self.vm_spec, adapter_type=bus_type,
      disk_size_in_mib=disk_size_mb, hotplug=hotplug
    )

  def add_nic(self, **kwargs):
    """
    Add NIC to the VM
    """
    subnet_uuid = self.acro_vm_util.get_or_create_subnet_uuid(self.cluster, 0)
    self.acro_vm_util.add_nic(self.vm_spec, subnet_uuid=subnet_uuid)

  @use_executor
  def power_on(self, **kwargs):
    """
    Power on the VM
    """
    self.acro_vm_util.power_on_vm_wait_for_ip(self.vm_spec)
    vm_info = self.acro_vm_util.get_vm(self.vm_spec["uuid"],
                                       complete_response=True)
    self.ip = self._get_vm_ip(vm_info['status']['resources'])
    INFO("VM IP: %s" % self.ip)
    if not hasattr(self, "guest"):
      self.setup_rpc(guest_os=self.guest_os)

    rest_vm_cls = entities.ENTITIES.get("rest_vm")(
      cluster=self.cluster, interface_type="REST"
    )
    vm_rest = rest_vm_cls.create(uuid=self.vm_spec["uuid"]) # bind
    self.guest.verify_os_boot_post_reboot(vm_rest)

  def power_off(self, **kwargs):
    """
    Power off the VM
    """
    self.acro_vm_util.power_off_vm(vm_spec=self.vm_spec)

  def power_reset(self, **kwargs):
    """
    Power reset the VM
    """
    self.power_off()
    self.power_on()

  def power_cycle(self, **kwargs):
    """
    Power cycle the VM
    """
    self.power_off()
    self.power_on()

  def reboot(self, **kwargs):
    """
    Reboot VM
    """
    self.power_off()
    self.power_on()

  def guest_reboot(self, **kwargs):
    """
    Reboot VM from inside the guest
    """
    self.guest.reboot()
    rest_vm_cls = entities.ENTITIES.get("rest_vm")(
      cluster=self.cluster, interface_type="REST"
    )
    vm_rest = rest_vm_cls.create(uuid=self.vm_spec["uuid"]) # bind
    self.guest.verify_os_boot_post_reboot(vm_rest)

  def shutdown(self, **kwargs):
    """
    Shutdown VM
    """
    self.acro_vm_util.guest_shutdown_vm(vm_spec=self.vm_spec)

  def update(self, **kwargs):
    """
    Update the VM
    """
    power_off_vm = kwargs.pop("power_off_vm", True)
    if power_off_vm:
      self.power_off()

    self.vm_spec = entities.ENTITIES.get("restv3_vm").update_vm(
      aplos_client=self.pc, vm_spec=self.vm_spec, **kwargs
    )

  def migrate(self, **kwargs):
    """
    Migrate VM
    Args:
    Returns:
    """
    # Perform Migration via Rest v2.
    prechecks = kwargs.pop("prechecks", True)
    if prechecks:
      is_migration_supported = VmChecks.is_lm_supported(
        cluster=self.cluster, features=self.features, boot_type=self.boot_type
      )
      if not is_migration_supported:
        return

    rest_vm_cls = entities.ENTITIES.get("rest_vm")(
      cluster=self.cluster, interface_type="REST"
    )
    vm_rest = rest_vm_cls.create(uuid=self.vm_spec["uuid"]) # bind
    vm_rest.migrate(**kwargs)

  def clone(self, **kwargs):
    """
    Clone VM
    """
    clone_vm_name = self.vm_spec["name"] + "_clone"
    entities.ENTITIES.get("restv3_vm").clone_vm(
      name=clone_vm_name, aplos_client=self.pc,
      source_vm_uuid=self.vm_spec["uuid"], cluster_uuid=self.pe.uuid
    )

  def remove(self, **kwargs):
    """
    Delete/remove the VM
    """
    self.acro_vm_util.delete_vm_by_uuid(uuid=self.vm_spec["uuid"])
    constants.VM_CACHE["vm_list"].remove(self.vm_spec["uuid"])

  def add_remove_vcpu(self, **kwargs):
    """
    Add remove cpus from the VM
    """
    # TODO: Add code

  def add_remove_mem(self, **kwargs):
    """
    Add remove memory from the VM
    """
    # TODO: Add code

  def add_remove_vdisk(self, **kwargs):
    """
    Add remove virtual disk from the VM
    """
    # TODO: Add code

  def add_remove_vnic(self, **kwargs):
    """
    Add remove virtual nic from the VM
    """
    # TODO: Add code

  def start_workloads(self, **kwargs):
    """
    Start workloads inside the VM
    Args:
    Returns:
    """
    acli_vm = entities.ENTITIES.get("rest_vm")(
      cluster=self.cluster, interface_type="ACLI"
    )
    vm_acli = acli_vm.create(uuid=self.vm_spec["uuid"]) # Bind the VM
    if kwargs.pop("power_off_non_migratable_vms", False):
      vm_info = vm_acli.get()["config"]
      if not vm_info["allow_live_migrate"]:
        INFO("VM: %s is not live migratable, power off the VM" % vm_acli.name)
        vm_acli.power_off()
        return

    if kwargs.pop("upgrade_test", False):
      if self.cluster._metadata["nodes_cache"]["nodes_count"] == 1:
        INFO("Cluster has only 1 node, power off the VM")
        vm_acli.power_off()
        return

    INFO("Start workloads on VM")
    workload_types = kwargs.pop("workload_types", ["io"])
    for workload_type in workload_types:
      if workload_type == "io":
        self.guest.run_fio()
      else:
        WARN("Workload type: %s not supported" % workload_type)

  def verify_workloads(self, **kwargs):
    """
    Verify if workloads are running inside the VM
    Args:
    Returns:
    """
    acli_vm = entities.ENTITIES.get("rest_vm")(
      cluster=self.cluster, interface_type="ACLI"
    )
    vm_acli = acli_vm.create(uuid=self.vm_spec["uuid"]) # Bind the VM
    vm_power_state = vm_acli.get_power_state()

    if kwargs.get("expected_power_state"):
      expected_power_state = kwargs.get("expected_power_state")
      if isinstance(expected_power_state, dict):
        exp_power_state = expected_power_state[self.vm_spec["name"]]
      else:
        exp_power_state = expected_power_state

      if exp_power_state == "off":
        INFO("VM: %s expected power state is OFF, skip verifying workload" \
             % self.vm_spec["name"])
        self.power_on()
        return
      elif exp_power_state == "on" and vm_power_state != 0:
        raise Exception("VM : %s was expected to be in power on state for " \
                        "verifying workloads" % self.vm_spec["name"])

    INFO("Verify workloads on VM")
    workload_types = kwargs.pop("workload_types", ["io"])
    for workload_type in workload_types:
      if workload_type == "io":
        self.guest.verify_process(process_name="fio")
      else:
        WARN("Workload type: %s not supported" % workload_type)

  def _get_vm_ip(self, vm_spec, return_all=False):
    """
    Retrieve VM's IP Address from the specified spec.

    Args:
      vm_spec(dict): Spec of the required VM.
      return_all(bool): Return a list of IP addresses (default: False)

    Returns:
      str/list: IP Address or list of IP Addresses of the VM, if present.
    """
    ip_list = []
    nic_list = vm_spec.get('nic_list', [])
    if not nic_list:
      ERROR("No NIC present in VM Spec.")
    for nic in nic_list:
      ip_endpoints = nic.get('ip_endpoint_list', [])
      for ip_endpoint in ip_endpoints:
        if ip_endpoint.get('ip'):
          if return_all and not ip_endpoint['ip'].startswith("169"):
            ip_list.append(ip_endpoint['ip'])
          else:
            if not ip_endpoint['ip'].startswith("169"):
              return ip_endpoint['ip']
    if ip_list:
      return ip_list
    else:
      raise NuTestEntityValidationError("No IP Addresses found in VM Spec.")
