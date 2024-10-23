"""
Copyright (c) 2022 Nutanix Inc. All rights reserved.

Author: pritam.chatterjee@nutanix.com
"""
# pylint: disable=import-error, arguments-differ
# pylint: disable=wrong-import-order, no-else-return, unnecessary-pass
# import importlib
# REQUESTS_MODULE = "requests"
# requests = importlib.import_module(REQUESTS_MODULE)
import os

import workflows.acropolis.mjolnir.ahv.workflows.gos_qual.configs.constants \
  as const
from framework.lib.nulog import DEBUG, INFO, ERROR  # pylint: disable=unused-import
from framework.lib.tools_client.base_rest_client import BaseRestClient


class ElkRestClient(BaseRestClient):
  """Implements a ELK stack Rest client"""

  # name of service
  name = "ELK"

  def __init__(self, username=None, password=None, logger=None):
    """
    Create instance of ElkRestClient
    Args:
      username(str):
      password(str):
      logger(object):
    """
    username = username or const.ELK_USERNAME
    password = password or const.ELK_PASSWORD
    super(ElkRestClient, self).__init__(username=username,
                                        password=password,
                                        logger=logger)
    self.auth = (self.username, self.password)

  def get_base_urls(self):
    """
    Method that can to be overridden to fetch the service URLs
    Returns:
      list: List of base URLS for the service
    """
    url_from_env = os.environ.get('ELK_WEBSERVICE_URL', None)
    if url_from_env:
      return [url_from_env]
    return self._get_urls_from_config_store()

  def get_fall_back_urls(self):
    """
    Returns a list of urls to fallback
    Returns:
      list: List of Fallback urls
    """
    return [const.ELK_BASE_URL]

  def get_authenticated_methods(self):
    """
    Specifies the http methods that require authentication.
    Returns:
      list(list): list of methods that require authentication.
    """
    return ['POST', 'PUT', 'DELETE', 'GET']

  def get_login_path(self):
    """
    Specifies the login end point
    Returns:
      str: The route to the login API end point
    """
    DEBUG(self)
    return ''

  def login(self, base_url):
    """
    Method that implements the login for the jarvis service.
    Args:
      base_url(str): The specific url where the login request should happen
    Returns:
      bool: True or False based on the success of login
    """
    pass

  def ingest_json_data(self, data, db_name="gos_qualification"):
    """
    Method to ingest json data into elk stack
    Args:
      data(dict):
      db_name(str):
    Returns:
      resp(object)
    Raises:
      RuntimeError
    """
    endpoint = os.path.join(db_name, "_doc/?pretty")
    url = os.path.join(self.get_base_urls()[0],
                       endpoint)
    DEBUG("ELK data ingest url: %s" % url)
    DEBUG(data)
    resp = self.post(url=url, json=data, verify=False)
    if resp.ok:
      INFO("Data ingest successfully")
      return resp
    else:
      ERROR(resp.__dict__)
      raise RuntimeError("Failed to ingest data")

  def _get_urls_from_config_store(self):
    """
    Internal method
    Returns:
       urls(list):
    """
    return [const.ELK_BASE_URL]

  def _check_login_and_send_request(self, method, url, **kwargs):
    """
    Internal method
    Args:
      method(str):
      url(str):
    Returns:
       result(dict):
    """
    base_url = self._get_base_url_from_full_url(url)
    result = self._request(method=method, url=url, **kwargs)
    self._last_used_base_url = base_url
    return result

# Unit Tests
# if __name__ == "__main__":
#   logger = logging.getLogger('elk')
#   handler = logging.FileHandler('stdout2.txt')
#   logger.addHandler(handler)
#   logger.setLevel(logging.DEBUG)
#   esearch = ElkRestClient(username="elastic",
#                           password="SFfdAQFwdu04dNyQdOWM",
#                           logger=logger)
#   # print
#   response = esearch.put('/gos_qualification', verify=False)
  