"""
Copyright (c) 2021 Nutanix Inc. All rights reserved.

Author: pritam.chatterjee@nutanix.com
"""
# pylint: disable=import-error, arguments-differ
try:
  from framework.lib.nulog import INFO, ERROR, WARN, \
    DEBUG  # pylint: disable=unused-import

  EXECUTOR = "nutest"
except Exception:  # pylint: disable=broad-except
  from libs.ahv.framework.proxy_logging \
    import INFO, ERROR, WARN, DEBUG  # pylint: disable=unused-import

  EXECUTOR = "mjolnir"
from libs.ahv.workflows.gos_qual.lib.base.abstracts \
  import AbstractVerifier
from libs.ahv.workflows.gos_qual.lib.base.gos_errors \
  import PostVerificationFailed
from libs.ahv.workflows.gos_qual.lib.base.utilities \
  import get_os_instance  # pylint: disable=unused-import, line-too-long


class VerifyOsBoot(AbstractVerifier):
  """VerifyOsBoot class"""

  def verify(self, **params):
    """
    Verify if the vm has got IP during 1st boot and
    tries to write a test file into the guest OS
    Args
      guest(object): GOS guest object
    Kwargs:
      retries(int): no of retries
      interval(int): sleep between retries
    Returns:
    """
    DEBUG(self)
    extra_params = params.get("extra_params")
    modules = extra_params.get("modules")
    # rpc_cls = modules.get("rpc_cls_v1")
    rpc_cls = modules.get("rpc_cls_v2")
    vm_name = extra_params.get("vm_name")
    cache = modules.get("cache")
    rest_vm = cache.get_entity(entity_type="rest_vm", name=vm_name)
    try:
      assert rest_vm.ip, "VM [%s] did not get any IP after power " \
                         "on for 15 mins" \
                         % vm_name
      extra_params["modules"]["rpc"] = get_os_instance(extra_params["os"])(
        conn_provider=rpc_cls(rest_vm)
      )
      INFO("RPC setup done")
      os = extra_params["modules"]["rpc"]
      WARN("Disabling auto updates to avoid interuptions in testing,"
           "Updates will be explicitely tested later.")
      assert os.disable_auto_upgrades(), \
        "Failed to disable automatic update for VM: %s" % vm_name
    except Exception:  # pylint: disable=broad-except
      PostVerificationFailed("Failed to setup RPC on guest VM")
