"""
Copyright (c) 2022 Nutanix Inc. All rights reserved.

Author: pritam.chatterjee@nutanix.com
"""

# pylint: disable=W0221, fixme, bad-continuation, import-error, no-self-use
# pylint: disable=wrong-import-position, no-name-in-module, ungrouped-imports
# pylint: disable=inconsistent-return-statements
import random

import copy
import importlib
import inspect
from distutils.version import StrictVersion
import re
from bs4 import BeautifulSoup

MOD = "requests"
REQUESTS = importlib.import_module(MOD)  # pylint: disable=import-error

from libs.ahv.workflows.gos_qual.configs import \
  constants as const
from libs.ahv.workflows.gos_qual.lib import tests  # pylint: disable=import-error
from libs.ahv.workflows.gos_qual.lib.base.utilities \
  import get_module_classes  # pylint: disable=import-error
from libs.ahv.workflows.gos_qual.lib.base.abstracts \
  import AbstractTest  # pylint: disable=import-error
from libs.ahv.workflows.gos_qual.lib.base.filters \
  import GuestTestFilter

try:
  from framework.lib.nulog import INFO, WARN, DEBUG, ERROR  # pylint: disable=unused-import
  EXECUTOR = "nutest"
except Exception:  # pylint: disable=broad-except
  from libs.ahv.framework.proxy_logging \
    import INFO, WARN, DEBUG, ERROR  # pylint: disable=import-error

  EXECUTOR = "mjolnir"


####################################
# Qualification test selector
####################################
class AbstractTestSelector:
  """AbstractTestSelector class"""

  def select(self):
    """
    Method to select the guest qualification test
    Args:
    Returns:
    Raises:
    """
    raise NotImplementedError


