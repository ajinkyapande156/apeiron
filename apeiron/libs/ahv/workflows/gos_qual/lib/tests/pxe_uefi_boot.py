"""
Copyright (c) 2022 Nutanix Inc. All rights reserved.

Author: pritam.chatterjee@nutanix.com
"""
# pylint: disable=import-error, fixme, arguments-differ
# pylint: disable=unused-variable, inconsistent-return-statements
# pylint: disable=too-many-locals
# pylint: disable=too-many-statements
try:
  from framework.lib.nulog import INFO, ERROR, STEP  # pylint: disable=unused-import
  EXECUTOR = "nutest"
except Exception: # pylint: disable=broad-except
  from libs.ahv.framework.proxy_logging \
    import INFO, ERROR, STEP, WARN  # pylint: disable=unused-import
  EXECUTOR = "mjolnir"
from libs.ahv.workflows.gos_qual.lib.base.base \
  import BaseTest
from libs.ahv.workflows.gos_qual.lib.base.gos_errors \
  import TestNotSupported
from libs.ahv.workflows.gos_qual.lib.base.utilities \
  import get_os_instance  # pylint: disable=unused-import, line-too-long


class PxeUefiBoot(BaseTest):
  """CdromUefiBoot class"""
  NAME = "pxe_uefi_boot"
  TAGS = ["boot", "uefi", "pxe", "credentialguard", "secureboot", "vtpm",
          "vtpm_secureboot"]
  PRE_OPERATIONS = ["pxe_setup"]
  POST_OPERATIONS = ["setup_rpc", "verify_os_boot", "set_boot_disk",
                     "validate_virtio_drivers",
                     "get_guest_build", "get_guest_edition",
                     "validate_arch", "validate_bits",
                     "validate_gpu", "validate_boot_type",
                     "check_device_status",
                     "prepare_for_vnic_hot_add"]  #, "pxe_teardown"]
  DEFAULT_PARAMS = {
    "memory": 2048,
    "vcpus": 2,
    "cores_per_vcpu": 1,
    "boot_disk_size": 80000,
    "boot_disk_type": "SCSI",
    "cdrom_bus_type": "SATA",
    "uefi_boot": True,
  }

  def run(self, **params):
    """
    Run the test
    Args:
    Returns:
    Raises:
    """
    STEP("Executing Test [%s] with boot disk [%s]"
         % (self.NAME,
            params.get("boot_disk_type")))
    extra_params = params.get("extra_params")
    modules = extra_params.get("modules")
    vm_name = extra_params.get("vm_name")
    cache = modules.get("cache")
    vm_cls = modules.get("rest_vm")
    vm = vm_cls(interface_type="REST", name=vm_name)
    acli_cls = modules.get("acli_vm")
    acli_vm = acli_cls(interface_type="ACLI", name=vm_name)
    # import pdb; pdb.set_trace()
    if vm._bind(**{"name": extra_params.get("vm_name")}):  # pylint: disable=protected-access
      INFO("VM already exisits, skipping re-install")
      vm.wait_for_ip()
      return True
    image = cache.get_entity(entity_type="rest_image", name="image")
    nw = cache.get_entity(entity_type="rest_nw", name="network")
    ctr = modules.get("rest_ctr")
    vtpm = dict()
    if params.get("virtual_tpm"):
      os = get_os_instance(extra_params["os"])(conn_provider=modules.get("rpc_cls_v2")(vm))
      if not os.SUPPORTED_FEATURES["vtpm"]:
        WARN("Test [%s] is not support for this guest OS. Refer [ENG-496749]" % self.NAME)
        raise TestNotSupported
      vtpm["virtual_tpm"] = params.pop("virtual_tpm")

    INFO("Creating network if not already present")
    nw_uuid = nw.create(bind=True, vlan_id=0)
    INFO("Using network with uuid: %s" %nw_uuid)

    INFO("Creating VM: %s" % extra_params.get("vm_name"))
    vm.create(bind=False,
              validate=True,
              name=extra_params.get("vm_name"),
              **params)
    INFO("VM created")

    if vtpm:
      INFO("Enabling vTPM on VM: %s" % extra_params.get("vm_name"))
      acli_vm.create(bind=True,
                     validate=True,
                     name=extra_params.get("vm_name")
                    )
      acli_vm.edit(**vtpm)

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
      INFO("Uploading kickstart image: %s for vm: %s"
           % (params.get("oemdrv"), extra_params.get("vm_name")))
      ks_iso_id = image.upload_image(extra_params.get("vm_name") + "_OEMDRV",
                                     params["oemdrv"], "ISO_IMAGE")[1]
      INFO("Mounting kickstart image to CDROM: %s" % params.get("oemdrv"))
      vm.add_disk(is_cdrom=True, is_empty=False,
                  disk_type=params.get("cdrom_bus_type"),
                  clone_container_uuid=ctr.entity_uuid,
                  clone_from_vmdisk=ks_iso_id
                 )
      INFO("Mounted kickstart image to cdrom")

    INFO("Powering on the VM %s for Network OS installation"
         % extra_params.get("vm_name"))
    # iso_id = image.upload_image(extra_params.get("vm_name"),
    #                             params["cdrom"],
    #                             "ISO_IMAGE")[1]
    # assert iso_id, "Failed to upload image"
    # INFO("Mounting install image to CDROM: %s" % params["cdrom"])
    # vm.add_disk(is_cdrom=True, is_empty=False,
    #             disk_type=params.get("cdrom_bus_type"),
    #             clone_container_uuid=ctr.entity_uuid,
    #             clone_from_vmdisk=iso_id
    #            )
    # INFO("Mounted install image to cdrom")
    # ks = get_ks_iso(images)
    vm.power_on(wait_for_ip=True, timeout=900)
    extra_params["install_media"] = "NETWORK"
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
    pxe_vm = modules.get("pxe_vm")
    pxe_vm.remove()
    vm = modules.get("rest_vm")
    vm.remove()
