"""
Copyright (c) 2024 Nutanix Inc. All rights reserved.

Author: amit.ghosh@nutanix.com
"""
#pylint:disable=no-self-use, no-member

from framework.lib.nulog import INFO
from libs.gateway.gateway_interface import \
GatewayClientInterface


class HostPasswordWF:
  """
  HostPasswordWorkflows class
  """
  def __init__(self, cluster):
    """
    Initialize object
    Args:
      cluster(object): Nutest cluster object
    """
    self.cluster = cluster
    self.hosts = self.cluster.hypervisors
    self.host_under_test = self.hosts[0]
    self.gw_obj = GatewayClientInterface(self.cluster)

  def get_password_info(self, user="admin", cert_type="Security"):
    """
    This method will get password metadata
    Args:
      user(str): user whose password metadata is retrieved
      cert_type(str): certificate type from cluster
    Returns:
      password metedata json
    Raises:
    """
    INFO("Trying to retrieve user password metadata")
    response = self.gw_obj.get_passwd_info(self.host_under_test.ip, \
    user=user, cert_type=cert_type)
    return response

  def set_password(self, present_pwd, pwd_to_set, \
  user="admin", cert_type="Security"):
    """
    This method will set password for user
    Args:
      present_pwd(str): current password for the user
      pwd_to_set(str): new password
      user(str): user whose password metadata is retrieved
      cert_type(str): certificate type from cluster
    Returns:
      None if successful else response json
    Raises:
    """
    INFO("Trying to set user password")
    response = self.gw_obj.update_passwd(self.host_under_test.ip, user=user, \
    cert_type=cert_type, new_passwd=pwd_to_set, old_passwd=present_pwd)
    return response

  def force_pwd_reset(self, user="admin"):
    """
    This method will set password for user back to default
    Args:
      user(str): user whose password metadata is retrieved
    Returns:
      None
    Raises:
    """
    INFO("Resetting password to RDM default")
    #Using host.execute, may need change when blocked
    force_payload = f"{user}:RDMCluster.123"
    self.host_under_test.execute(f"echo {force_payload} | chpasswd")
    