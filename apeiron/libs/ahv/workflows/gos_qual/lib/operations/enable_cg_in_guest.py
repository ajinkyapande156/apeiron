"""
Copyright (c) 2023 Nutanix Inc. All rights reserved.

Author: pritam.chatterjee@nutanix.com
"""
# pylint: disable=import-error, fixme, arguments-differ
# pylint: disable=inconsistent-return-statements
import traceback
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


class EnbaleCgInGuest(AbstractVerifier):
  """EnbaleCgInGuest class"""

  def verify(self, **params):
    """
    Enbale Cg In Guest
    Args
      guest(object): GOS guest object
    Kwargs:
    Returns:
    Raises:
      PostVerificationFailed
    """
    DEBUG(self)
    extra_params = params.get("extra_params")
    modules = extra_params.get("modules")
    vm_name = extra_params.get("vm_name")
    cache = modules.get("cache")
    boot = extra_params.get("boot")
    if "credentialguard" not in boot:
      INFO("This VM does not have CG boot enabled.")
      return True
    INFO("Enabling CG Now..")
    vm = cache.get_entity(entity_type="rest_vm", name=vm_name)
    os = modules.get("rpc")
    try:
      os.enable_credential_guard()
      INFO("Performing graceful reboot within guest after enabling CG!")
      os.reboot()
      os.verify_os_boot_post_reboot(vm)
    except Exception:  # pylint: disable=broad-except
      ERROR(traceback.format_exc())
      raise PostVerificationFailed("Failed to enable CG")
