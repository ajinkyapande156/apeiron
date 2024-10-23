"""
Copyright (c) 2024 Nutanix Inc. All rights reserved.

Author: pritam.chatterjee@nutanix.com
"""
import os

# pylint: disable=import-error, unused-import, unused-argument, no-member
from framework.operating_systems.operating_system import OperatingSystem
from libs.gateway.sdk_clients.sdk_clients import (
  GatewaySdkClients)
import workflows.acropolis.mjolnir.gateway.constants as const


class GatewayClientInterface:
  """Host Gateway API Interface class"""

  TYPE_MAP = {
    "gateway_sdk": (GatewaySdkClients,)
  }

  def __new__(cls, cluster, *args, **kwargs):
    """
    Gateway interface factory
    Args:
      cluster(object): Cluster object needed for copying certs
    Returns:
    Raises:
    """
    inf_type = kwargs.pop("type", "gateway_sdk")
    cls.copy_certs_from_cvm(cluster)
    if inf_type not in cls.TYPE_MAP:
      raise RuntimeError("Unable to create Host Gateway Interface object, "
                         "available types: %s" % cls.TYPE_MAP)
    gateway_cls = type('GatewayClient', cls.TYPE_MAP[inf_type], {})
    return gateway_cls(*args, **kwargs)

  @classmethod
  def copy_certs_from_cvm(cls, cluster):
    """
    Copy the certificates CVM ot nutest UBVM
    Args:
      cluster(object):
    Returns:
    Raises:
    """
    if not os.path.exists(const.CERT_LOC):
      os.makedirs(const.CERT_LOC)
    svm_ip = cluster.svms[0].ip
    prefix = "sshpass -p 'RDMCluster.123' "
    cmd = (f"{prefix} scp -o StrictHostKeychecking=no -r "
           f"nutanix@{svm_ip}:/home/certs/* {const.CERT_LOC}")
    result = OperatingSystem().local_execute(cmd)
    assert not result['status'], ("Failed to copy files, please clean-up ssh "
                                  "known keys and try")
    default_cert_dir = os.path.join(const.CERT_LOC, "default")
    if not os.path.exists(default_cert_dir):
      os.makedirs(default_cert_dir)
    cmd = (f'{prefix} scp -o StrictHostKeychecking=no -r '
           f'nutanix@{svm_ip}:/home/nutanix/certs/AHVGWDefaultCerts/*'
           f' {default_cert_dir}')
    result = OperatingSystem().local_execute(cmd)
    assert not result['status'], ("Failed to copy files, please clean-up ssh "
                                  "known keys and try")
