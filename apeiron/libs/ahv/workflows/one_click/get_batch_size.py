"""
Copyright (c) 2022 Nutanix Inc. All rights reserved.

Author: arundhathi.a@nutanix.com

Get Batch size
"""

from pprint import pprint
import math

from libs.ahv.workflows.one_click.jarvis_client import \
  JarvisClient
from framework.lib.nulog import INFO


def get_batch_size(clusters):
  """
  A Method to get the batch size for execution.

  Args:
    clusters(list): List of cluster names.

  Returns:
    batch_size(int): Size of the batch for execution.
  """
  batch_size = dict()
  for cluster in clusters:
    batch_size[cluster] = compute_num_of_vms(cluster)
  sorted_batch_size = sorted(batch_size.items(), key=lambda x: x[1])
  pprint(sorted_batch_size)
  #return minimum value
  return sorted_batch_size[0][1]

def compute_num_of_vms(cluster, host_load=40):
  """
  Calculate num of vms to create

  Args:
    cluster(str): Name of the cluster to compute number of VMs.
    host_load(int): Max Load on cluster

  Returns:
    num_of_vms(int) : num of vms to be created
  """
  jarvis_client = JarvisClient(
    username="svc.ahv-qa", password="6TcU84qZiZHTvFu!#jDD"
  )
  INFO("Calculate number of vms that can be created in parallel")
  fill_upto_given_per_mem = jarvis_client.get_free_mem(cluster) * \
                            (float(host_load) / 100)
  # assuming we will perform mem add , 8G
  num_parellel_vms = int(math.ceil(fill_upto_given_per_mem / 8))
  return int(num_parellel_vms)
