"""Copyright (c) 2021 Nutanix Inc. All rights reserved.

Author: vedant.dalal@nutanix.com
"""

# pylint: disable=invalid-name, no-self-use, too-many-lines, broad-except
from urllib.request import urlopen
import json
import uuid
import copy
import re
import ast

from framework.lib.nulog import INFO, ERROR
from libs.ahv.workflows.gos_qual.\
  generic_guest_qualifier_v2 import GenericGuestQualifierv2
from libs.ahv.workflows.one_click.args_manipulator \
  import ArgsManipulator
from libs.ahv.workflows.one_click.feat_manager \
  import FeatManager
from libs.ahv.workflows.one_click.\
  gpu_host_driver_helper import GPUHostDriverUtil
from libs.ahv.workflows.one_click import metadata
from libs.ahv.workflows.one_click import database
from libs.ahv.workflows.one_click.deployment_manager \
  import DeploymentManager

class MatrixGenerator():
  """
  A class containing the Modules to generate Matrix
  """
  def __init__(self):
    """
    Constructor Method.
    """
    self.dep_manager = DeploymentManager()
    self.feat_manager = FeatManager()
    self.args_manipulator = ArgsManipulator()
    self.gpu_host_driver_helper = GPUHostDriverUtil()

  def ahv_upgrade(self, ahv_product_meta, jobs, suite): #pylint: disable=too-many-branches,no-self-use,too-many-locals,too-many-statements
    """
    Method to create the AHV Upgrade Matrix

    Args:
      ahv_product_meta(json): A JSON object containing the Product Meta.
      jobs(json): A JSON object containing the Job details.
      suite(str): Suite Name.

    Returns:
      ahv_upgrade_list(list): List containing list of possible
                              combinations
    """
    # INFO("AHV Prod Meta: "+json.dumps(ahv_product_meta))
    ahv_upgrade_dict = {}
    out_counter = 0
    in_counter = 0
    dst_ahv = jobs["ahv_version"]
    aos_version = jobs["aos_version"]
    el_version = self.args_manipulator.get_el_version(dst_ahv)
    ahv_str = str(el_version+".nutanix."+dst_ahv)
    upgrade_paths = ahv_product_meta[ahv_str]["upgrade_from"]
    upgrade_paths.reverse()

    # upgrade_path_len = len(upgrade_paths)
    lcm_len = 1
    found_len = 1
    platform_len = 1

    if "lcm_url" in jobs.keys():
      lcm_len = len(jobs["lcm_url"])
      metadata.AHV_UPGRADE_HEADERS.insert(
        len(metadata.AHV_UPGRADE_HEADERS)-8,
        "LCM Version"
      )

    if "platforms" in jobs.keys():
      platform_len = len(jobs["platforms"])

    if "foundation_builds" in jobs.keys():
      found_len = len(jobs["foundation_builds"])
      metadata.AHV_UPGRADE_HEADERS.insert(
        len(metadata.AHV_UPGRADE_HEADERS)-8,
        "Foundation Build"
      )
    prioritized_list = []

    # Add the additional src ahv versions on same AOS
    src_ahv_list = []
    if jobs.get("add_src_ahv"):
      for src_ahv_input in jobs.get("add_src_ahv"):
        src_ahv_list.append(
          (self.args_manipulator.get_el_version(src_ahv_input)+
           ".nutanix."+src_ahv_input,)
        )
      prioritized_list.extend(src_ahv_list)

    dest_ahv_list = []
    # Add the additional dest ahv versions on same AOS
    if jobs.get("add_dest_ahv"):
      for dest_ahv in jobs.get("add_dest_ahv"):
        dest_ahv_list.append((
          self.args_manipulator.get_el_version(dest_ahv)+
          ".nutanix."+dest_ahv, "dest_ahv"))

    prioritized_list.extend(dest_ahv_list)

    prioritized_list.extend(self._prioritize_based_on_lts_sts(
      upgrade_paths=upgrade_paths,
      ahv_product_meta=ahv_product_meta,
      dst_aos=aos_version,
      jobs=jobs
    ))

    # Handle duplicates
    prioritized_list = list(set(prioritized_list))
    ahv_upgrade_set = set()
    for tup in prioritized_list:
      if len(tup) > 1 and tup[1] == "dest_ahv":
        ahv_upgrade_set.add((tup[0], tup[1]))
      else:
        ahv_upgrade_set.add((tup[0], "source_ahv"))

    for j in range(lcm_len): #pylint: disable=too-many-nested-blocks
      for k in range(found_len):
        for l in range(platform_len): #pylint: disable=invalid-name
          ahv_upgrade_dict.update({str(out_counter): {}})
          in_counter = 0
          for each_tup in ahv_upgrade_set:
            ahv_upgrade_dict[str(out_counter)].update({str(in_counter): {}})

            ahv_upgrade_dict[str(out_counter)][str(in_counter)].update(
              {
                "row_id": str(uuid.uuid1()),
                "Source_AHV": each_tup[0],
                "Source_AOS": aos_version,
                "Destination_AHV": ahv_str,
                "Platform": "",
                "out_key": str(out_counter),
                "in_key": str(in_counter),
                "matrix_type": str(suite),
                "uuid": str(database.matrices["uuid"]),
                "matrix_start_time": database.matrices["matrix_start_time"]
              }
            )
            if len(each_tup) > 1:
              if each_tup[1] == "dest_ahv":
                ahv_upgrade_dict[str(out_counter)][str(in_counter)].update(
                  {
                    "Source_AHV": ahv_str,
                    "Destination_AHV": each_tup[0]
                  }
                )

            if "lcm_url" in jobs.keys():
              lcm_url = jobs["lcm_url"][j]
              lcm_version = None
              lcm_list = lcm_url.split("/")
              lcm_list_len = len(lcm_list)
              if lcm_list_len >= 7:
                lcm_version = str(lcm_list[5]+"_"+lcm_list[6])
              else:
                lcm_version = str(lcm_list[lcm_list_len-2]+"_"+
                                  lcm_list[lcm_list_len-1])
              ahv_upgrade_dict[str(out_counter)][str(in_counter)].update(
                {
                  "LCM_Version": lcm_version,
                  "LCM_URL": lcm_url
                }
              )

            if "platforms" in jobs.keys():
              ahv_upgrade_dict[str(out_counter)][str(in_counter)].update(
                {
                  "Platform": jobs["platforms"][l]
                }
              )

            if "foundation_builds" in jobs.keys():
              found_url = jobs["foundation_builds"][k]
              found_build = self._get_foundation_build_version(found_url)
              ahv_upgrade_dict[str(out_counter)][str(in_counter)].update(
                {
                  "Foundation_Build": found_build,
                  "Foundation_URL": found_url
                }
              )
            in_counter += 1

          out_counter += 1
    # INFO("Out Counter: "+str(out_counter))
    # INFO("IN Counter: "+str(in_counter))
    return ahv_upgrade_dict

  def ahv_aos_upgrade(self, ahv_product_meta, jobs, suite): #pylint: disable=too-many-branches,no-self-use,too-many-statements,too-many-locals
    """
    Method to create the AHV-AOS Upgrade Matrix

    Args:
      ahv_product_meta(json): A JSON object containing the Product Meta
      jobs(json): A JSON object containing the Job details
      suite(str): Suite Name.

    Returns:
      ahv_aos_upgrade_list(list): List containing list of possible
                              combinations
    """
    ahv_aos_upgrade_dict = {}
    out_counter = 0
    in_counter = 0
    dst_ahv = jobs["ahv_version"]
    dst_aos = jobs["aos_version"]
    el_version = self.args_manipulator.get_el_version(dst_ahv)
    ahv_str = str(el_version+".nutanix."+dst_ahv)
    upgrade_paths = ahv_product_meta[ahv_str]["upgrade_from"]
    upgrade_paths.reverse()

    lcm_len = 1
    found_len = 1
    platform_len = 1

    if "lcm_url" in jobs.keys():
      lcm_len = len(jobs["lcm_url"])
      metadata.AHV_AOS_UPGRADE_HEADERS.insert(
        len(metadata.AHV_AOS_UPGRADE_HEADERS)-8,
        "LCM Version"
      )

    if "platforms" in jobs.keys():
      platform_len = len(jobs["platforms"])

    if "foundation_builds" in jobs.keys():
      found_len = len(jobs["foundation_builds"])
      metadata.AHV_AOS_UPGRADE_HEADERS.insert(
        len(metadata.AHV_AOS_UPGRADE_HEADERS)-8,
        "Foundation Build"
      )

    prioritized_list = self._prioritize_based_on_lts_sts(
      upgrade_paths=upgrade_paths,
      ahv_product_meta=ahv_product_meta,
      dst_aos=dst_aos,
      jobs=jobs
    )

    # Handle duplicates
    prioritized_list = list(set(prioritized_list))

    for j in range(lcm_len): #pylint: disable=too-many-nested-blocks
      for k in range(found_len):
        for l in range(platform_len): #pylint: disable=invalid-name
          ahv_aos_upgrade_dict.update({str(out_counter): {}})
          in_counter = 0

          for each_tup in prioritized_list:
            # INFO("LCM Len: "+str(lcm_len))
            # INFO("Found Len: "+str(found_len))
            # INFO("Platform Len: "+str(platform_len))

            ahv_aos_upgrade_dict[str(out_counter)].update({str(in_counter): {}})

            ahv_aos_upgrade_dict[str(out_counter)][str(in_counter)].update({
              "row_id": str(uuid.uuid1()),
              "Source_AHV": each_tup[0],
              "Source_AOS": each_tup[1],
              "Destination_AOS": dst_aos,
              "Destination_AHV": ahv_str,
              "Platform": "",
              "out_key": str(out_counter),
              "in_key": str(in_counter),
              "matrix_type": str(suite),
              "uuid": str(database.matrices["uuid"]),
              "matrix_start_time": database.matrices["matrix_start_time"]
            })

            if "lcm_url" in jobs.keys():
              lcm_url = jobs["lcm_url"][j]
              lcm_version = None
              lcm_list = lcm_url.split("/")
              lcm_list_len = len(lcm_list)
              if lcm_list_len >= 7:
                lcm_version = str(lcm_list[5]+"_"+lcm_list[6])
              else:
                lcm_version = str(lcm_list[lcm_list_len-2]+"_"+
                                  lcm_list[lcm_list_len-1])
              ahv_aos_upgrade_dict[str(out_counter)][str(in_counter)].update(
                {
                  "LCM_Version": lcm_version,
                  "LCM_URL": lcm_url
                }
              )

            if "platforms" in jobs.keys():
              ahv_aos_upgrade_dict[str(out_counter)][str(in_counter)].update(
                {
                  "Platform": jobs["platforms"][l]
                }
              )

            if "foundation_builds" in jobs.keys():
              found_url = jobs["foundation_builds"][k]
              found_build = self._get_foundation_build_version(found_url)
              ahv_aos_upgrade_dict[str(out_counter)][str(in_counter)].update(
                {
                  "Foundation_Build": found_build,
                  "Foundation_URL": found_url
                }
              )
            in_counter += 1

          out_counter += 1
    # INFO("Out Counter: "+str(out_counter))
    # INFO("IN Counter: "+str(in_counter))
    return ahv_aos_upgrade_dict

  def deployment_path(self, jobs, suite): #pylint: disable=no-self-use,too-many-locals
    """
    Method to create the Deployment Path Matrix

    Args:
      jobs(dict): Jobs
      suite(str): Suite Name.

    Returns:
      dep_path_list(list): List containing list of possible
                              combinations
    """
    platform_len = 1
    out_counter = 0
    in_counter = 0
    dep_path_dict = {}
    ahv_version = jobs["ahv_version"]
    aos_version = jobs["aos_version"]
    el_version = self.args_manipulator.get_el_version(
      ahv_version=ahv_version
    )
    ahv_str = str(el_version+".nutanix."+ahv_version)

    foundation_list = jobs["foundation_builds"]

    if "platforms" in jobs.keys():
      platform_len = len(jobs["platforms"])

    for l in range(platform_len): #pylint: disable=invalid-name
      dep_path_dict.update({str(out_counter): {}})
      in_counter = 0
      for foundation_build in foundation_list:
        if len(foundation_build.split("/")) > 5:
          if len(foundation_build.split("/")[4].split("-")) > 2:
            found_build = foundation_build.split("/")[4].split("-")[1]
          else:
            regex_list = re.findall("[0-9][.][0-9]", foundation_build)
            found_list = list(set(regex_list))
            if len(found_list) > 0:
              found_build = found_list[0]
            else:
              found_build = str(foundation_build.split("/")[4])
        else:
          regex_list = re.findall("[0-9][.][0-9]", foundation_build)
          found_list = list(set(regex_list))
          if len(found_list) > 0:
            found_build = found_list[0]
          else:
            found_build = str(foundation_build.split("/")[4])
        dep_path_dict[str(out_counter)].update({str(in_counter): {}})

        dep_path_dict[str(out_counter)][str(in_counter)].update({
          "row_id": str(uuid.uuid1()),
          "Source_AHV": ahv_str,
          "Source_AOS": aos_version,
          "Platform": "",
          "Foundation_Build": found_build,
          "Foundation_URL": foundation_build,
          "jobs": jobs,
          "out_key": str(out_counter),
          "in_key": str(in_counter),
          "matrix_type": str(suite),
          "uuid": str(database.matrices["uuid"]),
          "matrix_start_time": database.matrices["matrix_start_time"]
        })

        if "platforms" in jobs.keys():
          dep_path_dict[str(out_counter)][str(in_counter)].update(
            {
              "Platform": jobs["platforms"][l]
            }
          )

        in_counter += 1
      out_counter += 1

    return dep_path_dict

  def ngd_deployment(self, jobs, suite, **kwargs): #pylint: disable=no-self-use,too-many-locals,unused-argument
    """
    Method to create the Deployment Path Matrix

    Args:
      jobs(dict): Jobs
      suite(str): Suite Name.

    Returns:
      dep_path_list(list): List containing list of possible
                              combinations
    """
    platform_len = 1
    out_counter = 0
    in_counter = 0
    dep_path_dict = {}
    ahv_version = jobs["ahv_version"]
    aos_version = jobs["aos_version"]
    el_version = self.args_manipulator.get_el_version(
      ahv_version=ahv_version
    )
    ahv_str = str(el_version+".nutanix."+ahv_version)

    if "platforms" in jobs.keys():
      platform_len = len(jobs["platforms"])

    host_driver_map_list = self.gpu_host_driver_helper.fetch_host_driver_url(
      ahv_version=ahv_version,
      jobs=jobs
    )

    for l in range(platform_len): #pylint: disable=invalid-name
      dep_path_dict.update({str(out_counter): {}})
      in_counter = 0
      for driver_url_map in host_driver_map_list:
        host_driver = list(driver_url_map.keys())[0]
        host_driver_url = driver_url_map[host_driver]
        dep_path_dict[str(out_counter)].update({str(in_counter): {}})
        dep_path_dict[str(out_counter)][str(in_counter)].update({
          "row_id": str(uuid.uuid1()),
          "Source_AHV": ahv_str,
          "Source_AOS": aos_version,
          "Platform": "",
          "Driver": host_driver,
          "host_driver_url": host_driver_url,
          "jobs": jobs,
          "out_key": str(out_counter),
          "in_key": str(in_counter),
          "matrix_type": str(suite),
          "uuid": str(database.matrices["uuid"]),
          "matrix_start_time": database.matrices["matrix_start_time"]
        })

        if "platforms" in jobs.keys():
          dep_path_dict[str(out_counter)][str(in_counter)].update(
            {
              "Platform": jobs["platforms"][l]
            }
          )

        in_counter += 1
      out_counter += 1

    return dep_path_dict

  def ndk_deployment(self, jobs, prod_meta, suite_dict,#pylint: disable=no-self-use,too-many-locals
                     suite="csi_deployment"):
    """
    Method to create the Deployment Path Matrix

    Args:
      jobs(dict): Jobs.
      prod_meta(dict): Product Meta.
      suite_dict(dict): Suite Dictionary.
      suite(str): Suite Name.

    Returns:
      dep_path_list(list): List containing list of possible
                              combinations
    """
    platform_len = 1
    out_counter = 0
    in_counter = 0
    dep_path_dict = {}
    ndk_version = jobs["ndk_version"]
    full_ndk_version = "ndk."+str(ndk_version)
    aos_version = (prod_meta[full_ndk_version]["compatibilities"]
                   ["recommendations"]["AOS"][0])
    pc_version = prod_meta[full_ndk_version]["pc_version"][0]
    csi_version = prod_meta[full_ndk_version]["csi_version"][0]
    suite_name_full_list = suite.split("_")
    suite_name = "_".join(suite_name_full_list[1:])
    feat_dict = suite_dict[suite_name]
    found_len = 1
    platform_len = 1
    k8s_platform = ["capex"]

    if jobs.get("k8s_platform"):
      k8s_platform = jobs.get("k8s_platform")

    if jobs.get("aos_version"):
      aos_version = jobs.get("aos_version")
    if jobs.get("csi_version"):
      csi_version = jobs.get("csi_version")
    if jobs.get("pc_version"):
      pc_version = jobs.get("pc_version")

    if "foundation_builds" in jobs.keys():
      found_len = len(jobs["foundation_builds"])
      metadata.CSI_DEPLOYMENT_HEADERS.insert(
        len(metadata.CSI_DEPLOYMENT_HEADERS)-8,
        "Foundation Build"
      )
    if "platforms" in jobs.keys():
      platform_len = len(jobs["platforms"])

    for k in range(found_len): #pylint: disable=too-many-nested-blocks
      for l in range(platform_len): #pylint: disable=invalid-name
        dep_path_dict.update({str(out_counter): {}})
        in_counter = 0
        for each_k8s in k8s_platform:
          for feat in feat_dict.keys():
            INFO(str(feat_dict[feat]))
            for ind in range(len(feat_dict[feat]["job_profile"])):
              dep_path_dict[str(out_counter)].update({str(in_counter): {}})
              dep_path_dict[str(out_counter)][str(in_counter)].update({
                "row_id": str(uuid.uuid1()),
                "Source_NDK": ndk_version,
                "Source_CSI": csi_version,
                "Source_AOS": aos_version,
                "Source_PC": pc_version,
                "Feat": feat,
                "Feat_Index": str(ind+1),
                "Platform": "",
                "Kubernetes_Platform": each_k8s,
                "jobs": jobs,
                "job_profile": feat_dict[feat]["job_profile"][ind],
                "out_key": str(out_counter),
                "in_key": str(in_counter),
                "matrix_type": str(suite),
                "uuid": str(database.matrices["uuid"]),
                "matrix_start_time": database.matrices["matrix_start_time"]
              })

              if feat_dict[feat].get("failure_reason"):
                dep_path_dict[str(out_counter)][str(in_counter)].update({
                  "Result": "Failed",
                  "Status": "completed",
                  "Reason": feat_dict[feat]["failure_reason"]
                })

              if "platforms" in jobs.keys():
                dep_path_dict[str(out_counter)][str(in_counter)].update(
                  {
                    "Platform": jobs["platforms"][l]
                  }
                )

              if "foundation_builds" in jobs.keys():
                found_url = jobs["foundation_builds"][k]
                found_build = self._get_foundation_build_version(found_url)
                dep_path_dict[str(out_counter)][str(in_counter)].update(
                  {
                    "Foundation_Build": found_build,
                    "Foundation_URL": found_url
                  }
                )

              in_counter += 1
        out_counter += 1

    return dep_path_dict

  def ndk_upgrade(self, jobs, prod_meta, suite="csi_deployment", **kwargs):#pylint: disable=no-self-use,too-many-locals
    """
    Method to create the Deployment Path Matrix

    Args:
      jobs(dict): Jobs.
      prod_meta(dict): Product Meta.
      suite(str): Suite Name.

    Returns:
      dep_path_list(list): List containing list of possible
                              combinations
    """
    INFO(json.dumps(kwargs))
    platform_len = 1
    out_counter = 0
    in_counter = 0
    dep_path_dict = {}
    ndk_version = jobs["ndk_version"]
    full_ndk_version = "ndk."+str(ndk_version)
    aos_version = (prod_meta[full_ndk_version]["compatibilities"]
                   ["recommendations"]["AOS"][0])
    pc_version = prod_meta[full_ndk_version]["pc_version"][0]
    csi_version = prod_meta[full_ndk_version]["csi_version"][0]
    upgrade_paths = prod_meta[full_ndk_version]["upgrade_from"]
    found_len = 1
    platform_len = 1
    k8s_platform = ["capex"]

    if jobs.get("k8s_platform"):
      k8s_platform = jobs.get("k8s_platform")

    if jobs.get("aos_version"):
      aos_version = jobs.get("aos_version")
    if jobs.get("csi_version"):
      csi_version = jobs.get("csi_version")
    if jobs.get("pc_version"):
      pc_version = jobs.get("pc_version")

    if "foundation_builds" in jobs.keys():
      found_len = len(jobs["foundation_builds"])
      metadata.CSI_DEPLOYMENT_HEADERS.insert(
        len(metadata.CSI_DEPLOYMENT_HEADERS)-8,
        "Foundation Build"
      )
    if "platforms" in jobs.keys():
      platform_len = len(jobs["platforms"])

    upgrade_list = []
    for path in upgrade_paths:
      res_tup = (path)
      upgrade_list.append(res_tup)

    for k in range(found_len): #pylint: disable=too-many-nested-blocks
      for l in range(platform_len): #pylint: disable=invalid-name
        dep_path_dict.update({str(out_counter): {}})
        in_counter = 0
        for each_k8s in k8s_platform:
          for each_tup in upgrade_list:
            dep_path_dict[str(out_counter)].update({str(in_counter): {}})
            dep_path_dict[str(out_counter)][str(in_counter)].update({
              "row_id": str(uuid.uuid1()),
              "Source_NDK": each_tup,
              "Source_CSI": csi_version,
              "Source_AOS": aos_version,
              "Source_PC": pc_version,
              "Destination_NDK": full_ndk_version,
              "Platform": "",
              "Kubernetes_Platform": each_k8s,
              "jobs": jobs,
              "out_key": str(out_counter),
              "in_key": str(in_counter),
              "matrix_type": str(suite),
              "uuid": str(database.matrices["uuid"]),
              "matrix_start_time": database.matrices["matrix_start_time"],
              "test_args": {
                "main": {
                  "download_url": prod_meta[each_tup]["build_url"],
                  "upgrade_url": prod_meta[full_ndk_version]["build_url"],
                  "k8s_type": each_k8s
                }
              }
            })

            if "platforms" in jobs.keys():
              dep_path_dict[str(out_counter)][str(in_counter)].update(
                {
                  "Platform": jobs["platforms"][l]
                }
              )

            if "foundation_builds" in jobs.keys():
              found_url = jobs["foundation_builds"][k]
              found_build = self._get_foundation_build_version(found_url)
              dep_path_dict[str(out_counter)][str(in_counter)].update(
                {
                  "Foundation_Build": found_build,
                  "Foundation_URL": found_url
                }
              )

            in_counter += 1
        out_counter += 1

    return dep_path_dict

  def ndk_pc_upgrade(self, jobs, prod_meta, suite="ndk_pc_upgrade", **kwargs):#pylint: disable=no-self-use,too-many-locals
    """
    Method to create the Deployment Path Matrix

    Args:
      jobs(dict): Jobs.
      prod_meta(dict): Product Meta.
      suite(str): Suite Name.

    Returns:
      dep_path_list(list): List containing list of possible
                              combinations
    """
    INFO(json.dumps(kwargs))
    platform_len = 1
    out_counter = 0
    in_counter = 0
    dep_path_dict = {}
    ndk_version = jobs["ndk_version"]
    full_ndk_version = "ndk."+str(ndk_version)
    aos_version = (prod_meta[full_ndk_version]["compatibilities"]
                   ["recommendations"]["AOS"][0])
    pc_version = prod_meta[full_ndk_version]["pc_version"][0]
    csi_version = prod_meta[full_ndk_version]["csi_version"][0]
    upgrade_paths = prod_meta[full_ndk_version]["upgrade_from"]
    found_len = 1
    platform_len = 1
    k8s_platform = ["capex"]

    if jobs.get("k8s_platform"):
      k8s_platform = jobs.get("k8s_platform")

    if jobs.get("aos_version"):
      aos_version = jobs.get("aos_version")
    if jobs.get("csi_version"):
      csi_version = jobs.get("csi_version")
    if jobs.get("pc_version"):
      pc_version = jobs.get("pc_version")

    if "foundation_builds" in jobs.keys():
      found_len = len(jobs["foundation_builds"])
      metadata.CSI_DEPLOYMENT_HEADERS.insert(
        len(metadata.CSI_DEPLOYMENT_HEADERS)-8,
        "Foundation Build"
      )
    if "platforms" in jobs.keys():
      platform_len = len(jobs["platforms"])

    upgrade_list = []
    for path in upgrade_paths:
      src_pc_list = prod_meta[path]["pc_version"]
      for src_pc in src_pc_list:
        res_tup = (path, src_pc)
        upgrade_list.append(res_tup)

    for k in range(found_len): #pylint: disable=too-many-nested-blocks
      for l in range(platform_len): #pylint: disable=invalid-name
        dep_path_dict.update({str(out_counter): {}})
        in_counter = 0
        for each_k8s in k8s_platform:
          for each_tup in upgrade_list:
            dep_path_dict[str(out_counter)].update({str(in_counter): {}})
            dep_path_dict[str(out_counter)][str(in_counter)].update({
              "row_id": str(uuid.uuid1()),
              "Source_NDK": each_tup[0],
              "Source_CSI": csi_version,
              "Source_AOS": aos_version,
              "Source_PC": each_tup[1],
              "Destination_PC": pc_version,
              "Destination_NDK": full_ndk_version,
              "Platform": "",
              "Kubernetes_Platform": each_k8s,
              "jobs": jobs,
              "out_key": str(out_counter),
              "in_key": str(in_counter),
              "matrix_type": str(suite),
              "uuid": str(database.matrices["uuid"]),
              "matrix_start_time": database.matrices["matrix_start_time"]
            })

            if "platforms" in jobs.keys():
              dep_path_dict[str(out_counter)][str(in_counter)].update(
                {
                  "Platform": jobs["platforms"][l]
                }
              )

            if "foundation_builds" in jobs.keys():
              found_url = jobs["foundation_builds"][k]
              found_build = self._get_foundation_build_version(found_url)
              dep_path_dict[str(out_counter)][str(in_counter)].update(
                {
                  "Foundation_Build": found_build,
                  "Foundation_URL": found_url
                }
              )

            in_counter += 1
        out_counter += 1

    return dep_path_dict

  def ndk_csi_upgrade(self, jobs, prod_meta, suite="ndk_csi_upgrade", **kwargs):#pylint: disable=no-self-use,too-many-locals
    """
    Method to create the Deployment Path Matrix

    Args:
      jobs(dict): Jobs.
      prod_meta(dict): Product Meta.
      suite(str): Suite Name.

    Returns:
      dep_path_list(list): List containing list of possible
                              combinations
    """
    INFO(json.dumps(kwargs))
    platform_len = 1
    out_counter = 0
    in_counter = 0
    dep_path_dict = {}
    ndk_version = jobs["ndk_version"]
    full_ndk_version = "ndk."+str(ndk_version)
    aos_version = (prod_meta[full_ndk_version]["compatibilities"]
                   ["recommendations"]["AOS"][0])
    pc_version = prod_meta[full_ndk_version]["pc_version"][0]
    csi_version = prod_meta[full_ndk_version]["csi_version"][0]
    upgrade_paths = prod_meta[full_ndk_version]["upgrade_from"]
    found_len = 1
    platform_len = 1
    k8s_platform = ["capex"]

    if jobs.get("k8s_platform"):
      k8s_platform = jobs.get("k8s_platform")

    if jobs.get("aos_version"):
      aos_version = jobs.get("aos_version")
    if jobs.get("csi_version"):
      csi_version = jobs.get("csi_version")
    if jobs.get("pc_version"):
      pc_version = jobs.get("pc_version")

    if "foundation_builds" in jobs.keys():
      found_len = len(jobs["foundation_builds"])
      metadata.CSI_DEPLOYMENT_HEADERS.insert(
        len(metadata.CSI_DEPLOYMENT_HEADERS)-8,
        "Foundation Build"
      )
    if "platforms" in jobs.keys():
      platform_len = len(jobs["platforms"])

    upgrade_list = []
    for path in upgrade_paths:
      src_csi_list = prod_meta[path]["csi_version"]
      for src_csi in src_csi_list:
        res_tup = (path, src_csi)
        upgrade_list.append(res_tup)

    for k in range(found_len): #pylint: disable=too-many-nested-blocks
      for l in range(platform_len): #pylint: disable=invalid-name
        dep_path_dict.update({str(out_counter): {}})
        in_counter = 0
        for each_k8s in k8s_platform:
          for each_tup in upgrade_list:
            dep_path_dict[str(out_counter)].update({str(in_counter): {}})
            dep_path_dict[str(out_counter)][str(in_counter)].update({
              "row_id": str(uuid.uuid1()),
              "Source_NDK": each_tup[0],
              "Source_CSI": each_tup[1],
              "Source_AOS": aos_version,
              "Source_PC": pc_version,
              "Destination_CSI": csi_version,
              "Destination_NDK": full_ndk_version,
              "Platform": "",
              "Kubernetes_Platform": each_k8s,
              "jobs": jobs,
              "out_key": str(out_counter),
              "in_key": str(in_counter),
              "matrix_type": str(suite),
              "uuid": str(database.matrices["uuid"]),
              "matrix_start_time": database.matrices["matrix_start_time"]
            })

            if "platforms" in jobs.keys():
              dep_path_dict[str(out_counter)][str(in_counter)].update(
                {
                  "Platform": jobs["platforms"][l]
                }
              )

            if "foundation_builds" in jobs.keys():
              found_url = jobs["foundation_builds"][k]
              found_build = self._get_foundation_build_version(found_url)
              dep_path_dict[str(out_counter)][str(in_counter)].update(
                {
                  "Foundation_Build": found_build,
                  "Foundation_URL": found_url
                }
              )

            in_counter += 1
        out_counter += 1

    return dep_path_dict

  def ndk_aos_upgrade(self, jobs, prod_meta, suite="ndk_csi_upgrade", **kwargs):#pylint: disable=no-self-use,too-many-locals
    """
    Method to create the Deployment Path Matrix

    Args:
      jobs(dict): Jobs.
      prod_meta(dict): Product Meta.
      suite(str): Suite Name.

    Returns:
      dep_path_list(list): List containing list of possible
                              combinations
    """
    INFO(json.dumps(kwargs))
    platform_len = 1
    out_counter = 0
    in_counter = 0
    dep_path_dict = {}
    ndk_version = jobs["ndk_version"]
    full_ndk_version = "ndk."+str(ndk_version)
    aos_version = (prod_meta[full_ndk_version]["compatibilities"]
                   ["recommendations"]["AOS"][0])
    pc_version = prod_meta[full_ndk_version]["pc_version"][0]
    csi_version = prod_meta[full_ndk_version]["csi_version"][0]
    upgrade_paths = prod_meta[full_ndk_version]["upgrade_from"]
    found_len = 1
    platform_len = 1
    k8s_platform = ["capex"]

    if jobs.get("k8s_platform"):
      k8s_platform = jobs.get("k8s_platform")

    if jobs.get("aos_version"):
      aos_version = jobs.get("aos_version")
    if jobs.get("csi_version"):
      csi_version = jobs.get("csi_version")
    if jobs.get("pc_version"):
      pc_version = jobs.get("pc_version")

    if "foundation_builds" in jobs.keys():
      found_len = len(jobs["foundation_builds"])
      metadata.CSI_DEPLOYMENT_HEADERS.insert(
        len(metadata.CSI_DEPLOYMENT_HEADERS)-8,
        "Foundation Build"
      )
    if "platforms" in jobs.keys():
      platform_len = len(jobs["platforms"])

    upgrade_list = []
    for path in upgrade_paths:
      src_pe_list = prod_meta[path]["compatibilities"]["recommendations"]["AOS"]
      for src_pe in src_pe_list:
        res_tup = (path, src_pe)
        upgrade_list.append(res_tup)

    for k in range(found_len): #pylint: disable=too-many-nested-blocks
      for l in range(platform_len): #pylint: disable=invalid-name
        dep_path_dict.update({str(out_counter): {}})
        in_counter = 0
        for each_k8s in k8s_platform:
          for each_tup in upgrade_list:
            dep_path_dict[str(out_counter)].update({str(in_counter): {}})
            dep_path_dict[str(out_counter)][str(in_counter)].update({
              "row_id": str(uuid.uuid1()),
              "Source_NDK": each_tup[0],
              "Source_CSI": csi_version,
              "Source_AOS": each_tup[1],
              "Source_PC": pc_version,
              "Destination_AOS": aos_version,
              "Destination_NDK": full_ndk_version,
              "Platform": "",
              "Kubernetes_Platform": each_k8s,
              "jobs": jobs,
              "out_key": str(out_counter),
              "in_key": str(in_counter),
              "matrix_type": str(suite),
              "uuid": str(database.matrices["uuid"]),
              "matrix_start_time": database.matrices["matrix_start_time"]
            })

            if "platforms" in jobs.keys():
              dep_path_dict[str(out_counter)][str(in_counter)].update(
                {
                  "Platform": jobs["platforms"][l]
                }
              )

            if "foundation_builds" in jobs.keys():
              found_url = jobs["foundation_builds"][k]
              found_build = self._get_foundation_build_version(found_url)
              dep_path_dict[str(out_counter)][str(in_counter)].update(
                {
                  "Foundation_Build": found_build,
                  "Foundation_URL": found_url
                }
              )

            in_counter += 1
        out_counter += 1

    return dep_path_dict

  def ndk_csi_pc_aos_upgrade(self, jobs, prod_meta,#pylint: disable=no-self-use,too-many-locals
                             suite="ndk_csi_pc_aos_upgrade", **kwargs):
    """
    Method to create the Deployment Path Matrix

    Args:
      jobs(dict): Jobs.
      prod_meta(dict): Product Meta.
      suite(str): Suite Name.

    Returns:
      dep_path_list(list): List containing list of possible
                              combinations
    """
    INFO(json.dumps(kwargs))
    platform_len = 1
    out_counter = 0
    in_counter = 0
    dep_path_dict = {}
    ndk_version = jobs["ndk_version"]
    full_ndk_version = "ndk."+str(ndk_version)
    aos_version = (prod_meta[full_ndk_version]["compatibilities"]
                   ["recommendations"]["AOS"][0])
    pc_version = prod_meta[full_ndk_version]["pc_version"][0]
    csi_version = prod_meta[full_ndk_version]["csi_version"][0]
    upgrade_paths = prod_meta[full_ndk_version]["upgrade_from"]
    found_len = 1
    platform_len = 1
    k8s_platform = ["capex"]

    if jobs.get("k8s_platform"):
      k8s_platform = jobs.get("k8s_platform")

    if jobs.get("aos_version"):
      aos_version = jobs.get("aos_version")
    if jobs.get("csi_version"):
      csi_version = jobs.get("csi_version")
    if jobs.get("pc_version"):
      pc_version = jobs.get("pc_version")

    if "foundation_builds" in jobs.keys():
      found_len = len(jobs["foundation_builds"])
      metadata.CSI_DEPLOYMENT_HEADERS.insert(
        len(metadata.CSI_DEPLOYMENT_HEADERS)-8,
        "Foundation Build"
      )
    if "platforms" in jobs.keys():
      platform_len = len(jobs["platforms"])

    upgrade_list = []
    for path in upgrade_paths:
      src_pe = prod_meta[path]["compatibilities"]["recommendations"]["AOS"][-1]
      src_csi = prod_meta[path]["csi_version"][-1]
      src_pc = prod_meta[path]["pc_version"][-1]
      res_tup = (path, src_pe, src_csi, src_pc)
      upgrade_list.append(res_tup)

    for k in range(found_len): #pylint: disable=too-many-nested-blocks
      for l in range(platform_len): #pylint: disable=invalid-name
        dep_path_dict.update({str(out_counter): {}})
        in_counter = 0
        for each_k8s in k8s_platform:
          for each_tup in upgrade_list:
            dep_path_dict[str(out_counter)].update({str(in_counter): {}})
            dep_path_dict[str(out_counter)][str(in_counter)].update({
              "row_id": str(uuid.uuid1()),
              "Source_NDK": each_tup[0],
              "Source_CSI": each_tup[2],
              "Source_AOS": each_tup[1],
              "Source_PC": each_tup[3],
              "Destination_AOS": aos_version,
              "Destination_CSI": csi_version,
              "Destination_PC": pc_version,
              "Destination_NDK": full_ndk_version,
              "Platform": "",
              "Kubernetes_Platform": each_k8s,
              "jobs": jobs,
              "out_key": str(out_counter),
              "in_key": str(in_counter),
              "matrix_type": str(suite),
              "uuid": str(database.matrices["uuid"]),
              "matrix_start_time": database.matrices["matrix_start_time"]
            })

            if "platforms" in jobs.keys():
              dep_path_dict[str(out_counter)][str(in_counter)].update(
                {
                  "Platform": jobs["platforms"][l]
                }
              )

            if "foundation_builds" in jobs.keys():
              found_url = jobs["foundation_builds"][k]
              found_build = self._get_foundation_build_version(found_url)
              dep_path_dict[str(out_counter)][str(in_counter)].update(
                {
                  "Foundation_Build": found_build,
                  "Foundation_URL": found_url
                }
              )

            in_counter += 1
        out_counter += 1

    return dep_path_dict

  def ahv_feat_execution(self, jobs, suite_dict,#pylint: disable=no-self-use,too-many-locals
                         suite="ahv_feat_execution", **kwargs):
    """
    Method to create the Deployment Path Matrix

    Args:
      jobs(dict): Jobs
      suite_dict(dict): Suite Dictionary.
      suite(str): Suite Name.

    Returns:
      dep_path_list(list): List containing list of possible
                              combinations
    """
    INFO("kwargs: "+json.dumps(kwargs))
    platform_len = 1
    out_counter = 0
    in_counter = 0
    dep_path_dict = {}
    ahv_version = jobs["ahv_version"]
    aos_version = jobs.get("aos_version")

    suite_name_full_list = suite.split("_")
    suite_name = "_".join(suite_name_full_list[1:])
    feat_dict = suite_dict[suite_name]
    found_len = 1
    platform_len = 1

    if "foundation_builds" in jobs.keys():
      found_len = len(jobs["foundation_builds"])
      metadata.CSI_DEPLOYMENT_HEADERS.insert(
        len(metadata.CSI_DEPLOYMENT_HEADERS)-8,
        "Foundation Build"
      )
    if "platforms" in jobs.keys():
      platform_len = len(jobs["platforms"])

    for k in range(found_len):
      for l in range(platform_len): #pylint: disable=invalid-name
        dep_path_dict.update({str(out_counter): {}})
        in_counter = 0
        for feat in feat_dict.keys():
          INFO(str(feat_dict[feat]))
          for ind in range(len(feat_dict[feat]["job_profile"])):
            dep_path_dict[str(out_counter)].update({str(in_counter): {}})
            dep_path_dict[str(out_counter)][str(in_counter)].update({
              "row_id": str(uuid.uuid1()),
              "Source_AHV": ahv_version,
              "Source_AOS": aos_version,
              "Feat": feat,
              "Feat_Index": str(ind+1),
              "Platform": "",
              "jobs": jobs,
              "is_feat_execution": True,
              "job_profile": feat_dict[feat]["job_profile"][ind],
              "out_key": str(out_counter),
              "in_key": str(in_counter),
              "matrix_type": str(suite),
              "uuid": str(database.matrices["uuid"]),
              "matrix_start_time": database.matrices["matrix_start_time"]
            })

            if "platforms" in jobs.keys():
              dep_path_dict[str(out_counter)][str(in_counter)].update(
                {
                  "Platform": jobs["platforms"][l]
                }
              )

            if "foundation_builds" in jobs.keys():
              found_url = jobs["foundation_builds"][k]
              found_build = self._get_foundation_build_version(found_url)
              dep_path_dict[str(out_counter)][str(in_counter)].update(
                {
                  "Foundation_Build": found_build,
                  "Foundation_URL": found_url
                }
              )

            in_counter += 1
        out_counter += 1

    return dep_path_dict

  def csi_deployment(self, jobs, prod_meta, suite_dict,#pylint: disable=no-self-use,too-many-locals
                     suite="csi_deployment"):
    """
    Method to create the Deployment Path Matrix

    Args:
      jobs(dict): Jobs.
      prod_meta(dict): Product Meta.
      suite_dict(dict): Suite Dictionary.
      suite(str): Suite Name.

    Returns:
      dep_path_list(list): List containing list of possible
                              combinations
    """
    platform_len = 1
    out_counter = 0
    in_counter = 0
    dep_path_dict = {}
    csi_version = jobs["csi_version"]
    full_csi_version = "csi."+str(csi_version)
    aos_version = (prod_meta[full_csi_version]["compatibilities"]
                   ["recommendations"]["AOS"][0])
    pc_version = prod_meta[full_csi_version]["pc_version"][0]
    suite_name_full_list = suite.split("_")
    suite_name = "_".join(suite_name_full_list[1:])
    feat_dict = suite_dict[suite_name]
    found_len = 1
    platform_len = 1
    k8s_platform = ["capex"]

    if jobs.get("k8s_platform"):
      k8s_platform = jobs.get("k8s_platform")

    if jobs.get("aos_version"):
      aos_version = jobs.get("aos_version")

    if jobs.get("pc_version"):
      pc_version = jobs.get("pc_version")

    if "foundation_builds" in jobs.keys():
      found_len = len(jobs["foundation_builds"])
      metadata.CSI_DEPLOYMENT_HEADERS.insert(
        len(metadata.CSI_DEPLOYMENT_HEADERS)-8,
        "Foundation Build"
      )
    if "platforms" in jobs.keys():
      platform_len = len(jobs["platforms"])

    for k in range(found_len): #pylint: disable=too-many-nested-blocks
      for l in range(platform_len): #pylint: disable=invalid-name
        for each_k8s in k8s_platform:
          dep_path_dict.update({str(out_counter): {}})
          in_counter = 0
          for feat in feat_dict.keys():
            INFO(str(feat_dict[feat]))
            for ind in range(len(feat_dict[feat]["job_profile"])):
              dep_path_dict[str(out_counter)].update({str(in_counter): {}})
              dep_path_dict[str(out_counter)][str(in_counter)].update({
                "row_id": str(uuid.uuid1()),
                "Source_CSI": csi_version,
                "Source_AOS": aos_version,
                "Source_PC": pc_version,
                "Feat": feat,
                "Feat_Index": str(ind+1),
                "Platform": "",
                "Kubernetes_Platform": each_k8s,
                "jobs": jobs,
                "job_profile": feat_dict[feat]["job_profile"][ind],
                "out_key": str(out_counter),
                "in_key": str(in_counter),
                "matrix_type": str(suite),
                "uuid": str(database.matrices["uuid"]),
                "matrix_start_time": database.matrices["matrix_start_time"]
              })

              if feat_dict[feat].get("failure_reason"):
                dep_path_dict[str(out_counter)][str(in_counter)].update({
                  "Result": "Failed",
                  "Status": "completed",
                  "Reason": feat_dict[feat]["failure_reason"]
                })

              if "platforms" in jobs.keys():
                dep_path_dict[str(out_counter)][str(in_counter)].update(
                  {
                    "Platform": jobs["platforms"][l]
                  }
                )

              if "foundation_builds" in jobs.keys():
                found_url = jobs["foundation_builds"][k]
                found_build = self._get_foundation_build_version(found_url)
                dep_path_dict[str(out_counter)][str(in_counter)].update(
                  {
                    "Foundation_Build": found_build,
                    "Foundation_URL": found_url
                  }
                )

              in_counter += 1
          out_counter += 1

    return dep_path_dict

  def csi_deployment_path(self, jobs, prod_meta, suite): #pylint: disable=no-self-use,too-many-locals
    """
    Method to create the Deployment Path Matrix

    Args:
      jobs(dict): Jobs.
      prod_meta(dict): Product Meta.
      suite(str): Suite Name.

    Returns:
      dep_path_list(list): List containing list of possible
                              combinations
    """
    out_counter = 0
    in_counter = 0
    dep_path_dict = {}
    csi_version = jobs["csi_version"]
    full_csi_version = "csi."+str(csi_version)
    aos_version_list = (prod_meta[full_csi_version]["compatibilities"]
                        ["recommendations"]["AOS"])
    pc_version_list = prod_meta[full_csi_version]["pc_version"]
    found_len = 1
    platform_len = 1
    k8s_platform = ["capex"]

    if jobs.get("k8s_platform"):
      k8s_platform = jobs.get("k8s_platform")

    if "foundation_builds" in jobs.keys():
      found_len = len(jobs["foundation_builds"])
      metadata.CSI_DEPLOYMENT_HEADERS.insert(
        len(metadata.CSI_DEPLOYMENT_HEADERS)-8,
        "Foundation Build"
      )
    if "platforms" in jobs.keys():
      platform_len = len(jobs["platforms"])

    pc_prod_meta = json.loads(urlopen(
      metadata.PC_PRODUCT_META_URL
    ).read().decode())
    prioritzed_list = []
    for each_pc in pc_version_list:
      if pc_prod_meta.get(each_pc):
        pc_aos_list = pc_prod_meta[each_pc]["compatible_with_prism_element"]
        for each_aos in aos_version_list:
          if each_aos in pc_aos_list:
            prioritzed_list.append((csi_version, each_pc, each_aos))

    for k in range(found_len):
      for l in range(platform_len): #pylint: disable=invalid-name
        for each_k8s in k8s_platform:
          dep_path_dict.update({str(out_counter): {}})
          in_counter = 0
          for each_tuple in prioritzed_list:
            dep_path_dict[str(out_counter)].update({str(in_counter): {}})
            dep_path_dict[str(out_counter)][str(in_counter)].update({
              "row_id": str(uuid.uuid1()),
              "Source_CSI": each_tuple[0],
              "Source_AOS": each_tuple[2],
              "Source_PC": each_tuple[1],
              "Platform": "",
              "Kubernetes_Platform": each_k8s,
              "jobs": jobs,
              "out_key": str(out_counter),
              "in_key": str(in_counter),
              "matrix_type": str(suite),
              "uuid": str(database.matrices["uuid"]),
              "matrix_start_time": database.matrices["matrix_start_time"]
            })

            if "platforms" in jobs.keys():
              dep_path_dict[str(out_counter)][str(in_counter)].update(
                {
                  "Platform": jobs["platforms"][l]
                }
              )

            if "foundation_builds" in jobs.keys():
              found_url = jobs["foundation_builds"][k]
              found_build = self._get_foundation_build_version(found_url)
              dep_path_dict[str(out_counter)][str(in_counter)].update(
                {
                  "Foundation_Build": found_build,
                  "Foundation_URL": found_url
                }
              )

            in_counter += 1
          out_counter += 1

    return dep_path_dict

  def csi_pc_upgrade(self, jobs, prod_meta, suite, **kwargs): #pylint: disable=no-self-use,too-many-locals,too-many-branches,too-many-statements
    """
    Method to create the Deployment Path Matrix

    Args:
      jobs(dict): Jobs.
      prod_meta(dict): Product Meta.
      suite(str): Suite Name.

    Returns:
      dep_path_list(list): List containing list of possible
                              combinations
    """
    platform_len = 1
    out_counter = 0
    in_counter = 0
    dep_path_dict = {}
    csi_version = jobs["csi_version"]
    full_csi_version = "csi."+str(csi_version)
    aos_version = (prod_meta[full_csi_version]["compatibilities"]
                   ["recommendations"]["AOS"][0])
    pc_version = prod_meta[full_csi_version]["pc_version"][0]
    upgrade_paths = prod_meta[full_csi_version]["upgrade_from"]

    found_len = 1
    platform_len = 1
    lcm_len = 1
    k8s_platform = ["capex"]

    if jobs.get("k8s_platform"):
      k8s_platform = jobs.get("k8s_platform")

    if jobs.get("aos_version"):
      aos_version = jobs.get("aos_version")
    if jobs.get("pc_version"):
      pc_version = jobs.get("pc_version")

    aos_prod_meta = json.loads(
      urlopen(metadata.AOS_PRODUCT_META_URL).read().decode()
    )
    aos_supported_pc_list = (aos_prod_meta[aos_version]
                             ["compatible_with_prism_central"])
    prioritzed_list = []
    for each_csi in upgrade_paths:
      src_pc = ""
      pc_list = (prod_meta[each_csi]["pc_version"])
      INFO("CSI: "+str(each_csi)+". PC List: "+str(pc_list))
      INFO("CSI: "+str(each_csi)+". AOS PC List: "+str(aos_supported_pc_list))
      if len(pc_list) > 0:
        for each_pc in pc_list:
          if each_pc in aos_supported_pc_list and each_pc != pc_version:
            src_pc = each_pc
            prioritzed_list.append((each_csi, src_pc))
            break

    if "lcm_url" in jobs.keys():
      lcm_len = len(jobs["lcm_url"])
      metadata.CSI_PC_UPGRADE_HEADERS.insert(
        len(metadata.CSI_PC_UPGRADE_HEADERS)-8,
        "LCM Version"
      )

    if "foundation_builds" in jobs.keys():
      found_len = len(jobs["foundation_builds"])
      metadata.CSI_PC_UPGRADE_HEADERS.insert(
        len(metadata.CSI_PC_UPGRADE_HEADERS)-8,
        "Foundation Build"
      )
    if "platforms" in jobs.keys():
      platform_len = len(jobs["platforms"])

    for j in range(lcm_len):#pylint:  disable=too-many-nested-blocks
      for k in range(found_len):#pylint:  disable=too-many-nested-blocks
        for l in range(platform_len): #pylint: disable=invalid-name
          for each_k8s in k8s_platform:
            dep_path_dict.update({str(out_counter): {}})
            in_counter = 0
            for each_tuple in prioritzed_list:
              dep_path_dict[str(out_counter)].update({str(in_counter): {}})
              dep_path_dict[str(out_counter)][str(in_counter)].update({
                "row_id": str(uuid.uuid1()),
                "Source_CSI": each_tuple[0],
                "Source_AOS": aos_version,
                "Source_PC": each_tuple[1],
                "Destination_CSI": full_csi_version,
                "Destination_PC": pc_version,
                "Platform": "",
                "Kubernetes_Platform": each_k8s,
                "jobs": jobs,
                "job_profile": kwargs.get("job_profile"),
                "deployment_job_profile": kwargs.get("deployment_job_profile"),
                "out_key": str(out_counter),
                "in_key": str(in_counter),
                "matrix_type": str(suite),
                "uuid": str(database.matrices["uuid"]),
                "matrix_start_time": database.matrices["matrix_start_time"]
              })

              if "platforms" in jobs.keys():
                dep_path_dict[str(out_counter)][str(in_counter)].update(
                  {
                    "Platform": jobs["platforms"][l]
                  }
                )

              if "lcm_url" in jobs.keys():
                lcm_url = jobs["lcm_url"][j]
                lcm_version = None
                lcm_list = lcm_url.split("/")
                lcm_list_len = len(lcm_list)
                if lcm_list_len >= 7:
                  lcm_version = str(lcm_list[5]+"_"+lcm_list[6])
                else:
                  lcm_version = str(lcm_list[lcm_list_len-2]+"_"+
                                    lcm_list[lcm_list_len-1])
                dep_path_dict[str(out_counter)][str(in_counter)].update(
                  {
                    "LCM_Version": lcm_version,
                    "LCM_URL": lcm_url
                  }
                )

              if "foundation_builds" in jobs.keys():
                found_url = jobs["foundation_builds"][k]
                found_build = self._get_foundation_build_version(found_url)
                dep_path_dict[str(out_counter)][str(in_counter)].update(
                  {
                    "Foundation_Build": found_build,
                    "Foundation_URL": found_url
                  }
                )

              in_counter += 1
            out_counter += 1

    return dep_path_dict

  def csi_aos_upgrade(self, jobs, prod_meta, suite, **kwargs): #pylint: disable=no-self-use,too-many-locals
    """
    Method to create the Deployment Path Matrix

    Args:
      jobs(dict): Jobs.
      prod_meta(dict): Product Meta.
      suite(str): Suite Name.

    Returns:
      dep_path_list(list): List containing list of possible
                              combinations
    """
    platform_len = 1
    out_counter = 0
    in_counter = 0
    dep_path_dict = {}
    csi_version = jobs["csi_version"]
    full_csi_version = "csi."+str(csi_version)
    aos_version = (prod_meta[full_csi_version]["compatibilities"]
                   ["recommendations"]["AOS"][0])
    pc_version = prod_meta[full_csi_version]["pc_version"][0]
    upgrade_paths = prod_meta[full_csi_version]["upgrade_from"]

    found_len = 1
    platform_len = 1
    k8s_platform = ["capex"]

    if jobs.get("k8s_platform"):
      k8s_platform = jobs.get("k8s_platform")

    if jobs.get("aos_version"):
      aos_version = jobs.get("aos_version")
    if jobs.get("pc_version"):
      pc_version = jobs.get("pc_version")

    pc_prod_meta = json.loads(
      urlopen(metadata.PC_PRODUCT_META_URL).read().decode()
    )
    pc_supported_pc_list = (pc_prod_meta[pc_version]
                            ["compatible_with_prism_element"])
    prioritzed_list = []
    for each_csi in upgrade_paths:
      src_aos = ""
      aos_list = (prod_meta[each_csi]["compatibilities"]
                  ["recommendations"]["AOS"])
      if len(aos_list) > 0:
        for each_aos in aos_list:
          if each_aos in pc_supported_pc_list and each_aos != aos_version:
            src_aos = each_aos
            prioritzed_list.append((each_csi, src_aos))
            break

    if "foundation_builds" in jobs.keys():
      found_len = len(jobs["foundation_builds"])
      metadata.CSI_AOS_UPGRADE_HEADERS.insert(
        len(metadata.CSI_AOS_UPGRADE_HEADERS)-8,
        "Foundation Build"
      )
    if "platforms" in jobs.keys():
      platform_len = len(jobs["platforms"])

    for k in range(found_len):
      for l in range(platform_len): #pylint: disable=invalid-name
        for each_k8s in k8s_platform:
          dep_path_dict.update({str(out_counter): {}})
          in_counter = 0
          for each_tuple in prioritzed_list:
            dep_path_dict[str(out_counter)].update({str(in_counter): {}})
            dep_path_dict[str(out_counter)][str(in_counter)].update({
              "row_id": str(uuid.uuid1()),
              "Source_CSI": each_tuple[0],
              "Source_AOS": each_tuple[1],
              "Source_PC": pc_version,
              "Destination_CSI": csi_version,
              "Destination_AOS": aos_version,
              "Platform": "",
              "Kubernetes_Platform": each_k8s,
              "jobs": jobs,
              "job_profile": kwargs.get("job_profile"),
              "deployment_job_profile": kwargs.get("deployment_job_profile"),
              "out_key": str(out_counter),
              "in_key": str(in_counter),
              "matrix_type": str(suite),
              "uuid": str(database.matrices["uuid"]),
              "matrix_start_time": database.matrices["matrix_start_time"]
            })

            if "platforms" in jobs.keys():
              dep_path_dict[str(out_counter)][str(in_counter)].update(
                {
                  "Platform": jobs["platforms"][l]
                }
              )

            if "foundation_builds" in jobs.keys():
              found_url = jobs["foundation_builds"][k]
              found_build = self._get_foundation_build_version(found_url)
              dep_path_dict[str(out_counter)][str(in_counter)].update(
                {
                  "Foundation_Build": found_build,
                  "Foundation_URL": found_url
                }
              )

            in_counter += 1
          out_counter += 1

    return dep_path_dict

  def csi_upgrade(self, jobs, prod_meta, suite="csi_upgrade", **kwargs): #pylint: disable=no-self-use,too-many-locals
    """
    Method to create the Deployment Path Matrix

    Args:
      jobs(dict): Jobs.
      prod_meta(dict): Product Meta.
      suite(str): Suite Name.

    Returns:
      dep_path_list(list): List containing list of possible
                              combinations
    """
    platform_len = 1
    out_counter = 0
    in_counter = 0
    dep_path_dict = {}
    csi_version = jobs["csi_version"]
    full_csi_version = "csi."+str(csi_version)
    aos_version = (prod_meta[full_csi_version]["compatibilities"]
                   ["recommendations"]["AOS"][0])
    pc_version = prod_meta[full_csi_version]["pc_version"][0]
    upgrade_paths = prod_meta[full_csi_version]["upgrade_from"]

    found_len = 1
    platform_len = 1
    k8s_platform = ["capex"]

    if jobs.get("k8s_platform"):
      k8s_platform = jobs.get("k8s_platform")

    if jobs.get("aos_version"):
      aos_version = jobs.get("aos_version")

    if jobs.get("pc_version"):
      pc_version = jobs.get("pc_version")

    prioritzed_list = []
    for each_csi in upgrade_paths:
      src_nos = "6.6.2.6"
      src_pc = "pc.2023.3"
      nos_list = (prod_meta[each_csi]["compatibilities"]["recommendations"]
                  ["AOS"])
      pc_list = (prod_meta[each_csi]["pc_version"])
      if len(nos_list) > 0:
        src_nos = nos_list[-1]
      if len(pc_list) > 0:
        src_pc = pc_list[-1]
      prioritzed_list.append((each_csi, src_nos, src_pc))

    if "foundation_builds" in jobs.keys():
      found_len = len(jobs["foundation_builds"])
      metadata.CSI_DEPLOYMENT_HEADERS.insert(
        len(metadata.CSI_DEPLOYMENT_HEADERS)-8,
        "Foundation Build"
      )
    if "platforms" in jobs.keys():
      platform_len = len(jobs["platforms"])

    for k in range(found_len):
      for l in range(platform_len): #pylint: disable=invalid-name
        for each_k8s in k8s_platform:
          dep_path_dict.update({str(out_counter): {}})
          in_counter = 0
          for each_tuple in prioritzed_list:
            dep_path_dict[str(out_counter)].update({str(in_counter): {}})
            dep_path_dict[str(out_counter)][str(in_counter)].update({
              "row_id": str(uuid.uuid1()),
              "Source_CSI": each_tuple[0],
              "Source_AOS": each_tuple[1],
              "Source_PC": each_tuple[2],
              "Destination_CSI": csi_version,
              "Destination_AOS": aos_version,
              "Destination_PC": pc_version,
              "Platform": "",
              "Kubernetes_Platform": each_k8s,
              "jobs": jobs,
              "job_profile": kwargs.get("job_profile"),
              "deployment_job_profile": kwargs.get("deployment_job_profile"),
              "out_key": str(out_counter),
              "in_key": str(in_counter),
              "matrix_type": str(suite),
              "uuid": str(database.matrices["uuid"]),
              "matrix_start_time": database.matrices["matrix_start_time"]
            })

            if "platforms" in jobs.keys():
              dep_path_dict[str(out_counter)][str(in_counter)].update(
                {
                  "Platform": jobs["platforms"][l]
                }
              )

            if "foundation_builds" in jobs.keys():
              found_url = jobs["foundation_builds"][k]
              found_build = self._get_foundation_build_version(found_url)
              dep_path_dict[str(out_counter)][str(in_counter)].update(
                {
                  "Foundation_Build": found_build,
                  "Foundation_URL": found_url
                }
              )

            in_counter += 1
          out_counter += 1

    return dep_path_dict

  def objects_upgrade(self, jobs, prod_meta,#pylint: disable=no-self-use,too-many-locals,too-many-branches,too-many-statements
                      suite="objects_upgrade", **kwargs):
    """
    Method to create the Deployment Path Matrix

    Args:
      jobs(dict): Jobs.
      prod_meta(dict): Product Meta.
      suite(str): Suite Name.

    Returns:
      dep_path_list(list): List containing list of possible
                              combinations
    """
    INFO(str(kwargs))
    platform_len = 1
    out_counter = 0
    in_counter = 0
    dep_path_dict = {}
    objects_version = (jobs["objects_version"] if jobs["objects_version"] !=
                       "poseidon" else "master")
    skip_src_oss_list = ["3.1.2", "3.2.0.1", "3.2.0.2", "3.2.0.3", "3.2.1.1",
                         "3.3", "3.3.1.1", "3.4.0.1", "3.4.0.2", "3.5"]
    INFO(objects_version)
    buckets_service_prod_meta_url = copy.deepcopy(
      metadata.BUCKETS_SVC_PROD_META_URL
    )
    if jobs.get("buckets_service_prod_meta"):
      buckets_service_prod_meta_url = copy.deepcopy(
        jobs.get("buckets_service_prod_meta")
      )
    buckets_service_prod_meta = json.loads(
      urlopen(buckets_service_prod_meta_url).read().decode()
    )

    buckets_manager_prod_meta_url = copy.deepcopy(
      metadata.BUCKETS_MNGR_PROD_META_URL
    )
    if jobs.get("buckets_manager_prod_meta"):
      buckets_manager_prod_meta_url = copy.deepcopy(
        jobs.get("buckets_manager_prod_meta")
      )
    objects_prod_meta = json.loads(
      urlopen(buckets_manager_prod_meta_url).read().decode()
    )
    last_released_objects = None
    if (not objects_prod_meta.get(objects_version) and
        objects_version != "poseidon"):
      keylist = list(objects_prod_meta.keys())
      # print(keylist)
      partkeylist = copy.deepcopy(keylist)
      for each_obj in partkeylist:
        for each_type in ["rc", "master", "latest", "smoke_passed"]:
          if each_type in each_obj:
            keylist.remove(each_obj)
      INFO(keylist)
      last_released_objects = keylist[-1]
      if jobs.get("latest_released_objects"):
        last_released_objects = jobs.get("latest_released_objects")
      upgrade_from_paths = copy.deepcopy(
        objects_prod_meta[last_released_objects]["upgrade_from"]
      )
      if last_released_objects not in upgrade_from_paths:
        upgrade_from_paths.append(last_released_objects)

      objects_prod_meta.update({
        objects_version: objects_prod_meta[last_released_objects]
      })
      if objects_prod_meta.get(objects_version):
        objects_prod_meta[objects_version]["upgrade_from"] = upgrade_from_paths

      ###### For Buckets Service
      svc_keylist = list(buckets_service_prod_meta.keys())
      # print(keylist)
      svc_partkeylist = copy.deepcopy(svc_keylist)
      for each_obj in svc_partkeylist:
        for each_type in ["rc", "master", "latest", "smoke_passed"]:
          if each_type in each_obj:
            svc_keylist.remove(each_obj)
      INFO(svc_keylist)
      last_released_objects = svc_keylist[-1]
      if jobs.get("latest_released_objects"):
        last_released_objects = jobs.get("latest_released_objects")
      upgrade_from_paths = copy.deepcopy(
        buckets_service_prod_meta[last_released_objects]["upgrade_from"]
      )
      if (last_released_objects not in upgrade_from_paths and
          objects_version == "master"):
        upgrade_from_paths.append(last_released_objects)
      if objects_version != "master":
        for path in upgrade_from_paths:
          if path >= jobs.get("latest_released_objects"):
            upgrade_from_paths.remove(path)

      buckets_service_prod_meta.update({
        objects_version: buckets_service_prod_meta[last_released_objects]
      })
      if buckets_service_prod_meta.get(objects_version):
        (buckets_service_prod_meta[objects_version]
         ["upgrade_from"]) = upgrade_from_paths

    upgrade_from_paths = objects_prod_meta[objects_version]["upgrade_from"]
    if len(upgrade_from_paths) == 0:
      keylist = list(objects_prod_meta.keys())
      # print(keylist)
      partkeylist = copy.deepcopy(keylist)
      for each_obj in partkeylist:
        for each_type in ["rc", "master", "latest", "smoke_passed"]:
          if each_type in each_obj:
            keylist.remove(each_obj)
      INFO(keylist)
      # print(keylist[-1])
      upgrade_from_paths = objects_prod_meta[keylist[-1]]["upgrade_from"]
      upgrade_from_paths.append(keylist[-1])
    INFO("lro: "+jobs.get("latest_released_objects", "0"))
    INFO(upgrade_from_paths)
    copied_upgrade_from_paths = copy.deepcopy(upgrade_from_paths)
    for path in copied_upgrade_from_paths:
      INFO("path: "+str(path))
      if jobs.get("latest_released_objects"):
        if path >= jobs.get("latest_released_objects"):
          upgrade_from_paths.remove(path)
    INFO(upgrade_from_paths)

    upgrade_from_paths.reverse()
    msp_version = None
    pc_version = None
    found_len = 1
    platform_len = 1

    if jobs.get("skip_src_oss_list"):
      skip_src_oss_list = jobs.get("skip_src_oss_list")

    if jobs.get("msp_version"):
      msp_version = jobs.get("msp_version")

    if jobs.get("pc_version"):
      pc_version = jobs.get("pc_version")
    else:
      pc_version = prod_meta.get("pc_version")

    if "foundation_builds" in jobs.keys():
      found_len = len(jobs["foundation_builds"])
      metadata.CSI_DEPLOYMENT_HEADERS.insert(
        len(metadata.CSI_DEPLOYMENT_HEADERS)-8,
        "Foundation Build"
      )
    if "platforms" in jobs.keys():
      platform_len = len(jobs["platforms"])

    pc_prod_meta = json.loads(
      urlopen(metadata.PC_PRODUCT_META_URL).read().decode()
    )
    prioritzed_list = []
    min_src_objs = "2.0"
    if jobs.get("min_src_objects"):
      min_src_objs = jobs.get("min_src_objects")
    for src_objects in upgrade_from_paths:
      if (src_objects not in ["master"] and
          self.args_manipulator.version_comparator(
            src_objects, min_src_objs
          ) != min_src_objs):
        # INFO(buckets_service_prod_meta.keys())
        if (src_objects not in skip_src_oss_list and
            src_objects in buckets_service_prod_meta):
          INFO(src_objects)
          src_pc = self.fetch_source_pc_from_objects(
            src_objects=src_objects, dst_pc=pc_version
          )
          result_tup = self._spc_upgrade_list(
            pc_prod_meta=pc_prod_meta,
            src_pc=src_pc,
            dst_pc=pc_version,
            src_objects=src_objects,
            dst_objects=objects_version,
            jobs=jobs,
            buckets_mngr_prod_meta=objects_prod_meta,
            buckets_service_prod_meta=buckets_service_prod_meta,
            product_version=("" if jobs.get("product_version") == "latest"
                             else jobs.get("product_version")),
            msp_version=msp_version
          )
          src_aos = result_tup[1]
          dst_aos = result_tup[2]
          upgrade_list = result_tup[0]

          prioritzed_list.append((src_objects, src_aos, src_pc,
                                  upgrade_list, dst_aos))

    for k in range(found_len):
      for l in range(platform_len): #pylint: disable=invalid-name
        dep_path_dict.update({str(out_counter): {}})
        in_counter = 0
        for each_tup in prioritzed_list:
          dep_path_dict[str(out_counter)].update({str(in_counter): {}})
          dep_path_dict[str(out_counter)][str(in_counter)].update({
            "row_id": str(uuid.uuid1()),
            "Source_Objects": each_tup[0],
            "Source_AOS": each_tup[1],
            "Source_PC": each_tup[2],
            "Destination_Objects": objects_version,
            "Destination_AOS": each_tup[4],
            "Destination_PC": pc_version,
            "Platform": "",
            "jobs": jobs,
            "upgrade_list": each_tup[3],
            "cluster_size": 1,
            "out_key": str(out_counter),
            "in_key": str(in_counter),
            "matrix_type": str(suite),
            "uuid": str(database.matrices["uuid"]),
            "matrix_start_time": database.matrices["matrix_start_time"]
          })

          if jobs.get("extra_args"):
            dep_path_dict[str(out_counter)][str(in_counter)].update(
              {
                "extra_args": jobs.get("extra_args")
              }
            )

          if "platforms" in jobs.keys():
            dep_path_dict[str(out_counter)][str(in_counter)].update(
              {
                "Platform": jobs["platforms"][l]
              }
            )

          if "foundation_builds" in jobs.keys():
            found_url = jobs["foundation_builds"][k]
            found_build = self._get_foundation_build_version(found_url)
            dep_path_dict[str(out_counter)][str(in_counter)].update(
              {
                "Foundation_Build": found_build,
                "Foundation_URL": found_url
              }
            )

          in_counter += 1
        out_counter += 1

    return dep_path_dict

  def objects_feat_execution(self, jobs, prod_meta, suite_dict, #pylint: disable=no-self-use,too-many-locals
                             suite="objects_deployment"): #pylint: disable=no-self-use,too-many-locals
    """
    Method to create the Deployment Path Matrix

    Args:
      jobs(dict): Jobs.
      prod_meta(dict): Product Meta.
      suite_dict(dict): Suite Dictionary.
      suite(str): Suite Name.

    Returns:
      dep_path_list(list): List containing list of possible
                              combinations
    """
    INFO(json.dumps(prod_meta))
    platform_len = 1
    out_counter = 0
    in_counter = 0
    dep_path_dict = {}
    objects_version = jobs["objects_version"]
    suite_name_full_list = suite.split("_")
    suite_name = "_".join(suite_name_full_list[1:])
    feat_dict = suite_dict[suite_name]
    found_len = 1
    platform_len = 1
    INFO(str(feat_dict))
    node_list = self.feat_manager.fetch_set_of_node_size(
      feat_dict=suite_dict,
      pipeline=jobs.get("pipeline")
    )
    node_list.sort()
    node_list.reverse()
    if jobs.get("aos_version"):
      aos_version = jobs.get("aos_version")

    if jobs.get("pc_version"):
      pc_version = jobs.get("pc_version")

    if "foundation_builds" in jobs.keys():
      found_len = len(jobs["foundation_builds"])
      metadata.CSI_DEPLOYMENT_HEADERS.insert(
        len(metadata.CSI_DEPLOYMENT_HEADERS)-8,
        "Foundation Build"
      )
    if "platforms" in jobs.keys():
      platform_len = len(jobs["platforms"])

    for k in range(found_len):#pylint: disable=too-many-nested-blocks
      for l in range(platform_len): #pylint: disable=invalid-name
        dep_path_dict.update({str(out_counter): {}})
        in_counter = 0

        for node in node_list:
          for feat in feat_dict.keys():
            if node == feat_dict[feat].get("nodes", 1):
              INFO(str(feat_dict[feat]))
              for ind in range(len(feat_dict[feat]["job_profile"])):
                dep_path_dict[str(out_counter)].update({str(in_counter): {}})
                dep_path_dict[str(out_counter)][str(in_counter)].update({
                  "row_id": str(uuid.uuid1()),
                  "Source_Objects": objects_version,
                  "Source_AOS": aos_version,
                  "Source_PC": pc_version,
                  "Feat": feat,
                  "Feat_Index": str(ind+1),
                  "Platform": "",
                  "jobs": jobs,
                  "job_profile": feat_dict[feat]["job_profile"][ind],
                  "cluster_size": feat_dict[feat].get("nodes", 1),
                  "out_key": str(out_counter),
                  "in_key": str(in_counter),
                  "matrix_type": str(suite),
                  "selenium_vm_enabled": True,
                  "feat_execution": True,
                  "uuid": str(database.matrices["uuid"]),
                  "matrix_start_time": database.matrices["matrix_start_time"]
                })

                if jobs.get("extra_args"):
                  dep_path_dict[str(out_counter)][str(in_counter)].update(
                    {
                      "extra_args": jobs.get("extra_args")
                    }
                  )

                if feat_dict[feat].get("enable_direct_pool_execution"):
                  dep_path_dict[str(out_counter)][str(in_counter)].update(
                    {
                      "enable_direct_pool_execution": feat_dict[feat].get(
                        "enable_direct_pool_execution"
                      )
                    }
                  )
                  if feat_dict[feat].get("pool_name"):
                    dep_path_dict[str(out_counter)][str(in_counter)].update(
                      {
                        "specific_pool_name": feat_dict[feat].get(
                          "pool_name"
                        )
                      }
                    )

                if "platforms" in jobs.keys():
                  dep_path_dict[str(out_counter)][str(in_counter)].update(
                    {
                      "Platform": jobs["platforms"][l]
                    }
                  )

                if "foundation_builds" in jobs.keys():
                  found_url = jobs["foundation_builds"][k]
                  found_build = self._get_foundation_build_version(found_url)
                  dep_path_dict[str(out_counter)][str(in_counter)].update(
                    {
                      "Foundation_Build": found_build,
                      "Foundation_URL": found_url
                    }
                  )

                in_counter += 1
        out_counter += 1

    return dep_path_dict

  def objects_deployment(self, jobs, prod_meta,#pylint: disable=no-self-use,too-many-locals,too-many-branches,too-many-statements
                         suite="objects_deployment", **kwargs):
    """
    Method to create the Deployment Path Matrix

    Args:
      jobs(dict): Jobs.
      prod_meta(dict): Product Meta.
      suite(str): Suite Name.

    Returns:
      dep_path_list(list): List containing list of possible
                           combinations
    """
    INFO(json.dumps(kwargs))
    INFO(json.dumps(prod_meta))
    platform_len = 1
    out_counter = 0
    in_counter = 0
    dep_path_dict = {}
    objects_version = jobs["objects_version"]

    found_len = 1
    platform_len = 1

    OBJECTS_DEPLOYMENT_DICT_URL = ("http://uranus.corp.nutanix.com/"
                                   "~venkateswararao.b/Objects_deployments"
                                   "_config.json")
    if jobs.get("objects_deployment_dict"):
      OBJECTS_DEPLOYMENT_DICT_URL = jobs.get("objects_deployment_dict")
    obj_dict = json.loads(
      urlopen(
        OBJECTS_DEPLOYMENT_DICT_URL
      ).read().decode()
    )
    objects_dep_dict = copy.deepcopy(obj_dict[objects_version])
    objects_prod_meta = json.loads(
      urlopen(metadata.BUCKETS_MNGR_PROD_META_URL).read().decode()
    )
    pc_prod_meta = json.loads(
      urlopen(metadata.PC_PRODUCT_META_URL).read().decode()
    )
    supported_pc_list = []
    if objects_prod_meta.get(
        objects_version if objects_version != "poseidon" else "master"
    ):
      if objects_prod_meta[
          objects_version if objects_version != "poseidon" else "master"
      ].get("pc"):
        supported_pc_list = objects_prod_meta[
          objects_version if objects_version != "poseidon" else "master"
        ]["pc"][-3:]
    unique_aos_list = []
    INFO(str(supported_pc_list))
    count = 1
    for pc in supported_pc_list:
      aos = "6.5"
      if pc_prod_meta.get(pc):
        comp_aos_list = pc_prod_meta[pc]["compatible_with_prism_element"]
        unq_aos = comp_aos_list[-1]
        while unq_aos in unique_aos_list:
          comp_aos_list.pop()
          if len(comp_aos_list) > 0:
            unq_aos = comp_aos_list[-1]
        if unq_aos is not None:
          aos = unq_aos
      INFO(str(pc))
      objects_dep_dict.update({
        "Supported PC - "+str(count): {
          "rdm": {
            "pc": pc,
            "aos": aos
          }
        }
      })
      count += 1

    if jobs.get("aos_version"):
      aos_version = jobs.get("aos_version")

    if jobs.get("pc_version"):
      pc_version = jobs.get("pc_version")

    if "foundation_builds" in jobs.keys():
      found_len = len(jobs["foundation_builds"])
      metadata.CSI_DEPLOYMENT_HEADERS.insert(
        len(metadata.CSI_DEPLOYMENT_HEADERS)-8,
        "Foundation Build"
      )
    if "platforms" in jobs.keys():
      platform_len = len(jobs["platforms"])

    for k in range(found_len):
      for l in range(platform_len): #pylint: disable=invalid-name
        dep_path_dict.update({str(out_counter): {}})
        in_counter = 0

        for dep_case in objects_dep_dict.keys():
          src_aos = aos_version
          src_pc = pc_version
          if (objects_dep_dict[dep_case].get("rdm") and
              objects_dep_dict[dep_case]["rdm"].get("aos")):
            src_aos = objects_dep_dict[dep_case]["rdm"].get("aos")
          if (objects_dep_dict[dep_case].get("rdm") and
              objects_dep_dict[dep_case]["rdm"].get("pc")):
            src_pc = objects_dep_dict[dep_case]["rdm"].get("pc")
          dep_path_dict[str(out_counter)].update({str(in_counter): {}})
          dep_path_dict[str(out_counter)][str(in_counter)].update({
            "row_id": str(uuid.uuid1()),
            "Source_Objects": objects_version,
            "Source_AOS": src_aos,
            "Source_PC": src_pc,
            "Deployment_Case": dep_case,
            "Platform": "",
            "jobs": jobs,
            "extra_args": objects_dep_dict[dep_case],
            "cluster_size": 1,
            "out_key": str(out_counter),
            "in_key": str(in_counter),
            "matrix_type": str(suite),
            "uuid": str(database.matrices["uuid"]),
            "matrix_start_time": database.matrices["matrix_start_time"]
          })

          if objects_dep_dict[dep_case].get("test_args"):
            dep_path_dict[str(out_counter)][str(in_counter)].update({
              "test_args": objects_dep_dict[dep_case].get("test_args")
            })

          if objects_dep_dict[dep_case].get("failure_reason"):
            dep_path_dict[str(out_counter)][str(in_counter)].update({
              "Result": "Failed",
              "Status": "completed",
              "Reason": objects_dep_dict[dep_case]["failure_reason"]
            })

          if "platforms" in jobs.keys():
            dep_path_dict[str(out_counter)][str(in_counter)].update(
              {
                "Platform": jobs["platforms"][l]
              }
            )

          if "foundation_builds" in jobs.keys():
            found_url = jobs["foundation_builds"][k]
            found_build = self._get_foundation_build_version(found_url)
            dep_path_dict[str(out_counter)][str(in_counter)].update(
              {
                "Foundation_Build": found_build,
                "Foundation_URL": found_url
              }
            )

          in_counter += 1
        out_counter += 1

    return dep_path_dict

  def msp_pc_upgrade(self, msp_product_meta, jobs, suite):#pylint: disable=too-many-locals
    """
    Method to create the MSP-PC Upgrade Matrix

    Args:
      msp_product_meta(json): A JSON object containing the Product Meta.
      jobs(json): A JSON object containing the Job details.
      suite(str): Suite Name.

    Returns:
      ahv_upgrade_list(list): List containing list of possible
                              combinations
    """
    INFO("AHV Prod Meta: "+json.dumps(msp_product_meta))
    msp_upgrade_dict = {}
    out_counter = 0
    in_counter = 0
    dst_msp = jobs["msp_version"]
    pc_version = jobs.get("pc_version", "latest")
    pe_version = jobs.get("pe_version", "latest")

    upgrade_paths = msp_product_meta[dst_msp]["upgrade_from"]
    upgrade_paths.reverse()

    # upgrade_path_len = len(upgrade_paths)
    lcm_len = 1
    found_len = 1
    platform_len = 1

    if "lcm_url" in jobs.keys():
      lcm_len = len(jobs["lcm_url"])
      metadata.MSP_PC_UPGRADE_HEADERS.insert(
        len(metadata.MSP_PC_UPGRADE_HEADERS)-8,
        "LCM Version"
      )

    if "platforms" in jobs.keys():
      platform_len = len(jobs["1platforms"])

    if "foundation_builds" in jobs.keys():
      found_len = len(jobs["foundation_builds"])
      metadata.MSP_PC_UPGRADE_HEADERS.insert(
        len(metadata.MSP_PC_UPGRADE_HEADERS)-8,
        "Foundation Build"
      )
    prioritized_list = []

    for path in upgrade_paths:
      pc_ver = msp_product_meta[path]["pc"][0]
      pe_ver = msp_product_meta[path]["pe"][0]
      prioritized_list.append((path, pc_ver, pe_ver))

    # INFO("LCM Len: "+str(lcm_len))
    # INFO("Found Len: "+str(found_len))
    # INFO("Platform Len: "+str(platform_len))
    for j in range(lcm_len): #pylint: disable=too-many-nested-blocks
      for k in range(found_len):
        for l in range(platform_len): #pylint: disable=invalid-name
          msp_upgrade_dict.update({str(out_counter): {}})
          in_counter = 0
          for each_tup in prioritized_list:
            msp_upgrade_dict[str(out_counter)].update({str(in_counter): {}})
            INFO(pe_version)
            msp_upgrade_dict[str(out_counter)][str(in_counter)].update(
              {
                "row_id": str(uuid.uuid1()),
                "Source_MSP": each_tup[0],
                "Source_PC": each_tup[1],
                "Source_AOS": each_tup[2],
                "Objects_Version": metadata.MSP_OSS_MAPPING.get(each_tup[0]),
                "Destination_MSP": dst_msp,
                "Destination_PC": pc_version,
                "Destination_AOS": pe_version,
                "Platform": "",
                "upgrade_list": [],
                "out_key": str(out_counter),
                "in_key": str(in_counter),
                "matrix_type": str(suite),
                "uuid": str(database.matrices["uuid"]),
                "matrix_start_time": database.matrices["matrix_start_time"]
              }
            )

            if "lcm_url" in jobs.keys():
              lcm_url = jobs["lcm_url"][j]
              lcm_version = None
              lcm_list = lcm_url.split("/")
              lcm_list_len = len(lcm_list)
              if lcm_list_len >= 7:
                lcm_version = str(lcm_list[5]+"_"+lcm_list[6])
              else:
                lcm_version = str(lcm_list[lcm_list_len-2]+"_"+
                                  lcm_list[lcm_list_len-1])
              msp_upgrade_dict[str(out_counter)][str(in_counter)].update(
                {
                  "LCM_Version": lcm_version,
                  "LCM_URL": lcm_url
                }
              )

            if "platforms" in jobs.keys():
              msp_upgrade_dict[str(out_counter)][str(in_counter)].update(
                {
                  "Platform": jobs["platforms"][l]
                }
              )

            if "foundation_builds" in jobs.keys():
              found_url = jobs["foundation_builds"][k]
              found_build = self._get_foundation_build_version(found_url)
              msp_upgrade_dict[str(out_counter)][str(in_counter)].update(
                {
                  "Foundation_Build": found_build,
                  "Foundation_URL": found_url
                }
              )
            in_counter += 1

          out_counter += 1
    # INFO("Out Counter: "+str(out_counter))
    INFO("MSP PC Matrix : "+json.dumps(msp_upgrade_dict))
    return msp_upgrade_dict

  def ngd_upgrade(self, ahv_product_meta, jobs): #pylint: disable=too-many-branches,no-self-use,too-many-locals,too-many-statements
    """
    Method to create the AHV Upgrade Matrix

    Args:
      ahv_product_meta(json): A JSON object containing the Product Meta.
      jobs(json): A JSON object containing the Job details.

    Returns:
      ahv_upgrade_list(list): List containing list of possible
                              combinations
    """
    ngd_upgrade_dict = {}
    out_counter = 0
    in_counter = 0
    dst_ahv = jobs["ahv_version"]
    aos_version = jobs["aos_version"]
    el_version = self.args_manipulator.get_el_version(dst_ahv)
    ahv_str = str(el_version+".nutanix."+dst_ahv)
    upgrade_paths = ahv_product_meta[ahv_str]["upgrade_from"]
    upgrade_paths.reverse()

    # upgrade_path_len = len(upgrade_paths)
    lcm_len = 1
    found_len = 1
    platform_len = 1

    if "lcm_url" in jobs.keys():
      lcm_len = len(jobs["lcm_url"])
      metadata.NGD_AHV_UPGRADE_HEADERS.insert(
        len(metadata.NGD_AHV_UPGRADE_HEADERS)-8,
        "LCM Version"
      )

    if "platforms" in jobs.keys():
      platform_len = len(jobs["platforms"])

    if "foundation_builds" in jobs.keys():
      found_len = len(jobs["foundation_builds"])
      metadata.NGD_AHV_UPGRADE_HEADERS.insert(
        len(metadata.NGD_AHV_UPGRADE_HEADERS)-8,
        "Foundation Build"
      )

    # if "gpu_models" in jobs.keys():
    #   gpu_len = len(jobs["gpu_models"])

    prioritized_list = self._prioritize_based_on_lts_sts(
      upgrade_paths=upgrade_paths,
      ahv_product_meta=ahv_product_meta,
      dst_aos=aos_version,
      jobs=jobs
    )
    # print("LCM Len: "+str(lcm_len))
    # print("Found Len: "+str(found_len))
    # print("Platform Len: "+str(platform_len))
    gpu_models = (
      DeploymentManager.fetch_models_from_resource_manager()["gpu_models"]
    )
    left_gpu_models = [i for i in metadata.GPU_MODELS if i not in gpu_models]
    for j in range(lcm_len): #pylint: disable=too-many-nested-blocks
      for k in range(found_len):
        for l in range(platform_len): #pylint: disable=invalid-name
          for gpu_model in gpu_models:
            ngd_upgrade_dict.update({str(out_counter): {}})
            in_counter = 0
            for each_tup in prioritized_list:
              ngd_upgrade_dict[str(out_counter)].update({str(in_counter): {}})

              ngd_upgrade_dict[str(out_counter)][str(in_counter)].update(
                {
                  "row_id": str(uuid.uuid1()),
                  "Source_AHV": each_tup[0],
                  "Source_AOS": aos_version,
                  "Destination_AHV": ahv_str,
                  "GPU Model": "",
                  "Platform": ""
                }
              )

              if "lcm_url" in jobs.keys():
                lcm_url = jobs["lcm_url"][j]
                lcm_version = None
                lcm_list = lcm_url.split("/")
                lcm_list_len = len(lcm_list)
                if lcm_list_len >= 7:
                  lcm_version = str(lcm_list[5]+"_"+lcm_list[6])
                else:
                  lcm_version = str(lcm_list[lcm_list_len-2]+"_"+
                                    lcm_list[lcm_list_len-1])
                ngd_upgrade_dict[str(out_counter)][str(in_counter)].update(
                  {
                    "LCM_Version": lcm_version,
                    "LCM_URL": lcm_url
                  }
                )

              if "platforms" in jobs.keys():
                ngd_upgrade_dict[str(out_counter)][str(in_counter)].update(
                  {
                    "Platform": jobs["platforms"][l]
                  }
                )

              # if "gpu_models" in jobs.keys():
              ngd_upgrade_dict[str(out_counter)][str(in_counter)].update(
                {
                  "GPU_Model": gpu_model
                }
              )

              if "foundation_builds" in jobs.keys():
                found_url = jobs["foundation_builds"][k]
                found_build = self._get_foundation_build_version(found_url)
                ngd_upgrade_dict[str(out_counter)][str(in_counter)].update(
                  {
                    "Foundation_Build": found_build,
                    "Foundation_URL": found_url
                  }
                )
              in_counter += 1

            out_counter += 1

          for gpu_model in left_gpu_models: #pylint: disable=invalid-name
            ngd_upgrade_dict.update({str(out_counter): {}})
            in_counter = 0
            for each_tup in prioritized_list:
              ngd_upgrade_dict[str(out_counter)].update({str(in_counter): {}})

              ngd_upgrade_dict[str(out_counter)][str(in_counter)].update(
                {
                  "row_id": str(uuid.uuid1()),
                  "Source_AHV": each_tup[0],
                  "Source_AOS": aos_version,
                  "Destination_AHV": ahv_str,
                  "GPU Model": "",
                  "Platform": "",
                  "Result": "Skipped",
                  "Reason": "GPU card not available"
                }
              )

              if "lcm_url" in jobs.keys():
                lcm_url = jobs["lcm_url"][j]
                lcm_version = None
                lcm_list = lcm_url.split("/")
                lcm_list_len = len(lcm_list)
                if lcm_list_len >= 7:
                  lcm_version = str(lcm_list[5]+"_"+lcm_list[6])
                else:
                  lcm_version = str(lcm_list[lcm_list_len-2]+"_"+
                                    lcm_list[lcm_list_len-1])
                ngd_upgrade_dict[str(out_counter)][str(in_counter)].update(
                  {
                    "LCM_Version": lcm_version,
                    "LCM_URL": lcm_url
                  }
                )

              if "platforms" in jobs.keys():
                ngd_upgrade_dict[str(out_counter)][str(in_counter)].update(
                  {
                    "Platform": jobs["platforms"][l]
                  }
                )

              # if "gpu_models" in jobs.keys():
              ngd_upgrade_dict[str(out_counter)][str(in_counter)].update(
                {
                  "GPU_Model": gpu_model
                }
              )

              if "foundation_builds" in jobs.keys():
                found_url = jobs["foundation_builds"][k]
                found_build = self._get_foundation_build_version(found_url)
                ngd_upgrade_dict[str(out_counter)][str(in_counter)].update(
                  {
                    "Foundation_Build": found_build,
                    "Foundation_URL": found_url
                  }
                )
              in_counter += 1

            out_counter += 1
    # print("Out Counter: "+str(out_counter))
    # print("IN Counter: "+str(in_counter))
    return ngd_upgrade_dict

  def guest_os_qual(self, jobs, run_id=None, action="guest_os_qual"):
    """
    Method to create the Guest OS Qualification Matrix

    Args:
      jobs(dict): Jobs
      run_id(str): Use a given run id for gos qual execution and data
                   ingest in elk.
      action(str): Suite Name.
    Returns:
      execution_plan(list): List containing list of possible
                              combinations
    """
    classifier = jobs.pop("classifier", "one-click")
    g = GenericGuestQualifierv2(classifier=classifier,
                                run_id=str(run_id),
                                **jobs
                               )
    execution_plan = g.generate_plan(**jobs)
    return g.gos_to_oneclick_adapter(
      execution_plan=execution_plan, action=action, run_id=run_id,
      matrix_start_time=database.matrices["matrix_start_time"], **jobs
    )

  def multi_level_upgrade(self, jobs, ahv_product_meta,#pylint: disable=too-many-locals
                          suite="multi_level_upgrade"):
    """
    A method to generate matrix for multi level upgrade

    Args:
      jobs(dict): Jobs Dictionary
      ahv_product_meta(dict): AHV Product Meta
      suite(str): Suite Name

    Returns:
      multi_level_upgrade_dict(dict): Multilevel Upgrade Dict
    """
    multi_level_upgrade_dict = {}
    out_counter = 0
    in_counter = 0
    dst_ahv = jobs.get("ahv_version")
    dst_aos = jobs.get("aos_version")

    el_version = self.args_manipulator.get_el_version(dst_ahv)
    ahv_str = str(el_version+".nutanix."+dst_ahv)
    upgrade_paths = ahv_product_meta[ahv_str]["upgrade_from"]
    upgrade_paths.reverse()

    lcm_len = 1
    found_len = 1
    platform_len = 1

    if "lcm_url" in jobs.keys():
      lcm_len = len(jobs["lcm_url"])
      metadata.AHV_AOS_UPGRADE_HEADERS.insert(
        len(metadata.AHV_AOS_UPGRADE_HEADERS)-8,
        "LCM Version"
      )

    if "platforms" in jobs.keys():
      platform_len = len(jobs["platforms"])

    if "foundation_builds" in jobs.keys():
      found_len = len(jobs["foundation_builds"])
      metadata.AHV_AOS_UPGRADE_HEADERS.insert(
        len(metadata.AHV_AOS_UPGRADE_HEADERS)-8,
        "Foundation Build"
      )

    prioritized_list = self._multi_level_combination_generator(
      ahv_product_meta=ahv_product_meta,
      jobs=jobs
    )

    for j in range(lcm_len): #pylint: disable=too-many-nested-blocks
      for k in range(found_len):
        for l in range(platform_len): #pylint: disable=invalid-name
          multi_level_upgrade_dict.update({str(out_counter): {}})
          in_counter = 0

          for each_tup in prioritized_list:
            # INFO("LCM Len: "+str(lcm_len))
            # INFO("Found Len: "+str(found_len))
            # INFO("Platform Len: "+str(platform_len))

            multi_level_upgrade_dict[str(out_counter)].update(
              {str(in_counter): {}}
            )

            multi_level_upgrade_dict[str(out_counter)][str(in_counter)].update(
              {
                "row_id": str(uuid.uuid1()),
                "out_key": str(out_counter),
                "in_key": str(in_counter),
                "matrix_type": str(suite),
                "uuid": str(database.matrices["uuid"]),
                "matrix_start_time": database.matrices["matrix_start_time"],
                "Source_AHV": each_tup[0],
                "Source_AOS": each_tup[1],
                "Mid_AHV_Versions": each_tup[2],
                "Mid_AOS_Versions": each_tup[3],
                "Destination_AOS": dst_aos,
                "Destination_AHV": ahv_str,
                "Platform": ""
              }
            )

            if "lcm_url" in jobs.keys():
              lcm_url = jobs["lcm_url"][j]
              lcm_version = None
              lcm_list = lcm_url.split("/")
              lcm_list_len = len(lcm_list)
              if lcm_list_len >= 7:
                lcm_version = str(lcm_list[5]+"_"+lcm_list[6])
              else:
                lcm_version = str(lcm_list[lcm_list_len-2]+"_"+
                                  lcm_list[lcm_list_len-1])
              (multi_level_upgrade_dict[str(out_counter)]
               [str(in_counter)].update(
                 {
                   "LCM_Version": lcm_version,
                   "LCM_URL": lcm_url
                 }
               )
              )

            if "platforms" in jobs.keys():
              (multi_level_upgrade_dict[str(out_counter)]
               [str(in_counter)].update(
                 {
                   "Platform": jobs["platforms"][l]
                 }
               )
              )

            if "foundation_builds" in jobs.keys():
              found_url = jobs["foundation_builds"][k]
              found_build = self._get_foundation_build_version(found_url)
              (multi_level_upgrade_dict[str(out_counter)]
               [str(in_counter)].update(
                 {
                   "Foundation_Build": found_build,
                   "Foundation_URL": found_url
                 }
               )
              )
            in_counter += 1

          out_counter += 1
    # INFO("Out Counter: "+str(out_counter))
    # INFO("IN Counter: "+str(in_counter))
    return multi_level_upgrade_dict

  def fetch_source_pc_from_objects(self, src_objects, dst_pc):
    """
    A method to get the objects upgrade list.

    Args:
      src_objects(str): Source Objects.
      dst_pc(str): Destination PC.

    Returns:
      src_pc(str): Source PC.
    """
    SRC_PC_MAP = {
      "3.2.0.1": "pc.2022.4.0.2",
      "3.5": "pc.2022.6",
      "4.0": "pc.2022.9",
      "4.2": "pc.2023.1.0.2",
      "4.3": "pc.2023.4",
      "4.4": "pc.2024.1"
    }
    if dst_pc > "pc.2024.1":
      SRC_PC_MAP["4.2"] = "pc.2023.4"
      SRC_PC_MAP["4.0"] = "pc.2023.4"
    elif dst_pc <= "pc.2024.1":
      SRC_PC_MAP["4.2"] = "pc.2023.3.0.1"
      SRC_PC_MAP["4.0"] = "pc.2023.3.0.1"
    SRC_OBJECTS_LIST = list(SRC_PC_MAP.keys())
    SRC_OBJECTS_LIST.reverse()
    # print(SRC_OBJECTS_LIST)
    src_obj = SRC_OBJECTS_LIST.pop()
    # print(src_obj)
    src_pc = "pc.2021.5"
    while (ArgsManipulator.version_comparator(src_objects, src_obj) ==
           src_objects):
      src_pc = SRC_PC_MAP[src_obj]
      # print(src_pc)
      if src_obj == list(SRC_PC_MAP.keys())[-1]:
        break
      src_obj = SRC_OBJECTS_LIST.pop()

    return src_pc

  def pc_upgrade_paths(self, src_pc, dst_pc, pc_prod_meta):
    """
    A method to generate the PC Upgrade Paths.

    Args:
      src_pc(str): Source PC version.
      dst_pc(str): Destination PC version.
      pc_prod_meta(dict):  PC Product Meta Dict.

    Returns:
      res_tup(tup): Result Tuple containing upgrade paths and source &
                    destination AOS.
    """
    pc_upgrade_list = [{"pc": dst_pc}]
    common_aos_list = pc_prod_meta[dst_pc]["compatible_with_prism_element"]
    dst_aos = None
    INFO("Source Pc: "+src_pc+". Destination Pc: "+dst_pc)
    while dst_pc != src_pc:
      supported_pc_list = pc_prod_meta[dst_pc]["upgrade_from"]
      # print(supported_pc_list)
      supp_pc_list = copy.deepcopy(supported_pc_list)
      for each_pc in supp_pc_list:
        if "pc" not in each_pc:
          supported_pc_list.remove(each_pc)
      # INFO(common_aos_list)
      if src_pc not in supported_pc_list:
        dst_pc = supported_pc_list[0]
        curr_supp_aos_list = pc_prod_meta[dst_pc][
          "compatible_with_prism_element"
        ]
        common_aos = [
          element for element in common_aos_list if element in
          curr_supp_aos_list
        ]
        # INFO("common"+ str(common_aos))
        if len(common_aos) <= 0:
          if dst_aos is None:
            dst_aos = common_aos_list[0]
          pc_upgrade_list[-1].update({
            "pe": common_aos_list[0]
          })
          pc_upgrade_list.append({
            "pc": dst_pc
          })

          common_aos_list = copy.deepcopy(curr_supp_aos_list)
        else:
          pc_upgrade_list.append({
            "pc": dst_pc
          })
          common_aos_list = copy.deepcopy(common_aos)
        # INFO(dst_pc)
      else:
        dst_pc = src_pc
        curr_supp_aos_list = pc_prod_meta[dst_pc][
          "compatible_with_prism_element"
        ]
        common_aos = [
          element for element in common_aos_list if element in
          curr_supp_aos_list
        ]
        if len(common_aos) <= 0:
          if dst_aos is None:
            dst_aos = common_aos_list[0]
          pc_upgrade_list[-1].update({
            "pe": common_aos_list[0]
          })
          common_aos_list = copy.deepcopy(curr_supp_aos_list)
        else:
          common_aos_list = copy.deepcopy(common_aos)
    pc_upgrade_list.reverse()
    if dst_aos is None:
      dst_aos = common_aos_list[-1]
    return (pc_upgrade_list, common_aos_list[-1], dst_aos)

  def objects_upgrade_list(self, src_objects, dst_objects,
                           buckets_service_prod_meta, jobs):
    """
    A method to get the objects upgrade list.

    Args:
      src_objects(str): Source Objects.
      dst_objects(str): Destination Objects.
      buckets_service_prod_meta(dict): Buckets Service Product Meta Dictionary.
      jobs(dict): Jobs Dictionary.

    Returns:
      upgrade_list(list): Upgrade List of tuples.
    """
    objects_upgrade_list = (buckets_service_prod_meta[dst_objects]
                            ["upgrade_from"])
    result_list = []
    if len(objects_upgrade_list) == 0:
      keylist = list(buckets_service_prod_meta.keys())
      partkeylist = copy.deepcopy(keylist)
      for each_obj in partkeylist:
        for each_type in ["rc", "master", "latest", "smoke_passed"]:
          if each_type in each_obj:
            keylist.remove(each_obj)
      # INFO(keylist)
      objects_upgrade_list = [keylist[-1]]
      if jobs.get("latest_released_objects") and dst_objects == "master":
        objects_upgrade_list = [jobs.get("latest_released_objects")]
    while src_objects not in objects_upgrade_list:
      latest_objects = copy.deepcopy(objects_upgrade_list[0])
      if latest_objects == "3.5":
        result_list.append({
          "oss": "3.6",
          "aoss": "3.6"
        })
      else:
        result_list.append({
          "oss": latest_objects,
          "aoss": latest_objects
        })
      objects_upgrade_list = (buckets_service_prod_meta[latest_objects]
                              ["upgrade_from"])
    return result_list

  def _multi_level_combination_generator(self, ahv_product_meta, jobs):#pylint: disable=too-many-locals
    """
    A method to help generate the prioritized matrix list

    Args:
      ahv_product_meta(dict): AHV Product Meta.
      jobs(dict): Jobs.

    Returns:
      prioritized_list(list): Prioritized List for all combination.
    """
    prioritized_list = []
    dst_aos = jobs.get("aos_version")
    dst_ahv = jobs.get("ahv_version")
    levels = jobs.get("levels")
    INFO(json.dumps(jobs))
    if jobs.get("mid_ahv_versions") and jobs.get("mid_aos_versions"):#pylint: disable=too-many-nested-blocks
      intermediate_ahv_list = jobs["mid_ahv_versions"].split(",")
      intermediate_aos_list = jobs["mid_aos_versions"].split(",")
      intermediate_ahv_list.append(
        dst_ahv
      )
      intermediate_aos_list.append(
        "master" if dst_aos == "master" else metadata.AOS_MAPPING[(int(
          dst_aos.split(".")[0]))].format(x=dst_aos)
      )

      min_mid_ahv = (self.args_manipulator.get_el_version(
        ahv_version=intermediate_ahv_list[0]
      )+".nutanix."+intermediate_ahv_list[0])

      int_mid_ahv = intermediate_ahv_list[1] if levels > 2 else dst_ahv
      full_int_mid_ahv = (self.args_manipulator.get_el_version(
        ahv_version=int_mid_ahv
      )+".nutanix."+int_mid_ahv)

      upgrade_paths = copy.deepcopy(ahv_product_meta[min_mid_ahv]
                                    ["upgrade_from"])
      int_upgrade_paths = (ahv_product_meta[full_int_mid_ahv]
                           ["upgrade_from"])

      for src_ahv in upgrade_paths:
        if src_ahv not in int_upgrade_paths:
          _src_aos = self._fetch_compatible_aos(
            ahv_product_meta=ahv_product_meta,
            jobs=jobs,
            multi_level=True,
            src_ahv=src_ahv,
            dst_aos=intermediate_aos_list[0].split("-")[1]
          )
          if _src_aos is not None:
            prioritized_list.append(
              (
                src_ahv, _src_aos, ",".join(intermediate_ahv_list),
                ",".join(intermediate_aos_list)
              )
            )

    else:
      _prod_meta = ahv_product_meta
      _temp_ahv = (self.args_manipulator.get_el_version(ahv_version=dst_ahv)+
                   ".nutanix."+dst_ahv)
      _temp_aos = dst_aos
      mid_ahv_versions = dst_ahv
      mid_aos_versions = ("master" if dst_aos == "master"
                          else metadata.AOS_MAPPING[(int(
                            dst_aos.split(".")[0]
                          ))].format(x=dst_aos))
      for i in range(levels-1):#pylint: disable=unused-variable
        _top_upgrade_paths = _prod_meta[_temp_ahv]["upgrade_from"]
        # print(str(_top_upgrade_paths))
        _top_ahv = max(_top_upgrade_paths, key=len)

        mid_ahv_versions = (_top_ahv.split(".")[2]+"."+_top_ahv.split(".")[3]+
                            ","+mid_ahv_versions)

        _top_aos = self._fetch_compatible_aos(
          ahv_product_meta=ahv_product_meta,
          jobs=jobs,
          multi_level=True,
          src_ahv=_top_ahv,
          dst_aos=_temp_aos
        )
        _full_aos_version = ("master" if _top_aos == "master"
                             else metadata.AOS_MAPPING[(int(
                               _top_aos.split(".")[0]
                             ))].format(x=_top_aos))
        mid_aos_versions = _full_aos_version+","+mid_aos_versions

        if _prod_meta.get(_top_ahv):
          upgrade_paths = _prod_meta[_top_ahv]["upgrade_from"]
          # print("Top AHV: "+_top_ahv)
          # print("upgrade path: "+str(upgrade_paths))
          for src_ahv in upgrade_paths:
            if src_ahv not in _top_upgrade_paths:
              _src_aos = self._fetch_compatible_aos(
                ahv_product_meta=ahv_product_meta,
                jobs=jobs,
                multi_level=True,
                src_ahv=src_ahv,
                dst_aos=_top_aos
              )
              if i == levels-2 and _src_aos is not None:
                prioritized_list.append(
                  (
                    src_ahv, _src_aos, mid_ahv_versions, mid_aos_versions
                  )
                )

        _temp_ahv = _top_ahv
        _temp_aos = _src_aos

    return prioritized_list

  def _fetch_compatible_aos(self, ahv_product_meta, src_ahv,#pylint: disable=too-many-branches
                            dst_aos, jobs, multi_level=None):
    """
    A method to fetch the compatible AOS with given AHV.

    Args:
      ahv_product_meta(dict): AHV Product Meta.
      src_ahv(str): AHV version.
      dst_aos(str): AOS version.
      jobs(dict): Jobs.
      multi_level(bool): Multi level

    Returns:
      src_aos(str): Compatible AOS version.
    """
    aos_product_meta = json.loads(
      urlopen(metadata.AOS_PROD_META_URL).read().decode()
    )
    aos_upgrade_list = aos_product_meta[dst_aos]["upgrade_from"]
    if ahv_product_meta.get(str(src_ahv)) is None:
      return None
    src_aos_list = ast.literal_eval(json.dumps(
      ahv_product_meta[str(src_ahv)]["compatibilities"]
      ["recommendations"]["AOS"]
      ))
    nos_list = ast.literal_eval(json.dumps(
      ahv_product_meta[str(src_ahv)]["nos_version"]
      ))

    if jobs.get("min_src_aos") and not multi_level:
      for each_aos in src_aos_list:
        if (ArgsManipulator.version_comparator(
            each_aos, jobs.get("min_src_aos")
        ) == jobs.get("min_src_aos") and
            each_aos != jobs.get("min_src_aos")):
          src_aos_list.remove(each_aos)

      for each_aos in nos_list:
        if (ArgsManipulator.version_comparator(
            each_aos, jobs.get("min_src_aos")
        ) == jobs.get("min_src_aos") and
            each_aos != jobs.get("min_src_aos")):
          nos_list.remove(each_aos)

    if jobs.get("max_src_aos") and not multi_level:
      for each_aos in src_aos_list:
        if (ArgsManipulator.version_comparator(
            each_aos, jobs.get("max_src_aos")
        ) == each_aos and
            each_aos != jobs.get("max_src_aos")):
          src_aos_list.remove(each_aos)

      for each_aos in nos_list:
        if (ArgsManipulator.version_comparator(
            each_aos, jobs.get("max_src_aos")
        ) == each_aos and
            each_aos != jobs.get("max_src_aos")):
          nos_list.remove(each_aos)

    for each_aos in metadata.IGNORE_AOS_UPGRADE:
      if each_aos in src_aos_list:
        src_aos_list.remove(each_aos)

    for each_aos in metadata.IGNORE_AOS_UPGRADE:
      if each_aos in nos_list:
        nos_list.remove(each_aos)

    if len(src_aos_list) > 0:
      src_aos = min(filter(lambda s: isinstance(s, str),
                           (src_aos_list)))
      if (ArgsManipulator.version_comparator(src_aos, "5.15") == "5.15" or
          src_aos not in aos_upgrade_list):
        for val in nos_list:
          if val in aos_upgrade_list:
            if val in ["2020.09.16", "5.16", "5.17.1.3", "6.5", "6.5.0.1"]:
              continue
            if ArgsManipulator.version_comparator(val, "5.15") == val:
              src_aos = val
              break
            src_aos = nos_list[len(nos_list)-1]
          else:
            continue
    else:
      for val in nos_list:
        if val not in aos_upgrade_list:
          continue
        if ArgsManipulator.version_comparator(val, "5.15") == val:
          src_aos = val
          break
        src_aos = nos_list[len(nos_list)-1]

    return src_aos


  def _prioritize_based_on_lts_sts(self, upgrade_paths, ahv_product_meta, #pylint:disable=too-many-locals
                                   dst_aos, jobs):
    """
    A method to prioritize the Source AHV-AOS based on LTS and STS.

    Args:
      upgrade_paths(list): List containing compatible Source AHV versions.
      ahv_product_meta(dict): AHV Product Meta Dictionary.
      dst_aos(str): Destination/Source AOS.
      jobs(dict): jobs

    Returns:
      prioritized_list(list): List of Prioritized (AHV,AOS) tuples.
    """
    prioritized_list = []
    aos_product_meta = json.loads(
      urlopen(metadata.AOS_PROD_META_URL).read().decode()
    )
    aos_upgrade_list = aos_product_meta[dst_aos]["upgrade_from"]
    ahv_upgrade_list = ArgsManipulator().sort_ahv_versions(
      list_of_ahv=upgrade_paths
    )
    INFO(f"AHV Upgrade list: {ahv_upgrade_list}")

    ahv_aos_combos = set()
    for src_ahv in ahv_upgrade_list:#pylint: disable=too-many-nested-blocks
      recommended_aos_list = []
      nos_ver_list = []
      INFO(f"Source AHV: {src_ahv}")
      ahv_ver_key = src_ahv

      # Handle new AHV Format in prod meta
      if "-" in src_ahv:
        if "nutanix." in src_ahv:
          ahv_ver_key = src_ahv.split("nutanix.")[1].split("-")[0]

      if ahv_ver_key in ahv_product_meta.keys():
        recommended_aos_list = ahv_product_meta[ahv_ver_key].get(
          "compatibilities", {}).get("recommendations", {}).get(
            "AOS", ["master"]
          )
        nos_ver_list = ahv_product_meta[ahv_ver_key].get(
          "nos_version", ["master"]
        )

      INFO(f"Recommended AOS List: {recommended_aos_list}\n"
           f"NOS Version List: {nos_ver_list}")

      for invalid_aos in metadata.IGNORE_AOS_UPGRADE:
        if invalid_aos in recommended_aos_list:
          recommended_aos_list.remove(invalid_aos)
        if invalid_aos in nos_ver_list:
          nos_ver_list.remove(invalid_aos)

      # Try to check for possible valid combo in recommened AOS list
      for aos_ver in recommended_aos_list:
        if aos_ver in aos_upgrade_list:
          if self._is_ahv_aos_in_range(ahv=src_ahv, aos=aos_ver, jobs=jobs):
            ahv_aos_combos.add((src_ahv, aos_ver))

      # If recommended AOS list is not present, try with nos_version_list
      if len(recommended_aos_list) == 0:
        aos_ver = min(filter(lambda s: isinstance(s, str), (nos_ver_list)))
        if aos_ver in aos_upgrade_list:
          if self._is_ahv_aos_in_range(ahv=src_ahv, aos=aos_ver, jobs=jobs):
            ahv_aos_combos.add((src_ahv, aos_ver))

    for ahv_ver, aos_ver in ahv_aos_combos:
      prioritized_list.append((ahv_ver, aos_ver))

    INFO(f"Prioritized list: {prioritized_list}")
    return prioritized_list

  def _is_ahv_aos_in_range(self, ahv, aos, jobs):
    """
    Check if given AHV AOS combo is in range, by validating against the
    following params
      min_src_ahv
      max_src_ahv
      min_src_aos
      max_src_aos

    Args:
      ahv(str): AHV Version
      aos(str): AOS Version
      jobs(dict): Jobs dict

    Returns:
      (bool): True if the combo is valid, False otherwise
    """
    min_src_ahv = jobs.get("min_src_ahv")
    max_src_ahv = jobs.get("max_src_ahv")
    min_src_aos = jobs.get("min_src_aos")
    max_src_aos = jobs.get("max_src_aos")

    if "nutanix." in ahv:
      ahv = ahv.split("nutanix.")[1]

    if min_src_ahv:
      # Check if AHV is greater than equal to min_src_ahv
      recent_ahv = ArgsManipulator.version_comparator(ahv, min_src_ahv)
      if recent_ahv == min_src_ahv and ahv != min_src_ahv:
        return False
    if max_src_ahv:
      # Check if AHV is less than or equal to max_src_ahv
      recent_ahv = ArgsManipulator.version_comparator(ahv, max_src_ahv)
      if recent_ahv == ahv and ahv != max_src_ahv:
        return False
    if min_src_aos:
      # Check if AOS is greater than or equal to min_src_aos
      recent_aos = ArgsManipulator.version_comparator(aos, min_src_aos)
      if recent_aos == min_src_aos and aos != min_src_aos:
        return False
    if max_src_aos:
      # Check if AOS is less than or equal to max_src_aos
      recent_aos = ArgsManipulator.version_comparator(aos, max_src_aos)
      if recent_aos == aos and aos != max_src_aos:
        return False

    return True

  def _pc_upgrade_list(self, src_pc, dst_pc,
                       dst_objects, jobs):
    """
    A method to get the upgrade list for pc-objects upgrade

    Args:
      src_pc(str): Source PC version.
      dst_pc(str): Destination PC version.
      dst_objects(str): Destination Objects.
      jobs(dict):  Jobs Dict.

    Returns:
      res_tup(tup): Result Tuple.
    """
    upgrade_list = []
    last_upgrade = {
      "oss": dst_objects,
      "aoss": dst_objects,
      "msp": "2.4.3.4"
    }
    if jobs.get("oss_rim_url"):
      last_upgrade.update({
        "oss_rim_url": jobs.get("oss_rim_url")
      })
    if jobs.get("aoss_rim_url"):
      last_upgrade.update({
        "aoss_rim_url": jobs.get("aoss_rim_url")
      })
    if jobs.get("pc_rim_url"):
      last_upgrade.update({
        "pc_rim_url": jobs.get("pc_rim_url")
      })
    if jobs.get("pe_rim_url"):
      last_upgrade.update({
        "pe_rim_url": jobs.get("pe_rim_url")
      })

    if src_pc == "pc.2021.5":
      upgrade_list.extend(
        [
          {
            "pc": "pc.2021.9"
          },
          {
            "pc": "pc.2022.6",
          },
          {
            "pc": dst_pc
          }
        ]
      )
      upgrade_list.append(last_upgrade)
    elif src_pc == "pc.2022.4.0.2":
      upgrade_list.extend(
        [
          {
            "pc": "pc.2022.6",
          },
          {
            "pc": dst_pc
          }
        ]
      )
      upgrade_list.append(last_upgrade)
    else:
      upgrade_list.extend([
        {
          "pc": dst_pc
        }
      ])
      upgrade_list.append(last_upgrade)

    return upgrade_list

  def _spc_upgrade_list(self, pc_prod_meta, src_pc, dst_pc, src_objects,#pylint: disable=too-many-locals
                        dst_objects, jobs,
                        buckets_service_prod_meta, product_version,
                        msp_version=None, **kwargs):
    """
    A method to get the upgrade list for pc-objects upgrade

    Args:
      pc_prod_meta(dict): PC Product Meta Dict.
      src_pc(str): Source PC version.
      dst_pc(str): Destination PC version.
      src_objects(str): Source Objects.
      dst_objects(str): Destination Objects.
      jobs(dict):  Jobs Dict.
      buckets_service_prod_meta(dict): Buckets Service Product Meta.
      product_version(str): Product Version.
      msp_version(str): MSP Version.

    Returns:
      res_tup(tup): Result Tuple.
    """
    INFO(src_objects)
    # INFO(json.dumps(buckets_mngr_prod_meta))
    INFO(json.dumps(kwargs))
    upgrade_list = []
    objects_upgrade_list = []
    last_upgrade = {
      "oss": dst_objects,
      "aoss": dst_objects,
      "objects_manager_rc": product_version
    }
    if msp_version:
      last_upgrade.update({
        "msp": msp_version
      })
    if jobs.get("oss_rim_url"):
      last_upgrade.update({
        "oss_rim_url": jobs.get("oss_rim_url")
      })
    if jobs.get("aoss_rim_url"):
      last_upgrade.update({
        "aoss_rim_url": jobs.get("aoss_rim_url")
      })
    if jobs.get("pc_rim_url"):
      last_upgrade.update({
        "pc_rim_url": jobs.get("pc_rim_url")
      })
    if jobs.get("pe_rim_url"):
      last_upgrade.update({
        "pe_rim_url": jobs.get("pe_rim_url")
      })
    if jobs.get("msp_rim_url"):
      last_upgrade.update({
        "msp_rim_url": jobs.get("msp_rim_url")
      })
    pc_upgrade_tup = self.pc_upgrade_paths(
      src_pc=src_pc,
      dst_pc=dst_pc,
      pc_prod_meta=pc_prod_meta
    )
    upgrade_list = pc_upgrade_tup[0]
    INFO("Upgrade List: "+str(upgrade_list))
    objects_upgrade_list = self.objects_upgrade_list(
      src_objects=src_objects,
      dst_objects=dst_objects,
      buckets_service_prod_meta=buckets_service_prod_meta,
      jobs=jobs
    )
    objects_upgrade_list.reverse()
    INFO("Objects Upgrade: "+str(objects_upgrade_list))
    upgrade_list.extend(objects_upgrade_list)
    upgrade_list.append(last_upgrade)

    # INFO("Final List: "+str((upgrade_list, pc_upgrade_tup[1],
    #                          pc_upgrade_tup[2])))
    return (upgrade_list, pc_upgrade_tup[1], pc_upgrade_tup[2])

  def _get_foundation_build_version(self, foundation_url):
    """
    Get foundation build from the given foundation URL
    Args:
      foundation_url(string): Foundation URL
    Returns:
      foundation_build_version(string): Foundation Build Version
    """
    # Foundation build URL would most likely look like-
    # "http://endor.dyn.nutanix.com/builds/foundation-builds/master/"
    # "foundation-master-1-86cdc22a-universal-release.x86_64.tar.gz"
    # But if this format changes or we are using a private build etc.
    # this method should not break. It would return Unknown in the cases where
    # our logic to fetch foundation build version from the URL fails.
    try:
      foundation_build_version = foundation_url.split("/")[-2]
    except Exception as ex:
      ERROR(ex)
      foundation_build_version = "Unknown"
    return foundation_build_version
