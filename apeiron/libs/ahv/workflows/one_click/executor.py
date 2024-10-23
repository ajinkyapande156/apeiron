#pylint: disable=too-many-lines
"""
Copyright (c) 2021 Nutanix Inc. All rights reserved.

Author: vedant.dalal@nutanix.com
"""
from datetime import datetime, timedelta
import time
import json
import copy
import sys
import os
import traceback

from threading import RLock

from framework.lib.nulog import INFO, STEP, ERROR
from libs.ahv.workflows.one_click \
  import metadata
from libs.ahv.workflows.one_click.jarvis_client \
  import JarvisClient
from libs.ahv.workflows.one_click.jita_v2_client \
  import JitaClient
from libs.ahv.workflows.one_click.payload_generator \
  import PayloadGenerator
from libs.ahv.workflows.one_click.args_manipulator \
  import ArgsManipulator
from libs.ahv.workflows.one_click.deployment_manager \
  import DeploymentManager
from libs.ahv.workflows.one_click.emailer \
  import Emailer
from libs.ahv.workflows.one_click.rdm_client \
  import RDMClient
from libs.ahv.workflows.one_click.pu_test_generator \
  import PostUpgradeGenerator
from libs.ahv.workflows.one_click import database
from libs.ahv.workflows.one_click.elk_client \
  import ELKClient


