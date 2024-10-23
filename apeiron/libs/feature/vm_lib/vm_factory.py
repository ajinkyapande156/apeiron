"""
Copyright (c) 2022 Nutanix Inc. All rights reserved.

Author: pritam.chatterjee@nutanix.com
"""
# pylint: disable=no-member,arguments-differ,unused-import, no-self-use
# pylint: disable=invalid-name
import time
from framework.lib.nulog import INFO, WARN, DEBUG, ERROR, STEP
from libs.framework import mjolnir_entities as entities
from libs.feature.vm_lib.vm_images \
  import VmImage
from libs.feature.vm_lib.vm_images \
  import VirtioImage


####################################################
# DO NOT use any of the classes except VmFactory
####################################################


class AbstractOSInstall():
  """AbstractOSInstall class"""
  def prepare_for_install(self, **kwargs):
    """
    Prepare VM for OS install
    Args:
    Returns:
    Raises:
    """
    raise NotImplementedError


class BaseOsInstaller(AbstractOSInstall):
  """BaseOsInstaller class"""
  def _upload_image(self, image_url):
    """
    Internal method used for image upload
    Args:
      image_url(str): image link
    Returns:
      image_id(tuple):
    """
    image_cls = entities.ENTITIES.get("rest_image")
    image_name = "_".join(image_url.split("/")[-6:])
    if image_name.split(".")[-1] == "iso":
      image_type = "ISO_IMAGE"
    else:
      image_type = "DISK_IMAGE"
    image = image_cls(name=image_name)
    image_id = image.upload_image(image_name, image_url, image_type)[1]
    INFO("Image %s with id %s upload to cluster" % (image_name, image_id))
    return image_id


class CdromOsInstall(BaseOsInstaller):
  """CdromOsInstall class"""
  def prepare_for_install(self, vm, image_details, **kwargs):
    """
    Prepare VM for OS install
    Args:
      vm(object): Nutest VM object
      image_details(dict): image details with urls etc
    Returns:
    Raises:
    """
    bus_type = kwargs.get("cdrom_bus_type", "SATA")
    INFO("Preparing vm %s for OS install" % vm.name)
    if "windows" in image_details.get("os"):
      virtio_id = self._upload_image(VirtioImage.get_virtio_driver())
      INFO(
        "Mounting installation VIRTIO image %s to vm %s" % (virtio_id, vm.name))
      vm.add_disk(is_cdrom=True, is_empty=False,
                  disk_type=bus_type,
                  clone_container_uuid=
                  entities.ENTITIES.get("rest_ctr").entity_uuid,
                  clone_from_vmdisk=virtio_id
                 )
    else:
      oemdrv_id = self._upload_image(image_details["images"]["oemdrv"])
      INFO(
        "Mounting installation OEMDRV image %s to vm %s" % (oemdrv_id, vm.name))
      vm.add_disk(is_cdrom=True, is_empty=False,
                  disk_type=bus_type,
                  clone_container_uuid=
                  entities.ENTITIES.get("rest_ctr").entity_uuid,
                  clone_from_vmdisk=oemdrv_id
                 )
    image_id = self._upload_image(image_details["images"]["cdrom"])
    INFO("Mounting installation CDROM image %s to vm %s" % (image_id,
                                                            vm.name))
    vm.add_disk(is_cdrom=True, is_empty=False,
                disk_type=bus_type,
                clone_container_uuid=
                entities.ENTITIES.get("rest_ctr").entity_uuid,
                clone_from_vmdisk=image_id
               )
    INFO("Attaching boot disk to vm %s" % vm.name)
    vm.add_disk(disk_type=kwargs.get("boot_disk_type", "SCSI"),
                is_cdrom=False,
                container_uuid=entities.ENTITIES.get("rest_ctr").entity_uuid,
                size_mb=kwargs.get("boot_disk_size", 80000),
                device_index=0)
    INFO("OS install Prep completed for vm %s" % vm.name)


class DiskOsInstall(BaseOsInstaller):
  """DiskOsInstall class"""
  def prepare_for_install(self, vm, image_details, **kwargs):
    """
    Prepare VM for OS install
    Args:
      vm(object): Nutest VM object
      image_details(dict): image details with urls etc
    Returns:
    Raises:
    """
    bus_type = kwargs.get("boot_disk_type", "SCSI")
    INFO("Preparing vm %s for Disk OS boot" % vm.name)
    image_id = self._upload_image(image_details["images"]["disk"])
    vm.add_disk(disk_type=bus_type, is_cdrom=False,
                clone_from_vmdisk=image_id)
    INFO("OS install Prep completed for vm %s" % vm.name)


