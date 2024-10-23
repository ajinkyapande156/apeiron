"""
Copyright (c) 2021 Nutanix Inc. All rights reserved.

Author: vedant.dalal@nutanix.com

Jarvis Client Module.
"""
import json
import copy

from framework.lib.nulog import INFO, DEBUG, ERROR
from framework.lib.tools_client.jarvis_rest_client import JarvisRestClient
from libs.ahv.workflows.one_click import metadata

class JarvisClient(JarvisRestClient):
  """
  A class containing methods to expose Jarvis APIs
  """
  def __init__(self, username=None, password=None):
    """
    Constructor method

    Args:
      username(str): Username
      password(str): Password
    """
    super(JarvisClient, self).__init__(username=username, password=password)
    self.username = username
    self.password = password

  def get_node_pool_id(self, node_pool_name):
    """
    A method to get the Node Pool ID from it's name

    Args:
      node_pool_name(str): Node Pool Name

    Returns:
      node_pool_id(str): Node Pool ID
    """
    node_pool_id = None

    params = {
      "raw_query": json.dumps({
        "name":node_pool_name
      })
    }

    response = self.get(url=metadata.JARVIS_NODE_POOL_URL, params=params)

    if response.status_code == 200:
      result = response.json()
      if result["success"]:
        node_pool_id = result["data"][0]["_id"]["$oid"]
        INFO("Fetched the Node Pool ID: "+str(node_pool_id))
      else:
        ERROR("Unable to fetch the Node Pool ID: "+result["message"])
    else:
      ERROR("Unable to fetch the Node Pool ID. "+response.text)

    return node_pool_id

  def get_node_details_from_pool(self, node_pool_id):
    """
    A method to get Node Details of the given Node Pool

    Args:
      node_pool_id(str): Node Pool ID

    Returns:
      node_details(json): JSON containing Node details
    """
    node_details = None

    url = "{base_url}/{node_pool_id}/node_details".format(
      base_url=metadata.JARVIS_V2_NODE_POOL_URL,
      node_pool_id=node_pool_id
    )

    response = self.get(url=url)

    if response.status_code == 200:
      result = response.json()
      if result["success"]:
        node_details = result["data"]
        # INFO("Node details: "+json.dumps(node_details))
      else:
        ERROR("Unable to fetch the Node Details: "+result["message"])
    else:
      ERROR("Unable to fetch the Node Details. "+response.text)

    return node_details

  def only_all_flash_storage_nodes_in_pool(self, pool_name):
    """
    Check if pool has only nodes with all flash storage
    Args:
      pool_name(string): Pool name
    Returns:
      (bool): True if all available nodes have only all flash storage,
              False otherwise
    """
    all_flash_pool = True
    free_nodes = False
    # A node having only SSD Storage disk is called all flash storage node
    if pool_name in metadata.JARVIS_SPECIAL_POOLS:
      # NOTE: Handle global-pools
      DEBUG("Global pool will be treated as no-flash due to no visibility")
    else:
      pool_id = self.get_node_pool_id(node_pool_name=pool_name)
      node_details = self.get_node_details_from_pool(node_pool_id=pool_id)

      for node_detail in node_details:
        # Check only those nodes which are enabled and not part of
        # active cluster
        if node_detail["is_enabled"] and node_detail["cluster_name"] is None:
          free_nodes = True
          storage_disks = node_detail["hardware"]["storage"]
          # If there are no storage disks,
          # then it will be considered as non all flash node
          if len(storage_disks) == 0:
            all_flash_pool = False
          for storage_disk in storage_disks:
            if storage_disk["type"].lower() not in ["ssd", "nvme"]:
              all_flash_pool = False
              break
        if not all_flash_pool:
          INFO(f"Node: {node_detail['name']} is not an all-flash storage node")
          break

    # If there are no free nodes in the pool, return False
    if free_nodes is False:
      all_flash_pool = False

    return all_flash_pool

  def image_cluster(self, cluster_name, ahv, nos, nos_url=None,
                    found_vm_ip=None, foundation_build_url=None,
                    hypervisor_url=None):
    """
    A method to image a cluster

    Args:
      cluster_name(str): Name of the cluster to be imaged.
      ahv(str): AHV version to be imaged on cluster.
      nos(str): NOS version to be imaged on cluster.
      nos_url(str): NOS URL to be used for imaging. Optional.
      found_vm_ip(str): Foundation VM IP to be used for imaging. Optional.
      foundation_build_url(str): Foundation Build URL for imaging. Optional.
      hypervisor_url(str): AHV Hypervisor ISO URL

    Returns:
      image_req_id(str): Imaging ID.
    """
    basic_auth = (self.username, self.password)
    INFO("hypervisor_url: "+str(hypervisor_url))
    image_payload = copy.deepcopy(metadata.JARVIS_IMAGE_REQUEST_PAYLOAD)
    image_payload["cluster_name"] = cluster_name
    image_payload["nos_version"] = ("master" if nos == "master"
                                    else metadata.AOS_MAPPING[
                                      (int(nos.split(".")[0]))].format(x=nos))
    image_payload["hyp_version"] = ahv
    image_req_id = None
    if nos_url is not None:
      image_payload["nos_url"] = nos_url
    if found_vm_ip is not None:
      image_payload["foundation_vm_ip"] = found_vm_ip
      image_payload["use_foundation_vm"] = True
    if foundation_build_url is not None:
      image_payload["foundation_build_url"] = foundation_build_url
    if hypervisor_url is not None:
      image_payload["hypervisor_url"] = hypervisor_url
    INFO("Jarvis Payload: %s" % image_payload)
    response = self.post(url=metadata.JARVIS_IMAGE_REQUEST_URL, auth=basic_auth,
                         json=image_payload)
    INFO("Jarvis Response: "+str(response))
    if response.status_code == 200:
      result = response.json()
      if result["success"]:
        image_req_id = result["id"]
      else:
        ERROR("Unable to image the cluster: "+result["message"])
    else:
      ERROR("Unable to image the cluster. "+response.text)

    return image_req_id

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
      base_url=metadata.JARVIS_IMAGE_REQUEST_URL,
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

  def get_gpu_model_from_cluster(self, cluster_name):
    """
    A method to fetch status of cluster imaging

    Args:
      cluster_name(str): Cluster Name to be used fetch GPU Model.

    Returns:
      gpu_model(str): GPU Model Name.
    """
    gpu_model = None
    gpu_set = set()

    url = "{base_url}/{id}".format(
      base_url=metadata.JARVIS_CLUSTER_URL,
      id=cluster_name
    )

    response = self.get(url=url)
    if response.status_code == 200:
      result = response.json()
      if result["success"]:
        for each_dict in result["data"]["nodes"]:
          if ("gpu_model" in each_dict["hardware"].keys() and
              each_dict["hardware"]["gpu_model"] != ""):
            gpu_set.add(each_dict["hardware"]["gpu_model"])
      else:
        ERROR("Unable to fetch status of imaging of the cluster: "
              +result["message"])
    else:
      ERROR("Unable to fetch status of imaging of the cluster: "+response.text)

    gpu_model = "".join(gpu_set)
    return gpu_model

  def get_free_mem(self, cluster_name):
    """
    Get the host free memory.

    Args:
      cluster_name(str): Name of the cluster.

    Returns:
      available_ram(int): Free memory in MB.
    """
    # (with open('/Users/arundhathi/Nutest/nutest/experimental/arundathia/
    #  test.json') as json_file):
    #   data = json.load(json_file)
    #   if "hardware_consumption" in data["data"]:
    #     total_ram = data["data"]["hardware_consumption"]["available_ram"]
    #     no_of_nodes = data["data"]["nodes_cache"]["nodes_count"]
    #     available_ram = total_ram - (16 * no_of_nodes)
    #     return available_ram
    url = "{base_url}/{cluster_id}".format(
      base_url=metadata.JARVIS_CLUSTER_URL,
      cluster_id=cluster_name)
    response = self.get(url=url)

    total_ram, no_of_nodes, available_ram = 0, 0, 0

    if response.status_code == 200:
      result = response.json()
      if result["success"]:
        if "hardware_consumption" in result["data"].keys():
          total_ram = result["data"]["hardware_consumption"]["available_ram"]
          no_of_nodes = result["data"]["nodes_cache"]["nodes_count"]
          available_ram = total_ram - (16 * no_of_nodes)
        else:
          ERROR("Couldn't fetch Hardware Consumption")
      else:
        ERROR("Couldn't fetch Hardware Consumption: " + result["message"])
    else:
      ERROR("Couldn't fetch Hardware Consumption: " + response.text)
    return available_ram
