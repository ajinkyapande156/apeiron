"""
Copyright (c) 2023 Nutanix Inc. All rights reserved.

Author: rishabh.kumar@nutanix.com
"""

from libs.feature.node_add_remove.interfaces.ncli \
  import NodeAddRemoveNcli

class NodeAddRemoveFactory:
  """
    NodeAddRemoveFactory
  """
  MAP = {
    "ncli": NodeAddRemoveNcli
  }

  def __new__(cls, **kwargs):
    """
    Create a new instance of the class using the specified interface type
    Args:
    **kwargs : dict
      interface_type : str, optional
        The type of interface to use for the instance. Possible values
        are "ncli" (default) and any other supported interface type.

    Returns:
      instance : cls
        A new instance of the class, configured based on the provided kwargs.
    """
    interface_type = kwargs.pop("interface_type", "ncli")
    if not cls.MAP.get(interface_type):
      interface_type = "ncli"
    return cls.MAP[interface_type](**kwargs)
