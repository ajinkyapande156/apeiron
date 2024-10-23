"""
Copyright (c) 2024 Nutanix Inc. All rights reserved.

Author: pritam.chatterjee@nutanix.com
"""
from libs.gateway.sdk_clients.host_client import (
  HostMixin, HostFacade)
from libs.gateway.sdk_clients.vmm_client import (
  VmmMixin)
from libs.gateway.sdk_clients.net_client import (
  NetMixin, NetFacade)
from libs.gateway.sdk_clients.gateway_client import (
  GatewayMixin)
from libs.gateway.sdk_clients.event_client import (
  EventMixin)
from libs.gateway.gateway_auth import (
  HostGatewayConfigCertAuth)


class GatewaySdkClients:
  """Gatewaty SDK Clients"""
  # If you need access to multiple clients with one object
  # ease of use, everything accessible thru one object
  MIXIN_CLIENTS = {
    "host": HostMixin,
    "vmm": VmmMixin,
    "net": NetMixin,
    "gateway": GatewayMixin,
    "event": EventMixin
  }

  # If you need access to a single client only. this provides
  # flexibility to use selective version of client
  FACADE_CLIENTS = {
    "host": HostFacade,
    "vmm": VmmMixin,
    "net": NetFacade,
    "gateway": GatewayMixin,
    "event": EventMixin
  }

  # auth provider will handle following based on the selected:
  # 1. no_auth: Will configure hosts to enabled no_auth
  # 2. cert_auth: Copy the certs from CVM and setup on nutest launcher
  AUTH_PROVIDER = {
    # "no_auth": HostGatewayConfigNoAuth,
    "cert_auth": HostGatewayConfigCertAuth
  }

  def __new__(cls, *args, **kwargs):
    """
    Factory
    Args:
    Returns:
    Raises:
    """
    clients = kwargs.pop("clients", None)
    auth_provider = kwargs.pop("auth_provider", "cert_auth")

    auth = cls.AUTH_PROVIDER.get(auth_provider)
    if not clients:
      # create a mixin from all clients
      clients = tuple(cls.MIXIN_CLIENTS.values())
    elif len(clients.split(",")) > 1:
      # create a mixin from selective multiple clients
      clients = clients.split(",")
      clients = tuple([cls.MIXIN_CLIENTS[client] for client in clients if
                       client in cls.MIXIN_CLIENTS])
    elif len(clients.split(",")) == 1:
      # facade for single client
      clients = clients.split(",")
      clients = tuple([cls.FACADE_CLIENTS[client]  for client in clients if
                       client in cls.FACADE_CLIENTS])

    sdk_interface = type('SdkClientInterface', clients, {})
    return sdk_interface(auth, *args, **kwargs)
