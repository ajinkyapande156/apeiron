"""
Copyright (c) 2022 Nutanix Inc. All rights reserved.

Author: pritam.chatterjee@nutanix.com
"""
import copy
import os
import shutil

try:
  from framework.lib.nulog import INFO, WARN, DEBUG, ERROR  # pylint: disable=unused-import
  EXECUTOR = "nutest"
except Exception:  # pylint: disable=broad-except
  from libs.ahv.framework.proxy_logging \
    import INFO, WARN, DEBUG, ERROR  # pylint: disable=import-error
  EXECUTOR = "mjolnir"
from libs.ahv.workflows.gos_qual.configs.constants \
  import SUPPORTED_VENDORS  # pylint: disable=import-error


########################################
# Guest OS schema parsers
########################################

# NOTE: Move abstract class to base folder
class AbstractGosParser(object):
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
    "uefi": ["secureboot", "credentialguard", "vtpm", "vtpm_secureboot"]
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
    tmp = dict()
    for guest in data:
      if guest[-1] not in self.VARS:
        INFO("Skipping %s" % guest[-1])
        continue
      for var in self.VARS[guest[-1]]:
        # NOTE: exclude credential guard for non windows
        if "wind" not in guest[0] and "credentialguard" in var:
          INFO("Skipping credentialguard booting for non-windows OS")
          continue
        entry = (guest[0], guest[1], guest[2], guest[3], var)
        if entry not in data:
          tmp[entry] = copy.deepcopy(data[guest])
    data.update(tmp)
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
class AbstractGosSelector(object):
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


class BaseGosSelector(AbstractGosSelector):
  """BaseGosSelector class"""
  def __init__(self):
    """
    Create BaseGos Selection instance
    Args:
    Returns:
    """
    self.guests_db = None
    self.base_url = "http://endor.dyn.nutanix.com/acro_images/"
    self.search_url = os.path.join(self.base_url, "mjolnir_gos_images/")
    self.dir_tree = "acro_images/mjolnir_gos_images"

  def load_guests(self):
    """
    Method to load the guest OS
    Args:
    Returns:
    """
    shutil.rmtree(self.dir_tree, ignore_errors=True)
    INFO("Loading all available guest operating "
         "systems from image server")
    cmd = 'wget -r -nH -np -l 10 -R "index.html*" ' \
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
      self.guests_db[guest]["tier"] = \
      SUPPORTED_VENDORS[self.guests_db[guest]["vendor"]]["tier"]

  def _populate_guest_db(self, tree):
    """
    Internal method to populate guest_db
    Args:
      tree(dict): guest os database struct
    Returns:
    """
    self.guests_db = {}
    for guest in tree:
      info = guest.split("/")
      guest = os.path.join(self.base_url, guest)
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
          "disk": os.path.join(guest, "disk.qcow2"),
          "pxe": os.path.join(guest, "pxe.iso"),
          "oemdrv": os.path.join(guest, "oemdrv.iso"),
        },
        "username": None,
        "password": None,
      }
      self.guests_db[(tmp["os"], tmp["type"],
                      tmp["arch"], tmp["bits"], tmp["boot"])] = \
        copy.deepcopy(tmp)


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
    return self.generate_boot_vars(self.guests_db)


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
    return self.guests_db


# unittest
# if __name__ == "__main__":
#   selector = AutoGosSelector()
#   guests = selector.select()
