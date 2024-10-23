"""
Copyright (c) 2024 Nutanix Inc. All rights reserved.

Author: pritam.chatterjee@nutanix.com
"""
# pylint: disable=arguments-differ
import os
import time
from framework.lib.nulog import WARN
from framework.exceptions.interface_error import NuTestCommandExecutionError
import workflows.acropolis.mjolnir.gateway.constants as const


class AbstractHostGatewayConfigAuth:
  """AbstractHostGatewayConfigAuth"""

  @staticmethod
  def is_setup(*args, **kwargs):
    """
    Validate if already setup and ignore re-setting up
    Args:
    Kwargs:
    Returns:
    Raises:
    """
    raise NotImplementedError

  @staticmethod
  def setup_auth(*args, **kwargs):
    """
    Setups up host gateway for proper authentication
    Args:
    Kwargs:
    Returns:
    Raises:
    """
    raise NotImplementedError

  @staticmethod
  def restore_auth(*args, **kwargs):
    """
    Restore the auth to normal/default if applicable
    Args:
    Kwargs:
    Returns:
    Raises:
    """
    raise NotImplementedError


class HostGatewayConfigNoAuth(AbstractHostGatewayConfigAuth):
  """HostGatewayConfigNoAuth"""
  BACKUP = "/etc/ahv-gateway/config/ahv_gateway.yaml.org"
  DEST = "/etc/ahv-gateway/config/ahv_gateway.yaml"

  @staticmethod
  def setup_auth(host, config, *args, **kwargs):
    """
    Disables gateway certificate authentication in all hosts of the cluster
    Args:
      host(str):
      config(dict):
    Kwargs:
    Returns:
    Raises:
    """
    if not HostGatewayConfigNoAuth.is_setup(host):
      script = "http://10.48.220.201/scripts/gateway_py3_sdk/disable-auth.sh"
      cmd = f'wget {script}; sh disable-auth.sh'
      result = host.execute(cmd)
      assert result['status'] == 0, \
        "Failed to download disable and run auth script to host"
      cmd = f'systemctl restart ahv-gateway'
      result = host.execute(cmd)
      assert result['status'] == 0, \
        "Failed to restart gateway service after restoring auth settings"
      # wait for gateway to be up in 2secs
      time.sleep(2)
    config.verify_ssl = False
    return config

  @staticmethod
  def restore_auth(host, *args, **kwargs):
    """
    Enables gateway certificate authentication in all hosts of the
    cluster to normal/default
    Args:
      host(str):
    Kwargs:
    Returns:
    Raises:
    """
    cmd = f'cp {HostGatewayConfigNoAuth.BACKUP} {HostGatewayConfigNoAuth.DEST}'
    result = host.execute(cmd)
    assert result['status'] == 0, \
      "Failed to restore the original ahv gateway config file"
    cmd = f'rm -rf {HostGatewayConfigNoAuth.BACKUP}'
    result = host.execute(cmd)
    assert result['status'] == 0, \
      "Failed to delete the backup auth settings file"
    cmd = f'systemctl restart ahv-gateway'
    result = host.execute(cmd)
    assert result['status'] == 0, \
      "Failed to restart gateway service after restoring auth settings"

  @staticmethod
  def is_setup(host):
    """
    Validate if already setup and ignore re-setting up
    Args:
      host(str):
    Kwargs:
    Returns:
    Raises:
    """
    cmd = f'ls {HostGatewayConfigNoAuth.BACKUP}'
    try:
      host.execute(cmd)
      return True
    except NuTestCommandExecutionError:
      return False


class HostGatewayConfigCertAuth(AbstractHostGatewayConfigAuth):
  """HostGatewayConfigCertAuth"""

  @staticmethod
  def setup_auth(config, *args, **kwargs):
    """
    Setups up host gateway for certification based authentication
    Args:
      config(object): gateway config object
    Kwargs:
      service_name(str): Polaris|Genesis|Acropolis etc.
                         All services listed under /home/certs/ dir on CVM
    Returns:
    Raises:
    """
    if not os.path.exists(const.CERT_LOC):
      os.makedirs(const.CERT_LOC)
    cert_type = kwargs.pop('cert_type', "default")  # change this later
    if cert_type == "default":
      cert_file_loc = os.path.join(const.CERT_LOC, "default")
    else:
      cert_file_loc = os.path.join(const.CERT_LOC, cert_type + 'Service')
    ssl_ca_cert, cert_file, key_file = (
      HostGatewayConfigCertAuth.is_setup(cert_file_loc))

    config.ssl_ca_cert = ssl_ca_cert
    config.cert_file = cert_file
    config.key_file = key_file
    WARN(f'Using {cert_type} certifcates for gateway authentication')
    WARN(f'Using ssl_ca_cert: {config.ssl_ca_cert}')
    WARN(f'Using cert_file: {config.cert_file}')
    WARN(f'Using key_file: {config.key_file}')
    return config

  @staticmethod
  def is_setup(cert_dir):
    """
    Validate if already setup and ignore re-setting up
    Args:
      cert_dir(str):
    Kwargs:
    Returns:
    Raises:
    """
    assert os.path.exists(cert_dir), ("Certificate folder is not available in "
                                      "nutest")
    cert_files = os.listdir(cert_dir)
    if "default" in cert_dir:
      ssl_ca_cert = [cert for cert in cert_files if 'CA' in cert][0]
    else:
      ssl_ca_cert = os.path.join(const.CERT_LOC, "ca.pem")
    cert_file = [cert for cert in cert_files if cert.endswith(".crt")
                 and not 'CA' in cert][0]
    key_file = [cert for cert in cert_files if cert.endswith(".key")][0]
    return (os.path.join(cert_dir, ssl_ca_cert),
            os.path.join(cert_dir, cert_file),
            os.path.join(cert_dir, key_file))
