"""
Copyright (c) 2022 Nutanix Inc. All rights reserved.

Author: pritam.chatterjee@nutanix.com
"""
# pylint: disable=import-error, fixme
# pylint: disable=unused-variable
# pylint: disable=too-many-statements, line-too-long
# pylint: disable=too-many-locals, unused-import, bad-indentation
import inspect
import random
import uuid
from functools import partial
# from framework.entities.cluster.nos_cluster import NOSCluster
from framework.lib.test.nos_test import NOSTest
from framework.lib.nulog import INFO, WARN, DEBUG, ERROR, STEP
# entities
from framework.entities.vm.vm import Vm
from framework.entities.network.network import Network
from framework.entities.snapshot.snapshot import Snapshot
from framework.entities.container.container import Container
from framework.exceptions.nutest_error import NuTestError
from framework.interfaces.acli import ACLI
from framework.interfaces.ecli import ECLI
from workflows.acropolis.ahv.acro_image_utility import AcroImageUtil
from workflows.acropolis.ahv.acro_gos_utility import AcroGOSUtilv2
from workflows.acropolis.ahv.acro_gos_utility import AcroGOSUtil
from workflows.ahv.ha_test_lib import HaTestLib
from workflows.manageability.api.aplos import images_api as ImagesAPI
from workflows.manageability.api.aplos import vms_api as VmsAPI
from workflows.manageability.api.aplos import subnets_api as SubnetsAPI
from workflows.manageability.api.aplos.aplos_client import AplosClient
from libs.ahv.workflows.gos_qual.configs \
  import constants
# move away from this dir
from libs.framework import mjolnir_entities as entities
from workflows.acropolis.upgrade.perform_ahv_aos_upgrade import \
  PerformAhvAosUpgrade


def proxyfunc(*args, **kwargs):
  """Delayed instantiation

    Returns:
      Object of BaseRoutables class
  """
  return MjolnirProxy(*args, **kwargs)


class MjolnirProxy():
  """Proxy class for routable creation"""

  def __new__(cls, entity_type, entity_class, name=None,
              routable_type=None, **kwargs):
    """
      Creates an object of BaseRoutables

      Args:
        entity_type(str): entity type
        entity_class(str): class name of entity
        name(str): Name of entity
        routable_type(dict): Nutest or Mjolnir
        **kwargs

      Returns:
        obj of BaseRoutables class
    """
    # check if there is any conversion map corresponding to given entity
    if not name:
        name = entity_type + "_" + str(uuid.uuid1())
    if not routable_type:
      routable_type = constants.NUTEST_CONV_MAP
    conversion_map = routable_type
    if entity_type in conversion_map:
      _map = conversion_map[entity_type]
    else:
      _map = {}
    obj = BaseRoutables(_map, entity_class(**kwargs), entity_type, name)
    return obj


class BaseRoutables():
  """Base Routable class for supporting entities from different frameworks"""

  def __init__(self, _map, _obj, entity_type, name):
    """
     Constructor method

     Args:
       _map(dict): Nestest/Mjolnir Map
       _obj(object): object
       entity_type(str): entity type (vm, host, nw)
       name(str): entitiy name

      Returns:
        None
    """
    self._map = _map
    self._obj = _obj
    self.entity_type = entity_type
    self.name = name
    if not entity_type in constants.VM_CACHE:
      constants.VM_CACHE[entity_type] = {}
    if not self.get_entity(entity_type=entity_type, name=name):
      constants.VM_CACHE[entity_type][name] = self
      print(("Setting:", constants.VM_CACHE))
    else:
      print(("Before:", id(self)))
      self = self.get_entity(entity_type=entity_type, name=name) #pylint: disable=self-cls-assignment
      print(("After", id(self)))

  def __getattr__(self, action):
    """
      Gets actual action name from map

      Args:
        action(str): Method/Action name invoked

      Returns:
        Method name if action found in map else action
    """
    action = self.__getconv__(action)
    if action in constants.REMOVE_ACTIONS:
      #if action fails, entity will still be removed from cache
      self.delete_entity()
    return getattr(self._obj, action)

  def __getconv__(self, action):
    """
      Get method name if action found in map

      Args:
        action(str): method name

      Returns:
        Method name if action found in map else action
    """
    if action in self._map:
      return self._map[action]
    return action

  @classmethod
  def get_entity(cls, entity_type, name):
    """
      Get entity from cache

      Args:
        entity_type(str): entity type
        name(str): name of entity

      Returns:
        Returns entity if exists else None
    """
    if entity_type in constants.VM_CACHE:
      if name in constants.VM_CACHE[entity_type]: #pylint: disable=no-else-return
        return constants.VM_CACHE[entity_type][name]
      else:
        return None
    else:
      return None

  def delete_entity(self):
    """
      Get entity from cache

      Args:
      Returns:
    """
    if self.entity_type in constants.VM_CACHE:
      if self.name in constants.VM_CACHE[self.entity_type]:
        del constants.VM_CACHE[self.entity_type][self.name]
      else:
        INFO("%s not found under %s" % (self.name, self.entity_type))
    else:
      INFO("Entity type does not exist")