class BaseTestSelector(AbstractTestSelector):
  """BaseTestSelector class"""
  FILTERS = {
    "tests": GuestTestFilter
  }
  def __init__(self):
    """
    Create base test selector instance
    """
    self.available_tests = None
    self.test_plan = None
    self.test_db = self._load_tests()
    self.boot_tests = self._get_boot_tests()
    self.cpu_tests = self._get_cpu_tests()

  def filter(self, data, filters):
    """
    Add filter based on test name
    Args:
      data(list): data
      filters(dict): can have keys:  tests
    Returns:
       filtered(dict): guests satisfying the required filters
    """
    filtered = dict()
    shortest_filter = None
    for key, val in list(filters.items()):
      filtered[key] = self.FILTERS[key].a_filter(data, val)
      if shortest_filter:
        if len(filtered[key]) < filtered[shortest_filter]:
          shortest_filter = key
      else:
        shortest_filter = key

    selected = list()
    # perform interesection of different filters
    for val in filtered[shortest_filter]:
      count = len(list(filtered.keys())) - 1  # exclude the shortest_filter key
      for key in filtered:
        if key == shortest_filter:
          continue
        if val in filtered[key]:
          count -= 1
      if count == 0:
        selected.append(val)
    return selected

  def _load_tests(self):
    """
    Internal method for loading tests
    Returns:
      data(dict):
    """
    self.available_tests = get_module_classes(tests,
                                              predicate=lambda x:
                                              inspect.isclass(x)
                                              and not x.__subclasses__()
                                              and issubclass(x, AbstractTest))
    return self.available_tests

  def _discover_virtio_drivers(self, position=None, version=None):
    """
    Add the discovery logic here
    Args:
      position(int): n less than latest version
      version(str): virtio version
    Returns:
      each_iso(str): virtio url
    """
    INFO(self)
    url = 'http://endor.dyn.nutanix.com/acro_images/automation/' \
          'ahv_guest_os/VirtIO'
    ext = 'iso'
    page = REQUESTS.get(url).text
    soup = BeautifulSoup(page, 'html.parser')
    iso_paths = [url + '/' + node.get('href') for node in soup.find_all('a') if
                 node.get('href').endswith(ext)]
    versions = []
    # Find latest version if no version is provided
    if not version:
      for each_iso in iso_paths:
        res = re.search(r"Nutanix-VirtIO-\d\.\d\.\d\.iso", each_iso)
        if res:
          filename = res.group()
          search_version = re.search(r"\d\.\d\.\d", filename)
          versions.append(search_version.group())
      versions.sort(key=StrictVersion)
      INFO(versions)
      # fixme , remove 2.0.0
      if position:
        version = versions[-2 + position]
      else:
        version = versions[-2]
    # search
    for each_iso in iso_paths:
      res = re.search(r"Nutanix-VirtIO-\d\.\d\.\d\.iso", each_iso)
      if res:
        filename = res.group()
        search_version = re.search(r"\d\.\d\.\d", filename)
        if search_version.group() == version:
          return each_iso

  def _get_boot_test_params(self, guest_info, **kwargs):
    """
    Get the required images to be passed to boot tests
    Args:
      guest_info(dict): guest info dict
    Returns:
      boot_params(dict):
    """
    if guest_info["vendor"] in ["microsoft"]:
      boot_params = {
        "virtio": self._discover_virtio_drivers(**kwargs)
      }
      boot_params.update(guest_info["images"])
      boot_params.pop("oemdrv")
    elif guest_info["vendor"] in const.OEMDRV_BASED_VENDORS:
      boot_params = {}
      boot_params.update(guest_info["images"])
    else:
      boot_params = {}
      boot_params.update(guest_info["images"])
      boot_params.pop("oemdrv")
    return copy.deepcopy(boot_params)

  def _get_tests_with_tag(self, tag):
    """
    Internal method
    Args:
      tag(str):
    Returns:
    """
    return [test for test in self.available_tests if
            tag in self.available_tests[test].get_tags()]

  def _get_boot_tests(self):
    """
    Internal method
    Args:
    Returns:
    """
    return [test for test in self.available_tests if
            "boot" in self.available_tests[test].get_tags()]

  def _get_cpu_tests(self):
    """
    Internal method
    Args:
    Returns:
    """
    return [test for test in self.available_tests if
            "cpu" in self.available_tests[test].get_tags()]

  def _get_mem_tests(self):
    """
    Internal method
    Args:
    Returns:
    """
    return [test for test in self.available_tests if
            "memory" in self.available_tests[test].get_tags()]

  def _get_network_tests(self):
    """
    Internal method
    Args:
    Returns:
    """
    return [test for test in self.available_tests if
            "network" in self.available_tests[test].get_tags()]

  def _get_storage_tests(self):
    """
    Internal method
    Args:
    Returns:
    """
    return [test for test in self.available_tests if
            "storage" in self.available_tests[test].get_tags()]

  def _get_teardown_tests(self):
    """
    Internal method
    Args:
    Returns:
    """
    return [test for test in self.available_tests if
            "teardown" in self.available_tests[test].get_tags()]

  def _get_untagged_tests(self):
    """
    Internal method
    Args:
    Returns:
    """
    return [test for test in self.available_tests if
            not self.available_tests[test].get_tags()]

  def _get_snapshot_tests(self):
    """
    Internal method
    Args:
    Returns:
    """
    return [test for test in self.available_tests if
            "snapshot" in self.available_tests[test].get_tags()]

  def _get_clone_tests(self):
    """
    Internal method
    Args:
    Returns:
    """
    return [test for test in self.available_tests if
            "clone" in self.available_tests[test].get_tags()]

  def _get_lm_tests(self):
    """
    Internal method
    Args:
    Returns:
    """
    return [test for test in self.available_tests if
            "live_migration" in self.available_tests[test].get_tags()]

  def _get_misc_tests(self):
    """
    Internal method
    Args:
    Returns:
    """
    return [test for test in self.available_tests if not
        {"boot", "cpu", "memory", "storage", "network",
         "snapshot", "clone", "live_migration",
         "teardown"}.intersection(set(self.available_tests[test].get_tags()))]


