"""
Copyright (c) 2021 Nutanix Inc. All rights reserved.

Author: pritam.chatterjee@nutanix.com
"""
# pylint: disable=import-error, unused-variable, no-else-return
from libs.ahv.workflows.gos_qual.lib.operating_systems.\
  windowsserver2016 import WindowsServer2016


class Windows10(WindowsServer2016):
  """Windows10 class"""
  SUPPORTED_FEATURES = {
    "hotplug_vnic": True,
    "hotremove_vnic": True,
    "hotplug_scsi_vdisk": True,
    "hotplug_sata_vdisk": True,
    "hotplug_pci_vdisk": False,
    "coldplug_scsi_vdisk": True,
    "coldplug_sata_vdisk": True,
    "coldplug_pci_vdisk": False,
    "hotremove_vdisk": True,
    "hotplug_num_vcpu": False,  # OS does not support
    "hotremove_num_vcpu": False,
    "hotplug_num_core_per_vcpu": False,
    "hotremove_num_core_per_vcpu": False,
    "hotplug_vmem": True,
    "hotremove_vmem": False,
    "vtpm": True
  }

  def get_errored_devices(self, **kwargs):
    """
    Method to get the devices in not OK state
    Args:
    Kargs:
    Returns:
      stdout(bool):
    """
    # NOTE: Remove this method once winsrv 2016 driver update workaround
    #       is added.
    cmd = "powershell Get-PnpDevice -PresentOnly -Status ERROR,DEGRADED,UNKNOWN"
    res, stdout, stderr = self.conn.run_shell_command_sync(cmd)
    if "No matching Win32_PnPEntity objects" in stderr.decode():
      return False
    else:
      return stdout
