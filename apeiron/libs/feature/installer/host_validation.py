"""
Copyright (c) 2024 Nutanix Inc. All rights reserved.

Author: umashankar.vd@nutanix.com

Host specific validation post installation
"""
# pylint: disable=no-self-use, invalid-name, using-constant-test, no-else-return
# pylint: disable=unused-variable, unused-import, no-member
# pylint: disable=too-many-branches, too-many-statements, unused-argument
# pylint: disable=ungrouped-imports, line-too-long, too-many-locals
# pylint: disable=broad-except, singleton-comparison, bad-continuation
# pylint: disable=inconsistent-return-statements
#ahv_conn.execute("mkdir neg_scenario;cd neg_scenario;mkdir metadata;echo '%s' > metadata.installer.json;wget http:..endor.dyn.nutanix.com.builds.ahv-builds.10.10.0.10.0-663.iso.AHV-DVD-x86_64-10.0-663.iso;%s" %(neg_json["incorrect_ip"],command))
import re

from framework.lib.nulog import INFO, WARN, DEBUG, ERROR
import framework.operating_systems.operating_system.linux_operating_system \
  as LinuxOperatingSystem
from framework.exceptions.interface_error import NuTestCommandExecutionError
import workflows.acropolis.mjolnir.feature.installer.constants as const
from libs.framework.mjolnir_executor import use_executor


class HostValidation:
  """
  Class for performing validations on host setup by installer
  """

  def __init__(self, host_ip):
    """
    Args:
      host_ip(str) : Server management IP address
    Returns:
    Raises:
    """
    # use AHV gateway so it is not dependent on SSH/creds hardcoded
    # def run method -
    # basic minimal check - should not be junk and present
    self.host_ip = host_ip
    self.username = "root"
    self.password = "nutanix.4u"

  def network_validation(self, expected_num_int, bond_type):
    """
    Args:
      expected_num_int(int) : number of interfaces
      bond_type(str) : Bond type
    Returns:
    Raises:
    """
    #obtain bond mode and number of devices part of it from host
    #compare it with expected number
    command = "ovs-appctl bond.list"
    response = self._execute_on_host(self.host_ip, command)
    INFO("Here's what the command returned : %s " %response)
    INFO("Trying to identify number of interfaces")

    INFO("Trying to identify Bond mode")

  def config_files(self):
    """
    Args:
    Returns:
    Raises:
    """
    #check if hw_config file is present and fact.json
    #print the same

  def ahv_gateway(self):
    """
    Args:
    Returns:
    Raises:
    """

  def _execute_on_host(self, host_ip, cmd):
    """
    Args:
      host_ip(str) : Server management IP address
      cmd(str) : command to be run on host
    Returns:
    Raises:
    """
    #execute command and return stdout
    ahv_conn = LinuxOperatingSystem.LinuxOperatingSystem\
      (host_ip, self.username, self.password)
    INFO("Established connection as: %s " %self.username)
    return ahv_conn.execute(cmd)


