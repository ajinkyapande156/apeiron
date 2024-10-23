"""
Copyright (c) 2022 Nutanix Inc. All rights reserved.

Author: umashankar.vd@nutanix.com

Dodin phase specific library
"""
#pylint: disable=no-self-use, invalid-name, using-constant-test, no-else-return
# pylint: disable=unused-variable, unused-import, no-member
# pylint: disable=too-many-branches, too-many-statements, unused-argument
# pylint: disable=ungrouped-imports, line-too-long, too-many-locals
# pylint: disable=broad-except, singleton-comparison
import re
import time
import json
from pprint import pprint
from pexpect import pxssh
try:
  from framework.lib.nulog import INFO, WARN, ERROR, \
  STEP
  EXECUTOR = "nutest"
except Exception:  # pylint: disable=broad-except
  from libs.ahv.framework.proxy_logging \
  import INFO, ERROR, STEP
  EXECUTOR = "mjolnir"
import framework.operating_systems.operating_system.linux_operating_system \
  as LinuxOperatingSystem
from framework.entities.cluster.nos_cluster import NOSCluster
from framework.entities.vm.vm import Vm
from libs.framework import mjolnir_entities as entities
from libs.feature.vm_lib.vm_factory import VmFactory
from libs.workflows.generic.vm.acli import AcliVm
from workflows.acropolis.ahv.platform.ahv.workflows.platform_qualification.lib.cluster_helper import \
  ClusterHelper
from workflows.acropolis.ahv.platform.ahv.workflows.platform_qualification.lib.failure_ops import FailureOps

