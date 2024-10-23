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


class VmDelete(BaseTest):
  """VmDelete class"""
  NAME = "vm_delete"
  TAGS = ["teardown"]
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
    # vm.create(bind=True,
    #           validate=True,
    #           name=extra_params.get("vm_name")
    #          )
    assert vm.uuid, "Failed to discover VM for deletion"
    assert vm.name == extra_params.get("vm_name"), "Failed to discover " \
                                                   " correct VM for deletion"
    INFO("Deleting VM :%s" % vm.name)
    vm.remove()
    pxe_vm = modules.get("pxe_vm")
    if hasattr(pxe_vm, "uuid") and pxe_vm.uuid:
      INFO("Deleting PXE VM: %s" % pxe_vm.name)
      pxe_vm.remove()
