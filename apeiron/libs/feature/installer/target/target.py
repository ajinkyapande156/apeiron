"""
Copyright (c) 2024 Nutanix Inc. All rights reserved.

Author: pritam.chatterjee@nutanix.com
"""
#pylint: disable=no-self-use, invalid-name, using-constant-test, no-else-return
# pylint: disable=unused-variable, unused-import, no-member
# pylint: disable=too-many-branches, too-many-statements, unused-argument
# pylint: disable=ungrouped-imports, line-too-long, too-many-locals
# pylint: disable=broad-except, singleton-comparison, method-hidden, no-else-break
# pylint: disable=bad-continuation, simplifiable-if-statement, subprocess-run-check
import json
import time
import uuid
import re
import subprocess
from framework.lib.nulog import INFO, WARN, ERROR, STEP
from framework.entities.container.container import Container
from framework.exceptions.entity_error import NuTestEntityMissingError
import framework.operating_systems.operating_system.linux_operating_system \
  as LinuxOperatingSystem
from framework.exceptions.nutest_error import NuTestError
from workflows.acropolis.ahv.acro_image_utility import AcroImageUtil
from libs.workflows.generic.vm.vm_factory import (
  VmFactory)
from libs.feature.installer.custom_iso import custom_iso
from libs.feature.installer.ucsm_interface \
  import UcsLoginHandler
from libs.feature.installer.json_builder\
  import Json_Generator
from libs.workflows.screenshot.vm_screenshot \
  import Screenshot
import workflows.acropolis.mjolnir.feature.installer.constants as const


class AbstractTarget:
  """AbstractTarget class"""
  def create_target(self, **kwargs):
    """
    Create target object
    Args:
    Returns:
    Raises:
    """
    raise NotImplementedError

  def power_cycle(self, **kwargs):
    """
    Power target object
    Args:
    Returns:
    Raises:
    """
    raise NotImplementedError

  def mount_media(self, **kwargs):
    """
    Mount installation media/iso
    Args:
    Returns:
    Raises:
    """
    raise NotImplementedError

  def get_target_identifier(self, **kwargs):
    """
    Get target identifier
    Args:
    Returns:
    Raises:
    """
    raise NotImplementedError

  def capture_screenshot(self, **kwargs):
    """
    Get target screenshot
    Args:
    Returns:
    Raises:
    """
    raise NotImplementedError

  def delete_target(self, **kwargs):
    """
    Delete the target
    Args:
    Returns:
    Raises:
    """
    raise NotImplementedError

  def delete_install_media(self, **kwargs):
    """
    Delete the target
    Args:
    Returns:
    Raises:
    """
    raise NotImplementedError


