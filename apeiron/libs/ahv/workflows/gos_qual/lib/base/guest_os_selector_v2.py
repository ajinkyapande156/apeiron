"""
Copyright (c) 2022 Nutanix Inc. All rights reserved.

Author: pritam.chatterjee@nutanix.com
"""
# pylint: disable=unused-import, useless-import-alias, fixme
import copy
import os
import shutil

try:
  from framework.lib.nulog import INFO, WARN, DEBUG, ERROR
  EXECUTOR = "nutest"
except Exception:  # pylint: disable=broad-except
  from libs.ahv.framework.proxy_logging \
    import INFO, WARN, DEBUG, ERROR  # pylint: disable=import-error
  EXECUTOR = "mjolnir"
from libs.ahv.workflows.gos_qual.configs.constants \
  import SUPPORTED_VENDORS  # pylint: disable=import-error
from libs.ahv.workflows.gos_qual.configs.constants \
  import LINUX_BOOT_EXCLUDE
from libs.ahv.workflows.gos_qual.lib.base.filters \
  import GuestOSVendorFilter
from libs.ahv.workflows.gos_qual.lib.base.filters \
  import GuestOSVersionFilter
from libs.ahv.workflows.gos_qual.lib.base.filters \
  import GuestOSBootConfigFilter
from libs.ahv.workflows.gos_qual.lib.base.filters \
  import GuestOSEditionFilter
from libs.ahv.workflows.gos_qual.configs \
  import constants as constants


########################################
# Guest OS schema parsers
########################################

# NOTE: Move abstract class to base folder
class AbstractGosParser():
  """Abstract class"""
  def parse(self, guest_os):
    """
    Method to parse the input schema for guest operating systems
    Args:
      guest_os(str):
    Returns:
    Raises:
    """
    raise NotImplementedError

  def generate_boot_vars(self, data):
    """
    Method to generate boot test variations for guest operating systems
    Args:
      data(dict):
    Returns:
    Raises:
    """
    raise NotImplementedError


class BaseGosSchemaParser(AbstractGosParser):
  """BaseGosSchemaParser class"""
  VARS = {
    "legacy": [],
    "uefi": ["secureboot", "credentialguard", "vtpm", "vtpm_secureboot",
             "vtpm_credentialguard"]
  }

  def __init__(self, selector):
    """
    Create gos schema parser instance
    Args:
      selector(object): Gosselector object
    """
    self.selector = selector
    self.guests = dict()

  def generate_boot_vars(self, data):
    """
    Method to generate boot test variations for guest operating systems
    Args:
      data(dict): guest data
    Returns:
      data(dict): data
    """
    # tmp = dict()
    # for guest in data:
    #   if guest[-1] not in self.VARS:
    #     INFO("Skipping %s" % guest[-1])
    #     continue
    #   for var in self.VARS[guest[-1]]:
    #     # NOTE: exclude credential guard for non windows
    #     if "wind" not in guest[0] and "credentialguard" in var:
    #       INFO("Skipping credentialguard booting for non-windows OS")
    #       continue
    #     entry = (guest[0], guest[1], guest[2], guest[3], var)
    #     if entry not in data:
    #       tmp[entry] = copy.deepcopy(data[guest])
    # data.update(tmp)
    # return data
    tmp = list()

    for guest in data:
      if guest["boot"] not in self.VARS:
        INFO("Skipping automatic boot param "
             "generation for %s" % guest["os"])
        # tmp.append(copy.deepcopy(guest))
        continue
      for var in self.VARS[guest["boot"]]:
        # NOTE: exclude credential guard for non windows
        if "wind" not in guest["os"] and var in LINUX_BOOT_EXCLUDE:
          INFO("Skipping %s booting for non-windows OS" % LINUX_BOOT_EXCLUDE)
          continue
        new_guests = copy.deepcopy(guest)
        new_guests["boot"] = var
        tmp.append(copy.deepcopy(new_guests))
    data = data + tmp
    return data


class GosListSchemaParser(BaseGosSchemaParser):
  """GosListSchemaParser class"""
  def parse(self, guest_os):
    """
    Method to parse the input schema for guest operating systems
    Args:
      guest_os(list): list of guest os
    Returns:
      data(dict): guest data
    """
    self.selector.load_guests()
    if isinstance(guest_os, str):
      guest_os = [guest_os]
    data = {guest: self.selector.guests_db[guest] for guest in
            self.selector.guests_db if guest[0] in guest_os}
    return self.generate_boot_vars(data)


