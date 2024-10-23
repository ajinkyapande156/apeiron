"""
Copyright (c) 2024 Nutanix Inc. All rights reserved.

Author: pritam.chatterjee@nutanix.com
"""
# SDK imports
import ahv_gateway_client_net_v1

from libs.gateway.sdk_clients.base_client import (
  Base, BaseFacade)


class Netv1(Base):
  """V1 class"""
  def create_ovs_iface(self, host, payload, *args, **kwargs):
    """
    Creates an ovs iface
    Args:
      host(str): Host ip
      payload(dict): iface name
    Returns:
      api_response(dict):
    """
    openv_switch_interface = (
      ahv_gateway_client_net_v1.OpenvSwitchInterface.from_dict(payload))
    api_instance = self.get_api_instance(ahv_gateway_client_net_v1, host,
                                         *args, **kwargs)
    api_response = api_instance.create_ovs_iface(openv_switch_interface)
    return api_response

  def get_ovs_iface(self, host, iface, *args, **kwargs):
    """
    Retrieves the ovs iface details
    Args:
      host(str): Host ip
      iface(str): iface name
    Returns:
      api_response(dict):
    """
    api_instance = self.get_api_instance(ahv_gateway_client_net_v1, host,
                                         *args, **kwargs)
    api_response = api_instance.get_ovs_iface(iface)
    return api_response.to_dict()

  def update_ovs_iface(self, host, iface, *args, payload=None, **kwargs):
    """
    Updates the ovs iface
    Args:
      host(str):
      iface(str):
    Kwargs:
      payload(dict):
    Returns:
      api_response(dict):
    """
    openv_switch_interface = (
      ahv_gateway_client_net_v1.OpenvSwitchInterface.from_dict(payload))
    api_instance = self.get_api_instance(ahv_gateway_client_net_v1, host,
                                         *args, **kwargs)
    api_response = api_instance.update_ovs_iface(iface,
                                                 openv_switch_interface)
    return api_response

  def create_bridge(self, host, *args, payload=None, **kwargs):
    """
    Creates an ovs bridge
    Args:
      host(str):
    Kwargs:
      payload(dict):
    Returns:
      api_response(dict):
    """
    bridge = ahv_gateway_client_net_v1.Bridge.from_dict(payload)
    api_instance = self.get_api_instance(ahv_gateway_client_net_v1, host,
                                         *args, **kwargs)
    api_response = api_instance.create_bridge(bridge)
    return api_response


class Netv0(Base):
  """V0 class"""


class NetMixin(Netv1, Netv0):
  """Mixin class"""


class NetFacade(BaseFacade):
  """HostFacade class"""
  VERSION_MAP = {
    "v0": Netv0,
    "v1": Netv1,
    "default": NetMixin
  }
