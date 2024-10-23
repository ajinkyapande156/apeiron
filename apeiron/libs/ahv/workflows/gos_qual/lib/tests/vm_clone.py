"""
Copyright (c) 2022 Nutanix Inc. All rights reserved.

Author: pritam.chatterjee@nutanix.com
"""
# pylint: disable=import-error

try:
  from framework.lib.nulog import INFO, ERROR, STEP  # pylint: disable=unused-import
  EXECUTOR = "nutest"
except Exception: # pylint: disable=broad-except
  from libs.ahv.framework.proxy_logging \
    import INFO, ERROR, STEP  # pylint: disable=unused-import
  EXECUTOR = "mjolnir"
from libs.ahv.workflows.gos_qual.lib.base.base \
  import BaseTest
from libs.ahv.workflows.gos_qual.lib.base.utilities \
  import get_os_instance


class VmClone(BaseTest):
  """VmClone class"""
  NAME = "vm_clone"
  TAGS = ["clone"]
  POST_OPERATIONS = []
  DEFAULT_PARAMS = {}

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
    rpc_v1 = modules.get("rpc_cls_v1")
    vm_clone_name = vm.name + "_clone"
    INFO("Create clone VM: %s , for VM: %s" % (vm_clone_name, vm.name))
    vm_clone = vm.clone(name=vm_clone_name)
    INFO("Power on cloned VM: %s" % vm_clone_name)
    vm_clone.power_on(wait_for_ip=True)
    vm_clone_nics = vm_clone.get_nics()
    INFO("Nics: %s" % vm_clone_nics)
    INFO("Verify if cloned VM: %s is runnning" % vm_clone_name)
    vm_clone_verified = False
    for nic in vm_clone_nics:
      INFO("Try with IP: %s" % nic["ip_address"])
      try:
        clone_os = get_os_instance(extra_params["os"])(
          conn_provider=rpc_v1(nic["ip_address"])
        )
        clone_os.verify_os_boot_post_reboot(vm_clone)
        vm_clone_verified = True
      except Exception as ex: # pylint: disable=broad-except
        ERROR("Could not boot cloned VM with IP: %s, exception: %s" \
          % (nic["ip_address"], ex))
    assert vm_clone_verified, "Cloned VM: %s could not boot up" % vm_clone_name
    INFO("Delete cloned VM: %s" % vm_clone_name)
    vm_clone.remove()

    INFO("Test [%s] successfully executed" % self.NAME)