class DefaultTestSelector(BaseTestSelector):
  """DefaultTestSelector class"""

  def select(self, **kwargs):
    """
    Method to select the guest qualification test
    Args:
    Returns:
    """
    # FIXME: Only selects cdrom boot scenarios for boot test cases
    test_plan = kwargs.get("guest_plan")
    cpu = self._add_test_details(self._get_cpu_tests())
    mem = self._add_test_details(self._get_mem_tests())
    network = self._add_test_details(self._get_network_tests())
    storage = self._add_test_details(self._get_storage_tests())
    snapshot = self._add_test_details(self._get_snapshot_tests())
    clone = self._add_test_details(self._get_clone_tests())
    lm = self._add_test_details(self._get_lm_tests())
    misc = self._add_test_details(self._get_misc_tests())
    teardown = self._add_test_details(self._get_teardown_tests())
    for guest in test_plan:
      boot = self._add_test_details(self._select_boot_test(guest))
      test_plan[guest]["tests"] = list()
      test_plan[guest]["tests"] = test_plan[guest]["tests"] + \
                                  copy.deepcopy(boot) + \
                                  copy.deepcopy(cpu) \
                                  + copy.deepcopy(mem) + \
                                  copy.deepcopy(network) \
                                  + copy.deepcopy(storage) + \
                                  copy.deepcopy(snapshot) \
                                  + copy.deepcopy(clone) + \
                                  copy.deepcopy(lm) + \
                                  copy.deepcopy(misc) + \
                                  copy.deepcopy(teardown)
    return test_plan

  def _add_test_details(self, tests_data):
    """
    Internal method
    Args:
      tests_data(list):
    Returns:
      tmp(dict):
    """
    tmp = list()
    for test in tests_data:
      data = {
        "name": test,
        "instance": self.available_tests[test],
        "params": self.available_tests[test].get_default_params(),
        "pre_ops": self.available_tests[test].get_pre_operations(),
        "post_ops": self.available_tests[test].get_post_operations(),
        "tags": self.available_tests[test].get_tags()
      }
      tmp.append(copy.deepcopy(data))
    return tmp

  def _select_boot_test(self, guest):
    """
    Internal method
    Args:
      guest(list):
    Returns:
      data(list):
    """
    # find which boot tests are applicable
    if "solaris" in guest["os"]:
      return [test for test in self._get_boot_tests() if
              "disk" in self.available_tests[test].get_tags() and
              guest["boot"] in self.available_tests[test].get_tags()]
    return [test for test in self._get_boot_tests() if
            "cdrom" in self.available_tests[test].get_tags() and
            guest["boot"] in self.available_tests[test].get_tags()]


