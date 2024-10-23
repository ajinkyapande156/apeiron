"""
Copyright (c) 2024 Nutanix Inc. All rights reserved.

Author: pritam.chatterjee@nutanix.com
"""
# pylint: disable=import-error, unused-import, unused-argument, no-member
# pylint: disable=no-self-use, no-else-return, ungrouped-imports,
# pylint: disable=duplicate-string-formatting-argument, wrong-import-order
# pylint: disable=unused-variable, global-statement, protected-access

from framework.lib.nulog import INFO, STEP, WARN, ERROR
from libs.framework import mjolnir_entities as entities
from libs.feature.gateway.gateway import \
  HostGatewayInterface
from libs.feature.dirty_quota.dirty_quota_cluster \
  import DirtyQuotaCluster
from framework.exceptions.interface_error import NuTestCommandExecutionError
from libs.workflows.generic.vm.vm_factory import (
  VmFactory)
from libs.ahv.workflows.gos_qual.configs \
  import constants
from libs.framework.mjolnir_executor import use_executor
from libs.feature.error_injection.host_error_injection \
  import ErrorHost


VM_LIST = []


class BaseHelper:
  """Base class for HSM passthru helpers."""
  def __init__(self, cluster=None):
    """
    Create object
    Args:
       cluster(object):
    Returns:
    """
    self.cluster = cluster


