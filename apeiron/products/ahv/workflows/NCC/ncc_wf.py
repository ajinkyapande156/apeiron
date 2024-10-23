"""
Copyright (c) 2024 Nutanix Inc. All rights reserved.
Author: umashankar.vd@nutanix.com
Dodin Phase4
"""
# pylint: disable=unused-variable, unused-import, no-member
# pylint: disable=invalid-name, broad-except, unused-argument

import time
import textwrap
from prettytable import PrettyTable
from framework.lib.nulog import INFO, WARN, ERROR, \
  STEP
from libs.framework import mjolnir_entities as entities
from libs.feature.NCC.ncc_checks import NccCheck

class NCC_wf():
  """
  Class for NCC check workflow
  """
  def __init__(self, cluster):
    """
    Initialize workflow object
    Args:
        cluster(object): Nutest cluster object
    """
    self.cluster = cluster
    self.results = {}
    self.NCC_wf = NccCheck(self.cluster)

  def Ncc_Validation(self, **kwargs):
    """
    Generic function to handle NCC checks
    Depending on operation name, carries out tests
    If 'all' every hypervisor check is run but otherwise specific check is run
    Args:
      kwargs
    Returns:
      Nothing
    """
    check = kwargs.get("check_name", "all")
    if check == "all":
      stig_checks = []
      all_attributes = dir(self.stig_wf)
      for attribute in all_attributes:
        if "check_" in attribute:
          stig_checks.append(attribute)
          self.run_check(attribute, **kwargs)
      INFO("Here's the list of all NCC checks:%s"%stig_checks)
      INFO(self.results)
      self.result_tabulation(self.results)
      return
    #below instruction is for standlone validation
    self.run_check(check, **kwargs)

  def run_check(self, attribute, **kwargs):
    """
    Runner script to execute the NCC checks based on the
    attribute which is a callable function from STIG_checks.py

    Args:
      attribute (str): Callable function
      kwargs (json): Json with func args
    Raises:
      Exception
    """
    func_invoke = getattr(self.NCC_wf, attribute)
    func_invoke()
