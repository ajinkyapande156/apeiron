"""
Copyright (c) 2022 Nutanix Inc. All rights reserved.

Author: pritam.chatterjee@nutanix.com
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


class ValidateGpu(AbstractVerifier):
  """ValidateArch"""
  def verify(self, **params):
    """
    Verify OS gpu
    Args:
    Returns:
    """
    DEBUG(self)
    extra_params = params.get("extra_params")
    # os = extra_params["modules"]["rpc"]
    # expected = extra_params.get("graphics")
    # FIXME: Add support for GPU validation
    extra_params["detected_graphics"] = "no-gpu"
    extra_params["graphics_details"] = "NA"
