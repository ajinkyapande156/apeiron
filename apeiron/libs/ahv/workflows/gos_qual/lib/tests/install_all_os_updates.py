"""
Copyright (c) 2022 Nutanix Inc. All rights reserved.

Author: pritam.chatterjee@nutanix.com
"""
# pylint: disable=import-error, arguments-differ
try:
  from framework.lib.nulog import INFO, ERROR, STEP  # pylint: disable=unused-import
  EXECUTOR = "nutest"
except Exception: # pylint: disable=broad-except
  from libs.ahv.framework.proxy_logging \
    import INFO, ERROR, STEP  # pylint: disable=unused-import
  EXECUTOR = "mjolnir"
from libs.ahv.workflows.gos_qual.lib.base.base \
  import BaseTest


class InstallAllOsUpdates(BaseTest):
  """InstallAllOsUpdates class"""
  NAME = "install_os_updates"
  TAGS = [""]
  POST_OPERATIONS = ["validate_boot_type_in_guest",
                     "check_device_status"]
  DEFAULT_PARAMS = {}

  def run(self, **params):
    """
    Run the test
    Args:
    Returns:
    """
    STEP("Executing Test [%s]" % self.NAME)
    extra_params = params.get("extra_params")
    modules = extra_params.get("modules")
    rpc = modules.get("rpc")
    vm = modules.get("rest_vm")
    current_version = rpc.get_build_info()
    INFO("Version before OS update: %s" % current_version)
    if extra_params["vendor"] not in ["microsoft"]:
      rpc.install_os_updates(vm)
    else:
      rpc.install_all_os_updates(vm)
    updated_version = rpc.get_build_info()
    INFO("Version after OS updates: %s" % updated_version)
    extra_params["upgraded_build"] = updated_version