class BootVariationTestSelector(DefaultTestSelector):
  """BootVariationTestSelector class"""
  BOOT_PARAMS_MAP = {
    "uefi": {},
    "legacy": {},
    "secureboot": {
      "uefi_boot": True,
      "machine_type": "q35",
      "secure_boot": True
    },
    "credentialguard": {
      "uefi_boot": True,
      "machine_type": "q35",
      "secure_boot": True,
      "windows_credential_guard": True
    },
    "vtpm": {
      "uefi_boot": True,
      "virtual_tpm": True
    },
    "vtpm_secureboot": {
      "uefi_boot": True,
      "machine_type": "q35",
      "secure_boot": True,
      "virtual_tpm": True
    },
    "vtpm_credentialguard": {
      "uefi_boot": True,
      "machine_type": "q35",
      "secure_boot": True,
      "virtual_tpm": True,
      "windows_credential_guard": True
    }
  }

  def select(self, **kwargs):
    """
    Method to select the guest qualification test
    Args:
    Returns:
    """
    # NOTE: Only selects cdrom boot scenarios for boot test cases
    test_plan = kwargs.get("guest_plan")
    snapshot = [self._add_test_details(test) for test
                in self._get_snapshot_tests()]
    clone = [self._add_test_details(test) for test
             in self._get_clone_tests()]
    lm = [self._add_test_details(test) for test
          in self._get_lm_tests()]
    cpu = [self._add_test_details(test) for test in self._get_cpu_tests()]
    mem = [self._add_test_details(test) for test in self._get_mem_tests()]
    network = [self._add_test_details(test) for test
               in self._get_network_tests()]
    storage = [self._add_test_details(test) for test
               in self._get_storage_tests()]
    updates = [self._add_test_details(test) for test in
               self._get_tests_with_tag("install_updates")]
    teardown = [self._add_test_details(test) for test
                in self._get_teardown_tests()]

    for guest in test_plan:
      boot = [self._add_test_details
              (test, boot_feature=guest["boot"],
               test_params=self._get_boot_test_params(guest))
              for test in self._select_boot_test(guest)]
      if guest["os"] in ["solaris"]:
        self._handle_solaris_exception(boot)
      guest["tests"] = list()
      guest["tests"] = guest["tests"] + \
                       copy.deepcopy(boot) + \
                       copy.deepcopy(snapshot) + \
                       copy.deepcopy(clone) + \
                       copy.deepcopy(lm) + \
                       copy.deepcopy(cpu) + \
                       copy.deepcopy(mem) + \
                       copy.deepcopy(network) + \
                       copy.deepcopy(storage) + \
                       copy.deepcopy(updates) + \
                       copy.deepcopy(teardown)
      # guest["tests"] = guest["tests"] + \
      #                   copy.deepcopy(boot) + copy.deepcopy(network)
      if kwargs.get("test_filters"):
        INFO("Getting test filter")
        guest["tests"] = self.filter(guest["tests"], kwargs.get("test_filters"))
    return test_plan

  def _add_test_details(self, test, boot_feature=None,
                        test_params=None):
    """
    Internal method
    Args:
      test(str):
      boot_feature(str):
      test_params(dict):
    Returns:
      tmp(dict):
    """
    data = {
      "name": test,
      # "instance": self.available_tests[test],
      "params": copy.deepcopy(
        self.available_tests[test].get_default_params()),
      "pre_ops": self.available_tests[test].get_pre_operations(),
      "post_ops": self.available_tests[test].get_post_operations(),
      "tags": self.available_tests[test].get_tags()
    }
    if boot_feature:
      data["params"].update(self.BOOT_PARAMS_MAP[boot_feature])
    if test_params:
      data["params"].update(test_params)
    return copy.deepcopy(data)

  def _handle_solaris_exception(self, data):
    """
    Internal method to modify boot params for
    Solaris as an exception for guest qual
    Args:
      data(dict):
    Returns:
    """
    data[0]['params']['boot_disk_type'] = random.choice(["IDE", "SATA"])
    data[0]['params']['vnic_type'] = "E1000"


class ApcBootVariationTestSelector(BootVariationTestSelector):
  """ApcBootVariationTestSelector class"""
  def _get_boot_tests(self):
    """
    Internal method
    Args:
    Returns:
    """
    return [test for test in self.available_tests if
            "apc_boot" in self.available_tests[test].get_tags()]


class DiskBootVariationTestSelector(BootVariationTestSelector):
  """DiskBootVariationTestSelector class"""
  def _select_boot_test(self, guest):
    """
    Internal method
    Args:
      guest(list):
    Returns:
      data(list):
    """
    # find which boot tests are applicable
    return [test for test in self._get_boot_tests() if
            "disk" in self.available_tests[test].get_tags() and
            guest["boot"] in self.available_tests[test].get_tags()]

class PxeBootVariationTestSelector(BootVariationTestSelector):
  """PxeBootVariationTestSelector class"""
  def _select_boot_test(self, guest):
    """
    Internal method
    Args:
      guest(list):
    Returns:
      data(list):
    """
    # find which boot tests are applicable
    return [test for test in self._get_boot_tests() if
            "pxe" in self.available_tests[test].get_tags() and
            guest["boot"] in self.available_tests[test].get_tags()]


