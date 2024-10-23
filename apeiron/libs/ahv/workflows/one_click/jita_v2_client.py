"""
Copyright (c) 2021 Nutanix Inc. All rights reserved.

Author: vedant.dalal@nutanix.com
"""
import json
import time
import copy


from framework.lib.tools_client.jita_rest_client import JitaRestClient
from framework.lib.nulog import INFO, ERROR
from libs.ahv.workflows.one_click import metadata

class JitaClient(JitaRestClient):
  """
  Class contains methods overriding the methods of JitaRestClient on v2 API.
  """

  def __init__(self, username=None, password=None):
    """
    Method to initialize

    Args:
      username(str): Username
      password(str): Password
    """
    super(JitaClient, self).__init__(username=username, password=password)
    self.username = username
    self.password = password

  def create_testset(self, payload):
    """
    Create a new testset using payload
    Args:
      payload(json): payload for creating the test set in JITA
    """
    url = "{url}".format(url=metadata.TEST_SET_URL)
    auth_data = (self.username, self.password)

    response = self.post(url=url, auth=auth_data, json=payload, verify=False)
    if response.ok:
      INFO("Test set created successfully.")
    else:
      ERROR("Test set couldn't be created."+response.text)

  def clone_test_set(self, payload):
    """
    Method to clone JITA test set using JITA test set ID.
    Args:
      payload(dict): Payload.

    Returns:
      payload["name"](str): JITA test set name.
    """

    auth_data = (self.username, self.password)

    # INFO(payload)
    # if type(payload) is dict:
    #   payload = json.dumps(payload)
    response = self.post(url=metadata.TEST_SET_CLONE, auth=auth_data,
                         verify=False, json=payload)
    # INFO(response)
    if response.status_code == 200:
      result = response.json()
      if result["success"]:
        INFO("Testset: %s cloned successfully" % payload["name"])
      else:
        ERROR("Testset: couldn't be cloned: %s" % result["message"])
    return payload["name"]

  def get_testset_info(self, testset_id):#pylint: disable=arguments-differ
    """
    Method to get JITA test set details from JITA test set ID.
    Args:
        testset_id(str): JITA test set ID.
    Returns:
        testset_details(dict): JITA test set details/payload.
    """
    url = "{url}/{testset_id}".format(url=metadata.TEST_SET_URL,
                                      testset_id=testset_id)
    testset_details = None

    response = self.get(url=url)
    if response.status_code == 200:
      result = response.json()
      if result["success"] and result["data"]:
        INFO("Testset details found for: %s" % result["data"]["name"])
        testset_details = (result["data"])
        # INFO(testset_details)
      else:
        INFO("Unable to get Test set details: "+response.text)
    return testset_details

  def get_test_set_id(self, test_set_name, no_of_retries=20, retry_interval=15):
    """
    A method to retrieve testset id for the specified testset.

    Args:
      test_set_name(str): Test set name in JITA
      no_of_retries(int): No of times the ID is to be polled.
      retry_interval(int): Time interval between each poll.

    Returns:
      test_set_id(str): testset id, if the testset is valid
                        None, otherwise
    """
    test_set_id = None
    params = {
      "raw_query": json.dumps({
        "name":test_set_name
      })
    }

    while no_of_retries:
      resp = self.get(url=metadata.TEST_SET_URL, params=params)
      if resp.ok and resp.json()["data"]:
        INFO("Testset: {name} found.".format(name=test_set_name))
        test_set_id = resp.json()["data"][0]["_id"]['$oid']
        break
      INFO("Testset: {name} not found. {num} retries left.".format(
        name=test_set_name, num=no_of_retries-1))
      time.sleep(retry_interval)
      no_of_retries -= 1
      if no_of_retries == 0:
        ERROR("Unable to fetch the Testset ID: "+resp.text)
    return test_set_id

  def create_job_profile(self, payload):
    """
    Method that can create job profile for a testset.

    Args:
      payload(json): Json containing model schema for the API.

    Returns:
      payload["name"](str): Name of the Job Profile created.
    """
    auth_data = (self.username, self.password)
    resp = self.post(url=metadata.JOB_PROFILE_URL, auth=auth_data,
                     json=payload, verify=False)

    if resp.status_code == 200:
      if resp.json()["success"]:
        INFO(json.dumps(payload))
        INFO("Job Profile created successfully: "+payload["name"])
      else:
        ERROR("Job Profile couldn't be created msg: "+
              resp.json()["message"])
    else:
      ERROR("Job Profile couldn't be created: "+resp.text)

    return payload["name"]

  def get_job_profile_id(self, job_profile_name, no_of_retries=20,
                         retry_interval=9):
    """
    Method to fetch JITA job profile ID from JITA job profile name.

    Args:
      job_profile_name(str): JITA job profile name.
      no_of_retries(int): No of times the ID is to be polled.
      retry_interval(int): Time interval between each poll.

    Returns:
      job_profile_id(str): JITA job profile ID.
    """
    job_profile_id = None
    params = {
      "raw_query": json.dumps({
        "name":job_profile_name
      })
    }
    INFO("Fetching JP ID for: "+str(job_profile_name))
    while no_of_retries:
      response = self.get(url=metadata.JOB_PROFILE_URL, params=params,
                          verify=False)
      if response.status_code == 200:
        result = response.json()
        if result["data"]:
          INFO("Fetched the Job Profile {jp_name}.".format(
            jp_name=job_profile_name))
          job_profile_id = result["data"][0]["_id"]["$oid"]
          break
        ERROR("Failed to fetch Job Profile ID from JITA. Retrying. "+
              str(no_of_retries-1)+" retries left.")
      time.sleep(retry_interval)
      no_of_retries -= 1
      if no_of_retries == 0:
        ERROR("Unable to fetch the Job Profile ID: "+response.text)
    return job_profile_id

  def get_job_profile_info(self, job_profile_id):
    """
    Method to get JITA job profile details from JITA job profile ID.

    Args:
      job_profile_id(str): JITA job profile ID.

    Returns:
      job_profile_details(dict): JITA job profile details.
    """
    job_profile_details = None
    url = "{base_url}/{jp_id}".format(base_url=metadata.JOB_PROFILE_URL,
                                      jp_id=job_profile_id)

    response = self.get(url=url, verify=False)
    if response.status_code == 200:
      result = response.json()
      if result["success"] and result["data"]:
        INFO("Fetched Job Profile Details")
        job_profile_details = json.dumps(result)
        # INFO(job_profile_details)
      else:
        ERROR("Unable to get Job Profile details: "+response.text)
    return job_profile_details

  def task_trigger(self, job_profile_id):
    """
    A method to trigger a JITA Job Profile.

    Args:
      job_profile_id(str): JITA Job Profile ID

    Returns:
      task_id(str): Task ID of the Triggered Job.
    """
    task_id = None
    url = "{base_url}/{jp_id}/trigger?request_source=ui".format(
      base_url=metadata.JOB_PROFILE_URL, jp_id=job_profile_id)
    auth_data = (self.username, self.password)
    resp = self.post(url=url, auth=auth_data, json={})

    if resp.status_code == 200:
      result = resp.json()
      # INFO(result)
      if result["success"]:
        task_id = result["task_ids"][0]['$oid']
        INFO("Job Profile triggered successfully: "+str(task_id))
      else:
        ERROR("Failed to trigger the Job profile: "+
              result["message"])
    return task_id

  def get_reg_agave_task_status(self, task_id, no_of_retries=240,
                                retry_interval=300):
    """
    Method that can be used to fetch the status of a task.

    Args:
      task_id(str): Task ID of the job profile triggered.
      no_of_retries(int): No of times the status is to be polled.
      retry_interval(int): Time interval between each poll.

    Returns:
      upgrade_list(list): List updated with the Result and Reason.
    """
    task_status = False
    url = "{base_url}/{task_id}".format(
      base_url=metadata.TASK_POLL_URL, task_id=task_id
    )
    while no_of_retries:
      response = self.get(url=url)
      if response.status_code == 200:
        result = response.json()
        if result["success"]:
          if result["data"]["status"] == "completed":
            INFO("Task Status fetched successfully and is completed.")
            task_status = True
            break
          ERROR("Task Status is not completed. Retrying."
                " {num} retries left".format(num=no_of_retries-1))
      INFO("Current Status ->[%s]" % (result["data"]["status"]))
      INFO("Retrying")
      time.sleep(retry_interval)
      no_of_retries -= 1
    return task_status

  def get_agave_task_status(self, task_id):
    """
    Method that can be used to fetch the status of a task.

    Args:
      task_id(str): Task ID of the Task triggered.

    Returns:
      upgrade_list(list): List updated with the Result and Reason.
    """
    _task_status = None
    response = self.get(url="{base_url}/{task_id}".format(
      base_url=metadata.TASK_POLL_URL, task_id=task_id))
    if response.status_code == 200:
      if response.json()["success"]:
        if response.json()["data"]["status"]:
          INFO("Task Status fetched successfully.")
          _task_status = response.json()["data"]["status"]
        else:
          INFO("Task Status couldn't be fetched.")
    return _task_status

  def get_agave_test_result_count(self, task_id):
    """
    Method that can be used to fetch the status of a task.

    Args:
      task_id(str): Task ID of the Task triggered.

    Returns:
      upgrade_list(list): List updated with the Result and Reason.
    """
    _task_result = None
    response = self.get(url="{base_url}/{task_id}".format(
      base_url=metadata.TASK_POLL_URL, task_id=task_id))
    if response.status_code == 200:
      if response.json()["success"]:
        if response.json()["data"]["test_result_count"]:
          INFO("Task Status fetched successfully.")
          _task_result = response.json()["data"]["test_result_count"]
        else:
          INFO("Task Status couldn't be fetched.")
    return _task_result

  def get_jita_task_details(self, task_id):
    """
    Method that can be used to fetch the status of a task.

    Args:
      task_id(str): Task ID of the Task triggered.

    Returns:
      _task_details(dict): Task Details Dictionary.
    """
    _task_details = None
    response = self.get(url="{base_url}/{task_id}".format(
      base_url=metadata.TASK_POLL_URL, task_id=task_id))
    if response.status_code == 200:
      if response.json()["success"]:
        if response.json().get("data"):
          INFO("Task Details fetched successfully.")
          _task_details = response.json()["data"]
        else:
          INFO("Task Details couldn't be fetched.")
    return _task_details

  def get_cluster_name(self, task_id):
    """
    Method to retrieve deployed cluster name

    Args:
      task_id(str): Agave Task ID.

    Returns:
      cluster_name(str): Name of the Deployed Platform.
    """
    auth_data = (self.username, self.password)
    cluster_name = None
    payload = metadata.TASK_DEPLOYMENT_PAYLOAD
    payload["raw_query"]["task_id"]["$in"][0]["$oid"] = task_id
    response = self.post(url=metadata.TASK_DEPLOYMENT_URL, auth=auth_data,
                         json=payload, verify=False)

    if response.status_code == 200:
      result = response.json()
      if result["success"] and result["data"]:
        INFO("Fetched Deployed Cluster Name.")
        for i in range(len(result["data"])):
          if (result["data"][i].get("status") and
              result["data"][i].get("status") == "released"):
            if (result["data"][i].get("allocated_resources") and#pylint: disable=no-else-break
                (result["data"][i].get("allocated_resources")
                 [0].get("resource_name"))):
              cluster_name = (
                result["data"][i]["allocated_resources"][0]["resource_name"])
              break
            else:
              INFO("Allocated Resources not available or"
                   " does not have resource_manager")
          else:
            INFO("Status not available or not completed")
      else:
        INFO("Couldn't fetch the Cluster name.")
    else:
      INFO("Couldn't find the Platform model.")
    return cluster_name

  def get_platform_model(self, cluster_name):
    """
    Method to fetch the Model of deployed platform.

    Args:
      cluster_name(str): Cluster name.

    Returns:
      platform_model(str): Name of the Deployed Platform.
    """
    url = "{base_url}/{cluster_id}".format(
      base_url=metadata.JARVIS_CLUSTER_URL,
      cluster_id=cluster_name)
    platform_model = None
    response = self.get(url=url)

    if response.status_code == 200:
      result = response.json()
      if result["success"]:
        if "nodes_cache" in result["data"].keys():
          platform_model = ",".join(result["data"]["nodes_cache"]["model"])
        else:
          ERROR("Couldn't fetch Platform model")
      else:
        ERROR("Couldn't fetch Platform model: "+result["message"])
    else:
      ERROR("Couldn't fetch Platform model: "+response.text)

    return platform_model

  def get_agave_test_result(self, payload):
    """
    Method that can give the execution results.

    Args:
      payload(json): payload for getting the test results in JITA.

    Returns:
      tup(tuple): Tuple containing Reason and Result respectively.
    """
    auth_data = (self.username, self.password)
    tup = ()

    response = self.post(url=metadata.TEST_RESULT_URL, auth=auth_data,
                         json=payload, verify=False)
    if response.status_code == 200:#pylint: disable=too-many-nested-blocks
      result = response.json()
      if result["success"] and result["data"]:
        INFO("Fetched Test Result.")
        reason = "N/A"
        res = []
        for i in range(len(result["data"])):
          res.append(result["data"][i]["status"])
          if "exception_summary" in result["data"][i].keys():
            reason = result["data"][i]["exception_summary"]
          elif "status_transitions" in result["data"][i].keys():
            for ele in result["data"][i]["status_transitions"]:
              if ele["stage"] == "TEST_SKIPPED":
                reason = ele["reason"]
        res = ",".join(set(res))
        INFO("Test Result is "+res)
        tup = (reason, str(res))
      else:
        INFO("Couldn't fetch Test results.")

    return tup

  def delete_job_profile(self, job_profile_id):
    """
    A method to delete a job profile

    Args:
      job_profile_id(str): ID of the Job Profile to be deleted
    """
    url = "{base_url}/{jp_id}".format(
      base_url=metadata.JOB_PROFILE_URL, jp_id=job_profile_id)
    auth_data = (self.username, self.password)

    response = self.delete(url=url, auth=auth_data)
    if response.ok:
      INFO("Job Profile successfully deleted.")
    else:
      ERROR("Job Profile couldn't be deleted." + response.text)

  def delete_testset(self, test_set_id):
    """
    A method to delete a test set

    Args:
      test_set_id(str): ID of the Test set to be deleted
    """
    url = "{base_url}/{test_set_id}".format(
      base_url=metadata.TEST_SET_URL, test_set_id=test_set_id)
    auth_data = (self.username, self.password)

    response = self.delete(url=url, auth=auth_data)
    if response.ok:
      INFO("Test set successfully deleted.")
    else:
      ERROR("Test set coouldn't be deleted." + response.text)

  def add_cluster_to_jita_db(self, cluster_name, cluster_type="$NOS_CLUSTER"):
    """
    A method to add cluster to Jita DB.

    Args:
      cluster_name(str): Cluster Name to be added to Jita DB.
      cluster_type(str): Cluster Type.
    """
    resource_to_add = copy.deepcopy(cluster_name)
    cluster_search_payload = copy.deepcopy(metadata.JITA_DB_SEARCH_PARAMS)
    cluster_search_payload["raw_query"]["name"]["$regex"] = resource_to_add
    cluster_search_payload["raw_query"] = json.dumps(
      cluster_search_payload["raw_query"]
    )
    INFO(cluster_search_payload)
    cluster_search_response = self.get(url=metadata.JITA_CLUSTER_URL,
                                       params=cluster_search_payload,
                                       verify=False)
    INFO(cluster_search_response)
    if cluster_search_response.status_code == 200:
      cluster_search_result = cluster_search_response.json()
      INFO(cluster_search_result)
      if cluster_search_result["success"]:
        INFO("Cluster name is already added in Jita DB.")
        INFO("Checking if the cluster is tagged with the same cluster type.")
        if (cluster_search_result.get("data") and
            len(cluster_search_result["data"]) > 0):
          cluster_db_data = None
          for i in range(len(cluster_search_result["data"])):
            if cluster_search_result["data"][i]["name"] == resource_to_add:
              cluster_db_data = copy.deepcopy(cluster_search_result["data"][i])
          if cluster_db_data is not None:
            response_resource_type = cluster_db_data["type"]
            if response_resource_type == cluster_type:
              INFO("Cluster Type same as the input, no need to update.")
            else:
              INFO("Cluster Type not same as input, need to update.")
              INFO("Trying to delete the cluster entry from Jita DB.")
              resource_id = cluster_db_data["_id"]["$oid"]
              self.delete_resource_from_jita_db(
                resource_id=resource_id
              )

              INFO("Trying to add resource in Jita DB.")
              self.add_resource_to_jita_db(
                resource=resource_to_add,
                resource_type=cluster_type
              )
          else:
            INFO("No Data available.")
            INFO("Adding the cluster to Jita DB.")
            self.add_resource_to_jita_db(
              resource=cluster_name,
              resource_type=cluster_type
            )
        else:
          INFO("No Data available.")
          INFO("Adding the cluster to Jita DB.")
          self.add_resource_to_jita_db(
            resource=cluster_name,
            resource_type=cluster_type
          )

      else:
        INFO("Cluster not present in Jita DB currently.")
        INFO("Adding resource in Jita DB.")
        self.add_resource_to_jita_db(
          resource=cluster_name,
          resource_type=cluster_type
        )

  def delete_resource_from_jita_db(self, resource_id):
    """
    A method to delete the resource from Jita DB.

    Args:
      resource_id(str): Resource ID.
    """
    INFO("Deleting the Resource: "+str(resource_id)+" from Jita DB.")
    auth_data = (self.username, self.password)
    api_url = "{base_url}/{resource_id}".format(
      base_url=metadata.JITA_CLUSTER_URL,
      resource_id=resource_id
    )
    response = self.delete(url=api_url, auth=auth_data, verify=False)

    if response.status_code == 200:
      result = response.json()
      if result["success"]:
        INFO("Cluster name is deleted from Jita DB.")
      else:
        ERROR("Unable to delete the resource from Jita DB.")

  def add_resource_to_jita_db(self, resource, resource_type="$NOS_CLUSTER"):
    """
    A method to add resources to Jita DB

    Args:
      resource(str): Resource Name.
      resource_type(str): Resource Type.

    """
    payload = copy.deepcopy(metadata.JITA_CLUSTER_DB_PAYLOAD)
    auth_data = (self.username, self.password)
    payload["name"] = resource
    if resource_type is not None:
      payload["type"] = resource_type
    payload["fetch_from_jarvis"] = False

    response = self.post(url=metadata.JITA_CLUSTER_URL, auth=auth_data,
                         json=payload, verify=False)

    if response.status_code == 200:
      result = response.json()
      if result["success"]:
        INFO("Cluster name is added to Jita DB.")
      elif result["message"].find("Tried to save duplicate unique keys"):
        INFO("Cluster already exists in the Jita DB.")
      else:
        INFO("Cluster could not be added into Jita DB.")
