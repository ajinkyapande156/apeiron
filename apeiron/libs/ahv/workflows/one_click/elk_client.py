"""
Copyright (c) 2021 Nutanix Inc. All rights reserved.

Author: vedant.dalal@nutanix.com

ELK Client Module.
"""
import json

from framework.lib.nulog import INFO
from framework.lib.tools_client.base_rest_client import BaseRestClient
from libs.ahv.workflows.one_click import metadata

class ELKClient(BaseRestClient):
  """
  A ELK Client Class
  """
  def __init__(self, username=None, password=None):
    """
    Constructor method

    Args:
      username(str): Username
      password(str): Password
    """
    super(ELKClient, self).__init__(username=username, password=password)
    self.username = username
    self.password = password

  def ingest_data(self, db_name, data):
    """
    A method to deploy a cluster through RDM

    Args:
      db_name(str): Index Name where data is to be ingested.
      data(dict): Data to be ingested.
    """
    return
    url = metadata.INGESTION_URL.format(
      db_name=db_name
    )
    INFO("ELK Data Ingestion URL: "+str(url))
    INFO("ELK Data to be ingested: "+json.dumps(data))
    basic_auth = (self.username, self.password)

    response = self.post(url=url, auth=basic_auth, verify=False, json=data)
    INFO("One Click Index Response: "+str(response))

    if response.status_code == 201:
      result = response.json()
      INFO("Data Ingested Successfully. Data ID: "+str(result["_id"]))
      INFO("Elastic API response: "+json.dumps(result))
    else:
      INFO("Unable to ingest Data. Error: "+response.text)

  def ingest_data_with_id(self, db_name, data, data_id=None, op_type=None):
    """
    A method to deploy a cluster through RDM

    Args:
      db_name(str): Index Name where data is to be ingested.
      data(dict): Data to be ingested.
      data_id(str): Data ID to be ingested.
      op_type(str): Operation Type.

    Returns:
      ingestion_response(str): Ingestion Response.
    """
    return
    ingestion_id = None
    msg = ""
    url = metadata.INGESTION_URL.format(
      db_name=db_name
    )
    if data_id is not None:
      url += "/"+str(data_id)
    if op_type is not None:
      url += "?op_type=" + str(op_type)

    if "?" in url:
      url += "&pretty"
    else:
      url += "?pretty"
    INFO("ELK Data Ingestion URL: "+str(url))
    # INFO("ELK Data to be ingested: "+json.dumps(data))
    basic_auth = ("elastic", "sa.Z<FPnvRODb_^-")

    response = self.put(url=url, auth=basic_auth, verify=False, json=data)
    INFO("One Click Index Response: "+str(response))

    if response:
      if response.status_code == 201 or response.status_code == 200:
        result = response.json()
        INFO("Data Ingested Successfully. Data ID: "+str(result["_id"]))
        INFO("Elastic API response: "+json.dumps(result))
        ingestion_id = result.get("_id")
      else:
        INFO("Unable to ingest Data. Error: "+response.text)
        if "version_conflict_engine_exception" in response.text:
          msg += ("Unable to ingest as a key with same name exists."
                  "[Duplicate_Key_Error]")
        else:
          msg += response.text
    else:
      msg += "API Response is none"

    ingestion_response = {
      "ingestion_id": ingestion_id,
      "msg": msg
    }

    return ingestion_response

  def create_index(self, db_name):
    """
    A method to deploy a cluster through RDM

    Args:
      db_name(str): Index Name where data is to be ingested.
    """
    return
    url = metadata.INDEX_CREATION_URL.format(
      db_name=db_name
    )
    INFO("ELK Index Creation URL: "+str(url))
    basic_auth = (self.username, self.password)

    response = self.put(url=url, auth=basic_auth, verify=False)
    INFO("ELKClient Response: "+str(response))

    if response.status_code == 200:
      result = response.json()
      INFO("Index created Successfully.")
      INFO("Elastic API response: "+json.dumps(result))
    else:
      INFO("Unable to create index.")

  def query_elk(self, index_name, query_dict):
    """
    Query the Elasticsearch index to fetch results.

    Args:
      index_name(str): Name of Elastic Index.
      query_dict(dict): JSON format to be queried.

    Returns:
      query_result(list): List of the hits fetched.
    """
    return
    index_response = self.post(
      url="https://10.40.121.35:9200/"+str(index_name)+"/_search/?size=10000",
      auth=("elastic", "sa.Z<FPnvRODb_^-"), verify=False, json=query_dict
    )
    INFO(index_response)
    query_result = []
    if index_response.status_code == 200:
      result = index_response.json()
      INFO(json.dumps(result))
      if "hits" in result.keys():
        if "hits" in result["hits"].keys():
          for i in range(len(result["hits"]["hits"])):
            query_result.append(result["hits"]["hits"][i]["_source"])
          INFO("Final result: "+str(query_result))
        else:
          INFO('"hits" not found in result["hits"].keys()')
      else:
        INFO('"hits" not found in result.keys()')
    else:
      INFO("Unable to fetch query. Message: "+index_response.text)

    return query_result

  def elk_update_query(self, index_name, elk_func, payload, data_id):
    """
    Update a Elasticsearch doc in index.

    Args:
      index_name(str): Name of Elastic Index.
      elk_func(dict): JSON format to be queried.
      payload(dict): Elasticsearch Query.
      data_id(str): Elasticsearch Document ID

    Returns:
      query_result(list): List of the hits fetched.
    """
    return
    url = "{base_url}/{index_name}/{func}/{data_id}".format(
      base_url=metadata.ELK_BASE_URL,
      index_name=index_name,
      func=elk_func,
      data_id=data_id
    )

    response = self.post(
      url=url, auth=("elastic", "sa.Z<FPnvRODb_^-"),
      verify=False, json=payload
    )

    if response.status_code == 200:
      INFO(response)
      result = response.json()
      INFO(json.dumps(result))
      if result.get("_shards"):
        if result["_shards"].get("successful") == 1:
          INFO("ELK Updated for index: "+str(index_name)+" with _id: "+
               str(data_id))
          return True
        INFO("Unable to Update index but got shards. msg: ")
        return False
      INFO("Unable to Update index")
      return False
    INFO("ELK client failed. "+response.text)
    return False
