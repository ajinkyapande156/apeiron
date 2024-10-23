"""
Copyright (c) 2022 Nutanix Inc. All rights reserved.

Author: amit.ghosh@nutanix.com
"""
# pylint: disable = no-self-use, unused-import, no-member
from datetime import datetime
import os
from framework.operating_systems.operating_system import OperatingSystem
from framework.lib.nulog import INFO, STEP


class Screenshot:
  """
   Class to create VM console screeshot and copy to log
  """

  @staticmethod
  def take_screenshot(vm):
    """
      Take VM screenshot and copy to log
      Args:
      vm(object): vm object
      Returns:
      None
    """
    now = datetime.now()
    formatted_time = now.strftime('%H:%M:%S')
    vm_uuid = vm.uuid
    screen_name = f'{vm_uuid}'+formatted_time
    cmd_screenshot = f"virsh screenshot {vm_uuid} /home/{screen_name}.png"
    host = vm.get_hypervisor()
    INFO("Taking screenshot of VM")
    screen = host.execute(cmd_screenshot)
    assert not screen['status'], "unable to run command to get screenshot"
    host_ip = host.ip
    log_file_path = os.path.join(os.environ.get("NUTEST_LOGDIR"))
    prefix = "sshpass -p 'RDMCluster.123' "
    #Using SSH to host using root password, needs \
    #change when root access is locked
    cmd = (f"{prefix} scp -o StrictHostKeychecking=no -r "
           f"root@{host_ip}:/home/{screen_name}.png {log_file_path}")
    result = OperatingSystem().local_execute(cmd)
    assert not result['status'], "Failed to copy screenshot to nutest"
    screenshot = os.path.join(log_file_path, screen_name + '.png')
    result = OperatingSystem().local_execute(f"chmod +777 {screenshot}")
    assert not result['status'], (f"Failed to update permissions on "
                                  f"screenshot {screenshot}")
    STEP(f"Copied VM screenshot to {screenshot}")
