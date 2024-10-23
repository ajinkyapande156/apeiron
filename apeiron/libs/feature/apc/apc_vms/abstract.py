"""
Copyright (c) 2023 Nutanix Inc. All rights reserved.

Author: pritam.chatterjee@nutanix.com
"""


class AbstractApcVm():
  """AbstractApcVm"""
  def create(self, **kwargs):
    """
    create an apc enabled Vm with provided details
    Args:
    Returns:
    Raises:
    """
    raise NotImplementedError

  def get(self, **kwargs):
    """
    create an apc enabled Vm with provided details
    Args:
    Returns:
    Raises:
    """
    raise NotImplementedError

  def list(self, **kwargs):
    """
    create an apc enabled Vm with provided details
    Args:
    Returns:
    Raises:
    """
    raise NotImplementedError

  def toggle_apc(self, **kwargs):
    """
    Toggle apc status by updating the VM
    Args:
    Returns:
    Raises:
    """
    raise NotImplementedError

  def toggle_cpu_model(self, **kwargs):
    """
    Toggle cpu model by updating the VM
    Args:
    Returns:
    Raises:
    """
    raise NotImplementedError

  def get_apc_status(self, **kwargs):
    """
    get apc status
    Args:
    Returns:
    Raises:
    """
    raise NotImplementedError

  def get_cpu_model(self, **kwargs):
    """
    get cpu model for vm
    Args:
    Returns:
    Raises:
    """
    raise NotImplementedError

  def delete(self, **kwargs):
    """
    create an apc enabled Vm with provided details
    Args:
    Returns:
    Raises:
    """
    raise NotImplementedError

  def run_workload(self, **kwargs):
    """
    Runs a given workload
    Args:
    Returns:
    Raises:
    """
    raise NotImplementedError

  def run_workload_bg(self, **kwargs):
    """
    Runs a given workload in background
    Args:
    Returns:
    Raises:
    """
    raise NotImplementedError

  def stop_bg_workload(self, **kwargs):
    """
    stop a background workload
    Args:
    Returns:
    Raises:
    """
    raise NotImplementedError

  def get_bg_workload_status(self, **kwargs):
    """
    get background workload status
    Args:
    Returns:
    Raises:
    """
    raise NotImplementedError

  def power_cycle(self, **kwargs):
    """
    do a vm powercycle
    Args:
    Returns:
    Raises:
    """
    raise NotImplementedError

  def live_migrate(self, **kwargs):
    """
    perform vm live migrate
    Args:
    Returns:
    Raises:
    """
    raise NotImplementedError
