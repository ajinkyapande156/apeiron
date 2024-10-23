"""
Copyright (c) 2022 Nutanix Inc. All rights reserved.

Author: umashankar.vd@nutanix.com

Dodin phase specific library
"""
# pylint: disable=no-self-use, invalid-name, using-constant-test, no-else-return
# pylint: disable=unused-variable, unused-import, no-member
# pylint: disable=too-many-branches, too-many-statements, unused-argument
# pylint: disable=ungrouped-imports, line-too-long, too-many-locals
# pylint: disable=broad-except, singleton-comparison, bad-continuation
# pylint: disable=wrong-import-order
import json
from libs.ahv.workflows.one_click.jarvis_client \
  import JarvisClient
import workflows.acropolis.mjolnir.feature.installer.constants as const

from framework.lib.nulog import WARN


class Json_Generator():
  """
  This class is to generate various json's required for
  installer cases, both positive and negative
  """

  def __init__(self, **kwargs):
    """
    function to initialize library
    """
    self.remote_server = kwargs.get("remote_server", const.CALLBACK_SERVER)
    self.external_HDD = kwargs.get("HDD", False)
    self.hostname = kwargs.get("hostname", "Installer-Test")
    self.install_device = kwargs.get("install_device", "sda")
    self.node_type = kwargs.get("node_type", "compute_only")
    self.post_action = kwargs.get("post_action", "reboot")
    self.bond_mode = kwargs.get("bond_mode", "active-backup")
    self.vlan = kwargs.get("vlan", "0")
    self.uplinks = kwargs.get("uplinks", [])
    self.gateway = kwargs.get("gateway", "1.1.1.1")
    self.ip = kwargs.get("host_ip", "1.1.1.1")
    self.netmask = kwargs.get("netmask", "255.255.255.0")
    self.monitoring_ip = kwargs.get("monitoring_ip", const.CALLBACK_SERVER)
    self.ip_type = kwargs.get("IP_type", "dhcp")
    self.monitoring_uuid = kwargs.get("monitoring_uuid")
    assert self.monitoring_uuid, "Monitoring UUID is must for \
        validating error messages"

  def generate_dhcp_json(self):
    """
    Create target object
    Args:
    Returns:data(str)
    Raises:
    """
    if not self.monitoring_ip:
      WARN("Monitoring IP is not set and test will not be able to track progress")
    data = {
      "hostname": self.hostname,
      "install_device": self.install_device,
      "network_config": {
      "host_interfaces": [
              {
              "name": "br0",
              "vswitch": "br0"
              }
            ],
          "vswitches": [
                {
                "bond-mode": "active-backup",
                "name": "br0",
                "uplinks": []
                }
            ]
        },
      "use_dhcp": True,
      "node_type": self.node_type,
      "post_action": self.post_action,
      "monitoring_url_root": f"http://{self.monitoring_ip}?id={self.monitoring_uuid}&?stage=in_progress",
      "installing_callback_url": f"http://{self.monitoring_ip}?id={self.monitoring_uuid}&stage=started",
      "rebooting_callback_url": f"http://{self.monitoring_ip}?id={self.monitoring_uuid}&stage=finished",
      "vendor_callback_url": f"http://{self.monitoring_ip}?id={self.monitoring_uuid}&stage=successful",
      "version": "1.0"
    }

    return data

  def generate_static_json(self):
    """
    Create target object
    Args:
    Returns:data(str)
    Raises:
    """
    data = {
          "hostname": self.hostname,
          "install_device": self.install_device,
          "network_config": {
          "host_interfaces": [
            {
                "gateway": self.gateway,
                "ip": self.ip,
                "name": "br0",
                "netmask": self.netmask,
                "vlan": self.vlan,
                "vswitch": "br0"
            }
            ],
            "vswitches": [
                {
                    "bond-mode": self.bond_mode,
                    "name": "br0",
                    "uplinks": self.uplinks
                }
              ]
          },
      "node_type": self.node_type,
      "post_action": self.post_action,
      "monitoring_url_root": f"http://{self.monitoring_ip}?id={self.monitoring_uuid}&stage=in_progress",
      "installing_callback_url": f"http://{self.monitoring_ip}?id={self.monitoring_uuid}&stage=started",
      "rebooting_callback_url": f"http://{self.monitoring_ip}?id={self.monitoring_uuid}&stage=finished",
      "vendor_callback_url": f"http://{self.monitoring_ip}?id={self.monitoring_uuid}&stage=successful",
      "version": "1.0"
    }
    return data
