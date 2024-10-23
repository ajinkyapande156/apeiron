"""
Copyright (c) 2022 Nutanix Inc. All rights reserved.

Author: harunadhbabu.madasu@nutanix.com
"""
# pylint: disable=import-error, unused-variable, no-else-return
# pylint: disable=inconsistent-return-statements

from framework.lib.nulog import INFO
from libs.ahv.workflows.gos_qual.lib.operating_systems.\
  windows10 import Windows10

class Windows11(Windows10):
  """Windows11 class"""
  def get_os_bits(self):
    """Method to check if wmic tool is present
       Args:
       Returns:
         os_bits(int)
    """
    try:
      INFO("Check if wmic present")
      cmd = "wmic OS get OSArchitecture"
      res = self.conn.execute(cmd)
      if "OSArchitecture" in res:
        INFO("Wmic is present by default, so ignore the re-install")
        return super(Windows11, self).get_os_bits()

    except AssertionError:
      INFO("Wmic not present by default, so installing the Wmic tool")
      cmd = "DISM /Online /Add-Capability /CapabilityName:WMIC~~~~"
      res = self.conn.run_shell_command_sync(cmd)
      return super(Windows11, self).get_os_bits()
