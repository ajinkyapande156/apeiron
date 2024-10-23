"""
Copyright (c) 2022 Nutanix Inc. All rights reserved.

Author: vedant.dalal@nutanix.com
"""

import uuid
import datetime

from libs.ahv.workflows.one_click.task_manager.\
  constants import Constants

class Task():
  """
  A class containing methods to TASK module
  """
  def __init__(self, task, taskname=Constants.UNKNOWWN,
               wait_for_task_method=None, **kwargs):
    """
    Constructor Method

    Args:
      task(str): Task
      taskname(str): Taskname
      wait_for_task_method(bool): Wait for Task Method
    """
    self._task = task
    self._taskname = taskname
    self._kwargs = kwargs
    self._uuid = uuid.uuid4().hex
    self._state = Constants.INITIALIZED
    self._start_time = datetime.datetime.now()
    self._result = None
    self._exception = None
    self._wait_for_task_method = wait_for_task_method

  @property
  def start_time(self):
    """
    A method to initiate the Task start time.

    Returns:
      self._start_time(date): Start Time
    """
    return self._start_time

  @property
  def run_time(self):
    """
    A method to calculate the run time of Task.

    Returns:
      run_time(date): Task Run Time
    """
    return datetime.datetime.now() - self._start_time

  @property
  def is_long_running_task(self):
    """
    A method to check Long Running task.

    Returns:
      long_running_task(bool): Long Running Task
    """
    return self._long_running_task # pylint: disable=no-member

  @property
  def isbackground(self):
    """
    A method to check the Task background.

    Returns:
      background(n/a): Task Background
    """
    return self._background # pylint: disable=no-member

  @property
  def name(self):
    """
    A method to set the Task name.

    Returns:
      task_name(str): Task Name
    """
    if self._taskname:
      return self._taskname
    if hasattr(self._task, "__name__"):
      return self._task.__name__
    return Constants.UNKNOWWN

  @property
  def uuid(self):
    """
    A method to fetch the Task UUID.

    Returns:
      uuid(uuid): Task UUID
    """
    return self._uuid

  @property
  def status(self):
    """
    A method to fetch the task status.

    Returns:
      state(str): Task Status
    """
    return self._state

  @property
  def isrunning(self):#pylint: disable=inconsistent-return-statements
    """
    A method to check if task is running.

    Returns:
      is_running(bool): Is Task Running
    """
    if not self._wait_for_task_method:
      return self._state == Constants.RUNNING
    task_status = self._wait_for_task_method(self._result)
    self._state == task_status # pylint: disable=pointless-statement
    if task_status == Constants.RUNNING:
      return True

  def stop(self):
    """
    A method to stop the Task
    """
    #TODO : Implement this # pylint: disable=fixme
    pass #pylint: disable=unnecessary-pass

  def result(self):
    """
    A method to fetch the Task Result.

    Returns:
      result(str): Task Result
    """
    return self._result

  def task_exception(self):
    """
    A method to return the Task Exception

    Returns:
      exception(str): Task Exception
    """
    return self._exception

  def run(self):
    """
    A method to run the Task

    Returns:
      result(str): Task Status after run

    Raises:
      exception(str): Task Exception
    """
    self._state = Constants.STARTED
    try:
      self._state = Constants.RUNNING
      res = self._task(**self._kwargs)
      self._state = Constants.COMPLETED
      self._result = res
      return self._result
    except Exception as err:
      self._exception = err
      self._state = Constants.FAILED
      raise
