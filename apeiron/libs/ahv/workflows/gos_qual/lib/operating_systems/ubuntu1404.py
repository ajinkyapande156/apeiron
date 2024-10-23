"""
Copyright (c) 2021 Nutanix Inc. All rights reserved.

Author: pritam.chatterjee@nutanix.com
"""
# pylint: disable=import-error, unused-import
try:
  from framework.lib.nulog import INFO, ERROR, STEP, WARN  # pylint: disable=unused-import
  EXECUTOR = "nutest"
except Exception: # pylint: disable=broad-except
  from libs.ahv.framework.proxy_logging import \
    INFO, ERROR, STEP, WARN
  EXECUTOR = "mjolnir"
from libs.ahv.workflows.gos_qual.lib.operating_systems.\
  debian100 import Debian100


class Ubuntu1404(Debian100):
  """Ubuntu14.04 class"""
  pass
