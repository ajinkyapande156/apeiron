"""
Copyright (c) 2021 Nutanix Inc. All rights reserved.

Author: pritam.chatterjee@nutanix.com
"""
# pylint: disable=import-error, invalid-name, broad-except
import copy
import inspect
import pkgutil
import re
import time


try:
  from framework.lib.nulog import INFO, WARN

  EXECUTOR = "nutest"
except Exception:  # pylint: disable=broad-except
  from libs.ahv.framework.proxy_logging import \
    INFO, WARN  # pylint: disable=import-error

  EXECUTOR = "mjolnir"
from libs.ahv.workflows.gos_qual.lib \
  import operating_systems  # pylint: disable=import-error
from libs.ahv.workflows.gos_qual.lib.base.abstracts \
  import AbstractOperatingSystem  # pylint: disable=import-error, line-too-long


def get_module_classes(mod, predicate=None):
  """
  Load classes from a module object
  Args:
    mod(object): module object
    predicate(func): function to be executed for filtering criteria
  Returns:
    class_map(dict): module_name to class_object map
  """
  prefix = mod.__name__ + "."
  class_map = {}
  for (_, name, _) in \
      pkgutil.iter_modules(mod.__path__, prefix):
    _mod = __import__(name, fromlist="all")
    classes = list(set(
      [impl[1] for impl in inspect.getmembers(_mod, predicate=predicate)
       if name.split(".")[-1] in impl[1].__module__]))
    if classes:
      class_map[name.split(".")[-1]] = classes[-1]
  return class_map


def get_os_instance(guest_os):
  """
  Load the appropriate operating system class for guest os operations
  Args:
    guest_os(str): identifier string for guest os
  Returns:
    class_map(dict): module_name to class_object map
  """

  def _find_nearest_match(expected, available):
    """
    Internal function, don't bother
    Args:
      expected(str): expected
      available(str): available
    Returns:
      nearest_match(str): matched
    """
    nearest_match = 0
    expected = int(expected)
    available = list(map(int, available))
    available.sort()
    found = False
    if expected in available:
      return expected
    else:
      for i, val in enumerate(available):
        if expected < val and i == 0:
          return None  # No match found, reset to default
        elif expected < val:
          nearest_match = available[i - 1]
          found = True
          break
      if not found:
        nearest_match = available[-1]
    return nearest_match

  available_os = get_module_classes(
    operating_systems,
    predicate=lambda x: inspect.isclass(x)
    and issubclass(x, AbstractOperatingSystem))
  # INFO(available_os)
  value = guest_os.lower().split("_")[0]
  match = re.search(r'(\D+)([\d.]+)', value)
  flavor = match.group(1)
  version = "".join(match.group(2).split("."))
  os_vers = [re.split(r'\D+', gos)[-1]
             for gos in list(available_os.keys()) if flavor in gos]
  if os_vers:
    find = _find_nearest_match(version, os_vers)
  else:
    find = None
  if not find:
    INFO("Setting the operating system interface to %s"
         % operating_systems.default.Default)
    return operating_systems.default.Default
  else:
    INFO("Setting the operating system interface to %s"
         % available_os[flavor + str(find)])
    return available_os[flavor + str(find)]


def get_install_iso(iso_data):
  """
  Will be removed, so don't bother
  Args:
    iso_data(dict): iso details
  Returns:
  """
  return iso_data.get("iso")


def get_ks_iso(iso_data):
  """
  Will be removed, so don't bother
  Args:
    iso_data(dict): iso details
  Returns:
  """
  return iso_data.get("kickstart")


def get_pos_dict(data):
  """
  Converts a simple list pos to dict
  Args:
    data(list):
  Returns:
    new_dict(dict):
  """
  new_dict = dict()
  for i, val in enumerate(data):
    new_dict[i] = val
  return copy.deepcopy(new_dict)


def convert_list_to_pos_dict(plan):
  """
  Convert a list with dict to post dict recursively
  Args:
    plan(list):
  Returns:
    new_dict(dict):
  """
  new_dict = plan
  if isinstance(plan, list):
    new_dict = get_pos_dict(plan)
  for k in new_dict:
    if isinstance(new_dict[k], list):
      new_dict[k] = convert_list_to_pos_dict(new_dict[k])
    elif isinstance(new_dict[k], dict):
      new_dict[k] = convert_list_to_pos_dict(new_dict[k])
  return new_dict


def gos_list(data):
  """
  Converts a simple to pos dict to list
  Args:
    data(dict):
  Returns:
    new_list(list):
  """
  new_list = list()
  keys = sorted(list(data.keys()), key=int)
  for k in keys:
    new_list.append(data[k])
  return new_list


def convert_pos_dict_to_list(plan):
  """
  Converts a nested dict to list recursively
  Args:
    plan(dict):
  Returns:
    new_list(list):
  """
  new_list = plan
  if not plan:
    return
  if isinstance(plan, dict) and re.search(r'^\d{1,9}$', list(plan.keys())[0]):
    new_list = gos_list(plan)
  for val in new_list:
    if isinstance(val, dict):
      idx = new_list.index(val)
      new_list[idx] = convert_pos_dict_to_list(val)
    if isinstance(val, str) or isinstance(val, str):
      if isinstance(new_list, dict) and isinstance(new_list[val], dict):
        new_list[val] = convert_pos_dict_to_list(new_list[val])
  return new_list


def retry(times=5, interval=5, exceptions=(Exception)):
  """
  Decorator to retry a function based on exceptions thrown
  Args:
    times(int): The number of retries
    interval(int): Inverval between retries
    exceptions(tuple): Lists of exceptions that trigger a retry attempt
  Raises:
  Returns:
  """
  def decorator(func):
    """
    Decorator function
    Args:
      func(callable): function object for decorater func
    Returns:
    """
    def newfn(*args, **kwargs):
      """
      Wrapper function
      Args:
      Returns:
      """
      attempt = 0
      while attempt < times:
        try:
          return func(*args, **kwargs)
        except exceptions:
          WARN('Exception thrown when attempting to run %s, attempt '
               '%d of %d' % (func, attempt, times))
          attempt += 1
          time.sleep(interval)
      return func(*args, **kwargs)
    return newfn
  return decorator
