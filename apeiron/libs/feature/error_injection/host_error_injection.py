"""
Copyright (c) 2024 Nutanix Inc. All rights reserved.

Author: pritam.chatterjee@nutanix.com

Description:
inject error or correct error for host
"""
# pylint: disable=broad-except, unexpected-keyword-arg, unused-import
# pylint: disable=no-self-use, inconsistent-return-statements, no-else-return
# pylint: disable=unused-argument, protected-access
import random
import time
from framework.exceptions.interface_error import NuTestCommandExecutionError
from framework.lib.nulog import INFO, WARN, ERROR
from libs.framework import mjolnir_entities as entities
from libs.framework.mjolnir_executor import use_executor
from libs.feature.error_injection.cvm_error_injection \
  import ErrorCvm
from workflows.systest.lib.ipmi_tool import IpmiTool


class ErrorHost:
  """ErrorHost class"""
  def __init__(self):
    """Create object"""
    self.cluster = entities.ENTITIES.get("pe")

  def host_reboot(self, host, **kwargs):
    """
    Reboots the given host
    Args:
      host(object): nutest hypervisor object
    Returns:
    Raises:
    """
    try:
      self.is_host_accessbile(host, **kwargs)
      INFO("Check all CVMs are out of maintanence")
      err_cvm = ErrorCvm()
      err_cvm.wait_for_all_cvms_out_of_mm(**kwargs)
      host.reboot()
      INFO("Check all CVMs are out of maintanence")
      err_cvm.wait_for_all_cvms_out_of_mm(**kwargs)
      INFO("Checking if all hosts are schedulable")
      self.are_hosts_schedulable()
      INFO("Host %s is in good state" % host.ip)
    except NuTestCommandExecutionError:
      WARN("Continuing as this is expected error")

  def host_ipmi_powercycle(self, **kwargs):
    """
    Power cycle a host via IPMI
    Args:
      kwargs(dict): Kwargs
        host(object): Host object
    Returns:
    """
    # NOTE: DO NOT USE, NO ERRORS RAISED ON POWERCYCLE FAILURE
    host = kwargs.get("host", None)
    if host is None:
      INFO("No host provided, pick up a random host")
      host = random.choice(self.cluster.hypervisors)

    # IpmiTool module imported here doesn't accept ipmi username and address.
    # If host object doesn't have ipmi_address and ipmi_username, it will
    # fail with error - host object has no attribute.
    # Hence, setting it here with the use of ipmi attribute of host.
    if hasattr(host, 'ipmi'):
      setattr(host, 'ipmi_address', host.ipmi['ip'])
      setattr(host, 'ipmi_username', host.ipmi['user'])

    # Set the service_vmexternal_ip to svm IP as the IPMI module
    # uses that instead of svm IP
    if hasattr(host, '_svm_ip'):
      setattr(host, 'service_vmexternal_ip', host._svm_ip)

    ipmi_tool = IpmiTool(host)

    # host_power_off_time = time.time()
    # INFO("power off the host: %s" % host.ip)
    # ipmi_tool.power_off()

    # INFO("Monitor host until power off completes")
    # self._monitor_task(
    #   cluster=self.cluster, start_time=host_power_off_time,
    #   operation=".*HaFailover.*", timeout_in_sec=timeout
    # )

    time.sleep(120)

    # host_power_on_time = time.time()
    INFO("Power on host %s" % host.ip)
    ipmi_tool.power_on()

    # INFO("Monitor host until power on completes")
    # self._monitor_task(
    #   cluster=self.cluster, start_time=host_power_on_time,
    #   operation=".*HaFailover.*", timeout_in_sec=timeout
    # )
    self.wait_for_host_to_recover(host)

  def wait_for_host_to_recover(self, host, **kwargs):
    """
    Wait for host to reboot with cvm recovery
    Args:
      host(object): nutest hypervisor object
    Kwargs:
      retries: no of times to poll
      delay: delay between each poll
    Returns:
    Raises:
    """
    INFO("Check %s if host became accessible" % host.ip)
    self.is_host_accessbile(host, **kwargs)
    err_cvm = ErrorCvm()
    INFO("Check all CVMs are out of maintanence")
    err_cvm.wait_for_all_cvms_out_of_mm(**kwargs)
    INFO("Checking if all hosts are schedulable")
    self.are_hosts_schedulable()
    INFO("Host %s is in good state" % host.ip)

  @use_executor
  def is_host_accessbile(self, host, **kwarg):
    """
    Check if given host is accessible
    Args:
      host(object): nutest hypervisor object
    Returns:
    Raises:
    """
    return host.is_accessible()

  def are_hosts_schedulable(self):
    """
    Check if all hosts are schedulable
    Args:
    Returns:
    Raises:
    """
    cluster = entities.ENTITIES.get("pe")
    for host in cluster.hypervisors:
      self.is_host_schedulable(host, retries=30, delay=30)

  @use_executor
  def is_host_schedulable(self, host):
    """
    Check if the given host is schedulable
    Args:
      host(object): nutest hypervisor object
    Returns:
    Raises:
    """
    acli = entities.ENTITIES.get("acli_vm")(name="nothing")
    host_info = acli.execute(entity="host", cmd='get %s' % host.ip)
    is_schedulable = host_info["data"][host.uuid]["schedulable"]
    INFO("Host is schedulable: %s" % is_schedulable)
    assert is_schedulable, "Host is schedulable: %s" % is_schedulable

  def restart_service(self, host, service_name, **kwargs):
    """
    Restart Host Service
    Args:
      host(object): nutest hypervisor object
      service_name(str): service name
    Returns:
    Raises:
    """
    retries = kwargs.get("retries", 3)
    delay = kwargs.get("delay", 5)
    self.wait_for_host_to_recover(host)
    self.are_hosts_schedulable()
    self.is_host_accessbile(host)
    INFO("Restarting %s Service on: %s" % (service_name, host.ip))
    self._service_restart(service_name, host)
    service_status = self._check_service_is_active(
      host, service_name,
      retries=retries, delay=delay)
    assert service_status == "active", "Service is not active"
    self.wait_for_host_to_recover(host)
    self.are_hosts_schedulable()
    self.is_host_accessbile(host)

  def qemu_process_kill(self, vm_uuid, host, **kwargs):
    """
    Kill Qemu Process corresponding to a  VM
    Args:
      vm_uuid(str): Name of the VM for qemu process to kill
      host(object): nutest hypervisor object
    Returns:
    Raises:
    """

    cmd = ("ps -ef | grep '/usr/libexec/qemu-kvm -uuid %s' | grep -v grep | "
           "awk '{print $2}'") % vm_uuid
    result = host.execute(cmd)
    pid_a = result['stdout'].strip()
    assert pid_a is not None, ("Failed to find qemu process pid for %s"
                               % vm_uuid)
    cmd = "kill -9 %s" % pid_a
    result = host.execute(cmd)
    assert result['status'] == 0, "Failed to kill qemu process %s" % pid_a
    cmd = ("ps -ef | grep '/usr/libexec/qemu-kvm -uuid %s' | grep -v grep | "
           "awk '{print $2}'") % vm_uuid
    result = host.execute(cmd)
    pid_b = result['stdout'].strip()
    assert pid_a != pid_b, "qemu process did not change the pid %s" % pid_b


  def _service_restart(self, service_name, host):
    """
    Internal method to restart a service with systemctl command
    Args:
      host(object): nutest hypervisor object
      service_name(str): service to restart
    Returns:
    Raises:
    """
    cmd = "systemctl restart %s" % service_name
    result = host.execute(cmd)
    assert result["status"] == 0, "Service restart failed"

  @use_executor
  def _check_service_is_active(self, host, service_name, **kwargs):
    """
          Check if service is active

          Args:
            host(object): host on which cmd needs to run
            service_name(str): service for which status needs to be checked

          Returns:
            status of service
    """
    cmd = "systemctl is-active %s" % service_name
    INFO("Check service status %s on host: %s" % (service_name, host.ip))
    result = host.execute(cmd, ignore_errors=True)
    return result["stdout"].strip()
