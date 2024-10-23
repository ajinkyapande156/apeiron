"""
Copyright (c) 2023 Nutanix Inc. All rights reserved.

Author: pritam.chatterjee@nutanix.com
"""
import re
# pylint: disable=import-error, fixme, too-many-statements, unused-argument
# pylint: disable=too-many-locals, arguments-differ
# pylint: disable=inconsistent-return-statements, no-member, unused-variable
try:
  from framework.lib.nulog import INFO, ERROR, STEP, WARN  # pylint: disable=unused-import
  EXECUTOR = "nutest"
except Exception: # pylint: disable=broad-except
  from libs.ahv.framework.proxy_logging \
    import INFO, ERROR, STEP, WARN  # pylint: disable=unused-import
  EXECUTOR = "mjolnir"
from libs.ahv.workflows.gos_qual.lib.base.base \
  import BaseTest
# from libs.ahv.workflows.gos_qual.lib.base.gos_errors \
#   import TestNotSupported
from libs.ahv.workflows.gos_qual.lib.base.utilities \
  import get_os_instance  # pylint: disable=unused-import, line-too-long
from libs.feature.apc.factory import ApcVmFactory
from libs.framework.mjolnir_ddt \
  import MjolnirDataDrivenTest
from libs.workflows.apc.wf_helpers import ApcWfHelper

