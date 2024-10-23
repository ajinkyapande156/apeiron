"""
Copyright (c) 2022 Nutanix Inc. All rights reserved.

Author: pritam.chatterjee@nutanix.com
"""
# pylint: disable=dangerous-default-value, wrong-import-position
# pylint: disable=no-name-in-module
import copy
import os
import re
import shutil
import importlib
from distutils import version as StrictVersion
from functools import partial
from bs4 import BeautifulSoup

MOD = "requests"
REQUESTS = importlib.import_module(MOD)  # pylint: disable=import-error

from framework.lib.nulog import INFO
from libs.framework.configs.constants \
  import SUPPORTED_VENDORS  # pylint: disable=import-error
from libs.framework import mjolnir_entities as entities


class VmImageDiscovery():
  """VmImageDiscovery class"""
  def __init__(self, **kwargs):
    """
    Create BaseGos Selection instance
    Args:
    Returns:
    """
    self.guests_db = None
    self.base_url = kwargs.get("base_url",
                               "http://endor.dyn.nutanix.com/")
    # Note: For local debugging
    # self.base_url = "http://10.48.212.32/"
    self.search_url = os.path.join(self.base_url,
                                   "acro_images/mjolnir_gos_images/")
    # self.search_url = os.path.join(self.base_url,
    #                                "mjolnir_image_server/")
    # fixme: pritam.chatterjee to change dir_tree #pylint: disable=fixme
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
    entities.VM_IMAGES = self.guests_db

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
      guest["tier"] = SUPPORTED_VENDORS[guest["vendor"]]["tier"]
      guest_type = SUPPORTED_VENDORS[guest["vendor"]].get(guest["type"])
      if guest_type:
        if guest_type.get(guest["os"]):
          guest["vcpus"] = guest_type[guest["os"]].get("min_vcpu")
          guest["max_vcpus"] = guest_type[guest["os"]].get("max_vcpu")
        else:
          guest["vcpus"] = guest_type.get("min_vcpu")
          guest["max_vcpus"] = guest_type.get("max_vcpu")

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
      self.guests_db.append(copy.deepcopy(tmp))


class AbstractFilter():
  """AbstractFilter class"""
  @classmethod
  def a_filter(cls, data, criteria):
    """
    Filtering the guest os based on given conditions
    Args:
      data(list):
      criteria(str):
    Returns:
    Raises:
    """
    raise NotImplementedError

  @classmethod
  def _filter(cls, criterion, data):
    """
    Filter based on some condition
    Args:
      criterion(str): value of boot type
      data(dict): input data
    Returns:
    Raises:
    """
    raise NotImplementedError


class BaseFilter(AbstractFilter):
  """BaseFilter class"""

  @classmethod
  def a_filter(cls, data, criteria):
    """
    Filtering the guest os based on given conditions
    Args:
      data(list):
      criteria(str):
    Returns:
    """
    filtered = []
    for criterion in criteria.split(","):
      predicate = cls._filter
      criterion = criterion.strip()
      predicate = partial(predicate, criterion)
      filtered += list(filter(predicate, data))
    # perform the union of all the filtered dict values
    return filtered
    # return [dict(t) for t in {tuple(d.items()) for d in filtered}]


class GuestOSVendorFilter(BaseFilter):
  """GuestOSVendorFilter class"""

  @classmethod
  def _filter(cls, criterion, data):
    """
    Filter based on os vendor
    Args:
      criterion(str): value of boot type
      data(dict): input data
    Returns:
    """
    return True if criterion in data["vendor"] else False #pylint: disable=simplifiable-if-expression


class GuestOSVersionFilter(BaseFilter):
  """GuestOSVersionFilter class"""

  @classmethod
  def _filter(cls, criterion, data):
    """
    Filter based on os version
    Args:
      criterion(str): value of boot type
      data(dict): input data
    Returns:
    """
    pattern = '^' + criterion + "$"
    pattern = re.compile(pattern)
    return True if re.search(pattern, data["os"]) else False #pylint: disable=simplifiable-if-expression


class GuestOSBootConfigFilter(BaseFilter):
  """GuestOSBootConfigFilter class"""

  @classmethod
  def _filter(cls, criterion, data):
    """
    Filter based on boot type
    Args:
      criterion(str): value of boot type
      data(dict): input data
    Returns:
    """
    pattern = "^" + criterion + "$"
    pattern = re.compile(pattern)
    return True if re.search(pattern, data["boot"].strip()) else False #pylint: disable=simplifiable-if-expression


class GuestOSEditionFilter(BaseFilter):
  """GuestOSEditionFilter class"""

  @classmethod
  def _filter(cls, criterion, data):
    """
    Filter based on edition type
    Args:
      criterion(str): value of edition type
      data(dict): input data
    Returns:
    """
    pattern = "^" + criterion + "$"
    pattern = re.compile(pattern)
    return True if re.search(pattern, data["type"].strip()) else False #pylint: disable=simplifiable-if-expression


class VmImage():
  """MjolnirVmImage class"""
  FILTERS = {
    "vendor": GuestOSVendorFilter,
    "os": GuestOSVersionFilter,
    "boot": GuestOSBootConfigFilter,
    "type": GuestOSEditionFilter
  }

  def get_vm_image(self, filters={}):
    """
    Get the os image name
    Args:
      filters(dict):
    Returns:
    """
    if not entities.VM_IMAGES:
      img_srv_client = VmImageDiscovery()
      img_srv_client.load_guests()
    return self.filter(filters)

  def filter(self, filters):
    """
    Add filter based on guest vendor, os version and boot configs
    Args:
      filters(dict): can have keys:  vendor, os and boot
    Returns:
       filtered(dict): guests satisfying the required filters
    """
    data = copy.deepcopy(entities.VM_IMAGES)
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


class VirtioImage():
  """Virtio image class"""
  @staticmethod
  def get_virtio_driver(position=None, version=None): #pylint: disable=bad-option-value,inconsistent-return-statements
    """
    Add the discovery logic here
    Args:
      position(int): n less than latest version
      version(str): virtio version
    Returns:
      each_iso(str): virtio url
    """
    url = 'http://endor.dyn.nutanix.com/acro_images/automation/' \
          'ahv_guest_os/VirtIO'
    ext = 'iso'
    page = REQUESTS.get(url).text
    soup = BeautifulSoup(page, 'html.parser')
    iso_paths = [url + '/' + node.get('href') for node in soup.find_all('a') if
                 node.get('href').endswith(ext)]
    versions = []
    # Find latest version if no version is provided
    if not version:
      for each_iso in iso_paths:
        res = re.search(r"Nutanix-VirtIO-\d\.\d\.\d\.iso", each_iso)
        if res:
          filename = res.group()
          search_version = re.search(r"\d\.\d\.\d", filename)
          versions.append(search_version.group())
      versions.sort(key=StrictVersion.StrictVersion)
      INFO(versions)
      # fixme , remove 2.0.0 #pylint: disable=fixme
      if position:
        version = versions[-2 + position]
      else:
        version = versions[-2]
    # search
    for each_iso in iso_paths:
      res = re.search(r"Nutanix-VirtIO-\d\.\d\.\d\.iso", each_iso)
      if res:
        filename = res.group()
        search_version = re.search(r"\d\.\d\.\d", filename)
        if search_version.group() == version:
          return each_iso
