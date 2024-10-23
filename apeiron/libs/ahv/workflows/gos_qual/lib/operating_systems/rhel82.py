"""
Copyright (c) 2021 Nutanix Inc. All rights reserved.

Author: pritam.chatterjee@nutanix.com
"""
# pylint: disable=import-error
from libs.ahv.workflows.gos_qual.lib.operating_systems.\
  rhel79 import Rhel79


class Rhel82(Rhel79):
  """Rhel82 class"""
  def enable_kernel_debuginfo_repo(self):
    """
    Enables specific repo from RHEL kernel debuginfo pkgs
    Returns:
    """
    return self.enable_repo("rhel-8-for-x86_64-baseos-debug-rpms")

  def enable_rhcert_repo(self):
    """
    Enables specific repo from RHEL certification pkgs
    Returns:
    """
    return self.enable_repo("cert-1-for-rhel-8-x86_64-rpms")

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
                'redhat-certification-hardware'
               ]
    return self.install_packages(packages, **kwargs)
