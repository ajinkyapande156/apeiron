"""
Copyright (c) 2022 Nutanix Inc. All rights reserved.

Author: pritam.chatterjee@nutanix.com
"""
# pylint: disable=import-error

try:
  from framework.lib.nulog import INFO, ERROR, WARN, DEBUG  # pylint: disable=unused-import
  EXECUTOR = "nutest"
except Exception:  # pylint: disable=broad-except
  from libs.ahv.framework.proxy_logging \
    import INFO, ERROR, WARN, DEBUG  # pylint: disable=unused-import
  EXECUTOR = "mjolnir"
from libs.ahv.workflows.gos_qual.lib.base.abstracts \
  import AbstractVerifier


class VerifySyslog(AbstractVerifier):
  """VerifySyslog class"""
  def verify(self, **params):
    """
    Validates if there is any errors/conflicts in syslog
    Args
      guest(object): GOS guest object
    Kwargs:
    Returns:
    """
    DEBUG(self)
    INFO("Scanning syslog for errors and conflicts")
    extra_params = params.get("extra_params")
    modules = extra_params.get("modules")
    os = modules.get("rpc")
    os.verify_syslog_conflicts()
