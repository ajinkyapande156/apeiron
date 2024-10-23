"""
Copyright (c) 2023 Nutanix Inc. All rights reserved.

Author: rishabh.kumar@nutanix.com
"""
# pylint: disable=no-member
import random

from framework.hypervisors.consts import NodeType
from framework.lib.nulog import STEP

import workflows.acropolis.ahv.acro_host_helper as AcroHostHelper
from libs.feature.node_add_remove.factory import \
  NodeAddRemoveFactory
from workflows.acropolis.upgrade.vm_ops_setup import VMOpsSetup
# TODO: Saw some method to get in APC code, we can use that when it is ready
from workflows.acropolis.ahv.platform.ahv.workflows.platform_qualification.\
  lib.host_helper import HostHelper as PlatQualHostHelper

class BaseHelper:
  """
  BaseHelper Class
  """
  def __init__(self, **kwargs):
    """
    Initialise the object
    Args:
      **kwargs
        cluster(object): Nutest cluster object
    """
    self.cluster = kwargs.get("cluster", None)

  @staticmethod
  def _get_list_from_string(string, separator=","):
    """
    Create a list from a given string

    Args:
      string(str): String from which list is to be created
      separator(str): Each list item is separated with this character

    Returns:
      generated_list(list): The list that is generated from the string
    """
    generated_list = []
    for list_item in string.split(separator):
      list_item = list_item.strip()
      if len(list_item) > 0:
        generated_list.append(list_item)
    return generated_list


class HostHelper(BaseHelper):
  """
  HostHelper Class
  """
  def __init__(self, **kwargs):
    """
    Initialise the object
    Args:
    """
    super(HostHelper, self).__init__(**kwargs)
    self.removable_hosts = []

  def remove_nodes(self, **kwargs):
    """
    Remove nodes
    Args:
    Returns:
    """
    self._select_removable_hosts(**kwargs)
    node_add_remove_helper = NodeAddRemoveFactory(cluster=self.cluster,
                                                  **kwargs)
    for host in self.removable_hosts:
      STEP("Remove node with host ip: %s" % host.ip)
      node_add_remove_helper.remove_node(host=host)

    self.create_vms = kwargs.pop("create_vms", False)
    if self.create_vms:
      vm_ops_setup = VMOpsSetup(cluster=self.cluster)
      vm_ops_setup.pre_upgrade()

  def addback_nodes(self, **kwargs):
    """
    Addback the nodes that were removed from the cluster
    """
    node_add_remove_helper = NodeAddRemoveFactory(cluster=self.cluster,
                                                  **kwargs)
    for host in self.removable_hosts:
      STEP("Add back node with host ip: %s" % host.ip)
      is_co_node = False
      if host.node_type == NodeType.COMPUTE_ONLY:
        is_co_node = True
      node_add_remove_helper.addback_node(host=host, is_co_node=is_co_node)

    validate_vms = kwargs.pop("validate_vms", True)
    if self.create_vms and validate_vms:
      vm_ops_setup = VMOpsSetup(cluster=self.cluster)
      vm_ops_setup.post_upgrade()

  def _select_removable_hosts(self, **kwargs):
    """
    Select the removable hosts
    Args:
      **kwargs
        remove_cpu_models(str): Remove nodes with these CPU models. Multiple
                                cpu model names can be given separated by comma
        keep_cpu_models(str): Keep nodes with these CPU models and
                              remove all the other nodes. Multiple cpu model
                              names can be given separated by comma
        host_ips(str): Remove nodes with particular host IP. Multiple host IPs
                      can be provided separated by comma
        node_type(str): Node type, co - Compute only, hc - Hyperconverged
    """
    remove_cpu_models = kwargs.get("remove_cpu_models", "")
    keep_cpu_models = kwargs.get("keep_cpu_models", "")
    host_ips = kwargs.get("host_ips", "")
    node_type = kwargs.get("node_type", "")

    # Priority for selecting nodes - in cases where users provide options
    # If remove_cpu_models is given, those nodes would be removed and rest
    # of the options - keep_cpu_models, host_ips etc won't be looked at.
    # keep_cpu_models would only be checked when remove_cpu_models is empty.
    # And rest of the options - hosts_ips, random_node would be ignored.

    remove_cpu_models = self._get_list_from_string(string=remove_cpu_models)
    keep_cpu_models = self._get_list_from_string(string=keep_cpu_models)
    host_ips = self._get_list_from_string(string=host_ips)

    plat_qual_host_helper = PlatQualHostHelper()

    if len(remove_cpu_models) > 0:
      for host in self.cluster.hypervisors:
        cpu_model = plat_qual_host_helper.get_cpu_name(host.ip)
        if cpu_model in remove_cpu_models:
          self.removable_hosts.append(host)
    elif len(keep_cpu_models) > 0:
      for host in self.cluster.hypervisors:
        cpu_model = plat_qual_host_helper.get_cpu_name(host.ip)
        if cpu_model not in keep_cpu_models:
          self.removable_hosts.append(host)
    elif len(host_ips) > 0:
      for host in self.cluster.hypervisors:
        if host.ip in host_ips:
          self.removable_hosts.append(host)
    elif len(node_type) > 0:
      if node_type == "co":
        co_hosts = AcroHostHelper.get_co_hosts(self.cluster)
        if len(co_hosts) > 0:
          self.removable_hosts.append(random.choice(co_hosts))
      elif node_type == "hc":
        hc_hosts = AcroHostHelper.get_hc_hosts(self.cluster)
        if len(hc_hosts) > 0:
          self.removable_hosts.append(random.choice(hc_hosts))
    else:
      self.removable_hosts.append(random.choice(self.cluster.hypervisors))


class NodeAddRemoveWfHelper(HostHelper):
  """
  NodeAddRemoveWfHelper Class
  """
  def __init__(self, **kwargs):
    """
    Create NodeAddRemoveWfHelper Mixin object
    """
    super(NodeAddRemoveWfHelper, self).__init__(**kwargs)
    self.host_helper = HostHelper(**kwargs)
