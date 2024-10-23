"""
Copyright (c) 2022 Nutanix Inc. All rights reserved.

Author: pritam.chatterjee@nutanix.com
"""
# pylint: disable=import-error, invalid-name, arguments-differ
try:
  from framework.lib.nulog import INFO, ERROR, STEP, WARN  # pylint: disable=unused-import
  EXECUTOR = "nutest"
except Exception: # pylint: disable=broad-except
  from libs.ahv.framework.proxy_logging \
    import INFO, ERROR, STEP, WARN  # pylint: disable=unused-import
  EXECUTOR = "mjolnir"
from libs.ahv.workflows.gos_qual.lib.base.base \
  import BaseTest
from libs.ahv.workflows.gos_qual.lib.base.gos_errors \
  import TestNotSupported


class HotAddRemoveVcpus(BaseTest):
  """HotAddRemoveVcpus class"""
  NAME = "hot_add_remove_vcpus"
  TAGS = ["cpu"]
  POST_OPERATIONS = ["check_device_status"]
  DEFAULT_PARAMS = {
    "vcpus": 4
  }

  def __init__(self):
    """
    Initialize any object level variables here
    Args:
    """
    self._CACHE = dict()

  def run(self, **params):
    """
    Run the test
    Args:
    Returns:
    Raises:
      TestNotSupported
    """
    STEP("Executing Test [%s] " % self.NAME)
    extra_params = params.get("extra_params")
    if extra_params.get("max_vcpus"):
      params["vcpus"] = extra_params.get("max_vcpus")
      INFO(params["vcpus"])
    modules = extra_params.get("modules")
    vm_name = extra_params.get("vm_name")
    cache = modules.get("cache")
    vm = cache.get_entity(entity_type="rest_vm", name=vm_name)
    os = modules.get("rpc")
    if not os.SUPPORTED_FEATURES["hotplug_num_vcpu"] and \
      not os.SUPPORTED_FEATURES["hotplug_num_vcpu"]:
      WARN("Test [%s] is not support for this guest OS" % self.NAME)
      raise TestNotSupported
    acli_vm = cache.get_entity(entity_type="acli_vm", name=vm_name)
    vm_config = acli_vm.get()["config"]["boot"]
    if vm_config.get("windows_credential_guard"):
      WARN("Test [%s] is not support for credentialguard"
           % self.NAME)
      raise TestNotSupported
    # if vm_config.get("windows_credential_guard"):
    #   WARN("Test [%s] is not support for this credentialguard" % self.NAME)
    #   raise TestNotSupported
    self._CACHE["vm_state_before"] = vm.get()
    INFO("Adding %s vcpus" % params.get("vcpus"))
    vm.edit(**params)
    res = vm.get()
    assert params.get("vcpus") == res.get("num_vcpus"), \
      "Failed to cold add vcpus via RESTv2 Expected: [%s] " \
      "Found: [%s]" % (params.get("vcpus"), res.get("num_vcpus"))
    vm.power_on(wait_for_ip=True)
    os.verify_os_boot_post_reboot(vm)
    INFO("Added vcpus to VM: %s, now verifying" % vm.name)
    os.bring_cpu_online()
    cpu_count = os.get_guest_cpu().strip()
    cpu_count = int(cpu_count) / res.get("num_cores_per_vcpu")
    assert cpu_count == params.get("vcpus"), \
      "Failed to get proper cpu from guest OS Expected: [%s] " \
      "Found: [%s]" % (params.get("vcpus"), cpu_count)
    INFO("Hot add vcpu completed successfully for VM: %s"
         % vm.name)

    INFO("Powering off VM: %s for vcpu cold remove as "
         "hot remove is not supported" % vm.name)
    vm.power_off()
    vm.edit(**{"vcpus": self._CACHE["vm_state_before"]["num_vcpus"]})
    res = vm.get()
    assert self._CACHE.get("vm_state_before")["num_vcpus"] \
           == res.get("num_vcpus"), \
      "Failed to cold remove vcpus via RESTv2"
    vm.power_on(wait_for_ip=True)
    os.verify_os_boot_post_reboot(vm)
    INFO("Removed vcpu from VM: %s, now verifying" % vm.name)
    cpu_count = os.get_guest_cpu().strip()
    cpu_count = \
      int(cpu_count) / self._CACHE.get("vm_state_before")["num_cores_per_vcpu"]
    assert cpu_count == self._CACHE.get("vm_state_before")["num_vcpus"], \
      "Failed to get proper cpu from guest OS Expected: [%s] " \
      "Found: [%s]" % (self._CACHE.get("vm_state_before")["num_vcpus"],
                       cpu_count)
    INFO("Cold remove vcpu completed successfully for VM: %s"
         % vm.name)

  def teardown(self, **params):
    """
    Teardown
    Args:
    Returns:
    """
    STEP("Entering teardown in test: %s" % self.NAME)
    extra_params = params.get("extra_params")
    modules = extra_params.get("modules")
    vm_name = extra_params.get("vm_name")
    cache = modules.get("cache")
    vm = cache.get_entity(entity_type="rest_vm", name=vm_name)
    os = modules.get("rpc")
    vm.power_on(wait_for_ip=True)
    os.verify_os_boot_post_reboot(vm)
