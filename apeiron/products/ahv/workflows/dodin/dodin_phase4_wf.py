"""
Copyright (c) 2022 Nutanix Inc. All rights reserved.

Author: umashankar.vd@nutanix.com

Dodin Phase4
"""
# pylint: disable=unused-variable, unused-import, no-member
# pylint: disable=too-many-branches, too-many-statements, unused-argument
# pylint: disable=ungrouped-imports, line-too-long

import time
from framework.lib.nulog import INFO, WARN, ERROR, \
  STEP
from libs.framework import mjolnir_entities as entities
from libs.feature.dodin.dodin_phase4 \
    import DodinPhase4Libs


class DodinP4Wf():
  """
  This work flow is for covering tests
  as part of phase4, in addition to phase3
  """

  def __init__(self, cluster, **kwargs):
    """
    Initialize workflow object
    Args:
        cluster(object): Nutest cluster object
    """
    self.cluster = cluster
    self.dodin_obj = DodinPhase4Libs(self.cluster, **kwargs)
    self.testing_enable_dod = kwargs.get("testing_enable_dod", None)
    if not self.testing_enable_dod:
      self.dodin_obj.enable_dod_wf_using_script(**kwargs)
    self._validation = []
    self.network_script_content = "system_u:object_r:net_conf_t:s0"

  def dodin_phase4_validation(self, **kwargs):
    """
    Generic function to handle file related operations
    Depending on operation name, carries out tests
    Args:
      kwargs
    Returns:
      Nothing
    Raises:
      assert
    """
    validation = kwargs.get("operation", "all")
    if validation == "all":
      dodin_validations = []
      all_attributes = dir(self)
      for attribute in all_attributes:
        if "dodin_" in attribute:
          dodin_validations.append(attribute)
          func_invoke = getattr(self, attribute)
          func_invoke(**kwargs)
      INFO("Here's the list of all dodin checks:%s"\
        %dodin_validations)
      return
    #below instruction is for standlone validation
    func_invoke = getattr(self, validation)
    func_invoke(**kwargs)

  def dodin_network_script_validation(self, **kwargs):
    """
    Args:
      kwargs
    Returns:
      Nothing
    Raises:
      assert
    """
    STEP("There are %s nodes in the cluster" % \
      len(self.dodin_obj.cluster.hypervisors))
    INFO("Shall run NW script validation on all nodes")
    for host in self.cluster.hypervisors:
      STEP("Validation network script content on host: %s" %host.ip)
      content = self.dodin_obj.network_script_validation(host.ip, **kwargs)
      INFO("Network script content : %s" %content)
      if self.network_script_content in content['stdout']:
        INFO("Script content is as expected")
      else:
        raise AssertionError("Script content did not meet expectated value %s"\
          %self.network_script_content)

  def dodin_last_login(self, **kwargs):
    """
    Args:
      kwargs
    Returns:
      Nothing
    Raises:
      assert
    """
    STEP("There are %s nodes in the cluster" % \
      len(self.dodin_obj.cluster.hypervisors))
    for host in self.cluster.hypervisors:
      STEP("Ensuring that there are atleast 5 login before test")
      for login in range(0, 5):
        self.dodin_obj.ahv_login_logout(host.ip, **kwargs)
      STEP("Trying to obtain last login info of %s" %host.ip)
      login_info = self.dodin_obj.get_AHV_login_info(host.ip, **kwargs)
      if len(login_info) != 2:
        assert False, "Last 2 login info display req not met!!!"
      else:
        INFO("As expected last 2 login info was displayed")

  def dodin_set_password_nutanix_ahv(self, **kwargs):
    """
    Args:
      kwargs
    Returns:
      Nothing
    Raises:
      assert
    """
    STEP("Attempting to set password on all nodes one by one")
    nutanix_pwd = kwargs.get("nutanix_pwd")
    for host in self.cluster.hypervisors:
      STEP("Attempting to set password for nutanix user on:%s" %host.ip)
      cmd_dump = self.dodin_obj.set_password_nutanix_ahv(host, **kwargs)
      INFO("Here's what command returned:%s"%cmd_dump)
      assert cmd_dump is not None, "setting password failed!!"
      STEP("Testing if nutanix user can logon and check \
        CPU_stat file presence: %s"%host.ip)
      kwargs.update({"password":nutanix_pwd})
      kwargs.update({"username":"nutanix"})
      exists_flag = self.dodin_obj.confirm_file_existence(host.ip, **kwargs)
      if not exists_flag:
        INFO("Was able to login and confirm file was not present")
      else:
        assert False, "nutanix user was able to login, but file check failed!"

  def dodin_cpu_stats_file_check(self, **kwargs):
    """
    Args:
      kwargs
    Returns:
      Nothing
    Raises:
      assert
    """
    filepath = kwargs.get("filepath", "/usr/local/bin/get_vm_cpu_stats")
    STEP("Attempting to confirm if %s exists" %filepath)
    INFO("This test would be run as %s"%kwargs.get("username"))
    for host in self.cluster.hypervisors:
      STEP("Trying to check on host: %s" %host.ip)
      exists_flag = self.dodin_obj.confirm_file_existence(host.ip, **kwargs)
      if not exists_flag:
        INFO("get_vm_cpu_stats file is not present as expected")
      else:
        assert False, "get_vm_cpu_stats is present!!"

  def dodin_version_check(self, **kwargs):
    """
    Args:
      kwargs
    Returns:
      Nothing
    Raises:
      assert
    """
    STEP("There are %s nodes in the cluster" % \
      len(self.dodin_obj.cluster.hypervisors))
    INFO("Check nutanix_privileged_command_version on all the nodes")
    INFO("This test would be run as %s"%kwargs.get("username"))
    for host in self.cluster.hypervisors:
      STEP("NTNX privileged cmd version of host: %s" %host.ip)
      content = self.dodin_obj.get_version_nutanix_privileged_cmd(host.ip, **kwargs)
      INFO("NTNX privileged command details : %s" %content)
      STEP("Ensuring the value returned is a numeral")
      try:
        version = int(content['stdout'].strip())
      except:
        raise Exception("Version returned is %s but number expected"%content)
      INFO("Version returned is %s and it is a numeral"\
        %content['stdout'].strip())
      return #happy at this point

  def dodin_enter_debug_mode(self, **kwargs):
    """
    Args:
      kwargs
    Returns:
      Nothing
    Raises:
      assert
    """
    check_service_failed_attempt = kwargs.get\
      ("check_service_failed_attempt", "no")
    if check_service_failed_attempt == "yes":
      INFO("This is a negative case")
      INFO("Will be checking service status, \
        in failed attempt to enter debug mode")
    INFO("There are %s nodes in the cluster" % \
      len(self.dodin_obj.cluster.hypervisors))
    for host in self.cluster.hypervisors:
      STEP("Trying to enter debug mode on: %s" %host.ip)
      self.dodin_obj.enter_debug_mode(host.ip, **kwargs)

  def dodin_network_script_restart(self, **kwargs):
    """
    Args:
      kwargs
    Returns:
      Nothing
    Raises:
      assert
    """
    INFO("There are %s nodes in the cluster" % \
      len(self.dodin_obj.cluster.hypervisors))
    INFO("Running this test on only one node")
    STEP("Trying to restart network on: %s" \
      %self.dodin_obj.cluster.hypervisors[0].ip)
    try:
      info = self.dodin_obj.network_service_restart\
        (self.dodin_obj.cluster.hypervisors[0].ip, **kwargs)
      if 'ignoring input and appending output to' in info['stdout']:
        INFO("Network service restart was successful")
      else:
        assert False, "restart command did not return expected info"
    except Exception: #pylint: disable=broad-except
      WARN("Could not restart network scripts on host!!!")
      assert False, "Test Failed"

  def dodin_erase_boot_sector(self, **kwargs):
    """
    Args:
      kwargs
    Returns:
      Nothing
    Raises:
      assert
    """
    operation = kwargs.get("operation")
    username = kwargs.get("username")
    password = kwargs.get("nutanix_pwd")
    reboot = kwargs.get("with_reboot")
    STEP("Attempting to erase boot sector!")
    if reboot == "yes":
      INFO("AHV host is expected not to boot after this step")
      self.dodin_obj.erase_boot_sector_api\
        (self.cluster.hypervisors[0].ip, username, password, reboot=True)
    else:
      INFO("AHV host is expected not to go down though boot sector erased")
      self.dodin_obj.erase_boot_sector_api\
        (self.cluster.hypervisors[0].ip, username, password, reboot=False)
      INFO("since host was erased without reboot, host is expected to be up")
      start_time = time.time()
      is_host_accessible = False #setting to false to begin with
      while time.time() < (start_time+120):
        is_host_accessible = self.cluster.hypervisors[0].is_accessible()
        if self.cluster.hypervisors[0].is_accessible():
          INFO("Waiting for a 10s to check status again")
          time.sleep(10)
          continue
        assert False, "unexpected!!! Host went down"
      INFO("despite erase without reboot, host is up as expected")
      return
    INFO("Erased the boot sector, checking if host is not bootable")
    time.sleep(30)
    retry = 0
    for retry in range(0, 2):
      INFO("Iter %s: Snoozing for 30s!!" %retry)
      time.sleep(30)
      try:
        is_host_accessible = self.cluster.hypervisors[0].is_accessible()
      except Exception: #pylint: disable=broad-except
        INFO("Host being not reachable is expected, retrying!")
      if is_host_accessible:
        break
    if is_host_accessible:
      assert False, "Unexpected, host came up after erase and reboot"
    else:
      INFO("Host did not come back approx 15 mins after erasing with reboot")

  def dodin_passwordless_sudo_check(self, **kwargs):
    """
    Args:
      kwargs
    Returns:
      Nothing
    Raises:
      assert
    """
    for host in self.cluster.hypervisors:
      INFO("host %s"%host.ip)
      STEP("Checking passwordless behaviour on host:%s" %host.ip)
      self.dodin_obj.passwordless_sudo_check(host.ip, **kwargs)

  def dodin_virsh_command_check(self, **kwargs):
    """
    Args:
      kwargs
    Returns:
      Nothing
    Raises:
      assert
    """
    for host in self.cluster.hypervisors:
      INFO("host %s"%host.ip)
      STEP("Checking if we can run virsh command:%s" %host.ip)
      #self._nutanix_virsh_command(host.ip, **kwargs)
      if not self.dodin_obj.virsh_command_check(host.ip, **kwargs):
        raise Exception("Could not run virsh command")

  def dodin_user_lock_out_check(self, **kwargs):
    """
    Args:
      kwargs
    Returns:
      Nothing
    Raises:
      assert
    """
    for host in self.cluster.hypervisors:
      INFO("host %s"%host.ip)
      STEP("Checking if user gets locked out in 3 \
        failed attempts on:%s" %host.ip)
      INFO("Attempting to ensure we can login at first")
      self.dodin_obj.user_login_check(host.ip, **kwargs)
      INFO("No exception seen, we are able to login")
      STEP("Attempting 3 tries with wrong password")
      kwargs_wrong_pwd = {
        "username" : kwargs.get("username"),
        "password" : "password@junk"
      }
      for attempt in range(0, 3):
        INFO("Attempt %s" %attempt)
        try:
          self.dodin_obj.user_login_check(host.ip, **kwargs_wrong_pwd)
        except Exception: #pylint: disable=broad-except
          INFO(Exception)
          INFO("Login failed as expected with wrong creds")
      STEP("Attempting to login with right creds after 3 failed attempts")
      try:
        self.dodin_obj.user_login_check(host.ip, **kwargs)
        assert False, "User was not locked out after 3 failed logins"
      except Exception: #pylint: disable=broad-except
        INFO(Exception)
        INFO("As expected user is locked out")
      STEP("Resetting user : %s"%kwargs.get("username"))
      self.dodin_obj.ahv_user_unlock(host.ip, **kwargs)
      STEP("Trying to login with right credentials after resetting")
      self.dodin_obj.user_login_check(host.ip, **kwargs)
      INFO("No exception seen, we are able to login")

  def dodin_api_default_password_check(self, **kwargs):
    """
    func to call default password check library call
    and validate its output
    Args:
      kwargs
    Returns:
      Nothing
    Raises:
      assert
    """
    default_password_set = kwargs.get("default_password_set", "yes")
    user_to_check = kwargs.get("user_to_check")
    STEP("Checking if default password is set for %s user"%user_to_check)
    username = kwargs.get("username")
    # INFO("Running this test as %s user and on one host" %username)
    # info = self.dodin_obj.check_default_password\
    #   (self.cluster.hypervisors[0].ip, user_to_check, **kwargs)
    if default_password_set == "yes":
      STEP("Changing password to nutanix/4u for testing!")
      self.dodin_obj.update_password_ahv_defaults(self.cluster.hypervisors[0].ip, user_to_check)
      INFO("Running this test as %s user and on one host" %username)
      info = self.dodin_obj.check_default_password\
        (self.cluster.hypervisors[0].ip, user_to_check, **kwargs)
      INFO("ignoring exception as this is expected for default passwd usage")
      assert ('has a default password set' in info), \
        "API could not detect default password set!"
      INFO("API successfully detected default password set")
      STEP("Reverting password to non-default after testing!")
      self.dodin_obj.revert_password_ahv_defaults(self.cluster.hypervisors[0].ip, user_to_check)
    if default_password_set == "no":
      INFO("Running this test as %s user and on one host" %username)
      info = self.dodin_obj.check_default_password\
        (self.cluster.hypervisors[0].ip, user_to_check, **kwargs)
      assert ('does not have a default password set' in info), \
        "API could not detect default password set!"
      INFO("API successfully detected default password not set")

  def dodin_enable_dodin_using_script(self, **kwargs):
    """
    func to call enable dod using script
    Args:
      kwargs
    Returns:
      Nothing
    Raises:
      assert
    """
    status = self.dodin_obj.enable_dod_wf_using_script(**kwargs)
    if status:
      INFO("Dod enabled successfully")
    else:
      ERROR("Enabling dod workflow failed")
      assert False, "Enable dodin test failed"

  def dodin_disable_dodin_using_script(self, **kwargs):
    """
    func to call disable dod using script
    Args:
      kwargs
    Returns:
      Nothing
    Raises:
      assert
    """
    status = self.dodin_obj.disable_dodin_via_script(**kwargs)
    if status:
      INFO("Dod disabled successfully")
    else:
      ERROR("Disabling dod workflow failed")
      assert False, "disable dodin test failed"
