"""
Copyright (c) 2022 Nutanix Inc. All rights reserved.

Author: pritam.chatterjee@nutanix.com
"""
# pylint: disable=import-error

class AbstractTest(object):
  """AbstractTest class"""
  @classmethod
  def get_tags(cls):
    """
    Get tags for the test
    Args:
    Returns:
    Raises:
    """
    raise NotImplementedError

  @classmethod
  def get_default_params(cls):
    """
    Get default params for the test
    Args:
    Returns:
    Raises:
    """
    raise NotImplementedError

  @classmethod
  def get_pre_operations(cls):
    """
    Get default pre operations for the test
    Args:
    Returns:
    Raises:
    """
    raise NotImplementedError

  @classmethod
  def get_post_operations(cls):
    """
    Get default post operations for the test
    Args:
    Returns:
    Raises:
    """
    raise NotImplementedError

  @classmethod
  def execute_pre_operations(cls, *args, **kwargs):
    """
    Operations to be executed before the test execution starts
    Args:
    Returns:
    Raises:
    """
    raise NotImplementedError

  @classmethod
  def execute_post_operations(cls, **params):
    """
    Operations to be executed after the test execution starts
    Args:
    Returns:
    Raises:
    """
    raise NotImplementedError

  def run(self, *args, **kwargs):
    """
    Run the test
    Args:
    Returns:
    Raises:
    """
    raise NotImplementedError

  def teardown(self):
    """
    Cleanup for the tests
    Args:
    Returns:
    Raises:
    """
    raise NotImplementedError


class AbstractVerifier(object):
  """AbstractVerifier class"""
  def pre_validate(self, *args, **kwargs):
    """
    Validate if verifier needs to be executed
    Args:
    Returns:
    Raises:
    """
    pass

  def verify(self, *args, **kwargs):
    """
    Execute the verifier
    Args:
    Returns:
    Raises:
    """
    raise NotImplementedError


class AbstractExecutor(object):
  """AbstractExecutor class"""
  @staticmethod
  def execute_plan(*args, **kwargs):
    """
    Execute a plan
    Args:
    Returns:
    Raises:
    """
    raise NotImplementedError


class AbstractPlanner(object):
  """AbstractPlanner class"""
  @staticmethod
  def create_plan(*args, **kwargs):
    """
    Create a qualification plan
    Args:
    Returns:
    Raises:
    """
    raise NotImplementedError


class AbstractOperatingSystem(object):
  """AbstractOperatingSystem class"""
  def get_edition_info(self, **kwargs):
    """
    Get the type of operating system
    Args:
    Returns:
    Raises:
    """
    raise NotImplementedError

  def get_build_info(self, **kwargs):
    """
    Get build info from guest os
    Args:
    Returns:
    Raises:
    """
    raise NotImplementedError

  def get_kernel_info(self, **kwargs):
    """
    Get kernel info from guest os
    Args:
    Returns:
    Raises:
    """
    raise NotImplementedError

  def get_os_architecture(self):
    """
        Return OS Architecture info
        Args:
        Returns:
          os_arch(int)
        Raises:
    """
    raise NotImplementedError

  def verify_os_boot(self, **kwargs):
    """
    Verify successful boot of guest os
    Args:
    Returns:
    Raises:
    """
    raise NotImplementedError

  def install_os_updates(self, **kwargs):
    """
    Install latest updates on guest OS
    Args:
    Returns:
    Raises:
    """
    raise NotImplementedError

  def get_nics(self, **kwargs):
    """
    Get network interfaces
    Args:
    Returns:
      nics(list)
    Raises:
    """
    raise NotImplementedError

  def get_nics_with_ips(self, **kwargs):
    """
    Get network interfaces with their ips
    Args:
    Returns:
      nic_ips(dict)
    Raises:
    """
    raise NotImplementedError

  def get_threads_per_core(self, **kwargs):
    """
    Return number of threads per core
    Args:
    Returns:
      threads(int)
    Raises:
    """
    raise NotImplementedError

  def get_guest_cpu(self, **kwargs):
    """
    Get guest OS cpu info.
    Args:
    Returns:
    Raises:
    """
    raise NotImplementedError

  def get_guest_vcpu(self, **kwargs):
    """
    Get guest OS vcpu info.
    Args:
    Returns:
    Raises:
    """
    raise NotImplementedError

  def get_guest_memory(self, **kwargs):
    """
    Get guest OS memory info.
    Args:
    Returns:
    Raises:
    """
    raise NotImplementedError

  def verify_secure_boot(self, **kwargs):
    """
    Verify if OS has boot into secure boot mode
    Args:
      kwargs(dict): optional args for execute method
    Returns:
      output(bool):
    Raises:
    """
    raise NotImplementedError

  def verify_uefi_boot(self, **kwargs):
    """
    Verify if OS has boot into uefi mode
    Args:
      kwargs(dict): optional args for execute method
    Returns:
      output(bool):
    Raises:
    """
    raise NotImplementedError

  def verify_vtpm_boot(self, **kwargs):
    """
    Verify if OS has booted with vtpm enabled
    Args:
      kwargs(dict): optional args for execute method
    Returns:
      output(tuple): stdin, stdout, stderr
    Raises:
    """
    raise NotImplementedError

  def verify_cg_boot(self, **kwargs):
    """
    Verify if OS has booted with credential guard enabled
    Args:
      kwargs(dict): optional args for execute method
    Returns:
      output(tuple): stdin, stdout, stderr
    Raises:
    """
    raise NotImplementedError

  def bring_cpu_online(self):
    """
    Try to bring cpu/cores online after hot add
    Args:
    Returns:
    Raises:
    """
    raise NotImplementedError

  def bring_mem_online(self):
    """
    Try to bring memory online after hot add
    Args:
    Returns:
    Raises:
    """
    raise NotImplementedError

  def configure_rp_filter(self, **kwargs):
    """
    Configure rp filter from within guest OS to accept new IPs
    Args:
      kwargs(dict): optional args for execute method
    Returns:
      output(bool):
    Raises:
    """
    raise NotImplementedError

  def bring_vnics_online(self, **kwargs):
    """
    Bring new interfaces online in guest for vnic hot add
    Args:
      kwargs(dict): optional args for execute method
    Returns:
      output(bool):
    Raises:
    """
    raise NotImplementedError

  def verify_syslog_conflicts(self):
    """
    Verify for any conflict messages in syslogs
    Args:
    Returns:
    Raises:
    """
    raise NotImplementedError
