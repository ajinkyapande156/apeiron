"""
Copyright (c) 2023 Nutanix Inc. All rights reserved.

Author: pritam.chatterjee@nutanix.com
"""
from libs.feature.apc.apc_vms.apc_vm_restv4 \
  import ApcVmRestv4
from libs.feature.apc.apc_vms.apc_vm_restv3 \
  import ApcVmRestv3
from libs.feature.apc.apc_vms.apc_vm_acli \
  import ApcVmAcli


class ApcVmFactory:
  """ApcVmFactory class"""
  MAP = {
    "acli": ApcVmAcli,
    "restv3": ApcVmRestv3,
    "restv4": ApcVmRestv4
  }

  def __new__(cls, **kwargs):
    """
    Factory
    Args:
    Returns:
    """
    api_type = kwargs.pop("api_type", "restv3")
    if not cls.MAP.get(api_type):
      api_type = "restv3"
    return cls.MAP[api_type](**kwargs)