class VmTarget(AbstractTarget):
  """
  VM target class
  """
  def __init__(self, **kwargs):
    """
    Create Virtual Machine target object
    Args:
      kwargs
    Returns:
    Raises:
    """
    # super(VmTarget, self).__init__(**kwargs)
    self.json_handle = None
    self.custom_iso_handle = None
    self.handle = None
    self.cluster = None
    self.vm = None

  def create_target(self, **kwargs):
    """
    Create VM target and initialize it.
    Args:
    Returns:
      handle(object)
    Raises:
    """
    self.cluster = kwargs.get('cluster')
    assert self.cluster, "Nutest cluster object is need for VM target creation"
    # only uefi is support, for -ve provide the type explicitly
    name = kwargs.pop('target_name', "ahv_server")
    boot_type = kwargs.pop('boot_type', "uefi")
    vcpus = kwargs.pop('vcpus', 2)
    memory = kwargs.pop('memory', 4096)
    cores = kwargs.pop('cores', 2)
    disk_size = kwargs.pop('disk_size', 32768)
    # 2 nics are needed, change it for extra validations
    num_of_vnics = kwargs.pop('num_of_vnics', 2)
    self.handle = VmFactory(cluster=self.cluster,
                            interface_type="REST")
    INFO(f"Creating Target VM: {name}")
    INFO(f'kwargs: {kwargs}')
    self.vm = self.handle.create(**{'boot_type': boot_type,
                                    'name': name,
                                    'num_of_vnics': num_of_vnics,
                                    'cores_per_vcpu': cores,
                                    'vcpus': vcpus,
                                    'memory': memory,
                                    **kwargs})
    self.handle.add_disk(
      disk_size_mb=disk_size
    )

    res = self.cluster.execute(
      "acli vm.update_boot_device %s boot_device_order=kDisk,kCdrom"
      % self.vm.uuid)
    assert 'complete' in res['stdout'], (f"Failed to update the boot order "
                                         "for VM {self.vm.uuid}")

    assert self.handle, "Target Virtual Machine target creation failed"
    kwargs["monitoring_uuid"] = self.vm.uuid
    self.custom_iso_handle = custom_iso(**kwargs)
    self.json_handle = Json_Generator(**kwargs)
    return self.handle

  def get_target_identifier(self, **kwargs):
    """
    Create VM target and initialize it.
    Args:
    Returns:
      uuid(str):
    Raises:
    """
    target_name = kwargs.pop('target_name', "ahv_server")
    self.cluster = kwargs.pop('cluster')
    self.handle = VmFactory(cluster=self.cluster,
                            interface_type="REST")
    self.vm = self.handle.create(**{'name': target_name, 'bind': True,
                                    'wait_for_ip': False})
    assert self.vm.uuid, "Unable to discover Target"
    self.vm = self.handle.create(**{
                          'name': target_name,
                          'bind': True}
                          )
    assert self.vm.uuid, "Unable to discover Target"
    return self.vm.uuid

  def capture_screenshot(self, **kwargs):
    """
    Get target screenshot
    Args:
    Returns:
    Raises:
    """
    Screenshot().take_screenshot(self.vm)

  def power_cycle(self, **kwargs):
    """
    Power VM target object
    Args:
    Returns:
    Raises:
    """
    # as this vm will have ahv w/o no test agent
    verify_vm_boot = kwargs.get('verify_vm_boot', False)
    self.handle.power_on(verify_vm_boot=verify_vm_boot,
                         wait_for_ip=False)

  def mount_media(self, **kwargs):
    """
    Mount installation media/iso
    Args:
    Returns:
    Raises:
    """
    STEP("Creating Custom Metadata File")
    ip_type = kwargs.pop("IP_type", "dhcp")
    if ip_type == "static":
      data = self.json_handle.generate_static_json()
    else:
      data = self.json_handle.generate_dhcp_json()
    if kwargs.get("remove_from_meta", None):
      key = kwargs.pop("remove_from_meta")
      data.pop(key)
    json_data = json.dumps(data)
    INFO("Using below installer.json")
    INFO(json_data)
    STEP("Creating Custom ISO with the Metadata File")
    installer_media = self.custom_iso_handle.custom_iso_generate(json_data)[0]
    assert self.handle, "Virtual Machine target needs to be created"
    assert installer_media, "URL to get the installer media is required"
    bus_type = kwargs.get('bus_type', "SATA")
    device_index = kwargs.get('device_index', 0)
    img_name = kwargs.get('img_name', "AHV_SERVER")

    INFO(f"Mounting AHV installer media: {installer_media}")
    img_util = AcroImageUtil(self.cluster)

    img_ids = img_util.upload_image(img_name, installer_media, 'ISO_IMAGE')
    ctr = Container.list(self.cluster)[0]
    INFO("Choose container name=%s, uuid=%s" % (ctr.name, ctr.entity_uuid))
    INFO(f"Adding cdrom for mounting AHV Installer")
    self.vm.add_disk(is_cdrom=True, is_empty=False,
                     disk_type=bus_type, device_index=device_index,
                     clone_container_uuid=ctr.entity_uuid,
                     clone_from_vmdisk=img_ids[1])
    INFO("Mount CDROM with image name=%s, url=%s" % (img_name,
                                                     installer_media))

  def delete_target(self, **kwargs):
    """
    Idempotent
    Create VM target and initialize it.
    Args:
    Returns:
      uuid(str):
    Raises:
    """
    target_name = kwargs.pop('target_name', "ahv_server")
    self.cluster = kwargs.pop('cluster')
    self.handle = VmFactory(cluster=self.cluster,
                            interface_type="REST")
    self.vm = self.handle.create(**{'name': target_name, 'bind': True})
    self.handle.remove()

  def delete_install_media(self, **kwargs):
    """
    Idempotent
    Delete the install media from cluster.
    Args:
    Returns:
      uuid(str):
    Raises:
    """
    img_name = kwargs.get('img_name', "AHV_SERVER")
    INFO(f"Finding the installer media: {img_name}")
    self.cluster = kwargs.pop('cluster')
    self.cluster.execute(
      '/usr/local/nutanix/bin/acli -o json -y image.delete '
      f'{img_name}')


