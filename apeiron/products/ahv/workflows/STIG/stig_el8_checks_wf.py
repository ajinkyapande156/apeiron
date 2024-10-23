
"""
Copyright (c) 2022 Nutanix Inc. All rights reserved.
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
from libs.feature.STIG.stig_checks import StigCheck

class STIG_el8_wf():
  """
  Class for STIG check workflow
  """
  def __init__(self, cluster):
    """
    Initialize workflow object
    Args:
        cluster(object): Nutest cluster object
    """
    self.cluster = cluster
    self.stig_wf = StigCheck(self.cluster)
    self.results = {}
    self.pretty_table = PrettyTable(["Check_name", "Status", "Exception"])
    self.stig_wf._make_scanner_happy()

  def el8_stig_validation(self, **kwargs):
    """
    Generic function to handle file related operations
    Depending on operation name, carries out tests
    If 'all' every stig is checked but otherwise specific check is run
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
      INFO("Here's the list of all STIG checks:%s"%stig_checks)
      INFO(self.results)
      self.result_tabulation(self.results)
      return
    #below instruction is for standlone validation
    self.run_check(check, **kwargs)
    self.result_tabulation(self.results)

  def run_check(self, attribute, **kwargs):
    """
    Runner script to execute the stig check based on the
    attribute which is a callable function from STIG_checks.py

    Args:
      attribute (str): Callable function
      kwargs (json): Json with func args
    Raises:
      Exception
    """
    try:
      func_invoke = getattr(self.stig_wf, attribute)
      func_invoke()
      self.results[attribute] = {"status": "PASS"}
    except Exception as err:
      self.results[attribute] = {"status": "FAIL", "reason": err}

  def result_tabulation(self, results):
    """
    This function receives results in the form of json and tabulation
    of results is done here and printed.
    Also if there is any failed checks then it is raised here.
    Args:
      results (json): json from stick check runner
    Raises:
      Exception: if any of the check has failed
    """
    red_flag = False
    INFO("Number of checks run are - %s"%results.items())
    INFO("Here's the list of passed STIG checks")
    for attribute, result in results.items():
      if result['status'] == 'PASS':
        self.pretty_table.add_row([attribute, result['status'], "NA"])
    WARN("Here's the list of failed STIG checks")
    failed_count = 0
    for attribute, result in results.items():
      if result['status'] == 'FAIL':
        red_flag = True
        failed_count += 1
        reason = '\n'.join(textwrap.wrap(str(result['reason']), width=100))
        INFO(result)
        self.pretty_table.add_row([attribute, result['status'], reason])
    INFO(self.pretty_table) # displaying check results
    if red_flag:
      raise Exception("%s checks failed of %s checks run!, overall Status: %s"\
                      %(failed_count, len(results.items()), results.items()))
