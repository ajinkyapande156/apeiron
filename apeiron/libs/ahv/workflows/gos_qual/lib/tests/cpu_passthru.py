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


class CpuPassThru(BaseTest):
  """CpuPassThru class"""
  NAME = "cpu_passthru"
  TAGS = ["cpu"]
  POST_OPERATIONS = []
  DEFAULT_PARAMS = {}

  def run(self, **params):
    """
    Run the test
    Args:
    Returns:
    """
    pass
