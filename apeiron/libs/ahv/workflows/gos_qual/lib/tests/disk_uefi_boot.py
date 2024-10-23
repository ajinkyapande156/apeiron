"""
Copyright (c) 2021 Nutanix Inc. All rights reserved.

Author: pritam.chatterjee@nutanix.com
"""
# pylint: disable=import-error, fixme, too-many-statements,
# pylint: disable=protected-access, unused-import
# pylint: disable=too-many-locals, unused-variable, arguments-differ
# pylint: disable=inconsistent-return-statements
try:
  from framework.lib.nulog import INFO, ERROR, \
    STEP
  EXECUTOR = "nutest"
except Exception:  # pylint: disable=broad-except
  from libs.ahv.framework.proxy_logging \
    import INFO, ERROR, STEP, WARN
  EXECUTOR = "mjolnir"
from libs.ahv.workflows.gos_qual.lib.base.base \
  import BaseTest
from libs.ahv.workflows.gos_qual.lib.base.gos_errors \
  import TestNotSupported
from libs.ahv.workflows.gos_qual.lib.base.utilities \
  import get_os_instance  # pylint: disable=unused-import, line-too-long


# FIXME: This is just a variation of cdrom_legacy_boot test
#        Remove the duplicate code.
class DiskUefiBoot(BaseTest):
  """DiskUefiBoot class"""
  NAME = "disk_uefi_boot"
  TAGS = ["boot", "uefi", "disk",
          "credentialguard", "secureboot", "vtpm",
          "vtpm_secureboot", "vtpm_credentialguard"]
  POST_OPERATIONS = ["setup_rpc", "verify_os_boot",
                     # "validate_virtio_drivers",
                     "get_guest_build",
                     "get_guest_edition",
                     "validate_arch", "validate_bits",
                     "validate_gpu",
                     "validate_boot_type_on_vm",
                     "enable_cg_in_guest",
                     "validate_boot_type_in_guest",
                     "check_device_status"
                    ]
  DEFAULT_PARAMS = {
    "memory": 4096,
    "vcpus": 2,
    "cores_per_vcpu": 1,
    # "boot_disk_size": 80000,
    "boot_disk_type": "SCSI",
    "cdrom_bus_type": "SATA",
    "uefi_boot": True,
    # "vnic_type": "virtio"
  }

  def run(self, **params):
    """
    Run the test
    Args:
    Returns:
    Raises:
    """
    STEP("Executing Test [%s] with boot disk [%s]"
         % (self.NAME, params.get("boot_disk_type")))
    extra_params = params.get("extra_params")
    vm_name = extra_params.get("vm_name")
    modules = extra_params.get("modules")
    vm_cls = modules.get("rest_vm")
    image_cls = modules.get("rest_image")
    nw_cls = modules.get("rest_nw")
    ctr = modules.get("rest_ctr")
    # images = extra_params.get("images")
    vm = vm_cls(interface_type="REST", name=vm_name)
    acli_vm_cls = modules.get("acli_vm")
    acli_vm = acli_vm_cls(interface_type="ACLI", name=vm_name)
    acli_cls = modules.get("acli")
    acli = acli_cls(name="acli")
    if vm._bind(**{"name": extra_params.get("vm_name")}):
      INFO("VM already exisits, skipping re-install")
      vm.wait_for_ip()
      return True
    image = image_cls(name="image")
    nw = nw_cls(interface_type="REST", name="network")
    vtpm = dict()
    if params.get("virtual_tpm"):
      os = get_os_instance(extra_params["os"])(conn_provider=modules.get("rpc_cls_v2")(vm))
      if not os.SUPPORTED_FEATURES["vtpm"]:
        WARN("Test [%s] is not support for this guest OS. Refer [ENG-496749]" % self.NAME)
        raise TestNotSupported
      vtpm["virtual_tpm"] = params.pop("virtual_tpm")

    INFO("Creating network if not already present")
    nw_uuid = nw.create(bind=True, vlan_id=0)
    INFO("Using network with uuid: %s" % nw_uuid)

    INFO("Creating VM: %s" % extra_params.get("vm_name"))
    vm.create(bind=False,
              validate=True,
              name=extra_params.get("vm_name"),
              **params
             )
    INFO("VM created")
    acli_vm.create(bind=True,
                   validate=True,
                   name=extra_params.get("vm_name")
                  )
    if vtpm:
      INFO("Enabling vTPM on VM: %s" % extra_params.get("vm_name"))
      acli_vm.edit(**vtpm)

    if params.get("windows_credential_guard"):
      INFO("Enabling credentialguard on VM: %s" % extra_params.get("vm_name"))
      acli_vm.edit(**{"windows_credential_guard": True})

    INFO("Adding vNIC to VM: %s" % extra_params.get("vm_name"))
    if params.get("vnic_type") not in ["e1000"]:
      cmd = "nic_create  " + extra_params.get("vm_name") + \
            " model=e1000 " \
            "network=%s" %nw_uuid.uuid
      acli.execute('vm', cmd)
    else:
      vm.add_nic(network=nw_uuid)
    INFO("vNIC added to VM")

    INFO("Uploading OS boot image: %s for vm: %s"
         % (params["disk"], extra_params.get("vm_name")))
    disk_id = image.upload_image(extra_params.get("vm_name"),
                                 params["disk"],
                                 "DISK_IMAGE")[1]
    assert disk_id, "Failed to upload image"
    INFO("Adding the uploaded image as boot disk: %s" % params["disk"])
    vm.add_disk(is_cdrom=False,
                device_index=0,
                disk_type=params.get("boot_disk_type"),
                clone_from_vmdisk=disk_id
               )
    INFO("Added boot disk with uploaded image")
    INFO("Updating the boot device for VM: %s" % extra_params.get("vm_name"))
    vm.edit(
      **{
        "boot_device_type": "DISK",
        "device_bus": params.get("boot_disk_type"),
        "device_index": 0
      }
    )

    assert (len(vm.get_disks())) == 1, "Failed to add boot disk to VM"

    vm.power_on(wait_for_ip=True, timeout=900)
    extra_params["install_media"] = "DISK"
    extra_params["boot_disk"] = params.get("boot_disk_type")
    # FIXME: Add logic to enable gpu based VM if the host has GPU support
    extra_params["graphics"] = "non-gpu"

  def teardown(self, **params):
    """
    Delete the VM
    Args:
    Returns:
    """
    INFO("Executing teardown for %s" % self.NAME)
    extra_params = params.get("extra_params")
    modules = extra_params.get("modules")
    vm_name = extra_params.get("vm_name")
    cache = modules.get("cache")
    vm = cache.get_entity(entity_type="rest_vm", name=vm_name)
    vm.remove()
