"""
Copyright (c) 2023 Nutanix Inc. All rights reserved.

Author: pritam.chatterjee@nutanix.com
"""
# pylint: disable=import-error, unused-import, unused-argument, no-member
# pylint: disable=wrong-import-order
import json
import sys
from functools import wraps
from framework.lib.nulog import DEBUG
from libs.framework import mjolnir_entities as entities


class BaseRaw:
  """Base class"""

  def __init__(self, **kwargs):
    """
    Initialize the host configuration
    Args:
    Kwargs:
      cluster(object): NOS cluster object.
      port(str): Gateway API port
      host(str): Host IP
      cert_file(str): Cert file for gateway auth
      key_file(str): Key file for gateway auth

    """
    self.cluster = kwargs.get("cluster", entities.ENTITIES.get("pe"))
    self.port = kwargs.get("port", 7030)
    self.cert_file = kwargs.get(
      "cert_file", "/home/certs/AcropolisService/AcropolisService.crt")
    self.key_file = kwargs.get(
      "key_file", "/home/certs/AcropolisService/AcropolisService.key")
    self.ssl_ca_cert = kwargs.get(
      "ssl_ca_cert", "/home/certs/ca.pem")
    self.host = kwargs.get("host")
    # self.tls = kwargs.get("tls", False)
    self.host_uri = None

  @property
  def host(self):
    """
    Property Host
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
    cmd = "curl --cert %s --key %s --cacert %s -sk " \
          "https://%s:%s/api/host/v1/info" \
          % (self.cert_file, self.key_file, self.ssl_ca_cert, host, self.port)
    response = self.cluster.execute(cmd)
    assert response['stdout'], "Failed to get use gateway API %s" % response
    DEBUG("Connected to gateway on host %s successfully: %s"
          %(host, json.loads(response['stdout'])))
    self._host = "curl --cert %s --key %s --cacert %s -sk https://%s:%s/api/" \
                    % (self.cert_file, self.key_file, self.ssl_ca_cert,
                       host, self.port)
    DEBUG("Setting up host uri as: %s" % self.host)


  @property
  def port(self):
    """
    Property port
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

  @staticmethod
  def process_response(func):
    """
    Decorator to process the response for raw gateway request
    Args:
      func(object):
    Returns:
      wrapper(object):
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
      """
      Internal wrapper function
      Returns:
      """
      # obj = args[0]
      response = func(*args, **kwargs)
      return json.loads(response['stdout'])
    return wrapper
