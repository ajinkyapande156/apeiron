"""
Copyright (c) 2023 Nutanix Inc. All rights reserved.

Author: pritam.chatterjee@nutanix.com
"""
# pylint: disable=unused-argument, unused-import, broad-except, fixme
# pylint: disable=anomalous-backslash-in-string
from __future__ import division
from random import randrange
import uuid
from framework.lib.nulog import INFO, WARN, ERROR
from framework.exceptions.interface_error import NuTestCommandExecutionError
from libs.framework import mjolnir_entities as entities
from libs.framework.mjolnir_executor import use_executor
from libs.feature.dirty_quota import constants as const


class DirtyQuotaCluster:
  """DirtyQuotaVmLog class"""

  @staticmethod
  def toggle_gflag(**kwargs):
    """
    Toggles the current state of the DQ gflag
    Args:
    Returns:
    Raises:
    """
    svm = DirtyQuotaCluster.get_acropolis_leader()
    cluster = entities.ENTITIES.get("pe")
    state = DirtyQuotaCluster.get_gflag_state(svm)
    toggle = state.split("=")[-1]
    if "False" in toggle:
      toggle = "True"
    else:
      toggle = "False"
    INFO("Setting to %s" % toggle)
    cmd = "links http://0:2030/h/gflags?acropolis_kvm_migrate_dirty_quota=%s" \
          % toggle
    for cvm in cluster.svms:
      try:
        cvm.execute(cmd, timeout=10)
      except Exception as ex:
        ERROR(ex)
        WARN("Ignoring the exception for links command..")
    # Not needed as per https://jira.nutanix.com/browse/ENG-580323
    # INFO("Restarting acropolis services")
    # DirtyQuotaCluster.restart_acropolis()
    # INFO("Gflag setting completed")

  @staticmethod
  def get_acropolis_leader():
    """
    Get acropolis master svm
    Args:
    Returns:
    Raises:
    """
    cluster = entities.ENTITIES.get("pe")
    cmd = '/home/nutanix/ncc/panacea/bin/panacea_cli show_leaders | ' \
          'grep acropolis_master | awk "{print \$2}"'
    master_ip = cluster.execute(cmd)["stdout"].split()[-1].strip()
    INFO("Current acropolis master: %s" % master_ip)
    return cluster.get_svm_with_svm_ip(master_ip)

  @staticmethod
  def restart_acropolis(**kwargs):
    """
    Restarts acropolis service on cluster
    Args:
    Returns:
    Raises:
    """
    cluster = entities.ENTITIES.get("pe")
    for cvm in cluster.svms:
      cmd = "genesis stop acropolis"
      out = cvm.execute(cmd)["stdout"]
      INFO("Acropolis status on CVM: %s" % cvm.ip)
      INFO(out)
    INFO("Starting acropolis services")
    for cvm in cluster.svms:
      cmd = "cluster start"
      out = cvm.execute(cmd)["stdout"]
      INFO("Acropolis status on CVM: %s" % cvm.ip)
      INFO(out)
      # Execute only on 1 cvm
      break

  @staticmethod
  @use_executor
  def check_gflag_enabled(**kwargs):
    """
    Check if  DQ gflag is set to True
    Args:
    Returns:
    Raises:
    """
    cluster = entities.ENTITIES.get("pe")
    for svm in cluster.svms:
      state = DirtyQuotaCluster.get_gflag_state(svm)
      INFO("Current State: %s on %s" % (state, svm.ip))
      assert "--acropolis_kvm_migrate_dirty_quota=True" in state, \
        "Dirty Quota is disabled on svm %s" % svm.ip
    INFO("Dirty Quota is enabled")

  @staticmethod
  @use_executor
  def check_gflag_disabled(**kwargs):
    """
    Check if  DQ gflag is set to False
    Args:
    Returns:
    Raises
    """
    cluster = entities.ENTITIES.get("pe")
    for svm in cluster.svms:
      state = DirtyQuotaCluster.get_gflag_state(svm)
      INFO("Current State: %s on %s" % (state, svm.ip))
      assert "--acropolis_kvm_migrate_dirty_quota=False" in state, \
        "Dirty Quota is enabled on svm %s" % svm.ip
    INFO("Dirty Quota is disabled")

  @staticmethod
  def get_gflag_state(svm):
    """
    Method to get the state of DQ gflag.
    Args:
      svm(object):
    Returns:
      state(str):
    """
    cmd = 'links http://0:2030/h/gflags | grep dirty_quota'
    try:
      out = svm.execute(cmd)
    except NuTestCommandExecutionError:
      WARN("NO DIRTY QUOTA FLAG SET ON THE CLUSTER")
      return "--acropolis_kvm_migrate_dirty_quota=False"
    state = out["stdout"].strip()
    return state

  @staticmethod
  def enable_dq_gflag(**kwargs):
    """
    Enable dq gflag on the cluster persistent
    Args:
    Returns:
    """
    cluster = entities.ENTITIES.get("pe")
    if "--acropolis_kvm_migrate_dirty_quota=True" not in \
           DirtyQuotaCluster.get_gflag_state(cluster.svms[0]):
      INFO("Configuring Dirty Quota on the cluster")
      for cvm in cluster.svms:
        cmd = "echo --acropolis_kvm_migrate_dirty_quota=true " \
              ">> %s" % const.DQ_GFLAG_FILE
        INFO("Enabling gflag on cvm: %s" % cvm.ip)
        cvm.execute(cmd)
      DirtyQuotaCluster.restart_acropolis()
      INFO("Configuring Dirty Quota gflag completed")
    INFO("Dirty Quota is already configured on cluster")
