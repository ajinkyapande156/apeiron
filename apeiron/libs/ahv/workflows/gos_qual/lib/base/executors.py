"""
Copyright (c) 2022 Nutanix Inc. All rights reserved.

Author: pritam.chatterjee@nutanix.com
"""
# pylint: disable=import-error, unused-import, ungrouped-imports, fixme
# pylint: disable=too-many-statements, too-many-branches, no-self-use
# pylint: disable=no-else-return, fixme, useless-import-alias
# pylint: disable=self-cls-assignment, wrong-import-order
# pylint: disable=wrong-import-order, self-cls-assignment, no-else-return
# pylint: disable=useless-import-alias
import copy
import importlib
import inspect
import time
import traceback
from datetime import datetime
from threading import Lock
from threading import RLock
from functools import partial

from libs.ahv.workflows.gos_qual.lib import tests  # pylint: disable=import-error
from libs.ahv.workflows.gos_qual.lib.base.utilities \
  import get_module_classes  # pylint: disable=import-error
from libs.ahv.workflows.gos_qual.lib.base.abstracts \
  import AbstractTest  # pylint: disable=import-error
from libs.ahv.workflows.gos_qual.lib.base.utilities \
  import get_os_instance
from libs.ahv.workflows.gos_qual.lib.base.\
  elk_rest_client import ElkRestClient
from libs.ahv.workflows.gos_qual.lib.base.gos_errors \
  import TestNotSupported
from libs.ahv.workflows.one_click.task_manager.\
  task_manager import TaskManager
from framework.interfaces.acli import ACLI
from framework.entities.vm.vm import Vm
from framework.entities.network.network import Network
from framework.entities.snapshot.snapshot import Snapshot
from framework.entities.container.container import Container
from framework.exceptions.nutest_error import NuTestError
from workflows.acropolis.ahv.acro_image_utility import AcroImageUtil
from workflows.acropolis.ahv.acro_gos_utility import AcroGOSUtil
from workflows.acropolis.ahv.acro_gos_utility import AcroGOSUtilv2
from libs.ahv.workflows.one_click import get_batch_size
from libs.ahv.workflows.gos_qual.configs \
  import constants as constants


try:
  from framework.lib.nulog import INFO, WARN, DEBUG, ERROR, STEP
  EXECUTOR = "nutest"
except Exception:  # pylint: disable=broad-except
  from libs.ahv.framework.proxy_logging \
    import INFO, WARN, DEBUG, ERROR, STEP
  EXECUTOR = "mjolnir"



class AbstractExecutor():
  """AbstractExecutor class"""
  def execute(self, cluster, plan):
    """
    Execute the provided GOS plan
    Args:
      cluster(object): nutest cluster object
      plan(list): List of dicts
    Returns:
    Raises:
    """
    raise NotImplementedError


