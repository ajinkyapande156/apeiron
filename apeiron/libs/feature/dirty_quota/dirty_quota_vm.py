"""
Copyright (c) 2023 Nutanix Inc. All rights reserved.

Author: pritam.chatterjee@nutanix.com
"""
# pylint: disable=wrong-import-order, no-member, unused-variable
# pylint: disable=ungrouped-imports, no-self-use, fixme
# pylint: disable=anomalous-backslash-in-string, unused-import,
# pylint: disable=unnecessary-comprehension, unused-argument, broad-except
from __future__ import division
from random import randrange
import uuid
import time
import os
import json
from framework.lib.nulog import INFO, WARN, ERROR
from libs.framework import mjolnir_entities as entities
from framework.exceptions.entity_error import NuTestEntityValidationError
from libs.feature.apc.factory \
  import ApcVmFactory
from libs.feature.dirty_quota import constants as const
from libs.framework.mjolnir_executor import use_executor
from libs.feature.dirty_quota.dirty_quota_cluster \
  import DirtyQuotaCluster
from libs.workflows.apc.wf_helpers import ApcWfHelper


class DirtyQuotaVm:
  """DirtyQuotaVmProfile class"""

  def __init__(self, **kwargs):
    """
    Create a VM spec to achieve Dirty Quota based throttling during LM
    Kwargs:
      num_of_vcpus(int): Number of VM cpus. If given None, it will be determined
      transfer_rate(int): Network bandwidth to be used by qemu for LM
                          for this VM. If given None, it will be determined
      memory(int): VM memory in GB
      dirty_rate(int): in Mbps. The memory dirty rate for the VM.
                       If given None, it will be determined. We can control it.
      dirty_quota_per_vcpu(int): DO NOT CHANGE. dirty quota per vCPU.
      dirty_quota_interval(int): DO NOT CHANGE. dirty quota interval.
                                 Defaults to 1.
      min_dirty_quota_limit(int): DO NOT CHANGE. min dirty rate limit per vCPU
    Returns:
    """
    self.vcpus = kwargs.get("num_of_vcpus", 2)
    self.memory = kwargs.get("memory_size", 8)  # gb
    self.memory = self.memory * 1024
    self.transfer_rate = kwargs.get("transfer_rate", 5120)  # Mbps
    # hidden params as of now
    self.dirty_rate = kwargs.get("dirty_rate", None)  # MBps
    self.active_working_set = kwargs.get(
      "active_working_set") or self.memory * 0.80  # GB
    self.dirty_quota_per_vcpu = kwargs.get("dirty_quota_per_vcpu", None)  # MBps
    self.dirty_quota_interval = kwargs.get("dirty_quota_interval", 1)  # ms
    self.min_dirty_quota_limit = kwargs.get("min_dirty_quota_limit", 1)  # MBps
    self.pc = entities.ENTITIES.get("pc")
    self.vm = ApcVmFactory(**kwargs)
    self.running_workloads = []  # store the running workloads
    self.install_workloads = {
      "harry": self.install_dirty_harry,
      "fio": self.install_fio
    }
    self.verify_workloads = {
      "harry": self.verify_dirty_harry,
      "fio": self.verify_fio
    }
    self.run_workload = {
      "harry": self.run_dirty_harry,
      "fio": self.run_fio
    }
    self.vm_uuid = None

  def __getattr__(self, item):
    """
    Check the vm object for any undefined method
    Args:
      item(str):
    Returns:
    """
    WARN("Not able to find [%s] attribute for DirtyQuotaVmProfile,"
         " checking in [%s]" % (item, self.vm))
    return getattr(self.vm, item)

  def create(self, **kwargs):
    """
    Create a VM with DQ specs
    Args:
    Returns:
    """
    if not kwargs.get("vm_name"):
      kwargs["vm_name"] = "dirty_quota_vm_" + str(uuid.uuid1()).split("-")[0]
    kwargs["num_of_vcpus"] = self.vcpus
    kwargs["memory_size"] = self.memory
    self.display_spec()
    vm_spec = self.vm.create(**kwargs)
    self.vm_uuid = vm_spec.get("uuid")
    self.vm.add_guest_os(vm_spec, **kwargs)
    self.vm.power_on(vm_spec)
    self.vm.is_vm_accesible(vm_spec={"uuid": self.vm_uuid},
                            retries=60,
                            delay=5)
    if kwargs.get("configure_tools", True):
      self.configure_tools()
    return vm_spec

  # def discover_vm_by_name(self, **kwargs):
  #   """
  #   Discover any existing VM on setup by name
  #   Please NOTE vm name should be UNIQUE on the setup, otherwise
  #   this method will behave abnoramally
  #   :param kwargs:
  #   :return:
  #   """
  #   return self.vm.discover_by_name(**kwargs)

  def configure_tools(self, **kwargs):
    """
    Internal method to install the tools on dirty Quota based VMs
    Kwargs:
      workloads(str): comma seperated tools to be install
    """
    tools = kwargs.get("tools", [tool for tool in self.install_workloads])
    if isinstance(tools, str):
      tools = tools.split(",")
    for tool in tools:
      try:
        INFO("Trying to install and configure %s" % tool)
        self.install_workloads[tool]()
        self.verify_workloads[tool]()
        INFO("Installed and configured %s" % tool)
      except KeyError:
        ERROR("Tool %s not supported" % tool)

  @use_executor
  def install_dirty_harry(self):
    """
    Install dirty harry on VM
    Returns:
    Raises:
    """
    rpc = self.vm.is_vm_accesible(vm_spec={"uuid": self.vm_uuid},
                                  retries=60,
                                  delay=5)
    rpc.run_shell_command_sync("wget http://endor.dyn.nutanix.com/acro_images/"
                               "automation/ahv_guest_os/Misc/harry")
    rpc.run_shell_command_sync("chmod +x harry")

  def install_fio(self):
    """
    Install fio on VM
    Returns:
    Raises:
    """
    WARN("Images should already have fio installed and configured")

  def verify_dirty_harry(self):
    """
    Verify dirty harry on VM
    Returns:
      bool
    Raises:
    """
    WARN("No verification added from Dirty Harry")
    return True

  def verify_fio(self):
    """
    Verify fio on VM
    Returns:
      bool
    Raises:
    """
    rpc = self.vm.is_vm_accesible(vm_spec={"uuid": self.vm_uuid},
                                  retries=60,
                                  delay=5)
    result, stdout, stderr = rpc.run_shell_command_sync("fio --help")
    assert result == 0, "Failed to verify fio installation"
    return True

  def start_workload(self, **kwargs):
    """
    Run the provided workload
    Kwargs:
      dirty_rate(int): defaults to self.dirty_rate
      use_cpus(int): defaults to vm cpus
    Returns:
    Raises:
    """
    workloads = {
      "harry": self.run_dirty_harry,
      "fio": self.run_fio
    }
    workload = kwargs.get("workload", "harry")
    return workloads[workload](**kwargs)

  @use_executor
  def run_dirty_harry(self, **kwargs):
    """
    Run dirty harry on VM. No memory read operation
    Kwargs:
      dirty_rate(int): defaults to self.dirty_rate
      use_cpus(int): defaults to vm cpus
    Returns:
    Raises:
    """
    mem_before = self.get_memory_usage()
    # cpu_before = self.get_cpu_usage()
    rpc = self.vm.is_vm_accesible(vm_spec={"uuid": self.vm_uuid},
                                  retries=60,
                                  delay=5)
    INFO("Starting dirty-harry with following params:")
    mem_to_dirty = self.active_working_set / 1024
    INFO("CPUs: %s" % self.vcpus)
    INFO("Memory to dirty: %s" % mem_to_dirty)
    INFO("Dirty Rate: %s" % self.dirty_rate)
    cmd = "./harry -n %s -m %s -l %s" % (self.vcpus, mem_to_dirty,
                                         self.dirty_rate)
    task_id = rpc.run_shell_command_handsoff(cmd)
    self.running_workloads.append({
      "workload_type": "memory",
      "tool_type": "harry",
      "vm": self.vm_uuid,
      "ip": rpc.vm_ip,
      "task_id": task_id
    })
    time.sleep(30)
    assert mem_before < self.get_memory_usage(), "Memory utilizations " \
                                                 "did not go up"
    cmd = "ps -ef | grep harry | grep -v grep"
    result, stdout, stderr = rpc.run_shell_command_sync(cmd)
    assert result == 0, "Failed to validate if dirty_harry was started"

  def run_fio(self, **kwargs):
    """
    Run fio on VM. No memory read operation
    Kwargs:
    Returns:
    Raises:
    """
    rpc = self.vm.is_vm_accesible(vm_spec={"uuid": self.vm_uuid},
                                  retries=60,
                                  delay=5)
    cmd = 'fio --filename=/root/fio.test --size=5GB --direct=0 ' \
          '--rw=randrw --bs=4k --ioengine=libaio --iodepth=256 --numjobs=4 ' \
          '--name=iops-test-job --eta-newline=1 --verify=crc32c --runtime=300'
    task_id = rpc.run_shell_command_handsoff(cmd)
    self.running_workloads.append({
      "workload_type": "disk",
      "tool_type": "fio",
      "vm": self.vm_uuid,
      "ip": rpc.vm_ip,
      "task_id": task_id
    })
    cmd = "ps -ef | grep fio"
    result, stdout, stderr = rpc.run_shell_command_sync(cmd)
    assert result == 0, "Failed to validate if fio was started"

  def get_memory_usage(self):
    """
    Provides the memory usage on linux machine
    Returns:
      stdout(int):
    """
    rpc = self.vm.is_vm_accesible(vm_spec={"uuid": self.vm_uuid},
                                  retries=60,
                                  delay=5)
    assert "linux" in rpc.get_guest_os_info()["system"].lower(), \
      "This method will not work for non-Linux Operating systems"
    cmd = 'sar -r 1 5 | grep Average: | awk "{print \$5}"'
    result, stdout, stderr = rpc.run_shell_command_sync(cmd)
    assert result == 0, "Failed to get the memory usage"
    return float(stdout.strip())

  def get_cpu_usage(self):
    """
    Provides the cpu usage on linux machine
    Returns:
      usage(int):
    """
    rpc = self.vm.is_vm_accesible(vm_spec={"uuid": self.vm_uuid},
                                  retries=60,
                                  delay=5)
    assert "linux" in rpc.get_guest_os_info()["system"].lower(), \
      "This method will not work for non-Linux Operating systems"
    cmd = 'sar -u 1 5 | grep Average:| awk "{print \$3}"'
    result, stdout, stderr = rpc.run_shell_command_sync(cmd)
    assert result == 0, "Failed to get the cpu usage"
    return float(stdout.strip())

  def stop_workload(self, **kwargs):
    """
    stop the given workload running in background
    Kwargs:
      tool_type(str):
    Returns:
      bool
    """
    # TODO: Complete this method @pritam.chatterjee
    workload = kwargs.get("workload", "harry")
    rpc = self.vm.is_vm_accesible(vm_spec={"uuid": self.vm_uuid},
                                  retries=60,
                                  delay=5)
    for workloads in self.running_workloads:
      if workload == workloads["tool_type"]:
        INFO("Checking task: %s" % workloads["task_id"])
        status, _ = rpc.query_handsoff_task_status(workloads["task_id"])
        assert status == 1, "The workload is not running"
        INFO("Stopping working within the guest")
        cmd = 'ps -ef | grep %s | grep -v grep | awk "{print \$2}"' % workload
        result, stdout, stderr = rpc.run_shell_command_sync(cmd)
        # if stdout:
        #   import pdb;
        #   pdb.set_trace()

  def get_workload_status(self, **kwargs):
    """
    Get the workload status by tool name and VM name
    Kwargs:
      tool_type(str):
    Returns:
      bool
    """
    workload = kwargs.get("workload", "harry")
    rpc = self.vm.is_vm_accesible(vm_spec={"uuid": self.vm_uuid},
                                  retries=60,
                                  delay=5)
    # import pdb;
    # pdb.set_trace()
    for workloads in self.running_workloads:
      if workload == workloads["tool_type"]:
        INFO("Checking task: %s" % workloads["task_id"])
        status, _ = rpc.query_handsoff_task_status(workloads["task_id"])
        assert status == 1, "The workload is not running"
        cmd = "ps -ef | grep %s | grep -v grep" % workload
        result, stdout, stderr = rpc.run_shell_command_sync(cmd)
        assert result == 0, "Failed to validate if %s was started" % workload

  def display_spec(self):
    """
    Print the details of the Dirty Quota VM
    """
    # determine the dirty quota per vcpu with given transfer rate and vcpus
    self.dirty_quota_per_vcpu = ((self.transfer_rate / 2) *
                                 self.dirty_quota_interval) / self.vcpus
    INFO("Calculated DIRTY QUOTA PER vCPU: %s MBps" %
         self.dirty_quota_per_vcpu)

    # dirty_rate should be greater than the dirty rate limit to throttle
    if not self.dirty_rate:
      self.dirty_rate = self.transfer_rate / 2 + randrange(
        self.transfer_rate // 4)
    INFO("--------------------------")
    INFO("vCPU: %s" % self.vcpus)
    INFO("Memory: %s MB" % self.memory)
    INFO("Transfer rate: %s MBps" % self.transfer_rate)
    INFO("Dirty rate: %s MBps" % self.dirty_rate)
    INFO("Active working Set: %s MB" % self.active_working_set)
    INFO("--------------------------")

  def libvirt_service_restart(self, **kwargs):
    """
    Restart the libvirt service on host
    Args:
    Returns:
    Raises:
    """
    cluster = entities.ENTITIES.get("pe")
    helper = ApcWfHelper(cluster=cluster)
    host_uuid = self.vm.get(
      vm_spec={"uuid": self.vm_uuid})["host_reference"]["uuid"]
    host_obj = [hyp for hyp in cluster.hypervisors
                if hyp.uuid == host_uuid][0]
    helper.restart_libvirt(host_obj, **kwargs)

  def predict_lm_time(self):
    """
    Predict LM time for this VM
    Returns:
      predicted_time(int): secs
    """
    predicted_time = (2 * self.memory) / self.transfer_rate
    # INFO('Predicted Time: %s sec' % predicted_time)
    return predicted_time

  @use_executor
  def live_migrate(self, **kwargs):
    """
    Live migrate a VM with defined transfer rate
    Returns:
    """
    WARN("Live Migration will be done using ACLI as v3 API is not available")
    # FIXME: If the VM is powered-off, power it on.
    vm = ApcVmFactory(api_type="restv3")
    vm_spec = kwargs.get("vm_spec")
    current_host = vm.get(retries=3, delay=2,
                          vm_spec=vm_spec)["host_reference"]["uuid"]
    INFO("Current Host: %s" % current_host)
    acli_vm = ApcVmFactory(api_type="acli")
    try:
      acli_vm.migrate(retries=1, delay=1,
                      **{"vm_name": self.vm_uuid,
                         "host": kwargs.get("target_host",
                                            None),
                         "bandwidth_mbps": self.transfer_rate}
                      )
    except Exception as ex:
      if kwargs.get("auto_converge_fallback"):
        ERROR("Expected error: %s" % ex)
        ERROR("Continuing to check if auto-converge fallback happened")
      else:
        raise ex
    kwargs["source_host"] = current_host
    if not kwargs.get("auto_converge_fallback"):
      new_host = vm.get(retries=3, delay=2,
                        vm_spec=vm_spec)["host_reference"]["uuid"]
      INFO("New Host: %s" % new_host)
      assert not current_host == new_host, "VM host did not change after LM"
    self.validate_dirty_quota_migration(retries=10, delay=5, **kwargs)
    self.vm.is_vm_accesible(vm_spec={"uuid": self.vm_uuid},
                            retries=60,
                            delay=5)

  @use_executor
  def validate_dirty_quota_migration(self, **kwargs):
    """
    Validate that LM is performed with dirty quota
    Args:
    Returns:
    """
    migration_id = self._get_latest_migration_id()
    assert migration_id, "Failed to get migration id for %s" % self.vm_uuid
    INFO("Latest migration id %s" % migration_id)
    migrations_file = os.path.join(const.MIGRATIONS_DIR, migration_id + ".log")
    data = self._read_migration_file_on_host(host_uuid=
                                             kwargs.get("source_host"),
                                             migration_file=migrations_file)
    dq_enabled_itr = 0
    auto_cvg_itr = 0
    for entry in data:
      INFO("=========================")
      INFO(entry)
      if "dirty_quota_active" in entry and entry["dirty_quota_active"] == 1:
        dq_enabled_itr += 1
      elif "dirty_quota_active" in entry and entry["dirty_quota_active"] == 0:
        auto_cvg_itr += 1
      INFO("=========================")
      # import pdb; pdb.set_trace()
    INFO("=========================")
    INFO("Total iternations with dirty quota active: %s" % dq_enabled_itr)
    INFO("Total auto converge iterations: %s" % auto_cvg_itr)
    INFO("Total number of iternation: %s" % len(data))
    INFO("=========================")
    validate_dirty_quota = kwargs.get("validate_dirty_quota", True)
    if validate_dirty_quota:
      if kwargs.get("auto_converge_fallback"):
        assert len(data) - dq_enabled_itr > 1, \
          "No autoconverge failback observed"
      else:
        assert dq_enabled_itr, \
          "None of the LM iterations were dirty quota enabled"
      INFO("Dirty Quota usage was validated successfully")
    else:
      assert dq_enabled_itr == 0, \
        "Dirty Quota was used where it was not expected"

  @use_executor
  def update_vcpu_for_autoconverge(self):
    """
    Updates the vCPUs in the VM for fallback to auto-converge
    Args:
    Returns:
    Raises:
    """
    raise NotImplementedError

  def update_tranfer_rate_for_autoconverge(self):
    """
    Updates the transfer rate to be used during LM for fallback
    to auto-converge
    Returns:
    """
    self.transfer_rate = self.get_revised_transfer_rate_for_autoconverge()

  def get_revised_vcpu_for_autoconverge(self):
    """
    Get the revised vcpu for autoconverge fallback
    Returns:
      new_vcpu(int):
    """
    INFO("Current vCPUs: %s" % self.vcpus)
    INFO("Current TRANSFER RATE: %s" % self.transfer_rate)
    INFO("Current DIRTY QUOTA PER vCPU: %s" % self.dirty_quota_per_vcpu)
    # How many vcpus we need to throttle
    if self.dirty_quota_per_vcpu >= self.min_dirty_quota_limit:
      INFO("Making %s <= %s, by changing vCPU" % (self.dirty_quota_per_vcpu,
                                                  self.min_dirty_quota_limit))
      new_vcpu = ((self.transfer_rate / 2) *
                  self.dirty_quota_interval) / self.min_dirty_quota_limit
      INFO("Recommended vCPU: %s for auto-converge" % new_vcpu)
      return new_vcpu
    return self.vcpus

  def get_revised_transfer_rate_for_autoconverge(self):
    """
    Get the revised transfer rate for autoconverge fallback
    Returns:
      new_transfer_rate(int):
    """
    INFO("Current vCPUs: %s" % self.vcpus)
    INFO("Current TRANSFER RATE: %s" % self.transfer_rate)
    INFO("Current DIRTY QUOTA PER vCPU: %s" % self.dirty_quota_per_vcpu)
    # How many vcpus we need to throttle
    if self.dirty_quota_per_vcpu >= self.min_dirty_quota_limit:
      INFO("Making %s <= %s, by changing Transfer rate"
           % (self.dirty_quota_per_vcpu,
              self.min_dirty_quota_limit))
      new_transfer_rate = (self.vcpus *
                           self.min_dirty_quota_limit) / \
                          self.dirty_quota_interval
      INFO("Recommended TRANSFER RATE for auto-converge: %s"
           % new_transfer_rate)
      return new_transfer_rate
    return self.transfer_rate

  def _read_migration_file_on_host(self, host_uuid, migration_file):
    """
    Internal method to read a migration file on given host
    Args:
      host_uuid(str):
      migration_file(str):
    Returns:
      info(list): list of dict
    """
    cluster = entities.ENTITIES.get("pe")
    host_obj = [hyp for hyp in cluster.hypervisors
                if hyp.uuid == host_uuid][0]
    INFO("Source host :%s" % host_obj.uuid)
    INFO("Migration file: %s" % migration_file)
    cmd = 'cat %s' % migration_file
    res = host_obj.execute(cmd)

    assert res["status"] == 0, "Failed to read from migrations file %s" \
                               % migration_file
    data = res["stdout"].split('\r\n')
    assert data, "Failed to find any migrations file on the host %s" % host_uuid
    data.pop()  # remove EOF entry from read file
    info = []
    for line in data:
      info.append(json.loads(line))
    assert info, "Failed to process the data in migrations file %s" \
                 % migration_file
    return info

  def _get_latest_migration_id(self):
    """
    Internal method to get latest VM migration id
    Args:
    Returns:
      id(str):
    """
    # cluster = entities.ENTITIES.get("pe")
    svm = DirtyQuotaCluster.get_acropolis_leader()
    INFO("Checking for migration id on %s" % svm.ip)
    search_str = "Adding migration UUID"
    cmd = "grep -rn %s %s | grep %s" % (search_str, const.ACROPOLIS_LOG_FILE,
                                        self.vm_uuid)
    out = svm.execute(cmd)["stdout"]
    latest_mig_id = None
    if out:
      latest_mig_id = out.strip().split('\r\n')[-1].split(
        "Adding migration UUID")[1].strip().split()[0]
    return latest_mig_id
