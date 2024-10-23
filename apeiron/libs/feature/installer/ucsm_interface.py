"""
Copyright (c) 2024 Nutanix Inc. All rights reserved.

Authors: umashankar.vd@nutanix.com

This is the ucsm interface implementation of hypervisor power operations.
"""
# pylint: disable=arguments-differ
# pylint: disable=broad-except
# pylint: disable=useless-else-on-loop
# pylint: disable=protected-access
# pylint: disable=no-self-use, invalid-name, using-constant-test, no-else-return
# pylint: disable=unused-variable, unused-import, no-member
# pylint: disable=too-many-branches, too-many-statements, unused-argument
# pylint: disable=ungrouped-imports, line-too-long, too-many-locals
# pylint: disable=broad-except, singleton-comparison, inconsistent-return-statements

import time
import os
from ucsmsdk.ucshandle import UcsHandle
from ucsmsdk.mometa.vnic.VnicIpV4PooledAddr import VnicIpV4PooledAddr
from ucsmsdk.mometa.compute.ComputeRackUnit import ComputeRackUnit
from ucsmsdk.mometa.compute.ComputeBlade import ComputeBlade
from ucsmsdk.mometa.cimcvmedia.CimcvmediaConfigMountEntry import CimcvmediaConfigMountEntry
from ucsmsdk.mometa.cimcvmedia.CimcvmediaMountConfigPolicy import CimcvmediaMountConfigPolicy
from ucsmsdk.mometa.ls.LsPower import LsPower
from ucsmsdk.mometa.lsboot.LsbootBootSecurity import LsbootBootSecurity
from ucsmsdk.mometa.vnic.VnicEther import VnicEther
from framework.exceptions.nutest_error import NuTestError
from framework.lib.nulog import DEBUG, INFO

