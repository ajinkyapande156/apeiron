"""
Copyright (c) 2022 Nutanix Inc. All rights reserved.

Author: pritam.chatterjee@nutanix.com
"""
# pylint: disable=import-error
# pylint: disable=unused-variable
# pylint: disable=no-self-use, ungrouped-imports, unused-import
# pylint: disable=too-many-locals
# pylint: disable=unused-argument, useless-import-alias
# pylint: disable=too-many-statements
# pylint: disable=import-error, fixme, arguments-differ, no-else-return
# pylint: disable=unused-variable, consider-using-in, unnecessary-pass
# pylint: disable=inconsistent-return-statements, too-many-public-methods
# pylint: disable=no-self-use, ungrouped-imports, unused-import
import re
import time

from libs.ahv.workflows.gos_qual.lib.operating_systems. \
  default import Default
from libs.ahv.workflows.gos_qual.configs \
  import constants as constants

try:
  from framework.lib.nulog import INFO, WARN, \
    ERROR

  EXECUTOR = "nutest"
except Exception:  # pylint: disable=broad-except
  from libs.ahv.framework.proxy_logging \
    import INFO, WARN, ERROR

  EXECUTOR = "mjolnir"


class WindowsServer2012(Default):
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
    "vtpm": False
  }

  def verify_os_boot(self, vm=None):
    """
    Verify if the rpc agent is setup properly
    in the guest OS
    Args:
      vm(object): optional
    Returns:
      output(dict): stdout
    """
    res = super(WindowsServer2012, self).verify_os_boot(vm=vm)
    # Adding sleep for Windows only since we have a
    # few scripts running that needs to complete
    INFO("Waiting for sometime before rebooting windows")
    time.sleep(60)
    return res

  def verify_uefi_boot(self):
    """
    Verify if OS has boot into uefi mode
    Args:
    Returns:
      output(tuple): stdin, stdout, stderr
    """
    cmd = "bcdedit | find \"path\""
    res = self.conn.execute(cmd)
    if "winload.exe" in res:
      return "legacy"
    elif "winload.efi" in res:
      return "uefi"

  def verify_secure_boot(self):
    """
    Verify if OS has boot into secure boot mode
    Args:
    Returns:
      output(tuple): stdin, stdout, stderr
    """
    cmd = "powershell -command \"Confirm-SecureBootUEFI\""
    result, stdout, stderr = self.conn.run_shell_command_sync(cmd)
    if result == 0 and stdout.strip() == "True":
      return "secureboot"
    else:
      return "Not supported"

  def verify_vtpm_boot(self):
    """
    Verify if OS has booted with vtpm enabled
    Args:
    Returns:
      output(tuple): stdin, stdout, stderr
    """
    tpm_info = "wmic /namespace:\\\\root\\CIMV2\\Security\\MicrosoftTpm " \
               "path Win32_Tpm get /value"
    result, stdout, stderr = self.conn.run_shell_command_sync(tpm_info)

    if result == 0 and stderr.decode() == "No stderr":
      output = stdout
      sep = "="
      output_dict = dict(list(map(str.strip, sub.split(sep, 1)))
                         for sub in output.split('\n') if sep in sub)
      assert output_dict["IsActivated_InitialValue"] == 'TRUE' \
             and output_dict["IsEnabled_InitialValue"] == 'TRUE', \
        "TPM is not enabled on Guest OS"
      return "vtpm"
    else:
      return "Not supported"

  def verify_cg_boot(self):
    """
    Verify if OS has booted with credential guard enabled
    Args:
    Returns:
      output(tuple): stdin, stdout, stderr
    """
    # fixme: Need to implement for windows
    cmd = "powershell -command \"'CredentialGuard' " \
          "-match ((Get-ComputerInfo).DeviceGuardSecurityServicesConfigured\""
    return "credentialguard"

  def reboot(self):
    """
    Reboot guest OS
    Args:
    Returns:
    """
    cmd = "shutdown /r /t 10"
    res, _, _ = self.conn.run_shell_command_sync(cmd_str=cmd)
    assert res == 0, "Reboot cmd failed"
    # Wait for reboot
    time.sleep(60)
    return res

  def shutdown(self, **kwargs):
    """
    Shutdown guest OS
    Args:
    Returns:
    """
    cmd = "shutdown /s /t 10"
    res, _, _ = self.conn.run_shell_command_sync(cmd_str=cmd)
    assert res == 0, "Shutdown cmd failed"
    # Wait for shutdown
    time.sleep(90)
    return res

  def get_build_info(self):
    """
    Get the guest os build information
    Args:
    Returns:
      output(str): version
    """
    cmd = "systeminfo"
    res = self.conn.execute(cmd)
    build = re.search(r'OS Version:\s+(\d+\.\d+\.\d+).*\n',
                      res.strip()).groups()[0]
    return build

  def get_edition_info(self):
    """
    Get the guest os edition information
    Args:
    Returns:
      output(str): edition
    """
    cmd = "systeminfo"
    res = self.conn.execute(cmd)
    edition = re.search(r'OS Name:\s+([\w\s\.]*)\n',
                        res.strip()).groups()[0]
    return edition

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
    INFO("Installing choco")
    cmd = 'powershell -command \"Set-ExecutionPolicy Bypass ' \
          '-Scope Process -Force;' \
          '[System.Net.ServicePointManager]::SecurityProtocol=' \
          '[System.Net.ServicePointManager]::SecurityProtocol -bor 3072;' \
          'iex ((New-Object System.Net.WebClient).' \
          'DownloadString(\'https://community.chocolatey.org/install.ps1\'))\"'
    res, stdout, stderr = self.conn.run_shell_command_sync(cmd_str=cmd)
    assert res == 0, "Cmd execution failed: %s" % cmd
    INFO(stdout)
    INFO("Installing pwsh portable")
    cmd = "C:\\ProgramData\\chocolatey\\choco install " \
          "powershell.portable -y --force"
    res, stdout, _ = self.conn.run_shell_command_sync(cmd_str=cmd)
    assert res == 0, "Cmd execution failed: %s" % cmd
    INFO(stdout)
    INFO("Reboot after installing pwsh portable")
    self.reboot()
    self.verify_os_boot()
    if "exited 1603" or "exited -1" in stdout:
      INFO("Reinstall on failure of pwsh portable install")
      cmd = "choco install powershell.portable -y --force"
      res, stdout, _ = self.conn.run_shell_command_sync(cmd_str=cmd)
      assert res == 0, "Cmd execution failed: %s" % cmd
      INFO(stdout)
    cmd = "wmic qfe list"
    res, stdout, _ = self.conn.run_shell_command_sync(cmd_str=cmd)
    assert res == 0, "Cmd execution failed: %s" % cmd
    INFO(stdout)
    # cmd = 'C:\\ProgramData\\chocolatey\\lib\\powershell.portable' \
    #       '\\tools\\pwsh\\pwsh.exe -Command' \
    #       ' "& {&\'Install-PackageProvider\' ' \
    #       '-Name NuGet -MinimumVersion 2.8.5.201 -Force}"'
    # res, stdout, _ = self.conn.run_shell_command_sync(cmd_str=cmd)
    # assert res == 0, "Cmd execution failed: %s" % cmd
    # INFO(stdout)
    INFO("Install Module PSWindowsUpdate")
    cmd = 'C:\\ProgramData\\chocolatey\\lib\\powershell.portable' \
          '\\tools\\pwsh\\pwsh.exe -Command' \
          ' "& {&\'Install-Module\' ' \
          '-Name PSWindowsUpdate -Force}"'
    res, stdout, _ = self.conn.run_shell_command_sync(cmd_str=cmd)
    assert res == 0, "Cmd execution failed: %s" % cmd
    INFO(stdout)
    INFO("List all WindowsUpdate available and install all updates")
    cmd = 'C:\\ProgramData\\chocolatey\\lib\\powershell.portable' \
          '\\tools\\pwsh\\pwsh.exe -Command ' \
          '"& {&\'Get-WindowsUpdate\' -AcceptAll ' \
          '-Install -AutoReboot}"'
    task_id = self.conn.run_shell_command_handsoff(cmd_str=cmd)
    try:
      self.conn.wait_handsoff_task_complete(task_id, timeout=3600)
      res, stdout, _ = self.conn.query_handsoff_task_result(task_id=task_id)
      assert res == 0, "Cmd execution failed: %s" % cmd
      INFO(stdout)
    except:  # pylint: disable=bare-except
      INFO("Vm rebooted!!")
    time.sleep(20)
    retries = 60
    interval = 15
    res = None
    while True:
      try:
        res = self.verify_os_boot()
        break
      except:  # pylint: disable=bare-except
        if not retries:
          break
        retries = retries - 1
        WARN("Wait for VM to boot up")
        time.sleep(interval)
    if isinstance(res, dict):
      INFO("Successfully booted after installing updates")
    else:
      raise RuntimeError("Failed to boot after installing updates")

  def get_kernel_info(self):
    """
    Get Guest OS kernel
    Args:
    Returns:
    """
    return "NA"

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
    INFO("Installing choco")
    cmd = 'powershell -command \"Set-ExecutionPolicy Bypass ' \
          '-Scope Process -Force;' \
          '[System.Net.ServicePointManager]::SecurityProtocol=' \
          '[System.Net.ServicePointManager]::SecurityProtocol -bor 3072;' \
          'iex ((New-Object System.Net.WebClient).' \
          'DownloadString(\'https://community.chocolatey.org/install.ps1\'))\"'
    res, stdout, _ = self.conn.run_shell_command_sync(cmd_str=cmd)
    assert res == 0, "Cmd execution failed: %s" % cmd
    INFO(stdout)
    INFO("Installing pwsh portable")
    cmd = "C:\\ProgramData\\chocolatey\\choco install " \
          "powershell.portable -y --force"
    res, stdout, _ = self.conn.run_shell_command_sync(cmd_str=cmd)
    assert res == 0, "Cmd execution failed: %s" % cmd
    INFO(stdout)
    INFO("Reboot after installing pwsh portable")
    self.reboot()
    self.verify_os_boot()
    if "exited 1603" or "exited -1" in stdout:
      INFO("Reinstall on failure of pwsh portable install")
      cmd = "choco install powershell.portable -y --force"
      res, stdout, _ = self.conn.run_shell_command_sync(cmd_str=cmd)
      assert res == 0, "Cmd execution failed: %s" % cmd
      INFO(stdout)
    cmd = "wmic qfe list"
    res, stdout, _ = self.conn.run_shell_command_sync(cmd_str=cmd)
    assert res == 0, "Cmd execution failed: %s" % cmd
    INFO(stdout)
    # cmd = 'C:\\ProgramData\\chocolatey\\lib\\powershell.portable' \
    #       '\\tools\\pwsh\\pwsh.exe -Command' \
    #       ' "& {&\'Install-PackageProvider\' ' \
    #       '-Name NuGet -MinimumVersion 2.8.5.201 -Force}"'
    # out = self.conn.run_shell_command_sync(cmd_str=cmd)
    # INFO(out)
    INFO("Install Module PSWindowsUpdate")
    cmd = 'C:\\ProgramData\\chocolatey\\lib\\powershell.portable' \
          '\\tools\\pwsh\\pwsh.exe -Command' \
          ' "& {&\'Install-Module\' ' \
          '-Name PSWindowsUpdate -Force}"'
    res, stdout, _ = self.conn.run_shell_command_sync(cmd_str=cmd)
    assert res == 0, "Cmd execution failed: %s" % cmd
    INFO(stdout)
    while True:
      cmd = 'C:\\ProgramData\\chocolatey\\lib\\powershell.portable' \
            '\\tools\\pwsh\\pwsh.exe -Command' \
            ' \"Set-ExecutionPolicy Unrestricted\"'
      res, stdout, _ = self.conn.run_shell_command_sync(cmd_str=cmd)
      assert res == 0, "Cmd execution failed: %s" % cmd
      INFO("List all WindowsUpdate available")
      cmd = 'C:\\ProgramData\\chocolatey\\lib\\powershell.portable' \
            '\\tools\\pwsh\\pwsh.exe -Command' \
            ' \"ipmo PSWindowsUpdate;Get-WindowsUpdate\"'
      task_id = self.conn.run_shell_command_handsoff(cmd_str=cmd)
      self.conn.wait_handsoff_task_complete(task_id, 600)
      res, stdout, _ = self.conn.query_handsoff_task_result(task_id=task_id)
      if stdout == "No stdout":
        INFO("No more WindowsUpdate available")
        break
      INFO(stdout)
      INFO("Install all WindowsUpdate available")
      cmd = 'C:\\ProgramData\\chocolatey\\lib\\powershell.portable' \
            '\\tools\\pwsh\\pwsh.exe -Command' \
            ' \"ipmo PSWindowsUpdate;' \
            'Install-WindowsUpdate -AcceptAll -Install -AutoReboot\"'
      task_id = self.conn.run_shell_command_handsoff(cmd_str=cmd)
      try:
        self.conn.wait_handsoff_task_complete(task_id,
                                              timeout=3600 * 2)
        res, stdout, _ = self.conn.query_handsoff_task_result(task_id=task_id)
        assert res == 0, "Cmd execution failed: %s" % cmd
        INFO(stdout)
        time.sleep(20)
        self.verify_os_boot()
      except:  # pylint: disable=bare-except
        INFO("Vm rebooted!!")
        self.verify_os_boot()

  def get_threads_per_core(self):
    """
    Return number of threads per core
    Args:
    Returns:
      threads(int)
    Raises:
    """
    vcpu_cmd = "wmic cpu get NumberOfLogicalProcessors/Format:List"
    res = self.conn.execute(vcpu_cmd)
    vcpu_list = res.strip().split()
    vcpu_count = len(vcpu_list)
    logic_vcpu = int(vcpu_list[0].split("=")[1])
    vcore_cmd = "wmic cpu get NumberOfCores/Format:List"
    res = self.conn.execute(vcore_cmd)
    core_info = res.strip().split()[0]
    cores_per_cpu = int(core_info.split("=")[1])
    threads_per_core = logic_vcpu / cores_per_cpu
    return threads_per_core

  def get_os_architecture(self):
    """
        Return OS Architecture info
        Args:
        Returns:
          os_arch(int)
        Raises:
    """
    # cmd = "powershell -command " \
    #       "\"(Get-WMIObject -Class Win32_Processor).Architecture\""
    # res = self.conn.execute(cmd)
    # #checking only one cpu's arch
    # os_arch = res.strip().split()[1]
    # if os_arch == '9':
    #   arch = "x64"
    # elif os_arch == '0':
    #   arch = "x86"
    # return arch
    # fixme find cmd to do get os_architecture
    return "x86"

  def get_os_bits(self):
    """
       Return OS bits info
       Args:
       Returns:
         os_bits(int)
       Raises:
    """

    cmd = "wmic OS get OSArchitecture"
    res = self.conn.execute(cmd)
    os_bits = res.strip().split()[1]
    os_bits = os_bits.replace("-bit", "")
    return os_bits

  def get_installer_version(self, path):
    """
      Get version info from installer path

      Args:
        path(str) : Path to installer
      Returns:
        version(str) : version info
    """
    INFO("Getting virtio installer version")
    res = re.search(r"Nutanix-VirtIO-(\d\.\d\.\d)\.iso", path)
    search_version = res.group(1)
    INFO("Virtio installer version: %s" % search_version)
    return search_version

  def get_virtio_version(self, driver_name):
    """
      Return Virtio version info
      Args:
        driver_name(str): Name of driver
      Returns:
          virtio version(int)
      Raises:
    """
    retries = 3
    interval = 30
    INFO("Get Virtio Driver version")
    cmd = "powershell.exe \"gwmi win32_PnpSignedDriver | " \
          "where{$_.Description -eq '%s'} | " \
          "select DriverVersion\"" % driver_name
    while True:
      try:
        res = self.conn.execute(cmd)
        res_list = res.strip().splitlines()
        driver_version = res_list[-1].strip()
        INFO("%s , Version : %s" % (driver_name, driver_version))
        return driver_version
      except Exception as ex:  # pylint: disable=broad-except
        if not retries:
          raise ex
        retries = retries - 1
        self.reboot()
        WARN("Wait for VM to boot up")
        time.sleep(interval)

  def check_virtio_is_signed(self, driver_name):
    """
      Return Virtio driver signing info
      Args:
        driver_name(str): Name of driver
      Returns:
          is_signed(str)
      Raises:
    """
    retries = 3
    interval = 30
    INFO("Check Virtio driver signing info")
    cmd = "powershell.exe \"gwmi win32_PnpSignedDriver | " \
          "where{$_.Description -eq '%s'} | " \
          "select IsSigned\"" % driver_name
    while True:
      try:
        res = self.conn.execute(cmd)
        res_list = res.strip().splitlines()
        is_signed = res_list[-1].strip()
        INFO("%s , Signed : %s" % (driver_name, is_signed))
        return is_signed
      except Exception as ex:  # pylint: disable=broad-except
        if not retries:
          raise ex
        retries = retries - 1
        self.reboot()
        WARN("Wait for VM to boot up")
        time.sleep(interval)

  def install_virtio_driver_msi(self, driver_path=None):
    """
         Install/Upgrade Virtio driver via MSI
          Args:
            driver_path(str): path to installer
          Returns:
          Raises:
    """
    INFO("Installing Virtio driver via msi install")
    if not driver_path:
      cmd = "powershell.exe \"$msifiles = Get-ChildItem " \
            "-Path D:\\ -Recurse -Include *.msi;" \
            "foreach ($file in $msifiles) {Write-Host $file.FullName}\""
      res = self.conn.execute(cmd)
      files = res.splitlines()
    os_bits = self.get_os_bits()
    for file_name in files:
      if "64" in file_name:
        driver_path_64_bit = file_name
      else:
        driver_path_32_bit = file_name
    if os_bits == "64":
      driver_path = driver_path_64_bit
    else:
      driver_path = driver_path_32_bit
    cmd = "msiexec /i %s /quiet /log virtio.log" % driver_path
    # cmd = "Start-Process C:\Windows\System32\msiexec.exe " \
    #       "-ArgumentList \"/i %s /quiet\" -wait" % driver_path
    res = self.conn.run_shell_command_async(cmd_str=cmd)
    time.sleep(20)
    self.verify_os_boot()
    cmd = "type virtio.log"
    res, stdout, _ = self.conn.run_shell_command_sync(cmd)
    assert res == 0, "Install of Virtio drivers via msi failed"
    if "error status: 0" in stdout:
      INFO("Install of Virtio drivers via msi succeeded")
    else:
      raise "Install of Virtio drivers via msi failed"

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
      INFO("Installing driver %s", driver)
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
        and "Number successfully imported: 1" in stdout:
        INFO("Driver %s installed successfully" % driver)
      else:
        raise "Driver installation failed"

  def restart_service(self, service_name="winmgmt"):
    """
      Restart a given service

      Args:
        service_name(str): Name of service to restart

      Returns:
        None
    """
    INFO("Restarting service %s within guest" % service_name)
    cmd = "powershell.exe \"restart-service %s -force\"" % service_name
    res, _, _ = self.conn.run_shell_command_sync(cmd)
    assert res == 0, "Restart of service failed"
    cmd = "powershell.exe \"get-service %s | select Status\"" % service_name
    res, stdout, _ = self.conn.run_shell_command_sync(cmd)
    assert "Running" in stdout, "%s service not running" % service_name

  def windows_query_virtio_driver_info(self, vio_drivers):
    """
    Query all the virtio drivers information.

    Args:
      vio_drivers(dict): virtio driver info

    Returns:
      dict: a dictionary of installed virtio driver info
    """
    cmd = "driverquery /v"
    result = self.conn.execute(cmd)
    lines = result.splitlines()
    assert "==" in lines[2], "Couldn't find gauge line"
    cols = lines[2].split()
    pos = [0]
    pp = 0
    for col in cols:
      pp = pp + len(col) + 1
      pos.append(pp)
    for line in lines[3:]:
      name = line[pos[0]:pos[1]].strip()
      name = name.lower()
      if name in vio_drivers:
        vio_drivers[name][constants.STATE] = line[pos[5]:pos[6]].strip()
        vio_drivers[name][constants.IS_RUNNING] = line[pos[6]:pos[7]].strip()
        vio_drivers[name][constants.LINKDATE] = line[pos[12]:pos[13]].strip()
        vio_drivers[name][constants.PATH] = line[pos[13]:pos[14]].strip()
    return vio_drivers

  def get_virtio_driver_info(self, vio_drivers):
    """
      Get driver info of all virtio drivers

      Args:
        vio_drivers(dict): vio driver names dict
      Returns:
        vio_drivers(dict)
    """
    INFO("Getting Virtio driver info for all drivers")
    for driver in vio_drivers:
      vio_drivers[driver][constants.VERSION] = \
        self.get_virtio_version(driver_name=
                                vio_drivers[driver][constants.NAME])
      vio_drivers[driver][constants.IS_SIGNED] = \
        self.check_virtio_is_signed(driver_name=
                                    vio_drivers[driver][constants.NAME])
    vio_drivers = self.windows_query_virtio_driver_info(vio_drivers)
    return vio_drivers

  def install_fio(self):
    """
      Install fio within guest

      Returns:
        None
    """
    INFO("Installing FIO")
    cmd = "fio"
    res, stdout, _ = self.conn.run_shell_command_sync(cmd)
    if res != 0 and stdout != "No stdout":
      INFO("FIO already installed")
    else:
      installer_x64 = "http://endor.dyn.nutanix.com/acro_images/automation/" \
                      "ahv_guest_os/Misc//fio-3.27-x64.msi"
      installer_x86 = "http://endor.dyn.nutanix.com/acro_images/automation/" \
                      "ahv_guest_os/Misc//fio-3.27-x86.msi"
      local_fio_msi = "C:\\Users\\Administrator\\fio.msi"
      os_arch = self.get_os_bits()
      if "64" in os_arch:
        installer_path = installer_x64
      else:
        installer_path = installer_x86
      # Download the installer
      cmd = "powershell -command \"[Net.ServicePointManager]::" \
            "SecurityProtocol = " \
            "[Net.SecurityProtocolType]::Tls12;" \
            "Invoke-WebRequest -Uri %s -OutFile %s\"" % \
            (installer_path, local_fio_msi)
      res, _, _ = self.conn.run_shell_command_sync(cmd)
      assert res == 0, "Download of FIO via msi failed"
      INFO("Installing FIO..")
      # cmd = "msiexec /i %s /quiet" % local_fio_msi
      cmd = "powershell -command \"Start-Process msiexec.exe " \
            "-ArgumentList '/i %s /quiet' -wait\"" % local_fio_msi
      res, _, _ = self.conn.run_shell_command_sync(cmd_str=cmd)
      # fixme add msiexec exited check
      time.sleep(60)
      assert res == 0, "Install of FIO via msi failed"

  def run_io_workload(self, **params):
    """
    Run io workload within Guest

    Returns:
      None
    """
    if not params.get("disk_drive"):
      disk_drive = "C:"
    if not params.get("filename"):
      filename = "fio_write"
    path = disk_drive.replace(":", "\\:")
    cmd = "fio --rw=write --name=test --size=100M " \
          "--filename=%s\\%s --verify=md5 " \
          "--output=%s\\output.txt" % (path, filename, disk_drive)
    INFO("Running FIO workload")
    result, _, stderr = self.conn.run_shell_command_sync(cmd)

    assert result == 0 and stderr.decode() == "No stderr", \
      "Write to file failed. Cmd: %s" % cmd

  def run_fio(self, **kwargs):
    """
    Run FIO workload
    Args:
      kwargs(dict): Params to run fio workload
    Returns:
      None
    """
    self.install_fio()
    INFO("Starting FIO workload")
    name = kwargs.get("name", "test")
    iodepth = kwargs.get("iodepth", "10")
    rw = kwargs.get("rw", "randrw")
    size = kwargs.get("size", "4096m")
    verify = kwargs.get("verify", "md5")
    runtime = kwargs.get("runtime", "86400s")
    bs = kwargs.get("bs", "4k")
    ioengine = "windowsaio"
    cmd = "fio --name=%s --iodepth=%s --rw=%s --size=%s --verify=%s "\
          "--bs=%s --runtime=%s --direct=1 --ioengine=%s --time_based" \
          % (name, iodepth, rw, size, verify, bs, runtime, ioengine)

    self.conn.run_shell_command_async(cmd)
    self.verify_process(process_name="fio")

  def install_dirty_harry(self):
    """
    Install dirty harry on VM
    """
    pass

  def run_dirty_harry(self, **kwargs):
    """
    Run dirty harry workload on VM

    Args:
      (kwargs): Params to run dirty harry workload on VM
    """
    pass

  def verify_process(self, **kwargs):
    """
    Verify if a process is running inside the guest
    Args:
      kwargs(dict): Keyword args
    Returns:
      None
    """
    process_name = kwargs.get("process_name")
    cmd = "powershell -command Get-Process %s" % process_name
    status, stdout, stderr = self.conn.run_shell_command_sync(cmd)

    INFO("Task status=%s, stdout=%s, stderr=%s" % (status, stdout, stderr))
    if status != 0:
      self.conn.run_shell_command_sync("powershell -command systeminfo")
    assert status == 0, "Process %s not running inside guest" % process_name

  def run_io_integrity(self, **params):
    """
    Run io integrity within Guest

    Returns:
      None
    """
    vdisk_file = params.get("vdisk_file")
    file_size_gb = params.get("file_size_gb")
    time_limit_secs = params.get("time_limit_secs")
    INFO("Running IO integrity")
    result, _, stderr = \
      self.conn.run_io_integrity_test_sync(vdisk_file=vdisk_file,
                                           file_size_gb=file_size_gb,
                                           time_limit_secs=time_limit_secs)

    assert result == 0 and stderr.decode() == "No stderr", \
      "Running IO integrity failed."

  def set_disk_online(self):
    """Check status of each disk on Windows.
          In case they are offline, convert them and
          make them online"""
    self.conn.set_disk_online()

  def get_boot_disk(self):
    """
    Get the disk_name which is the boot disk on Windows OS

    Args:

    Returns:
      str: disk name on UVM which is the boot disk

    """
    cmd = "cmd.exe /c wmic diskdrive get Name,Partitions"
    INFO("Running cmd %s on uvm" % cmd)
    res, stdout, _ = self.conn.run_shell_command_sync(cmd)
    assert res == 0, "Error in running cmd : %s on uvm" % cmd
    INFO(stdout)
    disks = stdout.strip().splitlines()
    disks = [disk.strip() for disk in disks[1:] if disk != '']
    for disk in disks:
      disk_info = disk.split()
      partition = int(disk_info[-1])
      disk_name = disk_info[0]
      if partition >= 2:
        INFO("%s is boot disk" % disk_name)
        return disk_name

  def get_disk_drives(self):
    """
     Get all disk drives

     Returns:
      disks(list): List of available disks
    """
    cmd = "wmic diskdrive get Name"
    res, stdout, _ = self.conn.run_shell_command_sync(cmd_str=cmd)
    assert res == 0, "Could not get list of disk drives"
    disks = stdout.strip().splitlines()
    disks = [disk.strip() for disk in disks[1:] if disk != '']
    return disks

  def write_to_disk(self, **params):
    """
      Write contents to file

      Args:
        **params
      Returns:
        None
    """
    filename = params.get("filename", "sample")
    content = params.get("content", "This is a sample text file")
    INFO("Writing to Disk.")
    cmd = "echo %s > %s.txt" % (content, filename)
    result, _, stderr = self.conn.run_shell_command_sync(cmd)
    assert result == 0 and stderr.decode() == "No stderr", \
      "Write to file failed. Cmd: %s" % cmd
    echo_output = "It exists"
    cmd = "if exist %s.txt echo %s" % (filename, echo_output)
    result, stdout, _ = self.conn.run_shell_command_sync(cmd)
    assert result == 0 and echo_output in stdout, \
      "File not found. Cmd: %s" % cmd

  def ping_server(self, server=None):
    """
    Ping a given server

    Args:
      server(str): Server to ping
    Returns:
      None
    """
    if not server:
      server = "google.com"
    cmd = "ping %s" % server
    loss = "100% loss"  # ping failed
    INFO("Ping server: %s" % server)
    # fixme add better validation
    result, stdout, stderr = self.conn.run_shell_command_sync(cmd)
    assert result == 0 and stderr.decode() == "No stderr" \
           and loss not in stdout, \
      "Ping failed. Cmd: %s" % cmd

  def get_nics(self):
    """
    Get network interfaces
    Args:
    Returns:
      nics(list)
    """
    cmd = "ipconfig"
    data = self.conn.execute(cmd)
    nics = re.findall(r'Ethernet adapter(\s\w+):', data) + \
           re.findall(r'Ethernet adapter(\s\w+\s\d+):', data)
    return nics

  def get_nics_with_ips(self):
    """
    Get network interfaces with their ips
    Args:
    Returns:
      nic_ips(dict)
    """
    nics = self.get_nics()
    cmd = "ipconfig"
    data = self.conn.execute(cmd)
    ips = re.findall(r'IPv4 Address[.\s]+:\s(\d+.\d+.\d+.\d+)', data)
    nic_ips = {}
    for i, nic in enumerate(nics):
      nic_ips[nic] = ips[i]
    INFO(nic_ips)
    return nic_ips

  def configure_rp_filter(self):
    """
    Configure rp filter from within guest OS to accept new IPs
    Args:
    Returns:
      output(bool):
    """
    INFO("Nothing to be done for windows 2019 and above")

  def configure_tftp_env(self, **kwargs):
    """
    Manage and bringing up tftp boot env for linux
    by adding the required installation source files
    on tftp server
    Args:
    Returns:
    """
    # NOTE: @arundhathi, please use the wds_rpc object to
    # execute any command, since tftp for windows in on
    # wds and this object `self` is pxe server
    # e.g.
    # extra_params = kwargs.get("extra_params")
    # modules = extra_params.get("wds_rpc")
    # wds.conn.execute(cmd)
    unattend_dest_path = r"C:\RemoteInstall\WdsClientUnattend\unattend.xml"
    extra_params = kwargs.get("extra_params")
    modules = extra_params.get("modules")
    vm_name = extra_params.get("vm_name")
    cache = modules.get("cache")
    image = cache.get_entity(entity_type="rest_image", name="image")
    ctr = modules.get("rest_ctr")
    wds_vm = cache.get_entity(entity_type="pxe_vm", name=vm_name)
    os_name = extra_params.get("os")
    os_bits = extra_params.get("bits")
    unattend = kwargs.get("unattend")
    driver_path = "D:\\%s\\x64\\" % (constants.DRIVER_PATH[os_name])
    img_arch = "x%s" % os_bits
    INFO("Shutdown guest")
    self.shutdown()
    INFO("Attach VIRTIO ISO")
    os_image = image.upload_image(extra_params.get("os") + "_VIRTIO",
                                  kwargs["virtio"], "DISK_IMAGE")[1]

    wds_vm.add_disk(is_cdrom=True,
                    disk_type=kwargs.get("cdrom_bus_type"),
                    clone_container_uuid=ctr.entity_uuid,
                    clone_from_vmdisk=os_image)
    INFO("Attach CDROM")
    os_image = image.upload_image(extra_params.get("os") + "_ISO",
                                  kwargs["cdrom"], "DISK_IMAGE")[1]

    wds_vm.add_disk(is_cdrom=True,
                    disk_type=kwargs.get("cdrom_bus_type"),
                    clone_container_uuid=ctr.entity_uuid,
                    clone_from_vmdisk=os_image)
    wds_vm.power_on(wait_for_ip=True)
    self.verify_os_boot()
    # fixme: Get this info from test
    if self._is_uefi(**kwargs):
      img_arch = "x%sUEFI" % os_bits
    INFO("Copy unattend.xml")
    cmd = "powershell.exe \"Invoke-WebRequest -Uri \"%s\" -OutFile " \
          "%s\"" % (unattend, unattend_dest_path)
    result, _, _ = self.conn.run_shell_command_sync(cmd)
    assert result == 0, "Copying unattend.xml failed"
    INFO("Import Boot image")
    cmd = "wdsutil /Add-Image /ImageFile:%s /ImageType:Boot" \
          % constants.BOOT_WIM
    result, _, _ = self.conn.run_shell_command_sync(cmd)
    assert result == 0, "Import Boot image failed"
    INFO("Create image group")
    cmd = "powershell.exe \"New-WdsInstallImageGroup -Name 'PXEBoot'\""
    result, _, _ = self.conn.run_shell_command_sync(cmd)
    assert result == 0, "Creation of image group failed"
    INFO("Import Install image")
    cmd = "wdsutil /Add-Image /ImageFile:%s /ImageType:Install " \
          "/UnattendFile:%s" \
          % (constants.INSTALL_WIM, unattend_dest_path)
    result, _, _ = self.conn.run_shell_command_sync(cmd)
    assert result == 0, "Import of install image failed"
    for driver in constants.VIRTIO_DRIVERS:
      inf_path = driver_path + constants.VIRTIO_DRIVERS[driver][constants.FILE]
      cmd = "powershell.exe \"Import-WdsDriverPackage " \
            "-Path '%s' -DisplayName " \
            "'%s' -GroupName 'DriverGroup1' " \
            "-Architecture 'x%s'\"" % (inf_path, driver, os_bits)
      result, _, _ = self.conn.run_shell_command_sync(cmd)
      assert result == 0, "Import of drivers failed"
      cmd = "powershell.exe \"Add-WdsDriverPackage -Name '%s' " \
            "-ImageName 'Microsoft Windows Setup (x64)' " \
            "-Architecture 'x%s'\"" % (driver, os_bits)
      result, _, _ = self.conn.run_shell_command_sync(cmd)
      assert result == 0, "Addition of drivers to image failed"
    cmd = "wdsutil.exe /Set-Server /WdsUnattend /Policy:Enabled " \
          "/File:WdsClientUnattend\\unattend.xml /Architecture:%s" % img_arch
    result, _, _ = self.conn.run_shell_command_sync(cmd)
    assert result == 0, "Setting unattend.xml path failed"

  def configure_dnsmasq_env(self, **kwargs):
    """
    Configure dnsmasq for pointing to initrd & kernel image and installation
    source files on tftp server
    Args:
    Returns:
    """
    # NOTE: @arundhathi please review the changes required on pxe server
    #       for windows pxe boot.
    # Commenting this now since this might be required later
    # extra_params = kwargs.get("extra_params")
    # modules = extra_params.get("modules")
    # dnsmasq_conf = "/var/lib/tftpboot/pxelinux/pxelinux.cfg/default"
    # initrd_txt = '  append initrd= ' \
    #              'ip=dhcp inst.repo=%s' % modules["wds_vm"].ip
    # INFO("Updating initrd location and tftp ip in dnsmasq config")
    # cmd = 'sed -i "s@^  append.*@%s@g" %s' % (initrd_txt, dnsmasq_conf)
    # self.conn.execute(cmd)
    #
    # INFO("Updating kernel location in dnsmasq config")
    # kernel_txt = "  kernel "
    # cmd = 'sed -i "s@^  kernel.*@%s@g" %s' % (kernel_txt, dnsmasq_conf)
    # self.conn.execute(cmd)
    #
    # cmd = 'cat %s' % dnsmasq_conf
    # self.conn.execute(cmd)
    #
    # INFO("Updating the tftp root info in dnsmasq config")
    # dnsmasq_conf = "/etc/dnsmasq.conf"
    # tftp_root = r'tftp-root=%s' % modules["wds_vm"].ip
    # cmd = 'sed -i "s@^tftp-root=.*@%s@g" %s' % (tftp_root, dnsmasq_conf)
    # self.conn.execute(cmd)
    # cmd = "cat %s" % dnsmasq_conf
    # self.conn.execute(cmd)
    #
    # INFO("Updating the first boot file name in dnsmasq config")
    # cmd = 'sed -i "s@^dhcp-boot=.*@dhcp-boot=@g" %s' % dnsmasq_conf
    # self.conn.execute(cmd)
    # cmd = 'cat %s' % dnsmasq_conf
    # self.conn.execute(cmd)
    #
    # cmd = 'ps -ef | grep dnsmasq | grep -v grep | awk "{print $2}"'
    # (_, stdout, _) = self.conn.run_shell_command_sync(
    #   cmd)
    # ps = [i.split()[1] for i in stdout.split("\n") if i]
    # cmd = "kill -9 %s" % " ".join(ps)
    # self.conn.execute(cmd)
    #
    # cmd = "systemctl restart dnsmasq.service"
    # self.conn.execute(cmd)
    # cmd = "systemctl status dnsmasq.service"
    # return self.conn.execute(cmd)
    pass

  def verify_syslog_conflicts(self):
    """
    Verify for any conflict messages in syslogs
    Args:
    Returns:
    Raises:
    """
    INFO("Not required for windows")

  def generate_crash_dump(self):
    """
    Generate crash dump manually
    Args:
    Returns:
    Raises:
    """
    notmyfault = "https://download.sysinternals.com/files/NotMyFault.zip"
    local_file_name = "notmyfault.zip"
    notmyfault_cmd = "C:\\Users\\Administrator\\notmyfault64.exe " \
                     "-accepteula /crash"
    INFO("Download NotmyFault")
    cmd = "powershell -command \"Invoke-WebRequest -Uri %s -OutFile %s\"" \
          % (notmyfault, local_file_name)
    result, stdout, stderr = self.conn.run_shell_command_sync(cmd)
    assert result == 0, "Download failed: %s" % cmd
    INFO("Extract NotmyFault.zip")
    cmd = "powershell -command \"Expand-Archive %s" \
          " -DestinationPath C:\\Users\\Administrator -Force\"" \
          % local_file_name
    result, stdout, stderr = self.conn.run_shell_command_sync(cmd)
    assert result == 0, "Extract failed: %s" % cmd
    INFO("Generating crash using NotmyFault")
    cmd = "powershell -command \"%s\"" % notmyfault_cmd
    task_id = self.conn.run_shell_command_handsoff(cmd_str=cmd)
    try:
      self.conn.wait_handsoff_task_complete(task_id, 300)
      result, stdout, stderr = self.conn.query_handsoff_task_result(task_id)
      assert result == 0, "Cmd failed: %s" % cmd
      self.verify_os_boot()
    except:  # pylint: disable=bare-except
      INFO("Could not execute cmd %s!", cmd)

  def install_windbg(self):
    """
    Install Winbdg tool
    Args:
    Returns:
    Raises:
    """
    cmd = 'powershell -command \"Set-ExecutionPolicy Bypass ' \
          '-Scope Process -Force;' \
          '[System.Net.ServicePointManager]::SecurityProtocol=' \
          '[System.Net.ServicePointManager]::SecurityProtocol -bor 3072;' \
          'iex ((New-Object System.Net.WebClient).' \
          'DownloadString(\'https://community.chocolatey.org/install.ps1\'))\"'
    result, stdout, stderr = self.conn.run_shell_command_sync(cmd)
    assert result == 0, "Download failed: %s" % cmd
    INFO(stdout)
    self.reboot()
    self.verify_os_boot()
    cmd = "choco install windows-sdk-10-version-1803-windbg"
    task_id = self.conn.run_shell_command_handsoff(cmd_str=cmd)
    self.conn.wait_handsoff_task_complete(task_id, 300)
    result, stdout, stderr = self.conn.query_handsoff_task_result(task_id)
    assert result == 0, "WDK install failed: %s" % cmd

  def open_crash_dump(self, dump_file=None):
    """
    Open crash dump using Windbg
    Args:
      dump_file(str): Path to dump file
    Returns:
    Raises:
    """
    if not dump_file:
      dump_file = "C:\\Windows\\Memory.DMP"
    log_file = "log.txt"
    windbg_path = "C:\\Program Files (x86)\\Windows Kits\\10" \
                  "\\Debuggers\\x64\\windbg.exe"
    cmd = "del %s" % log_file
    res, stdout, _ = self.conn.run_shell_command_sync(cmd)
    assert res == 0, "Log file deletion failed"
    cmd = "del %s" % dump_file
    res, stdout, _ = self.conn.run_shell_command_sync(cmd)
    assert res == 0, "Dump file deletion failed"
    cmd = "\"%s\" -z %s -logo %s" % (windbg_path, dump_file, log_file)
    task_id = self.conn.run_shell_command_handsoff(cmd_str=cmd)
    self.conn.wait_handsoff_task_complete(task_id, 300)
    result, stdout, stderr = self.conn.query_handsoff_task_result(task_id)
    assert result == 0, "Opening crash dump failed: %s" % cmd
    INFO(stdout)
    cmd = "type %s" % log_file
    res, stdout, _ = self.conn.run_shell_command_sync(cmd)
    if "PARTIALLY CORRUPT" in stdout.upper() or "CORRUPT" in stdout.upper():
      raise "Dump file is CORRUPTED"
    INFO("Dump file not corrupted")

  def enable_credential_guard(self):
    """
      Enable CG within guest by adding reg entries
    """
    WARN("Credential guard is supported only for WS 2016 and above. Check [%s]"
         % "https://learn.microsoft.com/en-us/windows/security/"
           "identity-protection/credential-guard/credential-guard-requirements")

  def get_errored_devices(self, **kwargs):
    """
    Method to get the devices in not OK state
    Args:
    Kargs:
    Returns:
      stdout(bool):
    """
    WARN("Check for errored devices will be skipped for this OS"
         " as Get-PnpDevice command is not supported")

  def disable_auto_upgrades(self):
    """
    Method to disable automatic updating of guest OS
    Args:
    Kwargs:
    Returns:
      bool
    """
    cmd = "Net stop wuauserv"
    INFO("Stopping the Windows Update Service")
    res, stdout, stderr = self.conn.run_shell_command_sync(cmd)
    if "No stderr" in stderr.decode() and "stopped successfully" in stdout:
      INFO("Windows Update Service stopped successfully")
    elif "The Windows Update service is not started" in stderr.decode():
      INFO("Windows Update Service is already stopped")
    else:
      ERROR("Failed to stop automatic updates")
      return False
    cmd = 'sc config "wuauserv" start=disabled'
    INFO("Disabling the Windows Update Service")
    res, stdout, stderr = self.conn.run_shell_command_sync(cmd)
    if "No stderr" in stderr.decode() and "ChangeServiceConfig SUCCESS" \
      in stdout:
      INFO("Windows Update Service disabled successfully")
    else:
      ERROR("Failed to disable automating updates")
      return False
    return True