class OSInstallerFactory():
  """OSInstallerFactory class"""
  MAP = {
    "iso": CdromOsInstall,
    "disk": DiskOsInstall
  }

  def __new__(cls, install_type="iso"):
    """
    Return correct installation class
    Args:
      install_type(str):
    Returns:
    """
    if install_type not in cls.MAP:
      install_type = "iso"
    return cls.MAP[install_type]()


class AbstractVm():
  """AbstractVm class"""
  def create_compute(self, **kwargs):
    """
    Add compute resources to VM
    Args:
    Returns:
    Raises:
    """
    raise NotImplementedError

  def install_os(self, **kwargs):
    """
    Install os on VM
    Args:
    Returns:
    Raises:
    """
    raise NotImplementedError

  def create_storage(self, **kwargs):
    """
    Create storage resources for VM
    Args:
    Returns:
    Raises:
    """
    raise NotImplementedError

  def create_network(self, **kwargs):
    """
    Create network resources for VM
    Args:
    Returns:
    Raises:
    """
    raise NotImplementedError


class BaseVm(AbstractVm):
  """BaseVm class"""
  # Default resource for creating VM
  COMPUTE_CONFIG = {
    "memory": 4096,
    "vcpus": 2,
    "cores_per_vcpu": 1,
    "machine_type": "pc"
  }
  # Default resources for installing OS on VM
  # NOTE: boot disk will be added as a part of os install
  OS_INSTALL_CONFIG = {
    "install_type": "iso",
    "cdrom_bus_type": "SATA",
    "boot_disk_type": "SCSI",
    "boot_disk_size": 80000
  }
  # Default storage resources for VM
  STORAGE_CONFIG = []

  # Default nic resources for VM
  NIC_CONFIG = [
    {
      "model": "virtio",
      "connected": True
    }
  ]

  def create_vm(self, **kwargs):
    """
    Creates VM
    Args:
    Returns:
    """
    self.vm_name = kwargs.get("name")
    self.guest_os = kwargs.get("guest_os", "windows10")
    user_comp_config = kwargs.get("compute_config", {})
    user_os_inst_config = kwargs.get("os_install_config", {})
    user_storage_config = kwargs.get("storage_config", self.STORAGE_CONFIG)
    user_nic_config = kwargs.get("nic_config", self.NIC_CONFIG)
    self.create_compute(user_config=user_comp_config)
    if not kwargs.get("dummy_vm", False):
      print("I am not dummy")
      self.create_os(user_config=user_os_inst_config)
    self.create_storage(user_config=user_storage_config)
    self.create_network(user_config=user_nic_config)
    INFO("VM configuration completed, powering on the VM")
    if "nested" in self.vm.cluster.name:
      INFO("Nested cluster . Timeout is increased")
      timeout = 3600
    else:
      timeout = 1000
    INFO("Setting timeout to: %s" % timeout)
    if kwargs.get("dummy_vm", False):
      self.vm.power_on(wait_for_ip=False)
      print("I am dummy")
      return self.vm
    self.vm.power_on(wait_for_ip=True, timeout=timeout)
    self.verify_vm_boot()
    self.os_installer_cleanup()
    self.verify_vm_reboot()
    return self.vm

  def create_storage(self, user_config):
    """
    Add storage resources to VM
    Args:
      user_config(dict): configs
    Returns:
    """
    self.STORAGE_CONFIG = user_config
    if not self.STORAGE_CONFIG:
      INFO("No storage disks provided in config")
    WARN("Need to implement this!!")

  def create_network(self, user_config):
    """
    Add network resources to VM
    Args:
      user_config(dict): configs
    Returns:
    """
    self.NIC_CONFIG = user_config
    if not self.NIC_CONFIG:
      INFO("No nic info provided in config")
      return
    INFO("Adding vNIC to VM: %s" % self.vm.name)
    nw_cls = entities.ENTITIES.get("rest_nw")
    nw = nw_cls(interface_type="REST", name="network")
    INFO("Creating network if not already present")
    nw_uuid = nw.create(bind=True, vlan_id=0)
    self.vm.add_nic(network=nw_uuid)

  def get_vm_rpc(self):
    """
    Get rpc settings after OS install
    Args:
    Returns:
    """
    rpc_cls = entities.ENTITIES.get("rpc_vm")
    rpc_vm = rpc_cls(self.vm)
    return rpc_vm

  def verify_vm_boot(self):
    """
    Verify VM boot after OS install
    Args:
    Returns:
    """
    rpc_vm = self.get_vm_rpc()
    retries = 90
    interval = 15
    INFO("Verifying if the VM booted successfully and is accessible")
    while True:
      try:
        res = rpc_vm.get_guest_os_info()
        return res
      except Exception as ex:  # pylint: disable=broad-except
        if retries <= 0:
          raise ex
        retries = retries - 1
        WARN("Wait for VM to boot up, retries remaining: %s" % retries)
        time.sleep(interval)

  def os_installer_cleanup(self):
    """
    Perform cleanup after OS install
    Args:
    Returns:
    """
    time.sleep(60)
    self.vm.power_off()
    for cdrom in [disk for disk in self.vm.get_disks()
                  if disk.is_cdrom]:
      INFO("Deleting cdrom: %s" % cdrom.uuid)
      self.vm.delete_disk(
        disk_type=cdrom.bus,
        device_index=cdrom.index,
        vmdisk_uuid=cdrom.uuid
      )
    self.vm.power_on(wait_for_ip=True)

  def verify_vm_reboot(self):
    """
    Verify after VM reboot
    Args:
    Returns:
    """
    total_timeout = 900
    reboot_timeout = 300
    start = time.time()
    INFO("Verifying if the VM booted successfully and is accessible "
         "after vm was rebooted")
    rpc_vm = self.get_vm_rpc()
    while True:
      try:
        res = rpc_vm.get_guest_os_info()
        return res
      except Exception as ex:  # pylint: disable=broad-except
        end = time.time()
        if end - start >= total_timeout: #pylint: disable=no-else-raise
          raise ex
        elif end - start >= reboot_timeout:
          WARN("Rebooting the VM as a workaround")
          self.vm.power_cycle()
          self.vm.power_on(wait_for_ip=True)
          reboot_timeout += 300
        INFO("Retrying to connect after 2 secs")
        time.sleep(2)

  def _get_edition(self):
    """
    Verify OS edition details
    Args:
    Returns:
    """
    params = {}
    params["os"] = self.guest_os
    if self.guest_os.startswith("windowsserver"):
      params["type"] = self.OS_INSTALL_CONFIG.get("edition", "standard")
    elif self.guest_os.startswith("windows"):
      params["type"] = self.OS_INSTALL_CONFIG.get("edition", "enterprise")
    else:
      params["type"] = self.OS_INSTALL_CONFIG.get("edition", "server")
    return params


