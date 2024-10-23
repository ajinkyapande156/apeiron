"""
Copyright (c) 2021 Nutanix Inc. All rights reserved.

Author: arundhathi.a@nutanix.com
"""
# pylint: disable=import-error, fixme
try:
  from framework.lib.nulog import INFO, ERROR, STEP  # pylint: disable=unused-import
  EXECUTOR = "nutest"
except Exception: # pylint: disable=broad-except
  from libs.ahv.framework.proxy_logging \
    import INFO, ERROR, STEP  # pylint: disable=unused-import
  EXECUTOR = "mjolnir"
from libs.ahv.workflows.gos_qual.lib.base.base \
  import BaseTest


class VirtioDriverUpgrade(BaseTest):
  """CdromLegacyBoot class"""
  NAME = "virtio_driver_upgrade",
  TAGS = ["virtio"]
  POST_OPERATIONS = ["validate_virtio_drivers", "verify_os_boot"]
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
    #Install via MSI
    vm.power_on(wait_for_ip=True)
    os.verify_os_boot_post_reboot(vm)
    os.install_virtio_driver_msi()
    os.reboot()
    os.verify_os_boot_post_reboot(vm)
    os.restart_service()
