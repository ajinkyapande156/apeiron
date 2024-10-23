"""
Copyright (c) 2021 Nutanix Inc. All rights reserved.

Author: pritam.chatterjee@nutanix.com
"""
import re
import threading

# from threading import threading.Lock

# pylint: disable=import-error, fixme, protected-access
# pylint: disable=unused-variable
# pylint: disable=too-many-statements
# pylint: disable=too-many-locals, useless-import-alias, arguments-differ
# pylint: disable=inconsistent-return-statements
try:
  from framework.lib.nulog import INFO, ERROR, \
    STEP  # pylint: disable=unused-import
  # from framework.lib.nulog import add_custom_log_file as add_custom_log_file

  EXECUTOR = "nutest"
except Exception:  # pylint: disable=broad-except
  from libs.ahv.framework.proxy_logging \
    import INFO, ERROR, STEP  # pylint: disable=unused-import

  EXECUTOR = "mjolnir"
from libs.ahv.workflows.gos_qual.lib.base.base \
  import BaseTest
from libs.ahv.workflows.gos_qual.configs \
  import constants as constants


class CdromLegacyBoot(BaseTest):
  """CdromLegacyBoot class"""
  NAME = "cdrom_legacy_boot"
  TAGS = ["boot", "legacy", "cdrom"]
  POST_OPERATIONS = ["setup_rpc",
                     "verify_os_boot",
                     "set_boot_disk",
                     "validate_virtio_drivers",
                     "get_guest_build", "get_guest_edition",
                     "validate_arch", "validate_bits",
                     "validate_gpu", "validate_boot_type_on_vm",
                     "validate_boot_type_in_guest",
                     "check_device_status",
                     "prepare_for_vnic_hot_add"
                     ]
  DEFAULT_PARAMS = {
    "memory": 2048,
    "vcpus": 2,
    "cores_per_vcpu": 1,
    "boot_disk_size": 80000,
    "boot_disk_type": "SCSI",
    "cdrom_bus_type": "SATA",
    "uefi": False,
  }

  def run(self, **params):
    """
    Run the test
    Args:
    Returns:
    """
    extra_params = params.get("extra_params")
    vm_name = extra_params.get("vm_name")
    # thread_name = threading.currentThread().getName() + " :"
    # add_custom_log_file(vm_name + ".log", lambda x: thread_name in x.msg)

    STEP("Executing Test [%s] with boot disk [%s]"
         % (self.NAME,
            params.get("boot_disk_type")))
    if extra_params.get("vcpus"):
      params["vcpus"] = extra_params.get("vcpus")
    modules = extra_params.get("modules")
    # images = extra_params.get("images")
    vm_cls = modules.get("rest_vm")
    image_cls = modules.get("rest_image")
    nw_cls = modules.get("rest_nw")
    ctr = modules.get("rest_ctr")
    vm = vm_cls(interface_type="REST", name=vm_name)
    acli_cls = modules.get("acli_vm")
    acli_vm = acli_cls(interface_type="ACLI", name=vm_name)
    nw = nw_cls(interface_type="REST", name="network")
    img_lock = modules.get("img_upload_lock")
    with img_lock:
      INFO("Defining/Checking Image Upload control for Execution threads")
      my_signature = extra_params.get("os") + "_" + \
                     extra_params.get("type") + "_legacy"
      if params.get("oemdrv"):
        version = re.search(r"[\d+\.\d+]",
                            extra_params.get("os"))
        # NOTE: This could cause failure in OS install if rhel9 differs
        # from oel9, centos_stream9 etc
        oemdrv_signature = "OEMDRV_" + version.group(0)
        if oemdrv_signature not in constants.IMAGE_UPLOAD_SYNC_CACHE:
          constants.IMAGE_UPLOAD_SYNC_CACHE[oemdrv_signature] = threading.Lock()
          INFO(
            "Image upload cache entry added [%s] by: [%s]" % (oemdrv_signature,
                                                              vm_name))
      elif params.get("virtio"):
        version = re.search(r"Nutanix-VirtIO-(\d\.\d\.\d)\.iso",
                            params.get("virtio"))
        virtio_version = version.group(1)
        virtio_signature = "VIRTIO_" + virtio_version
        if virtio_signature not in constants.IMAGE_UPLOAD_SYNC_CACHE:
          constants.IMAGE_UPLOAD_SYNC_CACHE[virtio_signature] = threading.Lock()
          INFO(
            "Image upload cache entry added [%s] by: [%s]" % (virtio_signature,
                                                              vm_name))
    if vm._bind(**{"name": extra_params.get("vm_name"),
                   "exact_match": True}):  # pylint: disable=protected-access
      acli_vm.create(bind=True,
                     validate=True,
                     exact_match=True,
                     name=extra_params.get("vm_name"))
      nw.create(bind=True, vlan_id=0)
      INFO("VM already exisits, skipping re-install")
      vm.wait_for_ip()
      return True
    image = image_cls(name="image")

    INFO("Creating network if not already present")
    nw_uuid = nw.create(bind=True, vlan_id=0)
    INFO("Using network with uuid: %s" % nw_uuid)

    INFO("Creating VM: %s" % extra_params.get("vm_name"))
    vm.create(bind=False,
              validate=True,
              name=extra_params.get("vm_name"),
              **params)
    INFO("VM created")
    acli_vm.create(bind=True,
                   validate=True,
                   exact_match=True,
                   name=extra_params.get("vm_name"))

    INFO("Adding vNIC to VM: %s" % extra_params.get("vm_name"))
    vm.add_nic(network=nw_uuid)
    INFO("vNIC added to VM")

    INFO("Adding empty disk of type: %s" % params.get("boot_disk_type"))
    vm.add_disk(disk_type=params.get("boot_disk_type"), is_cdrom=False,
                container_uuid=ctr.entity_uuid,
                size_mb=params.get("boot_disk_size"))
    assert (len(vm.get_disks())) == 1, "Failed to add boot disk to VM"
    INFO("Added empty disk to VM")

    if params.get("oemdrv"):
      # threading.Locking
      with constants.IMAGE_UPLOAD_SYNC_CACHE[oemdrv_signature]:
        INFO("Uploading kickstart image: %s for vm: %s"
             % (params.get("oemdrv"), extra_params.get("vm_name")))
        ks_iso_id = image.upload_image(oemdrv_signature,
                                       params["oemdrv"], "ISO_IMAGE")[1]
        INFO("Mounting kickstart image to CDROM: %s" % params.get("oemdrv"))
      vm.add_disk(is_cdrom=True, is_empty=False,
                  disk_type=params.get("cdrom_bus_type"),
                  clone_container_uuid=ctr.entity_uuid,
                  clone_from_vmdisk=ks_iso_id
                  )
      INFO("Mounted kickstart image to cdrom")
    elif params.get("virtio"):
      # threading.Locking
      # get virtio version from installer path
      with constants.IMAGE_UPLOAD_SYNC_CACHE[virtio_signature]:
        # version = re.search(r"Nutanix-VirtIO-(\d\.\d\.\d)\.iso",
        #                     params.get("virtio"))
        # virtio_version = version.group(1)
        INFO("Uploading virtio image: %s for vm: %s"
             % (params.get("virtio"), extra_params.get("vm_name")))
        ks_iso_id = image.upload_image(virtio_signature,
                                       params["virtio"], "ISO_IMAGE")[1]
        INFO("Mounting virtio image to CDROM: %s" % params.get("virtio"))
      vm.add_disk(is_cdrom=True, is_empty=False,
                  disk_type=params.get("cdrom_bus_type"),
                  clone_container_uuid=ctr.entity_uuid,
                  clone_from_vmdisk=ks_iso_id
                  )
      INFO("Mounted virtio image to cdrom")

    INFO("Uploading OS installation image: %s for vm: %s"
         % (params["cdrom"], extra_params.get("vm_name")))
    iso_id = image.upload_image(my_signature,
                                params["cdrom"],
                                "ISO_IMAGE")[1]
    assert iso_id, "Failed to upload image"
    INFO("Mounting install image to CDROM: %s" % params["cdrom"])
    vm.add_disk(is_cdrom=True, is_empty=False,
                disk_type=params.get("cdrom_bus_type"),
                clone_container_uuid=ctr.entity_uuid,
                clone_from_vmdisk=iso_id
                )
    INFO("Mounted install image to cdrom")

    INFO("Updating the boot order to KDisk,kCdrom,kNet: ENG-648174")
    res = acli_vm.cluster.execute(
      "acli vm.update_boot_device %s boot_device_order=kDisk,kCdrom"
      % acli_vm.uuid)
    assert 'complete' in res['stdout'], ("Failed to update the boot order "
                                         "for VM %s") % acli_vm.name
    # ks = get_ks_iso(images)
    timeout = 3600
    INFO("Timeout: %s" % timeout)
    vm.power_on(wait_for_ip=True, timeout=timeout)
    extra_params["install_media"] = "CDROM"
    # FIXME: Add logic to enable gpu based VM if the host has GPU support
    extra_params["graphics"] = "non-gpu"
    extra_params["boot_disk"] = params.get("boot_disk_type")

  def teardown(self, **params):
    """
    Delete the VM
    Args:
    Returns:
    """
    # import pdb; pdb.set_trace()
    INFO("Executing teardown for Boot Test")
    extra_params = params.get("extra_params")
    modules = extra_params.get("modules")
    vm_name = extra_params.get("vm_name")
    cache = modules.get("cache")
    vm = cache.get_entity(entity_type="rest_vm", name=vm_name)
    vm.remove()