class GosDictSchemaParser(BaseGosSchemaParser):
  """GosDictSchemaParser class"""
  def parse(self, guest_os):
    """
    Method to parse the input schema for guest operating systems
    Args:
      guest_os(list): list of guest os
    Returns:
      data(dict): guest data
    """
    guest_data = dict()
    for guest in guest_os:
      for edition in guest_os[guest]:
        for install_method in edition["images"]:
          if install_method in ["uefi", "legacy"]:
            stype = edition.get("type", "server")
            arch = edition.get("arch", "x86")
            bits = edition.get("bits", "64")
            entry = (guest, stype,
                     arch, bits, install_method)
            guest_data[entry] = {
              "os": guest,
              "arch": arch,
              "bits": bits,
              "password": edition.get("password"),
              "username": edition.get("username"),
              "vendor": edition.get("vendor"),
              "type": stype,
            }
            guest_data[entry]["images"] = edition["images"][install_method]
            guest_data[entry]["tests"] = edition.get("tests") or None
    self.selector.set_guest_db(self.generate_boot_vars(guest_data))
    self.selector.populate_tier_info()
    return self.selector.guests_db


########################################
# Guest OS selectors
########################################
class AbstractGosSelector():
  """AbstractGosSelector class"""
  def select(self, **kwargs):
    """
    Method to select the guest OS
    Args:
    Returns:
    Raises:
    """
    raise NotImplementedError

  def load_guests(self):
    """
    Method to load the guest OS
    Args:
    Returns:
    Raises:
    """
    raise NotImplementedError

  def populate_tier_info(self):
    """
    Method to fetch guest OS tier info
    Args:
    Returns:
    Raises:
    """
    raise NotImplementedError

  def filter(self, data, filters):
    """
    Add filter based on guest vendor, os version and boot configs
    Args:
      data(list): data
      filters(dict): can have keys:  vendor, os and boot
    Returns:
       filtered(dict): guests satisfying the required filters
    Raises:
    """
    raise NotImplementedError


class BaseGosSelector(AbstractGosSelector):
  """BaseGosSelector class"""
  FILTERS = {
    "vendor": GuestOSVendorFilter,
    "os": GuestOSVersionFilter,
    "boot": GuestOSBootConfigFilter,
    "type": GuestOSEditionFilter
  }
  def __init__(self):
    """
    Create BaseGos Selection instance
    Args:
    Returns:
    """
    self.guests_db = None
    self.base_url = "http://endor.dyn.nutanix.com/"
    # Note: For local debugging
    # self.base_url = "http://10.48.220.201"
    self.search_url = os.path.join(self.base_url,
                                   "acro_images/mjolnir_gos_images/")
    # self.search_url = os.path.join(self.base_url,
    #                                "mjolnir_image_server/")
    # fixme: pritam.chatterjee to change dir_tree
    self.dir_tree = "acro_images/mjolnir_gos_images/"

  def load_guests(self):
    """
    Method to load the guest OS
    Args:
    Returns:
    """
    shutil.rmtree(self.dir_tree, ignore_errors=True)
    INFO("Loading all available guest operating "
         "systems from image server")
    cmd = 'wget -r -nH -nc -np -l 10 -R "*.*" ' \
          '-R "*.iso" %s > /dev/null 2>&1' % self.search_url
    os.system(cmd)
    tmp = [os.path.join(d, x)
           for d, dirs, _ in os.walk(self.dir_tree)
           for x in dirs]
    count = len(tmp[-1].split("/"))
    tmp = [x for x in tmp if len(x.split("/")) == count]
    self._populate_guest_db(tmp)
    self.populate_tier_info()

  def set_guest_db(self, data):
    """
    Change the guest db if required
    Args:
      data(dict): guest db data
    Returns:
    """
    self.guests_db = data

  def populate_tier_info(self):
    """
    Method to fetch guest OS tier info
    Args:
    Returns:
    """
    for guest in self.guests_db:
      # self.guests_db[guest]["tier"] = \
      # SUPPORTED_VENDORS[self.guests_db[guest]["vendor"]]["tier"]
      guest["tier"] = SUPPORTED_VENDORS[guest["vendor"]]["tier"]
      guest_type = SUPPORTED_VENDORS[guest["vendor"]].get(guest["type"])
      if guest_type:
        if guest_type.get(guest["os"]):
          guest["vcpus"] = guest_type[guest["os"]].get("min_vcpu", 0)
          guest["max_vcpus"] = guest_type[guest["os"]].get("max_vcpu", 0)
        else:
          guest["vcpus"] = guest_type.get("min_vcpu", 0)
          guest["max_vcpus"] = guest_type.get("max_vcpu", 0)


  def filter(self, data, filters):
    """
    Add filter based on guest vendor, os version and boot configs
    Args:
      data(list): data
      filters(dict): can have keys:  vendor, os and boot
    Returns:
       filtered(dict): guests satisfying the required filters
    """
    filtered = dict()
    shortest_filter = None
    for key, val in list(filters.items()):
      filtered[key] = self.FILTERS[key].a_filter(data, val)
      if shortest_filter:
        if len(filtered[key]) < len(filtered[shortest_filter]):
          shortest_filter = key
      else:
        shortest_filter = key

    selected = list()
    # perform interesection of different filters
    for val in filtered[shortest_filter]:
      count = len(list(filtered.keys())) - 1  # exclude the shortest_filter key
      for key in filtered:
        if key == shortest_filter:
          continue
        if val in filtered[key]:
          count -= 1
      if count == 0:
        selected.append(val)
    return selected


  def _populate_guest_db(self, tree):
    """
    Internal method to populate guest_db
    Args:
      tree(dict): guest os database struct
    Returns:
    """
    self.guests_db = list()
    for guest in tree:
      info = guest.split("/")
      guest = os.path.join(self.base_url, guest)
      INFO("info"+ str(info))
      INFO("Guest: "+str(guest))
      tmp = {
        "os": info[3],
        "vendor": info[2],
        "arch": info[4],
        "bits": info[5],
        "type": info[6],
        "boot": info[7],
        "build": None,
        "images": {
          "cdrom": os.path.join(guest, "cdrom.iso"),
          "unattend": os.path.join(guest, "unattend.xml"),
          "disk": os.path.join(guest, "disk.qcow2"),
          "pxe": os.path.join(guest, "pxe.qcow2"),
          "oemdrv": os.path.join(guest, "oemdrv.iso"),
        },
        "username": None,
        "password": None,
      }
      # self.guests_db[(tmp["os"], tmp["type"],
      #                 tmp["arch"], tmp["bits"], tmp["boot"])] = \
      #   copy.deepcopy(tmp)
      self.guests_db.append(copy.deepcopy(tmp))


