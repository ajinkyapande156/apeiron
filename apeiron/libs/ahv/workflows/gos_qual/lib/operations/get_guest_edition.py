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
from libs.ahv.workflows.gos_qual.lib.base.gos_errors \
  import PostVerificationFailed


class VerifyGuestEdition(AbstractVerifier):
  """VerifyGuestEdition class"""
  def verify(self, **params):
    """
    Gets the edition of the guest like server/desktop/home etc
    Args
      guest(object): GOS guest object
    Kwargs:
      retries(int): no of retries
      interval(int): sleep between retries
    Returns:
    """
    DEBUG(self)
    extra_params = params.get("extra_params")
    modules = extra_params.get("modules")
    os = modules.get("rpc")
    try:
      edition = os.get_edition_info()
      extra_params["edition"] = str(edition)
      INFO("Detected edition: %s" % edition)
    except Exception:  # pylint: disable=broad-except
      PostVerificationFailed("Failed to setup RPC on guest VM")
