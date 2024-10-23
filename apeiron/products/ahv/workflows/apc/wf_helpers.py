"""
Copyright (c) 2023 Nutanix Inc. All rights reserved.

Author: pritam.chatterjee@nutanix.com
"""
# pylint: disable=wrong-import-order, no-member, unused-variable
# pylint: disable=ungrouped-imports, no-self-use, fixme
# pylint: disable=anomalous-backslash-in-string, unused-import,
# pylint: disable=unnecessary-comprehension, unused-argument
# pylint: disable=bad-continuation, inconsistent-return-statements
# pylint: disable=too-many-locals, invalid-name, no-else-return
# pylint: disable=protected-access, useless-else-on-loop, broad-except
# pylint: disable=unexpected-keyword-arg, simplifiable-if-statement
# pylint: disable=too-many-lines
import copy
import re
import pandas as pd
import os
import random
from framework.lib.nulog import INFO, WARN, ERROR, STEP
from framework.exceptions.nutest_error import NuTestError
from framework.exceptions.interface_error import NuTestCommandExecutionError
from libs.framework import mjolnir_entities as entities
from libs.framework.mjolnir_executor import BasicExecutor
from libs.framework.mjolnir_executor import use_executor
from libs.feature.apc.factory \
  import ApcVmFactory
import workflows.acropolis.mjolnir.feature.apc.constants as const
import workflows.acropolis.mjolnir.feature.dumpxml.constants as xml_const
from libs.feature.apc.host_gateway \
  import HostGatewayInterface
from libs.feature.dirty_quota.dirty_quota_cluster \
  import DirtyQuotaCluster
from libs.feature.error_injection.cvm_error_injection \
  import ErrorCvm
from libs.feature.error_injection.host_error_injection \
  import ErrorHost
from libs.feature.node_add_remove.factory \
  import NodeAddRemoveFactory
from workflows.acropolis.upgrade.perform_ahv_aos_upgrade import \
  PerformAhvAosUpgrade
from libs.feature.dumpxml.dumpxml import DumpXml


class BaseHelper:
  """GuestHelper class"""

  def __init__(self, cluster=None):
    """
    Create object
    Args:
       cluster(object):
    Returns:
    """
    self.cluster = cluster
    self.executor = BasicExecutor(retries=3, delay=5)
    self.cluster = cluster
    self.workloads_bg = []  # used for storing bg workloads to check status
    self.gateway_inf = HostGatewayInterface()


class GuestHelper(BaseHelper):
  """GuestHelper class"""

  def guest_power_ops(self, **kwargs):
    """
    Toggle cpumodel with given api type and validate using acli, v3 and v4
    Args:
    Kwargs:
      action(str): reboot | shutdown_poweron
      expected_apc_status(str): If not provided, will do a get and note the
                                current apc status before power op compare it
                                with apc status after power op.
      expected_cpu_model(str):  If not provided, will do a get and note the
                                current cpu model before power op compare it
                                with apc status after power op.
    Returns:
    Raises:
    """
    action = kwargs.get("action", "reboot")
    api_type = kwargs.get("api_type")
    apc_vm = ApcVmFactory(api_type=api_type)

    rpc = apc_vm.is_vm_accesible(kwargs.get("vm_spec"))
    if action == "reboot":
      INFO("Rebooting..")
      rpc.run_shell_command_handsoff("reboot")
    elif action == "shutdown_poweron":
      INFO("Shuting Down..")
      rpc.run_shell_command_handsoff("shutdown")
      INFO("Powering on..")
      self.executor.execute(func=getattr(apc_vm, "update"),
                            vm_spec=kwargs.get("vm_spec"),
                            retries=1,
                            expected_result=kwargs.get("expected_result",
                                                       "Pass"))
    apc_vm.is_vm_accesible(kwargs.get("vm_spec"))
    INFO("Guest reboot is successful")

  def install_stress(self, **kwargs):
    """
    Install CPU stress tool
    Args:
    Kwargs:
    Returns:
    """
    api_type = kwargs.get("api_type")
    apc_vm = ApcVmFactory(api_type=api_type)
    # vm_uuid = kwargs.get("vm_spec").get("uuid") or kwargs.get("uuid")
    rpc = apc_vm.is_vm_accesible(kwargs.get("vm_spec"))
    cmd = "wget https://rpmfind.net/linux/fedora/linux/releases/39/" \
          "Everything/x86_64/os/Packages/s/stress-1.0.7-2.fc39.x86_64.rpm"
    rpc.run_shell_command_sync(cmd)
    cmd = "rpm -ivh stress-1.0.7-2.fc39.x86_64.rpm"
    rpc.run_shell_command_sync(cmd)

  def run_workload(self, **kwargs):
    """
    Runs given workload on given VM.
    NOTE: Manage installation seperately
    Kwargs:
      bg(bool):
    """
    workloads = {
      "cpu": self.run_cpu_workload
    }
    workload_type = kwargs.get("workload_type") or "cpu"
    workload = workloads.get(workload_type, "cpu")
    INFO("Selected workload [%s]" % workload)
    workload(**kwargs)

  def run_cpu_workload(self, **kwargs):
    """
    Runs cpu workload on given VM
    Kwargs:
      bg(bool):
    Returns:
    Raises:
    """
    api_type = kwargs.get("api_type")
    apc_vm = ApcVmFactory(api_type=api_type)
    cmd = kwargs.get("cmd", "stress --cpu 8 -v")
    # vm_uuid = kwargs.get("vm_spec").get("uuid") or kwargs.get("uuid")
    rpc = apc_vm.is_vm_accesible(kwargs.get("vm_spec"))
    task_id = rpc.run_shell_command_handsoff(cmd)
    self.workloads_bg.append(task_id)

  def check_bg_workload_status(self, **kwargs):
    """
    checks the background workload status
    Kwargs:
    Returns:
    Raises:
    """
    api_type = kwargs.get("api_type")
    apc_vm = ApcVmFactory(api_type=api_type)
    rpc = apc_vm.is_vm_accesible(kwargs.get("vm_spec"))
    for task in self.workloads_bg:
      INFO("Checking task: %s" % task)
      status, _ = rpc.query_handsoff_task_status(task)
      assert status == 1, "The workload is not running"
    INFO("All workloads are running as expected.")

  def get_cpu_flags_linux(self, **kwargs):
    """
    Check the cpu flags from linux guest OS
    Args:
    Returns:
    """
    api_type = kwargs.get("api_type")
    apc_vm = ApcVmFactory(api_type=api_type)
    csv_file = kwargs.get("dump_to_file", "flags.csv")
    spec = kwargs.get("spec")
    rpc = apc_vm.is_vm_accesible(kwargs.get("vm_spec"))
    cmd = 'cat /proc/cpuinfo | grep flags | uniq'
    _, stdout, _ = rpc.run_shell_command_sync(cmd)
    flags = stdout.split(":")[-1].strip()
    data = {
      "SPEC": [spec],
      "FLAGS": ','.join(sorted(flags.split())),
      "COUNT": len(flags.split())
    }
    df = pd.DataFrame(data)
    df.to_csv(csv_file, mode='a', header=False)
    INFO('---------------CPU_FLAGS------------------')
    INFO(df.to_string())
    INFO('---------------------------------')
    INFO("Flags added to csv file: %s" % os.path.abspath(csv_file))
    return data