class NutestExecutor(AbstractExecutor):
  """NutestExecutor class"""
  def __init__(self):
    """
    Create NutestExecutor class
    """
    self.db_conn = ElkRestClient()
    self._gos_qual_lock = RLock()
    self._img_upl_lock = Lock()

  def execute(self, cluster, plan):
    """
    Execute the provided GOS plan
    Args:
      cluster(object): nutest cluster object
      plan(list): List of dicts
    Returns:
    Raises:
      NutestError
    """
    self.failure_detected = []
    gos_qual_workers = self._get_workers(cluster, plan)
    INFO("Number of guest OS to be qualified concurrently: %s"
         % gos_qual_workers)
    quotas = {
      "gos_qual_slave": {
        "num_workers": gos_qual_workers
      }
    }
    gos_qual_task_manager = TaskManager(
      quotas=quotas,
      worker_poolsize=gos_qual_workers,
      timeout=96000000
    )
    guests_plan = copy.deepcopy(plan)
    while True:
      with self._gos_qual_lock:
        guest = guests_plan.pop()
        gos_qual_task_manager.add(self._execute,
                                  cluster=cluster,
                                  guest=guest,
                                  quota_type="gos_qual_slave")
        if not guests_plan:
          gos_qual_task_manager.complete_run(timeout=7200000)
          INFO("Not in-flight or pending qualification, exiting")
          break
    # If any guest has failed qualification, raise NutestException
    # to fail
    if self.failure_detected:
      raise NuTestError("Qualification failed for : %s" % self.failure_detected)

  def _get_workers(self, cluster, plan):
    """
    Internal method to decide on the worker threads
    Args:
      cluster(object):
       plan(list):
    Returns:
      num_workers(int):
    """
    # if nested cluster just run one test at a time
    if "nested" in cluster.name:
      num_workers = 2
      return num_workers
    for each_plan in plan:
      if "pxe" in each_plan.get("classifier"):
        INFO("Detect pxe based guest OS installation")
        num_workers = 1
        return num_workers
      elif "one-click" in each_plan.get("classifier"):
        INFO("Detect one-click based execution")
        num_workers = len(plan)
        return num_workers
      else:
        num_workers = get_batch_size.get_batch_size(
          clusters=[cluster.name]
        )
        return num_workers

  def _execute(self, cluster, guest):
    """
    Execute the provided GOS plan
    Args:
      cluster(object): nutest cluster object
      guest(dict): Guest info
    Returns:
    Raises:
      NutestError
    """
    INFO("Loading all available tests")
    available_tests = self._load_tests()
    guest["bits"] = str(guest["bits"])  # safeguard against JITA convertion
    guest_result = "Succeeded"
    STEP("Starting qualification for guest OS: %s arch: %s"
         " bits: %s boot_type: %s" % (guest["os"], guest["arch"],
                                      guest["bits"], guest["boot"]))
    guest["start_time"] = time.time()
    if not guest.get("vm_name"):
      guest["vm_name"] = "_".join([guest["os"],
                                   guest["type"],
                                   guest["arch"],
                                   guest["bits"],
                                   guest["boot"]])
    if guest["os"].startswith("win"):
      guest["os_type"] = "windows"
    else:
      guest["os_type"] = "linux"
    guest["aos"] = cluster.info()["version"]
    guest["ahv"] = cluster.hypervisors[0].hypervisor_version.full_version
    INFO("Loading modules for Nutest Executor")
    guest["modules"] = {
      "rest_vm": partial(proxyfunc, "rest_vm", Vm, cluster=cluster),  #partial
      "pxe_vm": partial(proxyfunc, "pxe_vm", Vm, cluster=cluster),
      "wds_vm": partial(proxyfunc, "wds_vm", Vm, cluster=cluster),
      "acli_vm": partial(proxyfunc, "acli_vm", Vm, cluster=cluster),
      "acli": partial(proxyfunc, "acli", ACLI, cluster=cluster),
      "rest_image": partial(proxyfunc, "rest_image", AcroImageUtil,
                            cluster=cluster),
      # fixme Change this to routable later if required
      "rest_ctr": Container.list(cluster)[0],
      "rest_nw": partial(proxyfunc, "rest_nw", Network, cluster=cluster),
      "rpc_cls_v1": AcroGOSUtil,  # handles gos connection thru ip
      "rpc_cls_v2": AcroGOSUtilv2,  # handles gos connection thru Vm object
      "rpc": None,  # This is updated by the boot tests
      "rest_snapshot": partial(proxyfunc, "rest_snapshot",
                               Snapshot, cluster=cluster),
      "cache": BaseRoutables,
      "img_upload_lock": self._img_upl_lock
    }
    for test in guest["tests"]:
      guest["modules"]["ssh"] = get_os_instance(guest["os"])(
        conn_provider=guest["modules"]["rest_vm"]
      )
      # NOTE: safeguard against jita conversions
      test["instance"] = copy.deepcopy(available_tests[test["name"]])()
      INFO("Setting test instance to: %s at loc: %s" % (test["instance"],
                                                        id(test["instance"])))
      if not test.get("params"):
        test["params"] = {}
      if not test.get("pre_ops"):
        test["pre_ops"] = []
      if not test.get("post_ops"):
        test["post_ops"] = []
      if not test.get("tags"):
        test["tags"] = []
      # NOTE: safeguard ends here
      try:
        test["test_start_time"] = time.time()
        test["instance"]. \
          execute_pre_operations(test["pre_ops"],
                                 extra_params=guest,
                                 **test["params"])
        test["instance"].run(extra_params=guest,
                             **test["params"])
        test["instance"]. \
          execute_post_operations(test["post_ops"],
                                  extra_params=guest,
                                  **test["params"])
        if "boot" in test["tags"] or "apc_boot" in test["tags"]:
          INFO("Skipping teardown for successful boot")
        else:
          test["instance"].teardown(extra_params=guest,
                                    **test["params"])
        test["result"] = "PASS"
      except TestNotSupported:
        WARN(traceback.format_exc())
        test["result"] = "NOT SUPPORTED"
        test["exception"] = traceback.format_exc()
        if "boot" in test["tags"] or "apc_boot" in test["tags"]:
          ERROR("Skipping other tests since boot test Not Supported")
          guest_result = "Not Supported"
          break
      except Exception:  # pylint: disable=broad-except
        ERROR(traceback.format_exc())
        test["result"] = "FAIL"
        test["exception"] = traceback.format_exc()
        guest_result = "Failed"
        try:
          test["instance"].teardown(extra_params=guest,
                                    **copy.deepcopy(test["params"]))
        except:  # pylint: disable=bare-except
          ERROR(traceback.format_exc())
          ERROR("Teardown failed")
        if "boot" in test["tags"] or "apc_boot" in test["tags"]:
          ERROR("Skipping other tests since boot test failed")
          break
      finally:
        test["test_end_time"] = time.time()
        test["test_runtime"] = test["test_end_time"] - \
                               test["test_start_time"]
    guest["end_time"] = time.time()
    guest["total_runtime"] = guest["end_time"] - \
                             guest["start_time"]
    guest["status"] = guest_result
    guest["qual_date"] = datetime.now().strftime(
      "%d/%m/%Y %H:%M:%S")
    INFO("Uploading results to ELK stack for guest OS: %s arch: %s"
         " bits: %s boot_type: %s" % (guest["os"], guest["arch"],
                                      guest["bits"], guest["boot"]))
    try:
      self._ingest_data(guest)
    except RuntimeError:
      ERROR("*********************************")
      ERROR("Unable to ingest data to ELK, hence failing the guest "
            "qualification for %s" % guest["os"])
      guest_result = "Failed"
      ERROR("*********************************")
      ERROR(traceback.format_exc())
    finally:
      if guest_result not in ["Succeeded", "Not Supported"]:
        self.failure_detected.append({guest["os"]: guest["tests"]})

  def _ingest_data(self, data):
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
      data["aos"] = str(data["aos"])
      data["ahv"] = str(data["ahv"])
      # sanitize the modules data.
      for test in data["tests"]:
        if test.get("exception") and not isinstance(test["exception"], str):
          test["exception"] = str(test["exception"])
      for module in data["modules"]:
        new_mods[module] = str(data["modules"][module])
      data["modules"] = new_mods

      new_tests = list()
      # sanitize the tests data.
      for test in data["tests"]:
        tmp = test
        if tmp.get("instance"):
          tmp["instance"] = str(tmp["instance"])
        else:
          tmp["instance"] = "NA"
        new_tests.append(tmp)
      data["tests"] = new_tests
      return data

    new_data = _sanitize(data)
    # pp = pprint.PrettyPrinter(indent=4)
    # INFO(pp.pformat(new_data))
    self.db_conn.ingest_json_data(new_data,
                                  db_name="gos_qualification")

  def _load_tests(self):
    """
    Internal method for loading tests
    Args:
    Returns:
      data(dict):
    """
    self.available_tests = get_module_classes(tests,
                                              predicate=lambda x:
                                              inspect.isclass(x)
                                              and not x.__subclasses__()
                                              and issubclass(x, AbstractTest))
    return self.available_tests