class LegacyVm(BaseVm):
  """LegacyVm class"""
  def create_compute(self, user_config):
    """
    Add compute resources to VM
    Args:
      user_config(dict): configs
    Returns:
    """
    config = {"uefi": False}
    self.COMPUTE_CONFIG.update(config)
    self.COMPUTE_CONFIG.update(user_config)
    vm_cls = entities.ENTITIES.get("rest_vm")
    self.vm = vm_cls(interface_type="REST", name=self.vm_name)
    self.vm.create(bind=False,
                   validate=True,
                   name=self.vm_name, **self.COMPUTE_CONFIG)
    INFO("Created VM %s with uuid %s" % (self.vm.name, self.vm.uuid))

  def create_os(self, user_config):
    """
    Install OS on VM
    Args:
      user_config(dict): configs
    Returns:
    """
    self.OS_INSTALL_CONFIG.update(user_config)
    params = self._get_edition()
    params["boot"] = "legacy"
    vm_image = VmImage()
    self.vm_image = vm_image.get_vm_image(filters=params)[0]
    install_type = self.OS_INSTALL_CONFIG.pop("install_type", "iso")
    self.installer = OSInstallerFactory(install_type=install_type)
    self.installer.prepare_for_install(self.vm, self.vm_image,
                                       **self.OS_INSTALL_CONFIG)


