"""
Copyright (c) 2022 Nutanix Inc. All rights reserved.

Author: pritam.chatterjee@nutanix.com
"""
# pylint: disable=import-error, invalid-name, unused-import, arguments-differ
try:
  from framework.lib.nulog import INFO, ERROR, STEP  # pylint: disable=unused-import
  EXECUTOR = "nutest"
except Exception:  # pylint: disable=broad-except
  from libs.ahv.framework.proxy_logging \
    import INFO, ERROR, STEP  # pylint: disable=unused-import
  EXECUTOR = "mjolnir"
from libs.ahv.workflows.gos_qual.lib.base.base \
  import BaseTest


class ColdAddRemoveCores(BaseTest):
  """ColdAddRemoveCores class"""
  NAME = "cold_add_remove_cores"
  TAGS = ["cpu"]
  POST_OPERATIONS = ["check_device_status"]
  DEFAULT_PARAMS = {
    "cores_per_vcpu": 4
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
    """
    STEP("Executing Test [%s] " % self.NAME)
    extra_params = params.get("extra_params")
    modules = extra_params.get("modules")
    vm_name = extra_params.get("vm_name")
    cache = modules.get("cache")
    vm = cache.get_entity(entity_type="rest_vm", name=vm_name)
    os = modules.get("rpc")
    self._CACHE["vm_state_before"] = vm.get()
    INFO("Powering off VM: %s for cores cold add" % vm.name)
    vm.power_off()
    INFO("Adding %s core" % params.get("cores_per_vcpu"))
    vm.edit(**params)
    res = vm.get()
    assert params.get("cores_per_vcpu") == res.get("num_cores_per_vcpu"), \
      "Failed to cold add cores via RESTv2 Expected: [%s] " \
      "Found: [%s]" % (params.get("cores_per_vcpu"),
                       res.get("num_cores_per_vcpu"))
    vm.power_on(wait_for_ip=True)
    os.verify_os_boot_post_reboot(vm)
    INFO("Added cores to VM: %s, now verifying" % vm.name)
    cores = os.get_guest_cpu().strip()
    cores = int(cores) / res.get("num_vcpus")
    assert cores == params.get("cores_per_vcpu"), \
      "Failed to get proper cores from guest OS Expected: [%s]" \
      " Found: [%s]" % (params.get("cores_per_vcpu"), cores)
    INFO("Cold add cores completed successfully for VM: %s"
         % vm.name)

    INFO("Powering off VM: %s for cores cold remove" % vm.name)
    vm.power_off()
    vm.edit(**{"cores_per_vcpu":
                 self._CACHE["vm_state_before"]["num_cores_per_vcpu"]})
    res = vm.get()
    assert self._CACHE.get("vm_state_before")["num_cores_per_vcpu"] \
           == res.get("num_cores_per_vcpu"), \
      "Failed to cold remove cores via RESTv2 Expected: [%s]" \
      " Found: [%s]" % \
      (self._CACHE.get("vm_state_before")["num_cores_per_vcpu"],
       res.get("num_cores_per_vcpu"))
    vm.power_on(wait_for_ip=True)
    os.verify_os_boot_post_reboot(vm)
    INFO("Removed cores from VM: %s, now verifying" % vm.name)
    cores = os.get_guest_cpu().strip()
    cores = int(cores) / self._CACHE.get("vm_state_before")["num_vcpus"]
    assert cores == \
           self._CACHE.get("vm_state_before")["num_cores_per_vcpu"], \
      "Failed to get proper cores from guest OS Expected: [%s]" \
      " Found: [%s]" % \
      (self._CACHE.get("vm_state_before")["num_cores_per_vcpu"],
       cores)
    INFO("Cold add cores completed successfully for VM: %s"
         % vm.name)

  def teardown(self, **params):
    """
    Teardown
    Args:
    Returns:
    """
    extra_params = params.get("extra_params")
    modules = extra_params.get("modules")
    vm_name = extra_params.get("vm_name")
    cache = modules.get("cache")
    vm = cache.get_entity(entity_type="rest_vm", name=vm_name)
    os = modules.get("rpc")
    vm.power_on(wait_for_ip=True)
    os.verify_os_boot_post_reboot(vm)
  #   vm.edit(**self._CACHE)
  #   assert params.get("vcpus") == res.get("num_vcpus"), \
  #     "Failed to update vcpus"
