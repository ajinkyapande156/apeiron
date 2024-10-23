"""
Copyright (c) 2022 Nutanix Inc. All rights reserved.

Author: umashankar.vd@nutanix.com

Nested Virt WF, this would as interface for
NV Feat - 12285 in Mjolnir config driven model
"""
# pylint: disable=unused-variable, unused-import, no-member

from framework.lib.nulog import INFO, WARN, ERROR, \
  STEP
from libs.framework import mjolnir_entities as entities
from libs.feature.nested_virtualization.hypervisor \
  import NestedVirtualizationFactory



class NestedVirtualizationWf():
  """
    This is workflow class for NV
    Provides generic functions for
    config drive mechanism and achieve
    Test Logic
    """

  def __init__(self, cluster=None):
    """
    Initialize workflow object
    Args:
      cluster(object): Nutest cluster object
    """
    self.cluster = cluster
    self.hw_flag = None
    self.timeout = 300

  def nested_virt_crud_wf(self, **kwargs):
    """
    Generic function to perform all CRUD tests
    Based on params sequence of operations are decided
    Args:
      kwargs
    Returns:
    """
    hypervisor_type = kwargs.get("hypervisor_type")
    hypervisor_obj = NestedVirtualizationFactory(self.cluster, hypervisor_type)
    # hypervisor_obj = fact.gethypervisor(hypervisor_type, cluster)
    hw_param = kwargs.get('hardware_param')
    vm_name = kwargs.get("vm_name")
    if hw_param == "True":
      INFO("Createvm with hw_param enabled")
      hypervisor_obj.create(**kwargs)
      hypervisor_obj.create_l2_network(**kwargs)
      vm_name, ip_addr = hypervisor_obj.vm_l2_deploy(**kwargs)
      hypervisor_obj.vm_l2_poweroff(**kwargs)
      hypervisor_obj.vm_l2_poweron(**kwargs)
      hypervisor_obj.vm_l2_vmlist()
      hypervisor_obj.run_l2_vm_io_workload(**kwargs)
      hypervisor_obj.vm_l2_poweroff(**kwargs)
      hypervisor_obj.vm_l2_delete(**kwargs)
    elif hw_param == "False":
      try:
        INFO("Createvm with hw_param disabled")
        hypervisor_obj.create(**kwargs)
        hypervisor_obj.create_l2_network(**kwargs)
        hypervisor_obj.vm_l2_deploy(**kwargs)
      except Exception:  # pylint: disable=broad-except
        acli_vm_cls = entities.ENTITIES.get("acli_vm")
        acli_vm = acli_vm_cls(interface_type="ACLI", name=vm_name)
        self.hw_flag = acli_vm.get()['config']['boot']\
        ['hardware_virtualization']
        if self.hw_flag is False:
          INFO("Current hw_virt status of %s is: %s" % (vm_name, self.hw_flag))
          INFO("This is an expected failure!!")
    else:
      INFO("Createvm with hw_param None, enable it later")
      hypervisor_obj.create(**kwargs)
      hypervisor_obj.create_l2_network(**kwargs)
      try:
        vm_name, ip_addr = hypervisor_obj.vm_l2_deploy(**kwargs)
        assert "L2 VM power on was expected to fail"
      except Exception:  # pylint: disable=broad-except
        INFO("Powering on VM failed as expected!!")
        INFO("Hardware param is disabled on Level 1 guest")
      hypervisor_obj.enable_vm_hardware_virtualization(**kwargs)
      hypervisor_obj.vm_l2_poweron(**kwargs)
      hypervisor_obj.vm_l2_vmlist()
      hypervisor_obj.run_l2_vm_io_workload(**kwargs)
      hypervisor_obj.vm_l2_poweroff(**kwargs)
      hypervisor_obj.vm_l2_delete(**kwargs)

  # def install_os(self, hypervisor_obj, kwargs, acli):
  #   """
  #       """
  #   hw_param = kwargs['kwargs']['hardware_param']
  #   if hw_param == True:
  #     INFO("Createvm with hw_param enabled")
  #     compute_config = {
  #       "compute_config": {
  #         "hardware_virtualization": "true",
  #         "uefi_boot": "false",
  #         "memory": 16000,
  #         "vcpus": 4
  #       }
  #     }
  #     os_install_config = {
  #       "os_install_config": {
  #         "boot_disk_size": 200000
  #       }
  #     }
  #     kwargs.update(compute_config)
  #     kwargs.update(os_install_config)
  #     vm = hypervisor_obj.install_hypervisor(**kwargs)
  #   elif hw_param == False:
  #     INFO("Createvm with hw_param disabled, enable it later")
  #
  # def enable_hyperv(self, hypervisor_obj, kwargs):
  #   """
  #       """
  #   hypervisor_obj.enable_hyperv()
  #
  # def create_switch(self, hypervisor_obj, kwargs):
  #   """
  #       """
  #   switch_name = kwargs['kwargs']['name']
  #   hypervisor_obj.create_l2_network(switch_name)
  #
  # def setup_l2_vm(self, hypervisor_obj, kwargs):
  #   """
  #       """
  #   l2_vm_os = kwargs['kwargs']['name']
  #   vm_name, ip_addr = hypervisor_obj.vm_l2_deploy("windows10")
  #
  # def crud_l2_ops(self, hypervisor_obj):
  #   """
  #       """
  #   hypervisor_obj.vm_l2_poweroff(vm_name)
  #   hypervisor_obj.vm_l2_poweron(vm_name)
  #   hypervisor_obj.vm_l2_vmlist()
  #   hypervisor_obj.run_l2_vm_io_workload(vm_name)
  #
  # def nested_virt_crud_wf_step(self, **kwargs):
  #   hypervisor_type = kwargs.get("hypervisor")
  #   cluster = entities.ENTITIES.get("rest_vm")
  #   acli = entities.ENTITIES.get("acli")
  #   fact = NestedVirtualizationFactory()
  #   hypervisor_obj = fact.gethypervisor(hypervisor_type, cluster)
  #   hw_param = kwargs.get('hardware_param')
  #
  #   """
  #       iterate over the list of operations to be carried
  #       This piece would need update at a later stage
  #       for operations/funcs to be invoked via executor
  #       """
  #   for operation in kwargs["operations"]:
  #     op_name = operation['operation']
  #     INFO("Attempting operation %s" % op_name)
  #     # self.op_name (hypervisor_obj, operation)
  #     function_to_be_called = getattr(self, op_name)
  #     if op_name == 'install_os':
  #       function_to_be_called(hypervisor_obj, operation, acli)
  #     else:
  #       function_to_be_called(hypervisor_obj, operation)