class Executor:
  """
  A class containing methods to execute the Upgrade and Deployment Suite.
  """
  def __init__(self):
    """
    Constructor Method
    """
    self._global_lock = RLock()
    self.payload_generator = PayloadGenerator()
    self.args_manipulator = ArgsManipulator()
    self.deployment_path = DeploymentManager()
    self.jarvis = JarvisClient(username="svc.ahv-qa",
                               password="6TcU84qZiZHTvFu!#jDD")
    self.jita = JitaClient(username="svc.ahv-qa",
                           password="6TcU84qZiZHTvFu!#jDD")
    self.objects_jita = JitaClient(username="svc.merit",
                                   password="ktqbF*cp+m9wjx8SPT2h")
    self.ndk_jita = JitaClient(
      username="svc-ndk-qa",
      password="+fwWa?Q%NkB*Gr3cngY6"
    )
    self.emailer = Emailer()
    self.cluster_name = "auto_cluster_prod_svc_ahv_qa_4f2090dce2c8"
    self.db_conn = ELKClient(
      username="elastic",
      password="sa.Z<FPnvRODb_^-"
    )
    self.elk_db_name = "one_click_db"
    self.pu_generator = PostUpgradeGenerator()
    self.JP_CLONER_MAP = {#pylint:disable=invalid-name
      "ahv_upgrade": self._clone_job_profile,
      "ahv_aos_upgrade": self._clone_job_profile,
      "deployment_path": self._clone_job_profile,
      "csi_functional_qual": self._clone_job_profile_msp,
      "csi_error_injection": self._clone_job_profile_msp,
      "multi_level_ahv_upgrade": self._clone_job_profile,
      "ngd_ahv_upgrade": self._clone_job_profile,
      "ngd_ahv_aos_upgrade": self._clone_job_profile,
      "guest_os_qual": self._clone_gos_job_profile,
      "pxe": self._clone_gos_job_profile,
      "virtio": self._clone_gos_job_profile,
      "gos_upgrade": self._clone_gos_job_profile
    }

    self.FEAT_PRODUCT_CLONER_MAP = {#pylint:disable=invalid-name
      "csi": self._clone_job_profile_msp,
      "objects": self._clone_job_profile_msp,
      "ndk": self._clone_job_profile_msp,
      "ahv": self._clone_job_profile
    }

    self.JITA_PRODUCT_MAP = {#pylint:disable=invalid-name
      "csi": self.ndk_jita,
      "ahv": self.jita,
      "objects": self.objects_jita,
      "msp": self.jita,
      "ndk": self.ndk_jita
    }

    self.rdm = RDMClient(
      username="svc.ahv-qa",
      password="6TcU84qZiZHTvFu!#jDD"
    )
    self.merit_rdm = RDMClient(
      username="svc.merit",
      password="ktqbF*cp+m9wjx8SPT2h"
    )

    self.RDM_PRODUCT_MAP = {#pylint:disable=invalid-name
      "csi": self.rdm,
      "ahv": self.rdm,
      "objects": self.merit_rdm,
      "msp": self.rdm,
      "ndk": self.rdm
    }

  def clone_and_execute_job_and_send_mail(self, headers, jobs, action, #pylint: disable=too-many-locals,too-many-branches,too-many-statements
                                          out_key, in_key, batch_size=1):
    """
    Method to Clone and Execute the Job Profile, and then Poll the
    triggered task.

    Args:
      headers(list): List of headers for matrix
      jobs(json): Jobs JSON for the particular run
      out_key(str): Outer Loop key in Matrix Dict
      in_key(str): Inner Loop key in Matrix Dict
      action(str): Action to be performed
                   (One of "ahv_upgrade", "ahv_aos_upgrade", "deployment_path")
      batch_size(int): Batch size to be executed together

    Returns
    """
    if (not (database.matrices[str(action)][str(out_key)]
             [str(in_key)].get("Status")) or
        (database.matrices[str(action)][str(out_key)][str(in_key)]
         ["Status"]) != "completed"):
      try: #pylint: disable=too-many-nested-blocks
        if database.matrices[action][str(out_key)][str(in_key)].get("Feat"):
          INFO("Feat: "+str(database.matrices[action][str(out_key)]
                            [str(in_key)]["Feat"]))
        for source_key in (database.matrices[action][str(out_key)]
                           [str(in_key)]).keys():
          if "Source_" in source_key:
            INFO(str(source_key).replace("_", " ")+": "+
                 str(database.matrices[action][str(out_key)][str(in_key)]
                     [source_key]))

        with self._global_lock:
          if (jobs.get("feat_execution_") and
              (database.matrices[action][str(out_key)]
               [str(in_key)].get("specific_pool_name"))):
            if (database.matrices[action][str(out_key)]
                [str(in_key)].get("specific_pool_name")) != "":
              jobs.update({
                "pool_name": (database.matrices[action][str(out_key)]
                              [str(in_key)].get("specific_pool_name"))
              })
          index_name = "one_click_db"
          if "csi" in action:
            index_name = "csi_apeiron_db"
            self.JP_CLONER_MAP.update({
              action: self.FEAT_PRODUCT_CLONER_MAP["csi"]
            })
          if "ndk" in action:
            index_name = "ndk_apeiron_db"
            self.JP_CLONER_MAP.update({
              action: self.FEAT_PRODUCT_CLONER_MAP["ndk"]
            })
          if jobs.get("product") == "ahv" and jobs.get("feat_execution_"):
            index_name = "one_click_db"
            self.JP_CLONER_MAP.update({
              action: self.FEAT_PRODUCT_CLONER_MAP["ahv"]
            })
          if "objects" in action:
            index_name = "objects_apeiron_db"
            self.JP_CLONER_MAP.update({
              action: self.FEAT_PRODUCT_CLONER_MAP["objects"]
            })
          for index in range(int(in_key), int(in_key)+batch_size):
            database.matrices[action][str(out_key)][str(index)].update(
              {
                "jobs": jobs
              }
            )

        if (not jobs.get("enable_direct_pool_execution") and not
            (database.matrices[action][str(out_key)]
             [str(in_key)]).get("enable_direct_pool_execution")):
          STEP("Deployment Manager Initiated.")
          deployment_path = DeploymentManager()
          self.cluster_name = deployment_path.resource_manager(
            jobs=copy.deepcopy(jobs),
            action=copy.deepcopy(action),
            out_key=copy.deepcopy(str(out_key)),
            in_key=copy.deepcopy(str(in_key))
          )
        else:
          self.cluster_name = "direct_pool_execution"
        with self._global_lock:
          for index in range(int(in_key), int(in_key)+batch_size):
            database.matrices[action][str(out_key)][str(index)].update(
              {
                "Start_Time": datetime.now().strftime("%d-%m-%Y %H:%M:%S")
              }
            )

        if self.cluster_name is not None:
          INFO(f"skip_reimaging val: {jobs.get('skip_reimaging')}")
          skip_reimaging = jobs.get("skip_reimaging")
          # If jobs has pool_execution param
          pool_exec = jobs.get("enable_direct_pool_execution")
          # If the action requires pool execution
          action_pool_exec = (
            database.matrices[action][str(out_key)][str(in_key)]
            .get("enable_direct_pool_execution")
          )
          if not skip_reimaging and not pool_exec and not action_pool_exec:
            self.cluster_name = deployment_path.deployment_manager(
              jobs=copy.deepcopy(jobs),
              action=copy.deepcopy(action),
              out_key=copy.deepcopy(str(out_key)),
              in_key=copy.deepcopy(str(in_key)),
              batch_size=batch_size,
              cluster_name=copy.deepcopy(self.cluster_name)
            )
          INFO(f"Cluster name: {self.cluster_name}")
          if self.cluster_name is None:
            ERROR("Unable to deploy a cluster")
            self.emailer.send_mail(
              out_key=copy.deepcopy(str(out_key)),
              in_key=copy.deepcopy(str(in_key)),
              action=copy.deepcopy(action),
              mail_type=copy.deepcopy("end")
            )
          else:
            with self._global_lock:
              for index in range(int(in_key), int(in_key)+batch_size):
                database.matrices[action][str(out_key)][str(index)].update({
                  "cluster_name": self.cluster_name
                })

            if (jobs.get("pc_enabled") and
                not jobs.get("enable_direct_pool_execution") and not
                (database.matrices[action][str(out_key)]
                 [str(in_key)]).get("enable_direct_pool_execution")):
              with self._global_lock:
                jobs.update({
                  "cluster_ip": self.cluster_name,
                  "cluster_details": {
                    "cluster_pc_ip": (database.resource_manager[
                      self.cluster_name
                    ].get("pc_name"))
                  }
                })

            self._update_db_with_local(
              index_name=index_name
            )

            STEP("Check if any pre-upgrade tests to be executed.")
            if action not in metadata.IGNORE_PRE_POST_UPGRADE:
              user_ts = None
              disable_bucket = False
              if "pre_upgrade_ts" in jobs.keys():
                user_ts = jobs["pre_upgrade_ts"]

                if (("Pre Upgrade Result" not in headers) and
                    ("Pre Upgrade Jita URL" not in headers)):
                  headers.extend(
                    metadata.PRE_POST_UPGRADE_HEADERS["pre_upgrade"]
                  )

              if jobs.get("disable_pu_bucket"):
                disable_bucket = True
              INFO("disable_var: "+str(disable_bucket))
              self._pre_and_post_upgrade_executor(
                jobs=jobs,
                action=action,
                in_key=in_key,
                out_key=out_key,
                _batch_size=batch_size,
                upgrade_action="pre_upgrade",
                disable_bucket=disable_bucket,
                user_ts=user_ts
              )

            STEP("Clone the given Job Profile.")
            if action in metadata.IGNORE_IMAGING_ACTIONS:
              upgrade_var = []
              for index in range(int(in_key), int(in_key)+batch_size):
                upgrade_var.append(copy.deepcopy(database.matrices[action]
                                                 [str(out_key)][str(index)]))
            else:
              upgrade_var = copy.deepcopy(database.matrices[action]
                                          [str(out_key)][str(in_key)])
            job_profile_name = self.JP_CLONER_MAP.get(
              action, self._clone_job_profile
            )(
              jobs=copy.deepcopy(jobs),
              upgrade_dict=upgrade_var,
              action=copy.deepcopy(action)
            )

            STEP("Fetch Job profile ID.")
            job_prof_id = self.JITA_PRODUCT_MAP[
              jobs.get("product")
            ].get_job_profile_id(
              copy.deepcopy(job_profile_name)
            )

            INFO("Job Profile ID: %s" % job_prof_id)

            if job_prof_id is None:
              with self._global_lock:
                for index in range(int(in_key), int(in_key)+batch_size):
                  database.matrices[action][str(out_key)][str(index)].update({
                    "Result": "Not Executed",
                    "Reason": "Unable to clone job profile.",
                    "Status": "pending"
                  })

              self.emailer.send_mail(
                out_key=copy.deepcopy(str(out_key)),
                in_key=copy.deepcopy(str(in_key)),
                action=copy.deepcopy(action),
                mail_type=copy.deepcopy("end")
              )

              self._update_db_with_local(
                index_name=index_name
              )

            else:
              STEP("Trigger the Job Profile.")
              task_id = self.JITA_PRODUCT_MAP[jobs.get(
                "product", self.jita
              )].task_trigger(
                job_prof_id
              )

              if task_id is None:
                with self._global_lock:
                  for index in range(int(in_key), int(in_key)+batch_size):
                    database.matrices[action][str(out_key)][str(index)].update({
                      "Result": "Not Executed",
                      "Reason": "Unable to Trigger job profile.",
                      "Status": "pending"
                    })

                self.emailer.send_mail(
                  out_key=copy.deepcopy(str(out_key)),
                  in_key=copy.deepcopy(str(in_key)),
                  action=copy.deepcopy(action),
                  mail_type=copy.deepcopy("end")
                )

                self._update_db_with_local(
                  index_name=index_name
                )
              else:

                with self._global_lock:
                  for index in range(int(in_key), int(in_key)+batch_size):
                    database.matrices[action][str(out_key)][str(index)].update({
                      "Jita_URL": (metadata.TEST_REPORT_URL
                                   +str(task_id))
                    })

                self.emailer.send_mail(
                  out_key=copy.deepcopy(str(out_key)),
                  in_key=copy.deepcopy(str(in_key)),
                  action=copy.deepcopy(action),
                  mail_type=copy.deepcopy("start")
                )

                self._update_db_with_local(
                  index_name=index_name
                )

                STEP("Poll the triggered Job Profiles.")
                _is_task_completed = self._poll_task(
                  jobs=jobs,
                  task_id=copy.deepcopy(task_id),
                  no_of_retries=copy.deepcopy(int(jobs["no_of_retries"])),
                  retry_interval=copy.deepcopy(int(jobs["retry_interval"])),
                  action=action,
                  in_key=in_key,
                  out_key=out_key,
                  batch_size=batch_size,
                  index_name=index_name
                )

                if _is_task_completed:
                  test_result_count = (
                    self.JITA_PRODUCT_MAP[
                      jobs.get("product", self.jita)
                    ].get_agave_test_result_count(
                      task_id=task_id
                    )
                  )
                  with self._global_lock:
                    if test_result_count is not None:
                      for index in range(int(in_key), int(in_key)+batch_size):
                        (database.matrices[action][str(out_key)]
                         [str(index)].update({
                           "test_result_count": test_result_count
                         }))
                    for index in range(int(in_key), int(in_key)+batch_size):
                      (database.matrices[action][str(out_key)]
                       [str(index)]).update({
                         "End_Time": datetime.now().strftime(
                           "%d-%m-%Y %H:%M:%S"
                         )
                       })
                  _result_dict = self._update_result(
                    jobs=jobs,
                    task_id=copy.deepcopy(task_id),
                    stime=copy.deepcopy(database.matrices[action][str(out_key)]
                                        [str(in_key)]["Start_Time"]),
                    etime=copy.deepcopy(database.matrices[action][str(out_key)]
                                        [str(in_key)]["End_Time"]),
                    platform_name=copy.deepcopy(database.matrices[action]
                                                [str(out_key)]
                                                [str(in_key)]["Platform"])
                  )
                  with self._global_lock:
                    for index in range(int(in_key), int(in_key)+batch_size):
                      if action in ["guest_os_qual", "pxe", "virtio",
                                    "gos_upgrade"]:
                        gos_result = self._update_gos_result(
                          in_key=str(index),
                          out_key=str(out_key),
                          action=action
                        )
                        _result_dict.update({
                          "Result": gos_result[0],
                          "Reason": gos_result[1]
                        })
                      (database.matrices[action][str(out_key)]
                       [str(index)]).update(
                         _result_dict
                       )

                else:
                  self._update_db_with_local(
                    index_name=index_name
                  )
                  end_time = datetime.strptime(
                    datetime.now().strftime("%d-%m-%Y %H:%M:%S"),
                    "%d-%m-%Y %H:%M:%S"
                  )
                  start_time = datetime.strptime(
                    (database.matrices[action][str(out_key)][str(in_key)]
                     ["Start_Time"]),
                    "%d-%m-%Y %H:%M:%S"
                  )
                  total_time = str(timedelta(seconds=int(
                    (end_time - start_time).total_seconds()
                  )))
                  with self._global_lock:
                    for index in range(int(in_key), int(in_key)+batch_size):
                      (database.matrices[action][str(out_key)]
                       [str(index)]).update({
                         "End_Time": datetime.now().strftime(
                           "%d-%m-%Y %H:%M:%S"
                         ),
                         "Total_Time": total_time,
                         "Status": "Pending",
                         "Result": "Pending"
                       })

                self.emailer.send_mail(
                  out_key=copy.deepcopy(str(out_key)),
                  in_key=copy.deepcopy(str(in_key)),
                  action=copy.deepcopy(action),
                  mail_type=copy.deepcopy("end")
                )
                if jobs.get("preserve_cluster_on_failure"):
                  if ((database.matrices[action][str(out_key)][str(in_key)]
                       ["Result"] == "Failed") and action not in
                      metadata.IGNORE_IMAGING_ACTIONS):
                    if (database.matrices[action][str(out_key)]
                        [str(in_key)].get("Reason")):
                      for reason in metadata.PRESERVE_ON_FAILURE_REASONS:
                        if (reason in database.matrices[action][str(out_key)]
                            [str(in_key)].get("Reason")):
                          with self._global_lock:
                            (database.resource_manager
                             [self.cluster_name]).update({
                               "preserve_cluster": True
                             })
                STEP("Check if the action needs Post Upgrade"
                     " and if "+action+" Succeeded")
                user_ts = None
                action_res = (database.matrices[action][str(out_key)]
                              [str(in_key)]["Result"])
                if (action_res in ["Succeeded", "Warning"] and action not in
                    metadata.IGNORE_PRE_POST_UPGRADE):
                  STEP("Check if Post Upgrade Test to be executed.")
                  if "post_upgrade_ts" in jobs.keys():
                    user_ts = jobs["post_upgrade_ts"]

                    if (("Post Upgrade Result" not in headers) and
                        ("Post Upgrade Jita URL" not in headers)):
                      headers.extend(
                        metadata.PRE_POST_UPGRADE_HEADERS["post_upgrade"]
                      )

                  if ("disable_pu_bucket" in jobs.keys() and
                      jobs["disable_pu_bucket"]):
                    if (("Post Upgrade Result" not in headers) and
                        ("Post Upgrade Jita URL" not in headers)):
                      headers.extend(
                        metadata.PRE_POST_UPGRADE_HEADERS["post_upgrade"]
                      )
                    disable_bucket = True

                  self._pre_and_post_upgrade_executor(
                    jobs=jobs,
                    action=action,
                    in_key=in_key,
                    out_key=out_key,
                    upgrade_action="post_upgrade",
                    user_ts=user_ts,
                    _batch_size=batch_size,
                    disable_bucket=disable_bucket
                  )
                        # else:
                        #   STEP("Post Upgrade Test will not
                        # be initiated, because Result is "
                        #        +str(database.matrices[action]
                        # [str(out_key)][str(in_key)]
                        #             ["Result"]))
              self.teardown(job_prof_id=job_prof_id, jobs=jobs)
        else:
          database.matrices[action][str(out_key)][str(index)].update({
            "Result": "Skipped",
            "Reason": ("Unable to proceed as all clusters are preserved"
                       " on failure."),
            "Status": "pending"
          })

        _print_list = self.args_manipulator.json_to_list_converter(
          upgrade_dict=database.matrices[action],
          headers=copy.deepcopy(headers)
        )
        self.args_manipulator.log_matrix_printer(
          headers=copy.deepcopy(headers),
          print_list=copy.deepcopy(_print_list)
        )

        if (database.resource_manager.get(self.cluster_name) and
            database.resource_manager[self.cluster_name].get(
              "deployment_to_release") and
            action not in metadata.IGNORE_IMAGING_ACTIONS):
          self.RDM_PRODUCT_MAP[jobs.get("product")].release_cluster(
            deployment_id=(database.resource_manager[self.cluster_name]
                           ["deployment_to_release"])
          )

        # UPDATE THE DB WITH LATEST EXECUTION
        if action not in metadata.GOS_ACTIONS:
          self._update_db_with_local(
            index_name=index_name
          )
        else:
          for index in range(int(in_key), int(in_key)+batch_size):
            database.matrices[action][str(out_key)][str(index)].update(
              {
                "matrix_start_time": database.matrices["matrix_start_time"]
              }
            )

            self._update_db_with_local(
              index_name=index_name
            )

      except Exception as e: #pylint: disable=bare-except,broad-except,invalid-name
        INFO("Thread hit an Exception. Error: "+str(e))
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        INFO("Exception Type: "+str(exc_type))
        INFO("Exception Filename: "+str(fname))
        INFO("Exception Line no.: "+str(exc_tb.tb_lineno))
        INFO(str(exc_obj))
        # Print the traceback
        ERROR(f"Traceback of exception: \n{traceback.format_exc()}")
        total_time = "N/A"
        end_time = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
        if "Start_Time" in (database.matrices[action][str(out_key)]
                            [str(in_key)].keys()):
          endtime = datetime.strptime(end_time,
                                      "%d-%m-%Y %H:%M:%S")
          starttime = datetime.strptime(
            database.matrices[action][str(out_key)][str(in_key)]["Start_Time"],
            "%d-%m-%Y %H:%M:%S"
          )
          total_time = str(timedelta(seconds=int(
            (endtime - starttime).total_seconds()
          )))
        with self._global_lock:
          for index in range(int(in_key), int(in_key)+batch_size):
            database.matrices[action][str(out_key)][str(index)].update({
              "End_Time": end_time,
              "Total_Time": total_time,
              "Status": "pending",
              "Result": "Failed",
              "Reason": "Thread hit an exception. "\
                        "Please check the 1-click Trigger Logs for details."
            })

      finally:
        if (not jobs.get("enable_direct_pool_execution") and not
            (database.matrices[action][str(out_key)]
             [str(in_key)]).get("enable_direct_pool_execution")):
          if "cluster_name" in (database.matrices[action][str(out_key)]
                                [str(in_key)].keys()):
            with self._global_lock:
              (database.resource_manager
               [(database.matrices[action][str(out_key)][str(in_key)]
                 ["cluster_name"])]["is_available"]) = True
              INFO("Cluster:"+str((database.matrices[action][str(out_key)]
                                   [str(in_key)]["cluster_name"]))+
                   " is made available in Resource Manager")
          elif self.cluster_name is not None:
            with self._global_lock:
              (database.resource_manager[self.cluster_name]
               ["is_available"]) = True
            INFO("Cluster is made available in Resource Manager")

  def msp_pc_executor(self, headers, jobs, action, #pylint: disable=too-many-locals,too-many-branches,too-many-statements
                      out_key, in_key, batch_size=1):
    """
    Method to Clone and Execute the Job Profile, and then Poll the
    triggered task.

    Args:
      headers(list): List of headers for matrix
      jobs(json): Jobs JSON for the particular run
      out_key(str): Outer Loop key in Matrix Dict
      in_key(str): Inner Loop key in Matrix Dict
      action(str): Action to be performed
                   (One of "ahv_upgrade", "ahv_aos_upgrade", "deployment_path")
      batch_size(int): Batch size to be executed together

    Returns
    """
    if (not (database.matrices[str(action)][str(out_key)]#pylint: disable=too-many-nested-blocks
             [str(in_key)]).get("Status") or
        (database.matrices[str(action)][str(out_key)][str(in_key)]
         ["Status"]) != "completed"):
      try: #pylint: disable=too-many-nested-blocks
        cluster_name = None
        job_prof_id = None
        dep_job_prof_id = None
        if database.matrices[action][str(out_key)][str(in_key)].get("Feat"):
          INFO("Feat: "+str(database.matrices[action][str(out_key)]
                            [str(in_key)]["Feat"]))
        for source_key in (database.matrices[action][str(out_key)]
                           [str(in_key)]).keys():
          if "Source_" in source_key:
            INFO(str(source_key).replace("_", " ")+": "+
                 str(database.matrices[action][str(out_key)][str(in_key)]
                     [source_key]))
        with self._global_lock:
          database.matrices[action][str(out_key)][str(in_key)].update(
            {
              "jobs": jobs
            }
          )
        index_name = "msp_apeiron_db"
        if "csi" in action:
          index_name = "csi_apeiron_db"

        if "objects" in action:
          index_name = "objects_apeiron_db"
          self.JP_CLONER_MAP.update({
            action: self.FEAT_PRODUCT_CLONER_MAP["objects"]
          })
          if (jobs.get("feat_execution_") and (not jobs.get("objects_upgrade_")
                                               and not jobs.get(
                                                 "objects_deployment_"
                                               ))):
            metadata.IGNORE_IMAGING_ACTIONS.append(action)

        STEP("Deployment Manager Initiated.")
        deployment_path = DeploymentManager()
        if not jobs.get("enable_direct_pool_execution"):
          cluster_name = deployment_path.resource_manager(
            jobs=copy.deepcopy(jobs),
            action=copy.deepcopy(action),
            out_key=copy.deepcopy(str(out_key)),
            in_key=copy.deepcopy(str(in_key))
          )
        else:
          cluster_name = "direct_pool_execution"
        with self._global_lock:
          database.matrices[action][str(out_key)][str(in_key)].update(
            {
              "Start_Time": datetime.now().strftime("%d-%m-%Y %H:%M:%S"),
              "Deployment_Start_Time": datetime.now().strftime(
                "%d-%m-%Y %H:%M:%S"
              )
            }
          )
        INFO("In_key: "+str(in_key)+". Cluster name"+str(cluster_name))
        if cluster_name is not None:
          INFO(f"skip_reimaging val: {jobs.get('skip_reimaging')}")
          skip_reimaging = jobs.get("skip_reimaging")
          # If jobs has pool_execution param
          pool_exec = jobs.get("enable_direct_pool_execution")
          # If the action requires pool execution
          action_pool_exec = (
            database.matrices[action][str(out_key)][str(in_key)]
            .get("enable_direct_pool_execution")
          )
          if not skip_reimaging and not pool_exec and not action_pool_exec:
            cluster_name = deployment_path.deployment_manager(
              jobs=copy.deepcopy(jobs),
              action=copy.deepcopy(action),
              out_key=copy.deepcopy(str(out_key)),
              in_key=copy.deepcopy(str(in_key)),
              batch_size=batch_size,
              cluster_name=copy.deepcopy(cluster_name)
            )
          if cluster_name is None:
            ERROR("Unable to deploy a cluster")
            self.emailer.send_mail(
              out_key=copy.deepcopy(str(out_key)),
              in_key=copy.deepcopy(str(in_key)),
              action=copy.deepcopy(action),
              mail_type=copy.deepcopy("end")
            )
          else:
            if database.resource_manager[cluster_name].get("pc_name"):
              INFO("PC Name: " +
                   str(database.resource_manager[cluster_name].get("pc_name")))

              with self._global_lock:
                jobs.update({
                  "cluster_ip": cluster_name,
                  "cluster_details": {
                    "cluster_pc_ip": (database.resource_manager[
                      cluster_name
                    ].get("pc_name"))
                  }
                })
            with self._global_lock:
              database.matrices[action][str(out_key)][str(in_key)].update({
                "cluster_name": cluster_name
              })
            if action not in metadata.STATIC_IGNORE_IMAGING_ACTIONS:
              self._update_db_with_local(
                index_name=index_name
              )

            STEP("Deploy MSP and AOSS.")
            INFO(str(database.resource_manager[cluster_name]))
            if (database.matrices[action][str(out_key)]
                [str(in_key)].get("feat_execution")):
              if not database.resource_manager[cluster_name].get(
                  "is_"+jobs.get("product")+"_deployed"
              ):
                self._deployment_trigger(
                  action=action,
                  in_key=in_key,
                  out_key=out_key,
                  jobs=jobs,
                  index_name=index_name,
                  dep_jp=True
                )
              else:
                (database.matrices[action][str(out_key)]
                 [str(in_key)]).update({
                   "Deployment_Result": "Succeeded"
                 })
            else:
              self._deployment_trigger(
                action=action,
                in_key=in_key,
                out_key=out_key,
                jobs=jobs,
                index_name=index_name,
                dep_jp=True
              )

            if ("Failed" not in database.matrices[action][str(out_key)]
                [str(in_key)]["Deployment_Result"]):
              STEP("Update the Resource Manager with Objects Deployed"
                   " if true.")
              if jobs.get("feat_execution"):
                with self._global_lock:
                  database.resource_manager[cluster_name].update({
                    "is_"+jobs.get("product")+"_deployed": True
                  })
              STEP("Check if any pre-upgrade tests to be executed.")
              if action not in metadata.IGNORE_PRE_POST_UPGRADE:
                user_ts = None
                disable_bucket = False
                if "pre_upgrade_ts" in jobs.keys():
                  user_ts = jobs["pre_upgrade_ts"]

                  if (("Pre Upgrade Result" not in headers) and
                      ("Pre Upgrade Jita URL" not in headers)):
                    headers.extend(
                      metadata.PRE_POST_UPGRADE_HEADERS["pre_upgrade"]
                    )

                if ("disable_pu_bucket" in jobs.keys() and
                    jobs["disable_pu_bucket"]):
                  disable_bucket = True
                INFO("disable_var: "+str(disable_bucket))
                self._pre_and_post_upgrade_executor(
                  jobs=jobs,
                  action=action,
                  in_key=in_key,
                  out_key=out_key,
                  _batch_size=batch_size,
                  upgrade_action="pre_upgrade",
                  disable_bucket=disable_bucket,
                  user_ts=user_ts
                )

              STEP("Clone the given Job Profile.")
              upgrade_var = copy.deepcopy(database.matrices[action]
                                          [str(out_key)][str(in_key)])
              job_profile_name = self._clone_job_profile_msp(
                jobs=copy.deepcopy(jobs),
                upgrade_dict=upgrade_var,
                action=action
              )
              # job_profile_name = self._clone_job_profile(
              #   jobs=copy.deepcopy(jobs),
              #   upgrade_dict=copy.deepcopy(database.matrices[action]
              #                              [str(out_key)]
              #                              [str(in_key)]),
              #   action=copy.deepcopy(action)
              # )

              STEP("Fetch Job profile ID.")
              job_prof_id = self.JITA_PRODUCT_MAP[
                jobs.get("product", self.jita)
              ].get_job_profile_id(
                copy.deepcopy(job_profile_name)
              )

              INFO("Job Profile ID: %s" % job_prof_id)

              if job_prof_id is None:
                with self._global_lock:
                  (database.matrices[action][str(out_key)]
                   [str(in_key)]).update({
                     "Result": "Not Executed",
                     "Reason": "Unable to clone job profile.",
                     "Status": "pending"
                   })

                self.emailer.send_mail(
                  out_key=copy.deepcopy(str(out_key)),
                  in_key=copy.deepcopy(str(in_key)),
                  action=copy.deepcopy(action),
                  mail_type=copy.deepcopy("end")
                )
                if action not in metadata.STATIC_IGNORE_IMAGING_ACTIONS:
                  self._update_db_with_local(
                    index_name=index_name
                  )
              else:
                STEP("Trigger the Job Profile.")
                task_id = self.JITA_PRODUCT_MAP[
                  jobs.get("product", self.jita)
                ].task_trigger(job_prof_id)

                if task_id is None:
                  with self._global_lock:
                    (database.matrices[action][str(out_key)]
                     [str(in_key)]).update({
                       "Result": "Not Executed",
                       "Reason": "Unable to Trigger job profile.",
                       "Status": "pending"
                     })

                  self.emailer.send_mail(
                    out_key=copy.deepcopy(str(out_key)),
                    in_key=copy.deepcopy(str(in_key)),
                    action=copy.deepcopy(action),
                    mail_type=copy.deepcopy("end")
                  )
                  if action not in metadata.STATIC_IGNORE_IMAGING_ACTIONS:
                    self._update_db_with_local(
                      index_name=index_name
                    )
                else:

                  with self._global_lock:
                    (database.matrices[action][str(out_key)]
                     [str(in_key)]).update({
                       "Jita_URL": (metadata.TEST_REPORT_URL
                                    +str(task_id))
                     })

                  self.emailer.send_mail(
                    out_key=copy.deepcopy(str(out_key)),
                    in_key=copy.deepcopy(str(in_key)),
                    action=copy.deepcopy(action),
                    mail_type=copy.deepcopy("start")
                  )
                  if action not in metadata.STATIC_IGNORE_IMAGING_ACTIONS:
                    self._update_db_with_local(
                      index_name=index_name
                    )

                  STEP("Poll the triggered Job Profiles.")
                  _is_task_completed = self._poll_task(
                    jobs=jobs,
                    task_id=copy.deepcopy(task_id),
                    no_of_retries=copy.deepcopy(
                      int(jobs["no_of_retries"])
                    ),
                    retry_interval=copy.deepcopy(
                      int(jobs["retry_interval"])
                    ),
                    action=action,
                    in_key=in_key,
                    out_key=out_key,
                    batch_size=batch_size,
                    index_name=index_name
                  )

                  if _is_task_completed:
                    with self._global_lock:
                      (database.matrices[action][str(out_key)]
                       [str(in_key)]).update({
                         "End_Time": datetime.now().strftime(
                           "%d-%m-%Y %H:%M:%S"
                         )
                       })
                    _main_result_dict = self._update_result(
                      jobs=jobs,
                      task_id=copy.deepcopy(task_id),
                      stime=copy.deepcopy(database.matrices[action]
                                          [str(out_key)][str(in_key)]
                                          ["Start_Time"]),
                      etime=copy.deepcopy(database.matrices[action]
                                          [str(out_key)][str(in_key)]
                                          ["End_Time"]),
                      platform_name=copy.deepcopy(database.matrices[action]
                                                  [str(out_key)]
                                                  [str(in_key)]["Platform"])
                    )
                    (database.matrices[action][str(out_key)]
                     [str(in_key)]).update(_main_result_dict)

                  else:
                    if action not in metadata.STATIC_IGNORE_IMAGING_ACTIONS:
                      self._update_db_with_local(
                        index_name=index_name
                      )
                    end_time = datetime.strptime(
                      datetime.now().strftime("%d-%m-%Y %H:%M:%S"),
                      "%d-%m-%Y %H:%M:%S"
                    )
                    start_time = datetime.strptime(
                      (database.matrices[action][str(out_key)]
                       [str(in_key)]["Start_Time"]),
                      "%d-%m-%Y %H:%M:%S"
                    )
                    total_time = str(timedelta(seconds=int(
                      (end_time - start_time).total_seconds()
                    )))
                    with self._global_lock:
                      (database.matrices[action][str(out_key)]
                       [str(in_key)]).update({
                         "End_Time": datetime.now().strftime(
                           "%d-%m-%Y %H:%M:%S"
                         ),
                         "Total_Time": total_time,
                         "Status": "Pending",
                         "Result": "Pending"
                       })

                  self.emailer.send_mail(
                    out_key=copy.deepcopy(str(out_key)),
                    in_key=copy.deepcopy(str(in_key)),
                    action=copy.deepcopy(action),
                    mail_type=copy.deepcopy("end")
                  )
                  if jobs.get("preserve_cluster_on_failure"):
                    if ((database.matrices[action][str(out_key)]
                         [str(in_key)]["Result"] == "Failed") and
                        action not in
                        metadata.STATIC_IGNORE_IMAGING_ACTIONS):
                      if (database.matrices[action][str(out_key)]
                          [str(in_key)].get("Reason")):
                        for reason in metadata.PRESERVE_ON_FAILURE_REASONS:
                          if (reason in database.matrices[action]
                              [str(out_key)][str(in_key)].get("Reason")):
                            with self._global_lock:
                              database.resource_manager[
                                cluster_name
                              ].update({
                                "preserve_cluster": True
                              })
                  STEP("Check if the action needs Post Upgrade"
                       " and if "+action+" Succeeded")
                  user_ts = None
                  action_res = (database.matrices[action][str(out_key)]
                                [str(in_key)]["Result"])
                  if (action_res in ["Succeeded", "Warning"] and action not in
                      metadata.IGNORE_PRE_POST_UPGRADE):
                    STEP("Check if Post Upgrade Test to be executed.")
                    if "post_upgrade_ts" in jobs.keys():
                      user_ts = jobs["post_upgrade_ts"]

                      if (("Post Upgrade Result" not in headers) and
                          ("Post Upgrade Jita URL" not in headers)):
                        headers.extend(
                          metadata.PRE_POST_UPGRADE_HEADERS["post_upgrade"]
                        )

                    if ("disable_pu_bucket" in jobs.keys() and
                        jobs["disable_pu_bucket"]):
                      if (("Post Upgrade Result" not in headers) and
                          ("Post Upgrade Jita URL" not in headers)):
                        headers.extend(
                          metadata.PRE_POST_UPGRADE_HEADERS["post_upgrade"]
                        )
                      disable_bucket = True

                    self._pre_and_post_upgrade_executor(
                      jobs=jobs,
                      action=action,
                      in_key=in_key,
                      out_key=out_key,
                      upgrade_action="post_upgrade",
                      user_ts=user_ts,
                      _batch_size=batch_size,
                      disable_bucket=disable_bucket
                    )
            else:
              with self._global_lock:
                if jobs.get("preserve_cluster_on_failure"):
                  database.resource_manager[cluster_name].update({
                    "preserve_cluster": True
                  })
                database.matrices[action][str(out_key)][str(in_key)].update({
                  "Result": "Failed",
                  "Reason": ("Unable to deploy MSP-AOSS. Please check - "+
                             str(database.matrices[action][str(out_key)]
                                 [str(in_key)]["Deployment_Jita_URL"])),
                  "Status": "completed"
                })

        else:
          database.matrices[action][str(out_key)][str(in_key)].update({
            "Result": "Skipped",
            "Reason": ("Unable to proceed as all clusters are preserved"
                       " on failure."),
            "Status": "pending"
          })

        self.emailer.send_mail(
          out_key=copy.deepcopy(str(out_key)),
          in_key=copy.deepcopy(str(in_key)),
          action=copy.deepcopy(action),
          mail_type=copy.deepcopy("end")
        )

        _print_list = self.args_manipulator.json_to_list_converter(
          upgrade_dict=database.matrices[action],
          headers=copy.deepcopy(headers)
        )
        self.args_manipulator.log_matrix_printer(
          headers=copy.deepcopy(headers),
          print_list=copy.deepcopy(_print_list)
        )
        if (database.resource_manager[
            database.matrices[action][str(out_key)][str(in_key)]
            ["cluster_name"]
        ].get(
          "deployment_to_release"
        ) and action not in metadata.IGNORE_IMAGING_ACTIONS):
          INFO("Releasing Scheduled Deployment for Cluster: "+str(
            database.matrices[action][str(out_key)][str(in_key)]
            ["cluster_name"]
          ))
          INFO("Resource Manager: "+json.dumps(database.resource_manager))
          self.RDM_PRODUCT_MAP[jobs.get("product")].release_cluster(
            deployment_id=(database.resource_manager[
              database.matrices[action][str(out_key)][str(in_key)]
              ["cluster_name"]
            ]["deployment_to_release"])
          )
        self.teardown(job_prof_id=job_prof_id, jobs=jobs,
                      dep_job_prof_id=dep_job_prof_id)

        # UPDATE THE DB WITH LATEST EXECUTION
        if action not in metadata.STATIC_IGNORE_IMAGING_ACTIONS:
          self._update_db_with_local(
            index_name=index_name
          )
        else:
          final_dict = database.matrices[action][str(out_key)][str(in_key)]
          final_dict.update(
            {
              "out_key": str(out_key),
              "in_key": str(in_key),
              "matrix_type": str(action),
              "uuid": str(database.matrices["uuid"]),
              "matrix_start_time": database.matrices["matrix_start_time"]
            }
          )

          self.db_conn.ingest_data(data=copy.deepcopy(final_dict),
                                   db_name=copy.deepcopy(self.elk_db_name))

      except Exception as e: #pylint: disable=bare-except,broad-except,invalid-name
        INFO("Thread hit an Exception. Error: "+str(e))
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        INFO("Exception Type: "+str(exc_type))
        INFO("Exception Filename: "+str(fname))
        INFO("Exception Line no.: "+str(exc_tb.tb_lineno))
        INFO(str(exc_obj))
        # Print the traceback
        ERROR(f"Traceback of exception: \n{traceback.format_exc()}")
        total_time = "N/A"
        end_time = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
        if "Start_Time" in (database.matrices[action][str(out_key)]
                            [str(in_key)].keys()):
          endtime = datetime.strptime(end_time,
                                      "%d-%m-%Y %H:%M:%S")
          starttime = datetime.strptime(
            database.matrices[action][str(out_key)][str(in_key)]["Start_Time"],
            "%d-%m-%Y %H:%M:%S"
          )
          total_time = str(timedelta(seconds=int(
            (endtime - starttime).total_seconds()
          )))
        with self._global_lock:
          for index in range(int(in_key), int(in_key)+batch_size):
            database.matrices[action][str(out_key)][str(index)].update({
              "End_Time": end_time,
              "Total_Time": total_time,
              "Status": "pending",
              "Result": "Failed",
              "Reason": "Thread hit an exception. "\
                        "Please check the 1-click Trigger Logs for details."
            })

      finally:
        if "cluster_name" in (database.matrices[action][str(out_key)]
                              [str(in_key)].keys()):
          with self._global_lock:
            (database.resource_manager
             [(database.matrices[action][str(out_key)][str(in_key)]
               ["cluster_name"])]["is_available"]) = True
            INFO("Cluster:"+str((database.matrices[action][str(out_key)]
                                 [str(in_key)]["cluster_name"]))+
                 " is made available in Resource Manager")
        elif cluster_name is not None:
          with self._global_lock:
            database.resource_manager[cluster_name]["is_available"] = True
            INFO("Cluster is made available in Resource Manager")

  def workload_executor(self, jobs): #pylint: disable=too-many-locals,too-many-branches,too-many-statements

    """
    Method to Clone and Execute the Job Profile, and then Poll the
    triggered task.

    Args:
      jobs(json): Jobs JSON for the particular run

    """
    # try: #pylint: disable=too-many-nested-blocks
    with self._global_lock:
      counter = 0

    for wk_detail in jobs.get("workload_details"):
      INFO("Initiate the Execution Data.")

      with self._global_lock:
        database.matrices["execution_data"].append({})
        database.matrices["execution_data"][counter].update(
          {
            "jobs": jobs
          }
        )
      INFO("Clone the Job Profile.")
      job_profile_name = self._clone_workload_job_profile(
        jobs=copy.deepcopy(jobs),
        workload_dict=wk_detail.get("workload_dict"),
        wk_name=wk_detail.get("workload_name")
      )

      STEP("Fetch Job profile ID.")
      job_prof_id = self.JITA_PRODUCT_MAP[
        jobs.get("product", self.jita)
      ].get_job_profile_id(
        copy.deepcopy(job_profile_name)
      )

      INFO("Job Profile ID: %s" % job_prof_id)

      if job_prof_id is None:
        with self._global_lock:
          database.matrices["execution_data"][counter].update({
            "job_profile_name": job_profile_name,
            "wk_name": wk_detail.get("workload_name"),
            "Result": "Not Executed",
            "Reason": "Unable to clone job profile.",
            "Status": "completed"
          })

      else:
        STEP("Trigger the Job Profile.")
        task_id = self.JITA_PRODUCT_MAP[
          jobs.get("product", self.jita)
        ].task_trigger(job_prof_id)

        if task_id is None:
          with self._global_lock:
            database.matrices["execution_data"][counter].update({
              "job_profile_name": job_profile_name,
              "job_profile_id": job_prof_id,
              "result": "Not Executed",
              "reason": "Unable to Trigger job profile.",
              "status": "completed"
            })

        else:
          INFO("Update the local DB with execution details.")
          with self._global_lock:
            database.matrices["execution_data"][counter].update({
              "job_profile_name": job_profile_name,
              "job_profile_id": job_prof_id,
              "jita_task_id": task_id,
              "jita_url": (metadata.TEST_REPORT_URL+str(task_id)),
              "status": "triggered",
              "start_time": datetime.now().strftime("%d-%m-%Y %H:%M:%S"),
              "start_time_epoch": str(time.time())
            })

          INFO("Update the Apeiron DB with execution details.")
          apeiron_db_query = {
            "doc": {
              "execution_data": database.matrices["execution_data"]
            },
            "detect_noop": False
          }
          elk_update = self.db_conn.elk_update_query(
            index_name="workload_execution",
            elk_func="_update",
            payload=apeiron_db_query,
            data_id=database.matrices["uuid"]
          )

          if not elk_update:
            ERROR("Unable to update Apeiron DB.")
            ERROR("Please check the logs and retry.")

          else:
            INFO("Apeiron DB update successfull.")

          STEP("Poll the triggered Job Profiles.")
          _is_task_completed = self._poll_task(
            jobs=jobs,
            task_id=copy.deepcopy(task_id),
            no_of_retries=copy.deepcopy(int(jobs["no_of_retries"])),
            retry_interval=copy.deepcopy(int(jobs["retry_interval"]))
          )

          if _is_task_completed:
            with self._global_lock:
              database.matrices["execution_data"][counter].update({
                "end_time": datetime.now().strftime("%d-%m-%Y %H:%M:%S"),
                "end_time_epoch": str(time.time())
              })
            _result_dict = self._update_result(
              jobs=jobs,
              task_id=copy.deepcopy(task_id),
              stime=copy.deepcopy(database.matrices["execution_data"]
                                  [counter]["start_time"]),
              etime=copy.deepcopy(database.matrices["execution_data"]
                                  [counter]["end_time"])
            )
            with self._global_lock:
              INFO("Updating the result dictionary to execution data")
              for each_key in _result_dict:
                database.matrices["execution_data"][counter].update({
                  each_key.lower(): _result_dict[each_key]
                })

          else:
            end_time = datetime.strptime(
              datetime.now().strftime("%d-%m-%Y %H:%M:%S"),
              "%d-%m-%Y %H:%M:%S"
            )
            start_time = datetime.strptime(
              (database.matrices["execution_data"][counter]
               ["start_time"]),
              "%d-%m-%Y %H:%M:%S"
            )
            total_time = str(timedelta(seconds=int(
              (end_time - start_time).total_seconds()
            )))
            with self._global_lock:
              database.matrices["execution_data"][counter].update({
                "end_time": datetime.now().strftime("%d-%m-%Y %H:%M:%S"),
                "total_time": total_time,
                "status": "pending",
                "result": "Crossed the Polling Limit"
              })

        self.teardown(job_prof_id=job_prof_id, jobs=jobs)
        INFO("Update the Apeiron DB with execution details.")
        apeiron_db_query = {
          "doc": {
            "execution_data": database.matrices["execution_data"]
          },
          "detect_noop": False
        }
        elk_update = self.db_conn.elk_update_query(
          index_name="workload_execution",
          elk_func="_update",
          payload=apeiron_db_query,
          data_id=database.matrices["uuid"]
        )

        if not elk_update:
          ERROR("Unable to update Apeiron DB.")
          ERROR("Please check the logs and retry.")

        else:
          INFO("Apeiron DB update successfull.")
      counter += 1

  def teardown(self, jobs, job_prof_id, dep_job_prof_id=None):
    """
    A teardown method to delete the cloned job profile and test set.

    Args:
      job_prof_id(str): Job Profile ID to be deleted.
      dep_job_prof_id(str): Deployment Job Profile ID to be deleted.
      jobs(dict): Jobs Dictionary.
    """
    # job_prof_details = self.jita.get_job_profile_info(

    # )

    # for testset_id in job_prof_details["data"]["test_sets"]:
    #   STEP("Deleting testset with id: %s" % testset_id)
    #   self.jita.delete_testset(test_set_id=testset_id)
    if dep_job_prof_id:
      STEP("Deleting job profile with id: %s" % dep_job_prof_id)
      self.JITA_PRODUCT_MAP[jobs.get("product", self.jita)].delete_job_profile(
        job_profile_id=copy.deepcopy(dep_job_prof_id)
      )
    if job_prof_id:
      STEP("Deleting job profile with id: %s" % job_prof_id)
      self.JITA_PRODUCT_MAP[jobs.get("product", self.jita)].delete_job_profile(
        job_profile_id=copy.deepcopy(job_prof_id)
      )

  def _deployment_trigger(self, action, in_key, out_key, jobs, index_name,#pylint: disable=too-many-locals
                          dep_jp=False):
    """
    A method to deploy the service.

    Args:
      action(str): Action Name.
      in_key(str): Matrix In Key.
      out_key(str): Matrix Out Key.
      jobs(dict): Jobs Dictionary.
      index_name(str): Apeiron DB Index name.
      dep_jp(bool): True if its a deployment step.

    """

    upgrade_var = copy.deepcopy(database.matrices[action]
                                [str(out_key)][str(in_key)])
    deploy_job_profile_name = self._clone_job_profile_msp(
      jobs=copy.deepcopy(jobs),
      upgrade_dict=upgrade_var,
      action=action,
      dep_jp=dep_jp
    )

    STEP("Fetch Job profile ID.")
    dep_job_prof_id = self.JITA_PRODUCT_MAP[
      jobs.get("product", self.jita)
    ].get_job_profile_id(
      copy.deepcopy(deploy_job_profile_name)
    )

    INFO("Job Profile ID: %s" % dep_job_prof_id)

    if dep_job_prof_id is None:
      with self._global_lock:
        database.matrices[action][str(out_key)][str(in_key)].update({
          "Result": "Not Executed",
          "Reason": "Unable to clone deployment job profile.",
          "Status": "completed"
        })

      self.emailer.send_mail(
        out_key=copy.deepcopy(str(out_key)),
        in_key=copy.deepcopy(str(in_key)),
        action=copy.deepcopy(action),
        mail_type=copy.deepcopy("end")
      )
      if action not in metadata.STATIC_IGNORE_IMAGING_ACTIONS:
        self._update_db_with_local(
          index_name=index_name
        )
    else:
      STEP("Trigger the Job Profile.")
      task_id = self.JITA_PRODUCT_MAP[
        jobs.get("product", self.jita)
      ].task_trigger(dep_job_prof_id)

      if task_id is None:
        with self._global_lock:
          database.matrices[action][str(out_key)][str(in_key)].update({
            "Result": "Not Executed",
            "Reason": "Unable to Trigger deployment job profile.",
            "Status": "completed"
          })

        self.emailer.send_mail(
          out_key=copy.deepcopy(str(out_key)),
          in_key=copy.deepcopy(str(in_key)),
          action=copy.deepcopy(action),
          mail_type=copy.deepcopy("end")
        )
        if action not in metadata.STATIC_IGNORE_IMAGING_ACTIONS:
          self._update_db_with_local(
            index_name=index_name
          )
      else:
        with self._global_lock:
          database.matrices[action][str(out_key)][str(in_key)].update({
            "Deployment_Jita_URL": (metadata.TEST_REPORT_URL
                                    +str(task_id))
          })

        self.emailer.send_mail(
          out_key=copy.deepcopy(str(out_key)),
          in_key=copy.deepcopy(str(in_key)),
          action=copy.deepcopy(action),
          mail_type=copy.deepcopy("start")
        )
        if action not in metadata.STATIC_IGNORE_IMAGING_ACTIONS:
          self._update_db_with_local(
            index_name=index_name
          )

        STEP("Poll the triggered Deployment Job Profiles.")
        _is_task_completed = self._poll_task(
          jobs=jobs,
          task_id=copy.deepcopy(task_id),
          no_of_retries=copy.deepcopy(int(jobs["no_of_retries"])),
          retry_interval=copy.deepcopy(int(jobs["retry_interval"]))
        )

        if not _is_task_completed:
          if action not in metadata.STATIC_IGNORE_IMAGING_ACTIONS:
            self._update_db_with_local(
              index_name=index_name
            )
          end_time = datetime.strptime(
            datetime.now().strftime("%d-%m-%Y %H:%M:%S"),
            "%d-%m-%Y %H:%M:%S"
          )
          start_time = datetime.strptime(
            (database.matrices[action][str(out_key)][str(in_key)]
             ["Deployment_Start_Time"]),
            "%d-%m-%Y %H:%M:%S"
          )
          total_time = str(timedelta(seconds=int(
            (end_time - start_time).total_seconds()
          )))
          with self._global_lock:
            database.matrices[action][str(out_key)][str(in_key)].update({
              "Deployment_End_Time": datetime.now().strftime(
                "%d-%m-%Y %H:%M:%S"
              ),
              "Deployment_Total_Time": total_time,
              "Deployment_Status": "Pending",
              "Deployment_Result": "Pending"
            })

          self.emailer.send_mail(
            out_key=copy.deepcopy(str(out_key)),
            in_key=copy.deepcopy(str(in_key)),
            action=copy.deepcopy(action),
            mail_type=copy.deepcopy("end")
          )
        else:
          with self._global_lock:
            database.matrices[action][str(out_key)][str(in_key)].update({
              "Deployment_End_Time": datetime.now().strftime(
                "%d-%m-%Y %H:%M:%S"
              )
            })
          _result_dict = self._update_result(
            jobs=jobs,
            task_id=copy.deepcopy(task_id),
            stime=copy.deepcopy(database.matrices[action][str(out_key)]
                                [str(in_key)]["Deployment_Start_Time"]),
            etime=copy.deepcopy(database.matrices[action][str(out_key)]
                                [str(in_key)]["Deployment_End_Time"]),
            platform_name=copy.deepcopy(database.matrices[action]
                                        [str(out_key)]
                                        [str(in_key)]["Platform"]),
            deployment=True
          )
          _result_dict.update({
            "Result": "",
            "Reason": ""
          })
          database.matrices[action][str(out_key)][str(in_key)].update(
            _result_dict
          )

          self.emailer.send_mail(
            out_key=copy.deepcopy(str(out_key)),
            in_key=copy.deepcopy(str(in_key)),
            action=copy.deepcopy(action),
            mail_type=copy.deepcopy("end")
          )

  def _clone_workload_job_profile(self, jobs, workload_dict, wk_name):
    """
    A method to clone the job profile

    Args:
      jobs(dict): Dictionary containing Job details.
      workload_dict(dict): Upgrade Dictionary.
      wk_name(str): Workload Name.

    Returns:
      job_profile_name(str): Cloned Job Profile Name
    """
    job_profile_id = self.JITA_PRODUCT_MAP[
      jobs.get("product", self.jita)
    ].get_job_profile_id(
      job_profile_name=copy.deepcopy(jobs["job_profile"]))
    job_profile_details = json.loads(
      self.JITA_PRODUCT_MAP[
        jobs.get("product", self.jita)
      ].get_job_profile_info(copy.deepcopy(job_profile_id)))
    INFO(json.dumps(job_profile_details))
    if job_profile_details["success"]:
      result = job_profile_details["data"]
      for i in metadata.JOB_CLONE_KEYS_TO_DELETE:
        if result.get(i) is not None:
          del result[i]
      test_sets = []

      for key in result["test_sets"]:
        testset_id = key["$oid"]
        # INFO("Testset ID: %s" % testset_id)
        _testset_payload = (self.JITA_PRODUCT_MAP[
          jobs.get("product", self.jita)
        ].get_testset_info(testset_id=testset_id))
        tests = []
        for i in metadata.TEST_SET_CLONE_KEYS_TO_DELETE:
          if _testset_payload.get(i) is not None:
            del _testset_payload[i]
        _testset_payload["name"] = str(wk_name+"_copy_"+(
          datetime.now().strftime("%d-%m-%Y_%H:%M:%S")))

        _testset_payload["args_map"]["oss_name"] = (
          jobs.get("cluster_details").get("oss_name")
        )
        _testset_payload["args_map"]["load_config_params"] = (
          "'"+workload_dict+"'"
        )

        tests.extend(_testset_payload["tests"])
        _testset_payload["tests"] = tests
        test_sets.append({"$oid":str(self.JITA_PRODUCT_MAP[
          jobs.get("product", self.jita)
        ].get_test_set_id(
          self.JITA_PRODUCT_MAP[
            jobs.get("product", self.jita)
          ].clone_test_set(
            payload=copy.deepcopy(_testset_payload)
          )))})
      result["test_sets"] = test_sets
      payload = self.payload_generator.workload_job_payload_builder(
        jobs=copy.deepcopy(jobs),
        fetched_dict=copy.deepcopy(result)
      )
      # INFO(json.dumps(payload))
      return self.JITA_PRODUCT_MAP[
        jobs.get("product", self.jita)
      ].create_job_profile(payload=payload)
    ERROR("Job Profile couldn't be cloned because "
          "of empty job profile details.")
    return None

  def _clone_job_profile_msp(self, jobs, upgrade_dict, action, dep_jp=False,#pylint: disable=too-many-locals,too-many-branches,too-many-statements
                             **kwargs):
    """
    A method to clone the job profile

    Args:
      jobs(dict): Dictionary containing Job details.
      upgrade_dict(dict): Upgrade Dictionary.
      action(str): Suite Name.
      dep_jp(str): Deployment Job Profile.

    Returns:
      job_profile_name(str): Cloned Job Profile Name
    """
    INFO("Jobs: "+str(jobs))
    if kwargs.get("action"):
      INFO("Clone JP action: "+str(kwargs.get("action")))
    jp_name = copy.deepcopy(jobs.get("job_profile"))
    if isinstance(upgrade_dict, list):
      upgrade_dict = copy.deepcopy(upgrade_dict[0])
    if upgrade_dict.get("job_profile"):
      jp_name = copy.deepcopy(upgrade_dict.get("job_profile"))
    if dep_jp:
      jp_name = copy.deepcopy(jobs["dep_job_profile"])
    job_profile_id = self.JITA_PRODUCT_MAP[
      jobs.get("product", self.jita)
    ].get_job_profile_id(
      job_profile_name=jp_name)
    job_profile_details = json.loads(
      self.JITA_PRODUCT_MAP[
        jobs.get("product", self.jita)
      ].get_job_profile_info(copy.deepcopy(job_profile_id)))
    INFO(json.dumps(job_profile_details))
    if job_profile_details["success"]:#pylint:disable=too-many-nested-blocks
      result = job_profile_details["data"]
      for i in metadata.JOB_CLONE_KEYS_TO_DELETE:
        if result.get(i) is not None:
          del result[i]
      test_sets = []

      for key in result["test_sets"]:
        time.sleep(2)
        testset_id = key["$oid"]
        # INFO("Testset ID: %s" % testset_id)
        _testset_payload = (self.JITA_PRODUCT_MAP[
          jobs.get("product", self.jita)
        ].get_testset_info(testset_id=testset_id))
        INFO("Input Testset Payload: "+json.dumps(_testset_payload))
        tests = []
        for i in metadata.TEST_SET_CLONE_KEYS_TO_DELETE:
          if _testset_payload.get(i) is not None:
            del _testset_payload[i]
        _testset_payload["name"] = str("apeiron_"+str(action)+"_"+
                                       str(upgrade_dict.get("row_id"))
                                       +"_"+(datetime.now().strftime(
                                         "%d-%m-%Y_%H:%M:%S"
                                       )))
        if upgrade_dict.get("test_args"):
          _testset_payload["args_map"].update(upgrade_dict["test_args"])
        if dep_jp:
          if (upgrade_dict.get("Destination_Objects") and
              action == "objects_upgrade"):
            _testset_payload["args_map"]["reset_objects_manager_version"] = (
              upgrade_dict.get("Source_Objects")
            )
          else:
            if upgrade_dict.get("Objects_Version") == "latest":
              _testset_payload["args_map"]["oss_deployments~0~image_tag"] = (
                "buckets-"+upgrade_dict.get("Objects_Version")
              )
              _testset_payload["args_map"]["objects_manager_version"] = (
                '"'+upgrade_dict.get("Objects_Version")+'"'
              )

            if (jobs.get("args_override") and
                jobs.get("product") == "objects"):
              if _testset_payload.get("args_override"):
                _testset_payload["args_override"].update(
                  jobs.get("args_override")
                )
              else:
                _testset_payload.update({
                  "args_override": jobs.get("args_override")
                })

            if upgrade_dict.get("Source_MSP"):
              _testset_payload["args_map"]["msp_controller_version"] = (
                upgrade_dict.get("Source_MSP")
              )

            if jobs.get("cluster_size"):
              _testset_payload["args_map"]["oss_deployments~0~oss_nodes"] = (
                jobs.get("cluster_size")
              )

            if upgrade_dict.get("cluster_size"):
              _testset_payload["args_map"]["oss_deployments~0~oss_nodes"] = (
                upgrade_dict.get("cluster_size")
              )

        else:
          if (jobs.get("args_override") and
              action != "objects_upgrade"):
            if _testset_payload.get("args_override"):
              _testset_payload["args_override"].update(
                jobs.get("args_override")
              )
            else:
              _testset_payload.update({
                "args_override": jobs.get("args_override")
              })

          if upgrade_dict.get("Kubernetes_Platform"):
            _testset_payload["args_map"].update({
              "k8s_type": upgrade_dict.get("Kubernetes_Platform")
            })

          if (upgrade_dict.get("Feat") and "eplication" in
              upgrade_dict.get("Feat") and jobs.get("product") == "objects"):
            if (jobs.get("args_override").get("oss_deployments~0~image_tag") !=
                ""):
              _testset_payload["args_map"].update({
                "oss_deployments~1~image_tag": jobs.get("args_override").get(
                  "oss_deployments~0~image_tag"
                ),
                "oss_deployments~1~new_registry": jobs.get("args_override").get(
                  "oss_deployments~0~new_registry"
                ),
              })
            else:
              _testset_payload["args_map"].update({
                "oss_deployments~1~image_tag": jobs.get("args_override").get(
                  "oss_deployments~0~image_tag"
                ),
                "oss_deployments~1~new_registry": (
                  jobs.get("args_override").get(
                    "oss_deployments~0~new_registry"
                  )
                )
              })

          if jobs.get("test_args") or upgrade_dict.get("test_args"):
            if (upgrade_dict.get("test_args") and
                upgrade_dict["test_args"].get("main")):
              _testset_payload["args_map"].update(
                upgrade_dict["test_args"].get("main")
              )
            if jobs.get("test_args") and jobs["test_args"].get("main"):
              _testset_payload["args_map"].update(
                jobs["test_args"].get("main")
              )

          if (upgrade_dict.get("Destination_MSP") or
              upgrade_dict.get("upgrade_list")):
            upgrade_list = []
            if upgrade_dict.get("upgrade_list"):
              upgrade_list = upgrade_dict.get("upgrade_list")
            else:
              target_dict = {
                "msp": upgrade_dict.get("Destination_MSP"),
                "pc": upgrade_dict.get("Destination_PC"),
                "pe": upgrade_dict.get("Destination_AOS")
              }

              if jobs.get("pc_rim_url"):
                target_dict.update({
                  "pc_rim_url": jobs.get("pc_rim_url")
                })

              if jobs.get("oss_rim_url"):
                target_dict.update({
                  "oss_rim_url": jobs.get("oss_rim_url")
                })

              if jobs.get("aoss_rim_url"):
                target_dict.update({
                  "aoss_rim_url": jobs.get("aoss_rim_url")
                })

              if jobs.get("pe_rim_url"):
                target_dict.update({
                  "pe_rim_url": jobs.get("pe_rim_url")
                })

              if jobs.get("msp_rim_url"):
                target_dict.update({
                  "msp_rim_url": jobs.get("msp_rim_url")
                })

              upgrade_list.append(target_dict)
            (_testset_payload["args_map"]
             ["test_tasks~steps_api~ordered_dict"
              "~0~func_kwargs~upgrade_list"]) = (
                "'"+json.dumps(upgrade_list)+"'")

        tests.extend(_testset_payload["tests"])
        _testset_payload["tests"] = tests
        INFO("Generated Testset Payload: "+json.dumps(_testset_payload))
        test_sets.append({"$oid":str(self.JITA_PRODUCT_MAP[
          jobs.get("product", self.jita)
        ].get_test_set_id(
          self.JITA_PRODUCT_MAP[
            jobs.get("product", self.jita)
          ].clone_test_set(
            payload=copy.deepcopy(_testset_payload)
          )))})
      result["test_sets"] = test_sets
      payload = self.payload_generator.workload_job_payload_builder(
        jobs=copy.deepcopy(jobs),
        fetched_dict=copy.deepcopy(result),
        upgrade_dict=copy.deepcopy(upgrade_dict),
        row_id=copy.deepcopy(upgrade_dict.get("row_id"))
      )
      # INFO(json.dumps(payload))
      return self.JITA_PRODUCT_MAP[
        jobs.get("product", self.jita)
      ].create_job_profile(payload=payload)
    ERROR("Job Profile couldn't be cloned because "
          "of empty job profile details.")
    return None

  def _clone_job_profile(self, jobs, upgrade_dict, action):
    """
    A method to clone the job profile

    Args:
      jobs(dict): Dictionary containing Job details.
      upgrade_dict(dict): Upgrade Dictionary.
      action(str): Action to be performed
                   (One of "ahv_upgrade", "ahv_aos_upgrade", "deployment_path")

    Returns:
      job_profile_name(str): Cloned Job Profile Name
    """
    jp_name = copy.deepcopy(jobs.get("job_profile"))
    if upgrade_dict.get("job_profile"):
      jp_name = copy.deepcopy(upgrade_dict.get("job_profile"))
    job_profile_id = self.JITA_PRODUCT_MAP[
      jobs.get("product", self.jita)
    ].get_job_profile_id(
      job_profile_name=copy.deepcopy(jp_name))
    job_profile_details = json.loads(
      self.JITA_PRODUCT_MAP[
        jobs.get("product", self.jita)
      ].get_job_profile_info(copy.deepcopy(job_profile_id)))
    if job_profile_details["success"]:
      result = job_profile_details["data"]
      for i in metadata.JOB_CLONE_KEYS_TO_DELETE:
        if result.get(i) is not None:
          del result[i]
      test_sets = []
      tup = self.payload_generator.testset_param_setter(
        upgrade_dict=copy.deepcopy(upgrade_dict),
        jobs=jobs
      )
      for key in result["test_sets"]:
        time.sleep(2)
        testset_id = key["$oid"]
        INFO("Testset ID: %s" % testset_id)
        _testset_payload = (self.payload_generator.testset_payload_generation(
          testset_id=copy.deepcopy(testset_id),
          new_ahv=copy.deepcopy(tup[0]),
          new_aos=copy.deepcopy(tup[1]), old_aos=copy.deepcopy(tup[3]),
          old_ahv=copy.deepcopy(tup[2]),
          lcm_url=copy.deepcopy(tup[4]),
          ahv_to_lcm_blacklist=copy.deepcopy(tup[5]),
          product_meta_url=copy.deepcopy(tup[6]),
          disable_nos_prod_meta=copy.deepcopy(tup[7]),
          new_nos_url=copy.deepcopy(tup[8]),
          skip_nos_supported_check=copy.deepcopy(tup[9]),
          darksite_bundle_url=copy.deepcopy(tup[10]),
          new_ahv_list=copy.deepcopy(tup[11]),
          new_nos_releases=copy.deepcopy(tup[12]),
          vlan=copy.deepcopy(tup[13]),
          nos_rim_urls=copy.deepcopy(tup[14]),
          nos_rim_url=copy.deepcopy(tup[15]),
          binary_location=copy.deepcopy(tup[16]),
          host_driver_url=copy.deepcopy(tup[17]),
          test_args=copy.deepcopy(tup[18]))
                           )
        test_sets.append({"$oid":str(self.JITA_PRODUCT_MAP[
          jobs.get("product", self.jita)
        ].get_test_set_id(
          self.JITA_PRODUCT_MAP[
            jobs.get("product", self.jita)
          ].clone_test_set(
            payload=copy.deepcopy(_testset_payload)
          )))})
      result["test_sets"] = test_sets
      payload = self.payload_generator.job_payload_builder(
        user_dict=copy.deepcopy(jobs),
        fetched_dict=copy.deepcopy(result),
        action=copy.deepcopy(action),
        upgrade_dict=copy.deepcopy(upgrade_dict),
        jobs=copy.deepcopy(jobs),
        task_id=upgrade_dict.get("row_id")
      )
      # INFO(json.dumps(payload))
      return self.JITA_PRODUCT_MAP[
        jobs.get("product", self.jita)
      ].create_job_profile(payload=payload)
    ERROR("Job Profile couldn't be cloned because "
          "of empty job profile details.")
    return None

  def _clone_gos_job_profile(self, jobs, upgrade_dict, action):
    """
    A method to clone the job profile for gos qual
    Args:
      jobs(dict): Dictionary containing Job details.
      upgrade_dict(list): GOS List
      action(str): don;t bother
    Returns:
      job_profile_name(str): Cloned Job Profile Name
    """
    INFO("Ignoring action for guest OS qualification: ", action)
    job_profile_id = self.JITA_PRODUCT_MAP[
      jobs.get("product", self.jita)
    ].get_job_profile_id(
      job_profile_name=jobs["job_profile"])
    job_profile_details = json.loads(
      self.JITA_PRODUCT_MAP[
        jobs.get("product", self.jita)
      ].get_job_profile_info(job_profile_id))
    if job_profile_details["success"]:
      result = job_profile_details["data"]
      for i in metadata.JOB_CLONE_KEYS_TO_DELETE:
        if result.get(i) is not None:
          del result[i]
      test_sets = []
      for key in result["test_sets"]:
        testset_id = key["$oid"]
        _testset_payload = \
          (self.payload_generator.gos_testset_payload_generation(
            copy.deepcopy(testset_id), upgrade_dict))
        test_sets.append({"$oid": str(self.JITA_PRODUCT_MAP[
          jobs.get("product", self.jita)
        ].get_test_set_id(
          self.JITA_PRODUCT_MAP[
            jobs.get("product", self.jita)
          ].clone_test_set(
            payload=_testset_payload
          )))})
      result["test_sets"] = test_sets
      payload = self.payload_generator.gos_job_payload_builder(
        user_dict=jobs,
        fetched_dict=result,
        gos_dict=upgrade_dict
      )
      # INFO(json.dumps(payload))
      return self.JITA_PRODUCT_MAP[
        jobs.get("product", self.jita)
      ].create_job_profile(payload=payload)
    ERROR("Job Profile couldn't be cloned because "
          "of empty job profile details.")
    return None

  def _post_upgrade_executor(self, jobs, bucket_dict, action, out_key, in_key,#pylint: disable=too-many-locals
                             action_str, upgrade_action):
    """
    A method to execute Post Upgrade tests

    Args:
      jobs(dict): Jobs Dictionary.
      bucket_dict(dict): Bucket Dict.
      action(str): Suite Name.
      out_key(str): Matrix outer key.
      in_key(str): Matrix inner key.
      action_str(str): Pre Upgrade or Post Upgrade.
      upgrade_action(str): Upgrade Action (pre_upgrade or post_upgrade).
    """
    if upgrade_action not in database.matrices[action][out_key][in_key].keys():
      database.matrices[action][out_key][in_key].update({
        upgrade_action: {
          "bucket_dict": {}
        }
      })
    for bucket in bucket_dict.keys():#pylint: disable=too-many-nested-blocks
      for feat in bucket_dict[bucket].keys():
        (database.matrices[action][out_key][in_key][upgrade_action]
         ["bucket_dict"]).update(
           {bucket: {}}
         )
        (database.matrices[action][out_key][in_key][upgrade_action]
         ["bucket_dict"][bucket]).update(
           {feat: {}}
         )
        (database.matrices[action][out_key][in_key][upgrade_action]
         ["bucket_dict"][bucket][feat]).update(
           {
             "Result": {},
             "Reason": {},
             "Status": {},
             "Jita_URL": {},
             "Task_ID": {},
             "Start_Time": {},
             "End_Time": {},
             "Total_Time": {}
           }
         )
        for key in bucket_dict[bucket][feat]["testsets"].keys():
          _job_prof_id = str(bucket_dict[bucket][feat]["job_profile_id"]
                             [str(key)])
          INFO("PU Job Profile ID to be executed next: "+_job_prof_id)

          if _job_prof_id is None:
            with self._global_lock:
              (database.matrices[action][out_key][in_key][upgrade_action]
               ["bucket_dict"][bucket][feat]["Result"]).update(
                 {
                   str(key): "Failed"
                 }
               )
              (database.matrices[action][out_key][in_key][upgrade_action]
               ["bucket_dict"][bucket][feat]["Reason"]).update(
                 {
                   str(key): ("Unable to fetch the "+action_str+
                              " Job Profile ID.")
                 }
               )
              (database.matrices[action][out_key][in_key][upgrade_action]
               ["bucket_dict"][bucket][feat]["Status"]).update(
                 {
                   str(key): "pending"
                 }
               )
          else:
            STEP("Trigger the "+action_str+" Job Profile for "+str(bucket)+
                 "_"+str(feat)+" Bucket.")
            task_id = self.JITA_PRODUCT_MAP[
              jobs.get("product", self.jita)
            ].task_trigger(_job_prof_id)

            if task_id is None:
              with self._global_lock:
                (database.matrices[action][out_key][in_key][upgrade_action]
                 ["bucket_dict"][bucket][feat]["Result"]).update(
                   {
                     str(key): "Failed"
                   }
                 )
                (database.matrices[action][out_key][in_key][upgrade_action]
                 ["bucket_dict"][bucket][feat]
                 ["Reason"]).update(
                   {
                     str(key): "Unable to Trigger the "+action_str+
                               " Job Profile."
                   }
                 )
                (database.matrices[action][out_key][in_key][upgrade_action]
                 ["bucket_dict"][bucket][feat]
                 ["Status"]).update(
                   {
                     str(key): "pending"
                   }
                 )
            else:
              with self._global_lock:
                (database.matrices[action][out_key][in_key][upgrade_action]
                 ["bucket_dict"][bucket][feat]
                 ["Start_Time"]).update({
                   str(key): datetime.now().strftime("%d-%m-%Y %H:%M:%S")
                 })
                (database.matrices[action][out_key][in_key][upgrade_action]
                 ["bucket_dict"][bucket][feat]
                 ["Jita_URL"]).update({
                   str(key): (metadata.TEST_REPORT_URL
                              +str(task_id))
                 })
                (database.matrices[action][out_key][in_key][upgrade_action]
                 ["bucket_dict"][bucket][feat]
                 ["Task_ID"]).update({
                   str(key): str(task_id)
                 })

              STEP("Poll the triggered "+action_str+" Job Profiles.")
              _is_task_completed = self._poll_task(
                jobs=jobs,
                task_id=task_id,
                no_of_retries=10000000,
                retry_interval=300
              )

              if _is_task_completed:
                INFO(action_str+" Task status for "+str(bucket)+
                     "_"+str(feat)+" Bucket is completed.")
                with self._global_lock:
                  (database.matrices[action][out_key][in_key][upgrade_action]
                   ["bucket_dict"][bucket][feat]["End_Time"]).update({
                     str(key): datetime.now().strftime("%d-%m-%Y %H:%M:%S")
                   })
                _pu_result_dict = self._update_result(
                  jobs=jobs,
                  task_id=copy.deepcopy(task_id),
                  stime=(database.matrices[action][out_key][in_key]
                         [upgrade_action]["bucket_dict"][bucket][feat]
                         ["Start_Time"][str(key)]),
                  etime=(database.matrices[action][out_key][in_key]
                         [upgrade_action]["bucket_dict"][bucket][feat]
                         ["End_Time"][str(key)])
                )
                with self._global_lock:
                  for each_res in _pu_result_dict:
                    (database.matrices[action][out_key][in_key]
                     [upgrade_action]["bucket_dict"][bucket][feat]).update({
                       each_res: {}
                     })
                    (database.matrices[action][out_key][in_key]
                     [upgrade_action]["bucket_dict"][bucket]
                     [feat][each_res]).update({
                       str(key): _pu_result_dict[each_res]
                     })

              else:
                INFO(action_str+" Task status for "+str(bucket)+
                     "_"+str(feat)+" Bucket is pending. Timeout Occurred.")
                end_time = datetime.strptime(
                  datetime.now().strftime("%d-%m-%Y %H:%M:%S"),
                  "%d-%m-%Y %H:%M:%S"
                )
                start_time = datetime.strptime(
                  (database.matrices[action][out_key][in_key][upgrade_action]
                   ["bucket_dict"][bucket][feat]["Start_Time"][str(key)]),
                  "%d-%m-%Y %H:%M:%S"
                )
                total_time = str(timedelta(seconds=int(
                  (end_time - start_time).total_seconds()
                )))
                with self._global_lock:
                  (database.matrices[action][out_key][in_key][upgrade_action]
                   ["bucket_dict"][bucket][feat]["End_Time"]).update(
                     {
                       str(key): datetime.now().strftime("%d-%m-%Y %H:%M:%S")
                     }
                   )
                  (database.matrices[action][out_key][in_key][upgrade_action]
                   ["bucket_dict"][bucket][feat]["Status"]).update(
                     {
                       str(key): "Pending"
                     }
                   )
                  (database.matrices[action][out_key][in_key][upgrade_action]
                   ["bucket_dict"][bucket][feat]["Result"]).update(
                     {
                       str(key): "Pending"
                     }
                   )
                  (database.matrices[action][out_key][in_key][upgrade_action]
                   ["bucket_dict"][bucket][feat]["Total_Time"]).update(
                     {
                       str(key): total_time
                     }
                   )

  def _pu_data_manipulator(self, action, out_key, in_key, action_str,#pylint: disable=too-many-locals
                           upgrade_action):
    """
    A method to update the Post Upgrade Execution which can be showed in Email

    Args:
      action(str): Suite Name.
      out_key(str): Matrix outer key.
      in_key(str): Matrix inner key.
      action_str(str): Pre Upgrade or Post Upgrade.
      upgrade_action(str): Upgrade Action (pre_upgrade or post_upgrade).
    """
    task_id_list = []
    result_set = set()
    bucket_dict = (database.matrices[action][out_key][in_key][upgrade_action]
                   ["bucket_dict"])
    INFO("Bucket Dict: "+json.dumps(bucket_dict))
    for bucket in bucket_dict.keys():#pylint: disable=too-many-nested-blocks
      for feat in bucket_dict[bucket].keys():
        if "Result" in bucket_dict[bucket][feat].keys():
          for key in bucket_dict[bucket][feat]["Result"].keys():
            res = bucket_dict[bucket][feat]["Result"][str(key)]
            if "," in res:
              res_list = res.split(",")
              for ele in res_list:
                result_set.add(ele.strip())
            else:
              result_set.add(res.strip())

        if "Task_ID" in bucket_dict[bucket][feat].keys():
          for key in bucket_dict[bucket][feat]["Task_ID"].keys():
            tid = bucket_dict[bucket][feat]["Task_ID"][str(key)]
            task_id_list.append(str(tid))

    task_id_str = ",".join(task_id_list)
    result_str = ",".join(result_set)
    INFO("PU Result: "+result_str)
    INFO("PU Task IDs: "+task_id_str)
    action_str = action_str.replace(" ", "_")
    INFO("Action string: "+action_str)
    with self._global_lock:
      database.matrices[action][out_key][in_key].update(
        {
          str(action_str)+"_Result": result_str,
          str(action_str)+"_Jita_URL": (metadata.TEST_REPORT_URL+
                                        str(task_id_str))
        }
      )

    INFO(database.matrices[action][out_key][in_key])

  def _poll_task(self, jobs, task_id, no_of_retries=1000000,
                 retry_interval=480, **kwargs):
    """
    A method to poll the task execution status.

    Args:
      task_id(str): Task ID.
      jobs(dict): Jobs Dictionary.
      no_of_retries(int): Number of Retries.
      retry_interval(int): Interval between each Retry.

    Returns:
      _is_task_completed(bool): True if the Task is completed, False in
                                other conditions.
    """
    _is_task_completed = False
    while no_of_retries:
      _task_status = self.JITA_PRODUCT_MAP[
        jobs.get("product", self.jita)
      ].get_agave_task_status(
        task_id=copy.deepcopy(task_id)
      )
      if (kwargs.get("action") and kwargs.get("out_key") and
          kwargs.get("in_key") and kwargs.get("batch_size") and
          kwargs.get("index_name")):
        _test_result_count = self.JITA_PRODUCT_MAP[
          jobs.get("product", self.jita)
        ].get_agave_test_result_count(
          task_id=task_id
        )
        with self._global_lock:
          for index in range(int(kwargs.get("in_key")),
                             (int(kwargs.get("in_key"))+
                              kwargs.get("batch_size"))):
            (database.matrices[kwargs.get("action")]
             [str(kwargs.get("out_key"))][str(index)]).update({
               "Status": _task_status,
               "test_result_count": _test_result_count})
        self._update_db_with_local(
          index_name=kwargs.get("index_name")
        )
      if _task_status in ["completed", "killed"]:
        _is_task_completed = True
        INFO("Task Status fetched successfully and is completed.")
        break
      INFO("Task Status is not completed. Retrying. {num}"
           " retries left".format(num=no_of_retries-1))
      time.sleep(retry_interval)
      no_of_retries -= 1
    return _is_task_completed

  def _update_result(self, jobs, task_id, stime, etime, platform_name=None,#pylint:disable=too-many-locals
                     deployment=False):
    """
    A method to update the matrix with the result obtained after
    the test has been executed.

    Args:
      stime(date): Start Time.
      etime(date): End Time.
      platform_name(str): Platform Name
      task_id(str): Task ID.
      jobs(dict): Jobs Dictionary.
      deployment(dict): Jobs Dictionary.

    Returns:
      result_dict(dict): Dictionary containing the Results.
    """
    result_dict = {}

    end_time = datetime.strptime(etime,
                                 "%d-%m-%Y %H:%M:%S")
    start_time = datetime.strptime(stime,
                                   "%d-%m-%Y %H:%M:%S")
    total_time = str(timedelta(seconds=int(
      (end_time - start_time).total_seconds()
    )))
    status = "completed"
    platform = self.JITA_PRODUCT_MAP[
      jobs.get("product", self.jita)
    ].get_platform_model(
      cluster_name=self.JITA_PRODUCT_MAP[
        jobs.get("product", self.jita)
      ].get_cluster_name(task_id=task_id)
    )
    (metadata.TEST_RESULT_PAYLOAD["raw_query"]
     ["agave_task_id"]["$in"][0]["$oid"]) = task_id
    tup = self.JITA_PRODUCT_MAP[
      jobs.get("product", self.jita)
    ].get_agave_test_result(
      payload=metadata.TEST_RESULT_PAYLOAD
    )
    result = tup[1]
    reason = tup[0]

    if deployment:
      result_dict.update({
        "Deployment_Status": status,
        "Deployment_Result": result,
        "Deployment_Reason": reason,
        "Deployment_Total_Time": total_time
      })
    else:
      result_dict.update({
        "Total_Time": total_time,
        "Status": status,
        "Result": result,
        "Reason": reason
      })

    if platform_name is not None:
      result_dict.update({
        "Platform": str(platform_name+" ("+str(platform)+")")
      })

    return result_dict

  def _update_gos_result(self, in_key, out_key, action):
    """
    A method to update the matrix with the result obtained after
    the test has been executed.

    Args:
      in_key(str): Platform Name
      out_key(str): Task ID.
      action(str): Suite name

    Returns:
      result_dict(dict): Dictionary containing the Results.
    """
    result = None
    reason = ""
    query_list = [
      {
        "match": {
          "classifier.keyword": metadata.GOS_CLASSIFIER_MAPPING[action]
        }
      }
    ]

    gos_row_data = database.matrices[action][str(out_key)][str(in_key)]
    for each in metadata.GOS_RESULT_UPDATE_KEYS:
      keyname = each.split(".")[0]
      query_list.append({"match": {each: gos_row_data[keyname]}})

    query = copy.deepcopy(metadata.GUEST_OS_RESULT_QUERY)
    query["query"]["bool"]["must"] = query_list
    INFO("Query: "+json.dumps(query))

    result_list = self.db_conn.query_elk(
      index_name="gos_qualification",
      query_dict=query
    )

    if not result_list:
      return ("Unable to fetch", "Unable to fetch")
    INFO("Result: "+ str(result_list))
    result = result_list[0]["status"]
    if result in ["FAIL", "Failed"]:
      for test in result_list[0]["tests"]:
        if test.get("exception") != "NA":
          reason += test.get("exception")
    return (result, reason)

  def _poll_imaging(self, image_id, no_of_retry=40, retry_interval=180):
    """
    A method to poll Imaging status.

    Args:
      image_id(str): Imaging ID.
      no_of_retry(int): Number of Retries.
      retry_interval(int): Interval between each Retry.

    Returns:
      task_completed(bool): Imaging Task Completion status.
    """
    task_completed = False
    while no_of_retry:
      _image_status = self.jarvis.image_status(
        image_id=copy.deepcopy(image_id)
      )
      if _image_status == "SUCCESS":
        INFO("Imaging Completed Successfully.")
        task_completed = True
        break
      if _image_status == "FAILED":
        task_completed = False
        break
      INFO("Retrying to fetch Imaging Status")
      time.sleep(retry_interval)
      no_of_retry -= 1

    return task_completed

  def _poll_pu_task(self, task_id, jobs,
                    upgrade_list,
                    headers,
                    no_of_retries=10000,
                    retry_interval=240):
    """
    A method to poll the task execution status.

    Args:
      task_id(str): Task ID.
      upgrade_list(dict): Upgrade Dict.
      headers(list): Headers List.
      jobs(dict): Jobs Dictionary.
      no_of_retries(int): No of retries.
      retry_interval(int): Interval between each Retry.

    Returns:
      upgrade_list(list): Upgrade List.
    """

    while no_of_retries:
      _task_status = self.JITA_PRODUCT_MAP[
        jobs.get("product", self.jita)
      ].get_agave_task_status(
        task_id=copy.deepcopy(task_id)
      )
      if _task_status == "completed":
        INFO("Task Status fetched successfully and is completed.")
        break
      INFO("Task Status is not completed. Retrying. {num}"
           " retries left".format(num=no_of_retries-1))
      print_list = []
      print_list.append(upgrade_list)
      self.args_manipulator.pretty_print(headers=headers,
                                         print_list=print_list)
      time.sleep(retry_interval)
      no_of_retries -= 1
    return upgrade_list

  # def _check_if_not_succeeded(self, test_list, headers, action):
  #   """
  #   A method to check if the result of the task
  #   and update the list to re run if not succeeded
  #   """

  #   if test_list[headers.index("Result")] != "Succeeded":
  #     _list_to_be_appended = test_list
  #     for i in range(headers.index("Platform"), headers.index("Jita URL")):
  #       _list_to_be_appended[i] = ""
  #     if action == "ahv_upgrade":
  #       with self._global_lock:
  #         self.ahv_upgrade_list.append(_list_to_be_appended)
  #     elif action == "ahv_aos_upgrade":
  #       with self._ahv_aos_upgrade_lock:
  #         self.ahv_aos_upgrade_list.append(_list_to_be_appended)
  #     else:
  #       with self._deployment_path_lock:
  #         self.deployment_path_list.append(_list_to_be_appended)

  def _update_db_with_local(self, index_name="one_click_db"):
    """
    A method to update the Apeiron DB with the local DB

    Args:
      index_name(str): ELK Index name to be updated.
    """
    suite_list = list(database.matrices.keys())
    for element in metadata.REPORT_GENERATION_KEYS_TO_DELETE:
      if element in suite_list:
        suite_list.remove(element)
    INFO(suite_list)
    for suite in suite_list:
      for out_key in database.matrices[str(suite)].keys():
        for in_key in database.matrices[str(suite)][str(out_key)].keys():
          row_payload = {
            "doc": database.matrices[str(suite)][str(out_key)][str(in_key)]
          }
          self.db_conn.elk_update_query(
            index_name=index_name,
            payload=row_payload,
            data_id=(database.matrices[str(suite)][str(out_key)][str(in_key)]
                     ["row_id"]),
            elk_func="_update"
          )

  def _pre_and_post_upgrade_executor(self, jobs, action, in_key,
                                     out_key, upgrade_action, disable_bucket,
                                     _batch_size, user_ts=None):
    """
    A method to execute pre or post upgrade

    Args:
      jobs(dict): Jobs Dictionary.
      action(str): Suite Name.
      out_key(str): Matrix outer key.
      in_key(str): Matrix inner key.
      upgrade_action(str): Upgrade Action (pre_upgrade or post_upgrade).
      disable_bucket(bool): Bucket needs to be disabled or not.
      _batch_size(int): Batch size to be executed together
      user_ts(list): User provided testset to be executed for upgrade_action.
    """

    action_char_list = upgrade_action.split("_")
    res_str_list = []
    for word in action_char_list:
      res_str_list.append(word.capitalize())
    action_str = " ".join(res_str_list)

    if (database.matrices[action][str(out_key)]
        [str(in_key)].get("cluster_name")):
      pu_cluster_name = (database.matrices[action][str(out_key)]
                         [str(in_key)].get("cluster_name"))
    else:
      pu_cluster_name = self.cluster_name

    _bucket_dict = self.pu_generator.post_upgrade_generator(
      in_key=copy.deepcopy(str(in_key)),
      jobs=copy.deepcopy(jobs),
      cluster_name=copy.deepcopy(pu_cluster_name),
      action=upgrade_action,
      user_ts=user_ts,
      disable_bucket=disable_bucket
    )

    if _bucket_dict is None:
      INFO("Bucket Dict not available.")
      INFO("No tests to be executed "+upgrade_action)
    else:

      if ((metadata.PRE_POST_UPGRADE_HEADERS[upgrade_action][0] not in
           metadata.AHV_AOS_UPGRADE_HEADERS) and (
             metadata.PRE_POST_UPGRADE_HEADERS[upgrade_action][1] not in
             metadata.AHV_AOS_UPGRADE_HEADERS)):
        metadata.AHV_AOS_UPGRADE_HEADERS.extend(
          metadata.PRE_POST_UPGRADE_HEADERS[upgrade_action]
        )

      if ((metadata.PRE_POST_UPGRADE_HEADERS[upgrade_action][0] not in
           metadata.AHV_UPGRADE_HEADERS) and (
             metadata.PRE_POST_UPGRADE_HEADERS[upgrade_action][1] not in
             metadata.AHV_UPGRADE_HEADERS)):
        metadata.AHV_UPGRADE_HEADERS.extend(
          metadata.PRE_POST_UPGRADE_HEADERS[upgrade_action]
        )
      with self._global_lock:
        for index in range(int(in_key), int(in_key)+_batch_size):
          (database.matrices[action][str(out_key)]
           [str(index)]).update(
             {
               "bucket_dict": _bucket_dict
             })

      self._post_upgrade_executor(
        jobs=jobs,
        bucket_dict=copy.deepcopy(_bucket_dict),
        action=copy.deepcopy(action),
        out_key=copy.deepcopy(str(out_key)),
        in_key=copy.deepcopy(str(in_key)),
        action_str=action_str,
        upgrade_action=upgrade_action
      )

      self._pu_data_manipulator(
        action=copy.deepcopy(action),
        out_key=copy.deepcopy(str(out_key)),
        in_key=copy.deepcopy(str(in_key)),
        action_str=action_str,
        upgrade_action=upgrade_action
      )
      INFO(json.dumps(database.matrices[action][str(out_key)]
                      [str(in_key)]["bucket_dict"]))
      if action not in metadata.STATIC_IGNORE_IMAGING_ACTIONS:
        self._update_db_with_local()
      self.emailer.send_mail(
        out_key=copy.deepcopy(str(out_key)),
        in_key=copy.deepcopy(str(in_key)),
        action=copy.deepcopy(action),
        mail_type=copy.deepcopy(upgrade_action)
      )
