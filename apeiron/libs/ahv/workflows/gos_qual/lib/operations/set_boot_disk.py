"""
Copyright (c) 2021 Nutanix Inc. All rights reserved.

Author: pritam.chatterjee@nutanix.com
"""
# pylint: disable=import-error, fixme
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


class SetBootDisk(AbstractVerifier):
  """SetBootDisk class"""

  def verify(self, **params):
    """
    Set boot disk
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
    vm = cache.get_entity(entity_type="rest_vm", name=vm_name)
    os = modules.get("rpc")
    try:
      vm.power_off()
      INFO("Setting boot disk: %s" % params.get("boot_disk_type"))
      vm.edit(boot_device_type="DISK", device_bus=params.get("boot_disk_type"),
              device_index=0)
      vm.power_on(wait_for_ip=True)
      return os.verify_os_boot_post_reboot(vm)
    except Exception:  # pylint: disable=broad-except
      ERROR(traceback.format_exc())
      raise PostVerificationFailed("Failed to set boot disk")
