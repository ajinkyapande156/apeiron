"""
Copyright (c) 2022 Nutanix Inc. All rights reserved.

Author: pritam.chatterjee@nutanix.com
"""
# pylint: disable=import-error, unused-import
# pylint: disable=ungrouped-imports
import copy
import pprint
import time
import traceback
from datetime import datetime
import uuid

try:
  from framework.lib.nulog import INFO, WARN, DEBUG, ERROR, \
    STEP
  EXECUTOR = "nutest"
except Exception:  # pylint: disable=broad-except
  from libs.ahv.framework.proxy_logging \
    import INFO, WARN, DEBUG, ERROR, STEP
  EXECUTOR = "mjolnir"
from libs.ahv.workflows.gos_qual.lib.base.\
  guest_os_selector import DefaultGosSelector
from libs.ahv.workflows.gos_qual.lib.base.\
  guest_os_selector import AutoGosSelector
from libs.ahv.workflows.gos_qual.lib.base.\
  guest_os_selector import VirtioGosSelector
from libs.ahv.workflows.gos_qual.lib.base.\
  qual_test_selector import DefaultTestSelector
from libs.ahv.workflows.gos_qual.lib.base.\
  qual_test_selector import BootVariationTestSelector
from libs.ahv.workflows.gos_qual.lib.base.\
  qual_test_selector import VirtioTestSelector
from libs.ahv.workflows.gos_qual.lib.base.\
  prioritize import DefaultPrioritizer
from libs.ahv.workflows.gos_qual.lib.base.\
  utilities import get_os_instance
from libs.ahv.workflows.gos_qual.lib.base.\
  elk_rest_client import ElkRestClient
from libs.ahv.workflows.gos_qual.lib.base.\
  gos_errors import TestNotSupported
from framework.entities.vm.vm import Vm
from framework.entities.network.network import Network
from framework.entities.snapshot.snapshot import Snapshot
from framework.entities.container.container import Container
from workflows.acropolis.ahv.acro_image_utility import AcroImageUtil
from workflows.acropolis.ahv.acro_gos_utility import AcroGOSUtil
from workflows.acropolis.ahv.acro_gos_utility import AcroGOSUtilv2


