"""
Copyright (c) 2022 Nutanix Inc. All rights reserved.

Author: umashankar.vd@nutanix.com

Factory for providing object for various Hypervisor type
"""

from libs.feature.nested_virtualization.\
  nested_hypervisors.hyperv import NestedHyperv
from libs.feature.nested_virtualization.\
  nested_hypervisors.kvm import NestedKvm
from libs.feature.nested_virtualization.\
  nested_hypervisors.vmware import NestedEsxi


class NestedVirtualizationFactory():
  """Nested hypervisor factory."""
  MAP = {
    "hyperv": NestedHyperv,
    "kvm": NestedKvm,
    "esxi": NestedEsxi
  }

  def __new__(cls, cluster, hypervisor_type="hyperv"):
    """
    Return correct nest hypervisor class
    Args:
      cluster(object):
      hypervisor_type(str):
    Returns:
    """
    if cls.MAP.get(hypervisor_type): #pylint: disable=no-else-return
      return cls.MAP.get(hypervisor_type)(cluster)
    else:
      raise NotImplementedError("Nested hypervisor of type %s is not "
                                "supported" % hypervisor_type)
