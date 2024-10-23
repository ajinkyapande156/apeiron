"""
Copyright (c) 2022 Nutanix Inc. All rights reserved.

Author: arundhathi.a@nutanix.com
"""
# pylint: disable=import-error

try:
  from framework.lib.nulog import INFO, ERROR, STEP  # pylint: disable=unused-import
  EXECUTOR = "nutest"
except Exception:  # pylint: disable=broad-except
  from libs.ahv.framework.proxy_logging \
    import INFO, ERROR, STEP  # pylint: disable=unused-import
  EXECUTOR = "mjolnir"
from libs.ahv.workflows.gos_qual.lib.base.base \
  import BaseTest
from libs.ahv.workflows.gos_qual.lib.\
  operations.it_mitigation import ItMitigationStateCheck


class CheckITMitigationState(BaseTest):
  """Check state of itlb-multihit-mitigation"""
  NAME = "itlb-multihit-mitigation"
  TAGS = [""]
  POST_OPERATIONS = ["verify_os_boot"]
  DEFAULT_PARAMS = {
  }

  @classmethod
  def run(cls, **params):
    """
    Run the test
    Args:
    Returns:
    """
    STEP("Executing Test [%s] " % cls.NAME)
    extra_params = params.get("extra_params")
    modules = extra_params.get("modules")
    vm_name = extra_params.get("vm_name")
    cache = modules.get("cache")
    vm = cache.get_entity(entity_type="rest_vm", name=vm_name)
    it_mitigation = ItMitigationStateCheck(vm.cluster)
    STEP("Check IT Mitigation state")
    status = it_mitigation.get_default_state_for_aos_version()
    it_mitigation.validate_it_mitigation(state=status)


  @classmethod
  def teardown(cls, **params):
    """
    Teardown
    Args:
    Returns:
    """
    pass
