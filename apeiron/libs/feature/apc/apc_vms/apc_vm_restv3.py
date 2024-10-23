"""
Copyright (c) 2023 Nutanix Inc. All rights reserved.

Author: pritam.chatterjee@nutanix.com
"""
# pylint: disable=bad-continuation, fixme, unused-argument, no-member
# pylint: disable=self-assigning-variable, no-else-return
# pylint: disable=inconsistent-return-statements, no-self-use, unused-import
# pylint: disable=invalid-name
# pylint: disable=import-error, fixme, arguments-differ, no-else-return
# pylint: disable=unused-variable, consider-using-in, unnecessary-pass
# pylint: disable=inconsistent-return-statements, too-many-public-methods
# pylint: disable=no-self-use, ungrouped-imports, unused-import
import uuid

from libs.framework.exceptions.entity_error import NuTestEntityValidationError
from framework.lib.nulog import INFO, WARN, ERROR
from libs.feature.apc.apc_vms.abstract \
  import AbstractApcVm
from libs.framework import mjolnir_entities as entities
from workflows.acropolis.ahv.ahv_uvm_resource import UVM_RESOURCE
from workflows.acropolis.ahv.ahv_uvm_resource import AHVUVMResource
from libs.framework.mjolnir_executor import \
  use_executor


# from workflows.manageability.api.aplos import vms_api as VmsAPI


# TODO: copy methods from VmsAPI when isolating from nutest


