"""
Copyright (c) 2022 Nutanix Inc. All rights reserved.

Author: umashankar.vd@nutanix.com

Factory method for providing object/functions of hyperv type
"""
# pylint: disable=import-error, fixme, too-many-statements,
# pylint: disable=protected-access, unused-import
# pylint: disable=too-many-locals, unused-variable, unused-import
# pylint: disable=no-member
import re
import time
try:
  from framework.lib.nulog import INFO, WARN, ERROR, \
    STEP
  EXECUTOR = "nutest"
except Exception:  # pylint: disable=broad-except
  from libs.ahv.framework.proxy_logging \
    import INFO, ERROR, STEP
  EXECUTOR = "mjolnir"
from libs.framework import mjolnir_entities as entities
#from framework.entities.vm.vm import Vm as virtual_machine
from libs.feature.vm_lib.vm_factory import VmFactory
from libs.feature.nested_virtualization.\
  nested_hypervisors.abstracts import AbstractNestedHypervisor
from libs.feature.nested_virtualization \
  import constants
#from workflows.acropolis.ahv.acro_gos_utility import AcroGOSUtilv2


class NestedHyperv(AbstractNestedHypervisor):
  """NestedHyperv class"""
  def __init__(self, cluster):
    """
    Create hyperv class instance
    Args:
      cluster(object): nutest cluster object
    """
    INFO("Initialising Nested HyperV class")
    self.cluster = cluster
    self.hyper_vm = None
    self._os = None
    self._l2_os = None
    self.vm_entity = entities.ENTITIES.get("rest_vm")
    self.acrogosutilv2_entity = entities.ENTITIES.get("rpc_vm")
    self.acrogosutil_entity = entities.ENTITIES.get("rpc")
    self.acli_vm_cls = entities.ENTITIES.get("acli_vm")
    self.rest_vm_cls = entities.ENTITIES.get("rest_vm")
    self.edit_args = {}

  def create(self, **params):
    """
    Create nested hypervisor
    Args:
      params
    Returns:
    Raises:
    """
    self.hyper_vm = VmFactory(**params)
    assert (len(self.hyper_vm.get_disks())) == 1, \
    "Failed to add boot disk to VM"
    self.hyper_vm.power_on(wait_for_ip=True, timeout=900)
    self._os = self.acrogosutilv2_entity(self.hyper_vm)
    self._enable_hyperv()
    return self.hyper_vm

  def get_status(self):
    """
    Return the state of hyper-v
    Args:
    Returns:
    """
    cmd = "powershell.exe \"Get-WindowsOptionalFeature -FeatureName " \
            "Microsoft-Hyper-V-All -Online | select state\""
    res, stdout, _ = self._os.run_shell_command_sync(cmd)
    if "Enabled" in stdout:
      status = "Enabled"
    else:
      status = "Not enabled"
    return status

  def create_hypervisor_vm(self, **kwargs):
    """
    create_hypervisor_vm
    Args:
    Returns:
    """
    self.hyper_vm = VmFactory(**kwargs)

  def create_l2_network(self, **kwargs):
    """
    Checks for presence of switch, if not creates one by name Extswitch
    Args:
      kwargs: switch name
    Returns:
    """
    switch_name = kwargs.get("switch_name")
    cmd_get_vm_switch = "powershell.exe \"Get-Vmswitch | select Name\""
    res, stdout, _ = self._os.run_shell_command_sync(cmd_get_vm_switch)
    if switch_name not in stdout:
      #need to fix timeout since below instruction would
      #restart the network and suspends conn
      INFO("External switch is not present on L1 host, creating one!")
      INFO("Getting list of adapters on the guest")
      #cmd_get_phy_adap = "powershell.exe \"(Get-Netadapter
      #-InterfaceDescription \"Intel*\" | select Name).name\""
      cmd_get_phy_adap = "powershell.exe \"(Get-Netadapter \
                        -Name \"Ethernet*\" | select Name).name\""
      res, stdout, _ = self._os.run_shell_command_sync(cmd_get_phy_adap)
      interface_name = stdout.strip()
      cmd_create_vswitch = "powershell.exe New-VMSwitch -name %s \
      -NetAdapterName '%s' -AllowManagementOS $true"\
      %(switch_name, interface_name)
      #Using handsoff mode as creating vswitch will reset mgmt int on the host
      #however we may see timeout in subsequent download operation - may need to
      #increase timeout from 180 sec to 240 sec
      #depending on size of vhd file[22 GB in this case]
      task_id = self._os.run_shell_command_handsoff(cmd_str=cmd_create_vswitch)
      try:
        self._os.wait_handsoff_task_complete(task_id, 300)
      except:  # pylint: disable=bare-except
        WARN("Could not add switch!!")
    else:
      INFO("Switch already exists!!")

  def get_l2_vm_power_state(self, **kwargs):
    """
    returns power state of the guest running on a nested AHV Guest
    Args:
      kwargs(str):
    Returns:
    """
    l2_vm_name = kwargs.get("l2_vm_name")
    cmd_power_state = "powershell.exe \"Get-VM -Name %s | select state\""\
    %l2_vm_name
    res, stdout, _ = self._os.run_shell_command_sync(cmd_power_state)
    return stdout

  def vm_l2_deploy(self, **kwargs):
    """
    Deploy a L2 guest by downloading it and use it as a boot disk -
    url is hard coded for now. Shall move this to configs
    Args:
      kwargs(str):
    Returns:
    """
    guest = kwargs.get("guest")
    l2_vm_name = kwargs.get("l2_vm_name")
    switch_name = kwargs.get("switch_name")
    cmd_download_vhd = """powershell.exe Measure-Command{ $wc = \
    New-Object System.Net.webclient;$wc.DownloadFile('%s','C:\\%s.vhdx')}"""\
                        %(constants.VHD_PATH[guest], l2_vm_name)
    task_id = self._os.run_shell_command_async(cmd_str=cmd_download_vhd)
    result = self._os.wait_task_complete(task_id, 600, interval=30)
    assert result == 0, "Could not download VHD file for %s VM " \
                        "within stipulated time!!"%l2_vm_name
    INFO("VHD file downloaded successfully")
    cmd_create_vm = """powershell.exe New-Vm -name %s -MemoryStartupBytes 4GB \
    -BootDevice VHD -vhdpath C:\\%s.vhdx -Generation 2 -Switchname %s"""\
                  %(l2_vm_name, l2_vm_name, switch_name)
    res, stdout, _ = self._os.run_shell_command_sync(cmd_create_vm)
    cmd_start_vm = "powershell.exe Start-Vm %s"%l2_vm_name
    res, stdout, stderr = self._os.run_shell_command_sync(cmd_start_vm)
    assert res == 0, "Power On L2 VM failed"
    INFO("Checking if VM boots up and is assigned an IP address")
    #time.sleep(240)
    ip_addr = self.get_vm_l2_ip(**kwargs)
    return l2_vm_name, ip_addr

  def vm_l2_poweron(self, **kwargs):
    """
    Performs power on operation on a guest running on a nested AHV guest
    Args:
      kwargs(str):
    Returns:
    """
    l2_vm_name = kwargs.get("l2_vm_name")
    current_power_state = self.get_l2_vm_power_state(**kwargs)
    if "Off" in current_power_state:
      cmd_poweron = "powershell.exe \"Start-VM -Name %s\""%l2_vm_name
      task_id = self._os.run_shell_command_handsoff(cmd_str=cmd_poweron)
    else:
      WARN("VM not in right state to perform the operation")

  def vm_l2_poweroff(self, **kwargs):
    """
    Gracefully shutsdown the VM, ensures it is powered off by polling
    Args:
      kwargs(str):
    Returns
    """
    l2_vm_name = kwargs.get("l2_vm_name")
    current_power_state = self.get_l2_vm_power_state(**kwargs)
    if "Running" in current_power_state:
      cmd_poweroff = "powershell.exe \"Stop-VM -Force -Name %s\""%l2_vm_name
      task_id = self._os.run_shell_command_handsoff(cmd_str=cmd_poweroff)
      retry = 10
      while retry > 0:
        current_power_state = self.get_l2_vm_power_state(**kwargs)
        if "Running" in current_power_state: #pylint: disable=no-else-continue
          INFO("Waiting for 30s for L2 VM to gracefully shutdown!")
          retry = retry - 1
          time.sleep(30)
          continue
        elif "Off" in current_power_state:
          INFO("VM shutdown successfully!")
          break
      assert "Off" in current_power_state, "Failed to shutdown the VM"
      INFO("L2 guest %s was successfully shutdown"%l2_vm_name)
    else:
      WARN("VM not in right state to perform the operation")

  def vm_l2_reboot(self, **kwargs):
    """
    Reboots a Nested guest after ensuring it is in ON state
    Args:
      kwargs
    Returns:
    """
    l2_vm_name = kwargs.get("l2_vm_name")
    current_power_state = self.get_l2_vm_power_state(**kwargs)
    if "Running" in current_power_state:
      cmd_reboot = "powershell.exe \"Restart-VM -Force -Name %s\""%l2_vm_name
      task_id = self._os.run_shell_command_handsoff(cmd_str=cmd_reboot)
    else:
      WARN("VM not in right state to perform the operation")

  def vm_l2_delete(self, **kwargs):
    """
    Delete a VM on an nested Hyper-V guest
    Args:
      kwargs
    Returns:
    """
    l2_vm_name = kwargs.get("l2_vm_name")
    vm_list_before = self.vm_l2_vmlist()
    if l2_vm_name in vm_list_before:
      cmd_delete_vm = "powershell.exe \"Remove-VM -Force -Name %s\""%l2_vm_name
      task = self._os.run_shell_command_handsoff(cmd_str=cmd_delete_vm)
      time.sleep(5)
    else:
      assert "VM not available on Host to be deleted"
    vm_list_after = self.vm_l2_vmlist()
    if l2_vm_name not in vm_list_after:
      INFO("VM was successfully deleted!!")
      operation_status = True
    else:
      WARN("VM delete operation was attempted but could not "
           "remove it successfully")
      operation_status = False
    return operation_status

  def vm_l2_vmlist(self):
    """
    returns list of VM from an Hyper-V nested guest
    Args:
    Returns:
    """
    cmd = "powershell.exe \"Get-VM\""
    res, stdout, _ = self._os.run_shell_command_sync(cmd)
    return stdout

  def vm_l2_ext_partition(self, **kwargs):
    """
    All instances of guests are provisioned from endor images,
    and may not have enough space, this function helps us to extend
    the C drive space to the max available space.
    Args:
      kwargs
    Returns:
    """
    vm_name = kwargs.get("vm_name")
    size = kwargs.get("size")
    vm = self.vm_entity(cluster=self.cluster)
    vm._bind(**{"name": vm_name})
    vm.update_disk(new_size=size, disk_type='scsi', device_index=0)
    cmd_max_c_size = "powershell.exe \"Get-PartitionSupportedSize " \
                      "-DriveLetter C | select SizeMax\""
    res, stdout, _ = self._os.run_shell_command_sync(cmd_max_c_size)
    size = re.findall('[0-9]+', stdout)
    cmd_extend_c_size = """powershell.exe Resize-Partition \
    -DriveLetter C -Size %s"""%size[0]
    res, stdout, _ = self._os.run_shell_command_sync(cmd_extend_c_size)

  def run_l2_vm_io_workload(self, **kwargs):
    """
    runs basic IO workload on a guest running on an
    Hyper-V nested guest
    Args:
      kwargs(str):
    Returns:
    """
    l2_vm_name = kwargs.get("l2_vm_name")
    #fetching ip address
    ip_address = self.get_vm_l2_ip(**kwargs)
    self._l2_os = self.acrogosutil_entity(ip_address[0])
    self._l2_os.run_io_integrity_test_sync()

  def get_vm_l2_ip(self, **kwargs):
    """
    retrieves IP address of a guest running on an
    Hyper-V nested guest
    Args:
      kwargs(str):
    Returns:
    """
    l2_vm_name = kwargs.get("l2_vm_name")
    cmd_retrieve_ip = "powershell.exe \"Get-VM -name %s | select " \
                      "-ExpandProperty networkadapters | select -Property " \
                      "vmname , ipaddresses\""%l2_vm_name
    interval = 30
    retry = 20
    while retry > 0:
      try:
        res, stdout, _ = self._os.run_shell_command_sync(cmd_retrieve_ip)
        ip_add = re.findall(r'[0-9]+(?:\.[0-9]+){3}', stdout)
        retry = retry-1
        if ip_add == []: #pylint: disable=no-else-continue
          time.sleep(interval)
          INFO("Looks like VM %s is not assigned IP address yet, Retrying!"\
          %l2_vm_name)
          continue
        else:
          INFO("Here's the ip address of the deployed VM: %s" % ip_add)
          break
      except Exception: # pylint: disable=broad-except
        assert "Timed out : Could not fetch IP address in stipulated time"
    return ip_add

  def enable_vm_hardware_virtualization(self, **kwargs):
    """
    Enable Hardware_virt param
    Args:
      kwargs
    """
    kwargs.update({"hw_toggle_flag":'true'})
    self._toggle_vm_hardware_virtualization(**kwargs)

  def disable_vm_hardware_virtualization(self, **kwargs):
    """
    Disable Hardware_virt param
    Args:
      kwargs
    """
    kwargs.update({"hw_toggle_flag":'false'})
    self._toggle_vm_hardware_virtualization(**kwargs)

  def get_vm_hardware_virtualization(self, **kwargs):
    """
    Enable Hardware_virt param
    Args:
      kwargs
    Returns:
      hw_virt_status
    """
    vm_name = kwargs.get("vm_name")
    self.vm = self.rest_vm_cls(interface_type="REST", name=vm_name)
    self.vm._bind(**{'name': vm_name})
    try:
      hw_virt_status = self.vm.get()['boot']['hardware_virtualization']
    except KeyError:
      hw_virt_status = None
      INFO("The hardware virtualization param None for the Guest!!")
    return hw_virt_status

  def _enable_hyperv(self):
    """
    Internal method specific to Hyper-v
    Args:
    Returns:
    """
    INFO("Enabling Hyper-V")
    current_status = self.get_status()
    if current_status == "Not enabled":
      cmd = "powershell.exe Enable-WindowsOptionalFeature -Online -NoRestart " \
            "-FeatureName Microsoft-Hyper-V -All"
      task_id = self._os.run_shell_command_handsoff(cmd_str=cmd)
      try:
        self._os.wait_handsoff_task_complete(task_id, 300)
        INFO("Rebooting after enabling Hyper-V")
        cmd = "shutdown /r /t 5"
        res, _, _ = self._os.run_shell_command_sync(cmd_str=cmd)
        assert res == 0, "Reboot cmd failed"
        time.sleep(60)
        res, _, _ = self._os.run_shell_command_sync(cmd_str=cmd)
        time.sleep(60)
      except:  # pylint: disable=bare-except
        WARN("Could not enable hyper-v!!")
      status = self.get_status()
      assert "Enabled" in status, "Hyper-V status is not enabled, " \
                                  "Terminating execution"
    elif current_status == "Enabled":
      INFO("Hyper-v is already enabled on the guest!!")
    return status


  def _toggle_vm_hardware_virtualization(self, **kwargs):
    """
    Private function to enable or disable
    Hw virtualization param
    Args:
      kwargs : with updated flag true/false
    """
    vm_name = kwargs.get("vm_name")
    hw_flag = kwargs.get("hw_toggle_flag")
    INFO("current HW virt status is: %s" \
    % self.get_vm_hardware_virtualization(**kwargs))
    if hw_flag == 'true':
      INFO("Attempting to enable HW virt param")
    self.vm = self.rest_vm_cls(interface_type="REST", name=vm_name)
    self.vm._bind(**{'name': vm_name})
    self.vm.power_off()
    self.edit_args = {"use_data_json_as_is" : {"boot":self.vm.get()['boot']}}
    self.edit_args['use_data_json_as_is']['boot']\
    ['hardware_virtualization'] = hw_flag
    self.vm.edit(**self.edit_args)
    INFO("Updated HW virt status is: %s" \
    % self.get_vm_hardware_virtualization(**kwargs))
    self.vm.power_on(wait_for_ip=False, timeout=900)
    time.sleep(60)
