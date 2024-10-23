"""
Copyright (c) 2023 Nutanix Inc. All rights reserved.

Author: pritam.chatterjee@nutanix.com
"""
# pylint: disable=bad-continuation, unused-argument, no-self-use, fixme
# pylint: disable=unused-import
import uuid
from framework.lib.nulog import INFO, WARN, ERROR
from libs.framework import mjolnir_entities as entities


class ApcVmAcli():
  """AbstractApcVm"""

  def __init__(self, *args, **kwargs):
    """
    create an apc enabled Vm with provided details
    Args:
    Returns:
    Raises:
        NuTestError
    """
    self.pe = entities.ENTITIES.get("pe")

  def create(self, **kwargs):
    """
    create an apc enabled Vm with provided details
    Args:
    Returns:
    Raises:
    """
    # FIXME: extra flags not handled here
    vm_name = kwargs.get("vm_name",
                         str(uuid.uuid1()).split("-")[0])
    vm_spec = {
      "no_key": [vm_name],
      "num_vcpus": kwargs.get("num_of_vcpus", 2),
      "num_vnuma_nodes": kwargs.get("vnuma_nodes", 0),
      "num_threads_per_core": kwargs.get("threads_per_core", 2),
      "num_cores_per_vcpu": kwargs.get("cores_per_vcpu", 1),
      "enable_metrics": False,
      "memory": str(kwargs.get("memory_size", 4 * 1024)) + "M",
      "uefi_boot": kwargs.get("boot_type", True),
      "windows_credential_guard": kwargs.get("cg", False),
      "secure_boot": kwargs.get("secure_boot", False),
      "machine_type": kwargs.get("machine_type", "pc"),
      "vcpu_hard_pin": kwargs.get("vcpu_hard_pin", False),
      "disable_branding": kwargs.get("disable_branding", False),
      "hardware_virtualization": kwargs.get("hardware_virtualization", False)
      # TODO: Remove this and check when the APC build is available
      # "apc_status": kwargs.get("apc_status", False),
      # "cpu_model": kwargs.get("cpu_model", "sandybridge")
    }
    return self._execute("vm", "create", vm_spec)

  def get(self, **kwargs):
    """
    create an apc enabled Vm with provided details
    Args:
    Returns:
    Raises:
    """
    vm_spec = {
      "no_key": [kwargs.get("vm_name")],
    }
    response = self._execute("vm", "get", vm_spec)
    # NOTE: Will only be for 1 VM. So using below code
    for vm_uuid in response["data"]:
      return response["data"][vm_uuid]

  def update(self, **kwargs):
    """
    Update the VM with provided params
    Kwargs:
    Returns:
    """
    vm_spec = {
      "no_key": [kwargs.pop("vm_name")],
    }
    vm_spec.update(**kwargs)
    return self._execute("vm", "update", payload=vm_spec)

  def list(self, *kwargs):
    """
    create an apc enabled Vm with provided details
    Args:
    Returns:
    Raises:
    """
    return self._execute("vm", "list", payload=None)

  def migrate(self, **kwargs):
    """
    migrate VM to dst host
    Args:
    Returns:
    Raises:
    """
    payload = {
      "no_key": kwargs.get("vm_name"),
      "host": kwargs.get("host"),
      "bandwidth_mbps": str(kwargs.get("bandwidth_mbps"))
    }
    payload = {k: v for k, v in payload.items() if v and v not in ['None']}
    cmd = "acli vm.migrate "
    for key in payload:
      if "no_key" in key:
        cmd += payload[key] + " "
      else:
        cmd += key + "=" + payload[key] + " "
    # import pdb; pdb.set_trace()
    INFO("Migration Command: %s" % cmd)
    return self.pe.execute(cmd, timeout=300)  # remove hardcoding @pritam
    # return self._execute("vm", "migrate", payload=payload)

  def delete(self, *args, **kwargs):
    """
    create an apc enabled Vm with provided details
    Args:
    Returns:
    Raises:
    """
    raise NotImplementedError

  def power_cycle(self, *args, **kwargs):
    """
    do a vm powercycle
    Args:
    Returns:
    Raises:
    """
    raise NotImplementedError

  def _execute(self, entity, method, payload):
    """
    Internal method to process payload and execute.
    Args:
      entity(str):
      method(str):
      payload(dict):
    Returns:
    Raises:
    """
    payload = {k: v for k, v in payload.items() if v}
    interface = entities.ENTITIES.get("acli_vm")(name="acli_vm")
    return interface.execute(entity, method, **payload)
