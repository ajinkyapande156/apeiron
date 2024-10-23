"""
Copyright (c) 2022 Nutanix Inc. All rights reserved.

Author: pritam.chatterjee@nutanix.com
"""
# pylint: disable=import-error, unused-import
import copy
import json
import pprint
import time
import traceback
from datetime import datetime
import uuid

try:
  from framework.lib.nulog import INFO, WARN, DEBUG, ERROR, STEP
except Exception:  # pylint: disable=broad-except
  from libs.ahv.framework.proxy_logging \
    import INFO, WARN, DEBUG, ERROR, STEP
  EXECUTOR = "mjolnir"
from libs.ahv.workflows.gos_qual.lib.base.guest_os_selector_v2 import (
  AutoGosSelector , VirtioGosSelector)
from libs.ahv.workflows.gos_qual.lib.base.\
  guest_os_selector_v2 import UpgradeGosSelector
from libs.ahv.workflows.gos_qual.lib.base.\
  qual_test_selector_v2 import BootVariationTestSelector
from libs.ahv.workflows.gos_qual.lib.base.\
  qual_test_selector_v2 import PxeBootVariationTestSelector
from libs.ahv.workflows.gos_qual.lib.base.\
  qual_test_selector_v2 import DiskBootVariationTestSelector
from libs.ahv.workflows.gos_qual.lib.base.\
  qual_test_selector_v2 import ApcBootVariationTestSelector
from libs.ahv.workflows.gos_qual.lib.base.\
  qual_test_selector_v2 import VirtioTestSelector
from libs.ahv.workflows.gos_qual.lib.base.\
  qual_test_selector_v2 import GuestUpgradeTestSelector
from libs.ahv.workflows.one_click.args_manipulator \
  import ArgsManipulator
from libs.ahv.workflows.gos_qual.lib.base. \
  executors import NutestExecutor
from libs.ahv.workflows.gos_qual.lib.base.\
  prioritize import DefaultPrioritizer
from libs.ahv.workflows.gos_qual.lib.base.utilities \
  import convert_pos_dict_to_list


