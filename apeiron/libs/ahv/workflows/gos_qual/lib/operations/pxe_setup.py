"""
Copyright (c) 2021 Nutanix Inc. All rights reserved.

Author: pritam.chatterjee@nutanix.com
"""
# pylint: disable=import-error, unused-import
# pylint: disable=too-many-locals
import copy
import time

try:
  from framework.lib.nulog import INFO, ERROR, WARN, \
    DEBUG  # pylint: disable=unused-import
  EXECUTOR = "nutest"
except Exception:  # pylint: disable=broad-except
  from libs.ahv.framework.proxy_logging \
    import INFO, ERROR, WARN, DEBUG  # pylint: disable=unused-import
  EXECUTOR = "mjolnir"
from libs.ahv.workflows.gos_qual.lib.base.abstracts \
  import AbstractVerifier
from libs.ahv.workflows.gos_qual.lib.base.utilities \
  import get_os_instance  # pylint: disable=unused-import, line-too-long


class PxeSetup(AbstractVerifier):
  """PxeSetup class"""

  def verify(self, **params):
    """
    Performs steps creating pxe boot env
    Args:
    Returns:
    """
    extra_params = params.get("extra_params")
    modules = extra_params.get("modules")
    os = extra_params.get("os")
    vm_name = extra_params.get("vm_name")
    image_cls = modules.get("rest_image")
    nw_cls = modules.get("rest_nw")
    image = image_cls(name="image")
    nw = nw_cls(interface_type="REST", name="network")
    ctr = modules.get("rest_ctr")
    pxe_vm_cls = modules.get("pxe_vm")
    pxe_vm = pxe_vm_cls(interface_type="REST", name=vm_name)
    INFO("Creating network if not already present")
    nw_uuid = nw.create(bind=True, vlan_id=0)
    INFO("Using network with uuid: %s" % nw_uuid)
    INFO("Starting PXE server deployment")
    boot_params = {
      'boot_disk_size': 80000,
      'boot_disk_type': 'SCSI',
      'cores_per_vcpu': 2,
      'memory': 4096,
      'machine_type': 'pc',
      'vcpus': 2,
      'uefi_boot': False
    }
    pxe_vm.create(bind=False,
                  validate=True,
                  name=extra_params.get("os") + "_PXE_SERVER",
                  **boot_params)
    INFO("PXE server pxe_vm created")
    INFO("Adding vNIC to pxe_vm: %s" % "PXE_SERVER")
    pxe_vm.add_nic(network=nw_uuid)
    INFO("vNIC added to pxe_vm")

    INFO("Uploading pxe server image: %s for deploying: %s"
         % (params.get("pxe"), "PXE_SERVER"))
    pxe_id = image.upload_image("MJOLNIR_PXE_SERVER",
                                params["pxe"], "DISK_IMAGE")[1]

    pxe_vm.add_disk(is_cdrom=False,
                    disk_type=params.get("cdrom_bus_type"),
                    clone_container_uuid=ctr.entity_uuid,
                    clone_from_vmdisk=pxe_id)
    INFO("Booting up the PXE server")
    pxe_vm.power_on(wait_for_ip=True)
    modules["pxe_vm"] = pxe_vm
    pxe_rpc = get_os_instance(os)(conn_provider=
                                  modules.get("rpc_cls_v1")(pxe_vm.ip))
    INFO("Dynamically configuring PXE server now")
    pxe_rpc.verify_os_boot()
    pxe_rpc.configure_tftp_env(**params)
    pxe_rpc.configure_dnsmasq_env(**params)
    INFO("Waiting for 10 secs for pxe-server to come-up..")
    time.sleep(10)