class LmHelper(BaseHelper):
  """GuestHelper class"""

  def validate_lm(self, **kwargs):
    """
    Migrate a VM
    Args:
    Kwargs:
    Returns:
    """
    validate_all_hosts = kwargs.get("validate_all_hosts")
    if validate_all_hosts:
      return self.validate_lm_roundrobin(**kwargs)
    assert kwargs.get("vm_spec"), "vm_spec not provided, lm cannot be performed"
    vm_uuid = kwargs.get("vm_spec").get("uuid") or kwargs.get("uuid")
    current_host = kwargs.get("vm_spec")["host_reference"]["uuid"]

    WARN("Live Migration will be done using ACLI as v3 API is not available")
    apc_vm = ApcVmFactory(api_type="acli")
    apc_restv3_vm = ApcVmFactory(api_type="restv3_vm")
    retries = kwargs.get("retries", 1)
    delay = kwargs.get("delay", 1)
    self.executor.execute(func=apc_vm.migrate, retries=retries,
                          delay=delay,
                          **{"vm_name": vm_uuid,
                             "host": kwargs.get("target_host",
                                                None)})
    # apc_vm.migrate(**{"vm_name": vm_uuid, "host": kwargs.get("target_host",
    #                                                          None)})
    vm_spec = {"uuid": vm_uuid}
    new_host = self.executor.execute(func=apc_restv3_vm.get, retries=retries,
                                     delay=delay,
                                     vm_spec=vm_spec)["host_reference"]["uuid"]
    assert new_host != current_host, "Live migrations failed, " \
                                     "New host: [%s] == Current host: [%s]"
    INFO("Live migration successful, New host: [%s] == Current host: [%s]"
         % (current_host, new_host))

  def validate_lm_roundrobin(self, **kwargs):
    """
    Migrate a VM to all available destination hosts
    Args:
    Kwargs:
    Returns:
    """
    vm_uuid = kwargs.get("vm_spec").get("uuid") or kwargs.get("uuid")
    vm_spec = {"uuid": vm_uuid}
    WARN("Live Migration will be done using ACLI as v3 API is not available")
    apc_vm = ApcVmFactory(api_type="acli")
    apc_restv3_vm = ApcVmFactory(api_type="restv3_vm")
    retries = kwargs.get("retries", 3)
    delay = kwargs.get("delay", 5)
    current_host = \
      self.executor.execute(func=apc_restv3_vm.get, retries=retries,
                            delay=delay,
                            vm_spec=vm_spec)["host_reference"]["uuid"]
    cluster = entities.ENTITIES.get("pe")
    host_uuids = [hyp.uuid for hyp in cluster.hypervisors]
    host_uuids.remove(current_host)
    host_uuids = [current_host] + host_uuids
    n = len(host_uuids)

    @use_executor
    def validate_host(apc_vm, target_host, **kwargs):
      retries = kwargs.get("retries", 3)
      delay = kwargs.get("delay", 5)
      new_host = \
        self.executor.execute(func=apc_vm.get, retries=retries,
                              delay=delay,
                              vm_spec=vm_spec)["host_reference"]["uuid"]
      assert new_host != target_host, "Live migrations failed, " \
                                      "New host: [%s] == Current host: [%s]" \
                                      % (current_host, new_host)
      INFO("Live migration successful, New host: [%s] == Current host: [%s]"
           % (current_host, new_host))
      return new_host

    for i, host in enumerate(host_uuids):
      if i < n - 1:
        INFO("Current Host: [%s] --> Target Host [%s]" % (current_host,
                                                          host_uuids[i + 1]))
        apc_vm.migrate(**{"vm_name": vm_uuid,
                          "host": host_uuids[i + 1]})
      else:
        INFO("Current Host: [%s] --> Target Host [%s]" % (current_host,
                                                          host_uuids[
                                                            i - (n - 1)]))
        apc_vm.migrate(**{"vm_name": vm_uuid,
                          "host": host_uuids[i - (n - 1)]})
      new_host = validate_host(apc_restv3_vm, current_host, **kwargs)
      INFO("Validating if the VM is up and running")
      apc_restv3_vm.is_vm_accesible(vm_spec)
      current_host = new_host


