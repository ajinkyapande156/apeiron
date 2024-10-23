"""
Copyright (c) 2024 Nutanix Inc. All rights reserved.

Author: pritam.chatterjee@nutanix.com
"""
# pylint: disable=import-error, unused-import, unused-argument
from framework.lib.nulog import INFO, WARN, ERROR, STEP
from libs.workflows.base_workflow import \
  BaseWorkflow
from libs.workflows.installer.wf_helpers import \
  AhvInstallerHelper



class AhvInstallerWf(BaseWorkflow):
  """AhvInstallerWf class"""

  def __init__(self, *args, **kwargs):
    """Constructor"""
    super(AhvInstallerWf, self).__init__(*args, **kwargs)
    self.wf_helper = AhvInstallerHelper(cluster=self.cluster)
    self.wf_helper.validate_setup_compatibility()

  def ahv_installer_generic(self, **kwargs):
    """
    Execute AHV installer tests
    :param kwargs:
    :return:
    """
    # action = kwargs.get('action', None)  # placeholder
    self.execute_validations(**kwargs)
