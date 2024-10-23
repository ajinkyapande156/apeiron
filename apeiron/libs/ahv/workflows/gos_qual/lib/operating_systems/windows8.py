"""
Copyright (c) 2022 Nutanix Inc. All rights reserved.

Author: arundhathi.a@nutanix.com
"""
# pylint: disable=import-error
# pylint: disable=ungrouped-imports

from libs.ahv.workflows.gos_qual.lib.operating_systems.\
  windowsserver2012 import WindowsServer2012

try:
  from framework.lib.nulog import INFO, WARN, ERROR  # pylint: disable=unused-import
  EXECUTOR = "nutest"
except Exception: # pylint: disable=broad-except
  from libs.ahv.framework.proxy_logging \
    import INFO, WARN, ERROR  # pylint: disable=unused-import
  EXECUTOR = "mjolnir"

class Windows8(WindowsServer2012):
  """Windows8 class"""
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
    "hotplug_num_vcpu": False,
    "hotremove_num_vcpu": False,
    "hotplug_num_core_per_vcpu": False,
    "hotremove_num_core_per_vcpu": False,
    "hotplug_vmem": True,
    "hotremove_vmem": False,
    "vtpm": False
  }