class UefiVm(BaseVm):
  """UefiVm class"""
  def create_compute(self, user_config):
    """
    Get comoute resources for VM
    Args:
      user_config(dict): configs
    Returns:
    """
    config = {"uefi": True}
    self.COMPUTE_CONFIG.update(config)
    self.COMPUTE_CONFIG.update(user_config)
    vm_cls = entities.ENTITIES.get("rest_vm")
    self.vm = vm_cls(interface_type="REST", name=self.vm_name)
    self.vm.create(bind=False,
                   validate=True,
                   name=self.vm_name, **self.COMPUTE_CONFIG)
    INFO("Created VM %s with uuid %s" % (self.vm.name, self.vm.uuid))

  def create_os(self, user_config):
    """
    Install OS on VM
    Args:
      user_config(dict): configs
    Returns:
    """
    self.OS_INSTALL_CONFIG.update(user_config)
    params = self._get_edition()
    params["boot"] = "uefi"
    vm_image = VmImage()
    self.vm_image = vm_image.get_vm_image(filters=params)[0]
    install_type = self.OS_INSTALL_CONFIG.pop("install_type", "iso")
    self.installer = OSInstallerFactory(install_type=install_type)
    self.installer.prepare_for_install(self.vm, self.vm_image,
                                       **self.OS_INSTALL_CONFIG)


class SbVm(UefiVm):
  """SbVm class"""
  def create_compute(self, user_config):
    """
    Get comoute resources for VM
    Args:
      user_config(dict): configs
    Returns:
    """
    super(SbVm, self).get_compute_resources(user_config)
    config = {"secure_boot": True}
    self.COMPUTE_CONFIG.update(config)
    vm_cls = entities.ENTITIES.get("rest_vm")
    self.vm = vm_cls(interface_type="REST", name=self.vm_name)
    self.vm.create(bind=False,
                   validate=True,
                   name=self.vm_name, **self.COMPUTE_CONFIG)
    INFO("Created VM %s with uuid %s" % (self.vm.name, self.vm.uuid))


class CgVm(SbVm):
  """CgVm class"""
  def create_compute(self, user_config):
    """
    Get compute resources for VM
    Args:
      user_config(dict): configs
    Returns:
    """
    super(CgVm, self).get_compute_resources(user_config)
    config = {"windows_credential_guard": True}
    self.COMPUTE_CONFIG.update(config)
    vm_cls = entities.ENTITIES.get("rest_vm")
    self.vm = vm_cls(interface_type="REST", name=self.vm_name)
    self.vm.create(bind=False,
                   validate=True,
                   name=self.vm_name, **self.COMPUTE_CONFIG)
    INFO("Created VM %s with uuid %s" % (self.vm.name, self.vm.uuid))


class VtpmVm(SbVm):
  """VtpmVm class"""
  def create_compute(self, user_config):
    """
    Get compute resources for VM
    Args:
      user_config(dict): configs
    Returns:
    """
    super(VtpmVm, self).get_compute_resources(user_config)
    config = {"virtual_tpm": True}
    # self.COMPUTE_CONFIG.update(config)
    rest_vm_cls = entities.ENTITIES.get("rest_vm")
    acli_vm_cls = entities.ENTITIES.get("acli_vm")
    self.vm = rest_vm_cls(interface_type="REST", name=self.vm_name)
    self.vm.create(bind=False,
                   validate=True,
                   name=self.vm_name, **self.COMPUTE_CONFIG)
    acli_vm = acli_vm_cls(interface_type="ACLI", name=self.vm_name)
    acli_vm.create(bind=True,
                   validate=True,
                   name=self.vm_name)
    acli_vm.edit(**config)
    INFO("Created VM %s with uuid %s" % (self.vm.name, self.vm.uuid))


class VmFactory():
  """VmFactory class"""
  MAP = {
    "legacy": LegacyVm,
    "uefi": UefiVm,
    "sb": SbVm,
    "cg": CgVm,
    "vtpm": VtpmVm
  }

  def __new__(cls, vm_type="legacy",
              **kwargs):
    """
    Return correct VM class
    Args:
      vm_type(str):
    Returns:
    """
    if not cls.MAP.get(vm_type):
      vm_type = "legacy"
    vm = cls.MAP.get(vm_type)()
    return vm.create_vm(**kwargs)
