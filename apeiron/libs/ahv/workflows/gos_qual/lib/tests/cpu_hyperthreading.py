"""
Copyright (c) 2022 Nutanix Inc. All rights reserved.

Author: pritam.chatterjee@nutanix.com
"""
# pylint: disable=import-error, invalid-name
import time

try:
  from framework.lib.nulog import INFO, ERROR, STEP  # pylint: disable=unused-import
  EXECUTOR = "nutest"
except Exception:  # pylint: disable=broad-except
  from libs.ahv.framework.proxy_logging \
    import INFO, ERROR, STEP  # pylint: disable=unused-import
  EXECUTOR = "mjolnir"
from libs.ahv.workflows.gos_qual.lib.base.base \
  import BaseTest


class CpuHyperThreading(BaseTest):
  """CpuHyperThreading class"""
  NAME = "cpu_hyperthreading"
  TAGS = ["cpu"]
  POST_OPERATIONS = []
  DEFAULT_PARAMS = {
    "num_threads_per_core": 2
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
    acli_vm = cache.get_entity(entity_type="acli_vm", name=vm_name)
    os = modules.get("rpc")
    # import pdb;
    # pdb.set_trace()
    acli_vm.create(bind=True,
                   validate=True,
                   name=extra_params.get("vm_name")
                  )
    INFO("Powering off the VM: %s for enabling hyperthreading" % acli_vm.name)
    vm.power_off()
    acli_vm.edit(**{"num_threads_per_core": params.get("num_threads_per_core")})
    vm.power_on(wait_for_ip=True)
    os.verify_os_boot_post_reboot(vm)
    retry = 12
    interval = 5
    while retry:
      threads = os.get_threads_per_core()
      try:
        assert threads == params.get("num_threads_per_core"), \
          "num_of_threads_per_core not match with guest Expected: %s " \
          "Found: %s" % (params.get("num_threads_per_core"),
                         threads)
        break
      except AssertionError:
        retry = retry - 1
        INFO("Retrying after %s sec" % interval)
        time.sleep(interval)
    INFO("Test [%s] completed successfully" % self.NAME)

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
    acli_vm = cache.get_entity(entity_type="acli_vm", name=vm_name)
    os = modules.get("rpc")
    vm.power_on(wait_for_ip=True)
    os.verify_os_boot_post_reboot(vm)
    INFO("Reverting cpu hyperthreading now")
    vm.power_off()
    acli_vm.edit(**{"num_threads_per_core": 1})
    vm.power_on(wait_for_ip=True)
    os.verify_os_boot_post_reboot(vm)
