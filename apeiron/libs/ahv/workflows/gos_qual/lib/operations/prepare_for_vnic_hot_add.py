"""
Copyright (c) 2021 Nutanix Inc. All rights reserved.

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


class PrepareForVnicHotAdd(AbstractVerifier):
  """PrepareForVnicHotAdd class"""
  def verify(self, **params):
    """
    Performs steps with guest OS to enable vnic hot add
    Args:
    Returns:
    """
    DEBUG(self)
    extra_params = params.get("extra_params")
    modules = extra_params.get("modules")
    os = modules.get("rpc")
    INFO("Configuring RP filter for guest OS")
    os.configure_rp_filter()
    INFO("Configuration steps completed successfully")
