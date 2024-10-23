"""
Copyright (c) 2024 Nutanix Inc. All rights reserved.

Author: pritam.chatterjee@nutanix.com
"""
# SDK imports

from libs.gateway.sdk_clients.base_client import (
  Base, BaseFacade)

class Gatewayv1(Base):
  """V1 class"""


class Gatewayv0(Base):
  """V0 class"""


class GatewayMixin(Gatewayv1, Gatewayv0):
  """Mixin class"""


class GatewayFacade(BaseFacade):
  """HostFacade class"""
  VERSION_MAP = {
    "v0": Gatewayv0,
    "v1": Gatewayv1,
    "default": GatewayMixin
  }
