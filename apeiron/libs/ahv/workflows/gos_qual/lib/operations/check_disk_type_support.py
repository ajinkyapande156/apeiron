"""
Copyright (c) 2022 Nutanix Inc. All rights reserved.

Author: pritam.chatterjee@nutanix.com
"""
# pylint: disable=import-error, fixme, arguments-differ
# pylint: disable=pointless-string-statement
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


class CheckDiskTypeSupported(AbstractVerifier):
  """CheckDiskTypeSupported"""

  def verify(self, **params):
    """
    Verify and update any disk type that is not supported for
    any guest OS
    Args:
    Returns:
    """
    extra_params = params.get("extra_params")
    os = extra_params["modules"]["rpc"]
    vdisks = params.get("vdisks")
    """
    Sample: SUPPORTED_FEATURES
    "hotplug_sata_vdisk": True,
    "hotplug_pci_vdisk": False,
    "coldplug_scsi_vdisk": True,
    "coldplug_sata_vdisk": True,
    "coldplug_pci_vdisk": False
    """

    selected_for_removal = []
    for vdisk in vdisks:
      selected_for_removal += [vdisk.get("bus_type")
                               for x in os.SUPPORTED_FEATURES if
                               params.get("type") + "_" +
                               vdisk.get("bus_type").lower() in x
                               and not os.SUPPORTED_FEATURES[x]]
    removal_idx = []
    for i in range(len(vdisks)):
      if vdisks[i].get("bus_type") in selected_for_removal:
        WARN("Disk of type %s will not be considered for vm: %s"
             % (selected_for_removal, extra_params.get("vm_name")))
        removal_idx.append(i)
    for i in removal_idx:
      params["vdisks"].pop(i)  # modify dict by reference
