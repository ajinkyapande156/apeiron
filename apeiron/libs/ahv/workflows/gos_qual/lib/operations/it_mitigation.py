"""
Copyright (c) 2022 Nutanix Inc. All rights reserved.

Author: arundhathi.a@nutanix.com
"""
# pylint: disable=unused-import
import time
from framework.lib.utils.version import Version
from framework.lib.release_version_helper import NOSVersion
try:
  from framework.lib.nulog import INFO, ERROR, WARN, \
    DEBUG  # pylint: disable=unused-import
  EXECUTOR = "nutest"
except Exception:  # pylint: disable=broad-except
  from libs.ahv.framework.proxy_logging \
    import INFO, ERROR, WARN, DEBUG  # pylint: disable=unused-import
  EXECUTOR = "mjolnir"


ENABLED = "ENABLED"
DISABLED = "DISABLED"
Y = "Y"
N = "N"
ITMITIGATON_ENABLED = "Enable iTLB Multihit M... : true"
ITMITIGATON_DISABLED = "Enable iTLB Multihit M... : false"
MIN_VERSION = "6.5.1.8"
MASTER = "master"

class ItMitigationStateCheck(object):
  """
  Class to check itlb-multihit-mitigation state
  """
  def __init__(self, cluster):
    """
    Constructor method

    Args:
      cluster(obj): cluster object
    """
    self.cluster = cluster

  def get_default_state_for_aos_version(self):
    """
    Fetch the default expected state of itlb-multihit-mitigation
    Args:
    Returns:
    """
    aos_version = NOSVersion(self.cluster.svms[0]).nos_version
    INFO("AOS Version: %s" % aos_version)
    if Version(aos_version) >= Version(MIN_VERSION) \
        or aos_version == MASTER:
      INFO("Expected state of itlb-multihit-mitigation: %s" % DISABLED)
      return DISABLED
    else:
      INFO("Expected state of itlb-multihit-mitigation: %s" % ENABLED)
      return ENABLED

  def get_it_mitigation_status(self):
    """
    Get status of itlb-multihit-mitigation
    Args:
    Returns:

    """
    cmd = "cat /sys/module/kvm/parameters/nx_huge_pages"
    res = list()
    INFO("Fetch current state of itlb-multihit-mitigation from host")
    for host in self.cluster.hypervisors:
      result = host.execute(cmd)
      INFO(result)
      if result["status"] == 0:
        res.append(result["stdout"].strip())
      else:
        raise "CMD execution failed: %s" % cmd
    INFO(res)
    return res

  def validate_it_mitigation(self, state=DISABLED):
    """
    Validate itlb-multihit-mitigation status based on AOS version

    Args:
      state(str): exepected state of it mitigation

    Returns:
      None
    """
    end_time = time.time() + 60
    while time.time() < end_time:
      try:
        out = self.get_it_mitigation_status()
        if len(set(out)) == 1:
          if state == ENABLED:
            assert Y in out, "Some hosts have it mitigation disabled"
          elif state == DISABLED:
            assert N in out, "Some hosts have it mitigation enabled"
          break
        else:
          raise "Some hosts have it mitigation enabled/disabled"
      except Exception: # pylint: disable=broad-except
        INFO("Retrying..")
        if time.time() > end_time:
          raise "Timeout: Some hosts have it mitigation enabled/disabled"


  def enable_it_mitigation(self):
    """
    Enable itlb-multihit-mitigation
    Args:
    Returns:
    """
    cmd = "ncli cluster edit-hypervisor-security-params " \
          "enable-itlb-multihit-mitigation=true"
    result = self.cluster.execute(cmd)
    assert result["status"] == 0, "Cmd execution failed"
    INFO(result["stdout"])
    if ITMITIGATON_ENABLED in result["stdout"]:
      INFO("enable-itlb-multihit-mitigation set to true")

  def disable_it_mitigation(self):
    """
    Disable itlb-multihit-mitigation
    Args:
    Returns:
    """
    cmd = "ncli cluster edit-hypervisor-security-params " \
          "enable-itlb-multihit-mitigation=false"
    result = self.cluster.execute(cmd)
    assert result["status"] == 0, "Cmd execution failed"
    INFO(result["stdout"])
    if ITMITIGATON_DISABLED in result["stdout"]:
      INFO("enable-itlb-multihit-mitigation set to false")


  def check_it_mitigation_is_applicable(self):
    """
    Check status if itlb-multihit-mitigation is applicable for this host
    Args:
    Returns:

    """
    cmd = "cat /sys/devices/system/cpu/vulnerabilities/itlb_multihit"
    res = list()
    INFO("Check if itlb-multihit-mitigation is applicable")
    for host in self.cluster.hypervisors:
      result = host.execute(cmd)
      INFO(result)
      if result["status"] == 0:
        res.append(result["stdout"].strip())
      else:
        raise "CMD execution failed: %s" % cmd
    INFO(res)
    return res