class VirtioTestSelector(BootVariationTestSelector):
  """
  Select the tests application for virtio qualification and also
  modify their arguments as required
  """

  def select(self, **kwargs):
    """
    Select the tests for virtio qualification suite
    Args:
    Returns:
    """
    test_plan = kwargs.get("guest_plan")
    storage = [self._add_test_details("hot_add_vdisks")]
    for guest in test_plan:
      boot1 = [self._add_test_details
               (test, boot_feature=guest["boot"],
                test_params=self._get_boot_test_params(guest,
                                                       version=kwargs.get
                                                       ("virtio_upgrade_path")))
               for test in self._select_boot_test(guest)]
      vm_delete = [self._add_test_details(test)
                   for test in self._get_teardown_tests()]
      boot2 = [self._add_test_details
               (test, boot_feature=guest["boot"],
                test_params=self._get_boot_test_params
                (guest, position=kwargs.get("virtio_install_path",
                                            -1)))
               for test in self._select_boot_test(guest)]
      virtio_upgrade = [self._add_test_details("virtio_driver_upgrade",
                                               test_params={
                                                 "virtio_upgrade_path":
                                                   self._discover_virtio_drivers
                                                     (
                                                     version=kwargs.get
                                                     ("virtio_upgrade_path")
                                                   )
                                               })]
      boot3 = [self._add_test_details
               (test, boot_feature=guest["boot"],
                test_params=self._get_boot_test_params
                (guest, position=kwargs.get("virtio_install_path",
                                            -1)))
               for test in self._select_boot_test(guest)]
      virtio_pnputil = [self._add_test_details("virtio_driver_upgrade_utilpnp",
                                               test_params={
                                                 "virtio_upgrade_path":
                                                   self._discover_virtio_drivers
                                                     (
                                                     version=kwargs.get
                                                     ("virtio_upgrade_path")
                                                   )
                                               })]
      guest["tests"] = list()
      guest["tests"] = guest["tests"] + \
                       copy.deepcopy(boot1) + \
                       copy.deepcopy(storage) + \
                       copy.deepcopy(vm_delete) + \
                       copy.deepcopy(boot2) + \
                       copy.deepcopy(storage) + \
                       copy.deepcopy(virtio_upgrade) + \
                       copy.deepcopy(storage) + \
                       copy.deepcopy(vm_delete) + \
                       copy.deepcopy(boot3) + \
                       copy.deepcopy(storage) + \
                       copy.deepcopy(virtio_pnputil) + \
                       copy.deepcopy(storage) + \
                       copy.deepcopy(vm_delete)
    return test_plan


class GuestUpgradeTestSelector(BootVariationTestSelector):
  """GuestUpgradeTestSelector class"""

  def select(self, **kwargs):
    """
    Method to select the guest qualification test
    Args:
    Returns:
    """
    # NOTE: Only selects cdrom boot scenarios for boot test cases
    test_plan = kwargs.get("guest_plan")
    #self.filter() add the filter here
    snapshot = [self._add_test_details(test) for test
                in self._get_snapshot_tests()]
    clone = [self._add_test_details(test) for test
             in self._get_clone_tests()]
    lm = [self._add_test_details(test) for test
          in self._get_lm_tests()]
    cpu = [self._add_test_details(test) for test in self._get_cpu_tests()]
    mem = [self._add_test_details(test) for test in self._get_mem_tests()]
    network = [self._add_test_details(test) for test
               in self._get_network_tests()]
    storage = [self._add_test_details(test) for test
               in self._get_storage_tests()]
    updates = [self._add_test_details("install_all_os_updates")]
    teardown = [self._add_test_details(test) for test
                in self._get_teardown_tests()]

    for guest in test_plan:
      boot = [self._add_test_details
              (test, boot_feature=guest["boot"],
               test_params=self._get_boot_test_params(guest))
              for test in self._select_boot_test(guest)]
      guest["tests"] = list()
      guest["tests"] = guest["tests"] + \
                       copy.deepcopy(boot) + \
                       copy.deepcopy(updates) + \
                       copy.deepcopy(snapshot) + \
                       copy.deepcopy(clone) + \
                       copy.deepcopy(lm) + \
                       copy.deepcopy(cpu) + \
                       copy.deepcopy(mem) + \
                       copy.deepcopy(network) + \
                       copy.deepcopy(storage) + \
                       copy.deepcopy(teardown)
      # guest["tests"] = guest["tests"] + \
      #                   copy.deepcopy(boot) + copy.deepcopy(network)
      if kwargs.get("test_filters"):
        INFO("Getting test filter")
        guest["tests"] = self.filter(guest["tests"], kwargs.get("test_filters"))
    return test_plan