class VmHelper(BaseHelper):
  """VmHelper class"""

  def validate_vm_create(self, **kwargs):
    """
    Validate vm create.
    Create different types of VMs are validate following:
    1. Power on
    2. Power cycle
    3.
    Args:
    Kwargs:
      cpu_model:
    Returns:
    Raises:
    """
    apc_vm = ApcVmFactory(**kwargs)
    vm_spec = self.executor.execute(func=getattr(apc_vm, "create"), **kwargs)
    if kwargs.get("power_on", True):
      response = self.executor.execute(vm_spec,
                                       func=getattr(apc_vm, "add_guest_os"),
                                       **kwargs)
      response = self.executor.execute(vm_spec,
                                       func=getattr(apc_vm, "power_on"))
      response = self.executor.execute(func=getattr(apc_vm, "get"),
                                       vm_spec=vm_spec)
      vm_rpc = self.executor.execute(response, func=getattr(apc_vm,
                                                            "is_vm_accesible"),
                                     retries=60, delay=5,
                                     expected_result="Pass")

      self.executor.execute(func=vm_rpc.get_guest_os_info)
      INFO("VM create, power-on and boot validated successfully")
    return vm_spec

  def validate_vm_clone(self, **kwargs):
    """
    Validate vm clone .
    Args:
    Kwargs:
      cpu_model:
    Returns:
    Raises:
    """
    apc_vm = ApcVmFactory(**kwargs)
    vm_spec = kwargs.get("vm_spec")
    return apc_vm.clone(vm_spec=vm_spec)

  def validate_boot_type(self, **kwargs):
    """
    Validate the VM boot type as provided
    Kwargs:
      api_type(str): Which type of interface to be used acli/restv3
      vm_uuid(str): VM uuid to be used for validating the boot type
    Raises:
    """
    vm_uuid = kwargs.get("vm_uuid")
    expected_boot_type = kwargs.get("boot_type", "UEFI")
    api_type = kwargs.get("api_type")
    apc_vm = ApcVmFactory(api_type=api_type)
    delay = kwargs.get("delay", 2)
    retries = kwargs.get("retries", 1)
    INFO("Using interface %s for boot type validation" % apc_vm)
    vm_spec = {"uuid": vm_uuid}
    # response = apc_vm.get(vm_spec=vm_spec)
    response = self.executor.execute(func=apc_vm.get, retries=retries,
                                     delay=delay,
                                     vm_spec=vm_spec)
    assert response["boot_config"]["boot_type"].lower() == expected_boot_type, \
      "Failed to validate boot type, expected: [%s] actual: [%s]" % \
      (expected_boot_type,
       response["boot_config"]["boot_type"])

  def validate_no_apc_config(self, **kwargs):
    """
    Validate the VM has not apc_config populated.
    Kwargs:
    Returns:
      True/False(bool)
    Raises:
    """
    vm_spec = kwargs.get("vm_spec")
    retries = kwargs.get("retries", 3)
    delay = kwargs.get("delay", 5)
    api_type = kwargs.get("api_type", "restv3")
    apc_vm = ApcVmFactory(api_type=api_type)
    response = self.executor.execute(func=apc_vm.get, retries=retries,
                                     delay=delay,
                                     vm_spec=vm_spec)
    assert "apc_config" in response and response["apc_config"]["enabled"] \
           is False, \
      "apc_config should be present and set to False, " \
      "but received %s" \
      % response["apc_config"]

  def validate_cpu_model_acli(self, **kwargs):
    """
    Validate the VM has cpu_model populated using acli.
    Kwargs:
    Returns:
      True/False(bool)
    Raises:
    """
    vm_spec = kwargs.get("vm_spec")
    retries = kwargs.get("retries", 3)
    delay = kwargs.get("delay", 5)
    acli_apc_vm = ApcVmFactory(api_type="acli")
    response = self.executor.execute(func=acli_apc_vm.get, retries=retries,
                                     delay=delay,
                                     vm_name=vm_spec.get("vm_name"))

    assert response.get("cpu_model"), "Expected to get cpu_model, but none " \
                                      "found"
    expected = kwargs.get("expected_cpu_model",
                          response.get("cpu_model")["name"])
    assert expected.lower() in response.get("cpu_model")["name"].lower(), \
      "CPU model is not correct in acli Expected: [%s] Actual [%s]" % \
      (expected, response.get("cpu_model")["name"])
    INFO("cpu_model validated successfully %s" % response.get("cpu_model"))
    if kwargs.get("cpu_minor_version"):
      assert kwargs.get("cpu_minor_version") in \
             response.get("cpu_model_minor_version_uuid"), \
        "Failed to compare the cpu minor version model, " \
        "expected: %s actual: %s" \
        % (kwargs.get("cpu_minor_version"),
           response.get("cpu_model_minor_version_uuid"))
      INFO("Got cpu_model_minor_version_uuid: %s"
           % response["cpu_model_minor_version_uuid"])

  def validate_no_cpu_model(self, **kwargs):
    """
    Validate the VM has no cpu_model_reference populated.
    Kwargs:
    Returns:
      True/False(bool)
    Raises:
    """
    vm_spec = kwargs.get("vm_spec")
    retries = kwargs.get("retries", 3)
    delay = kwargs.get("delay", 5)
    api_type = kwargs.get("api_type", "restv3")
    apc_vm = ApcVmFactory(api_type=api_type)
    response = self.executor.execute(func=apc_vm.get, retries=retries,
                                     delay=delay,
                                     vm_spec=vm_spec)
    assert response.get("apc_config"), "No apc_config found, " \
                                       "cannot check cpu_model_reference"
    assert not response["apc_config"].get("cpu_model_reference"), \
      "Expected no cpu_model_referenece, but received %s" \
      % response["apc_config"]["cpu_model_reference"]
    INFO("Successfully validated no cpu_model_reference %s"
         % response["apc_config"])

  def validate_no_cpu_model_acli(self, **kwargs):
    """
    Validate the VM has no cpu_model populated using acli.
    Kwargs:
    Returns:
      True/False(bool)
    Raises:
    """
    vm_spec = kwargs.get("vm_spec")
    retries = kwargs.get("retries", 3)
    delay = kwargs.get("delay", 5)
    acli_apc_vm = ApcVmFactory(api_type="acli")
    response = self.executor.execute(func=acli_apc_vm.get, retries=retries,
                                     delay=delay,
                                     vm_name=vm_spec.get("vm_name"))

    assert not response.get("cpu_model"), \
      "Expected no cpu_model, but found %s" % response.get("cpu_model")

    INFO("cpu_model validated successfully %s" % response.get("cpu_model"))

  def validate_apc_status(self, **kwargs):
    """
    Validate the VM apc status.
    Kwargs:
    Returns:
      True/False(bool)
    Raises:
    """
    vm_uuid = kwargs.get("vm_spec", {}).get("uuid") or kwargs.get("uuid")
    if kwargs.get("apc_enabled"):
      expected_apc_status = kwargs.get("apc_enabled")
    elif kwargs.get("vm_spec", {}).get("apc_config"):
      WARN("Using provided spec to get the expected apc_status")
      expected_apc_status = kwargs.get("vm_spec", {}).get("apc_config", {}). \
        get("enabled", False)
    else:
      expected_apc_status = False
    # assert expected_apc_status, \
    #   "Failed to get any expected apc status to check"
    api_type = kwargs.get("api_type", "restv3")
    apc_vm = ApcVmFactory(api_type=api_type)
    INFO("Using interface %s for apc config validation" % apc_vm)
    vm_spec = {"uuid": vm_uuid}
    # response = apc_vm.get(vm_spec=vm_spec)
    retries = kwargs.get("retries", 3)
    delay = kwargs.get("delay", 5)
    response = self.executor.execute(func=apc_vm.get, retries=retries,
                                     delay=delay,
                                     vm_spec=vm_spec)
    # apc_config should be present in any case
    assert response.get("apc_config"), "apc_config not found in vm.Get"
    # response should contain apc enabled key
    assert response["apc_config"]["enabled"] == expected_apc_status, \
      "Failed to validate apc status, expected: [%s] actual: [%s]" % \
      (expected_apc_status,
       response["apc_config"]["enabled"])
    INFO("EXPECTED APC STATUS: [%s]" % expected_apc_status)
    INFO("ACTUAL APC STATUS: [%s]" % response["apc_config"]["enabled"])
    INFO("Successfully validated")

  def validate_cpu_model(self, **kwargs):
    """
    Validate the VM cpu model
    Kwargs:
    Returns:
      True/False(bool)
    Raises:
    """
    expected_cpu_model = kwargs.get("cpu_model", self._get_default_cpu_model())
    # default model v3/UI is Broadwell
    vm_uuid = kwargs.get("vm_spec", {}).get("uuid") or kwargs.get("uuid")
    vm_spec = {"uuid": vm_uuid}
    # response = apc_vm.get(vm_spec=vm_spec)
    retries = kwargs.get("retries", 3)
    delay = kwargs.get("delay", 5)
    apc_vm = ApcVmFactory(api_type=kwargs.get("api_type", "restv3"))
    response = self.executor.execute(func=apc_vm.get, retries=retries,
                                     delay=delay,
                                     vm_spec=vm_spec)
    assert response["apc_config"]["cpu_model_reference"], \
      "cpu_model attribute is not set for the VM"
    if not expected_cpu_model:
      WARN("No expected cpu model provided, will just check if cpu_model "
           "is set")
      assert response["apc_config"]["cpu_model_reference"]["name"].lower(), \
        "CPU model is not set at all"
    else:
      assert expected_cpu_model.lower().strip() in \
             response["apc_config"]["cpu_model_reference"]["name"]. \
               lower().strip(), \
        "Failed to get proper cpu model, Expected [%s] Actual [%s]" \
        % (expected_cpu_model,
           response["apc_config"]["cpu_model_reference"]["name"])
    INFO("EXPECTED CPU MODEL: [%s]" % expected_cpu_model)
    INFO("ACTUAL CPU MODEL: [%s]"
         % response["apc_config"]["cpu_model_reference"]["name"])
    INFO("Successfully validated cpu model")
    return response

  def validate_apc_toggle(self, **kwargs):
    """
    Validate apc status toggle.
    NOTE: Does -ve validation if power_off is False.
    Kwargs:
    Returns:
      True/False(bool)
    Raises:
    """
    power_off = kwargs.get("power_off", True)
    vm_uuid = kwargs.get("vm_spec").get("uuid") or kwargs.get("uuid")
    # current_apc_state = kwargs.get("vm_spec").get("apc_config"). \
    #   get("apc_enabled")
    apc_vm = ApcVmFactory(api_type=kwargs.get("api_type", "restv3"))
    retries = kwargs.get("retries", 3)
    delay = kwargs.get("delay", 5)
    response = self.executor.execute(func=apc_vm.get, retries=retries,
                                     delay=delay,
                                     vm_spec=kwargs.get("vm_spec"))
    if not response.get("apc_config"):
      toggle = True
    elif not response.get("apc_config", {}).get("enabled"):
      toggle = True
    else:
      toggle = False
    current_apc_state = response.get("apc_config", {}).get("enabled")
    current_apc_state = response.get("apc_config", {}).get("enabled")
    if power_off:
      INFO("Powering off the VM to toggle apc_status")
      self.executor.execute(func=getattr(apc_vm, "power_off"),
                            vm_spec=kwargs.get("vm_spec"))
      assert self.is_powered_off(**kwargs)
    INFO("Toggle apc_status from [%s] --> [%s]" % (current_apc_state, toggle))
    expected_result = "Fail" if not power_off else "Pass"
    payload = copy.deepcopy(kwargs.get("vm_spec"))
    payload["uuid"] = vm_uuid
    payload["apc_config"] = {
      "enabled": toggle,
      # "cpu_model_reference": {
      #   "name": "SandyBridge",
      #   "uuid": self.cluster_helper.get_cpu_model_uuid("SandyBridge")
      # }
    }
    INFO("Adding APC CONFIG details")
    res = self.executor.execute(func=getattr(apc_vm, "update"),
                                vm_spec=payload,
                                retries=1,
                                expected_result=expected_result)
    vm_spec = {"uuid": vm_uuid}
    if power_off:
      INFO("Powering on the VM and toggle apc_status")
      self.executor.execute(func=getattr(apc_vm, "power_on"),
                            vm_spec=payload)
      assert self.is_powered_on(**kwargs)
      vm_spec["apc_enabled"] = toggle
      vm_spec["cpu_model_reference"] = {
        "name": "SandyBridge"
        # "uuid": self.cluster_helper.get_cpu_model_uuid("SandyBridge")
      }
    else:
      vm_spec["apc_enabled"] = current_apc_state
    INFO("Checking the apc_status")
    if expected_result not in ["Fail"]:
      self.validate_apc_status(**vm_spec)
      self.validate_cpu_model(**vm_spec)
    return res

  def validate_cpumodel_toggle(self, **kwargs):
    """
    Toggle cpumodel with given api type and validate using acli, v3 and v4
    Args:
    Kwargs:
      cpu_model:
    Returns:
    Raises:
    """
    power_off = kwargs.get("power_off", True)
    vm_uuid = kwargs.get("vm_spec").get("uuid") or kwargs.get("uuid")
    vm_spec = {"uuid": vm_uuid}
    retries = kwargs.get("retries", 3)
    delay = kwargs.get("delay", 5)
    apc_vm = ApcVmFactory(api_type=kwargs.get("api_type", "restv3"))
    response = self.executor.execute(func=apc_vm.get, retries=retries,
                                     delay=delay,
                                     vm_spec=vm_spec)
    apc_status = response.get("apc_config").get("enabled")
    current_cpu_model = response.get("apc_config").get("cpu_model_reference"). \
      get("name")
    expected_result = kwargs.get("expected_result", "Pass")
    new_cpu_model = kwargs.get("new_cpu_model", "Broadwell")  # default v3/UI

    if power_off:
      INFO("Powering off the VM and toggle cpu model")
      self.executor.execute(func=getattr(apc_vm, "power_off"),
                            vm_spec=kwargs.get("vm_spec"))
      assert self.is_powered_off(**kwargs)
    INFO("UPADTING CPU MODEL FROM [%s] --> [%s]" % (
      current_cpu_model, new_cpu_model))
    payload = copy.deepcopy(kwargs.get("vm_spec"))
    # FIXME: remove this section for adding cpu model
    payload["uuid"] = vm_uuid
    payload["apc_config"] = {
      "enabled": apc_status,
      "cpu_model_reference": {
        "name": self.cluster_helper.get_cpu_model_name(new_cpu_model),
        "uuid": self.cluster_helper.get_cpu_model_uuid(new_cpu_model)
      }
    }
    res = self.executor.execute(func=getattr(apc_vm, "update"),
                                vm_spec=payload,
                                retries=1,
                                expected_result=expected_result)
    if power_off:
      INFO("Powering on the VM after toggle cpu model")
      self.executor.execute(func=getattr(apc_vm, "power_on"),
                            vm_spec=payload)
      assert self.is_powered_on(**kwargs)

    if "Fail" in expected_result:
      vm_spec["apc_enabled"] = apc_status
      vm_spec["cpu_model_reference"] = {
        "name": current_cpu_model
        # "uuid": self.cluster_helper.get_cpu_model_uuid("SandyBridge")
      }
    else:
      vm_spec["apc_enabled"] = apc_status
      vm_spec["cpu_model_reference"] = {
        "name": new_cpu_model
        # "uuid": self.cluster_helper.get_cpu_model_uuid("SandyBridge")
      }
      vm_spec["cpu_model"] = new_cpu_model
    if expected_result not in ["Fail", "fail"]:
      self.validate_apc_status(**vm_spec)
      self.validate_cpu_model(**vm_spec)
    return res

  def power_ops(self, **kwargs):
    """
    Toggle cpumodel with given api type and validate using acli, v3 and v4
    Args:
    Kwargs:
      expected_apc_status(str): If not provided, will do a get and note the
                                current apc status before power op compare it
                                with apc status after power op.
      expected_cpu_model(str):  If not provided, will do a get and note the
                                current cpu model before power op compare it
                                with apc status after power op.
    Returns:
    Raises:
    """
    # expected_apc_status = kwargs.get("expected_apc_status")
    # expected_cpu_model = kwargs.get("expected_cpu_model")
    api_type = kwargs.get("api_type")
    apc_vm = ApcVmFactory(api_type=api_type)
    # vm_uuid = kwargs.get("vm_spec").get("uuid") or kwargs.get("uuid")
    INFO("Using interface %s for apc config validation" % apc_vm)

    INFO("Performing power_cycle")
    self.executor.execute(func=getattr(apc_vm, "power_off"),
                          vm_spec=kwargs.get("vm_spec"),
                          retries=5, delay=5)
    assert self.is_powered_off(**kwargs)
    self.executor.execute(func=getattr(apc_vm, "power_on"),
                          vm_spec=kwargs.get("vm_spec"),
                          retries=5, delay=5)
    assert self.is_powered_on(**kwargs)

  @use_executor
  def is_powered_off(self, **kwargs):
    """
    Validate if VM is powered off
    kwargs:
      vm_spec(dict)
    Returns:
      bool
    """
    api_type = kwargs.get("api_type")
    apc_vm = ApcVmFactory(api_type=api_type)
    retries = kwargs.get("retries", 3)
    delay = kwargs.get("delay", 5)
    response = self.executor.execute(func=apc_vm.get, retries=retries,
                                     delay=delay,
                                     vm_spec=kwargs.get("vm_spec"))
    assert response.get("power_state") == "OFF", "Failed to power_off VM"
    return True

  @use_executor
  def is_powered_on(self, **kwargs):
    """
    Validate if VM is powered on
    kwargs:
      vm_spec(dict)
    Returns:
      bool
    """
    api_type = kwargs.get("api_type")
    apc_vm = ApcVmFactory(api_type=api_type)
    retries = kwargs.get("retries", 3)
    delay = kwargs.get("delay", 5)
    response = self.executor.execute(func=apc_vm.get, retries=retries,
                                     delay=delay,
                                     vm_spec=kwargs.get("vm_spec"))
    assert response.get("power_state") == "ON", "Failed to power_on VM"
    INFO("Waiting for VM %s to be accesible"
         % kwargs.get("vm_spec").get("vm_name"))
    apc_vm.is_vm_accesible(kwargs.get("vm_spec"))
    return True

  def validate_delete_vm(self, **kwargs):
    """
    Validate if VM is deleted on
    kwargs:
    Returns:
      bool
    """
    vm_uuid = kwargs.get("vm_spec").get("uuid")
    api_type = kwargs.get("api_type")
    apc_vm = ApcVmFactory(api_type=api_type)
    retries = kwargs.get("retries", 3)
    delay = kwargs.get("delay", 5)
    self.executor.execute(vm_uuid, func=apc_vm.delete, retries=retries,
                          delay=delay,
                          )

  @use_executor
  def update_hyperv_flags_individually(self, **kwargs):
    """
    Method to disable the provided hyperv flags
    kwargs:
      hyperv_flags(dict):
    Returns:
    Raises:
    """
    hyperv_flags = kwargs.get("hyperv_flags", {})
    vm_spec = kwargs.get("vm_spec")
    if not hyperv_flags or not isinstance(hyperv_flags, dict):
      INFO("No hyperv flags provide for update, will keep default")
      hyperv_flags = {"clock": True}
    prefix = "enable_hyperv_"
    extra_flags = ""
    for flag in hyperv_flags:
      extra_flags += prefix + flag + "=" + hyperv_flags[flag] + ","
    extra_flags.rstrip(",")  # remove the last ,
    apc_vm = ApcVmFactory()
    apc_vm_acli = ApcVmFactory(api_type="acli")
    INFO("Powering off the VM and toggle hyperv extra flags individially")
    self.executor.execute(func=getattr(apc_vm, "power_off"),
                          vm_spec=kwargs.get("vm_spec"))
    assert self.is_powered_off(**kwargs), \
      "Failed to power-off vm %s" % vm_spec["vm_name"]

    res = apc_vm_acli.update(extra_flags=extra_flags,
                             vm_name=vm_spec.get("vm_name"))
    if "Hyper-V Enlightenments configuration cannot be updated" \
      in res['data'][0]:
      raise NuTestCommandExecutionError(res['data'])
    self.executor.execute(func=getattr(apc_vm, "power_on"),
                          vm_spec=kwargs.get("vm_spec"))
    assert self.is_powered_on(**kwargs), \
      "Failed to power-on vm %s" % vm_spec["vm_name"]

  def toggle_hyperv_flags(self, **kwargs):
    """
    Method to toggle disable_hyperv=true/false
    Returns:
    """
    apc_vm = ApcVmFactory()
    apc_vm_acli = ApcVmFactory(api_type="acli")
    vm_spec = kwargs.get("vm_spec")
    retries = kwargs.get("retries", 3)
    delay = kwargs.get("delay", 5)
    response = self.executor.execute(func=apc_vm_acli.get, retries=retries,
                                     delay=delay,
                                     vm_name=vm_spec.get("vm_name"))
    is_set = response.get("config").get("disable_hyperv", False)
    INFO("Powering off the VM and toggle hyperv flags")
    self.executor.execute(func=getattr(apc_vm, "power_off"),
                          vm_spec=kwargs.get("vm_spec"))
    assert self.is_powered_off(**kwargs), \
      "Failed to power-off vm %s" % vm_spec["vm_name"]
    if not is_set:
      apc_vm_acli.update(disable_hyperv="true", vm_name=vm_spec.get("vm_name"))
      kwargs["expected_hyperv_flags"] = {}
    else:
      apc_vm_acli.update(disable_hyperv="false", vm_name=vm_spec.get("vm_name"))
    INFO("Powering on the VM and toggle hyperv flags")
    self.executor.execute(func=getattr(apc_vm, "power_on"),
                          vm_spec=kwargs.get("vm_spec"))
    assert self.is_powered_on(**kwargs), \
      "Failed to power-on vm %s" % vm_spec["vm_name"]
    self.validate_hyperv_flags(**kwargs)

  def toggle_enable_metrics(self, **kwargs):
    """
    Method to toggle enable_metrics=true/false
    Returns:
    """
    apc_vm = ApcVmFactory()
    apc_vm_acli = ApcVmFactory(api_type="acli")
    vm_spec = kwargs.get("vm_spec")
    retries = kwargs.get("retries", 3)
    delay = kwargs.get("delay", 5)

    response = self.executor.execute(
      func=apc_vm_acli.get, retries=retries,
      delay=delay,
      vm_name=vm_spec.get("vm_name"))
    is_set = response.get("config").get("enable_metrics", False)
    hyperv_flags_bef = DumpXml.get_hyperv_flags(vm_uuid=vm_spec.get("uuid"))
    INFO("Powering off the VM and toggle enable_metrics")
    self.executor.execute(func=getattr(apc_vm, "power_off"),
                          vm_spec=kwargs.get("vm_spec"))
    assert self.is_powered_off(**kwargs), \
      "Failed to power-off vm %s" % vm_spec["vm_name"]
    if not is_set:
      apc_vm_acli.update(enable_metrics="true", vm_name=vm_spec.get("vm_name"))
    else:
      apc_vm_acli.update(enable_metrics="false", vm_name=vm_spec.get("vm_name"))
    INFO("Powering on the VM after toggle enable_metrics")
    self.executor.execute(func=getattr(apc_vm, "power_on"),
                          vm_spec=kwargs.get("vm_spec"))
    assert self.is_powered_on(**kwargs), \
      "Failed to power-on vm %s" % vm_spec["vm_name"]
    hyperv_flags_aft = DumpXml.get_hyperv_flags(vm_uuid=vm_spec.get("uuid"))
    assert hyperv_flags_bef == hyperv_flags_aft, \
      "Validation failed, expected: [%s] actual: [%s]" % \
      (hyperv_flags_bef, hyperv_flags_aft)
    INFO("Validation successful, expected: [%s] actual: [%s]"
         % (hyperv_flags_bef, hyperv_flags_aft))

  def validate_hyperv_flags(self, **kwargs):
    """
    Validate hyperv flags
    Args:
    Kwargs:
      vm_spec(dict):
    Returns:
    """
    expected_flags = kwargs.get("expected_hyperv_flags",
                                xml_const.DEFAULT_HYPERV_FLAGS)
    vm_spec = kwargs.get("vm_spec")
    hyperv_flags = DumpXml.get_hyperv_flags(vm_uuid=vm_spec.get("uuid"))
    assert hyperv_flags == expected_flags, \
      "Validation failed, expected: [%s] actual: [%s]" % \
      (hyperv_flags, expected_flags)
    INFO("Validation successful, expected: [%s] actual: [%s]"
         % (hyperv_flags, expected_flags))

  def _select_from_baseline(self, current_cpu_model):
    """
    Randomly select from any baseline CPU model
    Args:
      current_cpu_model(str):
    Returns:
    """
    while True:
      new_model = random.choice(self.get_baseline_cpu_models())
      if new_model != current_cpu_model:
        return str(new_model["name"])

  def _get_cpu_models(self):
    """
    Internal method to get cpu models for vendors
    Returns:
      str
    """
    vendor = self._get_cpu_vendor()
    if vendor == "Intel":
      return const.INTEL_CPU_MODELS
    else:
      return const.AMD_PROCESSOR_MODELS

  def _get_cpu_vendor(self):
    """
    Internal method to get host cpu vendor
    Returns:
      str
    """
    if "NX" in self.cluser.hypervisors[0]._model:
      return "Intel"
    elif "HPE" in self.cluser.hypervisors[0]._model:
      return "AMD"
    elif "AMD" in self.cluser.hypervisors[0]._model:
      return "AMD"
    else:
      ERROR("Unkown model: [%s]" % self.cluser.hypervisors[0]._model)
      return "Intel"


