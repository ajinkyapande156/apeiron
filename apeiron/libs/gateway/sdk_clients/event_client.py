"""
Copyright (c) 2024 Nutanix Inc. All rights reserved.

Author: pritam.chatterjee@nutanix.com
"""
# SDK imports

from libs.gateway.sdk_clients.base_client import (
  Base, BaseFacade)

class Eventv1(Base):
  """V1 class"""


class Eventv0(Base):
  """V0 class"""


class EventMixin(Eventv1, Eventv0):
  """Mixin class"""


class EventFacade(BaseFacade):
  """HostFacade class"""
  VERSION_MAP = {
    "v0": Eventv0,
    "v1": Eventv1,
    "default": EventMixin
  }
