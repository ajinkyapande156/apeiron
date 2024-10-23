"""
Workflows Helper - VM, Host etc.

Copyright (c) 2023 Nutanix Inc. All rights reserved.
Author: rishabh.kumar@nutanix.com
"""
#pylint: disable=consider-iterating-dictionary, too-many-locals
#pylint: disable=cell-var-from-loop, anomalous-backslash-in-string
#pylint: disable=inconsistent-return-statements, no-else-raise
#pylint: disable=broad-except, no-member, no-self-use
import copy
import math
import random
import time

from datetime import datetime

from framework.exceptions.entity_error import NuTestError
from framework.exceptions.interface_error import NuTestSSHTimeoutError
from framework.lib.nulog import INFO, ERROR, WARN
from framework.lib.parallel_executor import ParallelExecutor
from framework.lib.utils import ping, wait_for_response

from workflows.acropolis.ahv.storm_vms.monitor import Monitor as VMCrashMonitor
from workflows.acropolis.ahv_management.scheduler_test_lib import \
  SchedulerTestLib
from libs.framework import mjolnir_entities as entities
from libs.ahv.workflows.gos_qual.configs \
  import constants
from libs.workflows.generic.vm.vm_factory \
  import VmFactory
from libs.workflows.generic.vm.utilities \
  import vm_executor
from libs.workflows.generic.cluster.cluster_ops \
  import ClusterOps
from libs.workflows.generic import reports
import workflows.acropolis.ahv.acro_host_helper as AcroHostHelper
import workflows.acropolis.mjolnir.workflows.generic.vm.vm_checks as VmChecks


class BaseHelper:
  """
  BaseHelper class
  """
  def __init__(self, **kwargs):
    """
    Intantiate the object

    Args:
      kwargs(dict): Keyword arguments
    """
    self.cluster = kwargs.get("cluster")