class GenericGuestQualifierv2():
  """Guest qualification top level class"""
  GOS_SELECTORS = {
    "auto": AutoGosSelector,
    "virtio": VirtioGosSelector,
    "gos_upgrade": UpgradeGosSelector
  }

  TEST_SELECTORS = {
    "auto": BootVariationTestSelector,
    "virtio": VirtioTestSelector,
    "pxe": PxeBootVariationTestSelector,
    "gos_upgrade": GuestUpgradeTestSelector,
    "disk": DiskBootVariationTestSelector,
    "apc": ApcBootVariationTestSelector,
  }

  PRIORITY_SELECTORS = {
    "default": DefaultPrioritizer
  }

  EXECUTORS = {
    "default": NutestExecutor
  }

  def __init__(self,
               cluster=None,
               guest_selection_mode="auto",
               test_selection_mode="auto",
               classifier="Internal",
               executor="default",
               prioritization_mode="default",
               run_id=None,
               **kwargs
              ):
    """
    Create guest os qualification object
    Args:
      guest_selection_mode(str): GOS Selector class name
      test_selection_mode(str): Test Selector class name
      prioritization_mode(str): Prioritize stratergy
      cluster(object): cluster object mjolnir|nutest
      executor(str): Executor class name
      classifier(str): Internal|Official
      run_id(str): run id
    Kwargs:
    Returns:
    """
    self.cluster = cluster
    self.guest_selection_mode = guest_selection_mode
    self.test_selection_mode = test_selection_mode
    self.execution_mode = executor
    self.prioritization_mode = prioritization_mode
    self.guest_plan = None
    self.test_plan = None
    self.exec_priority = None
    self.classifier = classifier
    self.data = None
    self.uuid = run_id or str(uuid.uuid1())

    INFO("Ignoring extra args received: %s" % kwargs)

    # select guest OSes
    self.guest_os_selector = \
      self.GOS_SELECTORS[self.guest_selection_mode]()
    INFO("Initialized Guest OS selection with: %s" % self.guest_os_selector)
    self.qual_test_selector = \
      self.TEST_SELECTORS[self.test_selection_mode]()
    INFO("Initialized Qualification Test selection with: %s"
         % self.guest_os_selector)
    self.priority_selection = \
      self.PRIORITY_SELECTORS[self.prioritization_mode]()
    INFO("Initialized Prioritization with: %s" % self.guest_os_selector)
    self.executor = self.EXECUTORS[self.execution_mode]()
    INFO("Initialized Execution with: %s" % self.guest_os_selector)

  @staticmethod
  def gos_to_oneclick_adapter(execution_plan, platforms=None,
                              ahv_version=None,
                              aos_version=None, **kwargs):
    """
    Transform the execution_plan with one-click acceptable keys
    format
    Args:
      execution_plan(list): list of dicts
      platforms(list): list of platforms
      ahv_version(str): ahv version
      aos_version(str): aos version
    Returns:
      oneclick_dict(dict):
    """
    # execution_plan = convert_list_to_pos_dict(execution_plan)
    INFO("Ignoring extra args received: %s" % kwargs)
    oneclick_dict = {}
    platform_len = 1
    if platforms:
      platform_len = len(platforms)
    for i in range(platform_len):
      oneclick_dict[str(i)] = {}
      for j, entry in enumerate(execution_plan):
        entry["Platform"] = ""
        entry["Jita URL"] = ""
        entry["Result"] = ""
        entry["Status"] = ""
        entry["Reason"] = ""
        entry["Total_Time"] = ""
        entry["Start Time"] = ""
        entry["End Time"] = ""
        entry["Dashboard URL"] = ""
        entry["out_key"] = str(i)
        entry["in_key"] = str(j)
        entry["matrix_type"] = kwargs.get("action") or "guest_os_qual"
        entry["row_id"] = str(uuid.uuid1())
        entry["uuid"] = kwargs.get("run_id") or str(uuid.uuid1())
        entry["aos"] = aos_version
        el_version = ArgsManipulator().get_el_version(ahv_version)
        ahv_str = str(el_version + ".nutanix." + str(ahv_version))
        entry["ahv"] = ahv_str
        if isinstance(platforms, list):
          entry["Platform"] = platforms[i]
        oneclick_dict[str(i)][str(j)] = entry
    return oneclick_dict

  def generate_plan(self, **kwargs):
    """
    Generate matrix for guest OS qualification
    Args:
    Returns:
      test_plan(list): List for dicts
    """
    pp = pprint.PrettyPrinter(indent=4)
    if not kwargs.get("execution_plan"):
      STEP("Getting information about guest operating systems")
      self.guest_plan = self.guest_os_selector.select(**kwargs)
      INFO(pp.pformat(self.guest_plan))
      STEP("Discovering application tests for qualification")
      self.test_plan = self.qual_test_selector.select(guest_plan=
                                                      self.guest_plan,
                                                      **kwargs)
      self.test_plan = self.priority_selection.prioritize(**{"test_plan":
                                                               self.test_plan})
      self._add_metadata()
    else:
      INFO("Received an execution plan, skipping generation")
      if isinstance(kwargs.get("execution_plan"), dict):
        self.test_plan = convert_pos_dict_to_list(kwargs.get("execution_plan"))
      else:
        self.test_plan = kwargs.get("execution_plan")
    INFO(pp.pformat(self.test_plan))
    return self.test_plan

  def execute_plan(self):
    """
    Execute the given guest OS qualification plan
    Args:
    Returns:
    """
    self.executor.execute(self.cluster, self.test_plan)

  def _add_metadata(self):
    """
    Internal method for adding metadata fields for data collection
    Args:
    Returns:
    """
    guest_metadata = {
      "ahv": "Unknown",
      "aos": "Unknown",
      "edition": "NA",
      "upgraded_build": "NA",
      "install_media": "NA",
      "boot_disk": "NA",
      "graphics": "NA",
      "graphics_details": "NA",
      "virtio_driver": "NA",
      "total_runtime": "NA",
      "start_time": "NA",
      "end_time": "NA",
      "status": "NA",
      "qual_date": "NA",
      "classifier": self.classifier,
      "run_id": self.uuid
    }
    test_metadata = {
      "test_runtime": 0,
      "test_start_time": 0,
      "test_end_time": 0,
      "result": "NA",
      "test_data": "NA",
      "exception": "NA"
    }
    for guest in self.test_plan:
      INFO("Adding meta data for guest OS: %s" % guest["os"])
      guest.update(copy.deepcopy(guest_metadata))
      for test in guest["tests"]:
        test.update(copy.deepcopy(test_metadata))
