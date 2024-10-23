"""
Copyright (c) 2024 Nutanix Inc. All rights reserved.

Author: pritam.chatterjee@nutanix.com
"""

#pylint: disable = unused-import
#pylint: disable = no-member

# SDK imports
import ahv_gateway_client_host_v1
import ahv_gateway_client_host_v0

from libs.gateway.sdk_clients.base_client import (
  Base, BaseFacade)


class Hostv1(Base):
  """V1 class"""
  def get_host_version(self, host, *args, **kwargs):
    """
    Retrieves the host version
    Args:
      host(str): Host ip
    Returns:
      api_response(dict):
    """
    api_instance = self.get_api_instance(ahv_gateway_client_host_v1, host,
                                         *args, **kwargs)
    api_response = api_instance.get_host_version()
    return api_response.to_dict()

  def get_hostname(self, host, *args, **kwargs):
    """
    Retrieves the hostname
    Args:
      host(str): Host ip
    Returns:
      api_response(dict):
    """
    api_instance = self.get_api_instance(ahv_gateway_client_host_v1, host,
                                         *args, **kwargs)
    api_response = api_instance.get_hostname()
    return api_response.to_dict()

  def get_passwd_info(self, host, user, *args, **kwargs):
    """
    Retrieves the user passwd info
    Args:
      host(str): Host ip
      user(str):
    Returns:
      api_response(dict):
    """
    api_instance = self.get_api_instance(ahv_gateway_client_host_v1, host,
                                         *args, **kwargs)
    api_response = api_instance.get_passwd_info(user)
    return api_response.to_dict()

  def update_passwd(self, host, user, new_passwd, old_passwd, *args, **kwargs):
    """
    Updates the user password
    Args:
      host(str): Host ip
      user(str):
      new_passwd(str):
      old_passwd(str) :
    Returns:
      api_response(dict):
    """
    payload = {
      "new_password": new_passwd,
      "old_password": old_passwd
    }
    api_instance = self.get_api_instance(ahv_gateway_client_host_v1, host,
                                         *args, **kwargs)
    api_response = api_instance.update_passwd(user, payload)
    return api_response

class Hostv0(Base):
  """V0 class"""


class HostMixin(Hostv1, Hostv0):
  """Entrypoint Class"""



class HostFacade(BaseFacade):
  """HostFacade class"""
  VERSION_MAP = {
    "v0": Hostv0,
    "v1": Hostv1,
    "default": HostMixin
  }
