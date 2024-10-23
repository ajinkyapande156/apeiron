"""
Copyright (c) 2023 Nutanix Inc. All rights reserved.

Author: pritam.chatterjee@nutanix.com
"""
# pylint: disable=import-error, unused-import, unused-argument, no-member
# pylint: disable=wrong-import-order, no-self-use
import ahv_gateway_client_host_v1
from pprint import pprint
import json
import sys
from ahv_gateway_client_host_v1.apis.tags import default_api
from framework.lib.nulog import DEBUG


class Base:
  """Base class"""

  def __init__(self, **kwargs):
    """ kwargs:
    Initialize the host configuration
    """
    self.port = kwargs.get("port", 7030)
    self.host = kwargs.get("host")
    self.cert_file = kwargs.get("cert_file")
    self.key_file = kwargs.get("key_file")
    self.ssl_ca_cert = kwargs.get("ssl_ca_cert")
    self.host_uri = None

  @property
  def tls(self):
    """
    tls property
    Returns:
    """
    return self._tls

  @tls.setter
  def tls(self, tls):
    """
    tls setter
    Args:
      tls(bool):
    Raises:
    """
    if tls:
      raise NotImplementedError

  @property
  def host(self):
    """
    host property
    Returns:
    """
    return self._host

  @host.setter
  def host(self, host):
    """
    Setter Host
    Args:
      host(str): Host IP address
    """
    self._host = "http://%s:%s/api" % (host, self.port)
    with ahv_gateway_client_host_v1.Configuration(self.host) as client:
      response = client.get_host_info()
      DEBUG(response)

  @property
  def port(self):
    """
    Property Port
    Returns:
    """
    return self._port

  @port.setter
  def port(self, port):
    """
    Port setter
    Args:
      port(int):
    """
    self._port = port
