"""
Copyright (c) 2023 Nutanix Inc. All rights reserved.

Author: pritam.chatterjee@nutanix.com
"""
import json
from libs.framework import mjolnir_entities as entities


class HostGatewayInterface:
  """HostGatewayInterface class"""

  @staticmethod
  def get_cpu_models(host_ip):
    """
    Get cpu models for a host
    Args:
      host_ip(str):
    Returns:
    Raises:
    """
    cmd = "curl --cert /home/certs/AcropolisService/AcropolisService.crt " \
          "--key /home/certs/AcropolisService/AcropolisService.key --cacert " \
          "/home/certs/ca.pem -sk " \
          "https://%s:7030/api/host/v1/cpumodels" %host_ip
    response = entities.ENTITIES.get("pe").execute(cmd)
    assert response['stdout'], "Failed to get the cpu models from host gateway"
    return json.loads(response['stdout'])
