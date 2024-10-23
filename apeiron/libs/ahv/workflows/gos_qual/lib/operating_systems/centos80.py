"""
Copyright (c) 2022 Nutanix Inc. All rights reserved.

Author: pritam.chatterjee@nutanix.com
"""
# pylint: disable=import-error
from libs.ahv.workflows.gos_qual.lib.operating_systems.\
  rhel79 import Rhel79


class Centos80(Rhel79):
  """Centos80 class"""
  def install_fio(self):
    """
      Install fio within guest

      Returns:
        None
    """
    cmd = "wget http://mirror.centos.org/centos/8-stream/BaseOS/x86_64/os/" \
          "Packages/centos-gpg-keys-8-3.el8.noarch.rpm"
    self.conn.run_shell_command_sync(cmd)
    cmd = "sudo rpm -i centos-gpg-keys-8-3.el8.noarch.rpm"
    self.conn.run_shell_command_sync(cmd)
    cmd = "dnf --disablerepo '*' --enablerepo=extras swap " \
          "centos-linux-repos centos-stream-repos -y"
    self.conn.run_shell_command_sync(cmd)
    cmd = "yum install fio -y"
    self.conn.run_shell_command_sync(cmd)
    cmd = "whereis fio"
    (_, stdout, _) = self.conn.run_shell_command_sync(cmd)
    fio_locs = stdout.split()
    if "/usr/local/bin/fio" not in fio_locs:
      cmd = "ln -sf %s /usr/local/bin/fio" % fio_locs[1].strip()
      self.conn.execute(cmd)
