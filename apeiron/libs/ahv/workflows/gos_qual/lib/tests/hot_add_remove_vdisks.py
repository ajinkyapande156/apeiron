"""
Copyright (c) 2022 Nutanix Inc. All rights reserved.

Author: pritam.chatterjee@nutanix.com
"""
# pylint: disable=import-error, unused-import, invalid-name, arguments-differ
# pylint: disable=no-else-continue, unnecessary-pass
try:
  from framework.lib.nulog import INFO, ERROR, \
    STEP, WARN  # pylint: disable=unused-import

  EXECUTOR = "nutest"
except Exception:  # pylint: disable=broad-except
  from libs.ahv.framework.proxy_logging \
    import INFO, ERROR, STEP  # pylint: disable=unused-import

  EXECUTOR = "mjolnir"
from libs.ahv.workflows.gos_qual.lib.base.base \
  import BaseTest
from libs.ahv.workflows.gos_qual.lib.base.gos_errors \
  import TestNotSupported


# pylint: disable-msg=too-many-locals

class HotAddRemoveVdisks(BaseTest):
  """HotAddRemoveVdisks class"""
  NAME = "hot_add_remove_vdisks"
  TAGS = ["storage"]
  PRE_OPERATIONS = ["check_disk_type_support"]
  POST_OPERATIONS = ["run_io_integrity", "check_device_status"]
  DEFAULT_PARAMS = {
    "vdisks": [
      {
        "bus_type": "SCSI",
        "disk_size": 2048
      }
    ],
    "type": "hotplug"
  }

  def __init__(self):
    """
    Initialize any object level variables here
    Args:
    """
    self.INDICES = list()

  def run(self, **params):
    """
    Run the test
    Args:
    Returns:
    Raises:
    """
    STEP("Executing Test [%s] " % self.NAME)
    extra_params = params.get("extra_params")
    modules = extra_params.get("modules")
    vm_name = extra_params.get("vm_name")
    cache = modules.get("cache")
    vm = cache.get_entity(entity_type="rest_vm", name=vm_name)
    ctr = modules.get("rest_ctr")
    acli_vm = cache.get_entity(entity_type="acli_vm", name=vm_name)
    vm_config = acli_vm.get()["config"]["boot"]
    if vm_config.get("windows_credential_guard"):
      WARN("Test [%s] is not support for credentialguard"
           % self.NAME)
      raise TestNotSupported
    INFO("Get boot disk info")
    data = vm.get()
    boot_disk_index = data["boot"]["disk_address"]["device_index"]
    boot_disk_bus = data["boot"]["disk_address"]["device_bus"]
    INFO("Hot add disk to VM: %s" % vm.name)
    vdisks = params.get("vdisks")
    for vdisk in vdisks:
      existing_disks = len(vm.get_disks())
      INFO("Adding empty disk of type: %s" % vdisk.get("bus_type"))
      vm.add_disk(disk_type=vdisk.get("bus_type"), is_cdrom=False,
                  container_uuid=ctr.entity_uuid,
                  size_mb=vdisk.get("disk_size"))
      new_disks = len(vm.get_disks()) - existing_disks
      assert new_disks == 1, "Failed to add disk to VM"
    # validate , run io integrity

    INFO("Hot remove disk from VM: %s" % vm.name)
    disks = vm.get_disks()
    for disk in disks:
      if disk.bus == boot_disk_bus.lower() \
          and disk.index == boot_disk_index:
        continue
      else:
        self.INDICES.append({"bus": disk.bus, "index": disk.index})
    # validate , run io integrity

  def teardown(self, **params):
    """
    Teardown
    Args:
    Returns:
    """
    extra_params = params.get("extra_params")
    modules = extra_params.get("modules")
    vm_name = extra_params.get("vm_name")
    cache = modules.get("cache")
    vm = cache.get_entity(entity_type="rest_vm", name=vm_name)
    os = modules.get("rpc")
    deleted = []
    INFO("Disks: %s" % self.INDICES)
    for disk in self.INDICES:
      existing_disks = len(vm.get_disks())
      if deleted and disk["bus"] + "." + str(disk["index"]) in deleted:
        continue
      INFO("Deleting disk of type: %s at index:%s" %
           (disk["bus"], disk["index"]))
      vm.delete_disk(disk_type=disk["bus"], device_index=disk["index"])
      new_disks = existing_disks - len(vm.get_disks())
      assert new_disks == 1, "Failed to remove disk from VM"
      deleted.append(disk["bus"] + "." + str(disk["index"]))
    vm.power_on(wait_for_ip=True)
    os.verify_os_boot_post_reboot(vm)
