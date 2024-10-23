"""
Copyright (c) 2022 Nutanix Inc. All rights reserved.

Author: pritam.chatterjee@nutanix.com
"""
# pylint: disable=import-error, unused-import, too-many-locals, invalid-name
# pylint: disable=arguments-differ
try:
  from framework.lib.nulog import INFO, ERROR, STEP
  EXECUTOR = "nutest"
except Exception:  # pylint: disable=broad-except
  from libs.ahv.framework.proxy_logging \
    import INFO, ERROR, STEP
  EXECUTOR = "mjolnir"
from libs.ahv.workflows.gos_qual.lib.base.base \
  import BaseTest
from libs.ahv.workflows.gos_qual.lib.base.utilities \
  import get_os_instance


class ColdAddRemoveVnics(BaseTest):
  """ColdAddRemoveVnics class"""
  NAME = "cold_add_remove_vnics"
  TAGS = ["network"]
  POST_OPERATIONS = ["check_device_status"]
  DEFAULT_PARAMS = {
    "num_of_vnics": 1
  }

  def __init__(self):
    """
    Initialize any object level variables here
    Args:
    """
    self._CACHE = dict()

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
    nw = cache.get_entity(entity_type="rest_nw", name="network")
    os = modules.get("rpc")
    rpc_cls = modules.get("rpc_cls_v1")
    rpc_cls_2 = modules.get("rpc_cls_v2")
    self._CACHE["vm_state_0"] = vm.get_nics()

    for vnic in range(1, params.get("num_of_vnics") + 1):
      INFO("Powering off for adding vnic: %s to vm: %s"
           % (vnic, vm.name))
      vm.power_off()
      vm.add_nic(network=nw.create(bind=True, vlan_id=0))
      INFO("Powering on VM: %s after adding vnic: %s"
           % (vm.name, vnic))
      vm.power_on(wait_for_ip=True)
      os.verify_os_boot_post_reboot(vm)
      state = "vm_add_" + str(vnic)
      self._CACHE[state] = vm.get_nics()
      nic_ips = os.get_nics_with_ips()
      INFO("Nic ipaddresses: %s" % nic_ips)
      for nic in [i for i in nic_ips if "virbr" not in i]:
        os_mod = get_os_instance(extra_params["os"])(
          conn_provider=rpc_cls(nic_ips[nic])
        )
        res = os_mod.verify_os_boot_post_reboot(vm)
        INFO("State: %s" % self._CACHE)
        assert res["platform"], "Failed to connect to nic: %s with ip %s" \
                                % (nic, nic_ips[nic])
        INFO("Connection to nic: %s with ip %s was successful!"
             % ((nic, nic_ips[nic])))

    INFO("Cold add vnic was successful!")

    default_nic = self._CACHE["vm_state_0"][0]
    for i, vnic in enumerate(vm.get_nics()):
      if vnic["mac_address"] == default_nic["mac_address"]:
        INFO("Skipping removal of default nic: %s" % vnic)
        continue
      INFO("Powering off for removing vnic: %s to vm: %s"
           % (vnic, vm.name))
      vm.power_off()
      vm.remove_nic(mac_address=vnic["mac_address"])
      INFO("Powering on VM: %s after cold removal of vnic: %s" % (vm.name, i))
      vm.power_on(wait_for_ip=True)
      state = "vm_remove_" + str(vnic)
      self._CACHE[state] = vm.get_nics()
      os_mod = get_os_instance(extra_params["os"])(
        conn_provider=rpc_cls_2(vm)
      )
      os_mod.verify_os_boot_post_reboot(vm)
      INFO("nic removal successful!")
    INFO("Test [%s] successfully executed" % self.NAME)

  def teardown(self, **params):
    """
    Teardown
    Args:
    Returns:
    """
    STEP("Entering teardown in test: %s" % self.NAME)
    extra_params = params.get("extra_params")
    modules = extra_params.get("modules")
    vm_name = extra_params.get("vm_name")
    cache = modules.get("cache")
    vm = cache.get_entity(entity_type="rest_vm", name=vm_name)
    os = modules.get("rpc")
    vm.power_on(wait_for_ip=True)
    os.verify_os_boot_post_reboot(vm)