class HostHelper(BaseHelper):
  """HostHelper class for HSM helpers"""
  def validate_service_restart(self, **kwargs):
    """
    Validate service restarts on Host
    Args:
    Returns:
    Raises:
    """
    vm_name = kwargs.pop("vm_name", '')
    if vm_name not in [vm.name for vm in self.vm_list]:
      vm_name = []
    else:
      vm_name = [name.strip() for name in vm_name.split(",")]
    if not vm_name:
      vm_name = [vm.name for vm in self.vm_list]

    err_host = ErrorHost()

    for host in self.hsm_details:
      for i, card in enumerate(self.hsm_details[host]):
        vm = card['vm']
        if vm.name in vm_name:
          err_host.restart_service(card["host"], **kwargs)

  def validate_qemu_kill(self, **kwargs):
    """
    Validate qemu process kill
    Args:
    Returns:
    Raises:
    """
    vm_name = kwargs.pop("vm_name", None)
    err_host = ErrorHost()
    if not vm_name:
      # select only 1st vm created with HSM card passthru
      for host in self.hsm_details:
        for i, card in enumerate(self.hsm_details[host]):
          vm_name = card['vm']
          break

    for host in self.hsm_details:
      for i, card in enumerate(self.hsm_details[host]):
        vm = card['vm']
        if vm.name in vm_name:
          INFO("Killing qemu process for {} on host {}".format(vm.name,
                                                               host))
          err_host.qemu_process_kill(vm.uuid, card["host"], **kwargs)
          break

  def validate_host_reboot(self, **kwargs):
    """
    Validate host reboot with HSM card
    Args:
    Returns:
    Raises:
    """
    vm_name = kwargs.pop("vm_name", None)
    err_host = ErrorHost()
    if not vm_name:
      # select only 1st vm created with HSM card passthru
      for host in self.hsm_details:
        for i, card in enumerate(self.hsm_details[host]):
          vm_name = card['vm']
          break

    for host in self.hsm_details:
      for i, card in enumerate(self.hsm_details[host]):
        vm = card['vm']
        if vm.name in vm_name:
          INFO("Rebooting host {}".format(host))
          err_host.host_reboot(card["host"], **kwargs)
          break

  def validate_host_services(self, **kwargs):
    """
    Validate if adm and avm services are up and running
    Args:
    Returns:
    Raises:
    """
    hosts = self.cluster.hypervisors
    for host in hosts:
      STEP(" Checking ADM and AVM service status on hosts {}".format(host.ip))
      adm_details = self._get_service_details(host, service='adm.service')
      assert adm_details['adm.service'] == 'AHV Device Manager', \
        ("Failed to validate correct service name, "
         "expected:{} got {}").format('AHV Device Manager',
                                      adm_details['adm.service'])
      assert adm_details['Active'] == 'active', (
        ("Failed to validate correct service state, "
         "expected:{} got {}").format('active',
                                      adm_details['Active']))
      INFO("ADM service status is validated successfully")
      avm_details = self._get_service_details(host, service='avm.service')
      assert avm_details['avm.service'] == 'AHV VM Manager', \
        ("Failed to validate correct service name, "
         "expected:{} got {}").format('AHV VM Manager',
                                      adm_details['avm.service'])
      assert avm_details['Active'] == 'active', (
        ("Failed to validate correct service state, "
         "expected:{} got {}").format('active',
                                      adm_details['Active']))
      INFO("AVM service status is validated successfully")
    INFO("Service validation completed successfully.")

  def validate_host_pci_devices(self, **kwargs):
    """
    Validate if host is reporting proper PCI slots
    Args:
    Returns:
    Raises:
    """
    hosts = self.cluster.hypervisors
    for host in hosts:
      gateway = HostGatewayInterface(cluster=self.cluster, host=host.ip)
      STEP("Validating PCI devices on Host {}".format(host.ip))
      pci_devices = gateway.get_pci_devices()
      INFO("Validating schema for {}".format(pci_devices))
      actual = pci_devices['Members@odata.count']
      expected = self._has_hsm_cards(host)
      assert actual == expected, ("Failed to validate HSM cards for host {}, "
                                  "expected {}"
                                  " --> got {}").format(host.ip,
                                                        expected, actual)

      INFO("Validation successful for host {}, "
           "expected {}"
           " --> got {}".format(host.ip, expected, actual))

      for pci_device in pci_devices['Members']:
        STEP("Validating PCI device {} on Host {}".format(pci_device,
                                                          host.ip))
        result = gateway.get_pci_device_by_uuid(
          pci_device['@odata.id'].split('/')[-1])
        INFO("Validating schema for {}".format(result))
        self._validate_pci_device_schema(result, **kwargs)
        STEP("Validating PCI device {} functions on "
             "Host {}".format(pci_device, host.ip))

        result = gateway.get_pci_device_functions(
          pci_device['@odata.id'].split('/')[-1])
        INFO("Validating schema for {}".format(result))
        self._validate_pci_device_funcs_schema(result, **kwargs)
        for func in result["Members"]:
          STEP("Validating function {} for the PCI device {} on Host {}".
               format(func, pci_device, host.ip))
          result = gateway.get_pci_device_function_by_uuid(
            pci_device['@odata.id'].split('/')[-1],
            func['@odata.id'].split('/')[-1]
          )
          INFO("Validating schema for {}".format(result))
          self._validate_pci_device_func_schema(host, result, **kwargs)
      INFO("PCI device related read-only APIs on gateway is "
           "validated successfully")

  def get_hosts_with_hsm_cards(self, **kwargs):
    """
    Get all hosts with HSM cards
    Args:
    Returns:
      hsm_hosts(dict):
    """
    # For CO node discovery on nutest cluster object for expand cluster
    # with CO node scenarios
    INFO(f"Hypervisors: {self.cluster.hypervisors}")
    INFO(f"Has CO nodes: {self.cluster.has_compute_only()}")
    self.cluster._populate_co_hypervisors()
    INFO(f"Hypervisors: {self.cluster.hypervisors}")
    hosts = self.cluster.hypervisors
    hsm_hosts = {}
    for host in hosts:
      hsm_cards = self._get_hsm_card_names(host)
      hsm_hosts[host.ip] = []
      for card in hsm_cards:
        data = {
          'host': host,
          'card': card
        }
        hsm_hosts[host.ip].append(data)
    return hsm_hosts

  def get_hsm_device_details(self, **kwargs):
    """
    Get the details for HSM device group UUID from all hosts in cluster
    Args:
    Returns:
    """
    # NOTE: This should change once groups API is available from gateway side
    hsm_hosts = self.get_hosts_with_hsm_cards()
    for hsm_host in hsm_hosts:
      # host = hsm_hosts[hsm_host]
      gateway = HostGatewayInterface(cluster=self.cluster,
                                     host=hsm_host)
      pci_devices = gateway.get_pci_devices()
      for i, pci_device in enumerate(pci_devices['Members']):
        hsm_hosts[hsm_host][i]['device_id'] = (
          pci_device['@odata.id'].split('/'))[-1]
        funcs = gateway.get_pci_device_functions(
          pci_device['@odata.id'].split('/')[-1])
        for func in funcs["Members"]:
          result = gateway.get_pci_device_function_by_uuid(
            pci_device['@odata.id'].split('/')[-1],
            func['@odata.id'].split('/')[-1]
          )
          hsm_hosts[hsm_host][i]['groups'] = \
            [group['GroupLabel'] for group in result['Oem']['NTNX']['Groups']]
          hsm_hosts[hsm_host][i]['function_id'] = result['Id']
    return hsm_hosts

  def _get_service_details(self, host, service="adm.service"):
    """
    Get the service details from given host.
    Args:
      host(object): nutest host object
      service(str): should contain .service
    Returns:
      details(dict): service details
    Raises:
      AssertionError:
    """
    details = {
      service: 0,
      "Loaded": 1,
      "Active": 2,
      "Process": 3,
      # "Main PID": 4,
      "Tasks":5,
      "Memory": 6,
      "CGroup": 7
    }
    cmd = ('systemctl status {} --no-block | '
           'grep -A 5 {}'.format(service, service))
    result = host.execute(cmd)
    assert result['status'] == 0, ("Failed to get {} details on "
                                   "host {}").format(service, host.ip)
    out = result['stdout']
    out = [line.strip() for line in out.split('\n') if line]
    for i, line in enumerate(details):
      if i == 0:
        # extract service name
        details[line] = (
          ' '.join(out[details[line]].split("-")[-1].split()).strip())
      else:
        details[line] = out[details[line]].split()[1].strip()
    return details

  def _validate_pci_device_func_schema(self, host, data, **kwargs):
    """
    PCI devices get function schema validation
    Args:
      host(object):
      data(dict):
    Kwargs:
      enabled(bool): True
    Raises:
    """
    enabled = kwargs.get("enabled", True)
    assert data.get('@odata.id'), "@odata.id field missing in schema"
    assert isinstance(data['@odata.id'], str), ("Failed the validate "
                                                "@odata.id data type, "
                                                "expected string, "
                                                "but got something else")
    assert data.get('@odata.type'), '@odata.type field missing in schema'
    assert isinstance(data['@odata.type'], str), ("Failed the validate "
                                                  "@odata.type data type, "
                                                  "expected string, "
                                                  "but got something else")
    assert data.get('ClassCode'), 'ClassCode field missing in schema'
    assert (data.get('Description') and data['Description']
            in self._get_hsm_card_names(host)), \
      'Name field missing in schema'
    assert data.get('DeviceId'), 'DeviceId field missing in schema'
    assert data.get('Enabled') == enabled, (
      'Enabled field missing or not in expected state: %s'
      % enabled)
    assert data.get('FunctionType'), 'FunctionType field missing in schema'
    assert data.get("Id"), "Id field missing in schema"
    assert data.get("Name"), "Name field missing in schema"
    assert data.get("Oem") and "NTNX" in data["Oem"], \
      "Oem field missing in schema"
    self._validate_oem_schema(data.get("Oem"), **kwargs)
    assert data.get("RevisionId"), "RevisionId field missing in schema"
    assert data.get("SubsystemId"), "SubsystemId field missing in schema"
    assert data.get("SubsystemVendorId"), ("SubsystemVendorId field "
                                           "missing in schema")
    assert data.get("VendorId"), "VendorId field missing in schema"

  def _validate_oem_schema(self, data, **kwargs):
    """
    Validate OEM schema in get PCI device function api
    Args:
      data(dict):
    Kwargs:
      state(str): UVM.Available default
      group_label(list): Checks exsistance of the filed by default, else compare
      group_type(list): Checks exsistance of the filed by default, else compare
    Raises:
    """
    state = kwargs.get("state", "UVM.Available")
    group_label = kwargs.get("group_label", [])
    group_type = kwargs.get("group_type", [])
    schema = data.get("NTNX")
    assert (schema.get("State") and schema['State'] in
            state), \
      ("Failed to get desired state, got: {}, expected: {}".format(
        schema, state))

    assert schema.get("Groups"), "Group field missing in OEM schema"
    for group in schema["Groups"]:
      assert group["GroupLabel"], \
        "GroupLabel field missing in OEM Groups schema"

      assert group["GroupType"], \
        "GroupType field missing in OEL Groups schema"

      if group_label:
        assert group["GroupLabel"] in group_label, (
          "Failed to get desired GroupLabel actual: "
          "{} expected {}".format(group["GroupLabel"],
                                  group_label))
      if group_type:
        assert group["GroupType"] in group_label, (
          "Failed to get desired GroupType actual: "
          "{} expected {}".format(group["GroupType"],
                                  group_type))

  def _validate_pci_device_funcs_schema(self, data, **kwargs):
    """
    PCI devices functions schema validation
    Args:
      data(dict):
    Raises:
    """
    assert data.get('@odata.id'), "@odata.id field missing in schema"
    assert isinstance(data['@odata.id'], str), ("Failed the validate "
                                                "@odata.id data type, "
                                                "expected string, "
                                                "but got something else")
    assert data.get('@odata.type'), '@odata.type field missing in schema'
    assert isinstance(data['@odata.type'], str), ("Failed the validate "
                                                  "@odata.type data type, "
                                                  "expected string, "
                                                  "but got something else")
    assert data.get('Members'), 'Id field missing in schema'
    assert isinstance(data['Members'], list), ("Failed the validate "
                                               "Members data type, "
                                               "expected list, "
                                               "but got something else")
    assert data.get('Members@odata.count'), 'Name field missing in schema'
    assert isinstance(data['Members@odata.count'], int), (
      "Failed the validate Members@odata.count data type, expected list,"
      " but got something else")

    assert (data.get('Name') and data.get('Name') ==
            "PCIe Function Collection"), \
      'PCIeFunctions field missing in schema'

  def _validate_pci_devices_schema(self, data, **kwargs):
    """
    PCI devices list schema validation
    Args:
      data(dict):
    Raises:
    """
    assert data.get('@odata.id'), "@odata.id field missing in schema"
    assert data.get('@odata.type'), '@odata.type field missing in schema'
    assert data.get('Members'), 'Id field missing in schema'
    assert data.get('Members@odata.count'), 'Name field missing in schema'
    assert data.get('Name'), 'PCIeFunctions field missing in schema'

  def _validate_pci_device_schema(self, data, **kwargs):
    """
    PCI device schema validation
    Args:
      data(dict):
    Raises:
    """
    assert data.get('@odata.id'), "@odata.id field missing in schema"
    assert data.get('@odata.type'), '@odata.type field missing in schema'
    assert data.get('Id'), 'Id field missing in schema'
    assert data.get('Name'), 'Name field missing in schema'
    assert data.get('PCIeFunctions'), 'PCIeFunctions field missing in schema'

  def _has_hsm_cards(self, host):
    """
    Get the count of hsm cards from the host
    Args:
      host(object): Nutest host object
    Returns:
      count(int): number of hsm cards
    """
    cmd = 'lspci | grep "Hardware Security Module" | wc -l'
    result = host.execute(cmd)
    assert result['status'] == 0, ("Failed to get hsm cards count for "
                                   "host {}").format(host.ip)
    return int(result['stdout'].strip())

  def _get_hsm_card_names(self, host):
    """
    Returns a list of HSM card names available on the host
    Args:
      host(object): Nutest host object or any object that
      implements execute cmd
    Returns:
      hsm_cards(list)
    """
    hsm_cards = []
    cmd = 'lspci | grep "Hardware Security Module"'
    try:
      result = host.execute(cmd)
    except NuTestCommandExecutionError:
      return hsm_cards
    if isinstance(result, dict):
      # Works for host
      for card in result["stdout"].split("\n"):
        if not card:
          continue
        # hardcording `rev 01`
        hsm_cards.append(card.split(":")[-1].strip().replace(' (rev 01)', ''))
      return hsm_cards
    else:
      # Works for linux guest
      return [res for res in result.split('\n') if res]


