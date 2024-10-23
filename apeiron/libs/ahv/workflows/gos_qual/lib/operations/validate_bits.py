"""
Copyright (c) 2022 Nutanix Inc. All rights reserved.

Author: pritam.chatterjee@nutanix.com
"""
# pylint: disable=import-error
try:
  from framework.lib.nulog import INFO, ERROR, WARN, DEBUG  # pylint: disable=unused-import
  EXECUTOR = "nutest"
except Exception:  # pylint: disable=broad-except
  from ahv.framework.proxy_logging import INFO, ERROR, WARN, DEBUG  # pylint: disable=unused-import
  EXECUTOR = "mjolnir"
from libs.ahv.workflows.gos_qual.lib.base.abstracts \
  import AbstractVerifier


class ValidateBits(AbstractVerifier):
  """ValidateArch"""
  def verify(self, **params):
    """
    Verify OS bits
    Args:
    Returns:
    """
    DEBUG(self)
    extra_params = params.get("extra_params")
    expected = extra_params.get("bits")
    os = extra_params["modules"]["rpc"]
    actual = os.get_os_bits()
    assert actual == expected, "Failed to validate guest OS bits " \
                               "Expected: [%s] Found: [%s]" % (expected, actual)
    extra_params["detected_bits"] = actual
