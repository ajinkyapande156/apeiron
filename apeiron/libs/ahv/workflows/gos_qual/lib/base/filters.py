"""
Copyright (c) 2022 Nutanix Inc. All rights reserved.

Author: pritam.chatterjee@nutanix.com
"""
# pylint: disable=unused-import, no-member
import re
from functools import partial


class AbstractFilter(object):
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
    return True if criterion in data["vendor"] else False


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
    return True if criterion in data["os"] else False


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
    return True if re.search(pattern, data["boot"].strip()) else False


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
    return True if re.search(pattern, data["type"].strip()) else False

class GuestTestFilter(BaseFilter):
  """GuestTestFilter class"""

  @classmethod
  def _filter(cls, criterion, data):
    """
    Filter based on test name
    Args:
      criterion(str): value of test name
      data(dict): input data
    Returns:
    """
    return True if criterion in data["name"] else False