class HostHelper(BaseHelper):
  """HostHelper class"""

  def get_host_cpu_versions(self, host, cpu_model=None):
    """
    Get the cpu model versions from the host
    Args:
      host(object): nutest hypervisor object
      cpu_model(str): get the versions of a given cpu_model
    Returns:
      all_vers(list):
    Raises:
    """
    qemu_vers = self._get_cpu_model_versions(host.ip, cpu_model)
    all_host_vers = self._get_host_versions(qemu_vers)
    return all_host_vers

  def get_hosts_with_cpu_model(self, cpu_model=None):
    """
    Get the hosts with given cpu_model in the cluster
    Args:
      cpu_model(str):
    Returns:
    Returns:
      bool:
    Raises:
    """
    cpu_map = self.get_host_cpu_mapping()
    if not cpu_model:
      return list(cpu_map.keys())
    hosts = []
    for host in cpu_map:
      if self.is_model_supported(cpu_map[host], cpu_model):
        hosts.append(host)
    return hosts

  def is_model_supported(self, host_cpu_model, model_to_check):
    """
    Compares 2 cpu models
    Args:
      host_cpu_model(str):
      model_to_check(str):
    Returns:
      bool:
    Raises:
    """
    if model_to_check in self._fetch_support_cpus(host_cpu_model):
      return True
    return False

  def get_host_cpu_mapping(self):
    """
    Returns the host-wise processor model mapping
    Args:
    Returns:
      cpu_map(dict):
    Raises:
    """
    hosts = self.cluster.hypervisors
    cpu_map = {}
    for host in hosts:
      model = host.execute(
        "cat /sys/devices/cpu/caps/pmu_name")["stdout"].strip()
      cpu_map[host.uuid] = model
    return cpu_map

  def get_host_with_min_cpu(self):
    """
    Returns the host with min cpu model in cluster
    Args:
    Returns:
    Raises:
    """
    hosts = self.cluster.hypervisors
    min_host = hosts[0]

    vendor = self.cluster_helper.get_cpu_vendor()
    INFO("CPU Vendor: %s" % vendor)
    if vendor == "Intel":
      min_model = "icelake-server"
      supported_models = const.INTEL_CPU_MODELS
    else:
      min_model = "epyc-rome"
      supported_models = const.AMD_PROCESSOR_MODELS
    # total_support_models = len(supported_models)
    for host in hosts:
      data = self.gateway_inf.get_cpu_models(host.ip)["cpu_models"]
      cpu_models = [cpu_model["name"] for cpu_model in data]
      if supported_models.index(min_model.lower()) > len(cpu_models) - 1:
        min_model = supported_models[len(cpu_models) - 1]
        min_host = host
    INFO("Min cpu model: %s" % min_model)
    INFO("Min cpu host: %s" % min_host.ip)
    return min_host

  def get_host_with_max_cpu(self):
    """
    Returns the host with max cpu model in cluster
    Args:
    Returns:
    Raises:
    """
    hosts = self.cluster.hypervisors
    max_host = hosts[0]

    vendor = self.cluster_helper.get_cpu_vendor()
    INFO("CPU Vendor: %s" % vendor)
    if vendor == "Intel":
      max_model = "SandyBridge"
      supported_models = const.INTEL_CPU_MODELS
    else:
      max_model = "ROME"
      supported_models = const.AMD_PROCESSOR_MODELS
    # total_support_models = len(supported_models)
    for host in hosts:
      data = self.gateway_inf.get_cpu_models(host.ip)["cpu_models"]
      cpu_models = [cpu_model["name"] for cpu_model in data]
      if supported_models.index(max_model.lower()) < len(cpu_models) - 1:
        max_model = supported_models[len(cpu_models) - 1]
        max_host = host
    INFO("Max cpu model: %s" % max_model)
    INFO("Max cpu host: %s" % max_host.ip)
    return max_host

  def get_cpu_models_on_host(self, host_ip):
    """
    Returns all the cpu models with versions from a given host
    Args:
      host_ip(str):
    Returns:
    Raises:
    """
    cpu_data = self.gateway_inf.get_cpu_models(host_ip)
    cpu_models = []
    for model in cpu_data["cpu_models"]:
      cpu_models.append(cpu_data.get("name"))
    return cpu_models

  def restart_libvirt(self, host, **kwargs):
    """
      Initiate restart of libvirt service on host

      Args:
        host(object): Nutest host object
    """
    STEP("Restarting libvirt on host %s" % host.ip)
    self.cluster_helper.is_cluster_healthy()
    INFO("Check all hosts are schedulable")
    self.is_host_schedulable()
    INFO("Restarting libvirt on host: %s" % host.ip)
    retries = kwargs.get("retries", 25)
    delay = kwargs.get("delay", 5)
    result = host.execute("systemctl restart libvirtd")
    assert result["status"] == 0, "Service restart failed"
    service_status = self.check_service_is_active(host,
                                                  service_name="libvirtd",
                                                  retries=retries, delay=delay)
    assert service_status == "active", "Service is not active"
    self.cluster_helper.is_cluster_healthy()
    INFO("Check all hosts are schedulable")
    self.is_host_schedulable()

  def restart_gateway(self, host, **kwargs):
    """
      Initiate restart of host gateway service on host

      Args:
        host(object): Nutest host object
    """
    STEP("Restarting host gateway service on host %s" % host.ip)
    self.cluster_helper.is_cluster_healthy()
    INFO("Check all hosts are schedulable")
    self.is_host_schedulable()
    retries = kwargs.get("retries", 25)
    delay = kwargs.get("delay", 5)
    result = host.execute("systemctl restart ahv-gateway")
    assert result["status"] == 0, "Service restart failed"
    service_status = self.check_service_is_active(host,
                                                  service_name="ahv-gateway",
                                                  retries=retries, delay=delay)
    assert service_status == "active", "Service is not active"
    self.cluster_helper.is_cluster_healthy()
    INFO("Check all hosts are schedulable")
    self.is_host_schedulable()

  def restart_hostagent(self, host, **kwargs):
    """
      Initiate restart of host gateway service on host

      Args:
        host(object): Nutest host object
    """
    STEP("Restarting host gateway service on host %s" % host.ip)
    self.cluster_helper.is_cluster_healthy()
    INFO("Check all hosts are schedulable")
    self.is_host_schedulable()
    retries = kwargs.get("retries", 25)
    delay = kwargs.get("delay", 5)
    result = host.execute("systemctl restart ahv-host-agent")
    assert result["status"] == 0, "Service restart failed"
    service_status = self.check_service_is_active(host,
                                                  service_name="ahv-host-agent",
                                                  retries=retries, delay=delay)
    assert service_status == "active", "Service is not active"
    self.cluster_helper.is_cluster_healthy()
    INFO("Check all hosts are schedulable")
    self.is_host_schedulable()

  def restart_node(self, host, **kwargs):
    """
      Initiate reboot of given host

      Args:
        host(object): Nutest host object
    """
    err_host = ErrorHost()
    err_host.host_reboot(host, **kwargs)
    err_host.wait_for_host_to_recover(host, **kwargs)

  def create_vms_with_baseline(self, **kwargs):
    """
    Create VMs with support CPU models
    Args:
    Returns:
       vms_cache(list):
    """
    cpu_models = self.cluster_helper.get_baseline_cpu_models()
    INFO("Following baseline CPU models are present on the cluster: %s"
         % cpu_models)
    vms_cache = []
    for model in cpu_models:
      STEP("Creating VM with CPU model: %s" % model)
      vm_spec = {
        "vm_name": "apc_vm_%s" % model.get("name").split()[-1],
        "apc_config": {
          "enabled": True,
          "cpu_model_reference": {
            "kind": "cpu_model",
            "uuid": self.cluster_helper.get_cpu_model_uuid(model.get("name"))
          }
        },
        "cpu_model": model.get("name").split()[-1]
      }
      vm_details = self.vm_helper.validate_vm_create(**vm_spec)
      vms_cache.append(vm_details)
    return vms_cache

  def create_apc_vms_wo_cpu(self, **kwargs):
    """
    Create VMs without any apc
    Args:
    Returns:
       vms_cache(list):
    """
    vms_cache = []
    vm_spec = {
      "vm_name": "vm_with_apc_disabled",
      "apc_config": {
        "enabled": True
      }
    }
    STEP("Creating VMs with APC disabled and without APC")
    vms_cache.append(self.vm_helper.validate_vm_create(**vm_spec))
    return vms_cache

  def create_non_apc_vms(self, **kwargs):
    """
    Create VMs without any apc
    Args:
    Returns:
       vms_cache(list):
    """
    vms_cache = []
    vm_spec = {
      "vm_name": "vm_with_apc_disabled",
      "apc_config": {
        "enabled": False
      }
    }
    STEP("Creating VMs with APC disabled and without APC")
    vms_cache.append(self.vm_helper.validate_vm_create(**vm_spec))
    vm_spec = {
      "vm_name": "no_apc"
    }
    vms_cache.append(self.vm_helper.validate_vm_create(**vm_spec))
    return vms_cache

  def perform_node_remove_validations(self, **kwargs):
    """
    Node remove validations
    Args:
    Returns:
    """
    cpu_vms = kwargs.get("cpu_vms", [])
    apc_vms = kwargs.get("apc_vms", [])
    non_apc_vms = kwargs.get("non_apc_vms", [])
    cpu_vm_validations = ["validate_cpu_model_acli", "validate_cpu_model",
                          "validate_lm_roundrobin"]
    apc_vm_validations = ["validate_apc_status"]
    non_apc_vm_validations = ["validate_cpu_model_acli", "validate_cpu_model",
                              "validate_lm_roundrobin"]
    STEP("Running validations on VMs with CPU models defined")
    for vm in cpu_vms:
      INFO("Performing power-cycle on VM %s" % vm["vm_name"])
      self.power_ops(vm_spec=vm)
      for validation in cpu_vm_validations:
        STEP("Running validation [%s] on VM [%s]" % (validation,
                                                     vm["vm_name"]))
        getattr(self, validation)(**vm)

    STEP("Running validations on non APC VMs")
    for vm in non_apc_vms:
      INFO("Performing power-cycle on VM %s" % vm["vm_name"])
      self.power_ops(vm_spec=vm)
      INFO("Inserting the new baseline model for the VM to pick-up "
           "after power-cycle")
      cpu_model = self.cluster_helper.get_max_baseline_cpu_model()
      vm["cpu_model"] = cpu_model["name"].split()[-1]
      for validation in non_apc_vm_validations:
        STEP("Running validation [%s] on VM [%s]" % (validation,
                                                     vm["vm_name"]))

  def node_add_rm(self, **kwargs):
    """
      Initiate node add and remove operations
      Args:
      Retruns:
    """
    cluster = entities.ENTITIES.get("pe")
    node_handler = NodeAddRemoveFactory(cluster=cluster)
    host_min_cpu_bf = None
    try:
      STEP("Creating VMs with all supported CPU models")
      cpu_model_vms = self.create_vms_with_baseline()
      STEP("Create VM without APC and with APC set to False")
      non_apc_vms = self.create_non_apc_vms()
      STEP("Create VM with APC and no CPU models")
      apc_vms_no_cpu = self.create_apc_vms_wo_cpu()

      INFO("Finding the max CPU model from baseline CPU models")
      max_before_rm = self.cluster_helper.get_max_baseline_cpu_model()
      STEP("Max CPU baseline model before node removal is: %s" %
           max_before_rm["name"])

      INFO("Finding the host with minimum CPU model before node removal")
      host_min_cpu_bf = self.get_host_with_min_cpu()
      host_max_cpu_bf = self.get_host_with_max_cpu()
      assert not host_min_cpu_bf.ip == host_max_cpu_bf.ip, \
        "For node add remove " \
        "scenario, we need " \
        "nodes with " \
        "different CPU models"

      STEP("Host: %s has min CPU model, removing this host"
           % host_min_cpu_bf.ip)
      node_handler.remove_node(host_min_cpu_bf)

      # import pdb;
      # pdb.set_trace()
      max_after_rm = self.cluster_helper.get_max_baseline_cpu_model()
      STEP("Max CPU baseline model after node removal is: %s" %
           max_after_rm["name"])
      assert self.model_greater_than(max_after_rm["name"].split()[-1],
                                     max_before_rm["name"].split()[-1]), \
        "Max baseline CPU model should have changed % s --> %s" % (
          max_after_rm["name"],
          max_before_rm["name"]
        )
      INFO("CPU baseline model validation successful")

      INFO("Finding the host with minimum CPU model after node removal")
      host_max_cpu_bf = self.get_host_with_min_cpu()
      STEP("Host: %s has min CPU model" % host_max_cpu_bf.ip)
      vms_after_removal = []
      vm_spec = {
        "vm_name": "apc_vm_%s" % host_max_cpu_bf.get("name").split()[-1],
        "apc_config": {
          "enabled": True,
          "cpu_model_reference": {
            "kind": "cpu_model",
            "uuid": self.cluster_helper.get_cpu_model_uuid(
              host_max_cpu_bf.get("name"))
          }
        },
        "cpu_model": host_max_cpu_bf.get("name").split()[-1]
      }
      STEP("Creating VMs with max baseline mode after node removal")
      vms_after_removal.append(self.vm_helper.validate_vm_create(**vm_spec))

      # import pdb;
      # pdb.set_trace()
      node_rem = {
        "cpu_vms": cpu_model_vms,
        "apc_vms": apc_vms_no_cpu,
        "non_apc_vms": non_apc_vms
      }
      self.perform_node_remove_validations(**node_rem)

      STEP("Performing node add back: %s" % host_min_cpu_bf.ip)
      node_handler.addback_node(host_min_cpu_bf)
      host_min_cpu_bf = None
      self.perform_node_remove_validations(**node_rem)

    finally:
      if host_min_cpu_bf:
        INFO("Adding back the node % s" % host_min_cpu_bf.ip)
        node_handler.addback_node(host_min_cpu_bf)

  def aos_ahv_upgrade_handler(self, **kwargs):
    """
      Initiate aos and ahv upgrade
      Args:
      Returns:
      Raises:
    """
    cluster = entities.ENTITIES.get("pe")
    self.upgrade_handler = PerformAhvAosUpgrade(
      cluster=cluster, test_args=kwargs
    )

  @use_executor
  def check_service_is_active(self, host, service_name, **kwargs):
    """
          Check if service is active

          Args:
            host(object): host on which cmd needs to run
            service_name(str): service for which status needs to be checked

          Returns:
            status of service
    """
    cmd = "systemctl is-active %s" % service_name
    INFO("Check service status %s on host: %s" % (service_name, host.ip))
    result = host.execute(cmd, ignore_errors=True)
    return result["stdout"].strip()

  @use_executor
  def is_host_schedulable(self):
    """
    Check if all hosts are schedulable
    """
    acli = entities.ENTITIES.get("acli_vm")(name="nothing")
    cluster = entities.ENTITIES.get("pe")
    for host in cluster.hypervisors:
      host_info = acli.execute(entity="host", cmd='get %s' % host.ip)
      is_schedulable = host_info["data"][host.uuid]["schedulable"]
      INFO("Host is schedulable: %s" % is_schedulable)
      assert is_schedulable, "Host is schedulable: %s" % is_schedulable

  @staticmethod
  def _fetch_support_cpus(model):
    """
    Internal method to fetch supported cpu models for a given node.
    Args:
      model(str):
    Returns:
    Raises:
    """
    pattern = re.compile(model)
    for i, this in enumerate(const.ORDERED_PROCESSOR_MODELS):
      if re.search(pattern, this):
        return const.ORDERED_PROCESSOR_MODELS[:i + 1]

  @staticmethod
  def _get_host_versions(qemu_data):
    """
    Internal method to aggregate the host_version across qemu models.
    Args:
      qemu_data(dict):
    Returns:
      data(list):
    Raises:
    """
    host_vers = []
    for qemu_ver in qemu_data:
      for host_ver in qemu_ver["host_versions"]:
        host_vers.append(host_ver)
    return host_vers

  def _get_cpu_model_versions(self, host_ip, cpu_model):
    """
    Internal method to get the qemu versions of given model.
    Args:
      host_ip(str): IP address of Host
      cpu_model(str): CPU model name
    Returns:
      data(list):
    Raises:
    """
    INFO("Checking for %s" % cpu_model)
    cpu_data = self.gateway_inf.get_cpu_models(host_ip)["cpu_models"]
    if not cpu_model:
      return [qemu_ver for qemu_ver in cpu_data]

    # else filter
    data = [qemu_ver for qemu_ver in cpu_data
            if cpu_model in qemu_ver["name"].lower()]
    INFO("Filtered cpu models: %s" % data)
    assert len(data) >= 1, "CPU model reported by Gateway API " \
                           "should have been 1"
    data = data[0]
    return data["qemu_versions"]


