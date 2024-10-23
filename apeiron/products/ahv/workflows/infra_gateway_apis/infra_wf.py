"""
Copyright (c) 2024 Nutanix Inc. All rights reserved.

Author: pritam.chatterjee@nutanix.com
"""
# pylint: disable=import-error, unused-import, unused-argument
from framework.lib.nulog import INFO, WARN, ERROR, STEP
from libs.workflows.base_workflow import \
  BaseWorkflow
from libs.workflows.infra_gateway_apis.wf_helpers \
  import InfraGatewayWfHelper



class InfraGatewayWf(BaseWorkflow):
  """InfraGatewayWf class"""

  def __init__(self, *args, **kwargs):
    """Constructor"""
    super(InfraGatewayWf, self).__init__(*args, **kwargs)
    self.wf_helper = InfraGatewayWfHelper(cluster=self.cluster)
    self.wf_helper.validate_setup_compatibility()

  def infra_gw_generic(self, **kwargs):
    """
    Execute Infra GW Api tests
    Args:
    Returns:
    Raises:
    """
    # action = kwargs.get('action', None)  # placeholder
    self.execute_validations(**kwargs)