class VmHelper(BaseHelper):
  """
  VmHelper Class
  """
  def __init__(self, **kwargs):
    """
    Instantiate the object
    """
    super(VmHelper, self).__init__(**kwargs)
    self.vm_factory = {}

  def create_vm(self, interface_type="ACLI", **kwargs):
    """
    Create VM

    Args:
      interface_type(string): Interface type - ACLI, REST, REST_V3 etc.
    Returns:
      None
    Raises:
      Exception: If the VM is not found on cluster but is expected to be present
    """
    # Create VM name based on guest os and time of creation
    gos_list = kwargs.pop("guest_os", "ubuntu2004_desktop")
    gos_list = [gos.strip() for gos in gos_list.split(",")]
    guest_os = random.choice(gos_list)
    INFO("Using gos: %s" % guest_os)

    name = kwargs.get("name", "test_vm")
    if kwargs.pop("unique_vm_name", False):
      name = "%s_%s_%s" % (name, guest_os, str(datetime.utcnow()))
      name = name.replace(" ", "_")
      kwargs.update({"name": name})

    if kwargs.get("fail_if_not_present"):
      # If the VM is not present on cluster, fail the test.
      # Sample usage - for post upgrade tests.
      rest_vm_obj = entities.ENTITIES.get("rest_vm")(
        cluster=self.cluster, interface_type="REST"
      )
      vm_list = rest_vm_obj.list(self.cluster, json=True)
      is_vm_present = False
      for vm in vm_list:
        if vm["name"] == name:
          is_vm_present = True
          break
      if not is_vm_present:
        raise Exception("VM: %s not found on cluster" % name)

    prechecks = kwargs.pop("prechecks", True)
    if prechecks:
      is_vm_supported = VmChecks.is_vm_supported(
        cluster=self.cluster, features=kwargs.get("features", "")
      )
      if not is_vm_supported:
        INFO("Skip VM creation as it is not supported")
        return

    self.vm_name = name
    self.vm_factory[name] = VmFactory(cluster=self.cluster,
                                      interface_type=interface_type)

    boot_type = kwargs.get("boot_type", "legacy")
    features = kwargs.get("features", "")
    vm = self.vm_factory[name].create(cluster=self.cluster, **kwargs)

    # Add VM entry
    reports.VM_OPERATIONS.update({name: {}})
    reports.VM_OPERATIONS[name].update({
      "boot_type": boot_type,
      "features": features,
      "guest_os": guest_os
    })

    INFO("Setup rpc")
    self.vm_factory[name].setup_rpc(guest_os)

    # Update the VMs in cache - to be used for deleting VMs in teardown method
    if interface_type in ["REST", "ACLI"]:
      constants.VM_CACHE["vm_list"].append(vm.uuid)
    else:
      constants.VM_CACHE["vm_list"].append(vm["uuid"])

    return vm

  @vm_executor
  def add_boot_disk(self, **kwargs):
    """
    Add boot disk to VM
    Args:
    Returns:
    """
    # If vm_name is not provided, use the latest VM
    vm_factory = self.vm_factory[kwargs.pop("vm_name", self.vm_name)]
    vm_factory.add_boot_disk(**kwargs)

  @vm_executor
  def add_disk(self, **kwargs):
    """
    Add disk to VM
    """
    vm_factory = self.vm_factory[kwargs.pop("vm_name", self.vm_name)]
    vm_factory.add_disk(**kwargs)

  @vm_executor
  def run_io_integrity(self, **kwargs):
    """
    Run IO intergrity inside guest
    """
    vm_factory = self.vm_factory[kwargs.pop("vm_name", self.vm_name)]
    vm_factory.run_io_integrity(**kwargs)

  @vm_executor
  def add_nic(self, **kwargs):
    """
    Add NIC to the VM
    """
    vm_factory = self.vm_factory[kwargs.pop("vm_name", self.vm_name)]
    vm_factory.add_nic(**kwargs)

  @vm_executor
  def power_on(self, **kwargs):
    """
    Power on the VM
    """
    vm_factory = self.vm_factory[kwargs.pop("vm_name", self.vm_name)]
    INFO(f"Kwargs: {kwargs}")
    if kwargs.get("node_type"):
      node_type = kwargs.pop("node_type")
      target_host = self.pick_host(node_type=node_type)
      kwargs.update({"target_host": target_host})
    vm_factory.power_on(**kwargs)

  @vm_executor
  def power_off(self, **kwargs):
    """
    Power off the VM
    """
    vm_factory = self.vm_factory[kwargs.pop("vm_name", self.vm_name)]
    vm_factory.power_off(**kwargs)

  @vm_executor
  def power_reset(self, **kwargs):
    """
    Power reset the VM
    """
    vm_factory = self.vm_factory[kwargs.pop("vm_name", self.vm_name)]
    vm_factory.power_reset(**kwargs)

  @vm_executor
  def power_cycle(self, **kwargs):
    """
    Power cycle the VM
    """
    vm_factory = self.vm_factory[kwargs.pop("vm_name", self.vm_name)]
    vm_factory.power_cycle(**kwargs)

  @vm_executor
  def reboot(self, **kwargs):
    """
    Reboot VM
    """
    vm_factory = self.vm_factory[kwargs.pop("vm_name", self.vm_name)]
    vm_factory.reboot(**kwargs)

  @vm_executor
  def guest_reboot(self, **kwargs):
    """
    Reboot VM
    """
    vm_factory = self.vm_factory[kwargs.pop("vm_name", self.vm_name)]
    vm_factory.guest_reboot(**kwargs)

  @vm_executor
  def shutdown(self, **kwargs):
    """
    Shutdown VM
    """
    vm_factory = self.vm_factory[kwargs.pop("vm_name", self.vm_name)]
    vm_factory.shutdown(**kwargs)

  @vm_executor
  def guest_shutdown(self, **kwargs):
    """
    Shutdown VM
    """
    vm_factory = self.vm_factory[kwargs.pop("vm_name", self.vm_name)]
    vm_factory.guest_shutdown(**kwargs)

  @vm_executor
  def validate_boot_type(self, **kwargs):
    """
    Validate the boot type of the VM - UEFI, Secure boot etc.
    """
    vm_factory = self.vm_factory[kwargs.pop("vm_name", self.vm_name)]
    vm_factory.validate_boot_type(**kwargs)

  @vm_executor
  def validate_features(self, **kwargs):
    """
    Validate the VM features - vTPM, Credential Guard etc.
    """
    vm_factory = self.vm_factory[kwargs.pop("vm_name", self.vm_name)]
    vm_factory.validate_features(**kwargs)

  @vm_executor
  def update(self, **kwargs):
    """
    Update the VM
    """
    vm_factory = self.vm_factory[kwargs.pop("vm_name", self.vm_name)]
    vm_factory.update(**kwargs)

  @vm_executor
  def remove(self, **kwargs):
    """
    Delete/remove the VM
    """
    vm_name = kwargs.pop("vm_name", self.vm_name)
    vm_factory = self.vm_factory[vm_name]
    vm_factory.remove(**kwargs)
    # Delete vm entry from self.vm_factory dict
    self.vm_factory.pop(vm_name)

  @vm_executor
  def clone(self, **kwargs):
    """
    Clone VM
    """
    vm_factory = self.vm_factory[kwargs.pop("vm_name", self.vm_name)]
    vm_factory.clone(**kwargs)

  @vm_executor
  def snapshot(self, **kwargs):
    """
    Take snapshot of VM
    """
    vm_factory = self.vm_factory[kwargs.pop("vm_name", self.vm_name)]
    vm_factory.snapshot(**kwargs)

  @vm_executor
  def migrate(self, **kwargs):
    """
    Migrate the VM
    """
    vm_factory = self.vm_factory[kwargs.pop("vm_name", self.vm_name)]
    vm_factory.migrate(**kwargs)

  @vm_executor
  def add_remove_vcpu(self, **kwargs):
    """
    Add remove cpus from the VM
    """
    vm_factory = self.vm_factory[kwargs.pop("vm_name", self.vm_name)]
    vm_factory.add_remove_vcpu(**kwargs)

  @vm_executor
  def add_remove_mem(self, **kwargs):
    """
    Add remove memory from the VM
    """
    vm_factory = self.vm_factory[kwargs.pop("vm_name", self.vm_name)]
    vm_factory.add_remove_mem(**kwargs)

  @vm_executor
  def add_remove_vdisk(self, **kwargs):
    """
    Add remove virtual disk from the VM
    """
    vm_factory = self.vm_factory[kwargs.pop("vm_name", self.vm_name)]
    vm_factory.add_remove_vdisk(**kwargs)

  @vm_executor
  def add_remove_vnic(self, **kwargs):
    """
    Add remove virtual nic from the VM
    """
    vm_factory = self.vm_factory[kwargs.pop("vm_name", self.vm_name)]
    vm_factory.add_remove_vnic(**kwargs)

  @vm_executor
  def virtual_device_tests(self, **kwargs):
    """
    Perform virtual device tests
    """
    vm_factory = self.vm_factory[kwargs.pop("vm_name", self.vm_name)]
    vm_factory.virtual_device_tests(**kwargs)

  @vm_executor
  def enable_guest_features(self, **kwargs):
    """
    Enable features inside the guest
    """
    vm_factory = self.vm_factory[kwargs.pop("vm_name", self.vm_name)]
    vm_factory.enable_guest_features(**kwargs)

  @vm_executor
  def verify_guest_features(self, **kwargs):
    """
    Verify features inside the guest
    """
    vm_factory = self.vm_factory[kwargs.pop("vm_name", self.vm_name)]
    vm_factory.verify_guest_features(**kwargs)

  @vm_executor
  def start_workloads(self, **kwargs):
    """
    Start workloads inside the VM
    """
    vm_factory = self.vm_factory[kwargs.pop("vm_name", self.vm_name)]
    vm_factory.start_workloads(**kwargs)

  @vm_executor
  def verify_workloads(self, **kwargs):
    """
    Verify if workloads are running inside the VM
    """
    vm_factory = self.vm_factory[kwargs.pop("vm_name", self.vm_name)]
    vm_factory.verify_workloads(**kwargs)

  @vm_executor
  def vm_verifications(self, **kwargs):
    """
    Run verifications on VM
    """
    vm_factory = self.vm_factory[kwargs.pop("vm_name", self.vm_name)]
    vm_factory.vm_verifications(**kwargs)

  ############### Methods related to multiple VMs ###############
  def create_multiple_vms(self, **kwargs):
    """
    Create multiple VMs
    """
    num_vms = kwargs.pop("num_vms", 1)
    for num_vm in range(num_vms):
      payload = copy.deepcopy(kwargs)
      # For different configs for each VM
      for key in kwargs.keys():
        if isinstance(kwargs.get(key), list):
          index = num_vm % len(kwargs.get(key))
          INFO("Choose index: %s, val: %s from %s: %s"
               % (index, kwargs.get(key)[index], key, kwargs.get(key)))
          payload.update({
            key:kwargs.get(key)[index]
          })

      skip_vm_creation = False
      if payload.get("bind_preupgrade_vms", False):
        rest_vm_obj = entities.ENTITIES.get("rest_vm")(
          cluster=self.cluster, interface_type="REST"
        )
        vm_list = rest_vm_obj.list(self.cluster, json=True)
        is_vm_present = False
        for vm in vm_list:
          if vm["name"] == payload.get("name", ""):
            is_vm_present = True
            break
        if not is_vm_present:
          INFO("VM: %s is not present on cluster, so no need to create new VM"
               % payload.get("name"))
          skip_vm_creation = True

      if not skip_vm_creation:
        INFO("Create VM")
        self.create_vm(**payload)

      del payload

  def bulk_ops(self, **kwargs):
    """
    Perform bulk operations
    Raises:
      NuTestError(Exception): If there any errors in any of the bulk ops threads
    """
    operations = kwargs.pop("operations", "")
    operations = [operation.strip() for operation in operations.split(",")]
    pool_size = kwargs.pop("pool_size", 10)
    # To select random VMs when the operation needs to be done only
    # on some VMs and not all the VMs
    random_vms = kwargs.pop("random_vms", False)
    if random_vms:
      num_random_vms = min(len(self.vm_factory.keys()),
                           kwargs.pop("num_random_vms", 1))

    vm_factory_dict = self.vm_factory
    if random_vms:
      vm_names = list(vm_factory_dict.keys())
      random_vm_names = random.sample(vm_names, num_random_vms)
      random_vm_factory_dict = {
        vm_name: vm_factory_dict[vm_name] for vm_name in random_vm_names
      }
      vm_factory_dict = random_vm_factory_dict
    # Random VM selection logic over

    for operation in operations:
      executor = ParallelExecutor(pool_size=pool_size)
      for vm_name, _ in vm_factory_dict.items():
        params = copy.deepcopy(kwargs)
        params.update({"vm_name": vm_name})
        thread_name = "%s_%s" % (vm_name, operation)
        executor.add_task(
          target=getattr(self, operation), kwargs=params, thread_name=operation
        )
        del params
      results = executor.run()

      failure_count = 0
      total_count = 0
      for result in results:
        if 'exception' in result:
          failure_count += 1
        total_count += 1

      if failure_count == 0:
        INFO("Bulk operation: %s completed!" % operation)
      else:
        raise NuTestError("%s/%s failures in bulk ops: %s"
                          % (failure_count, total_count, operation))


