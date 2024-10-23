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


class ValidateArch(AbstractVerifier):
  """ValidateArch"""
  def verify(self, **params):
    """
    Verify OS architecture
    Args:
    Returns:
    """
    DEBUG(self)
    extra_params = params.get("extra_params")
    expected = extra_params.get("arch")
    os = extra_params["modules"]["rpc"]
    actual = os.get_os_architecture()
    assert actual == expected, "Failed to validate guest OS arch " \
                               "Expected: [%s] Found: [%s]" % (expected, actual)
    extra_params["detected_arch"] = actual
