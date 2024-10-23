"""
Copyright (c) 2023 Nutanix Inc. All rights reserved.

Author: pritam.chatterjee@nutanix.com
"""
# pylint: disable=line-too-long,unused-argument,no-self-use,unused-import
# pylint: disable=fixme
import random
import time
from framework.lib.nulog import INFO, WARN, ERROR, STEP
from framework.exceptions.nutest_error import NuTestError
from libs.framework import mjolnir_entities as entities
from libs.feature.dirty_quota.dirty_quota_vm import \
  DirtyQuotaVm
from libs.feature.dirty_quota.dirty_quota_cluster import \
  DirtyQuotaCluster
from workflows.acropolis.upgrade.perform_ahv_aos_upgrade import \
  PerformAhvAosUpgrade


class DirtyQuotaWorkflow:
  """DirtyQuotaWorkflow class"""

  def __init__(self, cluster=None, **kwargs):
    """
    Create object
    Args:
      cluster(object): nutest cluster object
    Returns:
    Raises:
    """
    self.cluster = cluster

  def validate_gflag(self, **kwargs):
    """
    Steps:
      1. Create a VM
      2. Update the gflag for dirty quota to True/False.
      3. Validate by Live migrating the VM
    Kwargs:
    """
    # FIME: Remove this once gflag is enabled by default
    if kwargs.get("set_dq_gflag", False):
      DirtyQuotaCluster.enable_dq_gflag(retries=30, delay=5)
    # perform_lm = kwargs.get("perform_lm", True)
    validations = kwargs.pop("validations", '')
    dq_cluster = DirtyQuotaCluster()
    dq_vm = DirtyQuotaVm(**kwargs)
    for validation in validations.split(","):
      if validation in ['']:
        continue
      validation = validation.strip()
      STEP("Executing: %s" % validation)
      try:
        getattr(dq_cluster, validation)(**kwargs)
      except AttributeError:
        vm_spec = dq_vm.create()
        kwargs["vm_spec"] = vm_spec
        getattr(dq_vm, validation)(**kwargs)
    # if perform_lm:
    #   STEP("Creating a VM to validate the effect on Live Migrations")
    #   dq_vm = DirtyQuotaVm(**kwargs)
    #   vm_spec = dq_vm.create()
    #   kwargs["vm_spec"] = vm_spec

  def validate_lm_with_dirty_quota(self, **kwargs):
    """
    Steps:
      1. Create a VM with required resources.
      2. Power on VM.
      3. Run workloads if mentioned in config.
      4. Do LM
      5.
    Kwargs:
      workload(str): run_fio|run_dirty_harry
    """
    # FIME: Remove this once gflag is enabled by default
    if kwargs.get("set_dq_gflag", False):
      DirtyQuotaCluster.enable_dq_gflag(retries=30, delay=5)
    # workload = kwargs.get("workload", "dirty_harry")
    validations = kwargs.pop("validations", '')
    dq_cluster = DirtyQuotaCluster()
    dq_vm = DirtyQuotaVm(**kwargs)
    vm_spec = dq_vm.create(**kwargs)
    kwargs["vm_spec"] = vm_spec
    # expected_time = dq_vm.predict_lm_time()
    if isinstance(validations, str):
      for validation in validations.split(","):
        if validation in ['']:
          continue
        validation = validation.strip()
        STEP("Executing: %s" % validation)
        try:
          getattr(dq_cluster, validation)(**kwargs)
        except AttributeError:
          getattr(dq_vm, validation)(**kwargs)
    elif isinstance(validations, list):
      kwargs.pop("expected_result")
      for validation in validations:
        STEP("Executing: %s" % validation["name"])
        try:
          getattr(dq_cluster, validation["name"])(
            expected_result=validation.get("expected_result", "Pass"), **kwargs)
        except AttributeError:
          getattr(dq_vm, validation["name"])(
            expected_result=validation.get("expected_result", "Pass"), **kwargs)

  def validate_upgrade(self, **kwargs):
    """
    Steps:
      1. Create a VM with required resources.
      2. Power on VM.
      3. Run workloads if mentioned in config.
      4. Do LM
      5. Validate the workloads are running.
      6. Perform upgrade
      7. Validate the workloads are running on the VM after upgrade
    Kwargs:
      workload(str): run_fio|run_dirty_harry
    """
    self.upgrade_handler = entities.ENTITIES.get("upgrade_handler")(
      test_args=kwargs)
    upgrade_type = kwargs.get("upgrade_type", "rel_to_rel")

    STEP("Reimaging cluster to source AHV and AOS if required")
    self.upgrade_handler.image_cluster()

    STEP("Performing Pre upgrade steps")
    params = {
      "num_of_vcpus": 8,
      "memory_size": 32,
      "transfer_rate": 2048,
      "dirty_rate": 1024,
      "active_working_set": 1024,
      "vm_name": "Dirty_Quota_Vm_Pre_Upgrade",
      "workload": "harry",
      "set_dq_gflag": False,
      "validate_dirty_quota": False,
      "validations": "check_gflag_disabled, "
                     "start_workload, "
                     "live_migrate, "
                     "get_workload_status"
    }
    if upgrade_type == "rel_to_future":
      # FIXME: Remove the dq gflag set after enabled by default
      params["validate_dirty_quota"] = True
      params["set_dq_gflag"] = False
      params["validations"] = "check_gflag_enabled, start_workload, " \
                              "live_migrate, get_workload_status"
    self.validate_lm_with_dirty_quota(**params)

    STEP("Performing Upgrade Now")
    self.upgrade_handler.trigger_upgrade()

    # if upgrade_type == "rel_to_future":
    #   STEP("Dirty Quota gflag will not be enabled here")
    # else:
    #   # FIXME: Remove the dq gflag set after enabled by default
    #   STEP("Enabling Dirty Quota gflag..STEP TO BE REMOVED AFTER VALIDATION")
    #   DirtyQuotaCluster.enable_dq_gflag(retries=30, delay=5)

    STEP("Performing Post upgrade validations")
    params = {
      "num_of_vcpus": 8,
      "memory_size": 32,
      "transfer_rate": 256,
      "dirty_rate": 1024,
      "active_working_set": 28672,
      "workload": "harry",
      "discover": True,
      "vm_name": "Dirty_Quota_Vm_Pre_Upgrade",
      "validate_dirty_quota": True,
      "validations": "check_gflag_enabled, "
                     "live_migrate, "
                     "get_workload_status"
    }
    self.validate_lm_with_dirty_quota(**params)
