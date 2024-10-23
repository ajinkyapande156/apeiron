"""
Copyright (c) 2023 Nutanix Inc. All rights reserved.

Author: pritam.chatterjee@nutanix.com
"""
# pylint: disable=invalid-name, broad-except, useless-else-on-loop
# pylint: disable=simplifiable-if-expression, no-else-return, unused-import
import time
import traceback
import inspect
from functools import wraps
from tabulate import tabulate
from framework.exceptions.nutest_error import NuTestError
from framework.lib.nulog import INFO, DEBUG, WARN, ERROR


class AbstractExecutor():
  """AbstractExecutor class"""
  def execute(self, *args, **kwargs):
    """
    Execute the target method
    Args:
    Returns:
    Raises:
    """
    raise NotImplementedError


class BasicExecutor(AbstractExecutor):
  """basic executor class"""

  def __init__(self, **kwargs):
    """
    Initialize a basic executor object
    Kwargs:
    Returns:
    Raises:
    """
    self.global_retry_count = kwargs.get("retries", 1)
    self.global_delay = kwargs.get("delay", 10)
    self.expected_result = "Pass"
    self.is_negative = False

  def execute(self, *args, **kwargs):
    """
    Execute the target method
    Args:
    Kwargs:
    Returns:
    Raises:
    """

    self.expected_result = kwargs.pop("expected_result", "Pass")
    # case1: Expected to PASS, retry if FAIL
    # case2: Expected to FAIL, retry if PASS
    self.is_negative = False if "pass" in self.expected_result.lower()\
      else True
    if self.is_negative:
      # case1
      return self.process_for_negative(*args, **kwargs)
    else:
      # case2
      return self.process_for_positive(*args, **kwargs)

  def process_for_positive(self, *args, **kwargs):
    """
    Execute the target method and validate it passes
    Args:
    Kwargs:
    Returns:
    Raises:
    """
    target = kwargs.pop("func")
    retries = kwargs.pop("retries", self.global_retry_count)
    interval = kwargs.pop("delay", self.global_delay)
    stats = {
      "func_name": [],
      "time(secs)": [],
      "attempt": [],
      "result": [],
      "exception": []
    }
    INFO("Function name: %s is expected to PASS" % target.__name__)
    exc = NuTestError
    for i in range(1, retries + 1):
      DEBUG("Function name: %s Retry count: %s" % (target, i))
      DEBUG(self.expected_result)
      start = time.time()
      try:
        stats["func_name"].append(target)
        stats["attempt"].append(i)
        result = target(*args, **kwargs)
        end = time.time()
        stats["time(secs)"].append(end - start)
        stats["result"].append("PASS")
        stats["exception"].append("NA")
        INFO(tabulate(stats, headers="keys",
                      tablefmt="grid"))
        return result
      except Exception as ex:
        exc = ex
        # this operation is not expected to fail
        # so attempting retry and updating result with status, exception
        WARN("This operation is expected to PASS, retrying again")
        INFO(traceback.format_exc())
        end = time.time()
        stats["time(secs)"].append(end - start)
        stats["result"].append("FAIL")
        stats["exception"].append(traceback.format_exc())
        time.sleep(interval)
    else:
      # once we go out of retries(i.e. for loop)
      INFO(tabulate(stats, headers="keys",
                    tablefmt="grid"))
      ERROR("Operation did not PASS after %s retries "
            "and %s sec delay" % (retries, interval))
      raise exc


  def process_for_negative(self, *args, **kwargs):
    """
    Execute the target method and validate it fails
    Args:
    Kwargs:
    Returns:
    Raises:
    """
    target = kwargs.pop("func")
    retries = kwargs.pop("retries", self.global_retry_count)
    interval = kwargs.pop("delay", self.global_delay)
    stats = {
      "func_name": [],
      "time(secs)": [],
      "attempt": [],
      "result": [],
      "exception": []
    }
    exc = NuTestError
    INFO("Function name: %s is expected to FAIL" % target.__name__)
    for i in range(1, retries + 1):
      DEBUG("Function name: %s Retry count: %s" % (target, i))
      result = None
      DEBUG(self.expected_result)
      start = time.time()
      try:
        stats["func_name"].append(target)
        stats["attempt"].append(i)
        result = target(*args, **kwargs)
        raise RuntimeError(
          "This operation was expected to FAIL, but it PASSED")
      # may need some customer exception if ops failure also raises NuTestError
      except RuntimeError:
          # this operation is expected to fail, but it passed,
          # so not attempting retry and updating status and exception
        end = time.time()
        WARN("THIS OPERATION IS EXPECTED TO FAIL, retrying again")
        stats["result"].append("FAIL")
        stats["time(secs)"].append(end - start)
        stats["exception"].append(traceback.format_exc())
        time.sleep(interval)
      except Exception:
        end = time.time()
        INFO("THIS OPERATION FAILED AS EXPECTED")
        stats["result"].append("PASS")
        stats["time(secs)"].append(end - start)
        stats["exception"].append(traceback.format_exc())
        INFO(tabulate(stats, headers="keys",
                      tablefmt="grid"))
        return result
    else:
      INFO(tabulate(stats, headers="keys",
                    tablefmt="grid"))
      raise exc("Operation did not FAIL after %s retries "
                "and %s sec delay" % (retries, interval))


def use_executor(func):
  """
  Decorator for using mjolnir executor
  Args:
    func(function): decorated method
  Returns:
  """

  @wraps(func)
  def wrapper(*args, **kwargs):
    """
    Internal
    Returns:
    """
    executor = BasicExecutor()
    retries = kwargs.pop("retries", 3)
    delay = kwargs.pop("delay", 2)
    for caller in inspect.stack():
      if "mjolnir_executor" in caller[1] and \
        caller[3] == "execute":
        WARN(caller)
        WARN("Disabling use_executor decorator for %s" % func.__name__)
        return func(*args, **kwargs)
    return executor.execute(*args, func=func, retries=retries, delay=delay,
                            **kwargs)

  return wrapper
