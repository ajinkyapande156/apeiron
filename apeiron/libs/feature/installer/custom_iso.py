"""
Copyright (c) 2022 Nutanix Inc. All rights reserved.

Author: umashankar.vd@nutanix.com

Dodin phase specific library
"""
#pylint: disable=no-self-use, invalid-name, using-constant-test, no-else-return
# pylint: disable=unused-variable, unused-import, no-member
# pylint: disable=too-many-branches, too-many-statements, unused-argument
# pylint: disable=ungrouped-imports, line-too-long, too-many-locals
# pylint: disable=broad-except, singleton-comparison
#ahv_conn.execute("mkdir neg_scenario;cd neg_scenario;mkdir metadata;echo '%s' > metadata/installer.json;wget http://endor.dyn.nutanix.com/builds/ahv-builds/10/10.0/10.0-663/iso/AHV-DVD-x86_64-10.0-663.iso;%s" %(neg_json["incorrect_ip"],command))
import time
from framework.lib.nulog import INFO
import framework.operating_systems.operating_system.linux_operating_system \
  as LinuxOperatingSystem
import workflows.acropolis.mjolnir.feature.installer.constants as const
from libs.feature.installer.json_builder import Json_Generator



class custom_iso():
  """
  This class is to generate custom ISO
  requires json and iso image
  resulting ISO will be preserved on container locally
  """
  def __init__(self, version="663", **kwargs):
    """
    func to initialize library to generate iso
    Args:
      version(str) : Version of AHV
      kwargs
    Returns: (iso_url(str), nfs_location(str))
    Raises:
    """
    self.custom_server_ip = kwargs.get("remote_server")
    self.xorriso_args = " -boot_image any keep -add ./metadata"
    #receive this from args
    self.base_build_url = kwargs.get("build_url")
    self.nfs_ip = kwargs.get("NFS_server")
    self.version = version
    self.iso_name = kwargs.get("iso_name")
    self.metadata_config_type = kwargs.get("metadata_type", None)
    self.metadata_hdd = kwargs.get("HDD", False)
    self.metadata_multinode = kwargs.get("multinode", False)
    self.timestamp = time.strftime('%Y%m%d_%H%M%S')
    self.custom_folder = f'custom_{self.timestamp}'
    self.json_handle = Json_Generator(**kwargs)
    self.ip_type = kwargs.get("IP_type")
    self.nfs_path = kwargs.get("nfs_path")
    self.multinode = kwargs.get("multinode_case")
    self.hdd = kwargs.get("metadata_via_hdd")
    self.serial_num = kwargs.get("serial_number")

  def custom_iso_generate(self, json_data):
    """
    Args:
      json_data(str) : json data for customization
    Returns: (iso_url(str), nfs_location(str))
    Raises:
    """
    #command = "xorriso -dev " + iso_name + self.xorriso_args
    #prepare the required folder structure
    #if self.metadata_hdd and self.metadata_multinode:
      #cleanup older files from nfs_path and remote server

      #prepare hdd image
    self.json_data = json_data
    ahv_conn = LinuxOperatingSystem.LinuxOperatingSystem\
      (self.custom_server_ip, 'nutanix', 'nutanix/4u')
    INFO("Established connection as: nutanix")
    command = """./customization_script.sh {} {} '{}' {} {} {} {} {}""".format(self.custom_folder, self.base_build_url, self.json_data, self.nfs_ip, self.nfs_path, self.hdd, self.multinode, self.serial_num)
    INFO("this is the command run: %s" % command)
    custom_script_response = ahv_conn.execute(command)
    INFO(custom_script_response)
    iso_url = "http://{}/nutanix/{}/{}".format(const.CALLBACK_SERVER,
                                               self.custom_folder, self.iso_name)
    nfs_location = "{}/{}/{}".format(self.nfs_path, self.custom_folder, self.iso_name)
    return (iso_url, nfs_location)
    # iso_name = self._prepare_custom_iso()
    # self._copy_destination_nfs(self.nfs_ip)

  def iso_download(self):
    """
    Args:
    Returns:
    Raises:
    """
    ahv_conn = LinuxOperatingSystem.LinuxOperatingSystem\
      (self.custom_server_ip, 'nutanix', 'nutanix/4u')
    INFO("Established connection as: nutanix")
    iso_download = "wget " + self.base_build_url
    ahv_conn.execute(iso_download)
    self._copy_destination_nfs(self.nfs_ip)

  def cleanup_iso(self):
    """
    Args:
    Returns:
    Raises:
    """
    ahv_conn = LinuxOperatingSystem.LinuxOperatingSystem\
      (self.custom_server_ip, 'nutanix', 'nutanix/4u')
    command = "rm " + self.iso_name
    ahv_conn.execute(command)

    ahv_conn_nfs = LinuxOperatingSystem.LinuxOperatingSystem\
      (self.nfs_ip, 'nutanix', 'nutanix/4u')
    command = "rm /home/nutanix/foundation/isos/hypervisor/kvm/" + self.iso_name
    ahv_conn_nfs.execute(command)


  def _copy_destination_nfs(self, nfs_ip):
    """
    Args:
      nfs_ip(str) : IP of NFS server
    Returns:
    Raises:
    """
    ahv_conn = LinuxOperatingSystem.LinuxOperatingSystem\
      (self.custom_server_ip, "nutanix", "nutanix/4u")
    INFO("Established connection as: nutanix")
    cmd = "sshpass -p {} scp {} nutanix@{}:/home/nutanix/foundation/isos/hypervisor/kvm".format('nutanix/4u', self.iso_name, nfs_ip)
    return ahv_conn.execute(cmd)
