"""
Copyright (c) 2022 Nutanix Inc. All rights reserved.

Author: pritam.chatterjee@nutanix.com
"""
# pylint: disable=import-error, fixme, invalid-name, arguments-differ
# pylint: disable=unused-import
import math

try:
  from framework.lib.nulog import INFO, WARN, ERROR, STEP  # pylint: disable=unused-import
  EXECUTOR = "nutest"
except Exception:  # pylint: disable=broad-except
  from libs.ahv.framework.proxy_logging \
    import INFO, ERROR, STEP  # pylint: disable=unused-import
  EXECUTOR = "mjolnir"
from libs.ahv.workflows.gos_qual.lib.base.base \
  import BaseTest
from libs.ahv.workflows.gos_qual.lib.base.gos_errors \
  import TestNotSupported


class HotAddRemoveMemory(BaseTest):
  """HotAddRemoveMemory class"""
  NAME = "hot_add_remove_mem"
  TAGS = ["memory"]
  POST_OPERATIONS = ["check_device_status"]
  DEFAULT_PARAMS = {
    "memory": 8192
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
    """
    STEP("Executing Test [%s] " % self.NAME)
    extra_params = params.get("extra_params")
    modules = extra_params.get("modules")
    vm_name = extra_params.get("vm_name")
    cache = modules.get("cache")
    vm = cache.get_entity(entity_type="rest_vm", name=vm_name)
    os = modules.get("rpc")
    acli_vm = cache.get_entity(entity_type="acli_vm", name=vm_name)
    vm_config = acli_vm.get()["config"]["boot"]
    if vm_config.get("windows_credential_guard"):
      WARN("Test [%s] is not support for credentialguard"
           % self.NAME)
      raise TestNotSupported
    self._CACHE["vm_state_before"] = vm.get()
    INFO("Adding %s memory" % params.get("memory"))
    vm.edit(**params)
    res = vm.get()
    assert params.get("memory") == res.get("memory_mb"), \
      "Failed to hot add memory via RESTv2"
    os.verify_os_boot_post_reboot(vm)
    INFO("Added memory to VM: %s, now verifying" % vm.name)
    os.bring_mem_online()
    mem = os.get_guest_memory().strip()
    mem = math.ceil(float(mem) / float(1024))
    assert mem == math.ceil(float(params.get("memory")) / float(1024)), \
      "Failed to get proper mem from guest OS Expected: [%s] " \
      "Found: [%s]" % (math.ceil(float(params.get("memory")) / float(1024)),
                       mem)
    INFO("Hot add memory completed successfully for VM: %s"
         % vm.name)

    # FIXME: Add logic to skip logic to smartly skip hot memory remove.

    INFO("Powering off VM: %s for memory cold remove as "
         "hot remove is not supported" % vm.name)
    vm.power_off()
    vm.edit(**{"memory": self._CACHE["vm_state_before"]["memory_mb"]})
    res = vm.get()
    assert self._CACHE.get("vm_state_before")["memory_mb"] \
           == res.get("memory_mb"), \
      "Failed to cold remove mem via RESTv2 Expected: [%s] " \
      "Found: [%s]" % (self._CACHE.get("vm_state_before")["memory_mb"],
                       res.get("memory_mb"))
    vm.power_on(wait_for_ip=True)
    os.verify_os_boot_post_reboot(vm)
    INFO("Removed memory from VM: %s, now verifying" % vm.name)
    mem = os.get_guest_memory().strip()
    mem = math.ceil(float(mem) / float(1024))
    assert mem == math.ceil(
      float(self._CACHE.get("vm_state_before")["memory_mb"])/float(1024)), \
      "Failed to get proper mem from guest OS Expected: [%s] " \
      "Found: [%s]" % (self._CACHE.get("vm_state_before")["memory_mb"],
                       mem)
    INFO("Cold remove memory completed successfully for VM: %s"
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