def proxyfunc(*args, **kwargs):
  """Delayed instantiation

    Returns:
      Object of BaseRoutables class
  """
  return MjolnirProxy(*args, **kwargs)

class MjolnirProxy():
  """Proxy class for routable creation"""

  def __new__(cls, entity_type, entity_class, name,
              routable_type=None, **kwargs):
    """
      Creates an object of BaseRoutables

      Args:
        entity_type(str): entity type
        entity_class(str): class name of entity
        name(str): Name of entity
        routable_type(dict): Nutest or Mjolnir
        **kwargs

      Returns:
        obj of BaseRoutables class
    """
    # check if there is any conversion map corresponding to given entity
    if not routable_type:
      routable_type = constants.NUTEST_CONV_MAP
    conversion_map = routable_type
    if entity_type in conversion_map:
      _map = conversion_map[entity_type]
    else:
      _map = {}
    obj = BaseRoutables(_map, entity_class(**kwargs), entity_type, name)
    return obj

class BaseRoutables():
  """Base Routable class for supporting entities from different frameworks"""

  def __init__(self, _map, _obj, entity_type, name):
    """
     Constructor method

     Args:
       _map(dict): Nestest/Mjolnir Map
       _obj(object): object
       entity_type(str): entity type (vm, host, nw)
       name(str): entitiy name

      Returns:
        None
    """
    self._map = _map
    self._obj = _obj
    self.entity_type = entity_type
    self.name = name
    if not entity_type in constants.VM_CACHE:
      constants.VM_CACHE[entity_type] = {}
    if not self.get_entity(entity_type=entity_type, name=name):
      constants.VM_CACHE[entity_type][name] = self
      print(("Setting:", constants.VM_CACHE))
    else:
      print(("Before:", id(self)))
      self = self.get_entity(entity_type=entity_type, name=name)
      print(("After", id(self)))

  def __getattr__(self, action):
    """
      Gets actual action name from map

      Args:
        action(str): Method/Action name invoked

      Returns:
        Method name if action found in map else action
    """
    action = self.__getconv__(action)
    if action in constants.REMOVE_ACTIONS:
      #if action fails, entity will still be removed from cache
      self.delete_entity()
    return getattr(self._obj, action)

  def __getconv__(self, action):
    """
      Get method name if action found in map

      Args:
        action(str): method name

      Returns:
        Method name if action found in map else action
    """
    if action in self._map:
      return self._map[action]
    return action

  @classmethod
  def get_entity(cls, entity_type, name):
    """
      Get entity from cache

      Args:
        entity_type(str): entity type
        name(str): name of entity

      Returns:
        Returns entity if exists else None
    """
    if entity_type in constants.VM_CACHE:
      if name in constants.VM_CACHE[entity_type]:
        return constants.VM_CACHE[entity_type][name]
      else:
        return None
    else:
      return None

  def delete_entity(self):
    """
      Get entity from cache

      Args:
      Returns:
    """
    if self.entity_type in constants.VM_CACHE:
      if self.name in constants.VM_CACHE[self.entity_type]:
        del constants.VM_CACHE[self.entity_type][self.name]
      else:
        INFO("%s not found under %s" % (self.name, self.entity_type))
    else:
      INFO("Entity type does not exist")
