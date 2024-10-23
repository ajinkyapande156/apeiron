"""
Copyright (c) 2022 Nutanix Inc. All rights reserved.

Author: vedant.dalal@nutanix.com
"""
from datetime import datetime
import json
import copy
from threading import RLock

from framework.lib.nulog import INFO
from libs.ahv.workflows.one_click import metadata
from libs.ahv.workflows.one_click import database
from libs.ahv.workflows.one_click.buckets import ahv
from libs.ahv.workflows.one_click.jita_v2_client \
  import JitaClient

class PostUpgradeGenerator():
  """
  Class to manipulate and generate a Post Upgrade Job Profile to be executed
  after the upgrade or deployment
  """

  def __init__(self):
    """
    Constructor Method
    """
    self.jita = JitaClient(
      username="svc.ahv-qa",
      password="6TcU84qZiZHTvFu!#jDD"
    )
    self._lock = RLock()
    self.test_file_map = {
      "ahv": ahv.BUCKETS
    }

  def get_post_upgrade_job_profile(self, matrix_index, matrix_len, jobs):
    """
    A method to generate post upgrade job profile to be executed

    Args:
      matrix_index(int): Index pointting the current execution
      matrix_len(int): Length of the matrix
      jobs(dict): Jobs Dictionary

    Returns:
      post_upgrade_jp(str): Post Upgrade job profile Name
    """
    job_profile_name = None
    tests_jp = []
    testset_id_list = []

    for feature in metadata.JOB_JSON_KEYS_TO_DELETE:
      if feature in jobs.keys():
        if "post_upgrade_tests" in jobs[feature].keys():
          testset_id_list.extend(self._get_pu_testset_id(
            matrix_index=matrix_index, matrix_len=matrix_len,
            jobs=jobs, action=feature))

    for each_ts in testset_id_list:
      tests_jp.append({"$oid": each_ts})

    jp_payload = metadata.PU_JOB_PROFILE_PAYLOAD
    jp_payload["name"] = ("jp_pu_v"+str(jobs["ahv_version"])+"_"+
                          str(jobs["aos_version"])+
                          datetime.now().strftime("%d-%m-%Y %H:%M:%S"))

    jp_payload["test_sets"] = tests_jp

    self.jita.create_job_profile(payload=jp_payload)

    return job_profile_name

  def generate_pu_test_dict(self, action, p1=False):#pylint: disable=no-self-use
    """
    A method to fetch and generate dictionary based on the tests in buckets.

    Args:
      action(str): Pre Upgrade or Post Upgrade
      p1(bool): Flag to check if p1 tests to be added

    Returns:
      bucketized_dict(dict): Dict containing the Bucket details
    """
    bucketized_dict = {}
    if not hasattr(self, 'product'):
      INFO("Product not recognised")
      return bucketized_dict

    for each_file in self.test_file_map.get(self.product, []):
      # if each_file.endswith(".json"):
      INFO("Bucket Name: "+str(each_file)+" added.")
      bucketized_dict.update({
        each_file: {}
      })

      main_data = self.test_file_map[self.product].get(each_file)
      INFO("generate_pu_test_dict file: "+json.dumps(main_data))
      if action in main_data.keys():
        data = main_data[action]
        for keys in data.keys():
          bucketized_dict[str(each_file)].update({
            str(keys): {}
          })
          ts_dict = data[keys]
          if p1:
            if "p1" in ts_dict:
              del ts_dict["p1"]
          bucketized_dict[str(each_file)][str(keys)].update(
            {
              "is_triggered": False,
              "is_executed": False,
              "testsets": ts_dict
            }
          )

    INFO("Bucketized Test Dictionary: "+json.dumps(bucketized_dict))
    return bucketized_dict

  def check_test_availability(self, action, p0=False, p1=False):
    """
    A method to check the availability of tests in the created buckets.

    Args:
      action(str): Upgrade Action (pre_upgrade or post_upgrade).
      p0(bool): P0 Tests to be checked.
      p1(bool): P1 Tests to be checked.

    Returns:
      True/False(bool): True/False based on tests availability.
    """
    bucket_dict = self.generate_pu_test_dict(action=action)
    INFO("Fetched the Post Upgrade Dictionary.")

    for bucket in bucket_dict:
      if len(bucket_dict[bucket].keys()) > 0:
        for feat in bucket_dict[bucket].keys():
          if p0 and p1:
            if ("p0" in bucket_dict[bucket][feat]["testsets"] and
                "p1" in bucket_dict[bucket][feat]["testsets"]):
              return True
          elif p0:
            if "p0" in bucket_dict[bucket][feat]["testsets"]:
              return True
          elif p1:
            if "p1" in bucket_dict[bucket][feat]["testsets"]:
              return True
          else:
            if ("p0" in bucket_dict[bucket][feat]["testsets"] or
                "p1" in bucket_dict[bucket][feat]["testsets"]):
              return True

    return False

  def post_upgrade_generator(self, in_key, jobs, cluster_name, action,#pylint: disable=too-many-locals
                             disable_bucket=False, user_ts=None):
    """
    A method to help generate the data over the different buckets

    Args:
      in_key(str): In Key of Matrix.
      jobs(dict): Jobs
      cluster_name(str): Name of the cluster to be executed on.
      action(str): Post Upgrade or Pre Upgrade.
      disable_bucket(bool): Bucket needs to be disabled or not.
      user_ts(list): User provided upgrade action to be executed.

    Returns:
      bucket_dict(dict): Buckets Dict.
    """
    self.product = jobs.get("product", "")
    top_rows = 2
    p1 = False
    bucket_dict = {}
    if "top_rows_for_buckets" in jobs.keys():
      top_rows = jobs["top_rows_for_buckets"]

    if self.check_test_availability(action=action):
      if int(in_key)+1 > top_rows:
        p1 = True

      if not disable_bucket:
        pu_test_dict = copy.deepcopy(
          self.generate_pu_test_dict(p1=p1, action=action)
        )
        bucket_dict.update(pu_test_dict)
        INFO("bucket dict after updating: "+json.dumps(bucket_dict))
      else:
        INFO("disable bucket info")
    else:
      INFO("Not available in the Buckets")
    if user_ts is not None:
      bucket_dict.update({
        "user_input": {
          "user_input": {
            "is_triggered": False,
            "is_executed": False,
            "testsets": {
              "p0": user_ts
            }
          }
        }
      })
    INFO("Intermediate Bucket Dict: "+json.dumps(bucket_dict))
    for bucket in bucket_dict:
      if len(bucket_dict[bucket].keys()) > 0:
        for feat in bucket_dict[bucket].keys():
          bucket_dict[bucket][feat].update(
            {
              "testset_name": {},
              "testset_id": {},
              "job_profile_name": {},
              "job_profile_id": {}
            }
          )
          for key in bucket_dict[bucket][feat]["testsets"].keys():
            ts_list = []
            for each_ts in bucket_dict[bucket][feat]["testsets"][key]:
              ts_id = self.jita.get_test_set_id(
                test_set_name=each_ts
              )

              ts_info = self.jita.get_testset_info(
                testset_id=ts_id
              )

              ts_list.extend(ts_info["tests"])

              ts_payload = metadata.TEST_SET_PAYLOAD
              ts_name = (str(bucket)+"_"+str(feat)+"_"+str(key)+"_ts_"+
                         str(datetime.now().strftime(
                           "%d-%m-%Y_%H:%M:%S"
                         )))
              ts_payload["name"] = ts_name
              ts_payload["tests"] = ts_list
              ts_payload["args_map"] = ts_info["args_map"]
              ts_payload["agave_options"] = ts_info["agave_options"]

              self.jita.create_testset(payload=ts_payload)

              final_ts_id = self.jita.get_test_set_id(
                test_set_name=ts_name
              )
              jp_name = (str(bucket)+"_"+str(feat)+"_"+str(key)+"_jp_"+
                         str(datetime.now().strftime(
                           "%d-%m-%Y_%H:%M:%S"
                         )))
              jp_id = self._pu_jp_builder(
                ts_id=final_ts_id,
                cluster_name=cluster_name,
                jp_name=jp_name
              )

              bucket_dict[bucket][feat]["testset_name"].update(
                {
                  str(key): str(ts_name)
                }
              )
              bucket_dict[bucket][feat]["testset_id"].update(
                {
                  str(key): str(final_ts_id)
                }
              )
              bucket_dict[bucket][feat]["job_profile_name"].update(
                {
                  str(key): str(jp_name)
                }
              )
              bucket_dict[bucket][feat]["job_profile_id"].update(
                {
                  str(key): str(jp_id)
                }
              )

              INFO("Bucket for "+str(bucket)+"_"+str(feat)+": "+
                   json.dumps(bucket_dict[bucket][feat]))

    INFO("Final Bucket Dict: "+json.dumps(bucket_dict))
    return bucket_dict if bool(bucket_dict) else None

  def _pu_jp_builder(self, ts_id, cluster_name, jp_name):
    """
    A method to build the payload for Post Upgrade job Profile.

    Args:
      ts_id(str): Final PU testset ID.
      cluster_name(str): Cluster Name
      jp_name(str): Job Profile Name

    Returns:
      final_jp_id(str): Job Profile ID
    """

    jp_payload = metadata.PU_JP_PAYLOAD

    jp_payload["name"] = jp_name
    jp_payload["infra"][0]["entries"] = [cluster_name]
    if database.resource_manager[cluster_name].get("pc_name"):
      jp_payload["infra"][0]["entries"].append(
        database.resource_manager[cluster_name]["pc_name"]
      )
    if database.resource_manager[cluster_name].get("selenium_vm_name"):
      jp_payload["infra"][0]["entries"].append(
        database.resource_manager[cluster_name]["selenium_vm_name"]
      )
    jp_payload["test_sets"][0]["$oid"] = ts_id

    final_jp_name = self.jita.create_job_profile(
      payload=jp_payload
    )

    final_jp_id = self.jita.get_job_profile_id(
      job_profile_name=final_jp_name
    )

    return final_jp_id

  def _get_pu_testset_id(self, matrix_index, matrix_len, jobs, action):
    """
    A method to generate Post upgrade testset for each feature

    Args:
      matrix_index(int): Index pointting the current execution.
      matrix_len(int): Length of the matrix.
      jobs(dict): Jobs Dictionary.
      action(str): Suite Name to be executed.

    Returns:
      testset_id(str): Generated Testset ID.
    """
    testset_id = []
    p0_execution_percent = (metadata.DEFAULT_POST_UPGRADE
                            ["p0_execution_percent"])
    if ("p0_execution_percent" in jobs[action]
        ["post_upgrade_tests"].keys()):
      p0_execution_percent = (jobs[action]["post_upgrade_tests"]
                              ["p0_execution_percent"])

    p1_execution_percent = (metadata.DEFAULT_POST_UPGRADE
                            ["p1_execution_percent"])
    if ("p1_execution_percent" in jobs[action]
        ["post_upgrade_tests"].keys()):
      p1_execution_percent = (jobs[action]["post_upgrade_tests"]
                              ["p1_execution_percent"])

    p2_execution_percent = (metadata.DEFAULT_POST_UPGRADE
                            ["p2_execution_percent"])
    if ("p2_execution_percent" in jobs[action]
        ["post_upgrade_tests"].keys()):
      p2_execution_percent = (jobs[action]["post_upgrade_tests"]
                              ["p2_execution_percent"])

    ## P0 Testset Generation
    p0_ts_id = self._generate_testset_from_each_priority(
      action="p0", jobs=jobs
    )
    testset_id.extend(p0_ts_id)

    ## P1 Testset Generation
    p1_paths = (int)((p1_execution_percent/100)*((matrix_len*100)/
                                                 p0_execution_percent))

    if matrix_index+1 < p1_paths:
      p1_ts_id = self._generate_testset_from_each_priority(
        action="p1", jobs=jobs
      )
      testset_id.extend(p1_ts_id)

    ## P2 Testset Generation
    p2_paths = (int)((p2_execution_percent/100)*((matrix_len*100)/
                                                 p0_execution_percent))

    if matrix_index+1 < p2_paths:
      p2_ts_id = self._generate_testset_from_each_priority(
        action="p2", jobs=jobs
      )
      testset_id.extend(p2_ts_id)

    return testset_id

  def _generate_testset_from_each_priority(self, action, jobs):
    """
    A method to generate Test set from each priority.

    Args:
      action(str): Suite name to be executed.
      jobs(dict): Jobs Dictionary.

    Returns:
      testset_id(str): Generated Testset ID.
    """
    testset_id = []
    if str(action)+"_tc" in jobs[action]["post_upgrade_tests"].keys():
      p_testset_id = self._generate_testset_from_testcase(
        action=action, jobs=jobs
      )
      testset_id.append(p_testset_id)

    if str(action)+"_ts" in jobs[action]["post_upgrade_tests"].keys():
      p_testset_id = self._generate_testset_from_testset(
        action=action, jobs=jobs
      )
      testset_id.extend(p_testset_id)

    if str(action)+"_jp" in jobs[action]["post_upgrade_tests"].keys():
      p_testset_id = self._generate_testset_from_job_profile(
        action=action, jobs=jobs
      )
      testset_id.extend(p_testset_id)

    return testset_id

  def _generate_testset_from_testcase(self, action, jobs):
    """
    A method to generate Test set from Testcase.

    Args:
      action(str): Suite name to be executed.
      jobs(dict): Jobs Dictionary.

    Returns:
      testset_id(str): Generated Testset ID.
    """
    testset_payload = metadata.TEST_SET_PAYLOAD
    testset_payload["name"] = (str(action)+"_tc_pu_v"+str(jobs["ahv_version"])
                               +"_"+str(jobs["aos_version"])+
                               datetime.now().strftime("%d-%m-%Y %H:%M:%S"))
    tc_name_ts = testset_payload["name"]
    for each_tc in jobs[action]["post_upgrade_tests"][str(action)+"_tc"]:
      testset_payload["tests"].append({"name": each_tc})

    self.jita.create_testset(payload=testset_payload)
    testset_id = self.jita.get_test_set_id(test_set_name=tc_name_ts)

    return testset_id

  def _generate_testset_from_testset(self, action, jobs):
    """
    A method to generate Test set from Testset.

    Args:
      action(str): Suite name to be executed.
      jobs(dict): Jobs Dictionary.

    Returns:
      testset_id(str): Generated Testset ID.
    """
    testset_id = []

    for each_ts in jobs[action]["post_upgrade_tests"][str(action)+"_ts"]:
      ts_id = self.jita.get_test_set_id(test_set_name=each_ts)
      testset_id.append(ts_id)

    return testset_id

  def _generate_testset_from_job_profile(self, action, jobs):
    """
    A method to generate Test set from Job Profile.

    Args:
      action(str): Suite name to be executed.
      jobs(dict): Jobs Dictionary.

    Returns:
      testset_id(str): Generated Testset ID.
    """
    testset_id = []

    for each_jp in jobs[action]["post_upgrade_tests"][str(action)+"_jp"]:
      ts_id = []
      job_prof_id = self.jita.get_job_profile_id(job_profile_name=each_jp)
      job_prof_details = self.jita.get_job_profile_info(
        job_profile_id=job_prof_id
      )

      for test_set_id in job_prof_details["data"]["test_sets"]:
        ts_id.append(test_set_id)

      testset_id.extend(ts_id)

    return testset_id
