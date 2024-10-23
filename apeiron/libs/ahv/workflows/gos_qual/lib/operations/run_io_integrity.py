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


class VerifyIOIntegrity(AbstractVerifier):
  """VerifyIOIntegrity class"""

  def verify(self, **params):
    """
    Run IOIntegrity
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
    INFO("Run IO integrity on VM")
    file_size_gb = 2
    time_limit_secs = 40
    try:
      os.install_fio()
      os.reboot()
      os.verify_os_boot_post_reboot(vm)
      boot_disk = os.get_boot_disk()
      INFO("Detected book disk %s" % boot_disk)
      drives = os.get_disk_drives()
      INFO("Detected disks attached to VM %s" % drives)
      os.set_disk_online()
      for drive in drives:
        if boot_disk not in drive:
          os.run_io_integrity(vdisk_file=drive,
                              file_size_gb=file_size_gb,
                              time_limit_secs=time_limit_secs)
      return True
    except Exception:  # pylint: disable=broad-except
      ERROR(traceback.format_exc())
      raise PostVerificationFailed("IO integrity failed ")
