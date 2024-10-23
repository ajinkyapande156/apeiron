"""
REST v4 VM

Copyright (c) 2023 Nutanix Inc. All rights reserved.
Author: rishabh.kumar@nutanix.com
"""
#pylint: disable=no-member, unused-argument, no-else-return, protected-access
from libs.workflows.generic.vm.base_vm import BaseVm


class RestVmV4(BaseVm):
  """
  Rest VM v4 class. This class contains methods specific to REST v4 API
  """
  def __init__(self, cluster, interface_type, **kwargs):
    """
    Instantiate the object
    Args:
      cluster(object): NuTest cluster object
      interface_type(str): Interface type
      kwargs(dict): Keyword args
    Raises:
      Exception: NotImplementedError
    """
    super(RestVmV4, self).__init__(cluster, interface_type, **kwargs)
    raise NotImplementedError("Rest v4 interface not supported currently")
