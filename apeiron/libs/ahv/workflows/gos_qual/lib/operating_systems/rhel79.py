"""
Copyright (c) 2021 Nutanix Inc. All rights reserved.

Author: pritam.chatterjee@nutanix.com
"""
# pylint: disable=import-error, unused-import
try:
  from framework.lib.nulog import INFO, ERROR, STEP, \
    WARN

  EXECUTOR = "nutest"
except Exception:  # pylint: disable=broad-except
  from libs.ahv.framework.proxy_logging \
    import INFO, ERROR, STEP, WARN

  EXECUTOR = "mjolnir"
from libs.ahv.workflows.gos_qual.lib.operating_systems. \
  default import Default
from libs.ahv.workflows.gos_qual.configs.constants \
  import RHCERT_USERNAME, RHCERT_PASSWORD
from libs.ahv.workflows.gos_qual.lib.base.utilities \
  import retry


class Rhel79(Default):
  """Rhel79 class"""

  def enable_subscription(self, **kwargs):
    """
    Enable subscription for RHEL systems
    Returns:
    """
    cmd = "subscription-manager list | grep Status:"
    res = self.conn.execute(cmd, **kwargs)
    if "Subscribed" in res:
      return res
    cmd = "subscription-manager register --username %s " \
          "--password %s --auto-attach" \
          % (RHCERT_USERNAME, RHCERT_PASSWORD)
    return self.conn.execute(cmd, **kwargs)

  def enable_kernel_debuginfo_repo(self):
    """
    Enables specific repo from RHEL kernel debuginfo pkgs
    Returns:
    """
    return self.enable_repo("rhel-7-server-debug-rpms")

  def enable_rhcert_repo(self):
    """
    Enables specific repo from RHEL certification pkgs
    Returns:
    """
    return self.enable_repo("rhel-7-server-cert-rpms")

  def enable_repo(self, repo_id, **kwargs):
    """
    Enables specific repo from RHEL subscription
    Args:
      repo_id(str): Repo id: eg. rhel-7-server-debug-rpms
    Returns:
    """
    cmd = "subscription-manager repos --enable=%s" % repo_id
    return self.conn.execute(cmd, **kwargs)

  def install_rhcert_packages(self, **kwargs):
    """
    Installs redhat-certification related packages
    Args:
    Returns:
    """
    packages = ['kernel-debuginfo-$(uname -r)',
                'kernel-debuginfo-common-x86_64-$(uname -r)',
                'redhat-certification',
                'redhat-certification-backend',
                'redhat-certification-hardware',
                'python-django',
                'python-django-bash-completion'
               ]
    return self.install_packages(packages, **kwargs)

  def install_packages(self, packages, **kwargs):
    """
    Install given packages using yum
    Args:
      packages(str, list): Single packages or list of packages
    Returns:
    """
    if isinstance(packages, str):
      packages = [packages]
    for pkg in packages:
      cmd = "yum install %s -y" % pkg
      self.conn.execute(cmd, **kwargs)

  def verify_packages(self, packages, **kwargs):
    """
    Verify if the packages are installed
    Args:
      packages(str, list): Single package or list of packages
    Returns:
      result(bool)
    """
    result = False
    if isinstance(packages, str):
      packages = [packages]
    for pkg in packages:
      cmd = "rpm -qa | grep %s" % pkg
      res = self.conn.execute(cmd, **kwargs)
      if pkg in res:
        result = True
    return result

  def start_rhcertd_service(self, **kwargs):
    """
    Start the rhel certification service
    Args:
    Returns:
      stdout(dict)
    """
    cmd = "rhcertd start"
    return self.conn.execute(cmd, **kwargs)

  def get_edition_info(self):
    """
    Get edition info
    Args:
    Returns:
      stdout(dict)
    """
    INFO(self)
    return "Server"

  def get_build_info(self, **kwargs):
    """
    Get build info
    Args:
    Returns:
      stdout(dict)
    """
    return "NA"

  @retry(times=3, interval=5, exceptions=(ValueError, TypeError,
                                          AssertionError))
  def install_os_updates(self, vm, **kwargs):
    """
    Install OS updates
    Args:
      vm(object): vm object
    Returns:
      stdout(dict)
    """
    cmd = "yum update -y"
    try:
      task_id = self.conn.run_shell_command_handsoff(cmd, **kwargs)
      self.conn.wait_handsoff_task_complete(task_id, 1800)
      INFO("Rebooting VM!!")
      self.reboot()
      self.verify_os_boot_post_reboot(vm)
    except:  # pylint: disable=bare-except
      self.verify_os_boot()
      self.verify_os_boot_post_reboot(vm)

  def install_fio(self):
    """
      Install fio within guest

      Returns:
        None
    """
    # fixme : no need to implement for linux
    cmd = "yum install fio -y"
    return self.conn.execute(cmd)