class AbstractEntityProvider():
  """AbstractEntityProvider class"""

  def build_entities(self):
    """
    Create entity map
    Raises:
    """
    raise NotImplementedError

  def get_entities(self):
    """
    Get entity map
    Raises:
    """
    raise NotImplementedError

  def get_common_params(self):
    """
    Get common params map
    Raises:
    """
    raise NotImplementedError


class BaseEntityProvider(AbstractEntityProvider):
  """BaseEntityProvider class"""

  def __init__(self, cluster, nos_test_obj=None):
    """
    Create base entity provider object
    Args:
      cluster(object): Ip address of setup
      nos_test_obj(obj): Nos test obj
    Returns:
    """
    # self.cluster_ip = cluster_ip
    self.cluster = cluster
    self.nos_test_obj = nos_test_obj
    self.build_entities()
    self.entity_map = {}

  def build_entities(self):
    """
    Create entity map
    Raises:
    """

  def get_entities(self):
    """
    Get entity map
    Raises:
    """

  def get_common_params(self):
    """
    Get common params map
    Raises:
    """


class NutestEntityProvider(BaseEntityProvider):
  """NutestEntityProvider class"""

  def __init__(self, cluster, nos_test_obj=None):
    """
    Create base entity provider object
    Args:
      cluster(object): Ip address of setup
      nos_test_obj(obj): Nos test obj
    Returns:
    """
    super(NutestEntityProvider, self).__init__(cluster,
                                               nos_test_obj=nos_test_obj)

  def build_entities(self):
    """
    Create entity map
    Raises:
    """
    DEBUG("Adding acli and restv2 entities from Nutest")
    if not self.cluster:
      WARN("No cluster is available")
      self.entity_map = {
        "rest_vm": partial(proxyfunc, "rest_vm", Vm),
        "acli_vm": partial(proxyfunc, "acli", ACLI),
        "ecli": partial(proxyfunc, "ecli", ECLI),
        "rpc_vm": AcroGOSUtilv2,
        "rpc": AcroGOSUtil,
        "rest_image": partial(proxyfunc, "rest_image", AcroImageUtil),
        # "rest_ctr": Container.list(self.cluster)[0],
        "rest_nw": partial(proxyfunc, "rest_nw", Network),
        "rest_snapshot": partial(proxyfunc, "rest_snapshot",
                                 Snapshot),
        # "pe": self.cluster,
        "rest_ha": partial(proxyfunc, "rest_ha", HaTestLib)
      }
    else:
      self.entity_map = {
        "rest_vm": partial(proxyfunc, "rest_vm", Vm, cluster=self.cluster),
        "acli_vm": partial(proxyfunc, "acli", ACLI, cluster=self.cluster),
        "ecli": partial(proxyfunc, "ecli", ECLI, cluster=self.cluster),
        "rpc_vm": AcroGOSUtilv2,
        "rpc": AcroGOSUtil,
        "rest_image": partial(proxyfunc, "rest_image", AcroImageUtil,
                              cluster=self.cluster),
        "rest_ctr": Container.list(self.cluster)[0],
        "rest_nw": partial(proxyfunc, "rest_nw", Network, cluster=self.cluster),
        "rest_snapshot": partial(proxyfunc, "rest_snapshot",
                                 Snapshot, cluster=self.cluster),
        "pe": self.cluster,
        "rest_ha": partial(proxyfunc, "rest_ha", HaTestLib, cluster=self.cluster)
      }
      if self.nos_test_obj:
        INFO("NOS Test object information will be added as execution is done"
             "via Nutest")
        self.nos_test_obj.upgrade_handler = partial(proxyfunc, "upgrade_handler",
                                                    PerformAhvAosUpgrade,
                                                    cluster=self.cluster)
        self.entity_map["upgrade_handler"] = self.nos_test_obj.upgrade_handler
        # self.entity_map["nos_obj"] = self.nos_test_obj
        # self.nos_test_obj.upgrade_handler = partial(proxyfunc,
        #                                             "upgrade_handler",
        #                                             PerformAhvAosUpgrade,
        #                                             cluster=self.cluster)
        # self.entity_map["upgrade_handler"] = self.nos_test_obj.upgrade_handler
      else:
        WARN("EXECUTION IS NOT DONE THROUGH NUTEST LAUCHER, UPGRADES IS NOT "
             "AVAILABLE IN THIS MODE")

      multi_cluster = self.cluster.get_multicluster_state()
      if multi_cluster:
        DEBUG("Adding restv3 and restv4 entities from Nutest")
        response = random.choice(multi_cluster)
        pc_ip = random.choice(response["clusterDetails"]["ipAddresses"])
        self.entity_map["pc"] = AplosClient(pc_ip)
        self.entity_map["restv3_vm"] = VmsAPI
        self.entity_map["restv3_image"] = ImagesAPI
        self.entity_map["restv3_nw"] = SubnetsAPI
      entities.ENTITIES = self.entity_map

  def get_entities(self):
    """
    Get entity map
    Returns:
    """
    return {"entities": {"entities": self.entity_map}}

  def get_common_params(self):
    """
    Get common params
    Returns:
    """
    return {"cluster": self.cluster}


