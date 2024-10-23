"""
Copyright (c) 2022 Nutanix Inc. All rights reserved.

Author: arundhathi.a@nutanix.com
"""
# pylint: disable=import-error, unused-import, invalid-name, arguments-differ
# pylint: disable=no-else-continue, unnecessary-pass
try:
  from framework.lib.nulog import INFO, ERROR, STEP, WARN  # pylint: disable=unused-import
  EXECUTOR = "nutest"
except Exception: # pylint: disable=broad-except
  from libs.ahv.framework.proxy_logging \
    import INFO, ERROR, STEP, WARN  # pylint: disable=unused-import
  EXECUTOR = "mjolnir"
from libs.ahv.workflows.gos_qual.lib.base.base \
  import BaseTest


# pylint: disable-msg=too-many-locals

class HotAddVdisks(BaseTest):
  """HotAddPCIVdisks class"""
  NAME = "hot_add_vdisks"
  TAGS = ["vdiskadd"]
  POST_OPERATIONS = ["check_device_status"]
  DEFAULT_PARAMS = {
    "vdisks": [
      # {
      #   "bus_type": "PCI",
      #   "disk_size": 2048
      # },
      {
        "bus_type": "SCSI",
        "disk_size": 2048
      },
      {
        "bus_type": "SCSI",
        "disk_size": 2048
      },
    ],
    "file_size_gb": 2,
    "time_limit_secs": 60
  }

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
    ctr = modules.get("rest_ctr")
    os = modules.get("rpc")
    indices = list()
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
    vm.power_on(wait_for_ip=True)
    #validate , run io integrity
    os.install_fio()
    os.reboot()
    os.verify_os_boot()
    drives = os.get_disk_drives()
    os.set_disk_online()
    for drive in drives:
      if "PHYSICALDRIVE0" not in drive:
        os.run_io_integrity(vdisk_file=drive,
                            file_size_gb=params.get("file_size_gb"),
                            time_limit_secs=params.get("time_limit_secs"))

    INFO("Hot remove disk from VM: %s" % vm.name)
    disks = vm.get_disks()
    for disk in disks:
      if disk.bus == boot_disk_bus.lower() \
          and disk.index == boot_disk_index:
        continue
      else:
        indices.append({"bus": disk.bus, "index": disk.index})
    deleted = []
    INFO("Disks: %s" % indices)
    for disk in indices:
      existing_disks = len(vm.get_disks())
      if deleted and disk["bus"] + "." + str(disk["index"]) in deleted:
        continue
      INFO("Deleting disk of type: %s at index:%s" %
           (disk["bus"], disk["index"]))
      vm.delete_disk(disk_type=disk["bus"], device_index=disk["index"])
      new_disks = existing_disks - len(vm.get_disks())
      assert new_disks == 1, "Failed to remove disk from VM"
      deleted.append(disk["bus"] + "." + str(disk["index"]))

  def teardown(self, **params):
    """
    Teardown
    Args:
    Returns:
    """
    pass
