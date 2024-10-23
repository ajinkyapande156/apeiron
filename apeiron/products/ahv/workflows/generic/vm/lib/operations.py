"""
VM Operations

Copyright (c) 2024 Nutanix Inc. All rights reserved.
Author: rishabh.kumar@nutanix.com
"""
#pylint: disable=no-else-return, unused-argument, broad-except
import math
from tabulate import tabulate

from framework.lib.nulog import INFO, STEP, WARN, ERROR
import workflows.acropolis.ahv.acro_host_helper as AcroHostHelper
from libs.ahv.framework.exceptions.errors \
  import EntityNotFoundError, UnsupportedParamError
from libs.framework import mjolnir_entities as entities

class VMOps():
  """VMOps class"""
  def __init__(self, cluster, guest, features, vm_name):
    """
    Instantiate method
    Args:
      cluster(object): NuTest Cluster object
      guest(object): GOS object
      features(string): VM features
      vm_name(string): VM Name
    Raises:
      EntityNotFoundError(Exception): If VM is not found on the cluster
    """
    self.cluster = cluster
    self.guest = guest
    self.features = features
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

  def add_vcpu(self, op_type="hot", **kwargs):
    """
    Add vCPU
    Args:
      op_type(str): Hot or cold
      kwargs(dict):
        add_num_vcpus(int): Number of vCPUs to add to the VM
    Returns:
    Raises:
      UnsupportedParamError(Exception): Unsupported param
    """
    STEP(f"Performing {op_type}_add_vcpu on VM {self.vm.name}")
    vm_config = self.vm.get()
    # Add vcpu params
    add_num_vcpus = kwargs.pop("add_num_vcpus", 1)
    vm_edit_params = {
      "vcpus": vm_config["num_vcpus"] + add_num_vcpus
    }

    if op_type == "hot":
      if vm_config["boot"].get("secure_boot", False):
        WARN("Hot add vcpu is not supported on Secure Boot VMs")
        return
      if not self.guest.SUPPORTED_FEATURES["hotplug_num_vcpu"]:
        WARN(f"Hotadd vcpu isn't supported on VM:{self.vm}, guest:{self.guest}")
        return
      if vm_config["power_state"] != "on":
        INFO("VM is not in power on state, powering it on for hot add test")
        self.vm.power_on()
        self.guest.verify_os_boot_post_reboot(self.vm)
    elif op_type == "cold":
      if vm_config["power_state"] == "on":
        INFO("VM is powered on, powering it off for cold add test")
        self.vm.power_off()
    else:
      raise UnsupportedParamError(f"op_type: {op_type}")

    # Update the VM
    INFO(f"Update VM: {self.vm.name} with params: {vm_edit_params}")
    self.vm.edit(**vm_edit_params)

    # Verify from API response
    vm_config_new = self.vm.get()
    assert vm_config_new["num_vcpus"] == vm_config["num_vcpus"]+add_num_vcpus,\
      "Failed to add %s num_vcpus to VM: %s. Expected -> %s, Found -> %s" \
      % (add_num_vcpus, self.vm.name, vm_config['num_vcpus'] + add_num_vcpus, \
         vm_config_new['num_vcpus'])

    # Verify from within the guest
    if op_type == "hot":
      self.guest.bring_cpu_online()
    elif op_type == "cold":
      self.vm.power_on()
      self.guest.verify_os_boot_post_reboot(self.vm)

    cpu_count = self.guest.get_guest_cpu().strip()
    cpu_count = int(cpu_count) / vm_config_new.get("num_cores_per_vcpu")

    assert cpu_count == vm_config_new["num_vcpus"], \
      "Failed to verify addition of %s num_vcpus on VM: %s. "\
      "Expected -> %s, Found -> %s" \
      % (add_num_vcpus, self.vm.name, vm_config_new['num_vcpus'], cpu_count)

  def add_cores(self, op_type="hot", **kwargs):
    """
    Add cpu cores
    Args:
      op_type(str): Hot or cold
      kwargs(dict):
        add_num_cores(int): Number of cores per vCPU to add to the VM
    Returns:
    Raises:
      UnsupportedParamError(Exception): Unsupported param
    """
    STEP(f"Performing {op_type}_add_cores on VM {self.vm.name}")
    vm_config = self.vm.get()
    add_num_cores = kwargs.pop("add_num_cores", 1)
    vm_edit_params = {
      "cores_per_vcpu": vm_config["num_cores_per_vcpu"] + add_num_cores
    }

    if op_type == "hot":
      WARN("Hot add cores is not supported")
      return
    elif op_type == "cold":
      if vm_config["power_state"] == "on":
        INFO("VM is powered on, powering it off for cold add test")
        self.vm.power_off()
    else:
      raise UnsupportedParamError(f"op_type: {op_type}")

    # Update the VM
    INFO(f"Update VM: {self.vm.name} with params: {vm_edit_params}")
    self.vm.edit(**vm_edit_params)

    # Verify from API response
    vm_config_new = self.vm.get()
    assert vm_config_new["num_cores_per_vcpu"] == \
      vm_config["num_cores_per_vcpu"] + add_num_cores, \
      "Failed to add %s cores_per_vcpu to VM: %s. Expected -> %s, Found -> %s" \
      % (add_num_cores, self.vm.name, \
         vm_config["num_cores_per_vcpu"] + add_num_cores, \
         vm_config_new["num_cores_per_vcpu"])

    # Verify from within the guest
    self.vm.power_on()
    self.guest.verify_os_boot_post_reboot(self.vm)

    cores = self.guest.get_guest_cpu().strip()
    cores = int(cores) / vm_config["num_vcpus"]

    assert cores == vm_config_new["num_cores_per_vcpu"], \
      "Failed to verify addition of %s cores_per_vcpu on VM: %s. "\
      "Expected -> %s, Found -> %s" % (add_num_cores, \
      self.vm.name, vm_config_new["num_cores_per_vcpu"], cores)

  def add_memory(self, op_type="hot", **kwargs):
    """
    Add memory
    Args:
      op_type(str): Hot or cold
      kwargs(dict):
        add_mem_mb(int): Memory in MB to be added
    Returns:
    Raises:
      UnsupportedParamError(Exception): Unsupported param
    """
    STEP(f"Performing {op_type}_add_memory on VM {self.vm.name}")
    vm_config = self.vm.get()
    add_mem_mb = kwargs.pop("add_mem_mb", 2048)
    vm_edit_params = {
      "memory": vm_config["memory_mb"] + add_mem_mb
    }

    if op_type == "hot":
      if vm_config["boot"].get("secure_boot", False):
        WARN("Hot add memory is not supported on Secure Boot VMs")
        return
      elif "mem_oc" in self.features:
        WARN("Hoy add memory is not supported on Memory Overcommit VMs")
        return
      if vm_config["power_state"] != "on":
        INFO("VM is not in power on state, powering it on for hot add test")
        self.vm.power_on()
        self.guest.verify_os_boot_post_reboot(self.vm)
    elif op_type == "cold":
      if vm_config["power_state"] == "on":
        INFO("VM is powered on, powering it off for cold add test")
        self.vm.power_off()
    else:
      raise UnsupportedParamError(f"op_type: {op_type}")

    # Update the VM
    INFO(f"Update VM: {self.vm.name} with params: {vm_edit_params}")
    self.vm.edit(**vm_edit_params)

    # Verify from API response
    vm_config_new = self.vm.get()
    assert vm_config_new["memory_mb"] == vm_config["memory_mb"] + add_mem_mb, \
      "Failed to add %s memory_mb to VM: %s. Expected -> %s, Found -> %s" \
      % (add_mem_mb, self.vm.name, vm_config["memory_mb"] + add_mem_mb, \
         vm_config_new["memory_mb"])

    # Verify from within the guest
    if op_type == "hot":
      self.guest.bring_mem_online()
    elif op_type == "cold":
      self.vm.power_on()
      self.guest.verify_os_boot_post_reboot(self.vm)

    mem_mb = self.guest.get_guest_memory().strip()
    mem_mb = math.ceil(float(mem_mb) / float(1024))
    expected_mem = math.ceil(float(vm_config_new["memory_mb"]) / float(1024))

    assert mem_mb == expected_mem, \
      "Failed to verify addition of %s memory_mb on VM: %s. "\
      "Expected -> %sG, Found -> %sG" \
      % (add_mem_mb, self.vm.name, expected_mem, mem_mb)

  def add_vdisk(self, op_type="hot", **kwargs):
    """
    Add vDisk
    Args:
      op_type(str): Hot or cold
      kwargs(dict):
        bus_type(str): Bus type
        disk_size(int): Disk size (MB)
    Returns:
    Raises:
      UnsupportedParamError(Exception): Unsupported param
    """
    STEP(f"Performing {op_type}_add_vDisk on VM {self.vm.name}")
    vm_config = self.vm.get()
    bus_type = "SCSI"
    disk_size = kwargs.pop("disk_size", 2048)

    if op_type == "hot":
      if vm_config["power_state"] != "on":
        INFO("VM is not in power on state, powering it on for hot add test")
        self.vm.power_on()
        self.guest.verify_os_boot_post_reboot(self.vm)
    elif op_type == "cold":
      if vm_config["power_state"] == "on":
        INFO("VM is powered on, powering it off for cold add test")
        self.vm.power_off()
      bus_type = kwargs.pop("bus_type",
                            vm_config["boot"]["disk_address"]["device_bus"])
    else:
      raise UnsupportedParamError(f"op_type: {op_type}")

    old_disks = len(self.vm.get_disks())
    INFO(f"Add {bus_type} disk of size {disk_size} to VM: {self.vm.name}")
    self.vm.add_disk(disk_type=bus_type, size_mb=disk_size, is_cdrom=False)

    # Verify from API response
    new_disks = len(self.vm.get_disks()) - old_disks
    assert new_disks == 1, f"Couldn't add {bus_type} disk to VM {self.vm.name}"

    if op_type == "cold":
      self.vm.power_on()
      self.guest.verify_os_boot_post_reboot(self.vm)

  def add_vnic(self, op_type="hot", **kwargs):
    """
    Add vNics
    Args:
      op_type(str): Hot or cold
      kwargs(dict):

    Returns:
    Raises:
      UnsupportedParamError(Exception): Unsupported param
    """
    STEP(f"Performing {op_type}_add_vNIC  on VM {self.vm.name}")
    vm_config = self.vm.get()
    vm_nics_before = len(self.vm.get_nics())

    if op_type == "hot":
      if vm_config["boot"].get("secure_boot", False):
        WARN("Hot add vNIC is not supported on Secure Boot VMs")
        return
      if vm_config["power_state"] != "on":
        INFO("VM is not in power on state, powering it on for hot add test")
        self.vm.power_on()
        self.guest.verify_os_boot_post_reboot(self.vm)
    elif op_type == "cold":
      if vm_config["power_state"] == "on":
        INFO("VM is powered on, powering it off for cold add test")
        self.vm.power_off()
    else:
      raise UnsupportedParamError(f"op_type: {op_type}")

    INFO(f"Add vNIC to VM {self.vm.name}")
    nw = entities.ENTITIES.get("rest_nw")(interface_type="REST")
    self.vm.add_nic(network=nw.create(bind=True, vlan_id=0))

    # Verify from API response
    vm_nics_curr = len(self.vm.get_nics())
    assert vm_nics_curr == vm_nics_before + 1, \
      f"Failed to add 1 vNIC to VM {self.vm.name}"

    if op_type == "cold":
      self.vm.power_on()
      self.guest.verify_os_boot_post_reboot(self.vm)

    nic_ips = self.guest.get_nics_with_ips()
    for nic in [i for i in nic_ips if "virbr" not in i]:
      gos_util = entities.ENTITIES.get("rpc")(nic_ips[nic])
      result, stdout, stderr = gos_util.check_ok()
      assert result == 0, "Getting os stats from IP %s failed: \n result=%s " \
                          "\n stdout=%s \n stderr:%s" % (gos_util.vm_ip,
                                                         result, stdout, stderr)
      INFO("Successful connection with nic:%s" % nic_ips[nic])

  def migrate_vm_across_node_type(self):
    """
    Migrate VM across all the different combination of node types
    Raises:
      Exception: If any VM migration or verification fails
    """
    co_hosts = AcroHostHelper.get_co_hosts(self.cluster)
    hc_hosts = AcroHostHelper.get_hc_hosts(self.cluster)
    node_combos = [["co", "co"], ["co", "hc"], ["hc", "co"], ["hc", "hc"]]

    table_headers = ["VM Name", "Path", "Migration Status", "Reason"]
    table_rows = []
    test_fail = False
    for node_combo in node_combos:
      res = self._migrate_vm_between_node_types(
        from_node=node_combo[0], to_node=node_combo[1],
        co_hosts=co_hosts, hc_hosts=hc_hosts
      )
      if "fail" in res.get("reason").lower():
        ERROR(f"VM: {self.vm.name} migration failed")
        test_fail = True
      path = f"{node_combo[0]} -> {node_combo[1]}"
      table_row = [self.vm.name, path, res.get("status"), res.get("reason")]
      table_rows.append(table_row)

    migration_table = tabulate(table_rows, table_headers, tablefmt="grid")
    INFO(f"\n{migration_table}\n")

    if test_fail:
      raise Exception("VM Migration step failed")

  def _migrate_vm_between_node_types(self, from_node, to_node, co_hosts,
                                     hc_hosts):
    """
    Migrate VM between different node type (co to hc, hc to co etc)
    Args:
      from_node(str): Source node type
      to_node(str): Destination node type
      co_hosts(list): List of Compute only hosts
      hc_hosts(list): List of Hyperconverged hosts
    Returns:
      res(dict): Result of the migration
    """
    res = {
      "status": "NA",
      "reason": ""
    }
    if from_node == "co" and to_node == "co":
      if len(co_hosts) < 2:
        res.update({
          "reason": f"CO-CO migration cannot be done, cluster has "
                    f"{len(co_hosts)} CO nodes"
        })
      else:
        res = self._migrate(source_host=co_hosts[0],
                            destination_host=co_hosts[1])

    elif from_node == "co" and to_node == "hc":
      if len(co_hosts) < 1 and len(hc_hosts) < 1:
        res.update({
          "reason": f"CO-HC migration cannot be done, cluster has "
                    f"{len(co_hosts)} CO nodes and {len(hc_hosts)} HC nodes"
        })
      else:
        res = self._migrate(source_host=co_hosts[0],
                            destination_host=hc_hosts[0])

    elif from_node == "hc" and to_node == "hc":
      if len(hc_hosts) < 2:
        res.update({
          "reason": f"HC-HC migration cannot be done, cluster has "
                    f"{len(hc_hosts)} HC nodes"
        })
      else:
        res = self._migrate(source_host=hc_hosts[0],
                            destination_host=hc_hosts[1])

    elif from_node == "hc" and to_node == "co":
      if len(co_hosts) < 1 and len(hc_hosts) < 1:
        res.update({
          "reason": f"HC-CO migration cannot be done, cluster has "
                    f"{len(hc_hosts)} HC nodes and {len(co_hosts)} CO nodes"
        })
      else:
        res = self._migrate(source_host=hc_hosts[0],
                            destination_host=co_hosts[0])

    return res

  def _migrate(self, source_host, destination_host):
    """
    Migrate a VM from given source to destination host
    Args:
      source_host(object): Source host object
      destination_host(object): Destination host object
    Returns:
      migration_res(dict): Result and reason
    """
    migration_res = {
      "status": "",
      "reason": ""
    }
    try:
      if self.vm.get()["host_uuid"] != source_host.uuid:
        INFO(f"Bring the VM: {self.vm.name} on expected "
             f"source_host: {source_host.uuid}")
        self.vm.migrate(destination_host=source_host)

      INFO(f"Migrate: {self.vm.name} from "
           f"{source_host.uuid} -> {destination_host.uuid}")
      self.vm.migrate(destination_host=destination_host)

      assert (self.vm.get()["host_uuid"] == destination_host.uuid), \
        f"VM: {self.vm.name} is on host: {self.vm.get()['host_uuid']}, "\
        f"but expected on: {destination_host.uuid}"

      migration_res.update({"status": "PASS"})
    except Exception as ex:
      migration_res.update({"status": "FAIL"})
      migration_res.update({"reason": str(ex)})
    return migration_res
