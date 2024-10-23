
"""
Copyright (c) 2022 Nutanix Inc. All rights reserved.
Author: umashankar.vd@nutanix.com
Dodin phase specific library
"""
#pylint: disable=unused-import, too-many-public-methods, useless-return
#pylint: disable=too-many-lines, bare-except, anomalous-backslash-in-string
#pylint: disable=line-too-long
#pylint: disable=broad-except
#pylint: disable=no-else-raise

import re
import time
import json
from pexpect import pxssh
import framework.operating_systems.operating_system.linux_operating_system \
  as LinuxOperatingSystem
try:
  from framework.lib.nulog import INFO, WARN, ERROR, \
    STEP
  EXECUTOR = "nutest"
except Exception:  # pylint: disable=broad-except
  from libs.ahv.framework.proxy_logging \
    import INFO, ERROR, STEP
  EXECUTOR = "mjolnir"
from libs.framework import mjolnir_entities as entities
from workflows.acropolis.ahv.platform.ahv.workflows.platform_qualification.lib.cluster_helper import \
  ClusterHelper
from libs.feature.dodin.dodin_phase4 import DodinPhase4Libs

class StigCheck():
  """
  This is stig check class and has functions for various stig compliance checks
  named check_<jiraticket>
  each check will establish ssh connection to host via either pxssh or
  leverage execute command attribute and run the command, validate
  and return pass if criteria is met otherwise raise exception
  """
  def __init__(self, cluster, **kwargs):
    """
    Initialize object
    Args:
        cluster(object): Nutest cluster object
    """
    # cluster_ip = "10.40.162.96"
    # self.cluster = NOSCluster(cluster=cluster_ip)
    self.cluster = cluster

    # self.cluster.enable_dod_mode(enable_sudo=True, enable_ahv_nutant_user=True)
    # self.cluster.enable_ssh_sudo_access()
    #initializing dod, if not dod then will enable dod
    self.dod_wf = DodinPhase4Libs(cluster=cluster, **kwargs)
    self.dod_wf.enable_dod_wf_using_script(**kwargs)
    #hardening by running additional security settings
    STEP("Getting current security params")
    self._get_security_params()

    #can add ncli settings here, removing it since this is done
    #by Dodin from Sept 13 - AUTO-26365, func that can help are
    #def _set_ncli_security and _make_scanner_happy, present in this class

  #this ticket is not present in the latest list, however since we have added,
  #not removing it - this was due to confusion in the initial list of tickets
  # Vs updated list
  def check_526717(self):
    """
    Args:
      Nothing
    Raises:
      Exception
    """
    STEP("Mount point check for log, Audit, tmp: 526717")

    mount_points_cmd = ["sudo mount | grep /var/log", "sudo mount | grep /var/log/audit", "sudo mount | grep /var/tmp"]
    for mount_cmd in mount_points_cmd:
      STEP("Checking moint point: %s"%mount_cmd)
      INFO("Running the command and then validate")
      info_log = self._run_cmd_pxssh(mount_cmd)
      if b'nodev' in info_log:
        INFO("nodev option is configured")
      else:
        raise Exception("nodev option is not")
      if b'nosuid' in info_log:
        INFO("nosuid option is configured")
      else:
        raise Exception("nosuid option is not")
      if b'noexec' in info_log:
        INFO("noexec option is configured")
      else:
        raise Exception("noexec option is not")

  def check_542963(self):
    """
    Args:
      Nothing
    Raises:
      Exception
    Returns:
      Nothing
    """
    STEP("RHEL-08-040172 - The systemd Ctrl-Alt-Delete burst key sequence in RHEL 8 must be disabled.")
    cmd_log = "sudo grep -i ctrl /etc/systemd/system.conf"
    info_log = self._run_cmd(cmd_log)
    INFO("here's what the command returned: %s"%info_log['stdout'])
    if 'CtrlAltDelBurstAction=none' in info_log['stdout'] and \
      '#CtrlAltDelBurstAction=none' not in info_log['stdout']:
      INFO("Config as expected!")
    else:
      WARN("RHEL 8 is not configured to reboot the system when Ctrl-Alt-Delete is pressed \
      seven times within two seconds")
      raise Exception("RHEL-08-040172 - failed")
    return

  # def check_539242(self):
  #   """
  #   Args:
  #     Nothing
  #   Raises:
  #     Exception
  #   Returns:
  #     Nothing
  #   """
  #   STEP("Verify RHEL 8 is not configured to reboot the system when \
  #     Ctrl-Alt-Delete is pressed seven times within two seconds with \
  #     the following command:")
  #   cmd_log = "sudo grep '/usr/bin/kmod' /etc/audit/audit.rules"
  #   info_log = self._run_cmd_pxssh(cmd_log)
  #   if b'-a always,exit -F path=/usr/bin/kmod -F perm=x -F auid>=1000 -F \
  #   auid!=unset -k modules' in info_log and b'#' not in info_log:
  #     INFO("Config as expected!")
  #   else:
  #     raise Exception("Check failed as command returned :%s"%info_log)
  #   return
  # def check_539203(self):
  #   """
  #   Args:
  #     Nothing
  #   Raises:
  #     Exception
  #   Returns:
  #     Nothing
  #   """
  #   STEP("Verify the audit system prevents unauthorized changes with the \
  #     following command:")
  #   cmd_log = "sudo grep '^\s*[^#]' /etc/audit/audit.rules | tail -1"
  #   info_log = self._run_cmd_pxssh(cmd_log)
  #   if b'-e 2' in info_log:
  #     INFO("Config as expected!")
  #   else:
  #     raise Exception("Check failed as command returned :%s"%info_log)
  #   return

#needs updating validation
  def check_542964(self):
    """
    using pxssh here because the command would return exception as the status
    is dead
    Args:
      Nothing
    Raises:
      Exception
    Returns:
      Nothing
    """
    STEP("RHEL-08-040180 Verify debug-shell systemd service must be disabled on RHEL 8")
    cmd_log = "sudo systemctl status debug-shell.service"
    try:
      info_log = self._run_cmd(cmd_log)
    except Exception as err:
      info_log = str(err)
      INFO("exception seen as service is down/inactive as expected!!")
      if 'Active: inactive (dead)' in info_log and 'Loaded: masked' in info_log:
        INFO("Debug service is disabled")
      else:
        WARN("RHEL-08-040180 Check failed - debug_shell service is not disabled")
        raise Exception("RHEL-08-040180 - Failed")
    return

#need validation of output, try using cmd exec instead of pxssh?
  def check_542925(self):
    """
    Args:
      Nothing
    Raises:
      Exception
    Returns:
      Nothing
    """
    STEP("RHEL-08-010287 - The RHEL 8 SSH daemon must be configured \
      to use system-wide crypto policies.")
    cmd_log = "sudo grep CRYPTO_POLICY /etc/sysconfig/sshd"
    info_log = self._run_cmd_pxssh(cmd_log)
    if b'# CRYPTO_POLICY=' in info_log:
      INFO("daemon configured to use system-wide crypto policies")
      INFO("RHEL-08-010287 - Verified")
    else:
      WARN("daemon not configured to use system-wide crypto policies")
      raise Exception("RHEL-08-010287 - Failed")
    return

