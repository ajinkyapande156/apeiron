"""
Copyright (c) 2022 Nutanix Inc. All rights reserved.

Author: pritam.chatterjee@nutanix.com
"""
# pylint: disable=import-error
import time
from framework.lib.nulog import INFO, ERROR, STEP, \
  WARN  # pylint: disable=unused-import
from libs.ahv.workflows.gos_qual.lib.operating_systems.\
  rhel79 import Rhel79


class OracleLinux78(Rhel79):
  """OracleLinux80 class"""

  def apply_os_workaround(self):
    """
    Apply workaround for incorrect driver binding
    Args:
    Returns:
    """
    INFO("Applying workaround for OEL vnic ip assignments")
    self.configure_rp_filter()

  def get_nics_with_ips(self):
    """
    Get network interfaces with their ips
    Args:
    Returns:
      nic_ips(dict)
    """
    nics = self.get_nics()
    # removes bridge interfaces
    nics = [i for i in nics if "virbr" not in i]
    nic_ips = {}
    retries = 10
    wait = 3
    for nic in nics:
      nic_ips[nic] = None
      while retries:
        nic_ips[nic] = self.parse_interface_ipv4(nic)
        if not nic_ips[nic]:
          WARN("Did not get IP yet, trying DHCLIENT as workaround")
          self.conn.execute("dhclient -I %s" % nic)
          retries = retries - 1
          time.sleep(wait)
        else:
          break
    return nic_ips
