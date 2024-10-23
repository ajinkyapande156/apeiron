"""
Copyright (c) 2023 Nutanix Inc. All rights reserved.

Author: pritam.chatterjee@nutanix.com
"""
# pylint: disable=import-error, fixme, arguments-differ
try:
  from framework.lib.nulog import INFO, ERROR, WARN, DEBUG  # pylint: disable=unused-import
  EXECUTOR = "nutest"
except Exception:  # pylint: disable=broad-except
  from libs.ahv.framework.proxy_logging \
    import INFO, ERROR, WARN, DEBUG  # pylint: disable=unused-import
  EXECUTOR = "mjolnir"
from libs.ahv.workflows.gos_qual.lib.base.abstracts \
  import AbstractVerifier
from libs.feature.dirty_quota.dirty_quota_vm \
  import DirtyQuotaVm
from libs.framework import mjolnir_entities as entities


class ValidateDqForLm(AbstractVerifier):
  """ValidateDqForLm class"""

  def verify(self, **params):
    """
    Verify OS boot type
    Args:
    Returns:
    """
    DEBUG(self)
    extra_params = params.get("extra_params")
    vm_name = extra_params.get("vm_name")
    source_host = extra_params.get("source_host")
    INFO("Initializing DQ lib for this validation")
    if entities.ENTITIES.get("pc"):
      dq_vm = DirtyQuotaVm()
      payload = {
        "vm_name": vm_name,
        "discover": True,
        "configure_tools": False
      }
      dq_vm.create(**payload)
      assert dq_vm.vm_uuid, "Failed to get VM uuid for %s" % vm_name
      dq_vm.validate_dirty_quota_migration(**{"source_host": source_host})
    else:
      WARN("This cluster is not registered with any PC, "
           "hence skipping validation")
