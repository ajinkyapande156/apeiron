"""
Copyright (c) 2024 Nutanix Inc. All rights reserved.

Author: pritam.chatterjee@nutanix.com
"""
# pylint: disable=import-error, unused-import, unused-argument, broad-except
from framework.lib.nulog import INFO, WARN, ERROR, STEP


class BaseWorkflow:
  """Base workflow class."""
  def __init__(self, *args, **kwargs):
    """Constructor."""
    self.cluster = kwargs.get("cluster")
    self.wf_helper = None

  def execute_validations(self, **kwargs):
    """
    Performs the provided vaidations
    Args:
    Returns:
    Raises:
    """
    clean_up = kwargs.pop("clean_up", None)
    clean_up_funcs = clean_up.split(",") if clean_up else []
    validations = kwargs.pop("validations", '')
    try:
      if isinstance(validations, str):
        for validation in validations.split(","):
          if validation in ['']:
            continue
          validation = validation.strip()
          STEP("Performing the validation: [%s]" % validation)
          getattr(self.wf_helper, validation)(**kwargs)
      elif isinstance(validations, list):
        for validation in validations:
          kwargs.pop("expected_result", {})
          kwargs.pop("vm_name", None)
          func_name = validation.pop("name")
          STEP("Executing: %s" % func_name)
          kwargs.update(validation)
          getattr(self.wf_helper, func_name)(
            **kwargs)
    except Exception as ex:
      STEP("WARNING - Executing clean-up methods in provided sequence: %s"
           % clean_up_funcs)
      for func_name in clean_up_funcs:
        kwargs.pop("expected_result", {})
        kwargs.pop("vm_name", None)
        STEP("Executing Cleanup Function: %s" % func_name)
        getattr(self.wf_helper, func_name)(
          **kwargs)
      raise ex
