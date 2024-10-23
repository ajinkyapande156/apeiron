"""
Copyright (c) 2024 Nutanix Inc. All rights reserved.
Author: rishabh.kumar@nutanix.com

VM and its config related constants
"""

######### VM Limits #########
MAX_VCPUS = {
  "pc": 240,
  "q35": 240
}

MAX_MEM_MB = 4718592
############################

######### Host Limits #########
MAX_VM_PER_HOST = 128
###############################

UNSUPPORTED_BOOT_FEATURE_COMBINATIONS = {
  "legacy": ["vtpm", "credential_guard", "hardware_virtualization"],
  "uefi": ["credential_guard"],
  "secure": ["hardware_virtualization"]
}

BOOT_TYPES = ["legacy", "uefi", "secure"]
VM_FEATURES = ["credential_guard", "vtpm", "hardware_virtualization", "mem_oc"]
GUEST_OS_PICKER = {
  "legacy": "almalinux83",
  "uefi": "win11_enterprise_22h2_uefi_cg",
  "secure": "win11_professional_uefi_q35",
  "cg": "win11_enterprise_22h2_uefi_cg"
}

# Filled at runtime, and stored inside CVM to be used by post upgrade test
PRE_UPGRADE_VM_DATA = {}

PRE_UPGRADE_STEPS = [
  {
    "name": "generic.generic_wf.GenericWorkflows.step",
    "func_kwargs": {
      "operations": "add_boot_disk, add_disk, add_nic, power_on, "\
                    "validate_boot_type, validate_features",
      "steps": "bulk_ops",
      "step_name_suffix": "VM_SETUP--add_boot_disk-add_disk-add_nic-power_on"
    }
  },
  {
    "name": "generic.generic_wf.GenericWorkflows.step",
    "func_kwargs": {
      "operations": "guest_reboot, guest_shutdown, power_on, power_cycle," \
                    "shutdown, power_on",
      "steps": "bulk_ops",
      "step_name_suffix": "VM_POWEROPS"
    }
  },
  {
    "name": "generic.generic_wf.GenericWorkflows.step",
    "func_kwargs": {
      "operations": "enable_guest_features",
      "steps": "bulk_ops",
      "guest_features": ["wsl"],
      "step_name_suffix": "ENABLE_GUEST_FEATURES"
    }
  },
  {
    "name": "generic.generic_wf.GenericWorkflows.step",
    "func_kwargs": {
      "operations": "start_workloads",
      "power_off_non_migratable_vms": True,
      "upgrade_test": True,
      "steps": "bulk_ops",
      "step_name_suffix": "START_WORKLOADS"
    }
  },
  {
    "name": "generic.generic_wf.GenericWorkflows.step",
    "func_kwargs": {
      "operations": "migrate",
      "steps": "bulk_ops",
      "step_name_suffix": "migrate_vms"
    }
  }
]

POST_UPGRADE_STEPS = [
  {
    "name": "generic.generic_wf.GenericWorkflows.step",
    "func_kwargs": {
      "operations": "verify_workloads",
      "steps": "bulk_ops",
      "workload_types": ["io"],
      "step_name_suffix": "verify_workloads"
    }
  },
  {
    "name": "generic.generic_wf.GenericWorkflows.step",
    "func_kwargs": {
      "operations": "verify_guest_features",
      "steps": "bulk_ops",
      "guest_features": ["wsl"],
      "step_name_suffix": "VERIFY_GUEST_FEATURES"
    }
  },
  {
    "name": "generic.generic_wf.GenericWorkflows.step",
    "func_kwargs": {
      "operations": "validate_boot_type, validate_features, migrate",
      "steps": "bulk_ops",
      "step_name_suffix": "migrate_vms"
    }
  },
  {
    "name": "generic.generic_wf.GenericWorkflows.step",
    "func_kwargs": {
      "steps": "verify_no_vms_crashed"
    }
  },
  {
    "name": "generic.generic_wf.GenericWorkflows.step",
    "func_kwargs": {
      "operations": "guest_reboot, guest_shutdown, power_on, "\
                    "power_cycle, shutdown, power_on",
      "steps": "bulk_ops",
      "step_name_suffix": "vm_powerops"
    }
  },
  {
    "name": "generic.generic_wf.GenericWorkflows.step",
    "func_kwargs": {
      "operations": "remove",
      "steps": "bulk_ops",
      "step_name_suffix": "Delete_VMs"
    }
  }
]
