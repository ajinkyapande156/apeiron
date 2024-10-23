"""
Copyright (c) 2022 Nutanix Inc. All rights reserved.

Author: pritam.chatterjee@nutanix.com
"""
# pylint: disable=arguments-differ
try:
  from framework.lib.nulog import INFO, ERROR, WARN, DEBUG  # pylint: disable=unused-import
  EXECUTOR = "nutest"
except Exception:  # pylint: disable=broad-except
  from libs.ahv.framework.proxy_logging \
    import INFO, ERROR, WARN, DEBUG  # pylint: disable=unused-import
  EXECUTOR = "mjolnir"
from libs.ahv.workflows.gos_qual.lib.base.abstracts \
  import AbstractVerifier


class CheckDeviceStatus(AbstractVerifier):
  "Validate Device Status within Guest OS"

  def verify(self, **params):
    """
    Verify and report the device status
    Args:
    Returns:
    """
    extra_params = params.get("extra_params")
    os = extra_params["modules"]["rpc"]
    stdout = os.get_errored_devices()
    assert not stdout, "Some deviced found in ERROR,DEGRADED,UNKNOWN %s" \
                       % stdout
    INFO("No devices found in ERROR,DEGRADED,UNKNOWN")
