"""
Copyright (c) 2021 Nutanix Inc. All rights reserved.

Author: pritam.chatterjee@nutanix.com
"""
# pylint: disable=import-error, fixme, arguments-differ
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



class VerifyOsBoot(AbstractVerifier):
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
    # vm = modules.get("rest_vm")
    os = modules.get("rpc")
    INFO("Verifying if the VM booted successfully")
    try:
      os.verify_os_boot(vm=vm)
      os.apply_os_workaround()
      INFO("VM boot was successful, "
           "now powering off VM for "
           "removing cdroms added for installation")
      # FIXME: Nutest hides any way to eject the cdrom
      #        Need to implement eject in operatingsystem
      #        class
      # Add a sleep for 30 sec if OS is windows
      vm.shutdown()
      for cdrom in [disk for disk in vm.get_disks()
                    if disk.is_cdrom]:
        INFO("Deleting cdrom: %s" % cdrom.uuid)
        vm.delete_disk(
          disk_type=cdrom.bus,
          device_index=cdrom.index,
          vmdisk_uuid=cdrom.uuid
        )
      vm.power_on(wait_for_ip=True)
      return os.verify_os_boot_post_reboot(vm)
    except Exception:  # pylint: disable=broad-except
      ERROR(traceback.format_exc())
      raise PostVerificationFailed("OS boot was not successful after 30mins")
