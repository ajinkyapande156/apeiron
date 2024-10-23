"""
Copyright (c) 2024 Nutanix Inc. All rights reserved.

Author: pritam.chatterjee@nutanix.com
"""
# pylint: disable=import-error, unused-import, unused-argument, no-member
import json
from libs.framework import mjolnir_entities as entities
from libs.feature.gateway.host import Host
from libs.feature.gateway.vmm import Vmm
from libs.feature.gateway.host_raw import HostRaw
from libs.feature.gateway.vmm_raw import VmmRaw

class HostGatewayInterface:
  """Host Gateway API Interface class"""

  TYPE_MAP = {
    "raw": (HostRaw, VmmRaw),
    "sdk": (Host, Vmm)
  }

  def __new__(cls, *args, **kwargs):
    """
    Gateway interface factory
    Returns:
    Raises:
    """
    inf_type = kwargs.pop("type", "raw")
    if inf_type not in cls.TYPE_MAP:
      raise RuntimeError("Unable to create Host Gateway Interface object, "
                         "available types: %s" % cls.TYPE_MAP)
    gateway_cls = type('Gateway', cls.TYPE_MAP[inf_type], {})
    return gateway_cls(*args, **kwargs)
