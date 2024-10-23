"""
NodeAddRemove using ncli

Copyright (c) 2023 Nutanix Inc. All rights reserved.

Author: rishabh.kumar@nutanix.com
"""
# pylint: disable=unused-argument, fixme, protected-access
from framework.lib.nulog import INFO

# TODO: Remove this dependency in the future
from workflows.acropolis.ahv_management.scheduler_test_lib import \
  SchedulerTestLib
from workflows.acropolis.upgrade.host_add_remove import HostAddRemove


class NodeAddRemoveNcli(HostAddRemove):
  """NodeAddRemoveNcli Class"""
  def __init__(self, **kwargs):
    """
    Initialize the object
    Args:
      **kwargs
        cluster(object): Nutest cluster object
    """
    self.cluster = kwargs.get("cluster", None)
    super(NodeAddRemoveNcli, self).__init__(cluster=self.cluster)

  def remove_node(self, host, **kwargs):
    """
    Remove node
    Args:
      host(object): Host object
    """
    INFO("Remove node with host ip: %s" % host.ip)
    self.remove_host(hypervisor=host, **kwargs)

    INFO("Verify if node with host ip: %s is removed" % host.ip)
    self.ensure_host_removal(host_ip=host.ip, **kwargs)

    # This is not required if we are doing node add via RPC, the node add
    # method does the discovery part as well

    # INFO("Wait for node with host ip: %s to become discoverable" % host.ip)
    # self.discover_node(svm_ip=host.svm.ip, **kwargs)

  def addback_node(self, host, **kwargs):
    """
      Add the node back to the cluster
      Args:
        host(object): Host object
    """
    is_co_node = kwargs.pop("is_co_node", False)
    INFO("Adding the node with host ip: %s" % host.ip)
    # ncli way to add host is not working, and it is even deprecated.
    # The recommendation is to use expand cluster API.

    # TODO: Create a separate RPC interface and not mix it with ncli
    test_args = {}
    if is_co_node:
      test_args.update({"node_type": "COMPUTE_ONLY"})
    scheduler_test_lib = SchedulerTestLib(cluster=self.cluster,
                                          test_args=test_args)
    scheduler_test_lib.wait_for_removed_node_unconfigured(node=host)
    scheduler_test_lib.add_node(node=host, **kwargs)
    self.cluster.hypervisors.append(host)
    if not is_co_node:
      self.cluster.svm_ips.append(host.svm.ip)
      self.cluster._svms.append(host.svm)
    ##################################################################

    INFO("Verify if node with host ip: %s got added back" % host.ip)
    self.ensure_host_existence(hypervisor_ip=host.ip, **kwargs)