class ClusterHelper(BaseHelper):
  """ClusterHelper class"""

  def is_cluster_healthy(self):
    """
    Check if cluster is healthy

    Returns:
      None
    """
    err_cvm = ErrorCvm()
    INFO("Check all CVMs are out of maintanence")
    err_cvm.wait_for_all_cvms_out_of_mm()

  def configure_apc(self, **kwargs):
    """
    Enable the gflag for APC and restart services
    Args:
    Returns:
    Raises:
    """
    cluster = entities.ENTITIES.get("pe")
    if not self.is_apc_configured():
      INFO("Configuring APC on the cluster")
      for cvm in cluster.svms:
        cmd = "echo --acropolis_enable_advanced_processor_compatibility=true " \
              ">> %s" % const.APC_GFLAG_FILE
        INFO("Enabling gflag on cvm: %s" % cvm.ip)
        cvm.execute(cmd)
      DirtyQuotaCluster.restart_acropolis()
      INFO("Configuring APC gflag completed")
    INFO("APC is already configured on cluster")

  @use_executor
  def configure_cpu_with_minor_version(self, model_id, minor_id, **kwargs):
    """
    Enable the gflag for cpu model minor version
    Args:
      model_id(str): cpu model uuid
      minor_id(str): minor version uuid
    Returns:
    Raises:
    """
    cmd1 = "links http://0:2030/h/gflags?" \
           "test_only_acropolis_cpu_model_uuid=%s" % model_id
    INFO("cmd: %s" % cmd1)
    INFO("Setting the model id glfag in cluster to: %s" % model_id)
    cmd2 = "links http://0:2030/h/gflags?" \
           "test_only_acropolis_cpu_model_minor_version_uuid=%s" % minor_id
    INFO("cmd: %s" % cmd2)
    INFO("Setting the minor version id glfag in cluster to: %s" % minor_id)
    cluster = entities.ENTITIES.get("pe")
    for cvm in cluster.svms:
      try:
        cvm.execute(cmd1, timeout=10)
      except Exception as ex:
        ERROR(ex)
        WARN("Ignoring the exception for links command..")
      try:
        cvm.execute(cmd2, timeout=10)
      except Exception as ex:
        ERROR(ex)
        WARN("Ignoring the exception for links command..")
    self.validate_cpu_minor_version(model_id, minor_id, retries=5,
                                    delay=2)

  @use_executor
  def validate_cpu_minor_version(self, model_id, minor_id):
    """
    Method to validate if gflags are set with given model and minor versions
    Args:
      model_id(str):
      minor_id(str):
    Returns:
    Raises:
    """
    cluster = entities.ENTITIES.get("pe")
    for cvm in cluster.svms:
      check1 = 'links http://0:2030/h/gflags | ' \
               'grep acropolis_cpu_model_uuid'
      out = cvm.execute(check1)
      state = out["stdout"]
      INFO(state)
      assert model_id in state, "Failed to get the required cpu model id"

      check2 = 'links http://0:2030/h/gflags | ' \
               'grep cpu_model_minor_version_uuid'
      out = cvm.execute(check2)
      state = out["stdout"]
      INFO(state)
      assert minor_id in state, "Failed to get the required cpu model " \
                                "minor version id"

  def is_apc_configured(self):
    """
    Check if APC is already configured on the cluster
    Args:
    Returns:
      configured(bool):
    """
    cluster = entities.ENTITIES.get("pe")
    configured = False
    for cvm in cluster.svms:
      cmd = 'grep "advanced_processor_compatibility" ' \
            '/home/nutanix/config/acropolis.gflags'
      try:
        cvm.execute(cmd)
      except NuTestCommandExecutionError as ex:
        if "No such file or directory" in str(ex):
          return configured
    configured = True
    return configured

  def configure_ha(self, **kwargs):
    """
    Validates HA failover with APC VM
    Args:
    Returns:
    Raises:
    """
    ha_type = kwargs.get("ha_type", "RS")
    ha_lib = entities.ENTITIES.get("rest_ha")(vlan_id=0, use_existing_vlan=True)
    if ha_type == "RS":  # reserve segment
      ha_lib.enable_reserved_segments_ha(num_host_failures_to_tolerate=1)
    elif ha_type == "RH":  # reserve host
      ha_lib.enable_reserved_host_ha(num_host_failures_to_tolerate=1)
    else:  # best effort HA
      ha_lib.enable_best_effort_ha()
    INFO("HA configured successfully.")

  def validate_ha(self, **kwargs):
    """
    Validate HA of APC VMs
    Kwargs:
      target_host(object): Nutest host object
    Returns:
    Raises:
    """
    ha_lib = entities.ENTITIES.get("rest_ha")(vlan_id=0,
                                              use_existing_vlan=True)
    target_host = kwargs.get("target_host")
    assert target_host, "Unabled to inject failure for HA, " \
                        "target_host not provided"
    ha_lib.break_libvirt_connection(target_host)
    ha_lib.wait_for_failover_complete(cutoff_usecs=kwargs.get("failover_wait",
                                                              900))
    all_vms = ha_lib.host_vms(target_host)
    ha_lib.wait_for_vms_migrated_from(all_vms,
                                      target_host.uuid)

  def restore_libvirtd(self, **kwargs):
    """
    Restore libvirtd connection to bring the cluster back to healthy state
    Kwargs:
      target_host(object): Nutest host object
    Returns:
    Raises:
    """
    ha_lib = entities.ENTITIES.get("rest_ha")(vlan_id=0,
                                              use_existing_vlan=True)
    target_host = kwargs.get("target_host")
    ha_lib.restore_libvirt_connection(target_host)

  def disable_ha(self):
    """
    Remove HA config from cluster
    Args:
    Returns:
    Raises:
    """
    ha_lib = entities.ENTITIES.get("rest_ha")(vlan_id=0,
                                              use_existing_vlan=True)
    ha_lib.disable_ha()

  def get_baseline_cpu_models(self):
    """
    Returns the baseline cpu models in the cluster
    Args:
    Returns:
    Raises:
    """
    # FIXME: Implement get list of supported cpu models api
    url = "clusters/%s/ahv_cluster_config/supported_cpu_models" \
          % self.cluster.uuid
    models = entities.ENTITIES.get("pc").send(method="get", uri=url).json()
    assert models, "No models found on cluster: %s" % models
    return models

  def model_greater_than(self, src, dst):
    """
    Compares the CPU model. If src is higher then returns then returns True
    else False
    Args:
      src(str):
      dst(str):
    Returns:
      bool
    """
    vendor = self.get_cpu_vendor()
    if vendor == "Intel":
      return self._compare_intel_cpu_models(src, dst)
    else:
      return self._compare_amd_cpu_models(src, dst)

  def get_cpu_vendor(self):
    """
    Returns the CPU vendor
    Args:
    Returns:
    Raises:
    """
    return self.get_baseline_cpu_models()[0]["vendor"]

  def get_cpu_model_name(self, cpu_model):
    """
    Returns the cpu model name by provided model name
    Args:
      cpu_model(str):
    Returns:
    Raises:
    """
    models = self.get_baseline_cpu_models()
    for model in models:
      if cpu_model.lower() in model["name"].lower():
        return model["name"]
    else:
      raise NuTestError("Model %s not found for cluster, models available: %s"
                        % (cpu_model, models))

  def get_cpu_model_uuid(self, cpu_model):
    """
    Returns the cpu uuid by model name
    Args:
      cpu_model(str):
    Returns:
    Raises:
    """
    models = self.get_baseline_cpu_models()
    for model in models:
      if cpu_model.lower() in model["name"].lower():
        return model["uuid"]
    else:
      raise NuTestError("Model %s not found for cluster, models available: %s"
                        % (cpu_model, models))

  def get_min_baseline_cpu_model(self):
    """
    Returns the minimum baseline cpu in the cluster
    Args:
    Returns:
    Raises:
    """
    return self.get_baseline_cpu_models()[0]

  def get_max_baseline_cpu_model(self):
    """
    Returns the minimum baseline cpu in the cluster
    Args:
    Returns:
    Raises:
    """
    # FIXME: Implement get list of supported cpu models api
    return self.get_baseline_cpu_models()[-1]

  def _get_default_cpu_model(self):
    """
    Returns the default CPU model if VM created with apc enabled and no
    cpu model ref provided
    Args:
    Returns:
    Raises:
    """
    vendor = self.get_cpu_vendor()
    if vendor == "Intel":
      return const.DEFAULT_v3_CPU_MODEL_INTEL
    else:
      return const.DEFAULT_v3_CPU_MODEL_AMD

  def _compare_intel_cpu_models(self, src, dst):
    """
    Compares the CPU model. If src is higher then returns then returns True
    else False
    Args:
      src(str):
      dst(str):
    Returns:
      bool
    """
    src_idx = const.INTEL_CPU_MODELS.index(src.lower())
    dst_idx = const.INTEL_CPU_MODELS.index(dst.lower())
    if src_idx > dst_idx:
      return True
    else:
      return False

  def _compare_amd_cpu_models(self, src, dst):
    """
    Compares the CPU model. If src is higher then returns then returns True
    else False
    Args:
      src(str):
      dst(str):
    Returns:
      bool
    """
    src_idx = const.AMD_PROCESSOR_MODELS.index(src.lower())
    dst_idx = const.AMD_PROCESSOR_MODELS.index(dst.lower())
    if src_idx > dst_idx:
      return True
    else:
      return False


# Main interface to this module. DONOT consume other classes directly
class ApcWfHelper(VmHelper, GuestHelper, LmHelper, HostHelper, ClusterHelper):
  """ApcWfHelper class"""

  def __init__(self, **kwargs):
    """
    Create ApcWfHelper Mixin object
    """
    super(ApcWfHelper, self).__init__(**kwargs)
    self.lm_helper = LmHelper(**kwargs)
    self.cluster_helper = ClusterHelper(**kwargs)
    self.host_helper = HostHelper(**kwargs)
    self.vm_helper = VmHelper(**kwargs)
    self.guest_helper = GuestHelper(**kwargs)