class VmHelper(BaseHelper):
  """VmHelper class"""

  @use_executor
  def create_vm_with_hsm_passthru(self, **kwargs):
    """
    Create VMs with HSM passthru
    Args:
    Returns:
    Raises
    """
    global VM_LIST
    if not hasattr(self, 'hsm_details'):
      self.hsm_details = self.host_helper.get_hsm_device_details()
    constants.VM_CACHE["vm_list"] = []
    vm_prefix = kwargs.pop('vm_name', 'hsm_vm')
    i = 1
    for host in self.hsm_details:
      for card in self.hsm_details[host]:
        # NOTE: Just taking the 1st group. This works for HSM cards as it
        #        has unique group, but what about other PCI devices ?
        group_uuid = card['groups'][0]
        if card.get('vm') and not kwargs.get("reassign_device", False):
          # This card is already assigned to some VM
          WARN("Skipping card %s as it is assigned to VM: %s" %
               (group_uuid, card.get('vm').name))
          continue
        vm_name = vm_prefix + "_" + str(i)
        INFO("Creating VM {} with {}".format(vm_name, card))
        kwargs["name"] = vm_name
        vm = self._create_add_assign_hsm_card(group_uuid, **kwargs)
        constants.VM_CACHE["vm_list"].append(vm.vm.uuid)
        card['vm'] = vm
        i += 1
    INFO("VM Create with HSM Card Completed Successfully, "
         "Validating HSM Card States: {}".format(self.hsm_details))

  @use_executor
  def validate_clone_for_vm_with_hsm(self, **kwargs):
    """
    Create and validate a clone for VM with HSM
    :param kwargs:
    :return:
    """
    global VM_LIST
    vm_name = kwargs.pop("vm_name", '')
    if vm_name not in [vm.name for vm in self.vm_list]:
      vm_name = []
    else:
      vm_name = [name.strip() for name in vm_name.split(",")]
    if not vm_name:
      vm_name = [vm.name for vm in self.vm_list]

    self.guest_helper.hsm_details = self.hsm_details

    INFO("Enabled for VMs: %s" % vm_name)
    for host in self.hsm_details:
      for card in self.hsm_details[host]:
        vm = card.get('vm')
        if vm.name in vm_name:
          assert vm, "VM not found for card {}, automation issue".format(card)
          INFO("Validating Power-On for VM {} and card {}".format(
            vm.name,
            card))
        else:
          # fix for multiple vms to check
          vm = [vm for vm in self.vm_list if vm.name in vm_name][0]
        clone_vm = vm.clone()
        self.vm_list.append(clone_vm)
        VM_LIST = self.vm_list

  @use_executor
  def assign_hsm_device(self, **kwargs):
    """
    Assign HSM card to VM
    Args:
    Returns:
    Raises:
    """
    vm_name = kwargs.pop("vm_name", '')
    if vm_name not in [vm.name for vm in self.vm_list]:
      vm_name = []
    else:
      vm_name = [name.strip() for name in vm_name.split(",")]
    if not vm_name:
      vm_name = [vm.name for vm in self.vm_list]

    for host in self.hsm_details:
      for i, card in enumerate(self.hsm_details[host]):
        group_uuid = card['groups'][0]
        vm = card['vm']
        if vm.name in vm_name:
          if kwargs.get("power_off", True):
            INFO("Powering off VM: %s before assign opearation" % vm_name)
            vm.power_off()
          else:
            WARN("Not powering off VM: %s before assign operation" % vm_name)
          res = vm.assign_pcie_device(group_uuid)
          assert "complete" in res['stdout'].lower(), \
            ("Failed to assign PCI device to vm %s with error %s "
             % (vm.name, res['stdout']))
          INFO("HSM Card Assign Completed Successfully "
               "for VM {}".format(vm.name))

  @use_executor
  def deassign_hsm_device(self, **kwargs):
    """
    Deassign HSM card to VM
    Args:
    Returns:
    Raises:
    """
    vm_name = kwargs.pop("vm_name", '')
    if vm_name not in [vm.name for vm in self.vm_list]:
      vm_name = []
    else:
      vm_name = [name.strip() for name in vm_name.split(",")]
    if not vm_name:
      vm_name = [vm.name for vm in self.vm_list]
    for host in self.hsm_details:
      for i, card in enumerate(self.hsm_details[host]):
        vm = card['vm']
        vm_data = vm.get()
        if kwargs.get("power_off", True):
          INFO("Powering off VM: %s before deassign opearation" % vm_name)
          vm.power_off()
        else:
          WARN("Not powering off VM: %s before deassign operation" % vm_name)
        # group_uuid = vm_data['pcie_device_info'][0]['group_uuid']
        config_uuid = vm_data['pcie_device_info'][0]['config_uuid']
        if vm.name in vm_name:
          res = vm.deassign_pcie_device(config_uuid)
          assert "complete" in res['stdout'].lower(), \
            ("Failed to unassign PCI device to vm %s with error %s "
             % (vm.name, res['stdout']))
          INFO("HSM Card De-Assign Completed Successfully "
               "for VM {}".format(vm.name))

  @use_executor
  def delete_vm_with_hsm_passthru(self, **kwargs):
    """
    Delete a VM with hsm passthru cards
    Args:
    Returns:
    """
    global VM_LIST
    vm_name = kwargs.pop("vm_name", '')
    if vm_name not in [vm.name for vm in self.vm_list]:
      vm_name = []
    else:
      vm_name = [name.strip() for name in vm_name.split(",")]
    if not vm_name:
      vm_name = [vm.name for vm in self.vm_list]
    if not vm_name:
      vm_name = self.vm_list
    INFO("Enabled for VMs: %s" % vm_name)
    remove_list = []
    for vm in self.vm_list:
      if vm.name in vm_name:
        vm.power_off()
        vm.remove()
        remove_list.append(vm)
    for vm in remove_list:
      self.vm_list.remove(vm)
    VM_LIST = self.vm_list

  @use_executor
  def validate_hsm_device_state(self, **kwargs):
    """
    Validate the hsm device states
    Kwargs:
      state(str): UVM.Assigned default
    """
    state = kwargs.get('state', 'UVM.Assigned')
    owner_check = kwargs.get('owner_check', True)
    vm_name = kwargs.pop("vm_name", '')
    if vm_name not in [vm.name for vm in self.vm_list]:
      vm_name = []
    else:
      vm_name = [name.strip() for name in vm_name.split(",")]
    if not vm_name:
      vm_name = [vm.name for vm in self.vm_list]
    INFO("Enabled for VMs: %s" % vm_name)
    reassign = False
    for host in self.hsm_details:
      if reassign:
        break
      for card in self.hsm_details[host]:
        gateway = HostGatewayInterface(cluster=self.cluster,
                                       host=host)
        result = gateway.get_pci_device_function_by_uuid(card['device_id'],
                                                         card['function_id'])
        INFO(result)
        if owner_check and card['vm'].name in vm_name:
          INFO("Validating card {} state".format(card))
          assert card['vm'].uuid == result['Oem']['NTNX'].get('Owner'), (
            "Incorrect VM uuid {} reported in "
            "HSM card info {}".format(card['vm'].uuid,
                                      result['Oem']['NTNX'].get('Owner')))
          self._validate_oem_schema(result['Oem'], state=state)
        elif owner_check and card['vm'].name not in vm_name:
          # fix this, will work only for single VM
          vm = [vm for vm in self.vm_list if vm.name in vm_name][0]
          assert vm.uuid == result['Oem']['NTNX'].get('Owner'), (
            "Incorrect VM uuid {} reported in "
            "HSM card info {}".format(vm.uuid,
                                      result['Oem']['NTNX'].get('Owner')))
          self._validate_oem_schema(result['Oem'], state=state)
          reassign = True

  @use_executor
  def validate_vm_pci_config(self, **kwargs):
    """
    Validate
    Kwargs:
      state(str): UVM.Assigned default
    """
    vm_name = kwargs.pop("vm_name", '')
    if vm_name not in [vm.name for vm in self.vm_list]:
      vm_name = []
    else:
      vm_name = [name.strip() for name in vm_name.split(",")]
    if not vm_name:
      vm_name = [vm.name for vm in self.vm_list]

    INFO("Enabled for VMs: %s" % vm_name)
    reassign = False
    for host in self.hsm_details:
      if reassign:
        break
      for card in self.hsm_details[host]:
        vm = card.get('vm')
        if vm.name in vm_name:
          assert vm, "VM not found for card {}, automation issue".format(card)
          INFO("Validating ACLI get for VM {} and card {}".format(vm.name,
                                                                  card))
        else:
          # fix for multiple VMs
          vm = [vm for vm in self.vm_list if vm.name in vm_name][0]
          reassign = True
        res = vm.get()
        for pci_data in res.get('pcie_device_info'):
          assert pci_data.get('group_uuid') == card.get('groups')[0], (
            "Failed to validate group_uuid in acli vm.get Expected {} "
            "Got {}".format(card.get('groups')[0],
                            pci_data.get('group_uuid')))
          assert pci_data.get('device_uuid') == card.get('function_id'), (
            "Failed to validate device id in acli vm.get Expected {} "
            "Got {}".format(card.get('function_id'),
                            pci_data.get('group_uuid')))
          assert pci_data.get('plugged_in'), (
            "Failed to validate plugged_in Expected {} "
            "Got {}".format(True, pci_data.get('plugged_in')))
          assert host == res.get('host_name'), (
            "Failed to validate VM host details Expected {} "
            "Got {}".format(host, res.get('host_name')))

  @use_executor
  def validate_power_cycle(self, **kwargs):
    """
    Validate HSM card state and in guest card after power cycle of VM
    Args:
    Returns:
    """
    vm_name = kwargs.pop("vm_name", '')
    if vm_name not in [vm.name for vm in self.vm_list]:
      vm_name = []
    else:
      vm_name = [name.strip() for name in vm_name.split(",")]
    if not vm_name:
      vm_name = [vm.name for vm in self.vm_list]

    self.guest_helper.hsm_details = self.hsm_details
    for host in self.hsm_details:
      for card in self.hsm_details[host]:
        vm = card.get('vm')
        if vm.name in vm_name:
          assert vm, "VM not found for card {}, automation issue".format(card)
          INFO("Validating Power-Cycle for VM {} and card {}".format(
            vm.name,
            card))
          power_cycle_params = {}
          if kwargs.get("change_host", False):
            kwargs.pop("change_host")
            hyp = [hyp for hyp in self.cluster.hypervisors
                   if hyp.ip != host][0]
            power_cycle_params["host"] = hyp.ip
            power_cycle_params["change_host"] = True
          vm.power_cycle(**power_cycle_params)
          INFO("Validating HSM device state after "
               "Power-Cycle of VM {}".format(vm.name))
          self.validate_hsm_device_state(state="UVM.Assigned")
          INFO("Validating PCI config of VM {}".format(vm.name))
          self.validate_vm_pci_config(owner=True)
          INFO("Validating HSM card within guest OS for VM {}".format(vm.name))
          self.guest_helper.validate_hsm_device_inguest()
    INFO("Power-Cycle validations for VM {} "
         "is successful".format(self.hsm_details))

  @use_executor
  def validate_power_on(self, **kwargs):
    """
    Validate HSM card state and in guest card after power on of VM
    Args:
    Returns:
    """
    vm_name = kwargs.pop("vm_name", '')
    if vm_name not in [vm.name for vm in self.vm_list]:
      vm_name = []
    else:
      vm_name = [name.strip() for name in vm_name.split(",")]
    if not vm_name:
      vm_name = [vm.name for vm in self.vm_list]

    self.guest_helper.hsm_details = self.hsm_details
    is_negative = kwargs.pop("is_negative", False)

    INFO("Enabled for VMs: %s" % vm_name)
    for host in self.hsm_details:
      for card in self.hsm_details[host]:
        vm = card.get('vm')
        if vm.name in vm_name:
          assert vm, "VM not found for card {}, automation issue".format(card)
          INFO("Validating Power-On for VM {} and card {}".format(
            vm.name,
            card))
        else:
          # fix for multiple vms to check
          vm = [vm for vm in self.vm_list if vm.name in vm_name][0]
        power_on_params = {}
        if kwargs.pop("change_host", False):
          hyp = [hyp for hyp in self.cluster.hypervisors
                 if hyp.ip != host][0]
          power_on_params["target_host"] = hyp
        vm.power_on(**power_on_params)
        expected_result = 'Pass'
        if is_negative:
          expected_result = 'Fail'
        INFO("Validating HSM device state after "
             "Power-On of VM {}".format(vm.name))
        self.validate_hsm_device_state(state="UVM.Assigned",
                                       expected_result=expected_result,
                                       vm_name=vm.name)
        INFO("Validating PCI config of VM {}".format(vm.name))
        self.validate_vm_pci_config(expected_result=expected_result,
                                    vm_name=vm.name)
        INFO("Validating HSM card within guest OS for VM {}".format(vm.name))
        self.guest_helper.validate_hsm_device_inguest(
          expected_result=expected_result, vm_name=vm.name)
    INFO("Power-On validations for VM {} "
         "is successful".format(self.hsm_details))

  def validate_power_off(self, **kwargs):
    """
    Validate HSM card state and in guest card after power off of VM
    Args:
    Returns:
    """
    vm_name = kwargs.pop("vm_name", '')
    if vm_name not in [vm.name for vm in self.vm_list]:
      vm_name = []
    else:
      vm_name = [name.strip() for name in vm_name.split(",")]
    if not vm_name:
      vm_name = [vm.name for vm in self.vm_list]

    self.guest_helper.hsm_details = self.hsm_details
    for host in self.hsm_details:
      for card in self.hsm_details[host]:
        vm = card.get('vm')
        if vm.name in vm_name:
          assert vm, "VM not found for card {}, automation issue".format(card)
          INFO("Validating Power-Off for VM {} and card {}".format(
            vm.name,
            card))
          vm.power_off()
          self.validate_hsm_device_state(state="UVM.Available",
                                         expected_result='Fail',
                                         vm_name=vm.name)
          INFO("Validation completed: HSM device state after "
               "Power-Off of VM {}, "
               "no pci device owner reported".format(vm.name))
          self.validate_vm_pci_config(expected_result='Fail',
                                      vm_name=vm.name)
          INFO("Valiation completed: PCI config of VM {}, "
               "no pci config reported in vm.get".format(vm.name))
    INFO("Power-Off validations for VM {} "
         "is successful".format(self.hsm_details))

  @use_executor
  def validate_lm(self, **kwargs):
    """
    Validate LM of VM with HSM passthrough - Negative
    Args:
    Returns:
    """
    vm_name = kwargs.pop("vm_name", '')
    if vm_name not in [vm.name for vm in self.vm_list]:
      vm_name = []
    else:
      vm_name = [name.strip() for name in vm_name.split(",")]
    vms = [vm for vm in self.vm_list if vm.name in vm_name]
    for vm in vms:
      vm.migrate()

  @use_executor
  def validate_clone(self, **kwargs):
    """
    Validate HSM card state and in guest card after acpi shutdown of VM
    Args:
    Returns:
    """

  def validate_acpi_shutdown(self, **kwargs):
    """
    Validate HSM card state and in guest card after acpi shutdown of VM
    Args:
    Returns:
    """

  def validate_acpi_reboot(self, **kwargs):
    """
    Validate HSM card state and in guest card after acpi reboot off of VM
    Args:
    Returns:
    """

  def _create_add_assign_hsm_card(self, group_uuid, **kwargs):
    """
    Internal method to create VM and assign HSM card
    Args:
      group_uuid (str): group uuid of hsm card
    Returns:
    """
    global VM_LIST
    vm = VmFactory(self.cluster, **kwargs)
    vm.create(**kwargs)
    self.vm_list.append(vm)
    VM_LIST = self.vm_list
    vm.add_boot_disk(**kwargs)
    vm.add_nic()
    assign_device = kwargs.get('assign_device', True)
    if assign_device:
      res = vm.assign_pcie_device(group_uuid)
      assert "complete" in res['stdout'].lower(), \
        (("Failed to assign PCI device to vm %s with error %s"
          % (vm.name, res['stdout'])))
      INFO("Device [%s] assigned to VM [%s]" % (group_uuid, vm.name))
    vm.power_on()
    return vm


