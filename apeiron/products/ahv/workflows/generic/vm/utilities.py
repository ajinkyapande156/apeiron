"""
Copyright (c) 2024 Nutanix Inc. All rights reserved.
Author: rishabh.kumar@nutanix.com

VM Utilities
"""
#pylint: disable=broad-except
import functools
import textwrap
import traceback
from tabulate import tabulate
from framework.lib.nulog import INFO, STEP, ERROR
from libs.workflows.generic import reports


def vm_executor(func):
  """
  Decorator for performing VM related methods
  Args:
    func(function): Method to be executed
  Returns:
  Raises:
      Exception: when func method fails
  """
  @functools.wraps(func)
  def wrapper(self, *args, **kwargs):
    """
    Wrapper
    Args:
    Returns:
    Raises:
      Exception: when func method fails
    """
    func_name = func.__name__
    vm_name = kwargs.get("vm_name", self.vm_name)
    exception = None
    expected_result = kwargs.pop("expected_result", "PASS")
    try:
      INFO("Executing %s on VM: %s" % (func_name, vm_name))
      func(self, *args, **kwargs)
      result = "PASS"
      if expected_result == "FAIL":
        result = "UNEXPECTED_PASS"
        exception = f"{func_name} was expected to FAIL but is PASSED"
    except Exception as ex:
      ERROR(traceback.format_exc())
      exception = str(ex)
      exception = traceback.format_exc()
      if expected_result == "FAIL":
        INFO(f"{func_name} failed as expected!")
        result = "EXPECTED_FAILURE"
      else:
        result = "FAIL"
        if reports.REPORT_ERRORS_END:
          self.vm_factory.pop(vm_name)

    # If vm_name is not present in VM_OPERATIONS dict, add it
    if vm_name not in reports.VM_OPERATIONS:
      reports.VM_OPERATIONS.update({vm_name: {}})

    if "vm_ops" not in reports.VM_OPERATIONS[vm_name]:
      reports.VM_OPERATIONS[vm_name]["vm_ops"] = []

    reports.VM_OPERATIONS[vm_name]["vm_ops"].append(
      [func_name, result, exception]
    )

    if result == "FAIL":
      reports.TEST_FAILED = True
      if reports.REPORT_ERRORS_END is False:
        raise Exception(exception)

  return wrapper

def wrap_text(text, width=50):
  """
  Method to wrap text for properly displaying exceptions in table
  Args:
    text(str): Text to wrap
    width(int): Width of each line
  Returns:
    str: Wrapped up text
  """
  return "\n".join(textwrap.wrap(str(text), width))


def display_vm_summary_report():
  """
  Display the VM details and the operations performed on it.
  """
  STEP("VM Summary")
  vm_table = []
  vm_table_headers = ["VM Name", "Boot Type", "Features", "Guest OS", \
                      "VM Operations"]
  vm_ops_headers = ["Operation", "Result", "Exception"]

  for vm_name, vm_details in reports.VM_OPERATIONS.items():
    curr_row = [vm_name]
    for header in range(1, len(vm_table_headers)-1):
      header_name = vm_table_headers[header].lower().replace(" ", "_")
      curr_row.append(vm_details.get(header_name, "NA"))

    vm_ops_table = []
    for op in vm_details.get("vm_ops", []):
      vm_ops_table.append([op[0], op[1], wrap_text(op[2])])

    vm_ops_table = tabulate(vm_ops_table, vm_ops_headers, tablefmt="grid")
    curr_row.append(vm_ops_table)
    vm_table.append(curr_row)

  vm_table = tabulate(vm_table, vm_table_headers, tablefmt="grid")
  STEP("\n%s\n" % vm_table)
