"""
Copyright (c) 2022 Nutanix Inc. All rights reserved.

Author: pritam.chatterjee@nutanix.com
"""
# pylint: disable=import-error, invalid-name, arguments-differ, no-else-continue
try:
  from framework.lib.nulog import INFO, ERROR, \
    STEP  # pylint: disable=unused-import

  EXECUTOR = "nutest"
except Exception:  # pylint: disable=broad-except
  from libs.ahv.framework.proxy_logging \
    import INFO, ERROR, STEP  # pylint: disable=unused-import

  EXECUTOR = "mjolnir"
from libs.ahv.workflows.gos_qual.lib.base.base \
  import BaseTest


# pylint: disable-msg=too-many-locals

class ColdAddRemoveVdisks(BaseTest):
  """ColdAddRemoveVdisks class"""
  NAME = "cold_add_remove_vdisks"
  TAGS = ["storage"]
  PRE_OPERATIONS = ["check_disk_type_support"]
  POST_OPERATIONS = ["run_io_integrity", "check_device_status"]
  DEFAULT_PARAMS = {
    "vdisks": [
      {
        "bus_type": "SCSI",
        "disk_size": 2048
      },
      {
        "bus_type": "PCI",
        "disk_size": 2048
      },
      {
        "bus_type": "SATA",
        "disk_size": 2048
      },
    ],
    "type": "coldplug"
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
    """
    STEP("Executing Test [%s] " % self.NAME)
    extra_params = params.get("extra_params")
    modules = extra_params.get("modules")
    vm_name = extra_params.get("vm_name")
    cache = modules.get("cache")
    vm = cache.get_entity(entity_type="rest_vm", name=vm_name)
    os = modules.get("rpc")
    ctr = modules.get("rest_ctr")
    INFO("Powering off VM: %s for disk cold add" % vm.name)
    vm.power_off()
    INFO("Get boot disk info")
    data = vm.get()
    boot_disk_index = data["boot"]["disk_address"]["device_index"]
    boot_disk_bus = data["boot"]["disk_address"]["device_bus"]
    vdisks = params.get("vdisks")
    for vdisk in vdisks:
      existing_disks = len(vm.get_disks())
      INFO("Adding empty disk of type: %s" % vdisk.get("bus_type"))
      vm.add_disk(disk_type=vdisk.get("bus_type"), is_cdrom=False,
                  container_uuid=ctr.entity_uuid,
                  size_mb=vdisk.get("disk_size"))
      new_disks = len(vm.get_disks()) - existing_disks
      assert new_disks == 1, "Failed to add disk to VM"
    vm.power_on(wait_for_ip=True)
    os.verify_os_boot_post_reboot(vm)
    # validate , run io integrity
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
    Remove all disks that were added
    Args:
    Returns:
    """
    STEP("Entering teardown in test: %s" % self.NAME)
    extra_params = params.get("extra_params")
    modules = extra_params.get("modules")
    vm_name = extra_params.get("vm_name")
    cache = modules.get("cache")
    vm = cache.get_entity(entity_type="rest_vm", name=vm_name)
    os = modules.get("rpc")
    INFO("Powering off VM: %s for vdisk cold remove" % vm.name)
    vm.power_off()
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