class CiscoHostTarget(AbstractTarget):
  """
  This class would be used if target is cisco server
  """
  def __init__(self, **kwargs):
    """
    Create Cisco UCS target object
    Args:
      kwargs
    Returns:
    Raises:
    """
    # super(CiscoHost, self).__init__(*args, **kwargs)
    self.username = None
    self.password = None
    self.hostname = None
    self.ipmi = None
    self.vmedia_policy = None
    self.parent_dn = None
    # NOTE: These can come from constants file as well

  def create_target(self, **kwargs):
    """
    Create Cisco UCS target and initialize it.
    Args:
    Returns:
    Raises:
    """
    self.username = kwargs.get('username', "ADMIN")
    self.password = kwargs.get('password', "ADMIN")
    self.ipmi = kwargs.get('ipmi', "ipmi")
    self.vmedia_policy = kwargs.get('vmedia_policy', "vmedia_policy")
    self.ip_type = kwargs.get("IP_type", "dhcp")
    self.parent_dn = kwargs.get('parent_dn', "org-root")
    self.install_device = kwargs.get("install_device")
    self.bond_mode = kwargs.get("bond_mode", "active-backup")
    self.ucsm_ip = kwargs.get("UCSM_ip")
    self.ucsm_user = kwargs.get("ucsm_user", "admin")
    self.ucsm_password = kwargs.get("ucsm_password", "admin")
    self.ipmi = kwargs.get("ipmi_ip")
    self.iso_name = kwargs.get("iso_name")
    self.host_ip = kwargs.get("host_ip")
    self.build_url = kwargs.get("build_url")
    self.nfs_path = kwargs.get("nfs_path")
    self.nfs_server = kwargs.get("NFS_server")
    self.remote_server = kwargs.get("remote_server")
    self.vmedia_policy = kwargs.get("vmedia_name")
    self.multinode = kwargs.get("multinode_case")
    self.hdd = kwargs.get("metadata_via_hdd")
    self.serial_num = kwargs.get("serial_number")
    self.random_reboot = kwargs.get("random_reboot", False)
    self.cluster = kwargs.get('cluster')
    self.boot_mode = kwargs.get("boot_mode")
    self.secure_boot = kwargs.get("secure_boot")
    self.uuid = uuid.uuid4()
    self.target_name = kwargs.get("target_name")

    #caching args for subsequent validation
    const.CACHE[self.target_name] = self.uuid
    kwargs.update(monitoring_uuid=const.CACHE[self.target_name])

    #initializing libraries
    self.custom_iso_handle = custom_iso(**kwargs)
    self.ucsm_handle = UcsLoginHandler(**kwargs)
    self.json_handle = Json_Generator(**kwargs)

    self.number_of_nics = kwargs.get("number_of_nics", None)
    if self.number_of_nics:
      self.ucsm_handle.add_vnics(self.number_of_nics)
    #add remove vnics in cleanup part

    # if self.boot_mode:
    #   STEP("Setting boot mode as per re")
    #   self.ucsm_handle.boot_policy_modify(self.boot_mode)

    if self.secure_boot == 'yes':
      STEP("Setting boot mode to Secure")
      self.ucsm_handle.secure_boot_modify(self.secure_boot)
      STEP("Ensuring no media is mounted before powercycle")
      self.ucsm_handle.vmedia_sp_detach()
      STEP("power cycling the node to ensure profile is applied")
      self.ucsm_handle.power_cycle()
      STEP("Waiting for 10 minutes")
      time.sleep(600)

  def get_target_identifier(self, **kwargs):
    """
    Get target identifier
    Args:
    Returns:
    Raises:
    """
    INFO(f"Identifier: {const.CACHE[kwargs.get('target_name')]}")
    return const.CACHE[kwargs.get('target_name')]

  def mount_media(self, **kwargs):
    """
    Mount installation media/iso
    Args:
    Returns:
    Raises:
    """
    # FIMXE: Uma to port the code from feature/installer/ucsm_interface.py
    STEP("Generating meta data")
    if self.ip_type == "static":
      data = self.json_handle.generate_static_json()
    else:
      data = self.json_handle.generate_dhcp_json()

    if kwargs.get("remove_from_meta", None):
      key = kwargs.pop("remove_from_meta")
      data.pop(key)

    self.json_data = json.dumps(data)
    INFO("Using below installer.json")
    INFO(self.json_data)

    STEP("Creating custom ISO")
    self.ISO_availability = self.custom_iso_handle.custom_iso_generate(self.json_data)
    INFO("Customized ISO is available at below location : ")
    INFO(self.ISO_availability)

    STEP("Preparing media policy")
    self.ucsm_handle.vmedia_update()

    STEP("Mounting Vmedia policy")
    self.ucsm_handle.vmedia_sp_detach()
    self.ucsm_handle.vmedia_sp_attach()

  def disconnect_connect_media(self, **kwargs):
    """
    Args:
    Returns:
    Raises:
    """
    STEP("disconnecting Vmedia policy")
    self.ucsm_handle.vmedia_sp_detach()
    STEP("Soak time to ensure disconnection failed the installation")
    time.sleep(300)
    STEP("connecting Vmedia policy")
    self.ucsm_handle.vmedia_sp_attach()
    STEP("Rebooting to re run automated installer")
    self.ucsm_handle.power_cycle()

  def power_cycle(self, **kwargs):
    """
    Power Cycle Cisco UCS target object
    Args:
    Returns:
    Raises:
    """
    STEP("Power cycling server, IPMI IP is : %s" %self.ipmi)
    self.ucsm_handle.power_cycle()

  def power_ops(self, desired_state, **kwargs):
    """
    Power Cycle Cisco UCS target object
    Args:
      desired_state (str) : Can be up, down
    Returns:
    Raises:
    """
    STEP("Power operation carried on server, IPMI IP is : %s" %self.ipmi)
    self.ucsm_handle.power_ops(desired_state)

  def add_nics(self, **kwargs):
    """
    Args:
      kwargs
    Returns:
    Raises:
    """
    STEP("Default number of vnics are 2")
    INFO("adding 4 more Vnics")
    self.ucsm_handle.add_vnics(4)

  def remove_nics(self, **kwargs):
    """
    Args:
      kwargs
    Returns:
    Raises:
    """
    STEP("Cleaning up vnics added during test")
    self.ucsm_handle.remove_vnics(4)

  def delete_target(self, **kwargs):
    """
    Delete the target
    Args:
    Returns:
    Raises:
    """
    WARN("Not needed for this Target")

  def delete_install_media(self, **kwargs):
    """
    Delete the target
    Args:
    Returns:
    Raises:
    """
    WARN("Not needed for this Target")

  def capture_screenshot(self, **kwargs):
    """
    Get target screenshot
    Args:
    Returns:
    Raises:
    """
    WARN("Not supported for this Target")

  def confirm_file_existence(self, host_ip, file_name):
    """
    function to confirm presence of file at specified location
    returns:
      true or false
    Args:
      host_ip (str): Ip addr
      file_name(str): args from config
    Returns:
      exists_flag : True if file is present
    """
    #cmd = "[! -f "+ "'" + file_name + "' ]" + "&& echo 'File is present'"
    cmd = "test -f " + file_name
    ahv_ssh_int = self._execute_on_host(host_ip, cmd)
    INFO(ahv_ssh_int)
    if ahv_ssh_int['status'] == 1: #returns status 1 if file does not exist
      exists_flag = False
    else:
      exists_flag = True
      INFO("Contents of the config file: %s" %self._execute_on_host(host_ip, "cat {}".format(file_name)))
    return exists_flag

  def get_boot_disk(self, host_ip, boot_device=None):
    """
    Args:
      host_ip (str): Ip addr
      boot_device (str) : string
    Returns:
      bool
    """
    if not boot_device:
      INFO("Boot device not provided, identifying largest device")
      boot_device = self.get_largest_disk_info(host_ip)
      INFO("Largest device is : %s" %boot_device)
    INFO("Attempting to obtain boot disk info")
    result = self._execute_on_host(host_ip, "lsblk | grep boot")
    INFO("Here's the disk info: %s" % result)
    if boot_device in result['stdout']:
      return True
    else:
      return False

  def get_largest_disk_info(self, host_ip):
    """
    Args:
      host_ip (str): Ip addr
    Returns:
      bool
    Raises:
    """
    INFO("attempting to get boot disk size")
    cmd = """MAX_SIZE=$(lsblk -b -o SIZE | tail -n +2 | sort -n | tail -n 1);lsblk -b -o NAME,SIZE | awk -v max="$MAX_SIZE" '$2 == max {print}'"""
    response = self._execute_on_host(host_ip, cmd)
    INFO("Largest disk is : %s" %response['stdout'])
    temp = response['stdout'].split("  ")
    largest_disk_name = temp[0]
    return largest_disk_name

  def get_secure_boot(self, host_ip):
    """
    Args:
      host_ip (str): Ip addr
    Returns:
      bool
    """
    INFO("Attempting to obtain host secure boot")
    result = self._execute_on_host(host_ip, "mokutil --sb")
    INFO("Here's the secure boot info: %s" % result)
    if "enabled" in result['stdout']:
      return True
    else:
      return False

  def get_nic_bonding(self, host_ip, bond_mode):
    """
    Args:
      host_ip (str): Ip addr
      bond_mode (str) : active-passive or other supported modes
    Returns:
      bool
    """
    INFO("Attempting to obtain NIC info")
    result = self._execute_on_host(host_ip, "ovs-appctl bond/list")
    INFO("Here's the OVS command output: %s" % result)
    #Identifying number of eth's
    pattern = re.compile(r'eth')
    matches = pattern.findall(result['stdout'])
    count_eth = len(matches)

    if bond_mode in result['stdout']:
      mode_flag = True
    else:
      mode_flag = False
    return(count_eth, mode_flag)

  def is_pingable(self, ip):
    """
    Args:
      ip (str): Ip addr
    Returns:
      bool
    Raises:
      Exception(e)
    """
    try:
      # Ping the IP address
      output = subprocess.run(
          ["ping", "-c", "1", ip],
          stdout=subprocess.PIPE,
          stderr=subprocess.PIPE
      )
      # Return True if ping was successful (exit code 0)
      return output.returncode == 0
    except Exception as e:
      print(f"Error occurred while pinging: {e}")
      return False

  def poll_ip(self, ip, interval=120, timeout=2400):
    """
    Args:
      ip (str): Ip addr
      interval (int) : delay for polling
      timeout(int): Overall timeout for waiting server bootup
    Returns:
      bool
    Raises:
      NuTestError
    """
    start_time = time.time()
    while True:
      if self.is_pingable(ip):
        INFO("IP is reachable, proceeding to validate!!")
        flag = True
        break
      else:
        INFO("IP is not reachable yet, waiting!!")
        flag = False

      # Check if the timeout has been reached
      if time.time() - start_time > timeout:
        WARN("Timeout reached, stopping polling.")
        raise NuTestError("Timedout waiting for cluster upgrade to complete")
      # Wait for the next poll
      time.sleep(interval)
    return flag

  def _execute_on_host(self, ip, cmd, username='root', password='nutanix/4u'):
    """
    Establish connection using ssh and specified user
    returns:
      connection objection
    Args:
      ip (str): ip addr
      cmd (str): Command to be run
      username (str) : username to login
      password (str) : password to login
    Returns:
      execution result of cmd provided
    """
    ahv_conn = LinuxOperatingSystem.LinuxOperatingSystem\
      (ip, username, password)
    INFO("Established connection as: %s " %username)
    return ahv_conn.execute(cmd)

class TargetFactory:
  """Factory class for creating target objects"""
  TARGETS = {
    "vm": VmTarget,
    "cisco_host": CiscoHostTarget
  }
  def __new__(cls, **kwargs):
    """
    Factory method for creating target objects
    Args:
    Returns:
    Raises:
    """
    target_type = kwargs.get('target_type', "vm")
    assert target_type in cls.TARGETS, "Unknown target type: %s" % target_type
    return cls.TARGETS[target_type](**kwargs)
