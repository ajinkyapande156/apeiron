"""
Copyright (c) 2021 Nutanix Inc. All rights reserved.

Author: arundhathi.a@nutanix.com
"""
# pylint: disable=useless-import-alias, arguments-differ
from framework.lib.utils.version import Version
# pylint: disable=import-error, fixme
# pylint: disable=too-many-locals
try:
  from framework.lib.nulog import INFO, ERROR, STEP  # pylint: disable=unused-import
  EXECUTOR = "nutest"
except Exception: # pylint: disable=broad-except
  from libs.ahv.framework.proxy_logging \
    import INFO, ERROR, STEP  # pylint: disable=unused-import
  EXECUTOR = "mjolnir"
from libs.ahv.workflows.gos_qual.lib.base.base \
  import BaseTest
from libs.ahv.workflows.gos_qual.configs \
  import constants as constants

class VirtioDriverUpgradePnputil(BaseTest):
  """CdromLegacyBoot class"""
  NAME = "virtio_driver_upgrade_pnputil"
  TAGS = ["virtio"]
  POST_OPERATIONS = ["validate_virtio_drivers", "verify_os_boot",
                     "check_device_status"]
  DEFAULT_PARAMS = {
  }

  def run(self, **params):
    """
    Run the test
    Args:
    Returns:
    """
    STEP("Executing Test [%s] with boot disk [%s]"
         % (self.NAME,
            params.get("boot_disk_type")))
    extra_params = params.get("extra_params")
    modules = extra_params.get("modules")
    vm_name = extra_params.get("vm_name")
    cache = modules.get("cache")
    vm = cache.get_entity(entity_type="rest_vm", name=vm_name)
    image = cache.get_entity(entity_type="rest_image", name="image")
    ctr = modules.get("rest_ctr")
    os = modules.get("rpc")
    virtio_driver_upgrade_iso = params.get("virtio_upgrade_path")
    virtio_version = os.get_installer_version(virtio_driver_upgrade_iso)
    INFO("Upgrading Virtio driver on vm: %s" % extra_params.get("vm_name"))
    vm.power_off()
    INFO("Uploading virtio image: %s for vm: %s"
         % (virtio_driver_upgrade_iso, extra_params.get("vm_name")))
    ks_iso_id = image.upload_image(extra_params.get("vm_name") +
                                   "_VIRTIOUPGRADE_" + virtio_version,
                                   virtio_driver_upgrade_iso, "ISO_IMAGE")[1]
    INFO("Mounting virtio image to CDROM: %s" % virtio_driver_upgrade_iso)
    vm.add_disk(is_cdrom=True, is_empty=False,
                disk_type="SATA",
                clone_container_uuid=ctr.entity_uuid,
                clone_from_vmdisk=ks_iso_id)
    INFO("Mounted virtio image to cdrom")
    #Install via PNPUTIL
    vm.power_on(wait_for_ip=True)
    os.verify_os_boot()
    os_name = extra_params["os"]
    driver_path = "D:\\%s\\%s\\" % (constants.DRIVER_PATH[os_name],
                                    constants.AMD64)
    virtio_drivers = constants.VIRTIO_DRIVERS
    if Version(virtio_version) > Version(constants.VIRTIO_120):
      driver_path = "D:\\%s\\%s\\" % (constants.DRIVER_PATH[os_name],
                                      constants.X64)
      virtio_drivers = constants.VIRTIO_DRIVERS_121
    os.install_virtio_pnputil(driver_path=driver_path,
                              driver_list=virtio_drivers)
    os.reboot()
    os.verify_os_boot_post_reboot(vm)
    os.restart_service()
