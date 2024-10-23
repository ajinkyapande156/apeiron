"""
Copyright (c) 2021 Nutanix Inc. All rights reserved.

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
from libs.ahv.workflows.gos_qual.lib.base.gos_errors \
  import PostVerificationFailed


class VerifyOsBootPostReboot(AbstractVerifier):
  """VerifyOsBoot class"""

  def verify(self, **params):
    """
    Verify if the vm has got IP during 1st boot and
    tries to write a test file into the guest OS
    Args
      guest(object): GOS guest object
    Kwargs:
      retries(int): no of retries
      interval(int): sleep between retries
    Returns:
    Raises:
      PostVerificationFailed
    """
    DEBUG(self)
    extra_params = params.get("extra_params")
    modules = extra_params.get("modules")
    vm_name = extra_params.get("vm_name")
    cache = modules.get("cache")
    vm = cache.get_entity(entity_type="rest_vm", name=vm_name)
    os = modules.get("rpc")
    INFO("Verifying if the VM booted successfully")
    try:
      return os.verify_os_boot_post_reboot(vm)
    except Exception:  # pylint: disable=broad-except
      raise PostVerificationFailed("Failed to verify OS boot")
