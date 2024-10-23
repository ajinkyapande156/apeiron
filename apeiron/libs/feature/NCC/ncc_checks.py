
"""
Copyright (c) 2024 Nutanix Inc. All rights reserved.
Author: umashankar.vd@nutanix.com
Dodin phase specific library
"""
#pylint: disable=unused-import, too-many-public-methods, useless-return
#pylint: disable=too-many-lines, bare-except, anomalous-backslash-in-string
#pylint: disable=line-too-long, unused-argument
#pylint: disable=broad-except
#pylint: disable=no-else-raise

import re
import time
import json
import framework.operating_systems.operating_system.linux_operating_system \
  as LinuxOperatingSystem
import workflows.acropolis.ahv.acro_host_helper as AcroHostHelper
try:
  from framework.lib.nulog import INFO, WARN, ERROR, \
    STEP
  EXECUTOR = "nutest"
except Exception:  # pylint: disable=broad-except
  from libs.ahv.framework.proxy_logging \
    import INFO, ERROR, STEP
  EXECUTOR = "mjolnir"
from libs.framework import mjolnir_entities as entities

class NccCheck():
  """
  This is stig check class and has functions for various stig compliance checks
  named check_<jiraticket>
  each check will establish ssh connection to host via either pxssh or
  leverage execute command attribute and run the command, validate
  and return pass if criteria is met otherwise raise exception
  """
  def __init__(self, cluster, **kwargs):
    """
    Initialize object
    Args:
        cluster(object): Nutest cluster object
    """
    self.cluster = cluster
    self.co_ip = AcroHostHelper.get_co_hosts(self.cluster)

  def ncc_default_password(self, default=True):
    """
    Args:
      Nothing
      default (boolean): This can be True/False
    Raises:
      Exception
    """
    alert_status = False
    STEP("NCC check for default password check")
    cmd = "ncc health_checks system_checks default_password_check"
    response = self.cluster.execute(cmd)
    INFO("here's what the check returned : %s" %response)
    pattern = "Please update the default password(s) on the AHV host(s) with IP: {} for user(s): root to harden the".format(self.co_ip[0].ip)
    #checking if matched
    if pattern in response['stdout']:
      INFO("Alert is returned")
      alert_status = True
    #checking status flag based on need
    if default:
      INFO("Expecting alerts as default password is in use")
      assert alert_status, "Expected alert not seen"
      INFO("Check returned fail alert as expected")
    else:
      INFO("Expecting no alert as non-default password is set")
      assert not alert_status, "Alert was seen though non default password is set"
      INFO("As expected alert was not seen")