#need validation of output, try using cmd exec instead of pxssh?
  def check_542919(self):
    """
    Args:
      Nothing
    Raises:
      Exception
    Returns:
      Nothing
    """
    STEP("RHEL-08-030742 - RHEL 8 must disable network management \
      of the chrony daemon.")
    cmd_log = "sudo grep -w 'cmdport' /etc/chrony.conf"
    info_log = self._run_cmd_pxssh(cmd_log)
    if b'cmdport 0' in info_log and b'#cmdport 0' not in info_log:
      INFO("RHEL 8 disables network management of the chrony daemon")
      INFO("RHEL-08-030742 - Verified")
    else:
      WARN("RHEL 8 is not disabled for network management of the chrony daemon")
      raise Exception("RHEL-08-030742 - Failed")
    return

  def check_542918(self):
    """
    Args:
      Nothing
    Raises:
      Exception
    Returns:
      Nothing
    """
    STEP("RHEL-08-030741 - RHEL 8 must disable the chrony daemon \
      from acting as a server.")
    cmd_log = "sudo grep -w 'port' /etc/chrony.conf"
    info_log = self._run_cmd_pxssh(cmd_log)
    if b'port 0' in info_log:
      INFO("disabled the chrony daemon from acting as a server")
      INFO("RHEL-08-030741 - Verified")
    else:
      WARN("chrony daemon from acting as a server is not disabled")
      raise Exception("RHEL-08-030741 - Failed")
    return

  def check_542917(self):
    """
    Args:
      Nothing
    Raises:
      Exception
    Returns:
      Nothing
    """
    STEP("RHEL-08-030740 - RHEL 8 must securely compare internal information \
    system clocks at least every 24 hours with a server synchronized to an \
    authoritative time source")
    cmd_log_1 = "sudo grep maxpoll /etc/chrony.conf"
    info_log_1 = self._run_cmd(cmd_log_1)
    maxpoll_value = int(info_log_1['stdout'].split("maxpoll")[1].strip().split()[0])
    INFO("Here's what the command returned: %s"%info_log_1['stdout'])
    if 'maxpoll' in info_log_1['stdout'] and maxpoll_value <= 16 and '#' not in info_log_1['stdout']:
      #checking value of last element
      INFO("maxpoll option is set to a number as expected")
    else:
      WARN("maxpoll option is set to a inappropriate number")
      raise Exception("RHEL-08-030740 - failed")
    INFO("Verify the chrony.conf file is configured to an authoritative \
      DoD time source")
    cmd_log_2 = "sudo grep -i server /etc/chrony.conf"
    info_log_2 = self._run_cmd(cmd_log_2)
    INFO("Here's what the command returned: %s"%info_log_2['stdout'])
    if 'server' in info_log_2['stdout'] and 'centos.pool.ntp.org' in info_log_2['stdout']:
      INFO("chrony.conf file is configured to an authoritative DoD time source")
    else:
      WARN("chrony.conf file is not configured to an authoritative DoD time source")
      raise Exception("RHEL-08-030740 - failed")
    return

  def check_542904(self):
    """
    Args:
      Nothing
    Raises:
      Exception
    Returns:
      Nothing
    """
    STEP("RHEL-08-040262 - RHEL 8 must not accept router advertisements on all\
       IPv6 interfaces by default.")
    cmd_log_1 = "sudo sysctl net.ipv6.conf.default.accept_ra"
    info_log_1 = self._run_cmd(cmd_log_1)
    if 'net.ipv6.conf.default.accept_ra = 0' in info_log_1['stdout'] and \
      '#' not in info_log_1['stdout']:
      #checking value of last element
      INFO("Router advertisements are not accepted by default")
    else:
      WARN("Advertisements are accepted by default")
      raise Exception("RHEL-08-040262 - failed")
    INFO("Check that the configuration files are present to enable this \
      network parameter")

    #trying to run the command, work if returns failure
    try:
      cmd_log_2 = "sudo grep -r net.ipv6.conf.default.accept_ra /run/sysctl.d/*.conf \
      /usr/local/lib/sysctl.d/*.conf /usr/lib/sysctl.d/*.conf /lib/sysctl.d/*.conf /etc/sysctl.conf /etc/sysctl.d/*.conf"
      info_log = self._run_cmd(cmd_log_2)
      INFO("Here's what the command returned:%s"%info_log)
    except Exception as err:
      #extracting stdout
      WARN("Command could have failed because some dir not found")
      info_log = str(err)
      INFO("Here's what the command returned:%s"%info_log)
      stdout = info_log[info_log.index('stdout')+9 : info_log.index('stderr')-3].split('\\r\\n')
      INFO("Display %s"%stdout)

    for info in stdout:
      if "net.ipv6.conf.default.accept_ra = 0" in info and not info.startswith("#") and info.startswith("/etc/sysctl.d"):
        status = True
        break
      status = False

    #Decision of part 2 verification of STIG based on status
    if status:
      INFO("Relevant network param enabled")
      INFO("RHEL-08-040262- Verified part 2")
    else:
      WARN("Relevant network param not enabled")
      raise Exception("RHEL-08-040262 - Failed")
    return

  def check_539564(self):
    """
    Args:
      Nothing
    Raises:
      Exception
    """
    STEP("RHEL-08-030602 - RHEL 8 must allocate an audit_backlog_limit of suff\
      icient size to capture processes that start prior to the audit daemon.")
    cmd_log_1 = "sudo grub2-editenv list | grep audit"
    info_log_1 = self._run_cmd(cmd_log_1)
    # Regular expression pattern to extract the value of audit_backlog_limit
    pattern = r"audit_backlog_limit=(\d+)"
    # Extracting the value of audit_backlog_limit
    match = re.search(pattern, info_log_1['stdout'])
    if match:
      audit_backlog_limit = int(match.group(1))
      if audit_backlog_limit >= 8192:
        INFO("audit_backlog_limit is equal to or greater than 8192")
      else:
        WARN("audit_backlog_limit is less than 8192")
        raise Exception("RHEL-08-030602 - failed")
    else:
      WARN("audit_backlog_limit entry not found")
      raise Exception("RHEL-08-030602 - failed")
    cmd_log_2 = "sudo grep audit /etc/default/grub"
    info_log_2 = self._run_cmd(cmd_log_2)
    # Regular expression pattern to extract the value of audit_backlog_limit
    pattern = r"audit_backlog_limit=(\d+)"
    # Extracting the value of audit_backlog_limit
    match = re.search(pattern, info_log_2['stdout'])
    if match:
      audit_backlog_limit = int(match.group(1))
      if audit_backlog_limit >= 8192:
        INFO("Check the audit_backlog_limit is set to persist in kernel \
        updates")
      else:
        WARN("Check the audit_backlog_limit is not set to persist")
        raise Exception("RHEL-08-030602 - failed")
    else:
      WARN("Check the audit_backlog_limit is not set to persist")
      raise Exception("RHEL-08-030602 - failed")

  def check_539563(self):
    """
    Args:
      Nothing
    Raises:
      Exception
    Returns:
      Nothing
    """
    STEP("RHEL-08-030590 - Successful/unsuccessful modifications to the \
      faillock log file in RHEL 8 must generate an audit record.")
    cmd_log_1 = "sudo grep dir /etc/security/faillock.conf"
    info_log_1 = self._run_cmd(cmd_log_1)
    INFO(info_log_1)
    if "dir = /var/log/faillock" in info_log_1['stdout'] \
      and '#dir = /var/log/faillock' not in info_log_1['stdout']:
      INFO("faillock tallies are stored")
    else:
      WARN("faillock tallies are not stored")
      raise Exception("RHEL-08-030590 - failed")
    cmd_log_2 = "sudo grep -w faillock /etc/audit/audit.rules"

    #second part verification
    INFO("Verifying part 2 of this stig")
    info_log_2 = self._run_cmd(cmd_log_2)
    if "-w /var/log/faillock -p wa -k logins" in info_log_2['stdout'] \
    and not info_log_2['stdout'].startswith("#"):
      INFO("file system rules in /etc/audit/audit.rules is good")
      INFO("RHEL-08-030590 - Verified")
    else:
      WARN("file system rules in /etc/audit/audit.rules is not as expected")
      raise Exception("RHEL-08-030590 - Failed")
    return

  def check_539195(self):
    """
    Args:
      Nothing
    Raises:
      Exception
    Returns:
      Nothing
    """
    STEP("RHEL-08-020300 - RHEL 8 must prevent the use of dictionary \
      words for passwords.")
    cmd_log = "sudo grep -r dictcheck /etc/security/pwquality.conf*"
    info_log = self._run_cmd(cmd_log)
    if 'dictcheck = 1' in info_log['stdout'] and not info_log['stdout'].startswith("#"):
      INFO("RHEL 8 prevents the use of dictionary words for passwords")
    else:
      WARN("setting to prevent use of dictionary words for passwords not set")
      raise Exception("RHEL-08-020300 - failed")
    return

  def check_537714(self):
    """
    Args:
      Nothing
    Raises:
      Exception
    Returns:
      Nothing
    """
    STEP("RHEL-08-020011- RHEL 8 must automatically lock an account \
      when three unsuccessful logon attempts occur.")
    cmd_log = "sudo grep 'deny =' /etc/security/faillock.conf"
    info_log = self._run_cmd(cmd_log)
    INFO("Here's what command returned: %s"%info_log)
    if 'deny = 3' in info_log['stdout'] and not info_log['stdout'].startswith("#"):
      INFO("file is configured to lock an account after three unsuccessful \
        logon attempts")
      INFO("RHEL-08-020011 - Verified")
    else:
      WARN("file not configured to lock an account after three unsuccessful \
        logon attempts")
      raise Exception("RHEL-08-020011 - failed")
    return

  def check_537719(self):
    """
    Args:
      Nothing
    Raises:
      Exception
    Returns:
      Nothing
    """
    STEP("RHEL-08-020015 - RHEL 8 must automatically lock an account until the locked \
    account is released by an administrator when three unsuccessful logon attempts occur during a 15-minute time period.")
    cmd_log = "sudo grep 'unlock_time =' /etc/security/faillock.conf"
    info_log = self._run_cmd(cmd_log)
    INFO("Here's what command returned: %s"%info_log)
    if 'unlock_time = 0' in info_log['stdout'] and not info_log['stdout'].startswith("#"):
      INFO("file is configured to lock an account until released by an administrator")
      INFO("RHEL-08-020015 - Verified")
    else:
      WARN("file is not configured to lock an account until released by an administrator")
      raise Exception("RHEL-08-020015 - failed")
    return

  def check_537703(self):
    """
    Args:
      Nothing
    Raises:
      Exception
    Returns:
      Nothing
    """
    STEP("RHEL-08-010674 - RHEL 8 must disable storing core dumps.")
    cmd_log = "sudo grep -i storage /etc/systemd/coredump.conf.d/nutanix-coredump.conf"
    info_log = self._run_cmd(cmd_log)
    INFO("Here's what the command returned:%s"%info_log)
    if "Storage=none" in info_log['stdout'] and '#' not in info_log['stdout']:
      INFO("operating system disabled storing core dumps for all users")
      INFO("RHEL-08-010674 - Verified")
    else:
      WARN("OS is not disabled for storing core dumps for all users")
      raise Exception("RHEL-08-010674 - Failed")
    return

  def check_537687(self):
    """
    Args:
      Nothing
    Raises:
      Exception
    Returns:
      Nothing
    """
    STEP("RHEL-08-010673 - RHEL 8 must disable core dumps for all users.")
    cmd_log = "sudo grep -r -s '^[^#].*core' /etc/security/limits.conf /etc/security/limits.d/.conf"

    try:
      cmd_log = "sudo grep -r -s '^[^#].*core' /etc/security/limits.conf /etc/security/limits.d/.conf"
      info_log = self._run_cmd(cmd_log)
      INFO("Here's what the command returned:%s"%info_log)
    except Exception as err:
      #extracting stdout
      WARN("Command could have failed because some dir not found")
      info_log = str(err)
      INFO("Here's what the command returned:%s"%info_log)
      stdout = info_log[info_log.index('stdout')+9 : info_log.index('stderr')-3].split('\\r\\n')
      INFO("Display %s"%stdout)

    for info in stdout:
      if "hard core 0" in info and not info.startswith("#"):
        status = True
        break
      status = False

    #Decision of part 2 verification of STIG based on status
    if status:
      INFO("operating system disabled storing core dumps for all users")
      INFO("RHEL-08-010673- Verified")
    else:
      WARN("OS is not disabled for storing core dumps for all users")
      raise Exception("RHEL-08-010673 - Failed")
    return

  def check_536748(self):
    """
    Args:
      Nothing
    Raises:
      Exception
    Returns:
      Nothing
    """
    STEP("RHEL-08-010372 - RHEL 8 must prevent the loading of a \
      new kernel for later execution.")
    cmd_log_1 = "sudo sysctl kernel.kexec_load_disabled"
    info_log_1 = self._run_cmd(cmd_log_1)
    INFO(info_log_1)
    if "kernel.kexec_load_disabled = 1" in info_log_1['stdout'] \
      and '#kernel.kexec_load_disabled = 1' not in info_log_1['stdout']:
      INFO("kernel.kexec_load_disabled is set to 1")
    else:
      WARN("kernel.kexec_load_disabled is not set to 1")
      raise Exception("RHEL-08-010372 - failed")
    cmd_log_2 = "sudo grep -r kernel.kexec_load_disabled /run/sysctl.d/.conf \
      /usr/local/lib/sysctl.d/.conf /usr/lib/sysctl.d/.conf /lib/sysctl.d/\
      .conf /etc/sysctl.conf /etc/sysctl.d/*.conf"
    try:
      info_log_2 = self._run_cmd(cmd_log_2)
      INFO("Here's what the command returned:%s"%info_log_2)
      stdout = info_log_2['stdout']
    except Exception as err:
      WARN("Command could have failed because some dir not found")
      info_log_2 = str(err)
      INFO("Here's what the command returned:%s"%info_log_2)
      stdout = info_log_2[info_log_2.index('stdout')+9 : info_log_2.index('stderr')-3].split('\\r\\n')
      INFO("Display %s"%stdout)
    #Validating output
    for info in stdout:
      if "kernel.kexec_load_disabled = 1" in info and not info.startswith("#") and info.startswith("/etc/sysctl.d"):
        status = True
        break
      status = False
    #decision on stig check
    if status:
      INFO("kernel.kexec_load_disabled is set to 1")
    else:
      WARN("kernel.kexec_load_disabled is not set to 1")
      raise Exception("RHEL-08-010372 - failed")
    return

  def check_536740(self):
    """
    Args:
      Nothing
    Raises:
      Exception
    Returns:
      Nothing
    """
    STEP("RHEL-08-010291 - The RHEL 8 operating system must implement \
      DoD-approved encryption to protect the confidentiality of SSH \
      server connections.")
    cmd_log = "sudo grep -i ciphers \
      /etc/crypto-policies/back-ends/opensshserver.config"
    info_log = self._run_cmd(cmd_log)
    INFO("Here's what the command returned:%s"%info_log)
    if "CRYPTO_POLICY='-oCiphers=aes256-ctr,aes192-ctr,aes128-ctr" in info_log['stdout'] \
      and not info_log['stdout'].startswith('#'):
      INFO("cipher entries in the opensshserver.config is as expected")
      INFO("RHEL-08-010291 - Verified")
    else:
      WARN("cipher entries in the opensshserver.config is not expected")
      raise Exception("RHEL-08-010291 - Failed")
    return

  def check_537716(self):
    """
    Args:
      Nothing
    Raises:
      Exception
    """
    STEP("RHEL-08-020013 - RHEL 8 must automatically lock an account when \
      three unsuccessful logon attempts occur during a 15-minute time period")
    cmd_log = "sudo grep 'fail_interval =' /etc/security/faillock.conf"
    info_log = self._run_cmd(cmd_log)
    INFO("Here's what the command returned:%s"%info_log)
    info_log['stdout'] = info_log['stdout'].split("\r\n")
    #info_log['stdout'] is list of lines returned by command

    for info in info_log['stdout']:
      if not info.strip().startswith("#"):
        # Extract the numeric value of "fail_interval"
        value = info.split("=")[-1].strip()
        try:
          value = int(value)
          if value >= 900:
            status = True
            break
        except:
          pass
      #in case fail_interval value is less than 900 or missing
      else:
        status = False

    #decision making on stig
    if status:
      INFO("faillock_interval is equal to or greater than 900")
      INFO("RHEL-08-020013 - Verified")
    else:
      WARN("audit_backlog_limit entry not found or less than 900")
      raise Exception("RHEL-08-020013 - Failed")

  def check_536710(self):
    """
    Args:
      Nothing
    Raises:
      Exception
    """
    STEP("RHEL-08-010200 - RHEL 8 must be configured so that all network \
    connections associated with SSH traffic are terminated at the end of \
    the session or after 10 minutes of inactivity")
    cmd_log = "sudo grep -ir clientalive /etc/ssh/sshd_config*"
    info_log = self._run_cmd(cmd_log)
    INFO("Here's what the command returned:%s"%info_log)
    if "ClientAliveCountMax 1" in info_log['stdout'] and not info_log['stdout'].startswith("#"):
      INFO("Verified all network connections are terminated if 10mins of \
        inactivity")
    else:
      WARN("Verification of network connection termination if 10 mins of \
        inactivity failed")
      raise Exception("RHEL-08-010200 - Failed")

  def check_536716(self):
    """
    Args:
      Nothing
    Raises:
      Exception
    """
    STEP("RHEL-08-010230 - The RHEL 8 /var/log/messages file must be \
      group-owned by root.")
    cmd_log = "sudo stat -c '%G' /var/log/messages"
    info_log = self._run_cmd(cmd_log)
    INFO("Here's what the command returned:%s"%info_log)
    if info_log['stdout'].strip() == 'root':
      INFO("/var/log/messages file is group-owned by root")
    else:
      WARN("/var/log/messages file is not group-owned by root")
      raise Exception("RHEL-08-010230 - Failed")

  def check_536718(self):
    """
    Args:
      Nothing
    Raises:
      Exception
    """
    STEP("RHEL-08-010290 - The RHEL 8 SSH server must be configured to use \
    only Message Authentication Codes (MACs) employing FIPS 140-2 validated \
    cryptographic hash algorithms.")
    cmd_log = "sudo grep -i macs /etc/crypto-policies/back-ends/opensshserver.config"
    info_log = self._run_cmd(cmd_log)
    INFO("Here's what the command returned:%s"%info_log)
    pattern = r'(-oMAC[Ss]=hmac-sha2-512,hmac-sha2-256,hmac-sha2-512-etm@openssh\.com,hmac-sha2-256-etm@openssh\.com)'
    #adding white space after hmac-sha2-256 because we dont expect any other values
    #post that and the order has to be 512 followed by 256
    #changing the expected output as per ENG-638399
    if re.search(pattern, info_log['stdout']) and not info_log['stdout'].startswith("#"):
      INFO("Verified the SSH server is configured to use only MACs employing \
      FIPS 140-2-approved algorithms")
    else:
      WARN("Verification of SSH server is configured to use only MACs \
      employing FIPS 140-2-approved algorithms failed")
      raise Exception("RHEL-08-010290 - Failed")

  def check_536743(self):
    """
    Args:
      Nothing
    Raises:
      Exception
    """
    STEP("RHEL-08-010293 - operating system must implement DoD-approved \
      encryption in the OpenSSL package")
    cmd_log_1 = "sudo grep -i opensslcnf.config /etc/pki/tls/openssl.cnf"
    info_log_1 = self._run_cmd(cmd_log_1)
    INFO("Here's what the command returned:%s"%info_log_1)
    INFO("Verifying part 1 of this STIG")
    if '.include /etc/crypto-policies/back-ends/opensslcnf.config' in \
      info_log_1['stdout']:
      INFO("verified system-wide crypto policies are in effect")
    else:
      WARN("system-wide crypto policies in effect verification failed")
      raise Exception("RHEL-08-010293 - Failed")
    INFO("Verifying part 2 of this STIG")
    cmd_log_2 = "sudo update-crypto-policies --show"
    info_log_2 = self._run_cmd(cmd_log_2)
    INFO("Here's what the command returned:%s"%info_log_2)
    INFO("Verifying part 1 of this STIG")
    if 'FIPS' in info_log_2['stdout'] and '#' not in info_log_2['stdout']:
      INFO("system-wide crypto policy in use if FIPS")
    else:
      WARN("system-wide crypto policy is not FIPS")
      raise Exception("RHEL-08-010293 - Failed")

  def check_537685(self):
    """
    Args:
      Nothing
    Raises:
      Exception
    """
    STEP("RHEL-08-010571 - must prevent files with the setuid and setgid \
      bit set from being executed on the /boot directory.")
    cmd_log = "sudo mount | grep '\s/boot\s'"
    info_log = self._run_cmd(cmd_log)
    INFO("Here's what the command returned:%s"%info_log)
    if 'nosuid' in info_log['stdout'] and '#' not in info_log['stdout']:
      INFO("settings to prevent files with the setuid and setgid bit set \
        from being executed on the /boot directory is present")
    else:
      WARN("settings to prevent files with the setuid and setgid bit set \
        from being executed on the /boot directory is not present")
      raise Exception("RHEL-08-010571 - Failed")

  def check_537686(self):
    """
    Args:
      Nothing
    Raises:
      Exception
    """
    STEP("RHEL-08-010580 - RHEL 8 must prevent special devices on non-root \
      local partitions.")
    cmd_log = "sudo mount | grep '^/dev\S* on /\S' | grep --invert-match \
    'nodev'"
    try:
      info_log = self._run_cmd(cmd_log)
      WARN("Command produced an output so this is a finding")
      raise Exception("RHEL-08-010580 - Failed")
    except:
      INFO("Expected exception since no output was produced by cmd")
      INFO("RHEL-08-010580 - Verified")
      INFO("Verification of all non-root local partitions are \
        mounted with the 'nodev' option passed")

  def check_537704(self):
    """
    Args:
      Nothing
    Raises:
      Exception
    """
    STEP("RHEL-08-010675 - RHEL 8 must disable core dump backtraces.")
    cmd_log = "sudo grep -ir ProcessSizeMax /etc/systemd/*"

    try:
      cmd_log = "sudo grep -ir ProcessSizeMax /etc/systemd/*"
      info_log = self._run_cmd(cmd_log)
      INFO("Here's what the command returned:%s"%info_log)
      stdout = info_log['stdout'].split('\r\n')
    except Exception as err:
      #extracting stdout
      WARN("Command could have failed because some dir not found")
      info_log = str(err)
      INFO("Here's what the command returned:%s"%info_log)
      stdout = info_log[info_log.index('stdout')+9 : info_log.index('stderr')-3].split('\\r\\n')
      INFO("Display %s"%stdout)

    for info in stdout:
      if "ProcessSizeMax=0" in info and not info.startswith("#") and info.startswith("/etc/systemd"):
        status = True
        break
      status = False

    #Decision of part 2 verification of STIG based on status
    if status:
      INFO("verified the operating system disables core dump backtraces ")
      INFO("RHEL-08-010675 = Verified")
    else:
      WARN("ProcessSizeMax is not 0 or commented out, verification of OS\
        core dump disable check failed")
      raise Exception("RHEL-08-010675 - Failed")

  def check_538684(self):
    """
    Args:
      Nothing
    Raises:
      Exception
    """
    STEP("RHEL-08-020017- RHEL 8 must ensure account lockouts persist.")
    cmd_log = "sudo grep 'dir =' /etc/security/faillock.conf"
    info_log = self._run_cmd(cmd_log)
    INFO("Here's what the command returned:%s"%info_log)
    if "dir = /var/log/faillock" in info_log['stdout'] and not info_log['stdout'].startswith("#"):
      INFO("Verified the /etc/security/faillock.conf file is configured use \
        a non-default faillock directory")
    else:
      WARN("Verification failed - /etc/security/faillock.conf file is not \
        configured use a non-default faillock directory")
      raise Exception("RHEL-08-020017 - Failed")

  def check_538686(self):
    """
    Args:
      Nothing
    Raises:
      Exception
    """
    STEP("RHEL-08-020019- RHEL 8 must prevent system messages from being \
      presented when three unsuccessful logon attempts occur.")
    cmd_log = "sudo grep silent /etc/security/faillock.conf"
    info_log = self._run_cmd(cmd_log)
    INFO("Here's what the command returned:%s"%info_log)
    if "silent" in info_log['stdout'] and not info_log['stdout'].startswith("#"):
      INFO("Verified the /etc/security/faillock.conf file is configured to \
        prevent informative messages from being presented at logon attempts")
      INFO("RHEL-08-020019 - Verified")
    else:
      WARN("Verification failed - /etc/security/faillock.conf file is not \
      configured to prevent informative messages from being presented at \
      logon attempts")
      raise Exception("RHEL-08-020019 - Failed")

  def check_538689(self):
    """
    Args:
      Nothing
    Raises:
      Exception
    """
    STEP("RHEL-08-020021 -RHEL 8 must log user name information when \
      unsuccessful logon attempts occur.")
    cmd_log = "sudo grep audit /etc/security/faillock.conf"
    info_log = self._run_cmd(cmd_log)
    INFO("Here's what the command returned:%s"%info_log)
    if "audit" in info_log['stdout'] and not info_log['stdout'].startswith('#'):
      INFO("Verified the /etc/security/faillock.conf file is configured \
      to log user name information when unsuccessful logon attempts occur")
    else:
      WARN("Verification failed - /etc/security/faillock.conf file is \
      configured to log user name information when unsuccessful logon \
      attempts occur")
      raise Exception("RHEL-08-020021 - Failed")

  def check_539114(self):
    """
    Args:
      Nothing
    Raises:
      Exception
    """
    STEP("RHEL-08-020023 - RHEL 8 must include root when automatically locking \
    an account until the locked account is released by an administrator when \
    three unsuccessful logon attempts occur during a 15-minute time period.")
    cmd_log = "sudo grep even_deny_root /etc/security/faillock.conf"
    info_log = self._run_cmd(cmd_log)
    INFO("Here's what the command returned:%s"%info_log)
    info_log['stdout'] = info_log['stdout'].split("\r\n")
    #info_log['stdout'] is list of lines returned by command

    for info in info_log['stdout']:
      if info.strip() == "even_deny_root":
        # Extract the numeric value of "fail_interval"
        status = True
        break
        #in case fail_interval value is less than 900 or missing
      status = False
    #decision making on stig
    if status:
      INFO("Verified /etc/security/faillock.conf file is configured to log \
      user name information when unsuccessful logon attempts occur")
      INFO("RHEL-08-020023 - Verified")
    else:
      WARN("Verification failed for /etc/security/faillock.conf file is \
      configured to log user name information when unsuccessful logon \
      attempts occur")
      raise Exception("RHEL-08-020023 - Failed")

  def check_539197(self):
    """
    Args:
      Nothing
    Raises:
      Exception
    """
    STEP("RHEL-08-030061 -The RHEL 8 audit system must audit local events.")
    cmd_log = "sudo grep local_events /etc/audit/auditd.conf"
    info_log = self._run_cmd(cmd_log)
    INFO("Here's what the command returned:%s"%info_log)
    if ("local_events = yes" in info_log['stdout']) and not info_log['stdout'].startswith("#"):
      INFO("Verified the RHEL 8 Audit Daemon is configured to include local \
        events")
    else:
      WARN("Verification failed - RHEL 8 Audit Daemon is not configured \
        to include local events")
      raise Exception("RHEL-08-030061 - Failed")

  def check_539198(self):
    """
    Args:
      Nothing
    Raises:
      Exception
    """
    STEP("RHEL-08-030062 -RHEL 8 must label all off-loaded audit logs before \
      sending them to the central log server.")
    cmd_log = "sudo grep 'name_format' /etc/audit/auditd.conf"
    info_log = self._run_cmd(cmd_log)
    INFO("Here's what the command returned:%s"%info_log)
    pattern = r"(?m)^(?!#).*name_format\s*=\s*(hostname|fqd|numeric)"
    matches = re.findall(pattern, info_log['stdout'].strip())
    if matches:
      INFO("Verified RHEL 8 Audit Daemon is configured to label all \
        off-loaded audit logs")
      INFO("RHEL-08-030062 - Verified")
    else:
      WARN("Verification failed - RHEL 8 Audit Daemon is not configured \
        to include local events")
      raise Exception("RHEL-08-030062 - Failed")

  def check_539199(self):
    """
    Args:
      Nothing
    Raises:
      Exception
    """
    STEP("RHEL-08-030063 - RHEL 8 must resolve audit information before \
      writing to disk.")
    cmd_log = "sudo grep 'log_format' /etc/audit/auditd.conf"
    info_log = self._run_cmd(cmd_log)
    INFO("Here's what the command returned:%s"%info_log)
    pattern = r"(?m)^(?!#).*log_format\s*=\s*ENRICHED\b"
    matches = re.findall(pattern, info_log['stdout'].strip())
    if matches:
      INFO("RHEL-08-030063 - Verified")
    else:
      WARN("Verification failed - RHEL 8 Audit Daemon is not configured \
        to include local events")
      raise Exception("RHEL-08-030062 - Failed")

  def check_539203(self):
    """
    Args:
      Nothing
    Raises:
      Exception
    """
    STEP("RHEL-08-030121 - RHEL 8 audit system must protect auditing rules \
      from unauthorized change.")
    cmd_log = "sudo grep '^\s*[^#]' /etc/audit/audit.rules | tail -1"
    info_log = self._run_cmd(cmd_log)
    INFO("Here's what the command returned:%s"%info_log)
    pattern = r"(?m)^(?!#).*-e\s+2\b"
    matches = re.findall(pattern, info_log['stdout'].strip())
    if matches:
      INFO("RHEL-08-030121 - Verified")
    else:
      WARN("Verification failed - audit system will not prevent unauthorized \
        changes")
      raise Exception("RHEL-08-030121 - Failed")

  def check_539208(self):
    """
    Args:
      Nothing
    Raises:
      Exception
    """
    STEP("RHEL-08-030190- Successful/unsuccessful uses of the su command in \
      RHEL 8 must generate an audit record.")
    cmd_log = "sudo grep -w /usr/bin/su /etc/audit/audit.rules"
    try:
      info_log = self._run_cmd(cmd_log)
      INFO("Here's what the command returned:%s"%info_log)
      pattern = r"(?m)^#\s*\S.*"
      matches = re.findall(pattern, info_log['stdout'].strip())
      if not matches:
        INFO("Pass criteria - Command should return a line of info")
        INFO("RHEL-08-030190 - Verified")
      else:
        WARN("Verification failed - output commented : audit system will not \
          prevent unauthorized changes")
        raise Exception("RHEL-08-030190 - Failed")
    except:
      WARN("Verification failed - audit system will not prevent unauthorized \
        changes")
      raise Exception("RHEL-08-030190 - Failed")

  def check_539209(self):
    """
    Args:
      Nothing
    Raises:
      Exception
    """
    STEP("RHEL-08-030300 - Successful/unsuccessful uses of the mount command \
      in RHEL 8 must generate an audit record.")
    cmd_log = "sudo grep -w /usr/bin/mount /etc/audit/audit.rules"
    try:
      info_log = self._run_cmd(cmd_log)
      INFO("Here's what the command returned:%s"%info_log)
      pattern = r"(?m)^#\s*\S.*"
      matches = re.findall(pattern, info_log['stdout'].strip())
      if not matches:
        INFO("Pass criteria - Command should return a line of info")
        INFO("RHEL-08-030300 - Verified")
      else:
        WARN("Verification failed - output commented:audit event would not be \
          generated for any successful/unsuccessful use of the 'mount' command")
        raise Exception("RHEL-08-030300 - Failed")
    except:
      WARN("Verification failed - audit event would not be generated for any \
        successful/unsuccessful use of the 'mount' command")
      raise Exception("RHEL-08-030300 - Failed")

  def check_539210(self):
    """
    Args:
      Nothing
    Raises:
      Exception
    """
    STEP("RHEL-08-030301 - Successful/unsuccessful uses of the umount command \
      in RHEL 8 must generate an audit record.")
    cmd_log = "sudo grep -w /usr/bin/umount /etc/audit/audit.rules"
    try:
      info_log = self._run_cmd(cmd_log)
      INFO("Here's what the command returned:%s"%info_log)
      pattern = r"(?m)^#\s*\S.*"
      matches = re.findall(pattern, info_log['stdout'].strip())
      if not matches:
        INFO("Pass criteria - Command should return a line of info")
        INFO("RHEL-08-030301 - Verified")
      else:
        WARN("Verification failed - output commented :audit event would not be \
        generated for any successful/unsuccessful use of the 'umount' command")
        raise Exception("RHEL-08-030301 - Failed")
    except:
      WARN("Verification failed - audit event would not be generated for any \
        successful/unsuccessful use of the 'umount' command")
      raise Exception("RHEL-08-030301 - Failed")

  def check_539211(self):
    """
    Args:
      Nothing
    Raises:
      Exception
    """
    STEP("RHEL-08-030310 - Successful/unsuccessful uses of unix_update \
      in RHEL 8 must generate an audit record.")
    cmd_log = "sudo grep -w 'unix_update' /etc/audit/audit.rules"
    try:
      info_log = self._run_cmd(cmd_log)
      INFO("Here's what the command returned:%s"%info_log)
      pattern = r"(?m)^#\s*\S.*"
      matches = re.findall(pattern, info_log['stdout'].strip())
      if not matches:
        INFO("Pass criteria - Command should return a line of info")
        INFO("RHEL-08-030310 - Verified")
      else:
        WARN("Verification failed - output commented:audit event would not be \
          generated for any successful/unsuccessful unix_update")
        raise Exception("RHEL-08-030310 - Failed")
    except:
      WARN("Verification failed - audit event would not be generated for any \
        generated for any successful/unsuccessful unix_update")
      raise Exception("RHEL-08-030310 - Failed")

  def check_539212(self):
    """
    Args:
      Nothing
    Raises:
      Exception
    """
    STEP("RHEL-08-030330 - Successful/unsuccessful uses of the setfacl command \
      in RHEL 8 must generate an audit record.")
    cmd_log = "sudo grep -w setfacl /etc/audit/audit.rules"
    try:
      info_log = self._run_cmd(cmd_log)
      INFO("Here's what the command returned:%s"%info_log)
      pattern = r"(?m)^#\s*\S.*"
      matches = re.findall(pattern, info_log['stdout'].strip())
      if not matches:
        INFO("Pass criteria - Command should return a line of info")
        INFO("RHEL-08-030330 - Verified")
      else:
        WARN("Verification failed - output commented:audit event would not be \
          generated for any successful/unsuccessful setfacl command")
        raise Exception("RHEL-08-030301 - Failed")
    except:
      WARN("Verification failed - audit event would not be generated for any \
        generated for any successful/unsuccessful setfacl command")
      raise Exception("RHEL-08-030330 - Failed")

  def check_539213(self):
    """
    Args:
      Nothing
    Raises:
      Exception
    """
    STEP("RHEL-08-030360 - Successful/unsuccessful uses of the init_module and \
      finit_module system calls in RHEL 8 must generate an audit record.")
    cmd_log = "sudo grep init_module /etc/audit/audit.rules"
    info_log = self._run_cmd(cmd_log)
    INFO("Here's what the command returned:%s"%info_log)
    # Define the patterns to match the audit rules
    pattern_init_module = r"-a always,exit -F arch=b32 -S init_module\s"
    pattern_finit_module = \
    r"-a always,exit -F arch=b32 -S init_module,finit_module\s"
    # Search for the patterns in the command output
    init_rule_found = re.search(pattern_init_module, info_log['stdout'])
    finit_rule_found = re.search(pattern_finit_module, info_log['stdout'])
    # Check if any of the rules are missing or commented out
    if not init_rule_found or init_rule_found.group(0).startswith("#"):
      raise Exception("RHEL-08-030360 - Failed : 'init_module' rule is \
        missing or commented out")
    if not finit_rule_found or finit_rule_found.group(0).startswith("#"):
      raise Exception("RHEL-08-030360 - Failed : 'finit_module' rule is \
        missing or commented out")
    # Stig check passed
    INFO("RHEL-08-030360 - Verified")

  def check_539239(self):
    """
    Args:
      Nothing
    Raises:
      Exception
    """
    STEP("RHEL-08-030390 - Successful/unsuccessful uses of the delete_module \
      command in RHEL 8 must generate an audit record.")
    cmd_log = "sudo grep -w 'delete_module' /etc/audit/audit.rules"
    try:
      info_log = self._run_cmd(cmd_log)
      INFO("Here's what the command returned:%s"%info_log)
      pattern = r"(?m)^#\s*\S.*"
      matches = re.findall(pattern, info_log['stdout'].strip())
      if not matches and info_log['stdout'] != '':
        INFO("Pass criteria - Command should return a line of info")
        INFO("RHEL-08-030390 - Verified")
      else:
        WARN("Verification failed - output commented : audit event would not \
        be generated for any successful/unsuccessful delete_module command")
        raise Exception("RHEL-08-030390 - Failed")
    except:
      WARN("Verification failed - audit event would not be generated for any \
        generated for any successful/unsuccessful delete_module command")
      raise Exception("RHEL-08-030390 - Failed")

  def check_539240(self):
    """
    Args:
      Nothing
    Raises:
      Exception
    """
    STEP("RHEL-08-030560-Successful/unsuccessful uses of the usermod command \
    in RHEL 8 must generate an audit record.")
    cmd_log = "sudo grep -w usermod /etc/audit/audit.rules"
    try:
      info_log = self._run_cmd(cmd_log)
      INFO("Here's what the command returned:%s"%info_log)
      pattern = r"(?m)^#\s*\S.*"
      matches = re.findall(pattern, info_log['stdout'].strip())
      if not matches and info_log['stdout'] != '':
        INFO("Pass criteria - Command should return a line of info")
        INFO("RHEL-08-030560 - Verified")
      else:
        WARN("Verification failed - output commented :audit event would not be \
          generated for any successful/unsuccessful usermod command")
        raise Exception("RHEL-08-030560 - Failed")
    except:
      WARN("Verification failed - audit event would not be generated for any \
        generated for any successful/unsuccessful usermod command")
      raise Exception("RHEL-08-030560 - Failed")

  def check_539241(self):
    """
    Args:
      Nothing
    Raises:
      Exception
    """
    STEP("RHEL-08-030570- Successful/unsuccessful uses of the chacl command in \
      RHEL 8 must generate an audit record.")
    cmd_log = "sudo grep -w chacl /etc/audit/audit.rules"
    try:
      info_log = self._run_cmd(cmd_log)
      INFO("Here's what the command returned:%s"%info_log)
      pattern = r"(?m)^#\s*\S.*"
      matches = re.findall(pattern, info_log['stdout'].strip())
      if not matches and info_log['stdout'] != '':
        INFO("Pass criteria - Command should return a line of info")
        INFO("RHEL-08-030570 - Verified")
      else:
        WARN("Verification failed - output commented :audit event would not be \
          generated for any successful/unsuccessful chacl command")
        raise Exception("RHEL-08-030570 - Failed")
    except:
      WARN("Verification failed - audit event would not be generated for any \
        generated for any successful/unsuccessful chacl command")
      raise Exception("RHEL-08-030570 - Failed")

  def check_539242(self):
    """
    Args:
      Nothing
    Raises:
      Exception
    """
    STEP("RHEL-08-030580 -Successful/unsuccessful uses of the kmod command in \
      RHEL 8 must generate an audit record.")
    cmd_log = "sudo grep '/usr/bin/kmod' /etc/audit/audit.rules"
    try:
      info_log = self._run_cmd(cmd_log)
      INFO("Here's what the command returned:%s"%info_log)
      pattern = r"(?m)^#\s*\S.*"
      matches = re.findall(pattern, info_log['stdout'].strip())
      if not matches and info_log['stdout'] != '':
        INFO("Pass criteria - Command should return a line of info")
        INFO("RHEL-08-030580 - Verified")
      else:
        WARN("Verification failed - output commented : audit event would not be\
          generated for any successful/unsuccessful kmod command")
        raise Exception("RHEL-08-030580 - Failed")
    except:
      WARN("Verification failed - audit event would not be generated for any \
        generated for any successful/unsuccessful kmod command")
      raise Exception("RHEL-08-030580 - Failed")

  def check_542903(self):
    """
    Args:
      Nothing
    Raises:
      Exception
    """
    STEP("RHEL-08-040250 - RHEL 8 must not forward IPv6 source-routed \
      packets by default.")
    cmd_log = "sudo sysctl net.ipv6.conf.default.accept_source_route"
    try:
      INFO("This STIG requires couple of checks")
      info_log = self._run_cmd(cmd_log)
      INFO("Here's what the command returned:%s"%info_log)
      if "net.ipv6.conf.default.accept_source_route = 0" in info_log['stdout'] \
      and not info_log['stdout'].startswith('#'):
        INFO("Pass criteria - Command should return a 0 value for arg")
        INFO("RHEL-08-040250- Verified part 1")
      else:
        WARN("Verification failed - kernel.yama.ptrace_scope is not 1")
        raise Exception("RHEL-08-040250 - Failed")
      cmd_log = "sudo grep -r net.ipv6.conf.default.accept_source_route \
      /run/sysctl.d/.conf /usr/local/lib/sysctl.d/.conf /usr/lib/sysctl.d/\
      .conf /lib/sysctl.d/.conf /etc/sysctl.conf /etc/sysctl.d/*.conf"
      info_log = self._run_cmd_pxssh(cmd_log)
      INFO("Here's what the command returned:%s"%info_log)
      if b"ipv6.conf.default.accept_source_route = 0" in info_log and \
      not b"#/etc/sysctl.d" in info_log:
        INFO("Pass criteria - Command should return a 0 value for arg")
        INFO("RHEL-08-040250- Verified part 2")
      else:
        WARN("Verification failed - ipv6.conf.default.accept_source_route \
        is not 0")
        raise Exception("RHEL-08-040250 - Failed")
    except:
      WARN("Verification failed - RHEL 8 could forward IPv6 source-routed \
        packets by default.")
      raise Exception("RHEL-08-040250 - Failed")

  def check_542905(self):
    """
    Args:
      Nothing
    Raises:
      Exception
    """
    STEP("RHEL-08-040282 - RHEL 8 must restrict usage of ptrace to descendant \
      processes.")
    cmd_log = "sudo sysctl kernel.yama.ptrace_scope"
    INFO("This STIG requires couple of checks")
    INFO("Starting with Verification of part 1")
    info_log = self._run_cmd(cmd_log)
    INFO("Here's what the command returned:%s"%info_log)
    if "kernel.yama.ptrace_scope = 1" in info_log['stdout'] and \
    not info_log['stdout'].startswith('#'):
      INFO("Pass criteria - Command should return a 1 value for arg")
      INFO("RHEL-08-040282- Verified part 1")
    else:
      WARN("Verification failed - kernel.yama.ptrace_scope is not 1")
      raise Exception("RHEL-08-040282 - Failed")

      #Part 2 verification, using pxssh since cmd execution returns failure
    STEP("Verifying part 2 of the stig")
    try:
      cmd_log = "sudo grep -r kernel.yama.ptrace_scope /run/sysctl.d/*.conf /usr/local/lib/sysctl.d/*.conf \
      /usr/lib/sysctl.d/*.conf /lib/sysctl.d/*.conf /etc/sysctl.conf /etc/sysctl.d/*.conf"
      info_log = self._run_cmd(cmd_log)
      INFO("Here's what the command returned:%s"%info_log)
    except Exception as err:
      #extracting stdout
      WARN("Command could have failed because some dir not found")
      info_log = str(err)
      INFO("Here's what the command returned:%s"%info_log)
      stdout = info_log[info_log.index('stdout')+9 : info_log.index('stderr')-3].split('\\r\\n')
      INFO("Display %s"%stdout)

    for info in stdout:
      if "kernel.yama.ptrace_scope = 1" in info and not info.startswith("#") and info.startswith("/etc/sysctl.d"):
        status = True
        break
      status = False

    #Decision of part 2 verification of STIG based on status
    if status:
      INFO("Pass criteria - Command should return a 1 value for arg")
      INFO("RHEL-08-040282- Verified part 2")
    else:
      WARN("Verification failed - kernel.yama.ptrace_scope is not 1")
      raise Exception("RHEL-08-040282 - Failed")

  def check_542912(self):
    """
    Args:
      Nothing
    Raises:
      Exception
    """
    STEP("RHEL-08-030700 - RHEL 8 must take appropriate action when the \
      internal event queue is full.")
    cmd_log = "sudo grep -i overflow_action /etc/audit/auditd.conf"
    info_log = self._run_cmd(cmd_log)
    INFO("Here's what the command returned:%s"%info_log)
    pattern = r"(?m)^\s*overflow_action\s*=\s*(?!syslog|single|halt|#)"
    matches = re.findall(pattern, info_log['stdout'].strip())
    if matches:
      INFO("Verified RHEL-08-030700 - RHEL 8 must take appropriate action \
        when the internal event queue is full.")
      INFO("RHEL-08-030700 - Verified")
    else:
      WARN("Verification failed - RHEL 8 may not take appropriate action \
        when the internal event queue is full.")
      raise Exception("RHEL-08-030700 - Failed")

  def check_542932(self):
    """
    Args:
      Nothing
    Raises:
      Exception
    """
    STEP("RHEL-08-020027 - RHEL 8 systems, versions 8.2 and above, must \
      configure SELinux context type to allow the use of a non-default \
      faillock tally directory.")
    try:
      cmd_log = "sudo grep -w dir /etc/security/faillock.conf"
      INFO("This STIG requires couple of checks")
      info_log = self._run_cmd(cmd_log)
      INFO("Here's what the command returned:%s"%info_log)
      if "dir = /var/log/faillock" in info_log['stdout'] and \
      not info_log['stdout'].startswith('#'):
        INFO("Pass criteria - location of the non-default tally directory \
          for the pam_faillock module")
        INFO("RHEL-08-020027 - Verified part 1")
      else:
        WARN("Verification failed - kernel.yama.ptrace_scope is not 1")
        raise Exception("RHEL-08-020027 - Failed")
      #part 2 verification
      cmd_log = "sudo ls -Zd /var/log/faillock"
      info_log = self._run_cmd(cmd_log)
      INFO("Here's what the command returned:%s"%info_log)
      if "faillog_t" in info_log['stdout'] and \
      not info_log['stdout'].startswith('#'):
        INFO("Pass criteria - location of the non-default tally directory \
          for the pam_faillock module")
        INFO("RHEL-08-020027- Verified part 2")
      else:
        WARN("Verification failed - security context type of the non-default \
          tally directory is not faillog_t")
        raise Exception("RHEL-08-020027 - Failed")
    except:
      WARN("Verification failed - security context type of the non-default \
          tally directory is not faillog_t")
      raise Exception("RHEL-08-020027 - Failed")

  def check_542937(self):
    """
    Args:
      Nothing
    Raises:
      Exception
    """
    STEP("RHEL-08-020104 - RHEL 8 systems, version 8.4 and above, must ensure \
    the password complexity module is configured for three retries or less.")
    try:
      cmd_log = "sudo grep -r retry /etc/security/pwquality.conf*"
      INFO("This STIG requires couple of checks")
      info_log = self._run_cmd(cmd_log)
      INFO("Here's what the command returned:%s"%info_log)
      if "/etc/security/pwquality.conf:retry = 3" in info_log['stdout'] and \
      not info_log['stdout'].startswith('#'):
        INFO("Pass criteria - location of the non-default tally directory \
          for the pam_faillock module")
        INFO("RHEL-08-020104 - Verified part 1")
      else:
        WARN("Verification failed - kernel.yama.ptrace_scope is not 1")
        raise Exception("RHEL-08-020104 - Failed")
    except:
      WARN("Verification failed - security context type of the non-default \
          tally directory is not faillog_t")
      raise Exception("RHEL-08-020104 - Failed")
    #part 2 verification
    INFO("RHEL-08-020104 - Part 2 verification")
    cmd_log = "sudo grep pwquality /etc/pam.d/system-auth \
      /etc/pam.d/password-auth | grep retry"
    try:
      info_log = self._run_cmd(cmd_log)
      WARN("Verification failed - security context type of the non-default \
        tally directory is not faillog_t")
      raise Exception("RHEL-08-020104 - Failed")
    except:
      INFO("Pass criteria - location of the non-default tally directory \
        for the pam_faillock module")
      INFO("RHEL-08-020104 - Verified part 2")

  def check_542959(self):
    """
    Args:
      Nothing
    Raises:
      Exception
    """
    STEP("RHEL-08-040161 - RHEL 8 must force a frequent session key \
      renegotiation for SSH connections to the server.")
    cmd_log = "sudo grep -ir RekeyLimit /etc/ssh/sshd_config*"
    info_log = self._run_cmd(cmd_log)
    INFO("Here's what the command returned:%s"%info_log)
    if "RekeyLimit 1G 1h" in info_log['stdout'] and \
      "#RekeyLimit 1G 1h" not in info_log['stdout']:
      INFO("RHEL-08-040161 SSH server is configured to force \
        frequent session key renegotiation")
      INFO("RHEL-08-040161 - Verified")
    else:
      WARN("Verification failed - SSH server is not configured to force \
        frequent session key renegotiation")
      raise Exception("RHEL-08-040161 - Failed")
  # def check_533674(self):
  #   """
  #   Args:
  #     Nothing
  #   Raises:
  #     Exception
  #   """
  #   STEP("Mount point check as part of 533674")
  #   INFO("Running the command and then validate")
  #   # Verify all non-root local partitions are mounted with the "nodev" option
  #   # with the following command:
  #   # $ sudo mount | grep '^/dev\S* on /\S' | grep --invert-match 'nodev'
  #   # If any output is produced, this is a finding.
  #   info_log = self._run_cmd_pxssh("sudo mount | grep '^/dev\S* on /\S' | grep --invert-match 'nodev'")
  #   if info_log:
  #     INFO("nodev option is configured for /var/log")
  #   else:
  #     WARN("nodev option is not set for /var/log")
  #   info_log = self._run_cmd_pxssh("sudo more /etc/fstab | grep /home")
  def check_563521(self):
    """
    Args:
      Nothing
    Raises:
      Exception
    """
    STEP("RHEL-08-010423: Check that the current GRUB 2 configuration \
      has poisoning of SLUB/SLAB objects enabled")
    cmd_log = "sudo grub2-editenv - list | grep slub_debug"
    info_log = self._run_cmd(cmd_log)
    INFO("This is part 1 check")
    INFO("Here's what the command returned:%s"%info_log)
    # Search for "slub_debug" settings in the content
    if 'slub_debug=P' in info_log['stdout'] and not info_log['stdout'].startswith('#'):
      INFO("Verified RHEL-08-010423 - GRUB 2 configuration has poisoning of \
      SLUB/SLAB objects enabled")
      INFO("RHEL-08-010423 - Part 1 Verified")
    else:
      WARN("Verification failed - GRUB 2 configuration does not have poisoning \
      of SLUB/SLAB objects enabled")
      raise Exception("RHEL-08-010423 - Failed")
    #part2 verification
    cmd_log = "sudo grep slub_debug /etc/default/grub"
    info_log = self._run_cmd(cmd_log)
    INFO("This is part 2 check")
    INFO("Here's what the command returned:%s"%info_log)
    # Define the regular expression pattern to match "slub_debug" settings
    if 'slub_debug=P' in info_log['stdout'] and info_log['stdout'].startswith('GRUB_CMDLINE_LINUX'):
      INFO("Verified RHEL-08-010423 - SLUB/SLAB objects is enabled by default \
      to persist in kernel updates")
      INFO("RHEL-08-010423 - Part 2 Verified")
    else:
      WARN("Verification failed - SLUB/SLAB objects is enabled by default to \
      persist in kernel updates")
      raise Exception("RHEL-08-010423 - Failed")

  def check_537661(self):
    """
    Args:
      Nothing
    Raises:
      Exception
    """
    STEP("RHEL-08-010421 -must clear the page allocator to prevent \
    use-after-free attacks.")
    cmd_log = "sudo grub2-editenv list | grep page_poison"
    info_log = self._run_cmd(cmd_log)
    INFO("This is part 1 check")
    INFO("Here's what the command returned:%s"%info_log)
    # Define the regular expression pattern to match "slub_debug" settings
    pattern = r"(?m)^\s*[^#]*\bpage_poison\s*=\s*([^\n#]*)"
    # Search for "slub_debug" settings in the content
    matches = re.findall(pattern, info_log['stdout'].strip())
    if matches:
      INFO("Verified RHEL-08-010421 - GRUB 2 configuration has page poisoning \
      is enabled")
      INFO("RHEL-08-010421 - Part 1 Verified")
    else:
      WARN("Verification failed - GRUB 2 configuration does not have page \
      poisoning is enabled")
      raise Exception("RHEL-08-010421- Failed")
    #part2 verification
    cmd_log = "sudo grep page_poison /etc/default/grub"
    info_log = self._run_cmd(cmd_log)
    INFO("This is part 2 check")
    INFO("Here's what the command returned:%s"%info_log)
    # Define the regular expression pattern to match "slub_debug" settings
    pattern = r"(?m)^\s*[^#]*\bpage_poison\s*=\s*([^\n#]*)"
    # Search for "slub_debug" settings in the content
    matches = re.findall(pattern, info_log['stdout'].strip())
    if matches:
      INFO("Verified RHEL-08-010421 - GRUB 2 configuration has page poisoning \
      is enabled")
      INFO("RHEL-08-010421 - Part 2 Verified")
    else:
      WARN("Verification failed - GRUB 2 configuration does not have page \
      poisoning is enabled")
      raise Exception("RHEL-08-010421 - Failed")

  def check_536746(self):
    """
    Args:
      Nothing
    Raises:
      Exception
    """
    STEP("RHEL-08-010360 -file integrity tool must notify the system \
    administrator when changes to the baseline configuration or anomalies \
    in the operation of any security functions are discovered within an \
    organizationally defined frequency")
    INFO("First ensuring AIDE is installed on the system")
    cmd_aide_check = "sudo ls -al /etc/cron.* | grep aide"
    info_log = self._run_cmd(cmd_aide_check)
    if "aide" in info_log['stdout']:
      INFO("AIDE is installed on the host")
    else:
      WARN("AIDE is not installed on the host")
      raise Exception("RHEL-08-010360 - Failed")
    #initializing the flags to false, these two should true for test to pass
    #by the end of execution
    controlling_script_flag = False
    file_application_notification = False
    # Check if the script file controlling the exec of the application exists
    try:
      cmd_log = "sudo grep aide /etc/crontab /var/spool/cron/root"
      info_log = self._run_cmd(cmd_log)
      if "/etc/crontab" in info_log['status'] and \
        "/var/spool/cron/root" in info_log['status']:
        INFO("Part 1 verified")
        controlling_script_flag = True
    except:
      WARN("script file controlling the execution of the file integrity \
      application does not exist")
    # Check if the file integrity app notifies designated personnel of changes
    try:
      cmd_log = "sudo more /etc/cron.weekly/aide"
      info_log = self._run_cmd(cmd_log)
      if "/usr/sbin/aide --check | /var/spool/mail -s" in info_log['status']:
        INFO("Part 2 verified and file integrity application will notify \
        designated personnel")
        file_application_notification = True
    except:
      WARN("file integrity application does not notify designated \
      personnel of changes")
    #final outcome
    if controlling_script_flag and file_application_notification:
      INFO("RHEL-08-010360 - Verified")
    else:
      WARN("Verification failed - file integrity tool not configured as \
      expected")
      raise Exception("RHEL-08-010360 - Failed")

  def check_542908(self):
    """
    Args:
      Nothing
    Raises:
      Exception
    """
    expected_aide_conf = """/usr/sbin/auditctl p+i+n+u+g+s+b+acl+xattrs+sha512
/usr/sbin/auditd p+i+n+u+g+s+b+acl+xattrs+sha512
/usr/sbin/ausearch p+i+n+u+g+s+b+acl+xattrs+sha512
/usr/sbin/aureport p+i+n+u+g+s+b+acl+xattrs+sha512
/usr/sbin/autrace p+i+n+u+g+s+b+acl+xattrs+sha512
/usr/sbin/rsyslogd p+i+n+u+g+s+b+acl+xattrs+sha512
/usr/sbin/augenrules p+i+n+u+g+s+b+acl+xattrs+sha512"""
    STEP("RHEL-08-030650 - Verify that Advanced Intrusion Detection Environment\
          (AIDE) is properly configured to use cryptographic mechanisms to prot\
         ect the integrity of audit tools.")
    cmd_log = "sudo grep -E '(\/usr\/sbin\/(audit|au|rsys))' /etc/aide.conf"
    info_log = self._run_cmd(cmd_log)
    INFO("Here's what the command returned:%s"%info_log)

    #Removing /r from stdout and trailing new line
    info_log['stdout'] = (info_log['stdout'].replace('\r', "")).rstrip()
    if expected_aide_conf in info_log['stdout'] \
      and not info_log['stdout'].startswith("#"):
      INFO("cryptographic mechanisms are being used is as expected")
      INFO("RHEL-08-030650 - Verified")
    else:
      WARN("Verification failed - cryptographic mechanisms are being used is \
           not as expected")
      raise Exception("RHEL-08-040161 - Failed")

  def check_537076(self):
    """
    Args:
      Nothing
    Raises:
      Exception
    """
    cmd_log = "sudo grep -i nopasswd /etc/sudoers /etc/sudoers.d/*"
    stdout = []
    try:
      info_log = self._run_cmd(cmd_log)
      INFO("Here's what the command returned:%s"%info_log)
      stdout.append(info_log['stdout'])
    except Exception as err:
      WARN("Command could have failed because some dir not found")
      INFO("Attempting to extract the stdout")
      info_log = str(err)
      INFO("Here's what the command returned:%s"%info_log)
      stdout = info_log[info_log.index('stdout')+9 : info_log.index('stderr')-3].split('\\r\\n')
      INFO("Display %s"%stdout)

    #verifying if "NOPASSWD" is present in the output
    for info in stdout:
      if "NOPASSWD" in info and not info.startswith("#"):
        status = True
        break
      status = False

    #Decision of part 2 verification of STIG based on status
    if status:
      WARN("Verification failed - users may not require password for\
           privilege escalation")
      raise Exception("RHEL-08-010380 - Failed")
    INFO("Verification passed - must require users to provide a password for \
          privilege escalation")
    INFO("RHEL-08-010380 - Verified")

  def rolling_reboot_hosts(self):
    """
    Rolling reboot hosts genesis workflow

    Returns:
      task_id(str): Task id to monitor rolling reboot of hosts
    """
    INFO("Rolling reboot hosts genesis workflow")
    cmd = "source /etc/profile; yes | rolling_restart -h"
    cluster_helper = ClusterHelper(cluster=self.cluster)
    kwargs = {"cvm_ip" : self.cluster.hypervisors[0].svm.ip}
    result = cluster_helper.execute(cmd, **kwargs)
    assert "ERROR" not in result, "Failed to start rolling reboot"
    task = re.search(r'ecli task.get [\w-]*', result).group()
    task_id = task.split(" ")[-1]
    self.monitor_rolling_reboot_hosts(task_id=task_id,
                                      timeout=3600*len(self.cluster.hypervisors))
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
        kwargs = {"cvm_ip" : self.cluster.hypervisors[0].svm.ip}
        result = cluster_helper.execute(cmd, **kwargs)
        output = json.loads(result)
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

  def _run_cmd_pxssh(self, cmd):
    """
    Args:
      cmd (str) : command to be run
    Raises:
      Exception
    Returns:
      conn.before
    """
    host_ip = self.cluster.hypervisors[0].ip
    conn = pxssh.pxssh()
    INFO("Command should be run on any host from cluster")
    INFO("Attempting command as nutant user on %s"%host_ip)
    conn.login(host_ip, "nutant", "RDMCluster.123")
    conn.sendline(cmd)
    conn.prompt(timeout=120)
    conn.close()
    INFO(conn.before)
    return conn.before

  def _run_cmd(self, cmd, username="nutant", password="RDMCluster.123", host_ip=None):
    """
    Establish connection using ssh and specified user
    Returns:
      connection objection
    Args:
      cmd (str) : command to be run
      username (str) : cmd to run as which user
      password (str) : creds for cmd to run
      host_ip (str) : defualt none, but otherwise ip address
    """
    if host_ip:
      INFO("Received IP during call : %s"%host_ip)
    else:
      INFO("Did not receive IP during call, init to default")
      host_ip = self.cluster.hypervisors[0].ip
    INFO("Command should be run on a host")
    INFO("Attempting command as %s user on %s"%(username, host_ip))
    ahv_conn = LinuxOperatingSystem.LinuxOperatingSystem(host_ip, \
      username, password)
    return ahv_conn.execute(cmd)

  def _get_security_params(self):
    """
    Func to get hypervisor security params before running the tests
    Args:
      Nothing
    Returns:
      security settings
    """
    INFO("Here's the security settings on AOS")
    cmd = "ncli cluster edit-hypervisor-security-params"
    INFO(self.cluster.hypervisors[0].svm.execute(cmd, timeout=180, ignore_errors=True, retries=2))
    return

  def _set_ncli_security(self):
    """
    Func to set ncli params before running the tests
    Args:
      Nothing
    Returns:
      Nothing
    """
    INFO("Attempting to set security-params for hypervisor")

    commands = ["ncli cluster edit-hypervisor-security-params enable-aide=true",
                "ncli cluster edit-hypervisor-security-params enable-high-strength-password=true",
                "ncli cluster edit-hypervisor-security-params enable-banner=true",
                "ncli cluster edit-hypervisor-security-params enable-core=false",
                "ncli cluster edit-hypervisor-security-params enable-logcore=false",
                "ncli cluster edit-hypervisor-security-params enable-memory-poison=true",
                "ncli cluster edit-hypervisor-security-params enable-itlb-multihit-mitigation=true",
                "ncli cluster edit-hypervisor-security-params enable-retbleed-mitigation=true"]

    for cmd in commands:
      INFO("Running cmd : %s"%cmd)
      self.cluster.hypervisors[0].svm.execute(cmd, timeout=180, ignore_errors=True, retries=2)

    #checking what all params set on cluster
    INFO("Latest settings on the cluster : %s"%self._get_security_params())

    #initiating rolling reboot before running the tests
    self.rolling_reboot_hosts()

  def _make_scanner_happy(self):
    """
    Func to set scanner happy before running the tests
    Args:
      Nothing
    Returns:
      Nothing
    """
    INFO("This is to make the scanner happy, run on host")
    cmd = "sudo /usr/libexec/stig.sh --make-scanner-happy"
    for host in self.cluster.hypervisors:
      INFO("Executing make scanner happy cmd as nutant user")
      self._run_cmd(cmd, username="nutant", password="RDMCluster.123", host_ip=host.ip)
    INFO("make scanner happy command executed successfully")
