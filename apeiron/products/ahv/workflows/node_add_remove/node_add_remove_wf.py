"""
Copyright (c) 2023 Nutanix Inc. All rights reserved.

Author: rishabh.kumar@nutanix.com
"""

from framework.lib.nulog import STEP
from libs.workflows.node_add_remove.wf_helpers import \
  NodeAddRemoveWfHelper


class NodeAddRemoveWorkflow:
  """
    NodeAddRemoveWorkflow class
  """
  def __init__(self, cluster=None, **kwargs):
    """
    Initialize object
    Args:
      cluster(object): Nutest cluster object
    """
    self.cluster = cluster
    self.wf_helper = NodeAddRemoveWfHelper(cluster=self.cluster, **kwargs)

  def node_add_remove_validations(self, **kwargs):
    """
    This method will invoke the node add remove scenario based on the params
    Args:
    Returns:
    Raises:
    """
    validations = kwargs.pop("validations", "")
    for validation in validations.split(","):
      validation = validation.strip()
      if len(validation) > 0:
        STEP("Performing the operation: [%s]" % validation)
        getattr(self.wf_helper, validation)(**kwargs)