class CdromApcBoot(BaseTest):
  """CdromApcBoot class"""
  NAME = "cdrom_apc_boot"
  TAGS = ["apc_boot", "uefi", "legacy", "cdrom",
          "credentialguard", "secureboot", "vtpm",
          "vtpm_secureboot", "vtpm_credentialguard"]
  POST_OPERATIONS = ["setup_rpc", "verify_os_boot", "set_boot_disk",
                     "validate_virtio_drivers",
                     "get_guest_build", "get_guest_edition",
                     "validate_arch", "validate_bits",
                     "validate_gpu", "enable_cg_in_guest",
                     "validate_boot_type",
                     "check_device_status",
                     "prepare_for_vnic_hot_add"
                    ]
  DEFAULT_PARAMS = {
    "memory": 4096,
    "vcpus": 2,
    "cores_per_vcpu": 1,
    "boot_disk_size": 80000,
    "boot_disk_type": "SCSI",
    "cdrom_bus_type": "SATA",
    "uefi_boot": True
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
    if extra_params.get("vcpus"):
      params["vcpus"] = extra_params.get("vcpus")
    vm_name = extra_params.get("vm_name")
    modules = extra_params.get("modules")
    vm_cls = modules.get("rest_vm")
    vm = vm_cls(interface_type="REST", name=vm_name)
    acli_cls = modules.get("acli_vm")
    acli_vm = acli_cls(interface_type="ACLI", name=vm_name)
    # Just to integrate with Mjolnir data driven env
    MjolnirDataDrivenTest(cluster=vm.cluster, config_data={})
    self.apc_helper = ApcWfHelper(cluster=vm.cluster)

    # Construct resource params for APC settings.
    params["vm_spec"] = {}
    if "apc_enabled" in params and params.get("apc_enabled"):
      params["vm_spec"]["apc_config"] = {
        "enabled": params.get("apc_enabled")
      }
      INFO("ADDING APC CONFIG: %s" % params["vm_spec"]["apc_config"])
      if params.get("cpu_model"):
        params["vm_spec"]["apc_config"].update({
          "cpu_model_reference": {
            "kind": "cpu_model",
            "uuid": self.apc_helper.get_cpu_model_uuid(params.get("cpu_model"))
          }})
        INFO("ADDING CPU MODEL: %s" % params["vm_spec"]["apc_config"])
    params["vm_spec"]["vm_name"] = vm_name
    params["vm_spec"]["memory_size"] = params.get("memory")
    params["vm_spec"]["num_of_vcpus"] = params.get("vcpus")
    params["vm_spec"]["cores_per_vcpu"] = params.get("cores_per_vcpu")
    params["vm_spec"]["poll_interval"] = 5
    params["vm_spec"]["vtpm"] = params.get("virtual_tpm")
    # Construct boot params
    if extra_params.get("boot") == "credentialguard":
      params["vm_spec"]["boot_type"] = "credential_guard"
    elif extra_params.get("boot") == "vtpm_credentialguard":
      params["vm_spec"]["boot_type"] = "credential_guard"
    elif extra_params.get("boot") == "vtpm_secureboot":
      params["vm_spec"]["boot_type"] = "secure_boot"
    elif extra_params.get("boot") == "secureboot":
      params["vm_spec"]["boot_type"] = "secure_boot"
    elif extra_params.get("boot") == "uefi":
      params["vm_spec"]["boot_type"] = "uefi"
    else:
      params["vm_spec"]["boot_type"] = "legacy"

    try:
      apc_vm = ApcVmFactory()
      vm_spec = apc_vm.discover_vm_by_name(vm_name=vm_name)
      INFO("VM already exisits, skipping re-install, "
           "just bindling Restv2 and Acli interfaces")
      vm._bind(**{"name": extra_params.get("vm_name")})  # pylint: disable=protected-access
      acli_vm.create(bind=True,
                     validate=True,
                     name=extra_params.get("vm_name")
                     )
      vm.wait_for_ip()
      return
    except AssertionError:
      vm_spec = apc_vm.create(**params["vm_spec"])

    # bind with v2 api for the vm
    vm._bind(**{"name": extra_params.get("vm_name")})  # pylint: disable=protected-access
    # FIXME: Rest of the operations are done with restv2 and acli as of now
    image_cls = modules.get("rest_image")
    ctr = modules.get("rest_ctr")
    image = image_cls(name="image")
    INFO("Adding empty disk of type: %s" % params.get("boot_disk_type"))
    vm.add_disk(disk_type=params.get("boot_disk_type"), is_cdrom=False,
                container_uuid=ctr.entity_uuid,
                size_mb=params.get("boot_disk_size"))
    assert (len(vm.get_disks())) == 1, "Failed to add boot disk to VM"
    INFO("Added empty disk to VM")

    # add the iso for fresh install
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
    elif params.get("virtio"):
      # get virtio version from installer path
      version = re.search(r"Nutanix-VirtIO-(\d\.\d\.\d)\.iso",
                          params.get("virtio"))
      virtio_version = version.group(1)
      INFO("Uploading virtio image: %s for vm: %s"
           % (params.get("virtio"), extra_params.get("vm_name")))
      ks_iso_id = image.upload_image(extra_params.get("vm_name") + "_VIRTIO_" +
                                     virtio_version,
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
    iso_id = image.upload_image(extra_params.get("vm_name"),
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
      % acli_vm.name)
    assert 'complete' in res['stdout'], ("Failed to update the boot order "
                                         "for VM %s") % acli_vm.name

    acli_vm.create(bind=True,
                   validate=True,
                   name=extra_params.get("vm_name")
                   )
    if "nested" in vm.cluster.name:
      INFO("Nested cluster . Timeout is increased")
      timeout = 3600
    else:
      timeout = 1000
    INFO("Timeout: %s" % timeout)
    vm.power_on(wait_for_ip=True, timeout=timeout)
    extra_params["install_media"] = "CDROM"
    extra_params["boot_disk"] = params.get("boot_disk_type")
    # FIXME: Add logic to enable gpu based VM if the host has GPU support
    extra_params["graphics"] = "non-gpu"

  def teardown(self, **params):
    """
    Delete the VM
    Args:
    Returns:
    """
    return
    # INFO("Executing teardown for %s" % self.NAME)
    # extra_params = params.get("extra_params")
    # modules = extra_params.get("modules")
    # vm_name = extra_params.get("vm_name")
    # cache = modules.get("cache")
    # vm = cache.get_entity(entity_type="rest_vm", name=vm_name)
    # vm.remove()
