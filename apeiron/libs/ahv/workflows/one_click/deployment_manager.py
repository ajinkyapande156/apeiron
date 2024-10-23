
"""
Copyright (c) 2022 Nutanix Inc. All rights reserved.

Author: vedant.dalal@nutanix.com
"""
# pylint:disable=inconsistent-return-statements
import time
import copy
import json
from datetime import datetime
from multiprocessing import RLock
from framework.lib.nulog import INFO, STEP, ERROR
from libs.ahv.workflows.one_click \
  import database, metadata as metadata
from libs.ahv.workflows.one_click.jarvis_client \
  import JarvisClient
from libs.ahv.workflows.one_click.args_manipulator \
  import ArgsManipulator
from libs.ahv.workflows.one_click.rdm_client \
  import RDMClient
from libs.ahv.workflows.one_click.emailer \
  import Emailer
from libs.ahv.workflows.one_click.jita_v2_client \
  import JitaClient
from workflows.acropolis.apeiron.framework.helper_module import ApeironUtil

class DeploymentManager():
  """
  A class containing Cluster Deployment Module.
  """

  def __init__(self):
    """
    Constructor Method.
    """
    self._resource_lock = RLock()
    self._db_lock = RLock()
    self.jarvis = JarvisClient(
      username="svc.ahv-qa",
      password="6TcU84qZiZHTvFu!#jDD"
    )
    self.emailer = Emailer()
    self.jita_client = JitaClient(
      username="svc.ahv-qa",
      password="6TcU84qZiZHTvFu!#jDD"
    )
    self.args_manipulator = ArgsManipulator()
    self.rdm = RDMClient(
      username="svc.ahv-qa",
      password="6TcU84qZiZHTvFu!#jDD"
    )
    self.merit_rdm = RDMClient(
      username="svc.merit",
      password="ktqbF*cp+m9wjx8SPT2h"
    )
    self.ndk_rdm = RDMClient(
      username="svc-ndk-qa",
      password="+fwWa?Q%NkB*Gr3cngY6"
    )

    self.RDM_PRODUCT_MAP = {#pylint: disable=invalid-name
      "csi": self.ndk_rdm,
      "ahv": self.rdm,
      "objects": self.merit_rdm,
      "msp": self.rdm,
      "ndk": self.ndk_rdm
    }

  @staticmethod
  def fetch_models_from_resource_manager():
    """
    A method to add clusters to resource manager

    Returns:
      model_dict(dict): Dict containing the platform and gpu models available
                        in resource manager.
    """
    model_dict = {
      "platforms": [],
      "gpu_models": []
    }

    for cluster in database.resource_manager:
      if ("platform" in database.resource_manager[cluster].keys() and
          database.resource_manager[cluster]["platform"] != ""):
        model_dict["platforms"].append(
          database.resource_manager[cluster]["platform"]
        )
      if ("gpu_model" in database.resource_manager[cluster].keys() and
          database.resource_manager[cluster]["gpu_model"] != ""):
        model_dict["gpu_models"].append(
          database.resource_manager[cluster]["gpu_model"]
        )

    return model_dict

  def resource_manager(self, jobs, action, out_key, in_key):#pylint: disable=too-many-locals,too-many-branches,too-many-statements,too-many-return-statements
    """
    Method to fetch a cluster from the resource manager.

    Args:
      jobs(dict): Jobs for the row to be executed.
      action(str): Suite to be executed
                   (e.g ahv_upgrade/ahv_aos_upgrade/deployment_path)
      out_key(str): Key of the outer Loop
      in_key(str): Key of the inner Loop

    Returns:
      cluster_name(str): Cluster Name
    """
    gpu_model = None
    platform = None
    nos_url = None
    test_dict = copy.deepcopy(database.matrices[action][out_key][in_key])
    if "GPU_Model" in test_dict.keys():
      gpu_model = test_dict["GPU_Model"]
      if gpu_model == "":
        gpu_model = None
    platform = test_dict["Platform"]
    if platform == "":
      platform = None
    cluster_name = None
    counter = 0
    if "nos_url" in jobs.keys():
      nos_url = jobs["nos_url"]
    INFO("Resource Manager: "+json.dumps(database.resource_manager))
    for cluster in database.resource_manager:#pylint: disable=too-many-nested-blocks
      # if "Start_Time" in database.resource_manager[cluster].keys():
      #   curr_time = datetime.strptime(
      #     datetime.now().strftime("%d-%m-%Y %H:%M:%S"), "%d-%m-%Y %H:%M:%S"
      #   )
      #   start_time = datetime.strptime(
      #     database.resource_manager[cluster]["Start_Time"],
      #     "%d-%m-%Y %H:%M:%S"
      #   )
      #   total_time = int((curr_time - start_time).total_seconds())
      #   if total_time > 45000:
      #     with self._resource_lock:
      #       database.resource_manager[cluster]["is_available"] = True
      if not database.resource_manager[cluster]["preserve_cluster"] and (
          database.resource_manager[cluster]["is_available"]
      ):
        if jobs.get("suite_based_resource_manager"):
          if database.resource_manager[cluster]["suite"] == action:
            if (test_dict.get("cluster_size") and database.resource_manager
                [cluster].get("nodes")):
              if (database.resource_manager
                  [cluster].get("nodes") >= test_dict.get("cluster_size")):
                if action == "ngd_ahv_upgrade":
                  if gpu_model is not None:
                    if gpu_model == (database.resource_manager[cluster]
                                     ["gpu_model"]):
                      counter += 1
                  else:
                    counter += 1
                else:
                  if platform is not None:
                    if platform == (database.resource_manager[cluster]
                                    ["platform"]):
                      counter += 1
                  else:
                    counter += 1
            else:
              if action == "ngd_ahv_upgrade":
                if gpu_model is not None:
                  if gpu_model == (database.resource_manager[cluster]
                                   ["gpu_model"]):
                    counter += 1
                else:
                  counter += 1
              else:
                if platform is not None:
                  if platform == (database.resource_manager[cluster]
                                  ["platform"]):
                    counter += 1
                else:
                  counter += 1
        else:
          if (test_dict.get("cluster_size") and database.resource_manager
              [cluster].get("nodes")):
            if (database.resource_manager
                [cluster].get("nodes") >= test_dict.get("cluster_size")):
              if action == "ngd_ahv_upgrade":
                if gpu_model is not None:
                  if gpu_model == (database.resource_manager[cluster]
                                   ["gpu_model"]):
                    counter += 1
                else:
                  counter += 1
              else:
                if platform is not None:
                  if platform == (database.resource_manager[cluster]
                                  ["platform"]):
                    counter += 1
                else:
                  counter += 1
          else:
            if action == "ngd_ahv_upgrade":
              if gpu_model is not None:
                if gpu_model == (database.resource_manager[cluster]
                                 ["gpu_model"]):
                  counter += 1
              else:
                counter += 1
            else:
              if platform is not None:
                if platform == database.resource_manager[cluster]["platform"]:
                  counter += 1
              else:
                counter += 1
    INFO("Resource Manager Counter: "+str(counter))
    if counter > 0: #pylint: disable=too-many-nested-blocks
      for cluster in database.resource_manager:
        if not database.resource_manager[cluster]["preserve_cluster"] and (
            database.resource_manager[cluster]["is_available"]
        ):
          if jobs.get("suite_based_resource_manager"):
            if database.resource_manager[cluster]["suite"] == action:
              if (test_dict.get("cluster_size") and database.resource_manager
                  [cluster].get("nodes")):
                if (database.resource_manager
                    [cluster].get("nodes") >= test_dict.get("cluster_size")):
                  if platform is not None:
                    if platform == (database.resource_manager[cluster]
                                    ["platform"]):
                      cluster_name = cluster
                  else:
                    cluster_name = cluster
                  with self._resource_lock:
                    database.resource_manager[cluster]["is_available"] = False
                    database.resource_manager[cluster].update(
                      {
                        "Start_Time": (
                          datetime.now().strftime("%d-%m-%Y %H:%M:%S")
                        )
                      }
                    )
                  INFO("Resource Manager returns cluster: "+str(cluster_name))
                  return cluster_name
              else:
                if platform is not None:
                  if platform == database.resource_manager[cluster]["platform"]:
                    cluster_name = cluster
                else:
                  cluster_name = cluster
                with self._resource_lock:
                  database.resource_manager[cluster]["is_available"] = False
                  database.resource_manager[cluster].update(
                    {
                      "Start_Time": (
                        datetime.now().strftime("%d-%m-%Y %H:%M:%S")
                      )
                    }
                  )
                INFO("Resource Manager returns cluster: "+str(cluster_name))
                return cluster_name
          else:
            if (test_dict.get("cluster_size") and database.resource_manager
                [cluster].get("nodes")):
              if (database.resource_manager
                  [cluster].get("nodes") >= test_dict.get("cluster_size")):
                if platform is not None:
                  if platform == database.resource_manager[cluster]["platform"]:
                    cluster_name = cluster
                else:
                  cluster_name = cluster
                with self._resource_lock:
                  database.resource_manager[cluster]["is_available"] = False
                  database.resource_manager[cluster].update(
                    {
                      "Start_Time": datetime.now().strftime("%d-%m-%Y %H:%M:%S")
                    }
                  )
                INFO("Resource Manager returns cluster: "+str(cluster_name))
                return cluster_name
            else:
              if platform is not None:
                if platform == database.resource_manager[cluster]["platform"]:
                  cluster_name = cluster
              else:
                cluster_name = cluster
              with self._resource_lock:
                database.resource_manager[cluster]["is_available"] = False
                database.resource_manager[cluster].update(
                  {
                    "Start_Time": datetime.now().strftime("%d-%m-%Y %H:%M:%S")
                  }
                )
              INFO("Resource Manager returns cluster: "+str(cluster_name))
              return cluster_name

    if "cluster_name" in jobs.keys():
      INFO("Cluster not available in Resource Manager.")
      if self._check_if_all_clusters_to_be_preserved():#pylint: disable=too-many-function-args
        INFO("No more clusters available as all Clusters are"
             " preserved in failure state.")
        return None
      INFO(f"Cluster not available in Resource Manager. "\
           f"Retrying after {metadata.CLUSTER_REQUEST_RETRY_DELAY}s")
      time.sleep(metadata.CLUSTER_REQUEST_RETRY_DELAY)
      return self.resource_manager(
        jobs=copy.deepcopy(jobs),
        action=copy.deepcopy(action),
        out_key=copy.deepcopy(out_key),
        in_key=copy.deepcopy(in_key)
      )

    STEP("Scheduling a Cluster Deployment")
    time_to_break = None
    pool_name = None
    cluster_nodes = test_dict.get("cluster_size", 3)
    if "csi" in action:
      cluster_nodes = 1

    no_of_clusters_rm = len(database.resource_manager.keys())
    if (jobs.get("max_clusters", 30) > no_of_clusters_rm and#pylint: disable=too-many-nested-blocks
        jobs.get("max_clusters", 30) >
        database.SCHEDULED_CLUSTERS.get(cluster_nodes, 0)):
      if jobs.get("max_cluster_based_on_size"):
        if (jobs["max_cluster_based_on_size"].get(str(cluster_nodes)) >
            database.SCHEDULED_CLUSTERS.get(cluster_nodes, 0)):
          INFO("Pools provided: "+str(jobs.get("pool_name")))
          for pool in jobs.get("pool_name"):
            if pool not in ["global-pool"]:
              INFO("Checking the pool: "+str(pool))
              free_nodes = self.args_manipulator.get_num_of_free_nodes(
                node_pool_name=pool
              )
              INFO("No of nodes available in "+str(pool)+" are: "+
                   str(free_nodes))
              if free_nodes >= cluster_nodes:
                with self._resource_lock:
                  pool_name = pool
                  time_to_break = True
                break
            else:
              INFO("Checking the global pool: "+str(pool))
              with self._resource_lock:
                pool_name = pool
                time_to_break = True
              break
      else:
        INFO("Pools provided: "+str(jobs.get("pool_name")))
        for pool in jobs.get("pool_name"):
          if pool not in ["global-pool"]:
            INFO("Checking the pool: "+str(pool))
            free_nodes = self.args_manipulator.get_num_of_free_nodes(
              node_pool_name=pool
            )
            INFO("No of nodes available in "+str(pool)+" are: "+
                 str(free_nodes))
            if free_nodes >= cluster_nodes:
              with self._resource_lock:
                pool_name = pool
                time_to_break = True
              break
          else:
            INFO("Checking the global pool: "+str(pool))
            with self._resource_lock:
              pool_name = pool
              time_to_break = True
            break

    if not time_to_break:
      INFO("No free nodes available in any of the Pools."
           " Retrying after 10 mins.")
      time.sleep(600)
      return self.resource_manager( #pylint: disable=no-value-for-parameter
        jobs=copy.deepcopy(jobs),
        action=copy.deepcopy(action),
        out_key=copy.deepcopy(out_key),
        in_key=copy.deepcopy(in_key)
      )
    deployment_payload = metadata.RDM_DEPLOYMENT_PAYLOAD
    deployment_payload["name"] = ("apeiron_"+str(action)+
                                  str(time.time()).replace(".", ""))
    pe_name = "apeiron_pe_"+str(action)+str(time.time()).replace(".", "")
    deployment_payload["resource_specs"][0]["name"] = pe_name

    INFO(f"Pool name: {pool_name}")
    if self.jarvis.only_all_flash_storage_nodes_in_pool(pool_name=pool_name):
      INFO(f"Pool: {pool_name} contains nodes with only all-flash storage")
      deployment_payload["resource_specs"][0][
        "hardware"]["all_flash_cluster"] = True

    if pool_name in ["global-pool"]:
      if jobs.get("global_pool_coupon"):
        metadata.GLOBAL_POOL_DEPLOYMENT_RES["infra"]["params"]["coupon"] = (
          jobs.get("global_pool_coupon")
        )
      deployment_payload["resource_specs"][0]["resources"] = (
        metadata.GLOBAL_POOL_DEPLOYMENT_RES
      )
    else:
      (deployment_payload["resource_specs"][0]["resources"]
       ["entries"]) = [pool_name]

    if jobs.get("block_nodes_wo_imaging", True):
      INFO("Blocking nodes without imaging them")
      deployment_payload["resource_specs"][0].update({
        "image_resource": False
      })
    else:
      INFO("Nodes would be imaged while reserving clusters, "\
           "update NOS and Hypervisor details in deployment payload")
      (deployment_payload["resource_specs"][0]["software"]["nos"]
       ["version"]) = "master"
      (deployment_payload["resource_specs"][0]["software"]["hypervisor"]
       ["version"]) = "branch_symlink"
      if nos_url is not None:
        (deployment_payload["resource_specs"][0]["software"]["nos"]
         ["build_url"]) = nos_url

    (deployment_payload["resource_specs"][0]["hardware"]
     ["cluster_min_nodes"]) = cluster_nodes
    # if platform is not None:
    #   (deployment_payload["resource_specs"][0]["hardware"]
    #    ["must_run_on_hardware_models"][0]) = platform

    if jobs.get("rdm_payload_update"):
      for payload in jobs["rdm_payload_update"]:
        key_to_update = payload["key_to_update"]
        value = payload["value"]
        INFO("Updating the rdm payload for key '{}' with new value "
             "as '{}'".format(key_to_update, value))
        deployment_payload.update(ApeironUtil.search_and_replace(\
          deployment_payload, key_to_update, value))

    INFO(f"Deployment payload: {json.dumps(deployment_payload)}")
    deployment_id = self.RDM_PRODUCT_MAP[jobs.get("product")].deploy_cluster(
      payload=deployment_payload
    )
    INFO("Scheduled Deployment ID: "+deployment_id)
    if deployment_id is not None:
      with self._resource_lock:
        if database.SCHEDULED_CLUSTERS.get(cluster_nodes):
          database.SCHEDULED_CLUSTERS[cluster_nodes] += 1
        else:
          database.SCHEDULED_CLUSTERS.update({
            cluster_nodes: 1
          })
      # List if successful, None if deployment fails
      dep_id = self._poll_deployment_schedule(
        deployment_id=deployment_id, jobs=jobs
      )

      if dep_id is not None:
        dep_id = dep_id[0]
        INFO("Deployment ID: "+str(dep_id))
        cluster_name = self.RDM_PRODUCT_MAP[
          jobs.get("product")
        ].get_cluster_name(
          deployment_id=dep_id
        )[0]
        self.add_cluster_to_resource_manager(
          cluster_list=[{cluster_name: platform}],
          to_be_released=str(deployment_id),
          is_available=False,
          nodes=cluster_nodes,
          suite=action
        )
        return cluster_name
      INFO("Unable to deploy.")
      cluster_name = None
      ERROR("Cluster name could not be fetched")
      INFO("Retrying to Deploy")
      return self.resource_manager( #pylint: disable=no-value-for-parameter
        jobs=copy.deepcopy(jobs),
        action=copy.deepcopy(action),
        out_key=copy.deepcopy(out_key),
        in_key=copy.deepcopy(in_key)
      )
    INFO("Unable to deploy.")
    cluster_name = None
    ERROR("Cluster name could not be fetched")
    INFO("Retrying to Deploy")
    return self.resource_manager( #pylint: disable=no-value-for-parameter
      jobs=copy.deepcopy(jobs),
      action=copy.deepcopy(action),
      out_key=copy.deepcopy(out_key),
      in_key=copy.deepcopy(in_key)
    )


  def deployment_manager(self, jobs, action, out_key, in_key, #pylint: disable=too-many-statements,too-many-branches,too-many-locals,too-many-return-statements
                         cluster_name, batch_size, recurse_limit=None):
    """
    A method to deploy a cluster for executing job profiles

    Args:
      jobs(dict): Jobs for the row to be executed.
      action(str): Suite to be executed
                   (e.g ahv_upgrade/ahv_aos_upgrade/deployment_path)
      out_key(str): Key of the outer Loop
      in_key(str): Key of the inner Loop
      cluster_name(str): Cluster Name to be reimaged
      batch_size(int): Batch Size to be executed together
      recurse_limit(int): Recursive limit incase of Recursion

    Returns:
      cluster_name(str): Cluster Name or None in case of failure.
    """
    foundation_build_url = None
    hypervisor_url = None
    co_imaging = False
    so_imaging = False
    test_dict = copy.deepcopy(database.matrices[action][out_key][in_key])
    if (action not in metadata.IGNORE_IMAGING_ACTIONS or action.split("_")[0]#pylint: disable=too-many-boolean-expressions
        not in metadata.IGNORE_IMAGING_ACTIONS or
        (action in metadata.IGNORE_IMAGING_ACTIONS and
         database.resource_manager[cluster_name]["is_reimaged"] is not True) or
        (test_dict.get("is_feat_execution") and
         database.resource_manager[cluster_name]["is_reimaged"] is not True)):
      if cluster_name is not None:
        STEP("Reimaging the Cluster.")
        nos_url = None
        found_vm_ip = None
        INFO(action)
        src_aos_ver = test_dict[metadata.src_aos_map.get(
          action, "Source_AOS"
        )]
        INFO(src_aos_ver)
        if (jobs.get("product") and action not in
            metadata.GOS_ACTIONS and
            metadata.PRODUCT_SRC_AOS_MAP.get(jobs.get("product"))):
          src_aos_ver = test_dict[
            metadata.PRODUCT_SRC_AOS_MAP.get(jobs.get("product"))
          ]
        if ("nos_url" in jobs.keys() and action not in
            ["ahv_aos_upgrade", "objects_upgrade"] and
            src_aos_ver in jobs.get("nos_url")):
          nos_url = jobs["nos_url"]
        if "foundation_vm_ip" in jobs.keys():
          found_vm_ip = jobs["foundation_vm_ip"]

        src_ahv = (test_dict[metadata.src_ahv_map[action]] if action in
                   metadata.src_ahv_map else "branch_symlink")
        if str(src_ahv.split(".")[0]) == "el6":
          with self._db_lock:
            for index in range(int(in_key), int(in_key)+batch_size):
              database.matrices[action][out_key][str(index)].update(
                metadata.FOUNDATION_MAPPING["el6"]
              )
            test_dict = database.matrices[action][out_key][in_key]
        if "Foundation_URL" in test_dict.keys():
          foundation_build_url = test_dict["Foundation_URL"]
        else:
          foundation_build_url = None

        hypervisor_url = None
        jarvis_cl = JarvisClient(
          username="svc.ahv-qa",
          password="6TcU84qZiZHTvFu!#jDD"
        )
        rdm_client = RDMClient(#pylint: disable=unused-variable
          username="svc.ahv-qa",
          password="6TcU84qZiZHTvFu!#jDD"
        )
        if jobs.get("product") in ["objects"]:
          jarvis_cl = JarvisClient(
            username="svc.merit",
            password="ktqbF*cp+m9wjx8SPT2h"
          )
          rdm_client = RDMClient(#pylint: disable=unused-variable
            username="svc.merit",
            password="ktqbF*cp+m9wjx8SPT2h"
          )
        INFO("foundation_build_url: "+str(foundation_build_url))
        INFO("hypervisor_url: "+str(hypervisor_url))
        imaging_client = rdm_client
        jarvis_imaging = False
        pc_version = None
        selenium_vm = None
        rdm_imaging = False
        pc_build_url = None
        rdm_arg = {}
        if jobs.get("co_imaging"):
          co_imaging = True
        if jobs.get("so_imaging"):
          so_imaging = True
        if jobs.get("jarvis_imaging"):
          imaging_client = jarvis_cl
          jarvis_imaging = True
        if jobs.get("rdm_imaging"):
          imaging_client = rdm_client
          rdm_imaging = True
        if jobs.get("pc_enabled"):
          pc_version = test_dict["Source_PC"]
          INFO("PC Enabled: "+str(pc_version))
          rdm_arg.update({
            "pcvm_size": jobs.get("pcvm_size", "small")
          })
        if jobs.get("selenium_vm_enabled") or test_dict.get(
            "selenium_vm_enabled"):
          selenium_vm = True
          INFO("Selenium VM Enabled: "+str(selenium_vm))
        if jobs.get("pc_build_url") and "upgrade" not in action:
          pc_build_url = jobs.get("pc_build_url")

        if test_dict.get("extra_args", {}).get("rdm"):
          rdm_arg.update(test_dict["extra_args"].get("rdm"))

        image_id = imaging_client.image_cluster(
          cluster_name=copy.deepcopy(cluster_name),
          ahv=copy.deepcopy(src_ahv),
          nos=copy.deepcopy(src_aos_ver),
          nos_url=copy.deepcopy(nos_url),
          found_vm_ip=copy.deepcopy(found_vm_ip),
          foundation_build_url=copy.deepcopy(foundation_build_url),
          hypervisor_url=copy.deepcopy(hypervisor_url),
          co_imaging=copy.deepcopy(co_imaging),
          so_imaging=copy.deepcopy(so_imaging),
          pc_version=copy.deepcopy(pc_version),
          pc_build_url=copy.deepcopy(pc_build_url),
          rdm_arg=copy.deepcopy(rdm_arg),
          selenium_vm=copy.deepcopy(selenium_vm),
          static_ips_to_reserve=jobs.get("static_ips_to_reserve"),
          rdm_payload_update=jobs.get("rdm_payload_update"),
          cluster_size=copy.deepcopy(database.resource_manager
                                     [cluster_name].get("nodes"))
        )
        INFO("Imaging ID: {image_id}".format(image_id=copy.deepcopy(image_id)))
        if image_id is not None:
          self.emailer.send_mail(out_key=copy.deepcopy(out_key),
                                 in_key=copy.deepcopy(in_key),
                                 action=copy.deepcopy(action),
                                 mail_type=copy.deepcopy("cluster_imaging"))
          _poll_status = self._poll_imaging(
            image_id=copy.deepcopy(image_id),
            jarvis_imaging=jarvis_imaging,
            rdm_imaging=rdm_imaging
          )
          if _poll_status is False:
            if recurse_limit is None:
              recurse_limit = 3
            ERROR("Imaging Failed. Retrying. Try no: "+str(recurse_limit))
            time.sleep(600)
            if recurse_limit is not None:
              if recurse_limit > 0:
                # with self._resource_lock:
                # database.resource_manager[cluster_name]["is_available"] = True
                cluster_name = self.deployment_manager(
                  jobs=copy.deepcopy(jobs),
                  action=copy.deepcopy(action),
                  out_key=copy.deepcopy(str(out_key)),
                  in_key=copy.deepcopy(str(in_key)),
                  batch_size=batch_size,
                  cluster_name=copy.deepcopy(cluster_name),
                  recurse_limit=recurse_limit-1
                )
              else:
                ERROR("Imaging Failed.")
                with self._resource_lock:
                  database.resource_manager[cluster_name]["is_available"] = True
                  if test_dict.get("feat_execution"):
                    (database.resource_manager[cluster_name]
                     ["preserve_cluster"]) = True
                with self._db_lock:
                  for index in range(int(in_key), int(in_key)+batch_size):
                    database.matrices[action][out_key][str(index)].update(
                      {
                        "Status": "completed",
                        "Result": "Failed",
                        "Reason": f"Imaging failed. RDM URL: "\
                                  f"{metadata.RDM_SCHEDULED_DEPLOYMENT_URL}/"\
                                  f"{image_id}"
                      }
                    )
                return None
          else:
            INFO("Cluster Imaging Succeeded.")
            dep_id = self.RDM_PRODUCT_MAP[
              jobs.get("product")
            ].get_deployment_id(deployment_id=image_id)
            if dep_id is not None:
              INFO("Deployment ID: "+str(dep_id))
              cluster_name_list = []
              for each_dep_id in dep_id:
                cluster_name_list.append(
                  self.RDM_PRODUCT_MAP[jobs.get("product")].get_cluster_name(
                    deployment_id=each_dep_id
                  )
                )

              INFO("Cluster List: "+str(cluster_name_list))

              pc_name = (None if len(cluster_name_list) < 2 else
                         cluster_name_list[1][1])
              with self._db_lock:
                database.resource_manager[cluster_name].update({
                  "pc_name": pc_name,
                  "is_reimaged": True,
                  "deployment_to_release": image_id
                })
                self.jita_client.add_cluster_to_jita_db(
                  cluster_name=pc_name,
                  cluster_type="$PRISM_CENTRAL"
                )

              sm_vm_name = (None if len(cluster_name_list) < 3 else
                            cluster_name_list[2][1])
              if sm_vm_name:
                with self._db_lock:
                  database.resource_manager[cluster_name].update({
                    "selenium_vm_name": sm_vm_name,
                  })
                  self.jita_client.add_cluster_to_jita_db(
                    cluster_name=sm_vm_name,
                    cluster_type="$SELENIUM_VM"
                  )

              INFO("Update Resource Manager: "+json.dumps(
                database.resource_manager
              ))

              time.sleep(10)
              self.RDM_PRODUCT_MAP[jobs.get("product")].extend_cluster_life(
                rdm_dep_id=image_id
              )
              time.sleep(10)
              self.RDM_PRODUCT_MAP[jobs.get("product")].extend_cluster_life(
                rdm_dep_id=image_id
              )

              return cluster_name
        else:
          if recurse_limit is None:
            recurse_limit = 3
          ERROR("Imaging Failed. Retrying. Try no: "+str(recurse_limit))
          time.sleep(600)
          if recurse_limit is not None:
            if recurse_limit > 0:
              cluster_name = self.deployment_manager(
                jobs=copy.deepcopy(jobs),
                action=copy.deepcopy(action),
                out_key=copy.deepcopy(str(out_key)),
                in_key=copy.deepcopy(str(in_key)),
                batch_size=batch_size,
                cluster_name=copy.deepcopy(cluster_name),
                recurse_limit=recurse_limit-1
              )
            else:
              ERROR("Imaging Failed.")
              with self._resource_lock:
                database.resource_manager[cluster_name]["is_available"] = True
              with self._db_lock:
                for index in range(int(in_key), int(in_key)+batch_size):
                  database.matrices[action][out_key][str(index)].update(
                    {
                      "Status": "completed",
                      "Result": "Failed",
                      "Reason": "Unable to Image the cluster. Imaging Failed"
                    }
                  )
              return None
      else:
        with self._db_lock:
          for index in range(int(in_key), int(in_key)+batch_size):
            database.matrices[action][out_key][str(index)].update(
              {
                "Result": "Failed",
                "Reason": "Unable to Image a cluster (cluster_name = None)"
              }
            )
        ERROR("Unable to Image a cluster")
      return cluster_name
    INFO("Cluster does not need to be reimaged.")
    return cluster_name

  def add_cluster_to_resource_manager(self, cluster_list, ngd=None,#pylint: disable=too-many-branches
                                      to_be_released=None, is_available=None,
                                      nodes=None, suite=None):
    """
    A method to add clusters to resource manager

    Args:
      cluster_list(list): List containing the Cluster and corresponding
                          Platform.
      ngd(bool): NGD Flag.
      to_be_released(bool): Flag regarding the cluster needs to be released.
      is_available(bool): Flag regarding the cluster availability. (Optional)
      nodes(int): Cluster Size/nodes
      suite(str): Suite Name.
    """
    STEP("Add the clusters provided by the user to Resource Manager.")
    if is_available is None:
      is_available = True
    for each_cluster in cluster_list:
      if ngd is not None and ngd:
        if isinstance(each_cluster, dict):
          cluster_name = each_cluster.keys()[0]
          gpu_model_name = each_cluster[cluster_name]
        else:
          cluster_name = each_cluster
          gpu_model_name = self.jarvis.get_gpu_model_from_cluster(
            cluster_name=cluster_name
          )
        with self._resource_lock:
          if cluster_name not in database.resource_manager.keys():
            database.resource_manager.update(
              {
                cluster_name: {
                  "gpu_model": gpu_model_name,
                  "is_available": is_available,
                  "is_reimaged": False,
                  "preserve_cluster": False
                }
              }
            )
            if to_be_released is not None:
              database.resource_manager[cluster_name].update(
                {
                  "to_be_released": to_be_released
                }
              )
            if suite is not None:
              database.resource_manager[cluster_name].update(
                {
                  "suite": suite
                }
              )
            if nodes is not None:
              database.resource_manager[cluster_name].update(
                {
                  "nodes": nodes
                }
              )
            self.jita_client.add_cluster_to_jita_db(
              cluster_name=cluster_name
            )
      else:
        if isinstance(each_cluster, dict):
          cluster_name = list(each_cluster.keys())[0]
          platform_name = each_cluster[cluster_name]
        else:
          cluster_name = each_cluster
          platform_name = ""
        with self._resource_lock:
          if cluster_name not in database.resource_manager.keys():
            database.resource_manager.update(
              {
                cluster_name: {
                  "platform": platform_name,
                  "is_available": is_available,
                  "is_reimaged": False,
                  "preserve_cluster": False
                }
              }
            )
            if to_be_released is not None:
              database.resource_manager[cluster_name].update(
                {
                  "to_be_released": to_be_released
                }
              )
            if suite is not None:
              database.resource_manager[cluster_name].update(
                {
                  "suite": suite
                }
              )
            if nodes is not None:
              database.resource_manager[cluster_name].update(
                {
                  "nodes": nodes
                }
              )
            self.jita_client.add_cluster_to_jita_db(
              cluster_name=cluster_name
            )
    INFO("Cluster added to resource manager.")

  def release_clusters(self, jobs):
    """
    A Method to release all the clusters.

    Args:
      jobs(dict): Jobs Dictionary.
    """

    for cluster in database.resource_manager:
      if database.resource_manager[cluster].get("to_be_released"):
        if database.resource_manager[cluster].get("deployment_to_release"):
          self.RDM_PRODUCT_MAP[jobs.get("product")].release_cluster(
            deployment_id=database.resource_manager[cluster]
            ["deployment_to_release"]
          )
          time.sleep(1200)
        self.RDM_PRODUCT_MAP[jobs.get("product")].release_cluster(
          deployment_id=database.resource_manager[cluster]["to_be_released"]
        )

  @staticmethod
  def _check_if_all_clusters_to_be_preserved():
    """
    A Method to check if all clusters in Resource Manager needs to be
    preserved.

    Returns:
      all_preserved(bool): True if all clusters are preserved.
    """
    all_preserved = True

    for cluster in database.resource_manager:
      if not database.resource_manager.get(cluster).get("preserve_cluster"):
        all_preserved = False
        return all_preserved

    return all_preserved

  def _poll_deployment_schedule(self, deployment_id, jobs, no_of_retry=5000,
                                retry_interval=180):
    """
    A method to poll the Deployment status

    Args:
      deployment_id(str): Deployment ID to be Scheduled.
      jobs(dict): Jobs Dictionary.
      no_of_retry(int): No of retries to be done.
      retry_interval(int): Retry interval between each Retry.

    Returns:
      dep_id(str): Deployment Schedule ID
    """
    dep_id = None
    time.sleep(20)
    while no_of_retry:
      dep_status = self.RDM_PRODUCT_MAP[
        jobs.get("product")
      ].get_deployment_status(deployment_id=deployment_id)
      INFO("Deployment status: " + str(dep_status))
      if dep_status not in [
          "PROCESSING", "PRE_PENDING", "PENDING",
          "REQUESTING_RESOURCES", "RESOURCES_ALLOCATED",
          "REQUESTING_SOFTWARE_RESOURCES", "PROVISIONING_SOFTWARE_RESOURCES",
          "SOFTWARE_RESOURCES_ALLOCATED", "PROVISIONING_RESOURCES",
          "UPDATING_DEPLOYMENTS_WITH_ALLOCATED_RESOURCES",
          "UPDATED_DEPLOYMENTS_WITH_ALLOCATED_RESOURCES"]:
        if dep_status in ["SUCCESS"]:
          time.sleep(60)
          dep_id = self.RDM_PRODUCT_MAP[jobs.get("product")].get_deployment_id(
            deployment_id=deployment_id
          )
        break
      deployment_data = self.RDM_PRODUCT_MAP[
        jobs.get("product")
      ].get_scheduled_deployment_data(deployment_id=deployment_id)
      if deployment_data.get("message"):
        INFO("Deployment Data contains message: " +
             deployment_data.get("message"))
        if metadata.RDM_FAILURE_MSG_1 in deployment_data.get("message"):
          INFO("Deployment in pending state as nodes not available,"
               "releasing the scheduled deployment.")
          self.RDM_PRODUCT_MAP[jobs.get("product")].release_cluster(
            deployment_id=deployment_id
          )
          break
        if metadata.RDM_FAILURE_MSG_2 in deployment_data.get("message"):
          INFO("Not enough free nodes exist in the pool.")
          self.RDM_PRODUCT_MAP[jobs.get("product")].release_cluster(
            deployment_id=deployment_id
          )
          break
      else:
        INFO("Deployment Data does not contain message.")
      time.sleep(retry_interval)
      if no_of_retry == 1:
        INFO("Maximum retries reached. Releasing the scheduled"
             " deployment ID: "+str(deployment_id))
        self.RDM_PRODUCT_MAP[jobs.get("product")].release_cluster(
          deployment_id=deployment_id
        )
      no_of_retry -= 1

    return dep_id

  def _poll_imaging(self, image_id, jarvis_imaging, rdm_imaging,#pylint: disable=no-self-use
                    no_of_retry=1000, retry_interval=180):
    """
    A method to poll Imaging status

    Args:
      image_id(str): Imaging ID to be Polled.
      jarvis_imaging(bool): True if image via Jarvis.
      rdm_imaging(bool): True if image via RDM.
      no_of_retry(int): No of retries to be done.
      retry_interval(int): Retry interval between each Retry.

    Returns:
      task_completed(bool): True if completed, else False.
    """
    task_completed = None
    jarvis_client = JarvisClient(
      username="svc.ahv-qa",
      password="6TcU84qZiZHTvFu!#jDD"
    )
    rdm_client = RDMClient(#pylint: disable=unused-variable
      username="svc.ahv-qa",
      password="6TcU84qZiZHTvFu!#jDD"
    )
    imaging_client = rdm_client
    if jarvis_imaging:
      imaging_client = jarvis_client

    if rdm_imaging:
      imaging_client = rdm_client

    while no_of_retry:
      _image_status = imaging_client.image_status(
        image_id=image_id
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
