"""
Copyright (c) 2024 Nutanix Inc. All rights reserved.
Author: rishabh.kumar@nutanix.com

Generate the VM combinations supported on the cluster
"""
from framework.lib.nulog import INFO
from libs.workflows.generic.vm.lib.vm_support \
  import VMSupport
from libs.workflows.generic.vm.lib.constants import (
  BOOT_TYPES, VM_FEATURES, UNSUPPORTED_BOOT_FEATURE_COMBINATIONS,
  GUEST_OS_PICKER, PRE_UPGRADE_STEPS, PRE_UPGRADE_VM_DATA, POST_UPGRADE_STEPS
)


class VMComboGenerator:
  """ VM Combo Generator class """
  def __init__(self, cluster, **kwargs):
    """
    Init method
    Args:
      cluster(object): NuTest cluster object
      kwargs(dict):
        combo_type(str): 1. one_to_one - Each VM has just one feature.
                            Here, max. possible combinations can be
                            (no. of boot_type * no. of. features)
                         2. combined - One VM per boot type and each of those
                            VM will have all the supported features.
    """
    self.cluster = cluster
    self.combo_type = kwargs.get("combo_type", "one_to_one")

  @staticmethod
  def create_pre_upgrade_steps(vm_combinations, **kwargs):
    """
    Create the pre upgrade test steps based on VM combinations
    Args:
      vm_combinations(list): List of VM combinations
    Returns:
      steps(dict): Test steps in the format required by framework
    """
    perform_powerops = kwargs.get("perform_powerops", True)
    steps = []
    for vm_combination in vm_combinations:
      boot_type = vm_combination[0]
      features = vm_combination[1]
      if "credential_guard" in features or "cg" in features:
        guest_os = GUEST_OS_PICKER["cg"]
      else:
        guest_os = GUEST_OS_PICKER[boot_type]
      vm_name = "%s_%s" % (boot_type, features.replace(", ", "_"))

      step = {
        "name": "generic.generic_wf.GenericWorkflows.step",
        "func_kwargs": {
          "interface_type": kwargs.get("interface_type", "REST"),
          "name":vm_name,
          "unique_vm_name": False,
          "vcpu": kwargs.get("vcpus", 2),
          "cores_per_vcpu": kwargs.get("cores_per_vcpu", 1),
          "memory": kwargs.get("memory", 4096),
          "boot_type": boot_type,
          "features": features,
          "guest_os": guest_os,
          "prechecks": False,
          "steps": "create_vm"
        }
      }
      steps.append(step)

      # Store the VM config here. vm_config of the VMs created during
      # pre upgrade test will be stored on CVM to be used by post upgrade test.
      PRE_UPGRADE_VM_DATA.update({vm_name: step["func_kwargs"]})
      PRE_UPGRADE_VM_DATA[vm_name].update({
        "bind": True,
        "exact_match": True
      })

    # Add the pre upgrade steps in config, these steps would be performed
    # on every VM created above, unless overwritten.
    for pre_upgrade_step in PRE_UPGRADE_STEPS:
      if perform_powerops or \
        pre_upgrade_step.get("func_kwargs", {})\
        .get("step_name_suffix", "").lower() != "vm_powerops":
        steps.append(pre_upgrade_step)

    return steps

  @staticmethod
  def create_post_upgrade_steps(vm_info, **kwargs):
    """
    Create the post upgrade steps
    Args:
      vm_info(dict): VM info stored on
    Returns:
      steps(dict): Test steps in the format required by framework
    """
    perform_powerops = kwargs.get("perform_powerops", True)
    steps = []
    expected_power_state_map = {}
    for vm_name, vm_data in vm_info.items():
      INFO("Found VM: %s in config" % vm_name)
      expected_power_state_map.update({
        vm_name: vm_data.pop("expected_power_state", "off")
      })
      step = {
        "name": "generic.generic_wf.GenericWorkflows.step",
        "func_kwargs": vm_data
      }
      step["func_kwargs"].update({"fail_if_not_present": True})
      steps.append(step)

    for post_upgrade_step in POST_UPGRADE_STEPS:
      if post_upgrade_step.get("func_kwargs", {}).get("operations", "") \
        in ["verify_workloads", "verify_guest_features"]:
        post_upgrade_step["func_kwargs"].update({
          "expected_power_state": expected_power_state_map
        })

      if perform_powerops or \
        post_upgrade_step.get("func_kwargs", {})\
        .get("step_name_suffix", "").lower() != "vm_powerops":
        steps.append(post_upgrade_step)

    return steps

  def generate_vm_combinations(self):
    """
    Generate VM combinations
    Args:
    Returns:
      vm_combinations(list): List of possible VM combinations
    """
    vm_support = VMSupport(cluster=self.cluster)
    vm_combinations = []
    if self.combo_type == "one_to_one":
      for boot_type in BOOT_TYPES:
        for feature in VM_FEATURES:
          if (feature not in UNSUPPORTED_BOOT_FEATURE_COMBINATIONS[boot_type]
              and vm_support.run_checks(boot_type=boot_type, feature=feature)):
            vm_combinations.append((boot_type, feature))
    else:
      for boot_type in BOOT_TYPES:
        curr_features = ""
        for feature in VM_FEATURES:
          if (feature not in UNSUPPORTED_BOOT_FEATURE_COMBINATIONS[boot_type]
              and vm_support.run_checks(boot_type=boot_type, feature=feature)):
            curr_features += feature
            curr_features += ", "
        curr_features = curr_features.rstrip(", ")
        vm_combinations.append((boot_type, curr_features))
      # Add a UEFI and Secure boot VM as the UEFI and Secure boot VM
      # chosen above have hardware_virtualization and credential_guard features
      # which don't allow VM migrtaions always. So, having a UEFI and Secure
      # Boot VM would help in getting coverage for all boot types
      # irrespective of cluster
      vm_combinations.append(("uefi", ""))
      vm_combinations.append(("secure", ""))

    INFO("Suported Combinations: %s" % len(vm_combinations))
    for vm_combination in vm_combinations:
      INFO("%s -- -- -- -- --  %s" % (vm_combination[0], vm_combination[1]))

    return vm_combinations