class GenericGuestQualifier(object):
  """Guest qualification top level class"""
  GOS_SELECTORS = {
    "auto": AutoGosSelector,
    "manual": DefaultGosSelector,
    "virtio_qual": VirtioGosSelector
  }

  QUAL_TEST_SELECTORS = {
    "auto": DefaultTestSelector,
    "with_boot_variations": BootVariationTestSelector,
    "virtio_qual": VirtioTestSelector
  }

  def __init__(self,
               cluster,
               guest_os=None,
               guest_selection_mode="manual",
               qual_tests=None,
               test_selection_mode="auto",
               executor=None,
               reporter=None,
               classifier="Internal",
               elk_db_name="gos_qualification",
               **kwargs):
    """
    Create guest os qualification object
    Args:
      guest_os(str|list): single or multiple guests
      guest_selection_mode(str): Selector class name
      qual_tests(dict): tests details
      test_selection_mode(str): Selector class name
      cluster(object): cluster object mjolnir|nutest
      executor(str): Executor class name
      reporter(str): Reporter class name
      classifier(str): Internal|Official
      elk_db_name(str): Elastic search DB name. DB needs to be precreated
    """
    self.cluster = cluster
    self.guest_os = guest_os
    self.guest_selection_mode = guest_selection_mode
    self.qual_tests = qual_tests
    self.test_selection_mode = test_selection_mode
    self.executor = executor
    self.reporter = reporter
    self.prioritizer = DefaultPrioritizer()
    self.guest_plan = None
    self.test_plan = None
    self.exec_priority = None
    self.classifier = classifier
    self.data = None
    self.elk_db_name = elk_db_name
    self.db_conn = ElkRestClient()
    self.params = kwargs

    # select guest OSes
    self.guest_os_selector = \
      self.GOS_SELECTORS[self.guest_selection_mode]()
    self.qual_test_selector = \
      self.QUAL_TEST_SELECTORS[self.test_selection_mode]()

  def plan(self):
    """
    Generates the guest operating system qualification plan
    Args:
    Returns:
    """
    pp = pprint.PrettyPrinter(indent=4)
    INFO("Getting information about guest operating systems")
    self.guest_plan = self.guest_os_selector.select(guest_os=self.guest_os,
                                                    **self.params)
    INFO(pp.pformat(self.guest_plan))
    # NOTE: Add parallel call for test selections
    INFO("Preparing test plan")
    self.test_plan = \
      self.qual_test_selector.select(guest_plan=
                                     copy.deepcopy(self.guest_plan),
                                     **self.params)
    INFO(pp.pformat(self.test_plan))
    INFO("Prioritizing test plan")
    self.exec_priority = \
      self.prioritizer.prioritize(test_plan=copy.deepcopy(self.test_plan))
    INFO("Enabling data collection and reporting")
    self.data_collector()
    INFO(pp.pformat(self.test_plan))

  def data_collector(self):
    """
    Enabled data collection
    Args:
    Returns:
    """
    run_id = uuid.uuid1()
    for guest in self.exec_priority:
      self.test_plan[guest]["classifier"] = self.classifier
      self.test_plan[guest]["edition"] = "NA"  # updated by boot test post-ops
      self.test_plan[guest]["build"] = "NA"  # updated by boot test post-ops
      self.test_plan[guest][
        "upgraded_build"] = "NA"  # updated by upgrade test post-ops
      self.test_plan[guest]["boot"] = guest[-1]
      self.test_plan[guest]["boot_disk"] = "NA"  # updated by boot test post-ops
      self.test_plan[guest][
        "graphics"] = "NA"  # to be updated by boot test post-ops
      self.test_plan[guest][
        "graphics_details"] = "NA"  # to be updated by gpu test pre-ops
      self.test_plan[guest]["install_media"] = "NA"  # updated by boot test
      self.test_plan[guest]["total_runtime"] = 0
      self.test_plan[guest]["virtio_driver"] = "NA"  # updated by boot post ops
      self.test_plan[guest]["guest_start_time"] = None
      self.test_plan[guest]["guest_end_time"] = None
      self.test_plan[guest]["run_id"] = run_id
      self.test_plan[guest]["ahv"] = "Unknown"
      self.test_plan[guest]["aos"] = "Unknown"
      self.test_plan[guest]["status"] = "NA"
      self.test_plan[guest]["qual_date"] = "NA"

      for test in self.test_plan[guest]["tests"]:
        test["test_runtime"] = 0
        test["test_start_time"] = None
        test["test_end_time"] = None
        test["result"] = None
        test["exception"] = "NA"
        test["test_data"] = "NA"

  def execute(self):
    """
    Executes the GOS qualification plan
    Args:
    Returns:
    """
    # pp = pprint.PrettyPrinter(indent=4)
    for _, guest in enumerate(self.exec_priority):
      guest_result = "QUALIFIED"
      self.test_plan[guest]["guest_start_time"] = time.time()
      self.test_plan[guest]["vm_name"] = "_".join(guest)
      if guest[0].startswith("win"):
        self.test_plan[guest]["os_type"] = "windows"
      else:
        self.test_plan[guest]["os_type"] = "linux"
      # NOTE: watch for any corruption in dict during parallel exec
      #       modules will be shared for all the tests for a guest OS
      aos = self.cluster.info()["version"]
      ahv = self.cluster.hypervisors[0].hypervisor_version
      self.test_plan[guest]["aos"] = aos
      self.test_plan[guest]["ahv"] = ahv.full_version
      modules = {
        "rest_vm": Vm(self.cluster, "REST"),
        "acli_vm": Vm(self.cluster, "ACLI"),
        "rest_image": AcroImageUtil(self.cluster),
        "rest_ctr": Container.list(self.cluster)[0],
        "rest_nw": Network(self.cluster, "REST"),
        "rpc_cls_v1": AcroGOSUtil,  # handles gos connection thru ip
        "rpc_cls_v2": AcroGOSUtilv2,  # handles gos connection thru Vm object
        "rpc": None,  # This is updated by the boot tests
        "rest_snapshot": Snapshot(self.cluster, "REST")
      }
      STEP("Started qualification for operating system: %s"
           % self.test_plan[guest]["vm_name"])
      for j, test in enumerate(self.test_plan[guest]["tests"]):
        self.test_plan[guest]["modules"] = modules
        self.test_plan[guest]["modules"]["ssh"] = \
          get_os_instance(guest[0])(
            conn_provider=self.test_plan[guest]["modules"]["rest_vm"]
          )
        try:
          test["test_start_time"] = time.time()
          test["instance"]. \
            execute_pre_operations(test["pre_ops"],
                                   extra_params=self.test_plan[guest],
                                   **test["params"])
          test["instance"].run(extra_params=self.test_plan[guest],
                               **test["params"])
          test["instance"]. \
            execute_post_operations(test["post_ops"],
                                    extra_params=self.test_plan[guest],
                                    **test["params"])
          # if not j == 0:
          #   test["instance"].teardown(extra_params=self.test_plan[guest],
          #                             **test["params"])
          test["result"] = "PASS"
        except TestNotSupported:
          WARN(traceback.format_exc())
          test["result"] = "NOT SUPPORTED"
          test["exception"] = traceback.format_exc()
        except Exception:  # pylint: disable=broad-except
          ERROR(traceback.format_exc())
          test["result"] = "FAIL"
          test["exception"] = traceback.format_exc()
          guest_result = "FAIL"
          # test["instance"].teardown(extra_params=self.test_plan[guest],
          #                           **test["params"])
          if j == 0:
            break
        finally:
          test["test_end_time"] = time.time()
          test["test_runtime"] = test["test_end_time"] - \
                                 test["test_start_time"]
      self.test_plan[guest]["guest_end_time"] = time.time()
      self.test_plan[guest]["total_runtime"] = \
        self.test_plan[guest]["guest_end_time"] - \
        self.test_plan[guest]["guest_start_time"]

      self.test_plan[guest]["status"] = guest_result
      self.test_plan[guest]["qual_date"] = datetime.now().strftime(
        "%d/%m/%Y %H:%M:%S")
      self._update_result(self.test_plan[guest])

  def _update_result(self, data):
    """
    Internal method to ingest data
    Args:
      data(dict): data to be inserted
    Returns:
    """

    # NOTE: Move this to elk client
    def _sanitize(data):
      """
      Internal method to prepare data for ingest
      Args:
        data(dict): data to be inserted
      Returns:
      NOTE: Make this generic
      """
      new_mods = dict()
      # sanitize the modules data.
      data["run_id"] = str(data["run_id"])
      for test in data["tests"]:
        if not isinstance(test["exception"], str):
          test["exception"] = str(test["exception"])
      for module in data["modules"]:
        new_mods[module] = str(data["modules"][module])
      data["modules"] = new_mods

      new_tests = list()
      # sanitize the tests data.
      for test in data["tests"]:
        tmp = test
        tmp["instance"] = str(tmp["instance"])
        new_tests.append(tmp)
      data["tests"] = new_tests

      return data

    new_data = _sanitize(data)
    pp = pprint.PrettyPrinter(indent=4)
    INFO(pp.pformat(new_data))
    self.db_conn.ingest_json_data(new_data,
                                  db_name=self.elk_db_name)
