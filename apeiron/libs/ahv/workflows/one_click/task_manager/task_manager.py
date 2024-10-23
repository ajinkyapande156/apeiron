"""
Copyright (c) 2022 Nutanix Inc. All rights reserved.

Author: vedant.dalal@nutanix.com
"""

import time
import datetime
from queue import Queue
from threading import Thread, RLock

from framework.lib.nulog import INFO, ERROR, WARN, DEBUG
from libs.ahv.workflows.one_click.task_manager.task \
  import Task
from libs.ahv.workflows.one_click.task_manager.worker \
  import Worker

class TaskManager():
  """
  Class to define Task Manager methods.
  """
  def __init__(self, quotas=None, worker_poolsize=10, timeout=7200):
    """
    Constructor Method.

    Args:
      quotas(dict): Details on task distribution.
      worker_poolsize(int): number of threads to distribute among tasks.
                            Only if perc of worker given instead of num_workers
      timeout(int): Timeout for worker to die
    """
    self._poolsize = worker_poolsize
    self._tasks_poolsize = 0 #Not supported yet
    self._timeout = timeout
    self._quotas = quotas
    self._init_taskid_based_workers()
    self._queues = {}
    self._time_to_exit = False
    self._lock = RLock()
    self._workers_initialized = False
    self.init_workers(self._poolsize)
    self._task_id_tasks = []
    self._do_not_accept_more_tasks = False

  def init_workers(self, poolsize=0):#pylint: disable=inconsistent-return-statements
    """
    Initialize workers

    Args:
      poolsize(int): Pool size.

    Returns:
      False if workers cannot be initialized.
    """
    if self._workers_initialized:
      ERROR("All workers are already initialized. Extending pool size is not "
            "supported yet")
      return False
    if poolsize < 0 and self._poolsize < 0:
      ERROR("Pool size is given as 0, can not initialize workers. "
            "Min value should be 1")
      return False
    if poolsize > 0:
      self._poolsize = poolsize
    self._init_workers()
    self._workers_initialized = True

  def add(self, target, task_id_based_task=False, **kwargs):#pylint: disable=inconsistent-return-statements
    """
    Method to add target Method and Args

    Args:
      target(func): Target Function Name.
      task_id_based_task(bool): Task ID based Task.

    Returns:
      rask: Task

    Raises:
      Exception
    """
    if self._time_to_exit or self._do_not_accept_more_tasks:
      target_name = target.__name__ if hasattr(target, "__name__") else target
      ERROR("Ignoring task : %s, ExitMarker : %s, DoNotAcceptTaskMarker : %s"
            %(target_name, self._time_to_exit, self._do_not_accept_more_tasks))
      return
    if task_id_based_task:
      return self._add_taskid_task(target, **kwargs)
    timeout = kwargs.pop("timeout", self._timeout)
    interval = kwargs.pop("retry_interval", 1)
    quota_type = kwargs.pop("quota_type")
    queue = self._queues[quota_type]
    task = Task(target, **kwargs)
    while timeout > 0:
      if self._time_to_exit:
        INFO("Exit is called, marking %s as no-op, Type : %s"
             %(target, quota_type))
        return
      try:
        queue.put({"target":task}, timeout=1)
        return task
      except:# pylint: disable=bare-except
        pass
      time.sleep(interval)
      timeout -= interval
    raise Exception("Timeout while adding task : %s, Type : %s"
                    %(target, quota_type))

  def complete_run(self, wait_for_inflight_tasks_to_schedule=True, # pylint: disable=invalid-name
                   wait_time=1, timeout=600):
    """Complete the run

    Args:
      wait_for_inflight_tasks_to_schedule(bool): Boolean to wait for inflight
                                                 tasks to schedule.
      timeout(int): Timeout in seconds.
      wait_time(int): Wati time for sleep.
    """
    INFO("Complete run is called. Setting TaskManager EXIT-MARKER=TRUE."
         " Prepare to exit")
    stime = time.time()
    self._do_not_accept_more_tasks = True
    self._are_all_queues_empty(wait_for_inflight_tasks_to_schedule, timeout)
    self._time_to_exit = True
    workers = self.get_active_workers()
    while time.time()-stime < timeout:
      DEBUG("Number of active workers : %s"%(workers))
      if workers["total_count"] < 1:
        break
      time.sleep(wait_time)
      workers = self.get_active_workers()
    num_ongoing_taks = self._are_all_queues_empty(False)
    INFO("Exiting from TaskManager.Num workers alive : %s, In flight Tasks : %s"
         %(workers, num_ongoing_taks))

  def get_active_workers(self, quota_type=None):
    """Get details on all active workers.

    Args:
      quota_type(str): Quota Type.

    Returns:
      res(dict): Dict on all active workers
    """
    res = {"total_count":0}
    quota_types = [quota_type]
    if not quota_type:
      quota_types = self._quotas.keys()
    for quota_type in quota_types:#pylint: disable=redefined-argument-from-local
      count = 0
      for thrd in self._quotas[quota_type]["threads"]:
        if thrd.is_alive():
          count += 1
          res["total_count"] += 1
      res[quota_type] = count
    return res

  def size(self):
    """
    Get size of thread pool.

    Returns:
      poolsize(int): Pool Size
    """
    return self._poolsize

  def _init_taskid_based_workers(self):
    """
    Initialize taskid based workers
    """
    if not self._quotas:
      if self._tasks_poolsize > 0:
        self._quotas = {"task_workers" : {"num_workers": 1}}
    elif self._tasks_poolsize > 0:
      self._quotas["task_workers"] = {"num_workers": 1}

  def _call_back(self, target, **kwargs): # pylint: disable=no-self-use
    """
    Callback function.

    Args:
      target(func): Target Function Name.

    Returns:
      target: Target Method
    """
    return target(**kwargs)

  def _add_taskid_task(self, target, **kwargs):#pylint: disable=inconsistent-return-statements
    """
    Method to add Task ID Task.

    Args:
      target(func): Target Function Name.

    Returns:
      task: task

    Raises:
      Exception
    """
    timeout = kwargs.pop("timeout", self._timeout)
    interval = kwargs.pop("retry_interval", 1)
    wait_for_task_method = kwargs.pop("wait_for_task_method")
    quota_type = "task_workers"
    queue = self._queues[quota_type]
    while timeout > 0:
      if self._time_to_exit:
        INFO("Exit is called, marking %s as no-op, Type : %s"
             %(target, quota_type))
        return
      if self._is_free_slot_available_for_task():
        task = Task(target, wait_for_task_method, **kwargs)
        try:
          queue.put({"target":task}, timeout=1)
          self._task_id_tasks[task] = {"start_time":datetime.datetime.now()}# pylint: disable=invalid-sequence-index
          return task
        except: # pylint: disable=bare-except
          #For any reason if we fail to put task in queue, just retry
          pass
      else:
        self._find_free_slot_for_task()
      timeout -= interval
      time.sleep(interval)
    raise Exception("Timeout while adding task : %s, Type : %s"
                    %(target, quota_type))

  def _is_free_slot_available_for_task(self):
    """
    Method to check if free slot available for task.

    Returns:
      Bool: True/False based on slot availability
    """
    with self._lock:
      if len(self._task_id_tasks) < self._tasks_poolsize:
        return True
    return False

  def _find_free_slot_for_task(self):
    """
    Method to find free slots for task

    Returns:
      Free slot if available
    """
    tasks = self._task_id_tasks.keys() # pylint: disable=no-member
    for task in tasks:
      if task.isrunning:
        continue
      with self._lock:
        self._task_id_tasks.pop(task)
      return

  def _are_all_queues_empty(self, wait_for_queues_to_empty=True, timeout=600,
                            interval=0.2):
    """
    Method to check if all queues are empty.

    Args:
      wait_for_queues_to_empty(bool): Boolean to wait for queues to empty.
      timeout(int): Timeout in seconds.
      interval(int): Interval for sleep.

    Returns:
      queue_length(int): Length of the Queue.
    """
    INFO("Checking if all queues are empty. wait_for_queues_to_empty : %s"
         %wait_for_queues_to_empty)
    etime = time.time()+timeout
    queue_length = 0
    while etime-time.time() > 0:
      queue_length = 0
      for queue_name, queue in self._queues.items(): # pylint: disable=unused-variable
        if queue.qsize() > 0:
          queue_length += queue.qsize()
          break
      if queue_length < 1:
        return 0
      if not wait_for_queues_to_empty:
        ERROR("Not all workers queues are empty. Total Tasks in Queue : %s"
              %queue_length)
        return queue_length
      time.sleep(interval)
    ERROR("Hit timeout after %s, while waiting for queues to be empty. Current "
          "queue size : %s"%(timeout, queue_length))
    return queue_length


  def _assign_workers(self):
    """Create worker and assign thread to run it
    """
    total_workers = 0
    pool_size = self._poolsize+0
    for key in self._quotas.keys():
      num_workers = qlength = 0
      quota = self._quotas[key]
      if quota.get("perc", 0) > 0:
        num_workers = (quota["perc"] * self._poolsize)/100
      elif quota.get("num_workers", 0) > 0:
        num_workers = quota.get("num_workers")
      else:
        WARN("Num worker allocated to %s is less than 1, allocating atleast 1 "
             "worker"%(key))
        num_workers = 1
      if pool_size < 1 and num_workers > 1:#pylint: disable=chained-comparison
        INFO("Not enough workers left in pool for %s. Current pool size : %s, "
             "workers defined to workoad : %s. Allocating atleast one worker"
             %(key, pool_size, num_workers))
        num_workers = 1
      elif pool_size > 0:
        if num_workers > pool_size:
          ERROR("Num workers defined for workload %s is %s, which is greater "
                "than pool size : %s. Taking min of both"%(key, num_workers,
                                                           pool_size))
          num_workers = min(num_workers, pool_size)
        pool_size -= num_workers
      pool_size # pylint: disable=pointless-statement
      qlength = num_workers*2
      total_workers = total_workers + num_workers
      quota["num_workers"] = num_workers
      self._quotas[key] = quota
      INFO("Creating queue for workload : %s, with quota : %s, Queuesize : %s"
           %(key, quota, qlength))
      queue = Queue(qlength)
      self._queues[key] = queue
    free_threads = self._poolsize - total_workers
    INFO("Total workers created : %s, Queue : %s, Quotas : %s"
         %(total_workers, total_workers*2, self._quotas))
    if free_threads > 0:
      #TODO add free threads to generic pool # pylint: disable=fixme
      pass

  def _get_task(self, worker_type, timeout=None):
    """Get task to execute based on worker type. If task is found in given queue
      created for worker, then execute else just retry to pop task from queue
      after 0.1 second

      Args:
        worker_type(str): Worker Type.
        timeout(int): Timeout in seconds.

      Returns:
        task: Task to execute.
    """
    stime = time.time()
    while not self._time_to_exit:
      if self._queues[worker_type].empty():
        time.sleep(0.1)
        continue
      try:
        with self._lock:
          task = self._queues[worker_type].get(timeout=0.1)
          return task
      except Exception as err: # pylint: disable=broad-except
        ERROR("Failed to get item from Queue : %s"%(worker_type))
        if timeout and (stime-time.time() > timeout):
          raise Exception("Timeout")
        continue
    while not self._queues[worker_type].empty():
      INFO("Emptying workload:%s Queue"%(worker_type))
      try:
        self._queues[worker_type].get(timeout=1)
      except Exception as err: # pylint: disable=broad-except
        ERROR("Failed to empty Queue : %s. Error : %s" %(worker_type, err))
        continue

  def _init_workers(self):
    """Init worker threads
    """
    self._assign_workers()
    for quota_type in self._quotas.keys():
      INFO("Creating workers for : %s workload, with args : %s"
           %(quota_type, self._quotas[quota_type]))
      num_workers = self._quotas[quota_type]["num_workers"]
      threads = []
      for i in range(num_workers):
        worker_name = "%sWorkerThread %s"%(quota_type.title(), i)
        wthread = self._start_worker(quota_type, worker_name, True)
        threads.append(wthread)
      self._quotas[quota_type]["threads"] = threads

  def _start_worker(self, quota_type, worker_name, daemon, retries=3):
    """Start worker

    Args:
      quota_type(str): Quota Type.
      worker_name(str): Worker Name.
      daemon(bool): Daemon.
      retries(int): Number of Retries.

    Returns:
      wthread(thread): Thread
    """
    while retries > 0:
      retries -= 1
      try:
        initworker = Worker(self, quota_type, worker_name)
        wthread = Thread(target=initworker.execute)
        wthread.name = worker_name
        wthread.daemon = daemon
        wthread.start()
        return wthread
      except KeyError as kerr:
        ERROR("Failed to start the worker %s, Retries left : %s, Error : %s"
              %(worker_name, retries, str(kerr)))
        if retries == 0:
          raise
