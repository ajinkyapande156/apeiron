"""
Copyright (c) 2024 Nutanix Inc. All rights reserved.
Author: rishabh.kumar@nutanix.com

Checks if VM creation and VM OPs supported on the given cluster
"""
from framework.lib.nulog import INFO
import workflows.acropolis.mjolnir.workflows.generic.vm.vm_checks as VMChecks


class VMSupport:
  """VM Support class"""

  def __init__(self, cluster):
    """
    Init method
    Args:
      cluster(object): NuTest cluster object
    """
    self.cluster = cluster

  def run_checks(self, **kwargs):
    """
    Run all the checks to see if VM creation is supported on the cluster
    Args:
    Returns:
      is_combo_supported(bool): True if supported, False otherwise
    """
    self.boot_type = kwargs.get("boot_type")
    self.feature = kwargs.get("feature")
    INFO("Run check on boot type: %s, features: %s" \
         % (self.boot_type, self.feature))
    is_combo_supported = VMChecks.is_vm_supported(cluster=self.cluster,
                                                  features=self.feature)
    return is_combo_supported
