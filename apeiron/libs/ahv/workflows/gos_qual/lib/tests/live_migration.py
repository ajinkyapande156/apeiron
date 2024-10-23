"""
Copyright (c) 2022 Nutanix Inc. All rights reserved.

Author: pritam.chatterjee@nutanix.com
"""
# pylint: disable=import-error, invalid-name, arguments-differ, no-self-use
# pylint: disable=protected-access, unused-import
try:
  from framework.lib.nulog import INFO, ERROR, WARN, STEP
  EXECUTOR = "nutest"
except Exception: # pylint: disable=broad-except
  from libs.ahv.framework.proxy_logging \
    import INFO, ERROR, STEP, WARN  # pylint: disable=unused-import
  EXECUTOR = "mjolnir"
from libs.ahv.workflows.gos_qual.lib.base.base \
  import BaseTest
from libs.ahv.workflows.gos_qual.lib.base.gos_errors \
  import TestNotSupported
import workflows.acropolis.mjolnir.workflows.generic.vm.vm_checks as vm_checks



class LiveMigration(BaseTest):
  """LiveMigration class"""
  NAME = "live_migration"
  TAGS = ["live_migration"]
  POST_OPERATIONS = ["validate_boot_type", "validate_dq_lm",
                     "check_device_status"]
  DEFAULT_PARAMS = {
    "num_of_migrations": 1
  }
  _CACHE = None

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
    # if vm has cg enabled and system under test does not support lm of cg vm
    acli_vm = cache.get_entity(entity_type="acli_vm", name=vm_name)
    vm_config = acli_vm.get()["config"]["boot"]
    if (vm_config.get("windows_credential_guard")
        and not vm_checks.is_cg_lm_supported(vm.cluster)):
      WARN("Test [%s] is not supported on Node model/platform"
           % self.NAME)
      raise TestNotSupported
    res = vm.get()
    # check if the vm has any source host.
    # save if in the params for ValidateDqForLm to pickup
    extra_params["source_host"] = res["host_uuid"]
    os = modules.get("rpc")
    INFO("Ensure VM: %s is powered on before live migration" % vm.name)
    vm.power_on(wait_for_ip=True)
    os.verify_os_boot()
    for migration_num in range(1, params.get("num_of_migrations")+1):
      INFO("Migrating VM: %s, iteration no. %s" % (vm.name, migration_num))
      vm.migrate(live=True)
      INFO("Verify if migration of VM: %s is successful" % vm.name)
      os.verify_os_boot()
      INFO("Migration of VM: %s successful!" % vm.name)

    INFO("Test [%s] successfully executed" % self.NAME)
