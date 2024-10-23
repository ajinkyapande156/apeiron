"""
Copyright (c) 2022 Nutanix Inc. All rights reserved.

Author: arundhathi.a@nutanix.com
"""
# pylint: disable=import-error, fixme, arguments-differ, no-else-return
# pylint: disable=unused-variable, consider-using-in, unnecessary-pass
# pylint: disable=inconsistent-return-statements, too-many-public-methods
# pylint: disable=no-self-use, ungrouped-imports, unused-import
# pylint: disable=useless-import-alias
import re
import time

from libs.ahv.workflows.gos_qual.lib.operating_systems.\
  windowsserver2012 import WindowsServer2012
from libs.ahv.workflows.gos_qual.configs \
  import constants as constants

try:
  from framework.lib.nulog import INFO, WARN, ERROR  # pylint: disable=unused-import
  EXECUTOR = "nutest"
except Exception: # pylint: disable=broad-except
  from libs.ahv.framework.proxy_logging \
    import INFO, WARN, ERROR  # pylint: disable=unused-import
  EXECUTOR = "mjolnir"


class WindowsServer2016(WindowsServer2012):
  """WindowsServer2012 class"""

  SUPPORTED_FEATURES = {
    "hotplug_vnic": True,
    "hotremove_vnic": True,
    "hotplug_scsi_vdisk": True,
    "hotplug_sata_vdisk": True,
    "hotplug_pci_vdisk": False,
    "coldplug_scsi_vdisk": True,
    "coldplug_sata_vdisk": True,
    "coldplug_pci_vdisk": False,
    "hotremove_vdisk": True,
    "hotplug_num_vcpu": True,
    "hotremove_num_vcpu": False,
    "hotplug_num_core_per_vcpu": False,
    "hotremove_num_core_per_vcpu": False,
    "hotplug_vmem": True,
    "hotremove_vmem": False,
    "vtpm": True
  }

  def verify_uefi_boot(self):
    """
    Verify if OS has boot into uefi mode
    Args:
    Returns:
      output(tuple): stdin, stdout, stderr
    """
    cmd = "powershell -command \"$env:firmware_type\""
    res = self.conn.execute(cmd)
    return res.strip().lower()

  def install_virtio_pnputil(self, driver_path, driver_list=None):
    """
         Install/Upgrade Virtio driver via pnputil
          Args:
            driver_path(str): path to installer
            driver_list(dict):
          Returns:
          Raises:
    """
    INFO("Installing Virtio driver via pnp util")
    if not driver_path:
      raise "Driver path not provided"
    if not driver_list:
      driver_list = list(constants.VIRTIO_DRIVERS.keys())
    INFO("Installing Virtio driver via pnputil")
    new_pnputil = False
    cmd = "pnputil -?"
    result, out, err = self.conn.run_shell_command_sync(cmd)
    assert (result == 0 or result == 3010), \
      "Execute pnputil error. err = %s" % err
    if "add-driver" in out and "delete-driver" in out:
      new_pnputil = True
    # Install the new drivers.
    for driver in driver_list:
      driver = driver.lower()
      INFO("Installing driver %s" % driver)
      if new_pnputil:
        cmd = "pnputil /add-driver \"%s%s.inf\" \
           /install > %s.txt" % (driver_path, driver, driver)
      else:
        cmd = "pnputil -i -a \"%s%s.inf\" > %s.txt" % \
              (driver_path, driver, driver)
      task_id = self.conn.run_shell_command_async(cmd)
      # result = gos_util.wait_task_complete(task_id, timeout=60)
      # assert (result == 0 or result == 3010),
      # "Driver installation failed. err = %s" % err
      time.sleep(30)
      cmd = "type %s.txt" % driver
      res, stdout, _ = self.conn.run_shell_command_sync(cmd)
      if driver in stdout and "Driver package added successfully" in stdout \
          and "Added driver packages:  1" in stdout:
        INFO("Driver %s installed successfully" % driver)
      else:
        raise "Driver installation failed"

  def install_os_updates(self, vm, **kwargs):
    """
    install latest updateds on guest operating system
    Args:
      vm(object): vm object
    Returns:
      output(str):
    Raises:
      RuntimeError
    """
    cmd = "wmic qfe list"
    out = self.conn.run_shell_command_sync(cmd_str=cmd)
    INFO(out)
    cmd = 'powershell -command "[Net.ServicePointManager]::SecurityProtocol ' \
          '= [Net.SecurityProtocolType]::Tls12;' \
          '& {&\'Install-PackageProvider\' ' \
          '-Name NuGet -MinimumVersion 2.8.5.201 -Force}"'
    out = self.conn.run_shell_command_sync(cmd_str=cmd)
    INFO(out)
    INFO("Install Module PSWindowsUpdate")
    cmd = 'powershell -command "[Net.ServicePointManager]::SecurityProtocol ' \
          '= [Net.SecurityProtocolType]::Tls12;' \
          '& {&\'Install-Module\' ' \
          '-Name PSWindowsUpdate -Force}"'
    out = self.conn.run_shell_command_sync(cmd_str=cmd)
    INFO(out)
    INFO("List all WindowsUpdate available and install all updates")
    cmd = 'powershell -command "[Net.ServicePointManager]::SecurityProtocol ' \
          '= [Net.SecurityProtocolType]::Tls12;' \
          '& {&\'Get-WindowsUpdate\' -AcceptAll ' \
          '-Install -AutoReboot}"'
    task_id = self.conn.run_shell_command_handsoff(cmd_str=cmd)
    try:
      self.conn.wait_handsoff_task_complete(task_id, timeout=3600)
      res, stdout, _ = self.conn.query_handsoff_task_result(task_id=task_id)
      assert res == 0, "Cmd execution failed: %s" % cmd
      INFO(stdout)
    except:  # pylint: disable=bare-except
      INFO("Vm rebooted!!")

    try:
      res = self.verify_os_boot()
    except:  # pylint: disable=bare-except
      WARN("Waiting for VM to boot up")
    if isinstance(res, dict):
      INFO("Successfully booted after installing updates")
    else:
      raise RuntimeError("Failed to boot after installing updates")

  def install_all_os_updates(self, vm, **kwargs):
    """
    install latest updateds on guest operating system
    Args:
      vm(object): vm object
    Returns:
      output(str):
    Raises:
      RuntimeError
    """
    cmd = "wmic qfe list"
    out = self.conn.run_shell_command_sync(cmd_str=cmd)
    INFO(out)
    cmd = 'powershell -command "[Net.ServicePointManager]::SecurityProtocol ' \
          '= [Net.SecurityProtocolType]::Tls12;' \
          '& {&\'Install-PackageProvider\' ' \
          '-Name NuGet -MinimumVersion 2.8.5.201 -Force}"'
    out = self.conn.run_shell_command_sync(cmd_str=cmd)
    INFO(out)
    INFO("Install Module PSWindowsUpdate")
    cmd = 'powershell -command "[Net.ServicePointManager]::SecurityProtocol ' \
          '= [Net.SecurityProtocolType]::Tls12;' \
          '& {&\'Install-Module\' ' \
          '-Name PSWindowsUpdate -Force}"'
    out = self.conn.run_shell_command_sync(cmd_str=cmd)
    INFO(out)
    while True:
      cmd = 'powershell -command \"Set-ExecutionPolicy Unrestricted\"'
      out = self.conn.run_shell_command_sync(cmd_str=cmd)
      INFO(out)
      INFO("List all WindowsUpdate available")
      cmd = 'powershell -command \"ipmo PSWindowsUpdate;Get-WindowsUpdate\"'
      task_id = self.conn.run_shell_command_handsoff(cmd_str=cmd)
      self.conn.wait_handsoff_task_complete(task_id, 600)
      res, stdout, _ = self.conn.query_handsoff_task_result(task_id=task_id)
      if stdout == "No stdout":
        INFO("No more WindowsUpdate available")
        break
      INFO(stdout)
      INFO("Install all WindowsUpdate available")
      cmd = 'powershell -command \"ipmo PSWindowsUpdate;' \
            'Install-WindowsUpdate -AcceptAll -Install -AutoReboot\"'
      task_id = self.conn.run_shell_command_handsoff(cmd_str=cmd)
      try:
        self.conn.wait_handsoff_task_complete(task_id, 3600)
        res, stdout, _ = self.conn.query_handsoff_task_result(task_id=task_id)
        assert res == 0, "Cmd execution failed: %s" % cmd
        INFO(stdout)
        time.sleep(20)
        self.verify_os_boot()
      except:  # pylint: disable=bare-except
        INFO("Vm rebooted!!")
        self.verify_os_boot()

  def verify_cg_boot(self):
    """
    Verify if OS has booted with credential guard enabled
    Args:
    Returns:
      output(tuple): stdin, stdout, stderr
    Raises:
    """
    cmd = "dir"
    res, stdout, _ = self.conn.run_shell_command_sync(cmd)
    is_cgvm = False
    cred_guard_cmd = "PowerShell Get-CimInstance -ClassName "
    cred_guard_cmd += "Win32_DeviceGuard -Namespace "
    cred_guard_cmd += "root\\Microsoft\\Windows\\DeviceGuard"
    ret, out, _ = self.conn.run_shell_command_sync(cred_guard_cmd)
    assert ret == 0, "Failed to run command in guest"
    ssr_instances = ""
    m1 = re.search(r"SecurityServicesRunning *: \{[0-9 ,]+\}", out)
    if m1 is not None:
      ssr_instances = m1.group(0)
      ssr_instances = ssr_instances.split(':')[1]
    m2 = re.search(r"VirtualizationBasedSecurityStatus *: 2", out)
    if '1' in ssr_instances and m2 is not None:
      INFO("Credential Guard is enabled in Guest: %s" % self.ip)
      return "credentialguard"
    if is_cgvm is False:
      msg = "Credential guard not enabled on guest: %s" % self.ip
      raise Exception(msg)

  def enable_credential_guard(self):
    """
      Enable CG within guest by adding reg entries
    """
    cmd = "REG ADD HKLM\\SYSTEM\\CurrentControlSet\\Control" \
          "\\DeviceGuard /v EnableVirtualizationBasedSecurity /t REG_DWORD /d 1"
    res, stdout, _ = self.conn.run_shell_command_sync(cmd)
    assert res == 0, "Cmd execution failed : %s" % cmd
    cmd = "REG ADD HKLM\\SYSTEM\\CurrentControlSet\\Control" \
          "\\DeviceGuard /v RequirePlatformSecurityFeatures /t REG_DWORD /d 1"
    res, stdout, _ = self.conn.run_shell_command_sync(cmd)
    assert res == 0, "Cmd execution failed : %s" % cmd
    cmd = "REG ADD HKLM\\SYSTEM\\CurrentControlSet\\Control" \
          "\\Lsa /v LsaCfgFlags /t REG_DWORD /d 1"
    res, stdout, _ = self.conn.run_shell_command_sync(cmd)
    assert res == 0, "Cmd execution failed : %s" % cmd

  def get_errored_devices(self, **kwargs):
    """
    Method to get the devices in not OK state
    Args:
    Kargs:
    Returns:
      stdout(bool):
    """
    # WARN("Check for errored devices will be skipped for this OS"
    #      " untill https://bugzilla.redhat.com/show_bug.cgi?id=1377155#c12"
    #      "workaround is added to automation")
    # NOTE: Uncomment following code if winsrv 2016 driver update workaround
    #       is added.
    cmd = "powershell Get-PnpDevice " \
          "-PresentOnly -Status ERROR,DEGRADED,UNKNOWN"
    res, stdout, stderr = self.conn.run_shell_command_sync(cmd)
    if "No matching Win32_PnPEntity objects" in stderr.decode():
      return False
    else:
      return stdout

  def get_hsm_card_names(self):
    """
    Method to get hsm card names in guest
    Args:
    Returns:
      hsm_cards(list):
    """
    search = "Network and Computing Encryption/Decryption Controller"
    cmd = "powershell Get-PnpDevice " \
          "-PresentOnly -Status ERROR"
    result = self.conn.execute(cmd)
    WARN("May not be able to detect multiple HSM cards on windows")
    if search in result:
      return [search]

  def apply_os_workaround(self):
    """
    Apply workaround for incorrect driver binding
    Args:
    Returns:
    """
    if "Windows Server 2016" in self.get_edition_info():
      WARN("Need to apply workaround for "
           "https://bugzilla.redhat.com/show_bug.cgi?id=1377155#c12, otherwise"
           "CPU hotplug will not work")

      INFO("Installing devcon.exe for updating the HID driver")

      cmd = "powershell -command Invoke-WebRequest " \
            "http://10.48.220.201/scripts/winserv2016_tools/devcon.exe " \
            "-O devcon.exe"
      res, stdout, _ = self.conn.run_shell_command_sync(cmd_str=cmd)
      assert res == 0, "Download for devcon.exe failed: %s" % cmd
      INFO(stdout)

      cmd = "powershell -command %cd%\\devcon.exe update " \
            "C:\\Windows\\INF\\machine.inf ACPI\\ACPI0010"
      res, stdout, _ = self.conn.run_shell_command_sync(cmd_str=cmd)
      assert res == 0, "HID Driver update failed"
      INFO(stdout)
      INFO("HID driver update successful")
