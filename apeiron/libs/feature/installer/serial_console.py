"""
Copyright (c) 2024 Nutanix Inc. All rights reserved.

Author: umashankar.vd@nutanix.com

"""
#pylint: disable=no-self-use, invalid-name, using-constant-test, no-else-return
# pylint: disable=unused-variable, unused-import, no-member
# pylint: disable=too-many-branches, too-many-statements, unused-argument
# pylint: disable=ungrouped-imports, line-too-long, too-many-locals
# pylint: disable=broad-except, singleton-comparison
#ahv_conn.execute("mkdir neg_scenario;cd neg_scenario;mkdir metadata;echo '%s' > metadata/installer.json;wget http://endor.dyn.nutanix.com/builds/ahv-builds/10/10.0/10.0-663/iso/AHV-DVD-x86_64-10.0-663.iso;%s" %(neg_json["incorrect_ip"],command))
try:
  from framework.lib.nulog import INFO, WARN, ERROR, \
  STEP
  EXECUTOR = "nutest"
except Exception:  # pylint: disable=broad-except
  from libs.ahv.framework.proxy_logging \
  import INFO
  EXECUTOR = "mjolnir"
import framework.operating_systems.operating_system.linux_operating_system \
  as LinuxOperatingSystem


class MonitorConsole():
  """
  Class for monitoring serial console of Cisco server
  """
  def __init__(self):
    """
    func to initialize library to generate iso
    Args:
    Returns:
    Raises:
    """
    self.ipmi = "10.49.104.169"
    self.remote_server_ip = '10.40.121.216'

  def validate_error(self):
    """
    Args:
    Returns:
    Raises:
    """
    ahv_conn_nfs = LinuxOperatingSystem.LinuxOperatingSystem\
      (self.remote_server_ip, 'nutanix', 'nutanix/4u')
    command = "sshpass -p admin ssh admin@%s > sol.txt" + self.ipmi
    ahv_conn_nfs.execute(command)
    INFO("Redirecting output to file on remote server")
    INFO("retrieving info from remote server")
    INFO("Checking if error message is present")