class ApcVmRestv3(AbstractApcVm):
  """AbstractApcVm"""

  def __init__(self, **kwargs):
    """
    Initialize rest ApcVm rest v3 object
    Args:
    Returns:
    Raises:
    """
    self.pc = entities.ENTITIES.get("pc")
    self.pe = entities.ENTITIES.get("pe")

  def create(self, **kwargs):
    """
    Create a VM
    Args:
    Returns:
    Raises:
    """
    # TODO: please remove this VmsAPI dependency from here.

    vm_name = kwargs.get("vm_name",
                         "apc_vm_" + str(uuid.uuid1()).split("-")[0])
    vm_spec = entities.ENTITIES.get("restv3_vm").get_sample_spec()
    self._add_cluster_ref(vm_spec)
    vm_spec["vm_name"] = vm_name
    if kwargs.get("discover"):
      assert kwargs.get("vm_name"), "VM name should be provided to discover VM"
      return self.discover_vm_by_name(**{"vm_name": vm_name})
    vm_spec.update(self._get_config(**kwargs))
    if kwargs.get("cpu_passthru"):
      vm_spec.update({"enable_cpu_passthrough": True})
    if kwargs.get("apc_config"):
      vm_spec.update({"apc_config": kwargs.get("apc_config")})
    if kwargs.get("vnuma_nodes") and kwargs.get("vnuma_nodes") > 1:
      entities.ENTITIES.get("restv3_vm"). \
        update_num_vnuma_nodes_in_vm_spec(vm_spec, kwargs.get("vnuma_nodes"))
    if kwargs.get("num_threads_per_core") and \
      kwargs.get("num_threads_per_core") > 1:
      entities.ENTITIES.get("restv3_vm"). \
        update_num_threads_in_vm_spec(vm_spec,
                                      kwargs.get("num_threads_per_core"))
    if kwargs.get("vtpm"):
      vm_spec.update(
        {
          "vtpm_config": {
            "vtpm_enabled": True
          }
        }
      )
    if kwargs.get("mem_oc"):
      entities.ENTITIES.get("restv3_vm").\
        update_mem_oc_in_vm_spec(vm_spec, kwargs.get("mem_oc"))
    vm_spec.update(self._get_boot_config(**kwargs))
    # add_vnic
    if kwargs.get("add_vnic", True):
      subnet_uuid = self._get_subnet_uuid()
      vm_spec = entities.ENTITIES.get("restv3_vm"). \
        add_nic_to_vm_spec(vm_spec, subnet_uuid)
    response = entities.ENTITIES.get("restv3_vm").create_vm(self.pc,
                                                            vm_spec=vm_spec)
    response["vm_name"] = vm_name
    return response

  def discover_vm_by_name(self, **kwargs):
    """
    Discover any existing VM on setup by name
    Please NOTE vm name should be UNIQUE on the setup, otherwise
    Args:
    Returns:
    Raises:
    """
    # FIXME: Does not have host reference
    vm_name = kwargs.get("vm_name")
    vm_list = entities.ENTITIES.get("restv3_vm").get_list(self.pc)
    discovered_vm = None
    for vm_spec in vm_list:
      if vm_spec["vm_name"] == vm_name.strip():
        INFO("Found the VM to bind: %s" % vm_spec)
        return vm_spec
    assert discovered_vm, "Failed to find the VM with name: %s" % vm_name

  @use_executor
  def clone(self, **kwargs):
    """
    Clones a Vm
    Args:
    Returns:
    Raises:
    """
    vm_uuid = kwargs.get("vm_spec").get("uuid") or kwargs.get("uuid")
    return entities.ENTITIES.get("restv3_vm").clone_vm(
      self.pc,
      vm_uuid,
      cluster_uuid=self.pe.uuid,

    )

  @use_executor
  def power_on(self, vm_spec):
    """
    Power on the VM.
    Args:
      vm_spec(dict):
    Kwargs:
    Returns:
    Raises:
    """
    vm_spec["power_state"] = "ON"
    response = self.update(
      vm_spec=vm_spec,
      retries=5,
      validate=False
    )
    ERROR(response)
    return response

  @use_executor
  def power_off(self, vm_spec):
    """
    Power off the VM.
    Args:
      vm_spec(dict):
    Kwargs:
    Returns:
    Raises:
    """
    vm_spec["power_state"] = "OFF"
    response = self.update(
      vm_spec=vm_spec,
      retries=5,
      validate=False
    )
    ERROR(response)
    return response

  def migrate(self, **kwargs):
    """
    create an apc enabled Vm with provided details
    Args:
    Returns:
    Raises:
    """
    raise NotImplementedError

  @use_executor
  def get(self, **kwargs):
    """
    create an apc enabled Vm with provided details
    Args:
    Returns:
    Raises:
    """
    vm_uuid = kwargs.get("vm_spec").get("uuid") or kwargs.get("uuid")
    response = self.pc.send(method='get', uri="vms/" + vm_uuid)
    if response.status_code not in [200, 201, 202]:
      ERROR("Unable to get successful response")
    response = response.json()
    vm_details = response["status"]["resources"]
    vm_details["uuid"] = vm_uuid
    vm_details["vm_name"] = kwargs.get("vm_spec").get("vm_name")
    return vm_details
    # return entities.ENTITIES.get("restv3_vm").get_vm(self.pc, **kwargs)

  def update(self, **kwargs):
    """
    Update VM
    Args:
    Returns:
    Raises:
    """
    vm_spec = kwargs.get("vm_spec", {})
    vm_details = entities.ENTITIES.get("restv3_vm").get_vm(self.pc, vm_spec)
    # import pdb; pdb.set_trace()
    # update the entity version and spec version in vm_spec
    # if "entity_version" in vm_spec:
    #   vm_spec["entity_version"] = str(int(vm_spec["entity_version"]) + 1)
    vm_spec["entity_version"] = vm_details["entity_version"]
    vm_spec["spec_version"] = vm_details["spec_version"]
    return entities.ENTITIES.get("restv3_vm").update_vm(
      self.pc,
      vm_spec
    )

  def list(self, **kwargs):
    """
    create an apc enabled Vm with provided details
    Args:
    Returns:
    Raises:
    """
    raise NotImplementedError

  def delete(self, **kwargs):
    """
    create an apc enabled Vm with provided details
    Args:
    Returns:
    Raises:
    """
    vm_uuid = kwargs.get("vm_spec").get("uuid") or kwargs.get("uuid")
    return entities.ENTITIES.get("restv3_vm").delete_vm(self.pc, vm_uuid)

  def power_cycle(self, **kwargs):
    """
    do a vm powercycle
    Args:
    Returns:
    Raises:
    """
    raise NotImplementedError

  def live_migrate(self, **kwargs):
    """
    perform vm live migrate
    Args:
    Returns:
    Raises:
    """
    raise NotImplementedError

  def add_guest_os(self, vm_spec, **kwargs):
    """
    Adds a guest os to the VM.
    Args:
      vm_spec(dict):
    Kwargs:
      guest_os(str): Name of the guest os. Defaults to rhel9.0
      guest_os_repo(str): From where to fetch the guest os
      install_process(str): disk based|cdrom based. By default,
                            it is disk based.
    Returns:
    Raises:
    """
    guest_os = kwargs.get("guest_os", "rhel90")
    guest_os_repo = kwargs.get("guest_os_repo", "ahv_uvm_resource")
    install_process = kwargs.get("install_process", "qcow2")
    if "ahv_uvm_resource" in guest_os_repo:
      install_process = "qcow2"
    else:
      install_process = install_process
    img_uuid = self._get_image_uuid(guest_os, guest_os_repo,
                                    install_process, kwargs.get("boot_type",
                                                                "uefi"))
    device_index = kwargs.get("device_index") or \
                   entities.ENTITIES.get("restv3_vm").find_usable_device_index(
                     vm_spec.get('disk_list', []),
                     kwargs.get("adapter_type", "SCSI")
                   )
    vm_spec = entities.ENTITIES.get("restv3_vm").add_disk_to_vm_spec(
      vm_spec,
      adapter_type=kwargs.get("adapter_type",
                              "SCSI"),
      data_source_uuid=img_uuid,
      data_source_name=guest_os,
      data_source_type="image"
    )
    boot_device = {
      "disk_address": {
        "adapter_type": kwargs.get("adapter_type", "SCSI"),
        "device_index": device_index
      }
    }
    if not vm_spec.get('boot_config', None):
      vm_spec['boot_config'] = {}

    vm_spec['boot_config']['boot_device'] = boot_device
    return entities.ENTITIES.get("restv3_vm").update_vm(
      self.pc,
      vm_spec
    )

  @use_executor
  def is_vm_accesible(self, vm_spec, **kwargs):
    """
    Wait for VM to boot up and become accessible.
    Args:
      vm_spec(dict): Spec of the required VM.
    Returns:
      rpc(object): test agent connection to VM
    Raises:
    """
    vm_details = self.get(vm_spec=vm_spec)
    ip = self._get_vm_ip(vm_details)
    rpc = entities.ENTITIES.get("rpc")(ip)
    if rpc.get_guest_os_info():
      return rpc
    raise NuTestEntityValidationError("VM is not accessible yet")

  @staticmethod
  def _get_vm_ip(vm_spec, return_all=False):
    """
    Retrieve VM's IP Address from the specified spec.

    Args:
      vm_spec(dict): Spec of the required VM.
      return_all(bool): Return a list of IP addresses (default: False)

    Returns:
      str/list: IP Address or list of IP Addresses of the VM, if present.
    """
    ip_list = []
    nic_list = vm_spec.get('nic_list', [])
    if not nic_list:
      ERROR("No NIC present in VM Spec.")
    for nic in nic_list:
      ip_endpoints = nic.get('ip_endpoint_list', [])
      for ip_endpoint in ip_endpoints:
        if ip_endpoint.get('ip'):
          if return_all:
            ip_list.append(ip_endpoint['ip'])
          else:
            return ip_endpoint['ip']
    if ip_list:
      return ip_list
    else:
      raise NuTestEntityValidationError("No IP Addresses found in VM Spec.")

  def _get_subnet_uuid(self, **kwargs):
    """
    Get subnet uuid
    Args:
    Returns:
    """
    subnet_uuid = self._get_subnet_uuid_from_list(**kwargs)
    if subnet_uuid is not None:
      return subnet_uuid
    else:
      INFO("Unable to find a subnet with the specified vlan. "
           "Creating a new one.")
      subnet_name = kwargs.get('subnet_name', 'vlan.0')
      cluster_reference = {
        "kind": "cluster",
        "name": self.pe.name,
        "uuid": self.pe.entity_id
      }
      subnet_spec = {
        "vlan_id": kwargs.get('vlan', 0),
        "name": subnet_name,
        "subnet_type": "VLAN",
        "cluster_reference": cluster_reference,
        "api_version": "3.0"
      }
      entities.ENTITIES.get("restv3_nw").create_subnet(self.pc,
                                                       subnet_spec)
      return self._get_subnet_uuid_from_list(**kwargs)

  def _get_subnet_uuid_from_list(self, **kwargs):
    """
    Get subnet list
    Args:
    Returns:
    """
    network_type = kwargs.get("network_type", "unmanaged")
    subnet_list = entities.ENTITIES.get("restv3_nw").get_list(self.pc)
    vlan_id = kwargs.get('vlan', 0)
    for subnet in subnet_list:
      if subnet['vlan_id'] == vlan_id and \
        subnet['cluster_reference']['uuid'] == self.pe.entity_id:
        if network_type == "unmanaged":
          return subnet['uuid']
        else:
          if 'ip_config' in subnet:
            return subnet['uuid']
    ERROR("Unable to retrieve the subnet uuid of the vlan %s from subnet list"
          % vlan_id)

  def _get_config(self, **kwargs):
    """
    _get_config
    Args:
    Returns:
    Raises:
    """
    return {
      "memory_size": kwargs.get("memory_size", 4 * 1024),
      "num_sockets": kwargs.get("num_of_vcpus", 2),
      "num_vcpus_per_socket": kwargs.get("cores_per_vcpu", 1),
      "poll_interval": 5  # what is this ?
    }

  def _get_boot_config(self, **kwargs):
    """
    _get_boot_config
    Args:
    Returns:
    Raises:
    """
    # TODO: make more generic to address any boot type
    # currently considering only legacy and cg+vtpm
    boot_type = kwargs.get("boot_type", "uefi")
    if boot_type == "uefi":
      return {
        'boot_config': {
          'boot_type': 'UEFI'
        }
      }
    elif boot_type == "secure_boot":
      return {
        'boot_config': {
          'boot_type': 'SECURE_BOOT'
        },
        'machine_type': 'Q35'
      }
    elif boot_type == "credential_guard":
      return {
        'boot_config': {
          'boot_type': 'SECURE_BOOT'
        },
        'hardware_virtualization_enabled': True,
        'machine_type': 'Q35'
      }
    else:
      return {}

  def _get_image_uuid(self, guest_os, guest_os_repo, install_process,
                      boot_type):
    """
    Get image uuid by name. If not present uploads.
    Args:
      guest_os(str):
      guest_os_repo(str):
      install_process(str):
      boot_type(str):
    Returns:
    """
    MAP = {
      "uefi": "disk_image_uefi_legacy",
      "legacy": "disk_image",
      "secure_boot": "disk_image_uefi_legacy",
      "credential_guard": "disk_image_uefi_legacy",
      "vtpm": "disk_image_uefi_legacy"
    }
    if "qcow2" in install_process:
      image_type = "DISK_IMAGE"
    else:
      image_type = "ISO_IMAGE"
    if "ahv_uvm_resource" in guest_os_repo:
      # source_uri = UVM_RESOURCE.get(guest_os)
      source_uri = AHVUVMResource(self.pe).get_image_name_url_common(
        guest_os,
        MAP[boot_type]
      )[1]
    else:
      ERROR("For now the guest OS images should be in ahv_uvm_resource.py")
      source_uri = None
    assert source_uri, "Could not find image %s in given location %s" % \
                       (guest_os, guest_os_repo)
    # NOTE: This will need fix for qcow2 based on legacy or uefi
    image_name = "apc_" + guest_os + "_" + MAP[boot_type]
    image_spec = self._get_image(image_name, image_type)
    if image_spec is None:
      WARN("Image not found, attempting to download image to cluster/pc.")
      image_spec = entities.ENTITIES.get("restv3_image").get_sample_spec(
        name=image_name,
        image_type=image_type,
        source_uri=source_uri
      )
      image_spec = entities.ENTITIES.get("restv3_image").create_image(
        self.pc,
        image_spec, poll_secs=1800
      )
    return image_spec["uuid"]

  def _get_image(self, image_name, image_type):
    """
    Get the image details by name
    Args:
      image_name(str):
      image_type(str):
    Returns:
    """
    for image in entities.ENTITIES.get("restv3_image").get_list(
      self.pc
    ):
      if (image.get("name") == image_name and
        image.get("image_type") == image_type):
        return image

    ERROR('Unable to find an image with name %s from the existing list.'
          % image_name)

  def _add_cluster_ref(self, entity_spec):
    """
    Add cluster ref to VM calls
    Args:
      entity_spec(dict):
    Returns:
    Raises:
    """
    entity_spec.update({'cluster_reference': {
      "kind": "cluster",
      "uuid": self.pe.uuid}
    })
