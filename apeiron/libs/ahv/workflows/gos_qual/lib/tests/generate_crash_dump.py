"""
Copyright (c) 2021 Nutanix Inc. All rights reserved.

Author: arundhathi.a@nutanix.com
"""
# pylint: disable=import-error, fixme
try:
  from framework.lib.nulog import INFO, ERROR, STEP  # pylint: disable=unused-import
  EXECUTOR = "nutest"
except Exception: # pylint: disable=broad-except
  from libs.ahv.framework.proxy_logging \
    import INFO, ERROR, STEP  # pylint: disable=unused-import
  EXECUTOR = "mjolnir"
from libs.ahv.workflows.gos_qual.lib.base.base \
  import BaseTest


class GenerateCrashDump(BaseTest):
  """GenerateCrashDump class"""
  NAME = "generate_crash_dump"
  TAGS = ["crash_dump"]
  POST_OPERATIONS = ["validate_crash_dump"]
  DEFAULT_PARAMS = {}

  def run(self, **params):
    """
    Run the test
    Args:
    Returns:
    """
    STEP("Generate Crash Dump")
    extra_params = params.get("extra_params")
    os = extra_params["modules"]["rpc"]
    os.generate_crash_dump()



  def teardown(self, **params):
    """
    Args:
    Returns:
    """
    pass
