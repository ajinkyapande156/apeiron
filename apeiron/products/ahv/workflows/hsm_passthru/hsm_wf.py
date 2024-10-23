"""
Copyright (c) 2024 Nutanix Inc. All rights reserved.

Author: pritam.chatterjee@nutanix.com
"""
# pylint: disable=import-error, unused-import, unused-argument
from framework.lib.nulog import INFO, WARN, ERROR, STEP
from libs.workflows.base_workflow import \
  BaseWorkflow
from libs.workflows.hsm_passthru.wf_helpers import \
  HsmWfHelper



class HsmPassthruWf(BaseWorkflow):
  """HsmPassthruWf class"""

  def __init__(self, *args, **kwargs):
    """Constructor"""
    super(HsmPassthruWf, self).__init__(*args, **kwargs)
    self.wf_helper = HsmWfHelper(cluster=self.cluster)
    self.wf_helper.validate_setup_compatibility()

  def hsm_generic(self, **kwargs):
    """
    Execute HSM device passthru tests
    :param kwargs:
    :return:
    """
    # action = kwargs.get('action', None)  # placeholder
    self.execute_validations(**kwargs)
