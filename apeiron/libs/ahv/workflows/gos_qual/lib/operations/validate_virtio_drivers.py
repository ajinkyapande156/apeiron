"""
Copyright (c) 2021 Nutanix Inc. All rights reserved.

Author: arundathi.a@nutanix.com
"""
import re
import copy
from framework.lib.utils.version import Version
# pylint: disable=import-error, fixme
# pylint: disable=no-self-use
try:
  from framework.lib.nulog import INFO, ERROR, WARN, DEBUG  # pylint: disable=unused-import
  EXECUTOR = "nutest"
except Exception:  # pylint: disable=broad-except
  from libs.ahv.framework.proxy_logging \
    import INFO, ERROR, WARN, DEBUG  # pylint: disable=unused-import
  EXECUTOR = "mjolnir"
from libs.ahv.workflows.gos_qual.lib.base.abstracts \
  import AbstractVerifier
from libs.ahv.workflows.gos_qual.lib.base.gos_errors \
  import PostVerificationFailed
from libs.ahv.workflows.gos_qual.configs \
  import constants as constants


class VerifyVirtioDrivers(AbstractVerifier):
  """VerifyOsBoot class"""

  def verify(self, **params):
    """
    Verify if the vm has virtio drivers installed
    Args
      guest(object): GOS guest object
    Kwargs:
    Returns:
    Raises:
      PostVerificationFailed
    """

    extra_params = params.get("extra_params")
    if extra_params["vendor"] not in ["microsoft"]:
      INFO("Skipping virtio driver check for Linux OS")
      return True
    # INDICES = list()
    virtio_drivers = copy.deepcopy(constants.VIRTIO_DRIVERS)
    modules = extra_params.get("modules")
    #vm = modules.get("rest_vm")
    os = modules.get("rpc")
    virtio_installer_path = params.get("virtio")
    virtio_driver_upgrade_iso = params.get("virtio_upgrade_path")
    if virtio_driver_upgrade_iso:
      virtio_installer_path = virtio_driver_upgrade_iso
    installed_version = os.get_installer_version(virtio_installer_path)
    if Version(installed_version) > Version(constants.VIRTIO_120):
      virtio_drivers = copy.deepcopy(constants.VIRTIO_DRIVERS_121)
    INFO("Verifying if the vm has Virtio drivers")
    try:
      virtio_drivers = os.get_virtio_driver_info(virtio_drivers)
      for driver in virtio_drivers:
        INFO("DRIVER INFO:{0} --> {1}".format(driver, virtio_drivers[driver]))
      # Version check
      for driver in virtio_drivers:
        if virtio_drivers[driver][constants.VERSION]:
          driver_version_guest = virtio_drivers[driver][constants.VERSION]
          search_version = re.compile(r'^%s' % installed_version)
          assert re.match(search_version, driver_version_guest), \
            "Virtio Version does not match"
        assert virtio_drivers[driver][constants.IS_SIGNED] == "True", \
          "Driver: %s not signed" % driver
      extra_params["virtio_version"] = installed_version
      #Write to disk
      os.write_to_disk()
      #run n/w workload
      os.ping_server()
    except Exception:  # pylint: disable=broad-except
      raise PostVerificationFailed("Failed to verify virtio versions")
