"""
Copyright (c) 2024 Nutanix Inc. All rights reserved.

Author: pritam.chatterjee@nutanix.com
"""
# SDK imports

from libs.gateway.sdk_clients.base_client import (
  Base, BaseFacade)

class Vmmv1(Base):
  """V1 class"""


class Vmmv0(Base):
  """V0 class"""


class VmmMixin(Vmmv1, Vmmv0):
  """Mixin class"""


class VmmFacade(BaseFacade):
  """HostFacade class"""
  VERSION_MAP = {
    "v0": Vmmv0,
    "v1": Vmmv1,
    "default": VmmMixin
  }
