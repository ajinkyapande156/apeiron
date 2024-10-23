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
from libs.ahv.workflows.gos_qual.lib.base.abstracts \
  import AbstractVerifier
from libs.ahv.workflows.gos_qual.lib.base.gos_errors \
  import PostVerificationFailed


class PrepareRhcertLTS(AbstractVerifier):
  """PrepareRhcertLTS class"""
  def verify(self, **params):
    """
    Prepare an RHEL system as LTS for running rhel certification tool
    Args:
    Kwargs:
    Returns:
    """
    DEBUG(self)
    extra_params = params.get("extra_params")
    modules = extra_params.get("modules")
    os = modules.get("rpc")
    INFO("Enabling subscription for RHEL systems")
    try:
      os.enable_subscription()
      os.enable_kernel_debuginfo_repo()
      os.enable_rhcert_repo()
      os.install_rhcert_packages()
      os.start_rhcertd_service()
    except:  # pylint: disable=broad-except
      raise PostVerificationFailed("Failed to prepare for Redhat certification")
