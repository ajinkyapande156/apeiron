"""
Copyright (c) 2022 Nutanix Inc. All rights reserved.

Author: pritam.chatterjee@nutanix.com
"""
# pylint: disable=import-error
try:
  from framework.lib.nulog import INFO, ERROR, STEP  # pylint: disable=unused-import
  EXECUTOR = "nutest"
except Exception: # pylint: disable=broad-except
  from libs.ahv.framework.proxy_logging \
    import INFO, ERROR, STEP  # pylint: disable=unused-import
  EXECUTOR = "mjolnir"
from libs.ahv.workflows.gos_qual.lib.base.base \
  import BaseTest


class VmSnapshot(BaseTest):
  """VmSnapshot class"""
  NAME = "vm_snapshot"
  TAGS = ["snapshot"]
  POST_OPERATIONS = []
  DEFAULT_PARAMS = {}

  def run(self, **params):
    """
    Run the test
    Args:
    Returns:
    """
    STEP("Executing Test [%s] " % self.NAME)
    extra_params = params.get("extra_params")
    modules = extra_params.get("modules")
    vm_name = extra_params.get("vm_name")
    cache = modules.get("cache")
    vm = cache.get_entity(entity_type="rest_vm", name=vm_name)
    snapshot_cls = modules.get("rest_snapshot")
    snapshot = snapshot_cls(interface_type="REST", name="snapshot")
    vm_uuid = vm.get()["uuid"]
    snapshot_name = vm.name + "_snapshot"
    INFO("Create snapshot:%s for VM: %s" % (snapshot_name, vm.name))
    vm_snapshot = snapshot.create(bind=False, snapshot_name=snapshot_name, \
      vm_uuid=vm_uuid)
    INFO("Delete created snapshot: %s" % snapshot_name)
    vm_snapshot.remove()
    INFO("Test [%s] successfully executed" % self.NAME)