class MjolnirDataDrivenTest():
  """MjolnirDDT class"""

  def __init__(self, cluster, config_data, nos_test_obj=None):
    """
    Instantiate Mjolnir executor class
    Args:
      cluster(object): cluster object
      config_data(list): List of config steps
      nos_test_obj(obj): Nos test obj
    Returns:
    """
    self.cluster = cluster
    # super(MjolnirDataDrivenTest, self).__init__(*args, **kwargs)
    self.pre_path = "workflows.acropolis.mjolnir.workflows."
    self.data = config_data
    self.common_params = {}
    self.entity_provider = self.data.get("entity_provider",
                                         NutestEntityProvider)(self.cluster,
                                                               nos_test_obj=\
                                                               nos_test_obj)
    self.entity_cache = BaseRoutables
    INFO("Loading cluster object")
    self.common_params = self.entity_provider.get_common_params()
    INFO("Loading entities")
    self.common_params.update(self.entity_provider.get_entities())
    INFO("Loading entity cache")
    self.common_params.update({"entity_cache": self.entity_cache})
    INFO("Test config: %s" % self.data)
    # self.step_retries = self.data.get("step_retries", 1)
    # self.setp_retry_interval = self.data.get("step_retry_interval", 3)
    self.cached_wf = {}

  def execute(self):
    """
    Execute the steps from config file
    Args:
    Returns:
    """
    steps = self.data.get("steps", [])
    for step in steps:
      step["name"] = self.pre_path + step["name"]
      func = self._get_func_to_exec(step)
      if step.get("func_kwargs"):
        func(**step.get("func_kwargs"))

  def _get_func_to_exec(self, step):
    """
    Get the import object from the step.
    Args:
      step (dict): Step details.
    Returns:
      import object
    """
    # Assuming path_list[-1] is a class name
    complete_path = str(step['name'])
    path_list = complete_path.split(".")
    import_path = ".".join(path_list[:-1])
    step['import_name'] = path_list[-1]
    # Additional test specific kwargs that maybe required by some classes
    try:
      import_file = __import__(import_path, fromlist=[path_list[-1]])
      step['import_name'] = path_list[-1]
    except ImportError:
      # Import error implies path_list[-1] is a function name, so we retry an
      # import with a shorter path
      import_path = ".".join(path_list[:-2])
      step['import_name'] = path_list[-2]
      step['func_name'] = path_list[-1]
      import_file = __import__(import_path, fromlist=[step['import_name']])
    get_import = getattr(import_file, step['import_name'])

  # if the name specified is a class
    if inspect.isclass(get_import):
      step.setdefault('class_args', [])
      step.setdefault('class_kwargs', {})
      # create the class object
      if step.get('func_name') and \
        "staticmethod" in str(get_import.__dict__[step['func_name']]) or \
        "classmethod" in str(get_import.__dict__[step['func_name']]):
        # if the function is a static function of a class
        func_call = getattr(step['class_obj'], step['func_name'])
      else:
        if step["import_name"] in self.cached_wf:
          # NOTE: Enabling workflow cache across steps
          func_call = getattr(self.cached_wf[step["import_name"]],
                              step.get('func_name', 'start'))
          return func_call
        class_init_mtd = getattr(get_import, '__init__')
        # argspec = inspect.getargspec(class_init_mtd)
        argspec = inspect.getfullargspec(class_init_mtd)
        args = argspec[0]
        # if the class constructor expects the common_param_name argument,
        # we pass
        # the common_param obj at the appropriate position. Else, if it
        # accepts keywords, we pass the common_param as a kwarg
        for comm_name, comm_value in self.common_params.items():
          if comm_name in args:
            if 'self' in args:
              args.remove('self')
            position = args.index(comm_name)
            step['class_args'].insert(position, comm_value)
          elif argspec[2] is not None:
            # if the init function is accepting kwargs
            # Ex: ArgSpec(args=['num', 'cluster'], varargs=None,
            # keywords=kwargs,
            #             defaults=None)
            if not step['class_kwargs'].get(comm_name):
              # If param is present in class_kwargs, that takes precedence over
              # the common param.
              step['class_kwargs'][comm_name] = comm_value
        step['class_obj'] = \
          get_import(*step['class_args'], **step['class_kwargs'])
        self.cached_wf[step['import_name']] = step['class_obj']
        func_call = getattr(step['class_obj'],
                            step.get('func_name', 'start'))
    else:
      # if the name is a static function
      func_call = get_import
    return func_call
