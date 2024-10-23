"""
Copyright (c) 2021 Nutanix Inc. All rights reserved.

Author: vedant.dalal@nutanix.com

RDM Client Module.
"""
# pylint:disable=inconsistent-return-statements
import copy
import time
import json

from framework.lib.nulog import INFO, ERROR
from framework.lib.tools_client.base_rest_client import BaseRestClient

from workflows.acropolis.apeiron.framework.rdm.url_builder import \
  create_pc_build_url, create_pc_url
from libs.ahv.workflows.one_click import metadata
from workflows.acropolis.apeiron.framework.helper_module import ApeironUtil


class RDMClient(BaseRestClient):
  """
  A RDM Client Class
  """
  def __init__(self, username=None, password=None):
    """
    Constructor method

    Args:
      username(str): Username
      password(str): Password
    """
    super(RDMClient, self).__init__(username=username, password=password)
    self.username = username
    self.password = password

  @staticmethod
  def get_ahv_url(full_ahv_ver):
    """
    Get the AHV URL based on build
    Args:
      full_ahv_ver(str): ex - el8.nutanix.ahv_ver (can be ahv_ver also)
    Returns:
      ahv_build_url(str): AHV build URL or None if AHV Version is branch_symlink
    """
    INFO(f"Full AHV Version: {full_ahv_ver}")
    if "branch_symlink" in full_ahv_ver:
      return None

    if "nutanix." in full_ahv_ver:
      ahv_ver = full_ahv_ver.split("nutanix.")[1]
    else:
      ahv_ver = full_ahv_ver
    INFO(f"AHV Version: {ahv_ver}")

    if "-" not in ahv_ver:
      ahv_build_url = f"http://endor.dyn.nutanix.com/builds/ahv-builds/"\
                      f"{ahv_ver}/iso/AHV-DVD-x86_64-{full_ahv_ver}.iso"
    else:
      # For 10.0.1-999 -> 10.0.1
      ahv_version = ahv_ver.split("-")[0]
      # For 10.0.1.999 -> 10/10.0.1/10.0.1-999
      major_version = ahv_version.split(".")[0]
      build_path = f"{major_version}/{ahv_version}/{ahv_ver}"

      ahv_build_url = f"http://endor.dyn.nutanix.com/builds/ahv-builds/"\
                      f"{build_path}/iso/AHV-DVD-x86_64-{ahv_ver}.iso"
    INFO(f"AHV: {ahv_ver}\nBUILD URL: {ahv_build_url}")
    return ahv_build_url

  def deploy_cluster(self, payload):
    """
    A method to deploy a cluster through RDM

    Args:
      payload(json): Payload to deploy a cluster

    Returns:
      deployment_id(str): Scheduled Deployment ID
    """
    deployment_id = None
    basic_auth = (self.username, self.password)
    response = self.post(url=metadata.RDM_SCHEDULED_DEPLOYMENT_URL,
                         auth=basic_auth, json=payload)
    INFO("RDM Deploy Cluster Payload: "+json.dumps(payload))
    if response.status_code == 200:
      result = response.json()
      if result["success"]:
        deployment_id = result["id"]
        INFO("Fetched the RDM Deployment ID")
      else:
        ERROR("Unable to Deploy/Fetch the Deployment ID: "+result["message"])
    else:
      ERROR("Unable to Deploy/Fetch the Deployment ID. "+response.text)

    return deployment_id

  def release_cluster(self, deployment_id):
    """
    A method to deploy a cluster through RDM

    Args:
      deployment_id(str): Deployment ID

    """
    basic_auth = (self.username, self.password)
    api_url = "{base_url}/{dep_id}/release_resources".format(
      base_url=metadata.RDM_SCHEDULED_DEPLOYMENT_URL,
      dep_id=str(deployment_id)
    )
    payload = {"force_release": True}
    response = self.post(url=api_url, auth=basic_auth, json=payload)

    if response.status_code == 200:
      result = response.json()
      if result["success"]:
        INFO("Released the cluster with deployment id: "+str(deployment_id))
      else:
        ERROR("Unable to release the Deployment ID: "+result["message"])
    else:
      ERROR("Unable to release the Deployment ID. "+response.text)

  def get_deployment_status(self, deployment_id):
    """
    A method to get the deployment status of the cluster

    Args:
      deployment_id(str): Scheduled Deployment ID

    Returns:
      deployment_status(str): Deployment Status
    """
    deployment_status = None
    url = "{base_url}/{deploy_id}".format(
      base_url=metadata.RDM_SCHEDULED_DEPLOYMENT_URL,
      deploy_id=deployment_id
    )

    response = self.get(url=url)

    if response.status_code == 200:
      result = response.json()
      if result["success"]:
        deployment_status = result["data"]["status"]
        INFO("Fetched the RDM Deployment Status: "+str(deployment_status))
      else:
        ERROR("Unable to Deploy/Fetch the Deployment Status: "+
              result["message"])
    else:
      ERROR("Unable to Deploy/Fetch the Deployment Status. "+response.text)

    return deployment_status

  def get_scheduled_deployment_data(self, deployment_id):
    """
    A method to get the deployment status of the cluster

    Args:
      deployment_id(str): Scheduled Deployment ID

    Returns:
      deployment_status(str): Deployment Status
    """
    deployment_data = None
    url = "{base_url}/{deploy_id}".format(
      base_url=metadata.RDM_SCHEDULED_DEPLOYMENT_URL,
      deploy_id=deployment_id
    )

    response = self.get(url=url)

    if response.status_code == 200:
      result = response.json()
      if result["success"]:
        deployment_data = result["data"]
        # INFO("Fetched the RDM Deployment Data: "+str(deployment_data))
      else:
        ERROR("Unable to Deploy/Fetch the Deployment Status: "+
              result["message"])
    else:
      ERROR("Unable to Deploy/Fetch the Deployment Status. "+response.text)

    return deployment_data

  def get_deployment_id(self, deployment_id):
    """
    A method to get the deployment status of the cluster

    Args:
      deployment_id(str): Scheduled Deployment ID

    Returns:
      deployment_id(str): Deployment Status
    """
    url = "{base_url}/{deploy_id}".format(
      base_url=metadata.RDM_SCHEDULED_DEPLOYMENT_URL,
      deploy_id=deployment_id
    )
    INFO(url)
    response = self.get(url=url)
    INFO(response)
    if response.status_code == 200:
      result = response.json()
      if result["success"]:
        if len(result["data"]["deployments"]) <= 1:
          deployment_id = [result["data"]["deployments"][0]["$oid"]]
        else:
          deployment_id = []
          for i in range(len(result["data"]["deployments"])-1):
            deployment_id.append(result["data"]["deployments"][i]["$oid"])
        INFO("Fetched the RDM Deployment ID")
      else:
        ERROR("Unable to Fetch the Deployment ID: "+result["message"])
    else:
      ERROR("Unable to Fetch the Deployment ID. "+response.text)

    return deployment_id

  def get_cluster_name(self, deployment_id):
    """
    A method to fetch the cluster name from the deployment details

    Args:
      deployment_id(str): Scheduled Deployment ID

    Returns:
      cluster_name(str): Deployed Cluster Name.
    """
    time.sleep(60)
    cluster_name = None
    cluster_ip = None
    url = "{base_url}/{deploy_id}".format(
      base_url=metadata.RDM_DEPLOYMENT_URL,
      deploy_id=deployment_id
    )

    response = self.get(url=url)

    if response.status_code == 200:
      result = response.json()
      if result["success"]:
        cluster_name = result["data"]["allocated_resource"]["name"]
        if result["data"]["allocated_resource"].get("svm_ip"):
          cluster_ip = result["data"]["allocated_resource"]["svm_ip"]
        if result["data"]["allocated_resource"].get("ip"):
          cluster_ip = result["data"]["allocated_resource"]["ip"]
        INFO("Fetched the RDM Deployment ID")
      else:
        ERROR("Unable to Fetch the Deployment ID: "+result["message"])
    else:
      ERROR("Unable to Fetch the Deployment ID. "+response.text)

    return (cluster_name, cluster_ip)

  def fetch_pc_build_url(self, pc_version):
    """
    A method to fetch the pc build url from pc version.

    Args:
      pc_version(str): PC Version.

    Returns:
      pc_build_url(str): PC Build URL.
    """
    pc_build_url = None
    url = create_pc_build_url(pc_version=pc_version)

    response = self.get(url=url)

    if response.status_code == 200:
      result = response.json()
      if result.get("result") and len(result["result"]["data"]) > 0:
        githash = result["result"]["data"][0]["githash"]
        gbn = result["result"]["data"][0]["gbn"]
        if githash and gbn is not None:
          pc_build_url = create_pc_url(pc_version=pc_version,
                                       githash=githash, gbn=gbn)
        INFO("Fetched the Build URL: " + str(pc_build_url))

      else:
        INFO("Unable to fetch the Build URL")
    else:
      INFO("Response Status Code not 200, instead found as: " +
           str(response.status_code))
      INFO("Error: " + str(response.text))

    return pc_build_url

  def image_cluster(self, cluster_name, ahv, nos, nos_url=None,#pylint: disable=too-many-locals,too-many-statements,too-many-branches
                    found_vm_ip=None, foundation_build_url=None,
                    hypervisor_url=None, co_imaging=None, so_imaging=None,
                    pc_version=None, pc_build_url=None, selenium_vm=None,
                    **kwargs):
    """
    A method to image a cluster

    Args:
      cluster_name(str): Name of the cluster to be imaged.
      ahv(str): AHV version to be imaged on cluster.
      nos(str): NOS version to be imaged on cluster.
      nos_url(str): NOS URL to be used for imaging. Optional.
      found_vm_ip(str): Foundation VM IP to be used for imaging. Optional.
      foundation_build_url(str): Foundation Build URL for imaging. Optional.
      hypervisor_url(str): AHV Hypervisor ISO URL.
      co_imaging(bool): Compute only nodes enabling.
      so_imaging(bool): Storage only nodes enabling.
      pc_version(str): PC version to re image.
      pc_build_url(str): PC Build URL.
      selenium_vm(bool): Selenium VM.

    Returns:
      image_req_id(str): Imaging ID.
    """
    INFO("PC Version: "+str(pc_version))
    basic_auth = (self.username, self.password)
    hypervisor_url = RDMClient.get_ahv_url(full_ahv_ver=ahv)
    INFO("hypervisor_url: "+str(hypervisor_url))
    image_payload = copy.deepcopy(metadata.RDM_IMAGING_PAYLOAD)
    image_payload["name"] = "svc_ahv_qa_"+str(time.time())
    im_payload_res_spec = copy.deepcopy(image_payload["resource_specs"][0])
    im_payload_res_spec["name"] = cluster_name
    im_payload_res_spec["resources"]["entries"][0]["name"] = cluster_name
    im_payload_res_spec["software"]["nos"]["version"] = (
      "master" if nos == "master" else metadata.AOS_MAPPING[
        (int(nos.split(".")[0]))].format(x=nos)
    )
    if kwargs.get("rdm_arg") and kwargs.get("rdm_arg") is not None:
      if kwargs["rdm_arg"].get("redundancy_factor"):
        im_payload_res_spec["software"]["nos"]["redundancy_factor"] = (
          int(kwargs["rdm_arg"]["redundancy_factor"])
        )

    if kwargs.get("rdm_arg") and kwargs.get("rdm_arg") is not None:
      if kwargs["rdm_arg"].get("all_flash_cluster"):
        im_payload_res_spec["hardware"]["all_flash_cluster"] = (
          int(kwargs["rdm_arg"]["all_flash_cluster"])
        )
    im_payload_res_spec["software"]["hypervisor"]["version"] = ahv
    image_req_id = None
    if nos_url is not None:
      im_payload_res_spec["software"]["nos"].update(
        {
          "build_url": nos_url
        }
      )
    if found_vm_ip is not None:
      im_payload_res_spec.update(
        {
          "foundation_vm_ip": found_vm_ip,
          "use_foundation_vm": True
        }
      )
    if foundation_build_url is not None:
      im_payload_res_spec.update(
        {
          "foundation_build_url": foundation_build_url
        }
      )
    if hypervisor_url is not None:
      im_payload_res_spec["software"]["hypervisor"].update({
        "build_url": str(hypervisor_url)
      })
    else:
      if ahv != "branch_symlink" and kwargs.get("full_ahv"):
        im_payload_res_spec["software"]["hypervisor"].update({
          "build_url": metadata.HYP_URL.format(
            hyp=str(ahv),
            hyp_full=str(kwargs["full_ahv"])
          )
        })

    if co_imaging:
      im_payload_res_spec["hardware"].update({
        "compute_nodes": {
          "min_count": 1
        }
      })
      im_payload_res_spec["software"].update({
        "compute_nodes": {
          "hypervisor_type": "ahv",
          "hypervisor_version": ahv,
        }
      })
      if hypervisor_url is not None:
        im_payload_res_spec["software"]["compute_nodes"].update({
          "hypervisor_url": str(hypervisor_url)
        })

    if so_imaging:
      im_payload_res_spec["hardware"].update({
        "storage_nodes": {
          "min_count": 1
        }
      })
      im_payload_res_spec["software"].update({
        "storage_nodes": {
          "hypervisor_type": "ahv",
          "hypervisor_version": ahv,
        }
      })
      if hypervisor_url is not None:
        im_payload_res_spec["software"]["storage_nodes"].update({
          "hypervisor_url": str(hypervisor_url)
        })

    if kwargs.get("rdm_arg") and kwargs.get("rdm_arg") is not None:
      if kwargs["rdm_arg"].get("min_host_gb_ram"):
        im_payload_res_spec["hardware"]["min_host_gb_ram"] = (
          int(kwargs["rdm_arg"]["min_host_gb_ram"])
        )

    if pc_version is not None:
      num_ips = 20
      base_num_ips = 20

      if kwargs.get("cluster_size"):
        num_ips = int(kwargs.get("cluster_size"))*base_num_ips

      if kwargs.get("static_ips_to_reserve"):
        num_ips = int(kwargs.get("static_ips_to_reserve"))

      im_payload_res_spec.update({
        "static_ips": [
          {
            "num_ips": num_ips,
            "continuous":True
          }
        ]
      })
    image_payload["resource_specs"][0] = copy.deepcopy(im_payload_res_spec)
    if pc_version is not None:
      pc_payload_res_spec = copy.deepcopy(metadata.RDM_PC_DEPLOYMENT_PAYLOAD)
      if kwargs.get("rdm_arg") and kwargs.get("rdm_arg") is not None:
        if kwargs["rdm_arg"].get("pc_num_instance"):
          pc_payload_res_spec["scaleout"]["num_instances"] = int(
            kwargs["rdm_arg"]["pc_num_instance"]
          )
        if kwargs["rdm_arg"].get("pcvm_size"):
          pc_payload_res_spec["scaleout"]["pcvm_size"] = (
            kwargs["rdm_arg"]["pcvm_size"]
          )
      pc_payload_res_spec["name"] = ("svc_ahv_qa_pc_"+
                                     str(time.time()).replace(".", ""))
      # pc_payload_res_spec["software"]["prism_central"]["version"] = pc_version
      pc_payload_res_spec["software"]["prism_central"]["build_url"] = (
        pc_build_url if pc_build_url else
        metadata.PC_BUILD_URL.get(
          pc_version, "pc.2022.6"
        )
      )
      pc_payload_res_spec["dependencies"] = [cluster_name]
      pc_payload_res_spec["provider"]["host"] = cluster_name
      pc_payload_res_spec["prism_elements"] = [{"host": cluster_name}]
      image_payload["resource_specs"].append(pc_payload_res_spec)

    if selenium_vm:
      pc_payload_res_spec = metadata.RDM_SELENIUM_VM_PAYLOAD
      if kwargs.get("rdm_arg", {}).get("selenium_build_url"):
        pc_payload_res_spec["software"]["build_url"] = \
          kwargs["rdm_arg"]["selenium_build_url"]
      pc_payload_res_spec["name"] = ("svc_ahv_qa_sm_vm_"+
                                     str(time.time()).replace(".", ""))
      pc_payload_res_spec["dependencies"] = [cluster_name]
      pc_payload_res_spec["provider"]["host"] = cluster_name

      image_payload["resource_specs"].append(pc_payload_res_spec)

    if (kwargs.get("rdm_payload_update") and
        kwargs.get("rdm_payload_update") is not None):
      for payload in kwargs["rdm_payload_update"]:
        key_to_update = payload["key_to_update"]
        value = payload["value"]
        INFO("Updating the rdm payload for key '{}' with new value "
             "as '{}'".format(key_to_update, value))
        image_payload.update(ApeironUtil.search_and_replace(\
          image_payload, key_to_update, value))
    INFO("RDM Imaging Payload: %s" % json.dumps(image_payload))
    response = self.post(url=metadata.RDM_SCHEDULED_DEPLOYMENT_URL,
                         auth=basic_auth, json=image_payload)
    INFO("RDM Imaging Response: "+str(response))
    if response.status_code == 200:
      result = response.json()
      if result["success"]:
        image_req_id = result["id"]
      else:
        ERROR("Unable to image the cluster: "+result["message"])
    else:
      ERROR("Unable to image the cluster. "+response.text)

    return image_req_id

  def extend_cluster_life(self, rdm_dep_id, hours=120):
    """
    A method to extend the cluster life.

    Args:
      rdm_dep_id(str): RDM Deployment ID.
      hours(int): Duration of extending the cluster life.
    """
    url = "{base_url}/{task_id}".format(
      base_url=metadata.RDM_SCHEDULED_DEPLOYMENT_URL,
      task_id=rdm_dep_id
    )
    api_payload = {"duration": hours}

    basic_auth = (self.username, self.password)

    response = self.put(url=url, auth=basic_auth, json=api_payload)

    if response.status_code == 200:
      result = response.json()
      if result["success"]:
        INFO("Deployemt ID: "+str(rdm_dep_id)+" extended by "+
             str(hours)+" hours.")
      else:
        ERROR("Unable to extend the deployment due to: "+result["message"])
    else:
      ERROR("Unable to extend the deployment, error message: "+response.text)

  def fetch_smoke_passed_pc_build_url(self, pc_version):
    """
    A method to fetch smoke passed PC Build URL

    Args:
      pc_version(str): PC Version

    Returns:
      pc_url(str): PC Build URL
    """
    response = self.get(url=create_pc_build_url(pc_version=pc_version))
    if response.status_code == 200:
      pc_data_dict = response.json()
      for pc_data in pc_data_dict["result"]["data"]:
        githash = pc_data.get("githash")
        gbn = pc_data.get("gbn")
        if githash and gbn is not None:
          return create_pc_url(pc_version=pc_version, githash=githash, gbn=gbn)
    return "unable_to_find_pc_url"

  def image_status(self, image_id):
    """
    A method to fetch status of cluster imaging

    Args:
      image_id(str): Imaging ID whose status to be checked.

    Returns:
      image_status(str): Imaging status.
    """
    image_status = None

    url = "{base_url}/{id}".format(
      base_url=metadata.RDM_SCHEDULED_DEPLOYMENT_URL,
      id=image_id
    )

    response = self.get(url=url)
    if response.status_code == 200:
      result = response.json()
      if result["success"]:
        image_status = result["data"]["status"]
      else:
        ERROR("Unable to fetch status of imaging of the cluster: "
              +result["message"])
    else:
      ERROR("Unable to fetch status of imaging of the cluster: "+response.text)

    return image_status