class HostHelper(BaseHelper):
  """
  Hosthelper Class
  """
  def rolling_maintenance_mode_host(self, **kwargs):
    """
    Perform rolling maintenace mode of hosts
    """
    scheduler_lib = SchedulerTestLib(self.cluster)
    timeout = kwargs.pop("timeout", 3600)
    check_restore_locality = kwargs.pop("check_restore_locality", True)
    for host in self.cluster.hypervisors:
      INFO("Starting rolling maintenace mode on host: %s" % host.ip)
      non_migratable_vm_option = kwargs.pop("non_migratable_vm_option", "BLOCK")
      scheduler_lib.enter_maintenance_mode(host.uuid, timeout_secs=timeout,
                                           non_migratable_vm_option=\
                                           non_migratable_vm_option)
      INFO("Exit maintenance mode on host %s" % host.ip)
      scheduler_lib.exit_maintenance_mode(host.uuid, timeout_secs=timeout,
                                          check_restore_locality=\
                                          check_restore_locality)

  def verify_host_memory(self, **kwargs):
    """
    Verify host memory fetched via API matches the memory displayed in the
    dmidecode command
    Args:
      kwargs(dict):
        permissible_error_percent(int): Difference percent allowed in API
                                        and dmidecode mem output
    Raises:
      Exception: If differnce b/w API and dmidecode mem output is more than
                 permissible limit
    """
    permissible_error_percent = kwargs.pop("permissible_error_percent", 5)
    cluster_ops = ClusterOps(cluster=self.cluster)
    hosts_info = cluster_ops.get_hosts_info()

    api_host_mem_dict = {}
    for host_info in hosts_info:
      host_ip = host_info["hypervisor_address"]
      api_host_mem_gb = \
        host_info["memory_capacity_in_bytes"]/(1024 * 1024 * 1024)
      api_host_mem_gb = math.ceil(api_host_mem_gb)
      api_host_mem_dict[host_ip] = int(api_host_mem_gb)

    dmidecode_host_mem_dict = {}
    for host in self.cluster.hypervisors:
      cmd = "dmidecode -t 17 | grep 'Size.*GB' | awk '{s+=$2} END {print s}'"
      res = host.execute(cmd)
      dmidecode_host_mem_dict[host.ip] = int(res["stdout"])

    for host in self.cluster.hypervisors:
      mem_diff = \
        abs(api_host_mem_dict[host.ip] - dmidecode_host_mem_dict[host.ip])
      mem_diff_perc = (mem_diff * 100)/dmidecode_host_mem_dict[host.ip]

      INFO("Host: %s, API Memory: %s, Memory from dmidecode cmd: %s, " \
           "difference: %s%%"  % (host.ip, api_host_mem_dict[host.ip], \
           dmidecode_host_mem_dict[host.ip], mem_diff_perc))
      if mem_diff_perc > permissible_error_percent:
        err_msg = "Mismatch of %s%% in memory from API and dmidecode" \
                  % mem_diff_perc
        raise Exception(err_msg)

  def verify_crash_kernel_is_loaded(self):
    """
    Verify if crash kernel is loaded on all the hosts
    This is verification for ENG-636541
    Raises:
      Exception: If crash kernel is not loaded on any of the hosts
    """
    cmd = "cat /sys/kernel/kexec_crash_loaded"
    # This command should return 1
    err_msg = []
    for host in self.cluster.hypervisors:
      res = host.execute(cmd)
      if res["status"] == 0:
        if res["stdout"].strip() == "1":
          INFO("Crash kernel is loaded on host: %s" % host.ip)
        else:
          msg = "Crash kernel not loaded on host: %s, output of cmd: %s -> %s" \
                % (host.ip, cmd, res)
          ERROR(msg)
          err_msg.append(msg)
      else:
        msg = "Failed to execute command: %s on host: %s" % (cmd, host.ip)
        ERROR(msg)
        err_msg.append(msg)
    if len(err_msg) > 0:
      raise Exception(err_msg)

  def trigger_host_crash(self, **kwargs):
    """
    Trigger host crash
    Args:
    Raises:
      NuTestSSHTimeoutError(Exception): If host crash command is timed out
      Exception: If the power state of any VM is different post crash
    """
    vm = entities.ENTITIES.get("rest_vm")(cluster=self.cluster,
                                          interface_type="REST")
    vm_list_before = vm.list(cluster=self.cluster, json=True)
    vm_power_state_dict = {}
    for vm_info in vm_list_before:
      vm_power_state_dict.update({vm_info["name"]: {}})
      vm_power_state_dict[vm_info["name"]].update({
        "before": vm_info["power_state"]
      })

    scheduler_lib = SchedulerTestLib(self.cluster)
    cmd = "echo c > /proc/sysrq-trigger"
    for host in self.cluster.hypervisors:
      cutoff_usecs = -1
      cutoff_usecs = scheduler_lib.latest_restore_locality_complete()
      try:
        INFO("Trigger crash on host: %s" % host.ip)
        res = host.execute(cmd, ignore_errors=True)
      except NuTestSSHTimeoutError as err:
        INFO("Waiting for host:%s to reboot and come back online" % host.ip)
        wait_for_response(lambda: ping(host.ip), True, timeout=3600, interval=5)
      sleep_time = kwargs.get("sleep_time", 900)
      INFO("Wait for %ss before triggering host crash on next node"% sleep_time)
      time.sleep(sleep_time)

      INFO("Wait for any restore Locality task to complete")
      scheduler_lib.wait_for_restore_locality_complete(
        cutoff_usecs, check_ssh_keys=False, timeout_secs=9000, check_tasks=True
      )

    vm_list_present = vm.list(cluster=self.cluster, json=True)
    for vm_info in vm_list_present:
      vm_power_state_dict[vm_info["name"]].update({
        "present": vm_info["power_state"]
      })

    if len(vm_list_before) != len(vm_list_present):
      raise Exception("VMs not same post host crash, VMs before: %s," \
                      "Current VMs: %s" % (vm_list_before, vm_list_present))

    err_msg = []
    for vm_name, power_state in vm_power_state_dict.items():
      if power_state["before"] != power_state["present"]:
        err_msg.append("VM: %s power state is not same post host crash. " \
                       "Power state before: %s, present: %s" % (vm_name, \
                       power_state["before"], power_state["present"]))

    if len(err_msg) > 0:
      ERROR(err_msg)
      raise Exception(err_msg)

  def pick_host(self, node_type):
    """
    Pick a host based on node_type
    Args:
      node_type(string): Supported values - "co" and "hc"
    Returns:
      selected_host(object): Target host
    """
    INFO(f"Pick a host of {node_type} node type")
    selected_host = None
    if node_type == "co":
      co_hosts = AcroHostHelper.get_co_hosts(self.cluster)
      if len(co_hosts) > 0:
        selected_host = random.choice(co_hosts)
      else:
        WARN("No CO nodes found in cluster, will return a random host")
    elif node_type == "hc":
      hc_hosts = AcroHostHelper.get_hc_hosts(self.cluster)
      if len(hc_hosts) > 0:
        selected_host = random.choice(hc_hosts)
      else:
        WARN("No HC nodes found in cluster, will return a random host")
    if selected_host is None:
      selected_host = random.choice(self.cluster.hypervisors)

    INFO(f"Picked host: {selected_host.ip}, UUID: {selected_host.uuid}"
         f" Type: {selected_host.node_type}")

    return selected_host


