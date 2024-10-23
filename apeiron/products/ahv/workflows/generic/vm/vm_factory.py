"""
VM Factory

Copyright (c) 2023 Nutanix Inc. All rights reserved.
Author: rishabh.kumar@nutanix.com

"""
from libs.workflows.generic.vm.acli import AcliVm
from libs.workflows.generic.vm.rest_v2 import RestVmV2
from libs.workflows.generic.vm.rest_v3 import RestVmV3
from libs.workflows.generic.vm.rest_v4 import RestVmV4


class VmFactory:
  """
  VM Factory class
  """
  MAP = {
    'ACLI': AcliVm,
    'REST': RestVmV2,
    'REST_V3': RestVmV3,
    'REST_V4': RestVmV4
  }

  def __new__(cls, cluster, interface_type="ACLI", **kwargs):
    """
    Return the appropriate VM class based on the interface type
    Args:
      cluster(object): NuTest cluster object
      interface_type(str): Interface type
      kwargs(dict): Keyword args
    Returns:
      vm_cls(class): VM class
    """
    vm_cls = cls.MAP.get(interface_type)(
      cluster=cluster, interface_type=interface_type, **kwargs
    )
    return vm_cls
