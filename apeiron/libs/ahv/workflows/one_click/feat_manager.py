"""
Copyright (c) 2022 Nutanix Inc. All rights reserved.

Author: vedant.dalal@nutanix.com

Manage the FEAT execution via Apeiron.
"""
import copy
from framework.lib.nulog import INFO

class FeatManager():
  """
  A class to maintain and manage the Feat execution via Apeiron
  """

  def __init__(self):
    """
    Constructor Method
    """

  @staticmethod
  def list_of_suite(product="csi", feat_dict=None):
    """
    A method to get the list of suite from the given feat dictionary

    Args:
      product(str): Product Name,
      feat_dict(dict): Feature Dictionary provided by user.

    Returns:
      suite_dict(dict): Suite Dictionary.
    """
    suite_dict = {}

    if feat_dict:
      for suite in feat_dict.keys():
        for feat in feat_dict[suite].keys():
          suite_feat_dict = feat_dict[suite][feat]
          for jp_index in range(len(suite_feat_dict["job_profile"])):
            INFO(str(suite)+" "+str(feat)+" "+str(jp_index))
            INFO(type(suite_feat_dict["job_profile"]))
            suite_feat_name = (str(product)+"~"+str(suite)+"~"+str(feat)+
                               "~"+str(jp_index+1))
            suite_dict.update({
              suite_feat_name: (
                suite_feat_dict
              )
            })

            suite_dict[suite_feat_name].update({
              "job_profile": suite_feat_dict["job_profile"][jp_index]
            })
    return suite_dict

  @staticmethod
  def get_num_of_workers(suite, suite_dict):
    """
    A method to fetch the number of workers

    Args:
      suite(str): Suite Name.
      suite_dict(dict): Suite Dictionary.

    Returns:
      worker_count(int): Number of workers.
    """

    feat_dict = suite_dict[suite]
    worker_count = 0
    for feat in feat_dict.keys():
      worker_count += len(feat_dict[feat]["job_profile"])

    return worker_count

  @staticmethod
  def fetch_suite_details(feat_dict, pipeline=None):
    """
    A method to fetch the suite details from the feature dictionary.

    Args:
      feat_dict(dict): Feature Dictionary.
      pipeline(str): Pipeline Frequency.

    Returns:
      new_feat_dict(dict): Final Feature Dictionary.
    """
    new_feat_dict = copy.deepcopy(feat_dict)
    if pipeline is not None:#pylint: disable=too-many-nested-blocks
      for suite in feat_dict.keys():
        if suite not in ["UPGRADE"]:
          for feat in feat_dict[suite].keys():
            suite_feat_dict = feat_dict[suite][feat]
            if not suite_feat_dict.get("pipeline"):
              del new_feat_dict[suite][feat]
            else:
              if suite_feat_dict.get("pipeline") != pipeline:
                del new_feat_dict[suite][feat]

    empty_suite_list = []
    for suite in list(new_feat_dict):
      if not bool(new_feat_dict[suite]):
        empty_suite_list.append(suite)

    for suite in empty_suite_list:
      del new_feat_dict[suite]

    return new_feat_dict

  @staticmethod
  def count_total_feats_to_execute(feat_dict, pipeline=None):
    """
    A method to count the total feats to execute from the feature dictionary.

    Args:
      feat_dict(dict): Feature Dictionary.
      pipeline(str): Pipeline Frequency.

    Returns:
      feat_counter(int): Features to execute counter.
    """
    feat_counter = 0

    for suite in feat_dict.keys():
      if suite not in ["UPGRADE"]:
        for feat in feat_dict[suite].keys():
          suite_feat_dict = feat_dict[suite][feat]
          if suite_feat_dict.get("pipeline") == pipeline:
            feat_counter += 1

    return feat_counter

  @staticmethod
  def fetch_set_of_node_size(feat_dict, pipeline=None):
    """
    A method to fetch the set of node sizes from the suite dictionary.

    Args:
      feat_dict(dict): Feature Dictionary.
      pipeline(str): Pipeline Frequency.

    Returns:
      node_set(list): List of Node Set.
    """
    node_set = set()

    for suite in feat_dict.keys():#pylint: disable=too-many-nested-blocks
      if suite not in ["UPGRADE"]:
        for feat in feat_dict[suite].keys():
          suite_feat_dict = feat_dict[suite][feat]
          if suite_feat_dict.get("pipeline") == pipeline:
            if suite_feat_dict.get("nodes"):
              node_set.add(suite_feat_dict.get("nodes"))
            else:
              if suite_feat_dict.get("enable_direct_pool_execution"):
                node_set.add(1)

    return list(node_set)

  @staticmethod
  def fetch_set_of_node_size_from_feat(feat_dict, pipeline=None):
    """
    A method to fetch the set of nodes size from all the feats.

    Args:
      feat_dict(dict): Feature Dictionary.
      pipeline(str): Pipeline Frequency.

    Returns:
      node_set(list): List of Node Set.
    """
    node_set = set()

    for feat in feat_dict.keys():
      suite_feat_dict = feat_dict[feat]
      if suite_feat_dict.get("pipeline") == pipeline:
        if suite_feat_dict.get("nodes"):
          node_set.add(suite_feat_dict.get("nodes"))

    return list(node_set)