class DefaultGosSelector(BaseGosSelector):
  """DefaultGosSelector class"""
  def select(self, **kwargs):
    """
    Method to select the guest OS
    Args:
    Returns:
      data(dict): guest os details
    """
    INFO("Performing manual selection of guests")
    guest_os = kwargs.get("guest_os")
    if isinstance(guest_os, str):
      parser = GosListSchemaParser(self)
    elif isinstance(guest_os, list):
      parser = GosListSchemaParser(self)
    elif isinstance(guest_os, dict):
      parser = GosDictSchemaParser(self)
    return parser.parse(guest_os)


class AutoGosSelector(BaseGosSelector, BaseGosSchemaParser):
  """AutoGosSelector class"""
  def select(self, **kwargs):
    """
    Method to select the guest OS
    Args:
    Returns:
      data(dict): guest os details
    """
    INFO("Performing automatic selection of guests")
    self.load_guests()
    data = self.generate_boot_vars(self.guests_db)
    if kwargs.get("filters"):
      return self.filter(data, kwargs.get("filters"))
    return data


class VirtioGosSelector(BaseGosSelector):
  """
  Selects windows guests for virtio driver qualification
  """
  def __init__(self):
    """
    Create VirtioGosSelector object
    Args:
    Returns:
    """
    super(VirtioGosSelector, self).__init__()
    INFO("Limiting search scope to Windows Guest OS only")
    self.search_url = os.path.join(self.search_url, "microsoft/")

  def select(self, **kwargs):
    """
    This will select only legacy and uefi boot variation as of now
    Returns:
      guests_db(dict):
    """
    INFO("Performing automatic selection of windows guests "
         "for virtio qualification, ignoring: %s for virtio qualification"
         % kwargs)
    self.load_guests()
    if kwargs.get("filters"):
      return self.filter(self.guests_db, kwargs.get("filters"))
    return self.guests_db

class UpgradeGosSelector(BaseGosSelector, BaseGosSchemaParser):
  """
  Selects guests for GOS Upgrade qualification
  """
  def select(self, **kwargs):
    """
    This will select only highest supported boot variation as of now
    Returns:
      guests_db(dict):
    """
    INFO("Performing automatic selection of guests "
         "for GOS Upgrade qualification, ignoring: %s for qualification"
         % kwargs)
    self.load_guests()
    to_remove = list()
    data = self.generate_boot_vars(self.guests_db)
    secure_boot = {"boot": "secureboot",
                   "os": "windows8, windows81, "
                         "windowsserver2012, windowsserver2012r2"}
    if kwargs.get("filters"):
      gos_upgrade = self.filter(data, kwargs.get("filters"))
      for gos in gos_upgrade:
        if gos["os"] in constants.FEATURES["VTPM"]["Not_Supported_Guests"]:
          to_remove.append(gos)
      #remove unsupported guests
      for i in to_remove:
        gos_upgrade.remove(i)
      #apply filter secure_boot
      other_guests = self.filter(data, secure_boot)
      if other_guests:
        gos_upgrade.extend(other_guests)
      return gos_upgrade
    return self.guests_db

# unit test
# if __name__ == "__main__":
#   selector = VirtioGosSelectorv2()
#   INFO(selector.select())
