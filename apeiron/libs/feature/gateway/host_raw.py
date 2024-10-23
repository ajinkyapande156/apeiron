"""
Copyright (c) 2024 Nutanix Inc. All rights reserved.

Author: pritam.chatterjee@nutanix.com
"""
# pylint: disable=import-error, unused-import, unused-argument, no-member
import os
import json
from libs.framework import mjolnir_entities as entities
from libs.feature.gateway.base_raw import BaseRaw


class HostRaw(BaseRaw):
  """HostRaw class"""

  # NOTE: Not useful
  # @BaseRaw.process_response
  # def get_pci_slots(self):
  #   endpoint = os.path.join(self.host +
  #                           "host/v1/redfish/v1/Chassis/ahv/PCIeSlots")
  #   response = self.cluster.execute(endpoint)
  #   assert response['stdout'], "Failed to get PCI slots on host %s" % response
  #   return response

  @BaseRaw.process_response
  def get_host_version(self):
    """
    Get the host version information
    Returns:
      response (dict): host version information
    """
    endpoint = os.path.join(self.host + "host/v1/version")
    response = self.cluster.execute(endpoint)
    return response

  @BaseRaw.process_response
  def get_host_info(self):
    """
    Get the host version information
    Returns:
      response (dict): host version information
    """
    endpoint = os.path.join(self.host + "host/v1/info")
    response = self.cluster.execute(endpoint)
    return response

  @BaseRaw.process_response
  def get_host_name(self):
    """
    Get the hostname for given host
    Returns:
      response (dict): host version information
    """
    endpoint = os.path.join(self.host + "host/v1/hostname")
    response = self.cluster.execute(endpoint)
    return response

  @BaseRaw.process_response
  def get_host_userpasswd_info(self, user):
    """
    Get the user password info on host
    Args:
      user(str):
    Returns:
      response (dict): host version information
    """
    endpoint = os.path.join(self.host + f"host/v0/users/{user}/password/info")
    response = self.cluster.execute(endpoint)
    return response

  @BaseRaw.process_response
  def update_host_userpasswd(self, user, payload):
    """
    Update the user password on host
    Args:
      user(str):
      payload(dict):
    Returns:
      response (dict): host version information
    """
    endpoint = os.path.join(self.host + f"host/v0/users/{user}/password/update"
                                        f" -X POST -H \"Content-Type: "
                                        f"application/json\" "
                                        f"-d \'{json.dumps(payload)}\'")
    response = self.cluster.execute(endpoint)
    return response

  @BaseRaw.process_response
  def get_host_custom_kernel(self):
    """
    Get the custom kernel info on host
    Returns:
      response (dict): host version information
    """
    endpoint = os.path.join(self.host + f"host/v0/custom-kernel")
    response = self.cluster.execute(endpoint)
    return response

  @BaseRaw.process_response
  def get_pci_devices(self):
    """
    List pci devices on Host
    Returns:
      response (dict):
    """
    endpoint = os.path.join(self.host +
                            "host/v1/redfish/v1/Chassis/ahv/PCIeDevices")
    response = self.cluster.execute(endpoint)
    assert response['stdout'], ("Failed to list PCI devices "
                                "on host %s") % response
    return response

  @BaseRaw.process_response
  def get_pci_device_by_uuid(self, uuid):
    """
    Get pci device with uuid on Host
    Args:
      uuid (str): uuid of pci device
    Returns:
      response (dict): pci device details
    """
    endpoint = os.path.join(self.host +
                            "host/v1/redfish/v1/Chassis/ahv/PCIeDevices/%s"
                            % uuid)
    response = self.cluster.execute(endpoint)
    assert response['stdout'], ("Failed to get PCI device info "
                                "on host %s") % response
    return response

  @BaseRaw.process_response
  def get_pci_device_functions(self, uuid):
    """
    list pci device function with pci device uuid on Host
    Args:
      uuid (str): uuid of pci device
    Returns:
      response (dict): pci device functions details
    """
    endpoint = os.path.join(self.host +
                            "host/v1/redfish/v1/Chassis/ahv/PCIeDevices/"
                            "%s/PCIeFunctions"
                            % uuid)
    response = self.cluster.execute(endpoint)
    assert response['stdout'], ("Failed to get PCI device function"
                                " on host %s") % response
    return response

  @BaseRaw.process_response
  def get_pci_device_function_by_uuid(self, pci_uuid, func_uuid):
    """
    Get pci device function details by function uuid on Host
    Args:
      pci_uuid (str): uuid of pci device
      func_uuid (str): uuid if specific function
    Returns:
      response (dict): pci device details
    """
    endpoint = os.path.join(self.host +
                            "host/v1/redfish/v1/Chassis/ahv/PCIeDevices/"
                            "%s/PCIeFunctions/%s"
                            % (pci_uuid, func_uuid))
    response = self.cluster.execute(endpoint)
    assert response['stdout'], ("Failed to get PCI device get function"
                                " on host %s") % response
    return response
