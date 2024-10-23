"""
Copyright (c) 2024 Nutanix Inc. All rights reserved.

Author: pritam.chatterjee@nutanix.com
"""
# pylint: disable=unused-argument
from framework.lib.nulog import INFO


class Base:
  """BaseClient"""
  def __init__(self, authenticator, *args, **kwargs):
    """
    Args:
      authenticator(object): The authenticator class
    """
    self.authenticator = authenticator

  def get_api_instance(self, client, host, *args, **kwargs):
    """
    Get the sdk client object
    Args:
      client(object): sdk client class
      host(str): Host ip
    Returns:
      api_instance(object): sdk client object
    """
    configuration = client.Configuration(
      host=f"https://{host}:7030/api"
    )
    configuration = self.authenticator.setup_auth(configuration,
                                                  *args, **kwargs)
    api_client = client.ApiClient(configuration)
    api_instance = client.DefaultApi(api_client)
    return api_instance


class BaseFacade:
  """BaseFacade class"""
  def __init__(self, *args, **kwargs):
    """Initialize Facade class"""
    # udpate the version maps for the child facade
    for vers in self.VERSION_MAP:
      self.VERSION_MAP[vers] = self.VERSION_MAP[vers](*args, **kwargs)
    self.api_version = kwargs.get("api_version", "default")

  def __getattr__(self, name, *args, **kwargs):
    """
    Route calls to visitor from facade
    Args:
      name(str): name of the
    Returns:
      object: visitor class
    """
    INFO("Using api_version {}".format(self.api_version))
    return getattr(self.api_version, name)

  @property
  def api_version(self):
    """
    Property
    Returns:
    """
    return self._api_version

  @api_version.setter
  def api_version(self, api_version):
    """
    Setter
    Args:
      api_version(str):
    """
    if api_version not in self.VERSION_MAP:
      INFO("Invalid API version '{}', "
           "switching to default".format(api_version))
      api_version = self.VERSION_MAP["default"]
    else:
      api_version = self.VERSION_MAP[api_version]
    self._api_version = api_version
