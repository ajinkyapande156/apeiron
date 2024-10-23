"""
Copyright (c) 2022 Nutanix Inc. All rights reserved.

Author: sonny.li@nutanix.com

Description:
inject error or correct error for CVM (qemu)
"""
# pylint: disable=broad-except, unexpected-keyword-arg, unused-import
# pylint: disable=no-self-use, inconsistent-return-statements, no-else-return
# pylint: disable=unused-argument

import json
import time

from framework.exceptions.entity_error import NuTestError
from framework.lib.nulog import INFO, ERROR
# from framework.lib.utils import wait_for_response
from libs.framework import mjolnir_entities as entities
from libs.framework.mjolnir_executor import use_executor


class ErrorCvm():
  """
  for cvm error related functions
  """
  def __init__(self):
    """Instance initiator
    Args:
    Returns:
    """
    self.cluster = entities.ENTITIES.get("pe")

  def wait_for_all_cvms_out_of_mm(self, **kwargs):
    """
    Wait for all cvm are out of Maintenance mode
    Returns:
      None
    """
    INFO("Wait for all CVMs are out of Maintenance mode")
    retries = kwargs.get("retries", 25)
    delay = kwargs.get("delay", 30)
    for cvm in self.cluster.svms:
      self.is_cvm_in_mm(cvm, retries=retries, delay=delay)
      # wait_for_response(lambda mycvm=cvm: self.is_cvm_in_mm(mycvm),
      #                   expected=False, timeout=600, interval=30)

  def get_ncli_host_ls_reliably(self, active_cvm, num_retry=3):
    """
    Get reliably 'ncli host ls --json true' for some rebooted cvm
    This is to handle ENG-471565, prism gate not up or others
    Args:
      active_cvm(obj): cvm object to run that command
      num_retry(int): number of times to retry
    Returns:
      output(str): json string of output of 'ncli host ls --json true'
    Raises:
      NuTestError(Exception)
    """
    for retrynum in range(num_retry):
      try:
        ret = active_cvm.execute('ncli host ls --json true', timeout=180)
        return ret
      except Exception as err:
        # may hit ENG-471565
        INFO("retrynum: %s, Hit error: %s" % (retrynum, str(err)))
        time.sleep(120)

    raise NuTestError("After retry: %s, CVM %s failed to run "
                      "'ncli host ls --json true'"
                      % (num_retry, active_cvm.ip))

  @use_executor
  def is_cvm_in_mm(self, cvm, **kwargs):
    """
    Check if cvm is in maintenance mode
    Args:
      cvm(obj): target cvm object to work on it (put into or out MM, etc.)
    Returns:
      bool: True: cvm is in MM, False: cvm is NOT in MM
    """
    active_cvm = self.get_active_cvm(cvm)
    ret = self.get_ncli_host_ls_reliably(active_cvm)
    for data in json.loads(ret['stdout'])['data']:
      if str(data['serviceVMExternalIP']) == cvm.ip:
        # if cvm is NOT put in maintenance mode for once,
        # no field "hostInMaintenanceMode" in data dictionary
        # this is for ENG-471532
        if 'hostInMaintenanceMode' in data and data['hostInMaintenanceMode']:
          INFO("CVM: %s in Maintenance mode" % cvm.ip)
          return True
        else:
          INFO("CVM: %s is NOT in Maintenance mode" % cvm.ip)
          return False

  def get_active_cvm(self, cvm):
    """
    Get active_cvm: cvm to run command, must be online and not target cvm
    Args:
      cvm(obj): target cvm object to work on it (put into or out MM, etc.)
    Returns:
      active_cvm(obj)
    """
    for svm in self.cluster.svms:
      if svm.ip != cvm.ip and svm.is_on() and svm.is_accessible():
        return svm
