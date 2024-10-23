"""
Copyright (c) 2022 Nutanix Inc. All rights reserved.

Author: vedant.dalal@nutanix.com
"""

from framework.lib.nulog import INFO, ERROR

class Worker():
  """
  A class containing methods to Worker module
  """
  def __init__(self, task_manager, worker_type, worker_name):
    """Create worker to execute actual task. Accepts DynamicQueues instance,
    worker type and worker name

    Args:
      task_manager(TaskManager): Task Manager
      worker_type(str): Worker Type
      worker_name(str): Worker Name
    """
    self._task_manager = task_manager
    self._type = worker_type
    self._is_active = True
    self._name = worker_name
    INFO("Initializing worker %s, for workload : %s"%(self._name, self._type))

  def execute(self):
    """Execute actual task given to worker
    """
    while not self._task_manager._time_to_exit: # pylint: disable=protected-access
      task = self._get_task()
      if not task:
        continue
      self._execute_task(task)
    self._is_active = False
    INFO("Exit is called. Exiting worker %s, type %s"%(self._name, self._type))

  def is_active(self):
    """Return True is this worker is active

    Returns:
      active: Worker active status
    """
    return self._is_active

  def _execute_task(self, task):
    """
    Execute task

    Args:
      task(task): Task

    Raises:
      exception: Task Exception
    """
    target = task.pop("target")
    try:
      target.run()
    except Exception as err:
      ERROR("Worker %s (type : %s), hit exception while executing task : %s,"
            "Err : (%s) %s"%(self._name, self._type, target, type(err), err))
      self._is_active = False
      raise

  def _get_task(self):
    """
    get task from worker queues to execute

    Returns:
      task: Task from worker queue to execute

    Raises:
      exception: Task Exception
    """
    try:
      return self._task_manager._get_task(self._type) # pylint: disable=protected-access
    except Exception as err:
      if "Timeout" in str(err):
        return None
      ERROR("Worker %s (type : %s), hit exception while getting task : %s"
            %(self._name, self._type, err))
      self._is_active = False
      raise
