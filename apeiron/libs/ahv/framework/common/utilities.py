'''
  Utilities module
'''


import collections
import importlib
import re
import json
import time

NUTEST_PLATFORM = True
try:
  from framework.exceptions.nutest_error import NuTestError # pylint: disable=wrong-import-position, unused-import
except Exception: # pylint: disable=broad-except
  NUTEST_PLATFORM = False

def update(dd, uu):
  """
    Args:
      dd(str): list
      uu(str): items

    Returns:
      (str): variable dd
  """
  for kk, vv in uu.items():
    if isinstance(vv, collections.Mapping):
      dd[kk] = update(dd.get(kk, {}), vv)
    else:
      dd[kk] = vv
  return dd

def dict_from_json(json_f):
  """
  Loads dict from json file
  Args:
    json_f(str): json file name
  Returns:
    data(dict): json data
  """
  with open(json_f, 'r') as fh:
    data = json.load(fh)
  return data


def function_loader(mod_path, test_name):
  """
    Args:
      mod_path(str): Path of module
      test_name(str): Name of test
    Returns:
      (function): Execute function
  """
  mod = importlib.import_module(mod_path, test_name)
  exec_func = getattr(mod, test_name)
  return exec_func


def docstring_loader(func):
  """
    Args:
      func(function): Function name
    Returns:
      (dict): Dictionary object
  """
  meta = func.__doc__.strip()
  meta = meta.split("\n")
  meta = [m.strip() for m in meta]
  doc_dict = {}
  for me in meta:
    if me.startswith("---"):
      break
    match = re.search(r'(\w+):([\[\s\w\]\",]+)', me)
    key = match.group(1).strip()
    val = match.group(2).strip()
    if "[" in val or "]" in val:
      val = re.findall(r'(\w+)', val)
    doc_dict[key] = val
  return doc_dict


def retry_until(func):
  """
    Args:
      func(function): Function name
    Returns:
      (function): Wrapper function
    Raises:
      (exception): reaise exception
  """
  def wrapper(*args, **kwargs):
    """
      Args:
        args(args): Varibale length argument list
        kwargs(kwargs): Arbitrary kwyword arguments
      Returns:
        (function): result function
    """
    no_of_retries = kwargs.pop("no_of_retries", 5)
    sleep_btw_reties = kwargs.pop("sleep_btw_retries", 2)
    expected_result = kwargs.pop("expected", None)
    result = None
    while no_of_retries:
      try:
        result = func(*args, **kwargs)
        if not expected_result or result.strip() == expected_result:
          break
      except Exception as ex: # pylint: disable=broad-except
        no_of_retries -= 1
        print("Retrying on exception %s, retry count: %s" % (ex, no_of_retries))
        time.sleep(sleep_btw_reties)
    if not no_of_retries:
      raise RuntimeError("Retry attempts failed")
    return result

  return wrapper


# if __name__ == "__main__":
#   get_call = {
#     "a": "123",
#     "b": {
#       "c": "a",
#       "d": [1, 2, 3]
#     }
#   }
