"""
Copyright (c) 2023 Nutanix Inc. All rights reserved.

Author: pritam.chatterjee@nutanix.com
"""
import copy
import os
import pandas as pd

# pylint: disable=wrong-import-order, no-member, unused-variable
# pylint: disable=ungrouped-imports, no-self-use, fixme, unused-import
# pylint: disable=anomalous-backslash-in-string, unused-import,
# pylint: disable=unnecessary-comprehension, unused-argument
# pylint: disable=bad-continuation, inconsistent-return-statements
# pylint: disable=too-many-locals, invalid-name, no-else-return
# pylint: disable=protected-access, useless-else-on-loop, too-many-function-args
# pylint: disable=too-many-statements
import time
from tabulate import tabulate
from libs.framework.nulog import INFO, WARN, ERROR, STEP
from libs.framework.exceptions.nutest_error import NuTestError
from libs.framework import mjolnir_entities as entities
from libs.feature.apc.factory import ApcVmFactory
from libs.framework.mjolnir_executor import BasicExecutor
from products.ahv.workflows.apc.wf_helpers import ApcWfHelper
from libs.feature.dirty_quota.dirty_quota_cluster \
  import DirtyQuotaCluster
from libs.ahv.workflows.gos_qual. \
  generic_guest_qualifier_v2 import GenericGuestQualifierv2


# from workflows.acropolis.upgrade.perform_ahv_aos_upgrade import \
#   PerformAhvAosUpgrade


