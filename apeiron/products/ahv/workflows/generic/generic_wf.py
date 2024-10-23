"""
Copyright (c) 2023 Nutanix Inc. All rights reserved.

Author: rishabh.kumar@nutanix.com
"""
import time

from framework.lib.nulog import INFO, STEP
from libs.workflows.generic.wf_helpers \
  import WorkflowsHelper
from libs.workflows.generic import reports

class GenericWorkflows:
  """Generic Workflows"""
  def __init__(self, cluster, **kwargs):
    """
    Initialize object
    Args:
      cluster(object): Nutest cluster object
    """
    self.cluster = cluster
    self.wf_helper = WorkflowsHelper(cluster=self.cluster, **kwargs)

  def step(self, **kwargs):
    """
    Perform the step mentioned in config file
    Args:
    Returns:
    """
    steps = kwargs.pop("steps", "")
    iterations = kwargs.pop("iterations", 1)
    # If same step is used for performing different operations based on
    # the arguments passed. For ex - bulk_ops, create_multiple_vms.
    # So, adding a suffix in step name for better logging and tracking
    step_name_suffix = kwargs.pop("step_name_suffix", "")

    for iteration in range(iterations):
      if iterations > 1:
        INFO("Iteration: [%s/%s]" % (iteration + 1, iterations))
      for step in steps.split(","):
        step = step.strip()
        if len(step) > 0:
          step_name = step
          if len(step_name_suffix) > 0:
            step_name = step + "___%s" % step_name_suffix
          STEP("Performing step: [%s]" % step_name)
          start_time = time.time()
          getattr(self.wf_helper, step)(**kwargs)
          time_taken = time.time() - start_time
          INFO("Time taken to perform step: %s = %ss"
               % (step_name, round(time_taken)))

          if not reports.OPERATIONS.get(step_name):
            reports.OPERATIONS.update({step_name: []})
          reports.OPERATIONS[step_name].append(time_taken)