class UcsLoginHandler():
  """
  This class is a context manager for UCSM login/logout.
  """

  def __init__(self, **kwargs):
    """
    Constructor for UcsLoginHandler.
    Args:
      kwargs
    """
    # self.hostname = ucsm
    # self.username = username
    # self.password = password
    # self.port = port
    # self.ipmi = ipmi
    # self.vmedia_policy = vmedia_policy
    self.ucsm_ip = kwargs.get("UCSM_ip")
    self.ucsm_user = kwargs.get("ucsm_user", "admin")
    self.ucsm_password = kwargs.get("ucsm_password", "admin")
    self.ipmi = kwargs.get("ipmi_ip")
    self.iso_name = kwargs.get("iso_name")
    self.host_ip = kwargs.get("host_ip")
    self.build_url = kwargs.get("build_url")
    self.nfs_path = kwargs.get("nfs_path")
    self.nfs_server = kwargs.get("NFS_server")
    self.remote_server = kwargs.get("remote_server")
    self.external_HDD = kwargs.get("metadata_via_hdd", "no")
    self.vmedia_policy = kwargs.get("vmedia_name")
    self.multinode = kwargs.get("multinode_case")
    self.hdd = kwargs.get("metadata_via_hdd")
    self.serial_num = kwargs.get("serial_number")
    self.boot_mode = kwargs.get("boot_mode", "uefi")
    self.port = 443

    self.parent_dn = "org-root"

  def ucs_login(self):
    """
    Login to UCSM.
    Args
    Returns:
      UcsHandle: The UcsHandle object.
    Raises
    """
    try:
      self.handle = UcsHandle(self.ucsm_ip, self.ucsm_user,
                              self.ucsm_password, self.port)
      self.handle.login()
      return self.handle
    except Exception as exc:
      raise NuTestError("Failed to login to UCSM: %s" % str(exc))

  def ucs_logout(self):
    """Exit Context Manager.
    Args:
    Returns:
    Raises:
    """
    self.handle.logout()

  def power_cycle(self):
    """
    Args:
    Returns:
    Raises:
    """
    self.ucs_login()
    servers = self._list_servers()
    for server in servers:
      bmc_address = self._get_cimc_addresses(server)
      if bmc_address == self.ipmi:
        power_mo = self.handle.query_dn(server.assigned_to_dn + "/power")
        power_mo.state = "cycle-immediate"
        self.handle.set_mo(power_mo)
        self.handle.commit()
    self.ucs_logout()

  def power_ops(self, desired_state):
    """
    Args:
      desired_state(str): can be up or down
    Returns:
    Raises:
    """
    INFO("Desired power state to be set is: %s" %desired_state)
    self.ucs_login()
    servers = self._list_servers()
    for server in servers:
      bmc_address = self._get_cimc_addresses(server)
      if bmc_address == self.ipmi:
        power_mo = self.handle.query_dn(server.assigned_to_dn + "/power")
        power_mo.state = desired_state
        self.handle.set_mo(power_mo)
        self.handle.commit()
    self.ucs_logout()

  def vmedia_update(self):
    """
    Args:
    Returns:
    Raises:
    """
    self.ucs_login()
    vmedia_policy_dn = self.parent_dn + "/mnt-cfg-policy-" + self.vmedia_policy
    vmedia_policy = self.handle.query_dn(vmedia_policy_dn)
    if vmedia_policy is None:
      INFO("vmedia_policy does not exist, creating it!")
      mo = CimcvmediaMountConfigPolicy(parent_mo_or_dn=self.parent_dn,
                                       name=self.vmedia_policy,
                                       retry_on_mount_fail="yes",
                                       policy_owner="local",
                                       descr="from nutest")
      self.handle.add_mo(mo, modify_present=True)
      self.handle.commit()
      #setting media policy obj after creation
      vmedia_policy = self.handle.query_dn(vmedia_policy_dn)

    mo = CimcvmediaConfigMountEntry(parent_mo_or_dn=vmedia_policy,
                                    mapping_name="AHVISO",
                                    device_type="cdd",
                                    image_file_name=self.iso_name,
                                    mount_protocol="nfs",
                                    remote_ip_address=self.nfs_server,
                                    image_path=self.nfs_path)
    self.handle.add_mo(mo, modify_present=True)
    self.handle.commit()

    #if HDD is set to yes then do this
    if self.hdd == "yes":
      mo = CimcvmediaConfigMountEntry(parent_mo_or_dn=vmedia_policy,
                                      mapping_name="meta-HDD",
                                      device_type="hdd",
                                      image_file_name="ahv-metadata.img",
                                      mount_protocol="nfs",
                                      remote_ip_address=self.nfs_server,
                                      image_path=self.nfs_path)
      self.handle.add_mo(mo, modify_present=True)
      self.handle.commit()
    #logout of UCSM
    self.ucs_logout()


  def vmedia_sp_attach(self):
    """
    Args:
    Returns: sp(object)
    Raises:
    """
    self.ucs_login()
    servers = self._list_servers()
    for server in servers:
      bmc_address = self._get_cimc_addresses(server)
      if bmc_address == self.ipmi:
        hp = self.handle.query_dn(server.dn)
        sp = self.handle.query_dn(hp.assigned_to_dn)
        vmedia_policy_dn = self.parent_dn + "/mnt-cfg-policy-" + self.vmedia_policy
        vmedia_policy = self.handle.query_dn(vmedia_policy_dn)
        if vmedia_policy is None:
          raise ValueError("vmedia_policy does not exist.")
        if sp.src_templ_name:
          sp_template = self.parent_dn + "/ls-" + sp.src_templ_name
          mo = self.handle.query_dn(sp_template)
        else:
          mo = self.handle.query_dn(sp)
        mo.vmedia_policy_name = self.vmedia_policy
        self.handle.set_mo(mo)
        self.handle.commit()
    self.ucs_logout()
    return sp

  def vmedia_sp_detach(self):
    """
    Args:
    Returns:sp(object)
    Raises:
    """
    self.ucs_login()
    servers = self._list_servers()
    for server in servers:
      bmc_address = self._get_cimc_addresses(server)
      if bmc_address == self.ipmi:
        hp = self.handle.query_dn(server.dn)
        sp = self.handle.query_dn(hp.assigned_to_dn)
        if sp is None:
          raise ValueError("sp does not exist.")
        if sp.src_templ_name:
          sp_template = self.parent_dn + "/ls-" + sp.src_templ_name
          mo = self.handle.query_dn(sp_template)
        else:
          mo = self.handle.query_dn(sp)
        mo.vmedia_policy_name = ""
        self.handle.set_mo(mo)
        self.handle.commit()
    self.ucs_logout()
    return sp

  def remove_vnics(self, num_of_vnics):
    """
    Args:
      num_of_vnics(int): Number of vNICs to be added
    Returns:
    Raises:
    """
    self.ucs_login()
    servers = self._list_servers()
    addr = "derived"
    stats_policy_name = "default"
    for server in servers:
      bmc_address = self._get_cimc_addresses(server)
      if bmc_address == self.ipmi:
        hp = self.handle.query_dn(server.dn)
        sp = self.handle.query_dn(hp.assigned_to_dn)
        if sp is None:
          raise ValueError("sp does not exist.")
        if sp.oper_src_templ_name:
          INFO("Service profile is from template, so setting dn to it")
          sp = self.handle.query_dn(sp.oper_src_templ_name)
        for nic in range(0, num_of_vnics):
          name = "nutest_"+str(nic)
          order = str(2+nic) #default number of NIC's 2
          mo = VnicEther(parent_mo_or_dn=sp, nw_ctrl_policy_name="", name=name,\
                         admin_host_port="ANY", admin_vcon="any",\
                          stats_policy_name=stats_policy_name, admin_cdn_name=""\
                            , switch_id="A", pin_to_group_name="", mtu="1500", \
                              qos_policy_name="", adaptor_profile_name="",\
                                ident_pool_name="default",\
                                  order=order, nw_templ_name="", addr=addr)
          self.handle.remove_mo(mo)
          self.handle.commit()

  def add_vnics(self, num_of_vnics):
    """
    Args:
      num_of_vnics(int): Number of vNICs to be added
    Returns:
    Raises:
    """
    self.ucs_login()
    servers = self._list_servers()
    addr = "derived"
    stats_policy_name = "default"
    for server in servers:
      bmc_address = self._get_cimc_addresses(server)
      if bmc_address == self.ipmi:
        hp = self.handle.query_dn(server.dn)
        sp = self.handle.query_dn(hp.assigned_to_dn)
        if sp is None:
          raise ValueError("sp does not exist.")
        if sp.oper_src_templ_name:
          INFO("Service profile is from template, so setting dn to it")
          sp = self.handle.query_dn(sp.oper_src_templ_name)
        for nic in range(0, num_of_vnics):
          name = "nutest_"+str(nic)
          order = str(2+nic) #default number of NIC's 2
          mo = VnicEther(parent_mo_or_dn=sp, nw_ctrl_policy_name="", name=name,\
                         admin_host_port="ANY", admin_vcon="any",\
                          stats_policy_name=stats_policy_name, admin_cdn_name="",\
                            switch_id="A", pin_to_group_name="", mtu="1500",\
                              qos_policy_name="", adaptor_profile_name="",\
                                ident_pool_name="default", order=order,\
                                  nw_templ_name="", addr=addr)
          self.handle.add_mo(mo, modify_present=True)
          self.handle.commit()
    self.ucs_logout()

  def boot_policy_modify(self, boot_mode="uefi"):
    """
    Args:
      boot_mode(str) : boot mode, legacy or uefi
    Returns:
    Raises:
    """
    self.ucs_login()
    servers = self._list_servers()
    for server in servers:
      bmc_address = self._get_cimc_addresses(server)
      if bmc_address == self.ipmi:
        hp = self.handle.query_dn(server.dn)
        sp = self.handle.query_dn(hp.assigned_to_dn)
        mo = self.handle.query_dn(sp.oper_boot_policy_name)
        mo.boot_mode = self.boot_mode
        self.handle.add_mo(mo, modify_present=True)
        self.handle.commit()
        break
    self.ucs_logout()

  def secure_boot_modify(self, secure_boot="no"):
    """
    Args:
      secure_boot(str) : yes or no
    Returns:
    Raises:
    """
    self.ucs_login()
    servers = self._list_servers()
    for server in servers:
      bmc_address = self._get_cimc_addresses(server)
      if bmc_address == self.ipmi:
        hp = self.handle.query_dn(server.dn)
        sp = self.handle.query_dn(hp.assigned_to_dn)
        secure_boot_policy = LsbootBootSecurity(parent_mo_or_dn=sp.oper_boot_policy_name)
        secure_boot_policy.secure_boot = secure_boot
        self.handle.set_mo(secure_boot_policy)
        self.handle.commit()
        break
    self.ucs_logout()

  def _get_cimc_addresses(self, phys_mo):
    """
    Args:
      phys_mo(object): Object of physical server to get CIMC
    Returns:
    Raises:
    """
    mos = self.handle.query_children(in_mo=phys_mo, class_id="MgmtController", hierarchy=True)
    bmc_addrs = []

    # IP v4 addresses
    ipv4AddrSet = [x for x in mos if x._class_id == 'VnicIpV4MgmtPooledAddr' or
                   x._class_id == 'VnicIpV4ProfDerivedAddr' or
                   x._class_id == 'VnicIpV4StaticAddr']
    for mo in ipv4AddrSet:
      if mo._class_id == 'VnicIpV4MgmtPooledAddr':
        access = 'in-band'
      else:
        access = 'oob'
      if mo.addr != '0.0.0.0':
        return mo.addr

    ipv4AddrSet = [x for x in mos if x._class_id == 'VnicIpV4PooledAddr']
    for mo in ipv4AddrSet:
      access = 'oob'
      if mo.addr != '0.0.0.0':
        return mo.addr

  def _list_servers(self):
    """
    Args:
    Returns:m(object)
    Raises:
    """
    blades = self.handle.query_classid(class_id="ComputeBlade")
    servers = self.handle.query_classid(class_id="ComputeRackUnit")
    m = blades + servers
    return m
