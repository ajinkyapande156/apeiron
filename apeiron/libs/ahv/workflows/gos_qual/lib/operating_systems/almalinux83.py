"""
Copyright (c) 2022 Nutanix Inc. All rights reserved.

Author: pritam.chatterjee@nutanix.com
"""
# pylint: disable=import-error
try:
  from framework.lib.nulog import INFO, ERROR, STEP, WARN  # pylint: disable=unused-import
  EXECUTOR = "nutest"
except Exception: # pylint: disable=broad-except
  from libs.ahv.framework.proxy_logging \
    import INFO, ERROR, STEP, WARN # pylint: disable=unused-import
  EXECUTOR = "mjolnir"
from libs.ahv.workflows.gos_qual.lib.\
  operating_systems.rhel82 import Rhel82


class AlmaLinux83(Rhel82):
  """AlmaLinux83 class"""
  pass
