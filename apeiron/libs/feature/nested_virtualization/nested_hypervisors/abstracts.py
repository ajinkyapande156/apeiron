"""
Copyright (c) 2022 Nutanix Inc. All rights reserved.

Author: umashankar.vd@nutanix.com

Factory method for providing object/functions of hyperv type
"""


class AbstractNestedHypervisor():
  """AbstractNestedHypervisor class"""
  def create(self, **kwargs):
    """
    Create nested hypervisor
    Args:
    Returns:
    Raises:
    """
    raise NotImplementedError

  def get_status(self):
    """
    get nested hypervisor status
    Args:
    Returns:
    Raises:
    """
    raise NotImplementedError

  def create_l2_network(self, **kwargs):
    """
    create_l2_network
    Args:
    Returns:
    Raises:
    """
    raise NotImplementedError

  def get_l2_vm_power_state(self, **kwargs):
    """
    get_l2_vm_power_state
    Args:
    Returns:
    Raises:
    """
    raise NotImplementedError

  def vm_l2_deploy(self, **kwargs):
    """
    vm_l2_deploy
    Args:
    Returns:
    Raises:
    """
    raise NotImplementedError

  def vm_l2_poweron(self, **kwargs):
    """
    vm_l2_poweron
    Args:
    Returns:
    Raises:
    """
    raise NotImplementedError

  def vm_l2_poweroff(self, **kwargs):
    """
    vm_l2_poweroff
    Args:
    Returns:
    Raises:
    """
    raise NotImplementedError

  def vm_l2_reboot(self, **kwargs):
    """
    vm_l2_reboot
    Args:
    Returns:
    Raises:
    """
    raise NotImplementedError

  def vm_l2_delete(self, **kwargs):
    """
    vm_l2_delete
    Args:
    Returns:
    Raises:
    """
    raise NotImplementedError

  def vm_l2_ext_partition(self, **kwargs):
    """
    vm_l2_ext_partition
    Args:
    Returns:
    Raises:
    """
    raise NotImplementedError

  def get_vm_l2_ip(self, **kwargs):
    """
    get_vm_l2_ip
    Args:
    Returns:
    Raises:
    """
    raise NotImplementedError

  def run_l2_vm_io_workload(self, **kwargs):
    """
    run_l2_vm_io_workload
    Args:
    Returns:
    Raises:
    """
    raise NotImplementedError

  def get_l2_vm_list(self, **kwargs):
    """
    get_l2_vm_list
    Args:
    Returns:
    Raises:
    """
    raise NotImplementedError