class GuestHelper(BaseHelper):
  """GuestHelper class"""
  @use_executor
  def validate_hsm_device_inguest(self, **kwargs):
    """
    Validate hsm device inside guest
    Args:
    Returns:
    Raises:
    """
    global VM_LIST

    vm_name = kwargs.pop("vm_name", '')
    if vm_name not in [vm.name for vm in VM_LIST]:
      vm_name = []
    else:
      vm_name = [name.strip() for name in vm_name.split(",")]
    if not vm_name:
      vm_name = [vm.name for vm in VM_LIST]

    for host in self.hsm_details:
      for card in self.hsm_details[host]:
        vm = card.get('vm')
        assert vm, "VM not found for card {}, automation issue".format(card)
        if vm.name in vm_name:
          cards = vm.guest.get_hsm_card_names()
          assert cards, "No cards detected in VM {}".format(vm.name)
          INFO("Cards {} are detected in VM {}".format(cards,
                                                       vm.name))
        else:
          vm = [vm for vm in VM_LIST if vm.name in vm_name][0]
          cards = vm.guest.get_hsm_card_names()
          assert cards, "No cards detected in VM {}".format(vm.name)
          INFO("Cards {} are detected in VM {}".format(cards,
                                                       vm.name))


class ClusterHelper(BaseHelper):
  """ClusterHelper class"""
  def is_pci_passthru_configured(self):
    """
    Check if gflag is enabled for PCI passthru
    Args;
    Returns:
    Raises:
    """
    cluster = entities.ENTITIES.get("pe")
    configured = False
    for cvm in cluster.svms:
      cmd = 'grep "acropolis_enable_PCIe_devices" ' \
            '/home/nutanix/config/acropolis.gflags'
      try:
        cvm.execute(cmd)
      except NuTestCommandExecutionError as ex:
        if "No such file or directory" in str(ex):
          return configured
    configured = True
    return configured

  def configure_pci_passthru(self, **kwargs):
    """
    Enable gflag to enable PCI passthru
    Args;
    Returns:
    Raises:
    """
    cluster = entities.ENTITIES.get("pe")
    if not self.is_pci_passthru_configured():
      INFO("Configuring PCI passthru on the cluster")
      for cvm in cluster.svms:
        cmd = "echo --acropolis_enable_PCIe_devices=true " \
              "> /home/nutanix/config/acropolis.gflags"
        INFO("Enabling gflag on cvm: %s" % cvm.ip)
        cvm.execute(cmd)
      DirtyQuotaCluster.restart_acropolis()
      INFO("Configuring PCI Passthru gflag completed")
    assert self.is_pci_passthru_configured()
    INFO("PCI Passthru is already configured on cluster")


class HsmWfHelper(HostHelper, VmHelper, GuestHelper, ClusterHelper):
  """HsmPassthruWf class"""
  def __init__(self, **kwargs):
    """
    Create HsmPassthruWf Mixin object
    """
    # NOTE: The objects are for internal use, workflow class should
    #       always use HsmPassthruWf object
    super(HsmWfHelper, self).__init__(**kwargs)
    self.vm_list = []
    self.host_helper = HostHelper(**kwargs)
    self.vm_helper = VmHelper(**kwargs)
    self.guest_helper = GuestHelper(**kwargs)
    self.cluster_helper = ClusterHelper(**kwargs)

  def validate_setup_compatibility(self, **kwargs):
    """
    Atleast 1 node should have HSM card(s) attached to it.
    Args:
    Returns:
    Raises:
    """
    hsm_hosts = self.host_helper.get_hosts_with_hsm_cards(**kwargs)
    is_present = False
    for host in hsm_hosts:
      if hsm_hosts[host]:
        is_present = True
        break
    assert is_present, "No HSM cards detected on any of the hosts"
    INFO("Setup validation successful")
