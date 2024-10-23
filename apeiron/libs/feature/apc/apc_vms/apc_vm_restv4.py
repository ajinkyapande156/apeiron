"""
Copyright (c) 2023 Nutanix Inc. All rights reserved.

Author: pritam.chatterjee@nutanix.com
"""
# pylint: disable=unused-import, no-self-use, unused-argument, fixme,
# pylint: disable= no-else-return
import random
import uuid

from framework.lib.nulog import INFO, WARN, ERROR
from libs.feature.apc.apc_vms.abstract \
  import AbstractApcVm
from libs.framework import mjolnir_entities as entities
from workflows.manageability.api.aplos import vms_api as VmsAPI


# TODO: copy methods from VmsAPI when isolating from nutest
# FIXME: The implementation is incomplete as of now.


class ApcVmRestv4(AbstractApcVm):
  """AbstractApcVm"""

  def __init__(self, **kwargs):
    """
    Initialize rest ApcVm rest v3 object
    Args:
    Returns:
    Raises:
    """
    self.vm_name = kwargs.get("vm_name",
                              str(uuid.uuid1()).split("-")[0])
    self.interface = entities.ENTITIES.get("restv3_vm")(name=self.vm_name)

  def __getattr__(self, item):
    """
    Execute a method from the interface class if not available here
    Args:
      item(str): function to execute
    Returns:
    Raises:
    """
    return self.interface.getattr(item)

  def create(self, **kwargs):
    """
    create an apc enabled Vm with provided details
    Args:
    Returns:
    Raises:
    """
    # TODO: please remove this VmsAPI dependency from here.
    vm_spec = VmsAPI.get_sample_spec()
    INFO('Updating VM [%s] configurations' % self.vm_name)
    vm_spec.update(self._get_config(**kwargs))
    if kwargs.get("apc_disabled", False):
      WARN("VM will be created with apc=disabled")
      vm_spec.pop("apc_config")
    vm_spec.update(self._get_boot_config(**kwargs))
    response = self.interface.create_vm_without_disk(self.vm_name, vm_spec,
                                                     False)
    return response

  def boot_with_os(self, **kwargs):
    """
    create an apc enabled Vm with provided details
    Args:
    Returns:
    Raises:
    """
    return self.interface.add_boot_disk(kwargs.get("vm_spec"),
                                        kwargs.get("os_name"))

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

  def delete(self, **kwargs):
    """
    create an apc enabled Vm with provided details
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

  def _get_config(self, **kwargs):
    """
    _get_config
    Args:
    Returns:
    Raises:
    """
    return {
      "vm_name": self.vm_name,
      "memory_size": kwargs.get("memory_size", 4 * 1024),
      "num_sockets": kwargs.get("num_of_vcpus", 2),
      "num_vcpus_per_socket": kwargs.get("cores_per_vcpu", 1),
      "apc_config": {
        "apc_enabled": True
      },
      "poll_interval": 5  # what is this ?
    }

  def _get_boot_config(self, **kwargs):
    """
    _get_boot_config
    Args:
    Returns:
    Raises:
    """
    # TODO: make more generic to address any boot type
    # currently considering only legacy and cg+vtpm
    boot_type = kwargs.get("boot_type", "legacy")
    if boot_type == "legacy":
      return {}
    else:
      return {
        'boot_config': {
          'boot_type': 'SECURE_BOOT'
        },
        'hardware_virtualization_enabled': True,
        'machine_type': 'Q35',
        'vtpm_config': {
          'vtpm_enabled': True
        }
      }
