"""
Copyright (c) 2022 Nutanix Inc. All rights reserved.

Author: pritam.chatterjee@nutanix.com
"""
# pylint: disable=import-error, unused-import
try:
  from framework.lib.nulog import INFO, ERROR, STEP, \
    WARN
  EXECUTOR = "nutest"
except Exception:  # pylint: disable=broad-except
  from libs.ahv.framework.proxy_logging \
    import INFO, ERROR, STEP, WARN
  EXECUTOR = "mjolnir"
from libs.ahv.workflows.gos_qual.lib.operating_systems. \
  default import Default


class Solaris114(Default):
  """Solaris114 class"""
  pass