class ClusterHelper(BaseHelper):
  """
  ClusterHelper Class
  """
  def verify_no_vms_crashed(self):
    """
    Verify none of the VMs crashed on the cluster
    """
    vm_crash_monitor = VMCrashMonitor(cluster=self.cluster)
    vm_crash_monitor.monitor_errors()

  def verify_vmcore_generation(self):
    """
    Verify if vmcore is generated on the cluster
    Raises:
      Exception: If vmcore file is not found in /var/crash directory
    """
    vmcore_found = False
    for host in self.cluster.hypervisors:
      cmd = "find /var/log/crash -name 'vmcore' -type f -exec du -h {} \;"
      res = host.execute(cmd)
      if res["status"] == 0:
        if len(res["stdout"]) > 0:
          INFO("vmcore file found on host: %s, details: %s" \
               % (host.ip, res["stdout"]))
          vmcore_found = True
        else:
          ERROR("vmcore file not found on host: %s" % host.ip)
    if vmcore_found is False:
      raise Exception("vmcore file not found in /var/crash dir on any hosts")

  def verify_no_reboot_warnings(self):
    """
    Verify no VM reboot warnings are present on the cluster
    Raises:
      Exception: If VM reboot warning are present
    """
    warnings_found = False
    cmd = "find . -type f -name '*acropolis*' | "\
          "xargs grep -r 'Generating RebootVmsToMigrate Alert'"
    for svm in self.cluster.svms:
      try:
        res = svm.execute(cmd)
        if res["status"] == 0 and len(res["stdout"]) > 0:
          warnings_found = True
          ERROR(f"Found {res['stdout']} on {svm.ip}")
      except Exception:
        pass
    if warnings_found:
      raise Exception("VM reboot warnings found on the cluster")
    else:
      INFO("No VM reboot warnings found on the cluster")

  def perform_upgrade(self, **kwargs):
    """
    Perfrom cluster upgrade
    """
    upgrade_handler = entities.ENTITIES.get("upgrade_handler")(test_args=kwargs)
    upgrade_handler.image_cluster()
    upgrade_handler.trigger_upgrade()
    upgrade_handler.teardown()

class WorkflowsHelper(VmHelper, HostHelper, ClusterHelper):
  """
  VmWorkflows Helper
  """
  def __init__(self, **kwargs):
    """
    Create VmWorkflowsHelper Mixin object
    """
    super(WorkflowsHelper, self).__init__(**kwargs)
    self.vm_helper = VmHelper(**kwargs)
    self.host_helper = HostHelper(**kwargs)
    self.cluster_helper = ClusterHelper(**kwargs)
