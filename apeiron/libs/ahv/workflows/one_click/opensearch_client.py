"""
Copyright (c) 2021 Nutanix Inc. All rights reserved.

Author: sohail.amanullah@nutanix.com

Opensearch Client Module.
"""
import json

from framework.lib.nulog import INFO, ERROR
from framework.lib.tools_client.base_rest_client import BaseRestClient
from libs.ahv.workflows.one_click import metadata

class OpensearchClient(BaseRestClient):
  """
  A Opensearch Client Class
  """
  def __init__(self, username=metadata.OPENSEARCH_USERNAME,\
               password=metadata.OPENSEARCH_PASSWORD):
    """
    Constructor method

    Args:
      username(str): Username
      password(str): Password
    """
    super(OpensearchClient, self).__init__(username=username, password=password)
    self.username = username
    self.password = password

  def ingest_data(self, db_name, data):
    """
    A method to Ingest Data to opensearch index.

    Args:
      db_name(str): Index Name where data is to be ingested.
      data(dict): Data to be ingested.
    """
    url = metadata.OPENSEARCH_INGESTION_URL.format(
      db_name=db_name
    )
    INFO(f"Opensearch Data Ingestion URL: {str(url)}")
    INFO(f"Opensearch Data to be ingested: {json.dumps(data)}")
    basic_auth = (self.username, self.password)

    response = self.post(url=url, auth=basic_auth, verify=False, json=data)
    INFO(f"One Click Index Response: {str(response)}")

    if response.status_code == 201:
      result = response.json()
      INFO(f"Data Ingested Successfully. Data ID: {str(result['_id'])}")
      INFO(f"Opensearch API response: {json.dumps(result)}")
    else:
      ERROR(f"Unable to ingest Data. Error: {response.text}")

  def ingest_data_with_id(self, db_name, data, data_id=None, op_type=None):
    """
    A method to injest data to index with id.

    Args:
      db_name(str): Index Name where data is to be ingested.
      data(dict): Data to be ingested.
      data_id(str): Data ID to be ingested.
      op_type(str): Operation Type.

    Returns:
      ingestion_response(str): Ingestion Response.
    """
    ingestion_id = None
    msg = ""
    url = metadata.OPENSEARCH_INGESTION_URL.format(
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
    INFO(f"Opensearch Data Ingestion URL: {str(url)}")
    basic_auth = (self.username, self.password)
    INFO(f"Opensearch Data to be ingested: {json.dumps(data)}")
    response = self.put(url=url, auth=basic_auth, verify=False, json=data)
    INFO(f"One Click Index Response: {str(response)}")

    if response:
      if response.status_code == 201 or response.status_code == 200:
        result = response.json()
        INFO(f"Data Ingested Successfully. Data ID: {str(result['_id'])}")
        INFO(f"Opensearch API response: {json.dumps(result)}")
        ingestion_id = result.get("_id")
      else:
        INFO(f"Unable to ingest Data. Error: {response.text}")
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
    INFO(f"Opensearch ingestion response {ingestion_response}")
    return ingestion_response

  def create_index(self, db_name):
    """
    A method to create new index in opensearch.

    Args:
      db_name(str): Index Name.
    """
    url = metadata.OPENSEARCH_INDEX_CREATION_URL.format(
      db_name=db_name
    )
    INFO(f"Opensearch Index Creation URL: {str(url)}")
    basic_auth = (self.username, self.password)

    response = self.put(url=url, auth=basic_auth, verify=False)
    INFO(f"OpensearchClient Response: {str(response)}")

    if response.status_code == 200:
      result = response.json()
      INFO(f"Index: {db_name} created Successfully.")
      INFO(f"Opensearch API response: {json.dumps(result)}")
    else:
      ERROR("Unable to create index.")

  def query_opensearch(self, index_name, query_dict):
    """
    Query the Opensearch index to fetch results.

    Args:
      index_name(str): Name of Opensearch Index.
      query_dict(dict): JSON format to be queried.

    Returns:
      query_result(list): List of the hits fetched.
    """
    base_url = metadata.OPENSEARCH_BASE_URL
    search_query = "_search/?size=10000"
    index_response = self.post(
      url=f"{base_url}/{str(index_name)}/{search_query}",
      auth=(self.username, self.password),
      verify=False, json=query_dict
    )
    INFO(f"Index response: {index_response}")
    query_result = []
    if index_response.status_code == 200:
      result = index_response.json()
      INFO(f"Index response JSON: {json.dumps(result)}")
      if "hits" in result.keys():
        if "hits" in result["hits"].keys():
          for i in range(len(result["hits"]["hits"])):
            query_result.append(result["hits"]["hits"][i]["_source"])
          INFO(f"Final result: {str(query_result)}")
        else:
          ERROR('"hits" not found in result["hits"].keys()')
      else:
        ERROR('"hits" not found in result.keys()')
    else:
      ERROR(f"Unable to fetch query. Message: {index_response.text}")

    return query_result

  def opensearch_update_query(self, index_name, opensearch_func,\
                              payload, data_id):
    """
    Update a Opensearch doc in index.

    Args:
      index_name(str): Name of Opensearch Index.
      opensearch_func(dict): JSON format to be queried.
      payload(dict): Opensearch Query.
      data_id(str): Opensearch Document ID

    Returns:
      query_result(list): List of the hits fetched.
    """
    url = "{base_url}/{index_name}/{func}/{data_id}".format(
      base_url=metadata.OPENSEARCH_BASE_URL,
      index_name=index_name,
      func=opensearch_func,
      data_id=data_id
    )

    response = self.post(
      url=url,
      auth=(self.username, self.password),
      verify=False, json=payload
    )

    if response.status_code == 200:
      INFO(response)
      result = response.json()
      INFO(json.dumps(result))
      if result.get("_shards"):
        if result["_shards"].get("successful") == 1:
          INFO(f"Opensearch Updated for index: {str(index_name)} with _id: \
               {str(data_id)}")
          return True
        ERROR("Unable to Update index but got shards. msg: ")
        return False
      ERROR("Unable to Update index")
      return False
    ERROR(f"Opensearch client failed. {response.text}")
    return False
