"""
Copyright (c) 2022 Nutanix Inc. All rights reserved.

Author: arundhathi.a@nutanix.com
"""
# pylint: disable=import-error, fixme
try:
  from framework.lib.nulog import INFO, ERROR, WARN, DEBUG  # pylint: disable=unused-import
  EXECUTOR = "nutest"
except Exception:  # pylint: disable=broad-except
  from libs.ahv.framework.proxy_logging \
    import INFO, ERROR, WARN, DEBUG  # pylint: disable=unused-import
  EXECUTOR = "mjolnir"
from libs.ahv.workflows.gos_qual.lib.base.abstracts \
  import AbstractVerifier


class ValidateCrashDump(AbstractVerifier):
  """ValidateCrashDump"""
  def verify(self, **params):
    """
    Verify OS gpu
    Args:
    Returns:
    """
    extra_params = params.get("extra_params")
    os = extra_params["modules"]["rpc"]
    os.install_windbg()
    os.open_crash_dump()

