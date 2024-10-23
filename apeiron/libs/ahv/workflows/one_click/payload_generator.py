"""
Copyright (c) 2021 Nutanix Inc. All rights reserved.

Author: vedant.dalal@nutanix.com
"""
import copy
import datetime
import json
from urllib.request import urlopen

from framework.lib.nulog import INFO
from libs.ahv.workflows.one_click import metadata
from libs.ahv.workflows.one_click import database
from libs.ahv.workflows.one_click.jita_v2_client \
  import JitaClient
from libs.ahv.workflows.one_click.rdm_client \
  import RDMClient
from libs.ahv.workflows.one_click.args_manipulator \
  import ArgsManipulator
from libs.ahv.workflows.gos_qual.lib.base.utilities \
  import convert_list_to_pos_dict


class PayloadGenerator():
  """
  A class containing methods used to generate payload for Job Profile and
  testset creation.
  """
  def __init__(self):
    """
    Constructor method
    """
    self.username = "svc.ahv-qa"
    self.password = "6TcU84qZiZHTvFu!#jDD"
    self.jita_client = JitaClient(username=self.username,
                                  password=self.password)
    self.rdm_client = RDMClient(username=self.username,
                                password=self.password)
    self.args_manipulator = ArgsManipulator()


  @staticmethod
  def add_infra(fetched_dict, cluster_name):
    """
    A method to create the list for the 'infra' key of the payload
    as per user input.

    Args:
      fetched_dict(dict): Dictionary containing payload fetched from
                         the given job profile.
      cluster_name(str): Cluster Name.

    Returns:
      updated_list(list): List for 'infra' key updated as per user input.
    """
    updated_list = fetched_dict["infra"][0]
    updated_list["type"] = "cluster"
    updated_list["entries"] = [cluster_name]

    return updated_list

  @staticmethod
  def add_hypervisor_version(fetched_dict, ahv_version=None,
                             foundation_build=None,
                             nos_url=None):
    """
    A method to create the dict for the 'requested_hardware' key of the
    payload as per user input, to add the AHV version.

    Args:
      ahv_version(dict): String containing AHV version.
      fetched_dict(dict): Dictionary containing payload fetched from
                          the given job profile.
      foundation_build(str): Foundation Build version.
      nos_url(str): NOS Build URL.

    Returns:
      updated_dict(dict): List for 'requested_hardware' key updated
                          as per user input.
    """
    updated_dict = fetched_dict["requested_hardware"]
    if ahv_version is not None:
      hypervisor_version = (ahv_version.split(".")[2]+"."+
                            ahv_version.split(".")[3])
      updated_dict["hypervisor_version"] = (hypervisor_version)

    if foundation_build is not None:
      updated_dict["imaging_options"]["foundation_build_url"] = (
        foundation_build
      )

    if nos_url is not None:
      updated_dict["imaging_options"]["nos_url"] = nos_url
    return updated_dict

  @staticmethod
  def add_aos_branch_git(aos_version, fetched_dict):
    """
    A method to create the dict for the 'git' key of the
    payload as per user input, to add the AOS branch.

    Args:
      aos_version(str): AOS version to be deployed on.
      fetched_dict(dict): Dictionary containing payload fetched from
                         the given job profile.

    Returns:
      updated_dict(dict): List for 'git' key updated as per user input.
    """
    updated_dict = fetched_dict["git"]
    # print aos_version
    updated_dict["branch"] = ("master" if aos_version == "master"
                              else metadata.AOS_MAPPING[(int(
                                aos_version.split(".")[0]
                              ))].format(x=aos_version))

    return updated_dict

  @staticmethod
  def add_aos_branch_system(aos_version, fetched_dict):
    """
    A method to create the dict for the 'system_under_test' key of the
    payload as per user input, to add the AOS branch.

    Args:
      aos_version(str): AOS version to be deployed on.
      fetched_dict(dict): Dictionary containing payload fetched from
                         the given job profile.

    Returns:
      updated_dict(dict): List for 'system_under_test' key updated as
                          per user input.
    """
    updated_dict = fetched_dict["system_under_test"]
    # print aos_version
    updated_dict["branch"] = ("master" if aos_version == "master"
                              else metadata.AOS_MAPPING[(int(
                                aos_version.split(".")[0]
                              ))].format(x=aos_version))

    return updated_dict

  @staticmethod
  def replace_build_selection(fetched_dict):
    """
    A method to create the dict for the 'build_selection' key of the
    payload as per user input, to replace 'by_latest_RC_tagged'.

    Args:
      fetched_dict(dict): Dictionary containing payload fetched from
                         the given job profile.

    Returns:
      updated_dict(dict): List for 'git' key updated as per user input.
    """
    updated_dict = fetched_dict["build_selection"]
    if (updated_dict.get("by_latest_smoked") and
        not updated_dict.get("build_type")):
      updated_dict.update({
        "build_type": "release"
      })
    return updated_dict

  def testset_param_setter(self, upgrade_dict, jobs): #pylint: disable=no-self-use,too-many-locals,too-many-branches,too-many-statements
    """
    A method to set the testset params

    Args:
      upgrade_dict(str): Upgrade Dictionary.
      jobs(dict): Jobs Dictionary.

    Returns:
      tup(tuple): tuple containing the params
    """
    old_aos = None
    old_ahv = None
    new_aos = None
    new_ahv = None
    new_ahv_list = None
    new_nos_releases = None
    vlan = None
    nos_rim_urls = None
    if "Source_AOS" and "Destination_AOS" in upgrade_dict.keys():
      # INFO("Headers have it")
      old_aos = upgrade_dict["Source_AOS"]
      new_aos = upgrade_dict["Destination_AOS"]
    if "Destination_AHV" in upgrade_dict:
      new_ahv = upgrade_dict["Destination_AHV"]
      old_ahv = upgrade_dict["Source_AHV"]

    if "Mid_AHV_Versions" and "Mid_AOS_Versions" in upgrade_dict.keys():
      new_ahv_list = upgrade_dict.get("Mid_AHV_Versions")
      new_nos_releases = upgrade_dict.get("Mid_AOS_Versions")

    lcm_url = None
    if "LCM_URL" in upgrade_dict.keys():
      lcm_url = upgrade_dict["LCM_URL"]

    ahv_to_lcm_blacklist = None
    product_meta_url = None
    disable_nos_prod_meta = None
    skip_nos_supported_check = None
    new_nos_url = None
    nos_rim_url = None
    binary_location = None
    darksite_bundle_url = None
    host_driver_url = None
    main_test_args = None

    if "vlan" in jobs.keys():
      vlan = jobs["vlan"]
    if "nos_rim_urls" in jobs.keys():
      nos_rim_urls = jobs["nos_rim_urls"]
    if "ahv_to_lcm_blacklist" in jobs.keys():
      ahv_to_lcm_blacklist = jobs["ahv_to_lcm_blacklist"]
    if "product_meta_url" in jobs.keys():
      product_meta_url = jobs["product_meta_url"]
    if "disable_nos_prod_meta" in jobs.keys():
      disable_nos_prod_meta = jobs["disable_nos_prod_meta"]
    if "skip_nos_supported_check" in jobs.keys():
      skip_nos_supported_check = jobs["skip_nos_supported_check"]
    if "darksite_bundle_url" in jobs.keys():
      darksite_bundle_url = jobs["darksite_bundle_url"]
    if "nos_url" in jobs.keys():
      new_nos_url = jobs["nos_url"]
    if "nos_rim_url" in jobs.keys():
      nos_rim_url = jobs["nos_rim_url"]
    if jobs.get("binary_location"):
      binary_location = jobs.get("binary_location")

    if upgrade_dict.get("darksite_bundle_url"):
      darksite_bundle_url = upgrade_dict["darksite_bundle_url"]
    if upgrade_dict.get("host_driver_url"):
      host_driver_url = upgrade_dict["host_driver_url"]
    if jobs.get("main_test_args"):
      main_test_args = jobs.get("main_test_args")

    tup = (new_ahv, new_aos, old_ahv, old_aos, lcm_url, ahv_to_lcm_blacklist,
           product_meta_url, disable_nos_prod_meta, new_nos_url,
           skip_nos_supported_check, darksite_bundle_url, new_ahv_list,
           new_nos_releases, vlan, nos_rim_urls, nos_rim_url, binary_location,
           host_driver_url, main_test_args)
    return tup

  def testset_payload_generation(self, testset_id, new_ahv=None, #pylint: disable=too-many-locals,too-many-branches,too-many-statements
                                 new_aos=None, old_aos=None, old_ahv=None,
                                 lcm_url=None, ahv_to_lcm_blacklist=None,
                                 product_meta_url=None, new_nos_url=None,
                                 disable_nos_prod_meta=None,
                                 skip_nos_supported_check=None,
                                 darksite_bundle_url=None,
                                 new_nos_releases=None, new_ahv_list=None,
                                 nos_rim_urls=None, vlan=None,
                                 nos_rim_url=None, binary_location=None,
                                 host_driver_url=None, test_args=None):
    """
    Method to generate payload for cloning Testset using JITA test set ID.
    Args:
      testset_id(str): JITA test set ID.
      new_ahv(str): Destination Hypervisor version. (Optional)
      lcm_url(str): LCM build URL. (Optional)
      old_ahv(str): Source Hypervisor version. (Optional)
      old_aos(str): Source AOS version. (Optional)
      new_aos(str): Destination AOS version. (Optional)
      ahv_to_lcm_blacklist(bool): AHV to LCM blacklist param. (Optional)
      product_meta_url(str): Product Meta URL. (Optional)
      new_nos_url(str): New NOS URL. (Optional)
      disable_nos_prod_meta(bool): Disable NOS Product Meta. (Optional)
      skip_nos_supported_check(bool): Skip NOS Supported Check. (Optional)
      darksite_bundle_url(str): NGD Darksite Bundle URL. (Optional)
      new_nos_releases(str): Multilevel NOS releases
      new_ahv_list(str): Multilevel AHV releases
      vlan(str): vlan id.
      nos_rim_urls(str): NOS RIM URLs.
      nos_rim_url(str): NOS RIM URL.
      binary_location(str): Binary Location.
      host_driver_url(str): GPU driver for the AHV host.
      test_args(dict): Test Args.

    Returns:
      payload(dict): JITA testset payload.
    """
    payload = (self.jita_client.get_testset_info(testset_id=testset_id))
    tests = []
    for i in metadata.TEST_SET_CLONE_KEYS_TO_DELETE:
      if payload.get(i) is not None:
        del payload[i]
    payload["name"] = str(payload["name"]+"_copy_"+(
      datetime.datetime.now().strftime("%d-%m-%Y_%H:%M:%S")))
    if new_ahv is not None:
      old_ahv_versioning = copy.deepcopy(str(new_ahv.split(".")[2])+"."+
                                         str(new_ahv.split(".")[3]))
      new_ahv_versioning = (old_ahv_versioning.split("-")[0].split(".")[0]+"/"+
                            old_ahv_versioning.split("-")[0]+"/"+
                            old_ahv_versioning)

      new_ahv_ver = (old_ahv_versioning if (len(new_ahv.split(".")) == 4 and
                                            len(new_ahv.split(".")[2]) == 8)
                     else new_ahv_versioning)
      if binary_location is not None:
        payload["args_map"]["binary_location"] = binary_location
      else:
        payload["args_map"]["binary_location"] = (
          "http://endor.dyn.nutanix.com/builds/ahv-builds/"+new_ahv_ver
        )
      payload["args_map"]["new_ahv"] = (old_ahv_versioning)
      payload["args_map"]["old_ahv"] = ((str(old_ahv.split(".")[2])+"."+
                                         str(old_ahv.split(".")[3])) if (
                                           len(old_ahv.split(".")) == 4 and
                                           len(old_ahv.split(".")[2]) == 8)
                                        else old_ahv)
      payload["args_map"]["get_dell_ptagent"] = True
      payload["args_map"]["ahv_to_lcm_blacklist"] = True
      payload["args_map"]["jarvis_username"] = self.username
      payload["args_map"]["jarvis_password"] = self.password
      if product_meta_url is not None:
        payload["args_map"]["product_meta_url"] = product_meta_url
      if new_nos_releases is not None:
        payload["args_map"]["new_nos_releases"] = new_nos_releases
      if new_ahv_list is not None:
        payload["args_map"]["new_ahv_list"] = new_ahv_list
      if darksite_bundle_url is not None:
        payload["args_map"]["darksite_bundle_url"] = darksite_bundle_url
      if host_driver_url is not None:
        payload["args_map"]["host_driver_url"] = host_driver_url
      if vlan is not None:
        payload["args_map"]["vlan"] = vlan
      if nos_rim_urls is not None:
        payload["args_map"]["nos_rim_urls"] = nos_rim_urls
      if skip_nos_supported_check is not None:
        payload["args_map"]["skip_nos_supported_check"] = (
          skip_nos_supported_check
        )
      if nos_rim_url is not None:
        payload["args_map"]["nos_rim_url"] = nos_rim_url
      if ahv_to_lcm_blacklist is not None:
        payload["args_map"]["ahv_to_lcm_blacklist"] = ahv_to_lcm_blacklist
      else:
        ahv_json = json.loads(urlopen(metadata.PRODUCT_META_FILE).read()
                              .decode())
        if new_ahv in ahv_json.keys():
          payload["args_map"]["ahv_to_lcm_blacklist"] = False
        else:
          payload["args_map"]["ahv_to_lcm_blacklist"] = True
    if old_aos and new_aos is not None:
      payload["args_map"]["disable_nos_prod_meta"] = True
      if disable_nos_prod_meta is not None:
        payload["args_map"]["disable_nos_prod_meta"] = disable_nos_prod_meta
      if new_nos_url is not None:
        payload["args_map"]["new_nos_url"] = new_nos_url
      payload["args_map"]["old_nos_release"] = ("master" if old_aos == "master"
                                                else metadata.AOS_MAPPING[
                                                  (int(
                                                    old_aos.split(".")[0]
                                                  ))].format(x=old_aos))
      payload["args_map"]["new_nos_release"] = ("master" if new_aos == "master"
                                                else metadata.AOS_MAPPING[
                                                  (int(
                                                    new_aos.split(".")[0]
                                                  ))].format(x=new_aos))

    if lcm_url is not None:
      payload["args_map"]["portal_url"] = lcm_url

    print(test_args)
    if test_args:
      payload["args_map"].update(
        test_args
      )

    tests.extend(payload["tests"])
    payload["tests"] = tests
    # INFO(payload)

    return payload

  def job_payload_builder(self, user_dict, fetched_dict, action, task_id,
                          upgrade_dict, jobs):
    """
    A method which updates the fetched job profile payload as per
    the user input dictionary, which then can be used as payload
    for cloning the job profile.

    Args:
      user_dict(dict): Dictionary containing the user input.
      fetched_dict(dict): Dictionary containing payload fetched from
                         the given job profile.
      action(str): Suite Name.
      task_id(str): Row Task ID.
      upgrade_dict(dict): Upgrade Dictionary.
      jobs(dict): Jobs.

    Returns:
      payload(dict): Dictionary as per the updated values
    """
    update_dict = {}
    start_jp = action
    update_dict["name"] = (start_jp+"_from_v"+upgrade_dict["Source_AHV"]+
                           "_"+upgrade_dict["Source_AOS"]+"_"+str(task_id)+"_"
                           +(datetime.datetime.now().strftime(
                             "%d-%m-%Y_%H:%M:%S"
                           )))
    jp_infra = fetched_dict.get("infra", [])
    if not (len(jp_infra) > 0 and "nested" in jp_infra[0].get("type")):
      update_dict["infra"] = []
      if (jobs.get("enable_direct_pool_execution") or
          (upgrade_dict.get("enable_direct_pool_execution"))):
        updated_list = {
          "kind": "ON_PREM",
          "type": "node_pool",
          "entries": jobs.get("pool_name")
        }
        updated_list["entries"] = jobs.get("pool_name")
        update_dict["infra"].append(updated_list)
      else:
        update_dict["infra"].append(PayloadGenerator.add_infra(
          fetched_dict=fetched_dict,
          cluster_name=upgrade_dict["cluster_name"]
        ))
    # INFO(fetched_dict)
    foundation_url = None
    nos_url = None
    if "Foundation_URL" in upgrade_dict.keys():
      foundation_url = upgrade_dict["Foundation_URL"]
    if "nos_url" in user_dict.keys():
      nos_url = user_dict["nos_url"]
    update_dict["requested_hardware"] = (
      PayloadGenerator.add_hypervisor_version(
        ahv_version=upgrade_dict["Source_AHV"],
        fetched_dict=fetched_dict,
        foundation_build=foundation_url,
        nos_url=nos_url
      )
    )
    update_dict["git"] = PayloadGenerator.add_aos_branch_git(
      aos_version=(upgrade_dict["Source_AOS"] if "Source_AOS" in
                   upgrade_dict.keys() else upgrade_dict["AOS_Version"]),
      fetched_dict=fetched_dict)
    if "system_under_test" in fetched_dict.keys():
      update_dict["system_under_test"] = (
        PayloadGenerator.add_aos_branch_system(
          aos_version=(upgrade_dict["Source_AOS"] if "Source_AOS" in
                       upgrade_dict.keys() else upgrade_dict["AOS_Version"]),
          fetched_dict=fetched_dict
        )
      )
    update_dict["build_selection"] = PayloadGenerator.replace_build_selection(
      fetched_dict=fetched_dict)

    for key in user_dict.keys():
      if key not in metadata.PAYLOAD_KEYS_TO_DELETE:
        update_dict[key] = user_dict[key]
    payload = self.args_manipulator.update(fetched_dict, update_dict)
    return payload

  def workload_job_payload_builder(self, jobs, fetched_dict, **kwargs):#pylint: disable=too-many-statements,too-many-branches,too-many-locals
    """
    A method which updates the fetched job profile payload as per
    the user input dictionary, which then can be used as payload
    for cloning the job profile.

    Args:
      jobs(dict): Dictionary containing the user input.
      fetched_dict(dict): Dictionary containing payload fetched from
                         the given job profile.

    Returns:
      payload(dict): Dictionary as per the updated values
    """
    update_dict = {}
    update_dict["name"] = ("apeiron_workload_"+kwargs.get("row_id", "")+"_"+
                           (datetime.datetime.now().strftime(
                             "%d-%m-%Y_%H:%M:%S"
                           )))
    update_dict["infra"] = []

    if (jobs.get("enable_direct_pool_execution") or
        (kwargs.get("upgrade_dict") and
         kwargs.get("upgrade_dict").get("enable_direct_pool_execution"))):
      updated_list = {
        "kind": "ON_PREM",
        "type": "node_pool",
        "entries": jobs.get("pool_name")
      }
      updated_list["entries"] = jobs.get("pool_name")
      if ("global-pool" in jobs.get("pool_name") and
          jobs.get("global_pool_coupon")):
        updated_list = {
          "kind": "PRIVATE_CLOUD",
          "type": "physical",
          "params": {
            "category": "general",
            "coupon": jobs.get("global_pool_coupon")
          }
        }

      update_dict["infra"].append(updated_list)
    else:
      update_dict["scheduling_options"] = fetched_dict["scheduling_options"]
      update_dict["scheduling_options"].update({
        "skip_resource_spec_match": True,
        "check_image_compatibility": False
      })
      update_dict.update({
        "allow_resource_sharing": False,
        "skip_commit_id_validation": None
      })
      if not kwargs.get("upgrade_dict"):
        cluster_list = [jobs["cluster_ip"]]
        if jobs.get("cluster_details"):
          if jobs["cluster_details"].get("cluster_pc_ip"):
            cluster_list.append(jobs["cluster_details"].get("cluster_pc_ip"))
      else:
        upgrade_dict = kwargs.get("upgrade_dict")
        cluster_list = [upgrade_dict.get("cluster_name")]
        cluster_list.append(
          database.resource_manager[
            upgrade_dict.get("cluster_name")
          ].get("pc_name")
        )

      if (jobs.get("selenium_vm_enabled") or
          upgrade_dict.get("selenium_vm_enabled")):
        cluster_list.append(
          database.resource_manager[
            upgrade_dict.get("cluster_name")
          ].get("selenium_vm_name")
        )

      updated_list = fetched_dict["infra"][0]
      updated_list["type"] = "cluster"
      updated_list["entries"] = cluster_list
      update_dict["infra"].append(updated_list)

    if kwargs.get("upgrade_dict"):
      upgrade_dict = kwargs.get("upgrade_dict")
      update_dict["git"] = PayloadGenerator.add_aos_branch_git(
        aos_version=(upgrade_dict["Source_AOS"] if "Source_AOS" in
                     upgrade_dict.keys() else upgrade_dict["AOS_Version"]),
        fetched_dict=fetched_dict)

      if (fetched_dict.get("resource_manager_json") and
          fetched_dict["resource_manager_json"].get("PRISM_CENTRAL")):
        pc_ver_list = upgrade_dict["Source_PC"].split(".")
        pc_build_url = self.rdm_client.fetch_smoke_passed_pc_build_url(
          pc_version=".".join(pc_ver_list[1:])
        )
        if jobs.get("pc_build_url"):
          pc_build_url = jobs.get("pc_build_url")
        update_dict["resource_manager_json"] = (
          fetched_dict["resource_manager_json"]
        )
        if pc_build_url is not None:
          (update_dict["resource_manager_json"]["PRISM_CENTRAL"]
           ["build"]).update({
             "branch": "master",
             "nos_build_url":pc_build_url
           })

    update_dict["build_selection"] = (
      PayloadGenerator.replace_build_selection(
        fetched_dict=fetched_dict
      )
    )
    if jobs["product"] == "objects":
      if fetched_dict.get("tester_tags"):
        test_tags = ["max_deployments__1", "throttle_tests__1"]
        test_tags.extend(fetched_dict.get("tester_tags"))
        update_dict.update({
          "tester_tags": test_tags
        })
      else:
        test_tags = ["max_deployments__1", "throttle_tests__1"]
        update_dict.update({
          "tester_tags": test_tags
        })
      if fetched_dict.get("plugins"):
        update_dict.update({
          "plugins": fetched_dict["plugins"]
        })
        if fetched_dict["plugins"].get("post_run"):
          update_dict["plugins"].update({
            "post_run": fetched_dict["plugins"]["post_run"]
          })

          plugin_counter = 0
          for i in range(len(update_dict["plugins"]["post_run"])):
            if (update_dict["plugins"]["post_run"][i].get("name") ==#pylint: disable=no-else-break
                "UpdateBranchPlugin"):
              update_dict["plugins"]["post_run"][i].update({
                "args": {
                  "branch": ("buckets-"+str(jobs.get("objects_version")) if
                             jobs.get("objects_version") != "poseidon"
                             else "poseidon")
                }
              })
              break
            else:
              plugin_counter += 1

          if plugin_counter == len(update_dict["plugins"]["post_run"]):
            update_dict["plugins"]["post_run"].append(
              {
                "metadata": {
                  "kind":"test"
                },
                "args": {
                  "branch": ("buckets-"+str(jobs.get("objects_version")) if
                             jobs.get("objects_version") != "poseidon"
                             else "poseidon")
                },
                "name":"UpdateBranchPlugin",
                "stage":"post_run",
                "description":("Updates the branch info of the test result"
                               "document with the info provided in args")
              }
            )

    if jobs.get("nos_url"):
      update_dict["requested_hardware"] = (
        PayloadGenerator.add_hypervisor_version(
          fetched_dict=fetched_dict,
          nos_url=jobs.get("nos_url")
        )
      )

    if jobs.get("product") in ["objects"]:
      if fetched_dict.get("plugins"):
        update_dict.update({
          "plugins": fetched_dict["plugins"]
        })
        if fetched_dict["plugins"].get("post_run"):
          update_dict["plugins"].update({
            "post_run": fetched_dict["plugins"]["post_run"]
          })
          post_plugin = copy.deepcopy(metadata.POST_RUN_PLUGIN)
          objects_version = jobs.get("objects_version")
          image_tag_oss_version = ("buckets-"+str(objects_version) if
                                   objects_version != "poseidon" else
                                   "poseidon")
          post_plugin["args"]["branch"] = image_tag_oss_version
          update_dict["plugins"]["post_run"].append(post_plugin)

    INFO(json.dumps(fetched_dict))

    for key in jobs.keys():
      if key not in metadata.PAYLOAD_KEYS_TO_DELETE:
        update_dict[key] = jobs[key]
    INFO(json.dumps(update_dict))
    payload = self.args_manipulator.update(fetched_dict, update_dict)
    INFO(json.dumps(payload))
    return payload

  def gos_testset_payload_generation(self, testset_id, test_args):
    """
    Generate GOS testset payload
    Args:
      testset_id(str):
      test_args(dict): gos details to be qualified
    Returns:
      payload(dict):
    """
    payload = (self.jita_client.get_testset_info(testset_id=testset_id))
    tests = []
    for i in metadata.TEST_SET_CLONE_KEYS_TO_DELETE:
      if payload.get(i) is not None:
        del payload[i]
    payload["name"] = str(payload["name"] + "_copy_" + (
      datetime.datetime.now().strftime("%d-%m-%Y_%H:%M:%S")))
    actual_args = copy.deepcopy(test_args)
    INFO(str(actual_args))

    for i in metadata.GOS_TESTARGS_TO_DELETE:
      for j in range(len(actual_args)):#pylint: disable=consider-using-enumerate
        if i in actual_args[j]:
          del actual_args[j][i]
    # Note: converting the test_args into dict format to bypass JITA issue
    #       PROHELP-15039
    payload["args_map"] = {
      "execution_plan": convert_list_to_pos_dict(actual_args)
    }
    tests.extend(payload["tests"])
    payload["tests"] = tests
    return payload

  def gos_job_payload_builder(self, user_dict, fetched_dict,
                              gos_dict):
    """
    A method which updates the fetched job profile payload as per
    the user input dictionary, which then can be used as payload
    for cloning the job profile.

    Args:
      user_dict(dict): Dictionary containing the user input.
      fetched_dict(dict): Dictionary containing payload fetched from
                         the given job profile.
      gos_dict(dict): Gos dict.

    Returns:
      payload(dict): Dictionary as per the updated values
    """
    update_dict = {}
    start_jp = "guest_os_qual"
    update_dict["name"] = (start_jp +
                           (datetime.datetime.now().strftime(
                             "%d-%m-%Y_%H:%M:%S"
                           )))
    update_dict["infra"] = []
    update_dict["infra"].append(PayloadGenerator.add_infra(
      fetched_dict=fetched_dict,
      cluster_name=gos_dict[0]["cluster_name"]
    ))
    # INFO(fetched_dict)
    foundation_url = None
    nos_url = None
    if "Foundation_URL" in gos_dict[0].keys():
      foundation_url = gos_dict[0]["Foundation_URL"]
    if "nos_url" in user_dict.keys():
      nos_url = user_dict["nos_url"]
    update_dict["requested_hardware"] = PayloadGenerator.add_hypervisor_version(
      ahv_version=gos_dict[0]["ahv"],
      fetched_dict=fetched_dict,
      foundation_build=foundation_url,
      nos_url=nos_url
    )
    update_dict["git"] = PayloadGenerator.add_aos_branch_git(
      aos_version=(gos_dict[0]["aos"] if "aos" in gos_dict[0].keys() else
                   gos_dict[0]["aos"]),
      fetched_dict=fetched_dict)
    if "system_under_test" in fetched_dict.keys():
      update_dict["system_under_test"] = PayloadGenerator.add_aos_branch_system(
        aos_version=(gos_dict[0]["aos"] if "aos" in gos_dict[0].keys() else
                     gos_dict[0]["aos"]),
        fetched_dict=fetched_dict)
    update_dict["build_selection"] = PayloadGenerator.replace_build_selection(
      fetched_dict=fetched_dict)

    for key in user_dict.keys():
      if key not in metadata.PAYLOAD_KEYS_TO_DELETE:
        update_dict[key] = user_dict[key]
    payload = self.args_manipulator.update(fetched_dict, update_dict)
    return payload