class DodinPhase4Libs():
  """
  This class is to provide core library for
  Dodin phase 4 test coverage
  """

  def __init__(self, cluster, **kwargs):
    """
    Function to initialize library
    Enables dodin mode on cluster by default,
    if already enabled then skips it
    Args:
      cluster (object): Nos object
    """
    self.nutant_pwd = "RDMCluster.123"
    self.root_pwd = "RDMCluster.123"
    self.nutanix_pwd = kwargs.get("nutanix_pwd")
    self.cluster = cluster
    #commenting the legacy way of enabling dod
    #added dedicated tests for this
    #self._enable_dodin_mode(enable_ahv_gflag=False)
    self.svm_to_run_script = self.cluster.get_accessible_svm()

  def enable_dod_wf_using_script(self, **kwargs):
    """
    Args:
      kwargs : list of args
    Raises:
      Nothing
    Returns:
      Nothing
    """
    if self._dodin_enabled_check():
      INFO("Skipping enable Dodin as it is  already enabled")
      return False
    else:
      if self.nutanix_pwd:
        STEP("Trying to set password for nutanix user")
        password = self.nutanix_pwd
        INFO("Password to be set from config : %s" %password)
        cmd = "echo '%s' | sudo passwd --stdin nutanix" %password
        for host in self.cluster.hypervisors:
          stdout = self.execute_on_host(host.ip, cmd, "root", self.root_pwd)
      return self.enable_dodin_via_script(**kwargs)

  def enter_debug_mode(self, host_ip, **kwargs):
    """
    Args:
      host_ip (str): Host for debug mode check
      kwargs(json): args from config
    Raises:
      assert : if unable to enter debug mode
    Returns:
      Nothing
    """
    username = kwargs.get("username")
    password = kwargs.get("nutanix_pwd")
    terminate_before_passwd = kwargs.get("negative", "no")
    try:
      before_test = self.debug_mode_service_status(host_ip, username, password)
      INFO("This test is run as: %s"%username)
      conn = pxssh.pxssh()
      STEP("Logging into the host")
      conn.login(host_ip, username, password)
      STEP("Sending the command to enter debug mode")
      conn.sendline("sudo /usr/bin/start_debug_mode.sh")
      conn.prompt(timeout=60)
      STEP("Expecting password to be prompted")
      if b'[sudo] password for nutanix' not in conn.before:
        assert False, "Password for nutanix user was not prompted"
      INFO("Password prompted for %s user, will enter and proceed" %username)
      conn.sendline(password)
      conn.prompt()
      STEP("Checking if prompted to Keyin YES to enter debug mode")
      INFO(conn.before)
      if b"system for 1 hour. [ yes, no ]:" not in conn.before:
        assert False, "Could not enter debug mode"
      conn.sendline("yes")
      conn.prompt()
      STEP("Checking if prompted to enter ID")
      INFO(conn.before)
      if b'Enter an associated Nutanix support ticket number to continue:' \
        not in conn.before:
        assert False, "Expected prompt to key in ticket number"
      conn.sendline("123")
      conn.prompt()
      STEP("Checking if prompted for root password")
      INFO(conn.before)
      if b'continue connecting' in conn.before:
        INFO("Prompted to accept fingerprint")
        conn.sendline('yes')
        conn.prompt()
      if b"password:" not in conn.before:
        assert False, "Expected password prompt"
      if terminate_before_passwd == "yes":
        STEP("Terminating attempt without keying in password")
        conn.close()
        after_test = self.debug_mode_service_status(host_ip, username, password)
        INFO("Expecting debug service to be down")
        assert after_test, "Service status not as expected"
        return
      conn.sendline(self.root_pwd)
      conn.prompt()
      INFO(conn.before)
      STEP("Checking if in root user mode")
      if b"[root@" not in conn.before:
        assert False, "Not in root mode"
      INFO("Entered debug mode successfully on:%s!!!" %host_ip)
      INFO("Here's the entire command behavior")
      INFO(conn.before)
      STEP("Verifying sshd_debug service status")
      assert not self.debug_mode_service_status(host_ip, username, password), \
        "sshd_service is runinng!!"
      INFO("As expected service is down, while in debug mode")
      STEP("Exiting debug mode by logging out as root")
      conn.sendline("exit")
      conn.prompt()
      # STEP("Verifying sshd_debug service on exit")
      # time.sleep(5)
      # assert not self.debug_mode_service_status(host_ip, username, password), \
      #   "sshd_service is running upon exit!!"
      # INFO("sshd_service is not running as expected")
      # STEP("closing the connection on %s" %host_ip)
      # conn.close()
    except Exception: #pylint: disable=broad-except
      WARN("unexpected debug mode behavior seen")
      assert False, "Debug mode test failed!!"

  def debug_mode_service_status(self, host_ip, username, password):
    """
    This func returns status of the service
    for debug mode, active meaning it is in debug mode
    an exit from debug mode should see this in dead state
    Args:
      host_ip (str): ip addr
      username (str): name of the user
      password (str): password to be used
    Returns:
      True or False
    """
    INFO("Fetching sshd_debug service status")
    conn_status = pxssh.pxssh()
    conn_status.login(host_ip, username, password)
    conn_status.sendline("systemctl status sshd_debug")
    conn_status.prompt()
    INFO("service check cmd output:%s"%conn_status.before)
    if (b'active (running)' in conn_status.before) and \
      (b'inactive (dead)' not in conn_status.before):
      conn_status.close()
      return True
    conn_status.close()
    return False

  def get_password_set_status(self, ip, password, username='nutant'):
    """
    This function helps to check if password is set for nutanix user
    Args:
      ip (str) : ip addr
      password (str) : password for nutant user
      username (str) : nutant by default
    Returns:
      boolean
    """
    INFO("checking if password is set for nutanix user")
    cmd_to_check_pwd_status = "sudo grep nutanix /etc/shadow"
    info = self.execute_on_host(ip, cmd_to_check_pwd_status, username, password)
    INFO("password check command returned:%s"%info)
    if '!!' in info['stdout'].split(":"):
      return False
    return True

  def network_script_validation(self, host_ip, **kwargs):
    """
    this functions returns the contents of network scripts
    Args:
      host_ip (str): Host on which user to be unlocked
    Raises:
      Nothing
    Returns:
      stdout (str): returns what command returned
    """
    password = kwargs.get("nutanix_pwd")
    username = kwargs.get("username")
    #self.hh = DoDINHostHelper(self.cluster)
    cmd = "ls -laZ /etc/sysconfig/network-scripts/ifcfg-br0"
    #stdout = self.hh.execute_on_host(cmd)
    INFO("Running network script validation as %s user" %username)
    stdout = self.execute_on_host(host_ip, cmd, username, password)
    #stdout = ahv_ssh_int.execute(cmd)
    return stdout

  def get_version_nutanix_privileged_cmd(self, host_ip, **kwargs):
    """
    this function would return the nutanix-privileged-command
    attributes
    Args:
      host_ip (str): Host to get privileged cmd whitelist version
    Raises:
      Exception
    Returns:
      stdout (str)
    """
    password = kwargs.get("nutanix_pwd")
    username = kwargs.get("username")
    cmd = 'nutanix_privileged_cmd --whitelist-version'
    #version validation is not done as of now
    stdout = self.execute_on_host(host_ip, cmd, username, password)
    return stdout

  def set_password_nutanix_ahv(self, host, **kwargs):
    """
    login as nutant user
    set password for nutanix user
    cannot use Dodin@123 or Nutanix.123
    Args:
      host (object): Host object on which password to be set
      kwargs(json): args from config
    Raises:
      Exception
    Returns:
      stdout (str): None if command failed to set password
    """
    password = kwargs.get("nutanix_pwd")
    INFO("Here's the password being set: %s" %password)
    hard_check = kwargs.get("hard_check", "no")
    cmd = "echo '"+ password +"' | sudo passwd --stdin nutanix"
    try:
      if not self.get_password_set_status(host.ip, password=self.nutant_pwd)\
       and hard_check == 'yes':
        INFO("Password for nutanix user is not set on:%s"%host.ip)
      else:
        INFO("Password is set for nutanix user on:%s"%host.ip)
      stdout = self.execute_on_host(host.ip, cmd, "nutant", self.nutant_pwd)
      INFO("Running the command on the host ip:%s and name:%s as nutant user" \
        %(host.ip, host.name))
      INFO(stdout)
    except Exception as ex: #pylint: disable=broad-except
      stdout = None
      WARN(ex)
      WARN("Attempt to set password for nutanix user could have failed!!")
    return stdout

  def virsh_command_check(self, host_ip, **kwargs):
    """
    Login as nutanix user
    Try to run virsh command
    expected to run without failure
    Args:
      host_ip (str): Host on which virsh command to be checked
      kwargs(json): args from config
    Raises:
      Nothing
    Returns:
      Nothing
    """
    username = kwargs.get("username")
    password = kwargs.get("nutanix_pwd")
    cmd = "virsh -list"
    #stdout, stderr, _ = self.execute_on_host(host_ip, cmd, username, password)
    STEP("Establishing connection as: %s"%username)
    conn = pxssh.pxssh()
    conn.login(host_ip, username, password)
    conn.sendline(cmd)
    conn.prompt()
    INFO("Here's what the command returned:%s"%conn.before)
    if b'virsh' in conn.before:
      INFO("Successfully entered virsh prompt")
      virsh_entered_status = True
    else:
      WARN("Looks like we could not enter Virsh prompt")
      virsh_entered_status = False
    conn.close()
    return virsh_entered_status

  def get_AHV_login_info(self, host_ip, **kwargs):
    """
    Login as Nutanix user onto host
    returns login info for validation
    Args:
      host_ip (str): Host on which login info to be obtained
      kwargs(json): args from config
    Raises:
      Nothing
    Returns:
      Nothing
    """
    cmd = "echo 'trying to fetch login info'"
    pattern = "Last login:"
    username = kwargs.get("username")
    password = kwargs.get("nutanix_pwd")
    ahv_conn = LinuxOperatingSystem.LinuxOperatingSystem\
      (host_ip, username, password)
    int_conn = ahv_conn.get_interactive_channel()
    ahv_conn.send_to_interactive_channel(cmd, int_conn)
    ahv_login_info = ahv_conn.receive_from_interactive_channel(int_conn)
    ahv_conn.close_interactive_channel(int_conn)
    INFO(ahv_login_info)
    INFO([(pattern, m.start(), m.end()) for m in re.finditer\
      (pattern, ahv_login_info)])
    return ([(pattern, m.start(), m.end()) for m in re.finditer\
      (pattern, ahv_login_info)])

  def ahv_login_logout(self, host_ip, **kwargs):
    """
    This function is to simply login and logout
    Helps in user lock out tests and login info
    validation tests
    Args:
      host_ip (str): Host on which login/logout to be performed
      kwargs(json): args from config
    Raises:
      Nothing
    Returns:
      Nothing
    """
    username = kwargs.get("username")
    password = kwargs.get("nutanix_pwd")
    cmd = "echo 'dry login'"
    ahv_conn = LinuxOperatingSystem.LinuxOperatingSystem\
      (host_ip, username, password)
    int_conn = ahv_conn.get_interactive_channel()
    ahv_conn.send_to_interactive_channel(cmd, int_conn)
    ahv_login_info = ahv_conn.receive_from_interactive_channel(int_conn)
    ahv_conn.close_interactive_channel(int_conn)
    INFO("Login successful!")
    time.sleep(20)

  def ahv_user_unlock(self, host_ip, **kwargs):
    """
    Args:
      host_ip (str): Host on which user to be unlocked
      kwargs(json): args from config
    Raises:
      Nothing
    Returns:
      Nothing
    """
    username = kwargs.get("username", "nutant")
    password = kwargs.get("password", self.nutant_pwd)
    user_to_be_unlocked = kwargs.get("user_to_unlock", "nutanix")
    INFO("Trying to unlock %s user"%user_to_be_unlocked)
    cmd_to_unlock = "sudo faillock --user " + user_to_be_unlocked + " --reset"
    conn = pxssh.pxssh()
    conn.login(host_ip, "nutant", self.nutant_pwd)
    conn.sendline(cmd_to_unlock)
    conn.prompt()
    INFO("What transcribed during pwd reset: %s"%conn.before)
    conn.close()

  def user_login_check(self, host_ip, **kwargs):
    """
    Args:
      host_ip (str): Host to check user login
      kwargs(json): args from config
    Returns:
      Nothing
    Raises:
      Nothing
    """
    username = kwargs.get("username", "nutant")
    password = kwargs.get("nutanix_pwd", self.nutant_pwd)
    conn = pxssh.pxssh()
    conn.login(host_ip, username, password)
    conn.close()

  def passwordless_sudo_check(self, host_ip, **kwargs):
    """
    Login to ahv as Nutanix user
    Try running a command as sudo
    Expected behavior - it should prompt for password
    Args:
      host_ip (str): Host to test passwordless check
      kwargs(json): args from config
    Returns:
      Nothing
    Raises:
      Nothing
    """
    username = kwargs.get("username")
    password = kwargs.get("nutanix_pwd")
    STEP("trying to check if passwordless sudo is disabled")
    INFO("To achive this check, trying to create file in /var/www/html")
    timestr = time.strftime("%Y%m%d-%H%M%S")
    cmd = "sudo mkdir /var/test_%s"%timestr
    conn = pxssh.pxssh()
    conn.login(host_ip, username, password)
    conn.sendline(cmd)
    conn.prompt()
    if b'[sudo] password for ' in conn.before:
      INFO("Prompted password")
      INFO("on host: %s - passwordless sudo is disabled" %host_ip)
      conn.sendline(password)
      conn.prompt()
      INFO("Password keyed and now here's the entire command behavior")
      INFO(conn.before)
    else:
      WARN("here's what command returned:%s"%conn.before)
      INFO("it appears file was created without password prompting")
      conn.sendline("exit")
      conn.prompt()
      assert False, "Test failed"

  def erase_boot_sector_api(self, host_ip, username, password, reboot=True):
    """
    Args:
      host_ip (str): ip addr of host to erase boot sector
      username (str): username to login to host
      password (str): password to login to host
      reboot (boolean): True to reboot after erase, False dont reboot
    Returns:
      Nothing
    Raises:
      Nothing
    """
    cmd = "nutanix_privileged_cmd /usr/libexec/disable_auto_boot.sh -f"
    if reboot:
      cmd += " -r"
    INFO("cmd to be run is:%s" %cmd)
    erase_api_return = self.execute_on_host(self.cluster.hypervisors[0].ip, \
                                       cmd, username, password)
    INFO(erase_api_return)
    if 'Successfully disabled automatic booting into AHV' in \
      erase_api_return['stdout']:
      INFO("Successfully erased boot sector")
      if reboot:
        INFO("Since this is erase with reboot, need additional validation")
        if 'Rebooting the system. The system will not come up automatically anymore!' in erase_api_return['stdout']:
          INFO("erase with reboot successfully done")
        else:
          assert False, "Erase boot sector with reboot did not return \
            expected message"
    else:
      assert False, "Erase boot sector api did not return success!"

  def confirm_file_existence(self, host_ip, **kwargs):
    """
    function to confirm presence of file at specified location
    returns:
      true or false
    Args:
      host_ip (str): Ip addr
      kwargs(json): args from config
    Returns:
      exists_flag : True if file is present
    """
    username = kwargs.get("username")
    password = kwargs.get("nutanix_pwd")
    file_path = kwargs.get("filepath", "/usr/local/bin/get_vm_cpu_stats")
    #cmd = "test -f "+ file_path + " && echo 'File exists'"
    cmd = "[ ! -f "+ "'" + file_path + "' ]" + "&& echo 'File not present'"
    ahv_ssh_int = self.execute_on_host(host_ip, cmd, username, password)
    #stdout = ahv_ssh_int.execute(cmd)
    INFO(ahv_ssh_int)
    if (ahv_ssh_int['stdout'] == "File not present\r\n") \
      & ahv_ssh_int['status'] == 0:
      exists_flag = False
    else:
      exists_flag = True
    return exists_flag

  def network_service_restart(self, host_ip, **kwargs):
    """
    Args:
      host_ip (str): ip addr of host where network needs restart
    Returns:
      ahv_ssh_int(str): var for holding result of cmd execution
    Raises:
      Nothing
    """
    username = kwargs.get('username')
    password = kwargs.get('nutanix_pwd')
    INFO("running the test as %s user:" %username)
    cmd = "nutanix_privileged_cmd /usr/bin/nohup /usr/bin/systemctl \
      restart network"
    ahv_ssh_int = self.execute_on_host(self.cluster.hypervisors[0].ip, \
      cmd, username, password)
    #stdout = ahv_ssh_int.execute(cmd)
    INFO(ahv_ssh_int)
    return ahv_ssh_int

  def dodin_regression(self, test, **kwargs):
    """
    Args:
      kwargs (json): input json from config
      test (str): specifies type of test - cg, vtpm, wsl
    Returns:
      Nothing
    Raises:
      Nothing
    """
    vm_type = kwargs.get("vm_type", "uefi")
    if test == 'cg':
      INFO(kwargs)
      self.cg_vm = VmFactory("sb", **kwargs)
    elif test == 'vtpm':
      self.vtpm_vm = VmFactory(vm_type, **kwargs)
    else:
      self.wsl = VmFactory(vm_type, **kwargs)
    STEP("Performing power operations on the guest:%s" %test)

    STEP("Adding disk for running FIO")

    STEP("Running FIO on guest: %s" %test)

  def execute_on_host(self, ip, cmd, username, password):
    """
    Establish connection using ssh and specified user
    returns:
      connection objection
    Args:
      ip (str): ip addr
      cmd (str): Command to be run
      username (str) : username to login
      password (str) : password to login
    Returns:
      execution result of cmd provided
    """
    ahv_conn = LinuxOperatingSystem.LinuxOperatingSystem\
      (ip, username, password)
    INFO("Established connection as: %s " %username)
    return ahv_conn.execute(cmd)

  def get_gflags_status(self):
    """
    Args:
      Nothing
    Returns:
      Nothing
    Raises:
      Nothing
    """

  def create_nutant_user(self):
    """
    This we can leverage _enable_dodin_mode func
    Args:
      Nothing
    Returns:
      Nothing
    Raises:
      Nothing
    """

  def check_default_password(self, host_ip, user_to_be_tested, **kwargs):
    """
    This func is to check if a user is set with default
    password
    Args:
      host_ip (str): ip addr
      user_to_be_tested (str): user name under test
      kwargs (json): args for test
    Returns:
      str :string returned by API
    """
    username = kwargs.get("username")
    password = kwargs.get("nutanix_pwd")
    INFO("This call is run as %s user" %username)
    cmd = "nutanix_privileged_cmd /usr/libexec/check_no_default_password.py " + user_to_be_tested
    STEP("Testing default password for %s user"%user_to_be_tested)
    try:
      return self.execute_on_host(host_ip, cmd, username, password)['stdout']
    except Exception as ex: #pylint: disable=broad-except
      INFO("printing exception from library:%s"%ex)
      return str(ex)

  def update_password_ahv_defaults(self, host_ip, username):
    """
    This func will set default password to nutanix/4u
    Args:
      host_ip (str): ip addr
      username (str): user name under test
    Returns:
      json :returned by execute func
    """
    cmd = """echo "%s:nutanix/4u" | sudo chpasswd"""%username
    return self.execute_on_host(host_ip, cmd, "nutant", "RDMCluster.123")

  def revert_password_ahv_defaults(self, host_ip, username):
    """
    This func will revert set default password to RDMCluster.123
    Args:
      host_ip (str): ip addr
      username (str): user name under test
    Returns:
      json :returned by execute func
    """
    cmd = """echo "%s:RDMCluster.123" | sudo chpasswd"""%username
    return self.execute_on_host(host_ip, cmd, "nutant", "RDMCluster.123")

  def enable_dodin_via_script(self, **kwargs):
    """
    Args:
      Nothing
    Returns:
      boolean
    Raises:
      assertion : in case enable dod step fails
    """
    #setting up pre-dodin steps
    #creating nutant user with RDMCluster.123 as pwd
    ahv_admin_pwd = kwargs.get("ahv_admin_password", "RDMCluster.123")
    rsyslog_required = kwargs.get("rsyslog_required", 'yes')

    #creating nutant user
    INFO("Creating nutant user and touch file for reference")
    nutant_user = self.cluster.execute("hostssh '/usr/libexec/add_ahv_test_user.sh -f RDMCluster.123 nosshkey'")
    INFO(nutant_user['stdout'])
    #creating nutant user touch file
    INFO("creating touch files for nutant user")
    touchfile = self.cluster.execute("touch /home/nutanix/.ahv_nutant_user_created", on_all_svms=True)
    INFO(touchfile)
    #setting up dedicated rsyslog server
    if rsyslog_required == 'yes':
      STEP("Setting up dedicated rsyslog server")
      rsyslog_ip = self._setup_dedicated_rsyslog_server(**kwargs)
      INFO("Here's the rsyslog server : %s" %rsyslog_ip)
      cmd_enable_dod = "configure_dod_mode.sh enter_dod_mode -p=%s -r=ahv-rsyslog-test.eng.nutanix.com\
          -ca=/home/nutanix/ca.pem --auth-mode=x509/name --permitted-peers=ahv-rsyslog-test.eng.nutanix.com --no-reboot" %(ahv_admin_pwd)
    else:
      #I am not worried here about rsyslog setup
      cmd_enable_dod = "touch ca.crt && configure_dod_mode.sh enter_dod_mode -p=%s -r=1.1.1.1 -ca=ca.crt --auth-mode=FIXME --permitted-peers=FIXME --no-reboot" %ahv_admin_pwd
    STEP("Setting up dod on the cluster")
    INFO(cmd_enable_dod)
    response = self.cluster.execute(cmd_enable_dod, svm=self.svm_to_run_script, timeout=1800, ignore_errors=True)
    INFO("Response : {}".format(response))

    #checking if the command ran successfully without errors
    #in case of any errors then the status would be non-zero

    assert response['status'] == 0, "Command to enable dod failed to execute : %s" %response

    if "dod mode is already enabled" in response['stdout']:
      INFO('Dod is already enabled on the cluster')
      return False

    log_response = self.cluster.execute("cat /home/nutanix/data/logs/configure_dod_mode.log", svm=self.svm_to_run_script)
    INFO("DOD LOG : {}".format(log_response["stdout"]))

    #verifying output of the script
    text_readable = re.sub(r'\x1b\[[0-9;]*[mG]', '',
                           str(response['stdout']))
    pattern = re.compile(r'(.*?)\s+\[\s+(OK|FAILED)\s+\]')
    matches = re.findall(pattern, text_readable)
    dod_step_details = {key.strip(): value.strip() for key, value in matches}
    INFO(dod_step_details)
    failed_steps = []
    for step, status in dod_step_details.items():
      if status == "FAILED":
        if step not in ["Install virus scanner",
                        "Setting up Rsyslog Forwarding"]:
          failed_steps.append(step)
    if failed_steps:
      ERROR("DoDIN enablement failed at {}\n.".format(",".join(failed_steps)))
      assert False, "Failed to enable dod, some steps FAILED!"
    #rolling reboot
    self.rolling_reboot_hosts()
    wait_time = 10*60
    INFO("Waiting for {} secs for DODIN settings to sync.".format(wait_time))
    time.sleep(wait_time)
    INFO("DoDIN mode enabled successfully on cluster %s" % self)

    #creating touch for dodin
    INFO("creating dod enabled touch file")
    self.cluster.execute("touch /home/nutanix/.dodin_enabled", on_all_svms=True)
    INFO("setting up default password file")
    self.cluster.execute("echo 'RDMCluster.123' > /home/nutanix/.use_default_ntnx_sudo_pwd", on_all_svms=True)
    #touch file for script on all SVM's
    INFO("Setting up touch file for scripts to understand dod is enabled")
    self.cluster.execute("touch /home/nutanix/.dod_mode_enabled", on_all_svms=True)
    return True

  def disable_dodin_via_script(self, **kwargs):
    """
    Args:
      Nothing
    Returns:
      boolean
    Raises:
      Nothing
    """
    #gathering info from config
    ahv_admin_pwd = kwargs.get("ahv_admin_password", 'RDMCluster.123')
    cvm_nutanix_pwd = kwargs.get("cvm_nutanix_password", 'RDMCluster.123')
    #Execution
    STEP("Attempting to disable dod")
    INFO("running the script to disable dod")
    INFO("Turning off sudo so that disable dod wont prompt password")
    cmd = "echo 'RDMCluster.123' | sudo --stdin /srv/salt/statechange ntnxusersudoauth off"
    self.cluster.execute(cmd, on_all_svms=True)
    cmd_disable_dod = "configure_dod_mode.sh leave_dod_mode --ahv_admin_pw=%s --cvm_nutanix_pw=%s" \
      %(ahv_admin_pwd, cvm_nutanix_pwd)
    INFO("Here's the command run : %s" %cmd_disable_dod)
    svm_to_run_script = self.cluster.get_accessible_svm()
    response = self.cluster.execute(cmd_disable_dod, svm=svm_to_run_script, timeout=900, ignore_errors=True)
    steps = response['stdout'].split('\r\n')
    if 'dod mode was not enabled' in response['stdout']:
      ERROR("Dod is not enabled on the cluster")
      return False
    for step in steps:
      INFO(step)
    #removing marker file
    self.cluster.execute("mv /home/nutanix/.dod_mode_enabled /home/nutanix/.dod_mode_disabled", on_all_svms=True)
    for step in steps:
      if 'FAILED' in step:
        flag = False
        break
      flag = True
    return flag

    #disabling rsyslog server config:Yet to be implemented

  def rolling_reboot_hosts(self):
    """
    Rolling reboot hosts genesis workflow

    Returns:
      task_id(str): Task id to monitor rolling reboot of hosts
    """
    INFO("Rolling reboot hosts genesis workflow")
    cmd = "source /etc/profile; yes | rolling_restart -h"
    result = self.cluster.execute(cmd)
    assert "ERROR" not in result, "Failed to start rolling reboot"
    task = re.search(r'ecli task.get [\w-]*', result['stdout']).group()
    task_id = task.split(" ")[-1]
    self.monitor_rolling_reboot_hosts(task_id=task_id,
                                      timeout=7200)
    return task_id

  def monitor_rolling_reboot_hosts(self, task_id, timeout=3600):
    """
    Monitor rolling reboot of hosts

    Args:
      task_id(str): Task ID to track rolling reboot
      timeout(int): Task timeout

    Returns:

    Raises:
      (Exception): If rolling reboot fails
    """
    STEP("Monitor rolling reboot of hosts")
    cluster_helper = ClusterHelper(cluster=self.cluster)
    err_msg = ""
    end_time = time.time() + timeout
    while time.time() < end_time:
      try:
        cmd = "source /etc/profile; " + "ecli task.get " + task_id
        result = self.cluster.execute(cmd)
        output = json.loads(result['stdout'])
        INFO("Hypervisor rolling restart status: %s" % output['status'])
        if "hypervisor rolling restart" in output["operation_type"].lower() \
            and output["status"] == "kRunning":
          INFO("Output: %s" % output)
        elif output["status"] == "kFailed":
          err_msg = "Hypervisor rolling restart operation failed, output: %s" \
                    % output
          break
        elif output["status"] == "kSucceeded":
          INFO("Hypervisor rolling restart operation Succeeded")
          return
      except Exception as ex:
        ERROR(ex)
      time.sleep(300)
    if len(err_msg) == 0:
      err_msg = "Timed out waiting to monitor rolling reboot of hosts in %ss" \
                % timeout
    raise Exception(err_msg)

  def _setup_dedicated_rsyslog_server(self, **kwargs):
    """
    Args:
      Nothing
    Returns:
      string : ip address of the rsyslog server
    Raises:
      Nothing
    """
    STEP("setting up dedicated rsyslog server with encryption")
    INFO("Checking if rsyslog server is already present")
    vm = AcliVm(self.cluster, interface_type="ACLI", **kwargs)
    VM_exist = vm.get_vm_present(name='rsyslog_server')
    if VM_exist == None:
      INFO("A local uvm would be used for log forwarding")
      INFO("Downloading relevant scripts")
      resp = self.cluster.execute("wget http://10.48.209.6/configure_dod_script/prepare_dod_requirements.sh",
                                  timeout=60, ignore_errors=True, on_all_svms=True)
      INFO(resp)
      resp = self.cluster.execute("wget http://10.48.209.6/configure_dod_script/rsyslog_encrypted_setup.sh",
                                  timeout=60, ignore_errors=True, on_all_svms=True)
      INFO(resp)
      resp = self.cluster.execute("wget http://10.48.209.6/configure_dod_script/lib.sh",
                                  timeout=60, ignore_errors=True, on_all_svms=True)
      INFO(resp)
      INFO("Running script to setup rsyslog environment")

      #running script to setup rsyslog server
      perm = self.cluster.execute("sudo chmod 777 prepare_dod_requirements.sh", on_all_svms=True)
      self.cluster.execute("sudo chmod 777 rsyslog_encrypted_setup.sh", on_all_svms=True)
      INFO(perm)
      #svm_to_run_script = self.cluster.get_accessible_svm()
      response = self.cluster.execute("./prepare_dod_requirements.sh",
                                      svm=self.svm_to_run_script,
                                      timeout=900, ignore_errors=True)

      INFO("Response : {}".format(response))
      pattern = r'Rsyslog Server:  \(IP\s*(\d{1,3}(?:\.\d{1,3}){3})\)'
      matches = re.findall(pattern, response['stdout'])
      # log_response = self.cluster.execute("cat /home/nutanix/data/logs/configure_dod_mode.log", svm = svm_to_run_script)
      # INFO("rsyslog setup : {}".format(log_response["stdout"]))
      return matches[0]
    #if vm exists then fetch its IP
    else:
      rsyslog_server = vm.bind_vm_present(name='rsyslog_server')
      return rsyslog_server.vm_ip()

  def _dodin_enabled_check(self):
    """
    Args:
      Nothing
    Returns:
      boolean
    Raises:
      Nothing
    """
    #setting first time password for nutanix
    INFO("Checking if DOD is enabled before attempting to set pwd for nutanix")
    if self.cluster.svms[0].exists("/home/nutanix/.dodin_enabled"):
      INFO("Skipping DODIN enablement on %s, Already enabled." % self.cluster.name)
      return True
    INFO("Dodin is not enabled on %s" %self.cluster.name)
    return False

  def _ahv_gflag_check(self):
    """
    Func to return true or false based on general check
    of flags present
    Args:
      Nothing
    Returns:
      Nothing
    Raises:
      Nothing
    """
    cmd = "allssh 'cat ~/config/*.gflags'"
    INFO("This command can be run from any CVM")
    INFO("Chosing to run the command on first CVM : %s"\
      %self.cluster.svm_ips[0])
    conn = pxssh.pxssh()
    conn.login(self.cluster.svm_ips[0], "nutanix", "RDMCluster.123")
    conn.sendline(cmd)
    conn.prompt()
    INFO("Here are the gflags set")
    pprint(conn.before)
    if b'No such file or directory' in conn.before:
      return False
    else:
      return True

  def _enable_host_gflags(self):
    """
    Function to enable glags, on need basis call func to set all glags
    from list
    Args:
      Nothing
    Returns:
      Nothing
    Raises:
      Nothing
    """
    gflags = ['allssh \'echo -e "--hypervisor_username=nutanix" >> \
    /home/nutanix/config/genesis.gflags\'',
              'allssh \'echo -e "--hypervisor_username=nutanix" >> \
    /home/nutanix/config/acropolis.gflags\'',
              'allssh \'echo -e "--use_kvm_ssh_client=true" >> \
    /home/nutanix/config/acropolis.gflags\'',
              'allssh \'echo -e "--hypervisor_username=nutanix" >> \
    /home/nutanix/config/cluster_health.gflags\'',
              'allssh \'echo -e --ahv_enable_file_integrity_ncc_check=true >> \
    /home/nutanix/config/cluster_health.gflags\'',
              'allssh \'echo -e --ahv_enable_remote_log_forwarding_ncc_check=\
              true >> /home/nutanix/config/cluster_health.gflags\'',
              'allssh \'echo -e --cvm_enable_file_integrity_ncc_check=true >> \
    /home/nutanix/config/cluster_health.gflags\'',
              'allssh \'echo -e --enable_rsyslog_forwarding_check=true >> \
    /home/nutanix/config/cluster_health.gflags\'']
    STEP("Enabling gflag on cluster")
    INFO("This settings can be done from any CVM")
    INFO("These flags would be set:%s" %gflags)
    conn = pxssh.pxssh()
    conn.login(self.cluster.svm_ips[0], "nutanix", "RDMCluster.123")
    for gflag in gflags:
      conn.sendline(gflag)
      conn.prompt()
      INFO("setting gflag: %s, returned"%gflag)
      INFO(conn.before)

  def _enable_dodin_mode(self, enable_ahv_gflag=True, **kwargs):
    """
    Args:
      enable_ahv_gflag (boolean): True enables gflags
    Returns:
      Nothing
    Raises:
      Nothing
    """
    #setting first time password for nutanix
    INFO("Checking if DOD is enabled before attempting to set pwd for nutanix")
    if self.cluster.svms[0].exists("/home/nutanix/.dodin_enabled"):
      INFO("Skipping DODIN enablement on %s, Already enabled." % self)
      return
    INFO("Trying to set password for nutanix user")
    password = self.nutanix_pwd
    INFO("Password to be set from config : %s" %password)
    cmd = "echo '%s' | sudo passwd --stdin nutanix" %password
    for host in self.cluster.hypervisors:
      stdout = self.execute_on_host(host.ip, cmd, "root", self.root_pwd)
    #Trying to enable dod default wf as RDM
    self.cluster.enable_dod_mode(enable_sudo=True, enable_ahv_nutant_user=True)
    self.cluster.enable_ssh_sudo_access()
    INFO("checking if necessary flags are present")
    # gflag_status = self._ahv_gflag_check()
    # if gflag_status:
    #   INFO("gflags are set!")
    #   return
    if enable_ahv_gflag:
      INFO("glags are not set, doing it now!")
      self._enable_host_gflags()
      INFO("Checking the gflag status after enabling it!")
      if self._ahv_gflag_check:
        INFO("gflags are set now!")
      WARN("Could not turn on gflags")
    INFO("Tester opted out of enabling gflags")