class ApcWorkflow:
  """ApcWorkflow class"""

  def __init__(self, cluster=None, **kwargs):
    """
    Create object
    Args:
      cluster(object):
    Returns:
    Raises:
    """
    self.cluster = cluster
    self.wf_helper = ApcWfHelper(cluster=self.cluster)
    self.vm_cache = []

  def basic_apc_vm_validations(self, **kwargs):
    """
    Steps:
      1. Create a VM with APC enabled or disabled, different cpu models
      2. Will used restv3 or restv4 as per given config. Defaults to v3
      3. Power on VM.
      4. Run workloads if mentioned in config.
      5. Do LM if mentioned in config
    Args:
    Returns:
    Raises:
    """
    validations = kwargs.pop("validations", '')
    STEP("Creating VM with provided specs")
    INFO("Validating cpu model %s" % kwargs.get("cpu_model", "default"))
    if "apc_enabled" in kwargs:
      kwargs["apc_config"] = {
        "enabled": kwargs.get("apc_enabled", True)
      }
      INFO("ADDING APC CONFIG: %s" % kwargs["apc_config"])
      if kwargs.get("cpu_model"):
        INFO("Adding cpu model reference for %s" % kwargs.get("cpu_model"))
        kwargs["apc_config"].update({
          "cpu_model_reference": {
            "kind": "cpu_model",
            "uuid": self.wf_helper.get_cpu_model_uuid(kwargs.get("cpu_model"))
          }})
        INFO("ADDING CPU MODEL: %s" % kwargs["apc_config"])
    vm_details = self.wf_helper.validate_vm_create(**kwargs)
    # for validation in validations.split(","):
    #   if validation in ['']:
    #     continue
    #   validation = validation.strip()
    #   STEP("Performing the validation: [%s]" % validation)
    #   getattr(self.wf_helper, validation)(vm_spec=vm_details, **kwargs)

    if isinstance(validations, str):
      for validation in validations.split(","):
        if validation in ['']:
          continue
        validation = validation.strip()
        STEP("Performing the validation: [%s]" % validation)
        getattr(self.wf_helper, validation)(vm_spec=vm_details, **kwargs)
    elif isinstance(validations, list):
      kwargs.pop("expected_result", {})
      for validation in validations:
        STEP("Executing: %s" % validation["name"])
        getattr(self.wf_helper, validation["name"])(
          expected_result=validation.get("expected_result", "Pass"),
          vm_spec=vm_details,
          **kwargs)
    self.vm_cache.append(vm_details)
    if kwargs.get("test_clone"):
      STEP("Validating VM clone")
      clone_vm_details = self.wf_helper.validate_vm_clone(vm_spec=vm_details)
      for validation in validations.split(","):
        if validation in ['']:
          continue
        validation = validation.strip()
        STEP("Performing the validation on Cloned VM: [%s]" % validation)
        getattr(self.wf_helper, validation)(vm_spec=clone_vm_details, **kwargs)
    return vm_details

  def validate_ha(self, **kwargs):
    """
    Priority: P2
    Validate apc enabled|disabled with different VM params like, enable_matrix,
    cpu_passthru
    Args:
    Kwargs:
      on_create(bool):
    Returns:
    Raises:
    """
    default = [
      {
        "vm_name": "apc_enabled_vm_1",
        "apc_enabled": True,
        "boot_type": "uefi",
        "add_vnic": True,
        # "validations": ["validate_apc_status", "validate_cpu_model"]
      }
    ]
    plan = kwargs.pop("plan", default)
    INFO("Configuring HA")
    self.wf_helper.configure_ha()

    INFO("Finding the host with max supported cpu model and "
         "setting up testbed: %s" % plan)
    host = self.wf_helper.get_host_with_max_cpu()
    # import pdb; pdb.set_trace()

    vms_to_check = []
    for vm in plan:
      vm_spec = self.basic_apc_vm_validations(**vm)
      apc_vm = ApcVmFactory(**kwargs)
      vms_to_check.append(vm_spec)
      vm_spec['host_reference'] = apc_vm.get(vm_spec=vm_spec)['host_reference']
      if not host.uuid == vm_spec['host_reference']['uuid']:
        INFO("Live migrating VM %s to host %s" % (vm_spec["uuid"],
                                                  host.uuid))
        self.wf_helper.validate_lm(vm_spec=vm_spec,
                                   target_host=host.uuid)

    INFO("Testbed setup compeleted, all VM are on host: %s" % host.uuid)

    STEP("Triggering HA by stopping libvirtd on Host %s" % host.uuid)
    self.wf_helper.validate_ha(target_host=host)

    # NOTE: This can be made parallel once stable
    try:
      for i, vm_spec in enumerate(vms_to_check):
        validations = plan[i].get("validations", '')
        for validation in validations.split(","):
          if validation in ['']:
            continue
          validation = validation.strip()
          STEP("Performing the validation post HA failover: [%s] for VM: [%s]"
               % (validation, vm_spec["uuid"]))
          getattr(self.wf_helper, validation)(vm_spec=vm_spec, **plan[i])
      INFO("HA validation successfully completed")
    except Exception as ex:
      ERROR("HA validation failed")
      raise ex
    finally:
      INFO("Recovering livirtd on failed Host %s" % host.uuid)
      self.wf_helper.restore_libvirtd(target_host=host)
      INFO("Removing HA from cluster")
      self.wf_helper.disable_ha()

  def validate_service_restarts(self, **kwargs):
    """
    Priority: P2
    Validate different operations on the cluster and host like:
      service restarts
    Args:
    Kwargs:
      operation(str): libvirt_restart|gateway_restart|acropolis_restart|
                      node_restart
      which_host(str): max_cpu_supported|min_cpu_supported
      plan(list): list of dict with vm configurations and
                  validations to be performed. Validations are performed before
                  and after
    Returns:
    Raises:
    """
    default = [
      {
        "vm_name": "apc_enabled_vm_1",
        "apc_enabled": True,
        "boot_type": "uefi",
        "add_vnic": True,
        # "validations": ["validate_apc_status", "validate_cpu_model"]
      }
    ]
    operations_dict = {
      "libvirt_restart": self.wf_helper.restart_libvirt,
      "gateway_restart": self.wf_helper.restart_gateway,
      "node_restart": self.wf_helper.restart_node,
      "hostagent_restart": self.wf_helper.restart_hostagent
    }
    host_selection_dict = {
      "max_cpu_supported": self.wf_helper.get_host_with_max_cpu,
      "min_cpu_supported": self.wf_helper.get_host_with_min_cpu
    }
    plan = kwargs.get("plan", default)
    operation = kwargs.get("operation", "libvirt_restart")
    which_host = kwargs.get("which_host", "max_cpu_supported")
    INFO("=====================")
    INFO("Plan: %s" % plan)
    INFO("Operation: %s" % operation)
    INFO("On which Host: %s [Not valid for upgrades]" % which_host)
    INFO("=====================")

    INFO("Finding the host with %s and "
         "setting up testbed" % which_host)
    host = host_selection_dict[which_host]()

    vms_to_check = []
    for vm in plan:
      vm_spec = self.basic_apc_vm_validations(**vm)
      apc_vm = ApcVmFactory(**kwargs)
      vms_to_check.append(vm_spec)
      vm_spec['host_reference'] = apc_vm.get(vm_spec=vm_spec)['host_reference']
      if not host.uuid == vm_spec['host_reference']['uuid']:
        INFO("Live migrating VM %s to host %s" % (vm_spec["uuid"],
                                                  host.uuid))
        self.wf_helper.validate_lm(vm_spec=vm_spec,
                                   target_host=host.uuid)

    INFO("Testbed setup compeleted, all VM are on host: %s" % host.uuid)

    # import pdb; pdb.set_trace()
    STEP("Performing operation %s on %s" % (operation, host.uuid))
    operations_dict[operation](host=host)

    # NOTE: This can be made parallel once stable
    try:
      for i, vm_spec in enumerate(vms_to_check):
        validations = plan[i].get("validations", '')
        for validation in validations.split(","):
          if validation in ['']:
            continue
          validation = validation.strip()
          STEP("Performing the validation post operation [%s]: [%s] "
               "for VM: [%s]"
               % (operation, validation, vm_spec["uuid"]))
          getattr(self.wf_helper, validation)(vm_spec=vm_spec, **plan[i])
      INFO("%s validation successful" % operation)
    except Exception as ex:
      ERROR("%s validation failed" % operation)
      raise ex

  def validate_node_add_remove(self, **kwargs):
    """
    Priority: P2
    Validate apc enabled|disabled with different VM params like, enable_matrix,
    cpu_passthru
    Args:
    Kwargs:
      on_create(bool):
    Returns:
    Raises:
    """
    self.wf_helper.node_add_rm(**kwargs)

  def validate_guest_cpu_flags_upgrade(self, **kwargs):
    """
    Priority: P1
    Validate Guest OS CPU flags after upgrade to APC build.
    Args:
    Kwargs:
      on_create(bool):
    Returns:
    Raises:
    """
    # Get the VMs created by GOS qual framework (inputs, cpu_models)
    upgrade_handler = entities.ENTITIES.get("upgrade_handler")(
      test_args=kwargs)
    STEP("Reimaging cluster to source AHV and AOS if required")
    upgrade_handler.image_cluster()
    filters = {
      "os": "rhel9.2,windows10_22H2,windows11_22H2",
      "type": "server, enterprise",
      "boot": "legacy, uefi, secureboot, vtpm_secureboot"
    }
    test_filters = {
      "tests": "cdrom_apc_boot"
    }
    report = {
      "Guest_OS": [],
      "VM_Name": [],
      "Boot_Config": [],
      "Cpu_Flags_Pre": [],
      "Cpu_Flags_Post": [],
      "Cpu_Flags_Count_Pre": [],
      "Cpu_Flags_Count_Post": [],
      "Cpu_Model": []
    }
    g = GenericGuestQualifierv2(self.cluster, test_selection_mode="apc")
    if "rel_to_master" in kwargs.get("upgrade_type"):
      cpu_models = self.wf_helper.get_baseline_cpu_models()
      # Discover all the VMs and create a list of flags against their name
      plan = g.generate_plan(filters=filters, test_filters=test_filters)
      STEP("Adding following CPU models for VM creation: %s" % cpu_models)
      execution_plan = []
      for each in plan:
        for cpu_model in cpu_models:
          model_name = cpu_model["name"].split()[-1].strip()
          mod = copy.deepcopy(each)
          mod["tests"][0]["params"]["apc_enabled"] = True
          mod["tests"][0]["params"]["cpu_model"] = model_name
          mod["vm_name"] = "_".join([mod["os"], mod["boot"], model_name])
          execution_plan.append(mod)
          report["Guest_OS"].append(mod["os"])
          report["VM_Name"].append(mod["vm_name"])
          report["Boot_Config"].append(mod["boot"])
    else:
      plan = g.generate_plan(filters=filters, test_filters=test_filters)
      execution_plan = plan
      for i, each in enumerate(plan):
        each["vm_name"] = "_".join([each["os"], each["boot"],
                                    "pre_upgrade_" + str(i)])
        report["Guest_OS"].append(each["os"])
        report["VM_Name"].append(each["vm_name"])
        report["Boot_Config"].append(each["boot"])
    STEP("Creating VMs now in Pre-Upgrade ")
    g.generate_plan(execution_plan=execution_plan)
    g.execute_plan()

    for vm_name in report["VM_Name"]:
      vm_spec = self.wf_helper.validate_vm_create(
        **{
          "power_on": False,
          "discover": True,
          "vm_name": vm_name
        }
      )
      STEP("Capturing flags before Upgrade: %s" % vm_name)
      if "windows" not in vm_name:
        data = self.wf_helper.get_cpu_flags_linux(vm_spec=vm_spec)
        report["Cpu_Flags_Pre"].append(data["FLAGS"])
        report["Cpu_Flags_Count_Pre"].append(data["COUNT"])
      else:
        report["Cpu_Flags_Pre"].append('NA')
        report["Cpu_Flags_Count_Pre"].append(0)

    STEP("Performing Upgrade now")
    upgrade_handler.trigger_upgrade()

    if kwargs.get("rel_to_master"):
      # CPU model should not change after power-cycle
      pass
    else:
      for vm_name in report["VM_Name"]:
        # perform power-cycle of all VMs
        vm_spec = self.wf_helper.validate_vm_create(
          **{
            "power_on": False,
            "discover": True,
            "vm_name": vm_name
          }
        )
        STEP("Validating Post-Upgrade for VM: %s" % vm_name)
        INFO("CHECKING NO CPU MODEL BEFORE POWER-CYCLE FOR VM: %s" % vm_name)
        self.wf_helper.validate_no_cpu_model_acli(vm_spec=vm_spec)
        INFO("CHECKING POWER-OPS FOR VM: %s" % vm_name)
        self.wf_helper.power_ops(vm_spec=vm_spec)
        # validate that the max baseline model is used for them

        max_baseline = \
          self.wf_helper.get_max_baseline_cpu_model()["name"].split()[-1]
        INFO("CHECKING IF %s PICKED CPU MODEL: %s" % (vm_name, max_baseline))
        self.wf_helper.validate_cpu_model_acli(vm_spec=vm_spec,
                                               expected_cpu_model=max_baseline)

        INFO("CHECKING THERE IS NO apc_config IN REST API FOR VM: %s" % vm_name)
        self.wf_helper.validate_no_apc_config(vm_spec=vm_spec)
        # INFO("VALIDATING LM To ALL HOSTS ON CLUSTER FOR VM: %s" % vm_name)
        # self.wf_helper.validate_lm_roundrobin(vm_spec=vm_spec)

    for vm_name in report["VM_Name"]:
      vm_spec = self.wf_helper.validate_vm_create(
        **{
          "power_on": False,
          "discover": True,
          "vm_name": vm_name
        }
      )
      STEP("Capturing flags after Upgrade for :%s" % vm_name)
      if "windows" not in vm_name:
        data = self.wf_helper.get_cpu_flags_linux(vm_spec=vm_spec)
        report["Cpu_Flags_Post"].append(data["FLAGS"])
        report["Cpu_Flags_Count_Post"].append(data["COUNT"])
      else:
        report["Cpu_Flags_Post"].append('NA')
        report["Cpu_Flags_Count_Post"].append(0)

    INFO(tabulate(report, headers="keys",
                  tablefmt="grid"))
    INFO(report)
    df = pd.DataFrame.from_dict(report, orient='index').T
    fh = os.path.join(os.environ['NUTEST_LOGDIR'], "cpu_flags.csv")
    df.to_csv(fh)

  def delete_from_vm_cache(self, **kwargs):
    """
    Delete VMs created by workflow methods.
    Args:
    Kwargs:
    Returns:
    Raises:
    """
    for vm_spec in self.vm_cache:
      self.wf_helper.validate_delete_vm(vm_spec)

  def validate_cpu_model_minor_versions(self, **kwargs):
    """
    Priority: P1, P2
    Steps:
      1. Find a host that supports given CPU model
      2. Find all the versions for the given CPU model
      3. Create a VM with those models and power on
      4. Do basic validation.
    Args:
    Kwargs:
      cpu_model:
    Returns:
    Raises:
    """
    cpu_model = kwargs.get("cpu_model", "sandybridge")
    host = self.wf_helper.get_host_with_max_cpu()
    minor_vers = self.wf_helper.get_host_cpu_versions(host, cpu_model=cpu_model)
    try:
      for minor_ver in minor_vers:
        STEP("Checking minor version: %s" % minor_ver["name"])
        INFO("=======================")
        INFO("CPU Model: %s" % cpu_model)
        INFO("CPU Model Minor Version: %s" % minor_ver["name"])
        INFO("Minor version uuid: %s" % minor_ver["uuid"])
        INFO("=======================")
        self.wf_helper.configure_cpu_with_minor_version(
          model_id=self.wf_helper.get_cpu_model_uuid(cpu_model),
          minor_id=minor_ver["uuid"],
          retries=kwargs.get("retries", 5),
          delay=kwargs.get("delay", 5)
        )
        STEP("Creating VM with minor version: %s" % minor_ver["name"])
        payload = {
          "api_type": "restv3",
          "guest_os": "rhel90",
          "boot_type": "uefi",
          "add_vnic": True,
          "apc_enabled": True,
          "cpu_minor_version": minor_ver["uuid"],
          "validations": "validate_apc_status, validate_cpu_model_acli"
        }
        self.basic_apc_vm_validations(**payload)
        STEP("Clearing all flags for: %s" % minor_ver["name"])
        DirtyQuotaCluster.restart_acropolis()
        time.sleep(10)
    finally:
      STEP("Clearing all flags for minor version gflags")
      DirtyQuotaCluster.restart_acropolis()