class ValidationWithCallback:
  """ValidationWithCallback"""
  def __init__(self, **kwargs):
    """
    Initialize a callback server for monitoring AHV Server installation
    Args:
    Returns:
    Raises:
    """
    self.callback_server = kwargs.get("callback_server",
                                      const.CALLBACK_SERVER)
    self.username = kwargs.get("username", const.CALLBACK_USER)
    self.password = kwargs.get("password", const.CALLBACK_PASSWORD)
    self.log_file = kwargs.get("log_file", const.CALLBACK_LOG)
    self.conn = LinuxOperatingSystem.LinuxOperatingSystem \
      (self.callback_server, self.username, self.password)
    test_cmd = "date"
    self.conn.execute(test_cmd)
    DEBUG(f"Connection to {self.callback_server} successful")

  def check_installation_start(self, **kwargs):
    """
    Validate Installation Start
    Args:
    Returns:
    Raises:

    Logs:
    10.117.188.114 - - [09/Aug/2024:09:52:04 +0000] "GET /?stage=started HTTP/1.1" 200 2228 "-" "curl/7.61.1"
    """
    identifier = kwargs.pop("identifier")
    assert identifier, ("An identifier must be specified as callback_server "
                        "is a shared resource")
    try:
      details = self._parse(identifier, "stage=started", **kwargs)
    except AssertionError:
      details = self._get_dummy_details("stage=started")
    return details

  def check_installation_finish(self, **kwargs):
    """
    Validate Installation Finish
    Args:
    Returns:
    Raises:

    Logs:
    10.117.186.232 - - [09/Aug/2024:09:56:20 +0000] "GET /?stage=finished HTTP/1.1" 200 2228 "-" "curl/7.61.1"
    """
    identifier = kwargs.pop("identifier")
    assert identifier, ("An identifier must be specified as callback_server "
                        "is a shared resource")
    try:
      details = self._parse(identifier, "stage=finished", **kwargs)
    except AssertionError:
      details = self._get_dummy_details("stage=finished")
    return details

  def check_config_inprogress(self, **kwargs):
    """
    Validate Post install task Inprogress
    Args:
    Returns:
    Raises:

    Logs:
    10.117.188.114 - - [09/Aug/2024:10:02:33 +0000] "POST /?stage=in_progress&step=info HTTP/1.1" 404 198 "-" "Python-urllib/3.6"
    """
    identifier = kwargs.pop("identifier")
    assert identifier, ("An identifier must be specified as callback_server "
                        "is a shared resource")
    try:
      details = self._parse(identifier, "stage=in_progress&step=info",
                            **kwargs)
    except AssertionError:
      details = self._get_dummy_details("stage=in_progress&step=info")
    return details

  def check_firstboot_start(self, **kwargs):
    """
    Validate firstboot script running
    Args:
    Returns:
    Raises:

    Logs:
    10.117.188.114 - - [09/Aug/2024:10:02:33 +0000] "POST /?stage=in_progress&stage=Running%20firstboot%20scripts HTTP/1.1" 404 198 "-" "Python-urllib/3.6"
    """
    identifier = kwargs.pop("identifier")
    assert identifier, ("An identifier must be specified as callback_server "
                        "is a shared resource")
    try:
      details = self._parse(
        identifier,
  "stage=in_progress&step=Running%20firstboot%20scripts",
        **kwargs)
    except AssertionError:
      details = self._get_dummy_details(
        "stage=in_progress&step=Running%20firstboot%20scripts")
    return details

  def check_firstboot_complete(self, **kwargs):
    """
    Validate firstboot script completed
    Args:
    Returns:
    Raises:

    Logs:
    10.117.188.114 - - [09/Aug/2024:10:05:36 +0000] "POST /?stage=in_progress&stage=Last%20reboot%20complete HTTP/1.1" 404 198 "-" "Python-urllib/3.6"
    """
    identifier = kwargs.pop("identifier")
    assert identifier, ("An identifier must be specified as callback_server "
                        "is a shared resource")
    try:
      details = self._parse(
        identifier,
        "stage=in_progress&step=Last%20reboot%20complete", **kwargs)
    except AssertionError:
      details = self._get_dummy_details(
        "stage=in_progress&step=Last%20reboot%20complete")
    return details

  def check_success(self, **kwargs):
    """
    Validate install successful
    Args:
    Returns:
    Raises:

    Logs:
    10.117.188.114 - - [09/Aug/2024:10:06:21 +0000] "GET /?stage=successful HTTP/1.1" 200 2228 "-" "Python-urllib/3.6"
    """
    identifier = kwargs.pop("identifier")
    assert identifier, ("An identifier must be specified as callback_server "
                        "is a shared resource")
    try:
      details = self._parse(
        identifier,
        "stage=successful",
        **kwargs
      )
    except AssertionError:
      details = self._get_dummy_details(
        "stage=successful")
    return details

  @use_executor
  def _parse(self, identifier, string, **kwargs):
    """
    Internal method
    Args:
      identifier(str):
      string (str):
    Returns:
    """
    res = self._grep(identifier)
    assert not res['status'], (f"No installer callback logs present"
                               f"for {identifier}")
    data = res['stdout']
    INFO(f"Log: {data}")
    data = [line.strip() for line in data.split("\n") if line]
    line = self._search(string, data)
    assert line, (f"No installer callback logs present for {identifier} "
                  f"and step {string}")
    details = self._extract_details(line)
    return details

  def _extract_details(self, line):
    """
    Internal method
    Args:
      line(str):
    Returns:
    """
    details = dict()
    details['stage'] = re.search(r'stage=(\w+)', line).groups()[0]
    details['ip'] = re.search(r'^(\d{1,3}.\d{1,3}.\d{1,3}.\d{1,3})',
                             line).groups()[0]
    details['timestamp'] = re.search(
      r'\[(\w+/\w+/\w+:\w+:\w+:\w+\s+\+\d+)\]', line).groups()[0]
    details['log'] = line
    return details

  def _get_dummy_details(self, string):
    """
    Internal method
    Args:
      string(str):
    Returns:
    """
    return {
      "stage": string,
      "ip": "-",
      "timestamp": "-",
      "log": "ERROR: Not Found"
    }

  def _search(self, string, data):
    """
    Internal method
    Args:
      data(str):
      string(str):
    Returns:
    """
    pattern = re.compile(string)
    for line in data:
      if re.search(pattern, line):
        return line

  def _grep(self, identifier):
    """
    Internal method
    Args:
      identifier(str):
    Returns:
    """
    cmd = f"grep {identifier} {self.log_file}"
    return self.conn.execute(cmd,
                            ignore_errors=True,
                            run_as_root=True)
