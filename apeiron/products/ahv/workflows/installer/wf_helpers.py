"""
Copyright (c) 2024 Nutanix Inc. All rights reserved.

Author: pritam.chatterjee@nutanix.com
"""
# pylint: disable=import-error, unused-import, unused-argument, no-member
# pylint: disable=no-self-use, no-else-return, ungrouped-imports,
# pylint: disable=duplicate-string-formatting-argument, wrong-import-order
# pylint: disable=unused-variable, global-statement
# pylint: disable=ungrouped-imports, line-too-long, too-many-locals
# pylint: disable=unsubscriptable-object

import time
import pandas as pd
import tabulate
from framework.lib.nulog import INFO, STEP, WARN, ERROR
from libs.feature.installer.target.target import \
  TargetFactory
from libs.feature.installer.host_validation import \
  ValidationWithCallback
import workflows.acropolis.mjolnir.feature.installer.constants as const


class BaseHelper():
  """BaseHelper Class for AHV Installer"""
  # NOTE: Any global configs and data can be present here
  def __init__(self, cluster=None):
    """
    Args:
      cluster(obj) : cluster object
    Returns:
    Raises:
    """
    self.cluster = cluster


class HostHelper(BaseHelper):
  """HostHelper class for AHV Installer"""
  def validate_custom_iso_installer(self, **kwargs):
    """
    Validate custom ISO based installation
    Args:
    Retruns:
    Raises:
    """
    STEP("Creating and Preparing the Target")
    target = TargetFactory(**kwargs)
    target.create_target(cluster=self.cluster, **kwargs)
    # """
    # - Default gateway: 10.117.255.1
    # - VLAN ID: 194
    # - IT reserved range: 10.117.255.1 - 10.117.255.5
    # - Static range: 10.117.255.6 - 10.117.255.254
    # """
    STEP("Attaching Installation Media on Target")
    target.mount_media(**kwargs)
    const.CACHE['target'] = target
    # vnics_count = kwargs.pop('num_of_vnics', 2)
    STEP("Doing PowerCycle on Target to trigger installation")
    target.power_cycle()

  def validate_random_reboot(self, **kwargs):
    """
    Perform random reboot to disrupt installation
    Args:
    Retruns:
    Raises:
    """
    # STEP("Waiting for 600s to ensure installation kicks off")
    # time.sleep(30)
    # target = TargetFactory(**kwargs)
    target = const.CACHE['target']
    STEP("Waiting for 12 mins to ensure installation kicks off")
    time.sleep(720)
    STEP("Doing PowerCycle on Target to disrupt installation")
    target.power_cycle()

  def validate_disconnect_media(self, **kwargs):
    """
    Perform random reboot to disrupt installation
    Args:
    Retruns:
    Raises:
    """
    target = const.CACHE['target']
    STEP("Waiting for 12 mins to ensure installation kicks off")
    time.sleep(720)
    STEP("disconnect/connect media on Target to disrupt installation")
    target.disconnect_connect_media()

  def validate_post_install(self, **kwargs):
    """
    Validate AHV Server post installation
    Args:
    Retruns:
    Raises:
    """
    #default username and password post installation, this will not change
    target = const.CACHE['target']
    STEP("Verifying Hardware_config file present")
    assert target.confirm_file_existence(target.host_ip, "hardware_config.json"), \
      "Hardware_config.json file is not present"
    INFO("Hardware_config.json file is present")

    STEP("Verifying Factory config file present")
    assert target.confirm_file_existence(target.host_ip, "factory_config.json"), \
      "factory_config.json file is not present"
    INFO("factory_config.json file is present")

    STEP("Verifying the boot disk")
    INFO("if Install device was not provided, largest disk to be chosen")
    assert target.get_boot_disk(target.host_ip, target.install_device), \
      "AHV is installed on a different disk"
    INFO("AHV is installed on expected device")

    STEP("Verifying the Bond mode and Nic used")
    nic_info = target.get_nic_bonding(target.host_ip, target.bond_mode)
    INFO("Number of interfaces part of bond: %s" %nic_info[0])
    assert nic_info[1], "Wrong bond mode set"

    STEP("Verifying number of interfaces in interfaces")
    if target.number_of_nics:
      expected = 2 + target.number_of_nics
    else:
      expected = 2
    assert expected == nic_info[0], "Incorrect number of NIC's part of bond"
    INFO("Right number of devices part of nic bond")
    STEP("Cleaning up any added NIC interfaces")
    if target.number_of_nics:
      target.ucsm_handle.remove_vnics(target.number_of_nics)

    if target.secure_boot == "yes":
      STEP("Verifying secure boot status")
      assert target.get_secure_boot(target.host_ip), "Secure boot is not enabled on host!!"
      INFO("Secure boot is enabled as expected")

  def validate_disable_secure_boot(self, **kwargs):
    """
    Validate AHV Server disable secure boot WF
    Args:
    Retruns:
    Raises:
      assertion
    """
    target = const.CACHE['target']
    STEP("Disabling secure on Service profile")
    target.ucsm_handle.secure_boot_modify("no")
    INFO("Powercycling server to ensure SB settings are applied")
    target.power_cycle()
    INFO("Snooze time after powercycle")
    time.sleep(420)
    INFO("Waiting for server to boot up")
    if target.poll_ip(target.host_ip):
      assert not target.get_secure_boot(target.host_ip), "SB is not disabled!!"
    INFO("SB is disabled successfully and AHV reflects the same")

  def validate_power_ops(self, **kwargs):
    """
    Validate AHV Server installation steps for success
    Args:
    Retruns:
    Raises:
    """
    target = const.CACHE['target']
    STEP("power cycling server after installation")
    target.power_cycle()
    INFO("Snooze time after powercycle")
    time.sleep(420)
    INFO("Waiting for server to boot up")
    target.poll_ip(target.host_ip)
    INFO("Server booted up post powercycle")

    STEP("power on/off server check")
    INFO("powering off server")
    target.power_ops(desired_state="down")
    INFO("Sleep for 60 seconds to allow poweroff operation")
    time.sleep(60)
    INFO("Powering on server and allowing a minute for state to change")
    target.power_ops(desired_state="up")
    time.sleep(60)
    target.poll_ip(target.host_ip)
    INFO("Server booted up post power ON/OFF operation")

  def validate_install_success(self, **kwargs):
    """
    Validate AHV Server installation steps for success
    Args:
    Retruns:
    Raises:
    """
    target_name = kwargs.pop("target_name")
    target = TargetFactory(**kwargs)
    validator = ValidationWithCallback(**kwargs)
    identifier = target.get_target_identifier(cluster=self.cluster,
                                              target_name=target_name)
    results = {
      "step1": None,
      "step2": None,
      "step3": None,
      "step4": None,
      "step5": None,
      "step6": None
    }
    try:
      STEP(f"Validating Installation start on {target} with ID {identifier}")
      results["step1"] = validator.check_installation_start(
        identifier=identifier,
        retries=30,
        delay=20,
      )

      STEP(f"Validating Installation finish on {target} with ID {identifier}")
      results["step2"] = validator.check_installation_finish(
        identifier=identifier,
        retries=30,
        delay=20,
      )

      STEP(f"Validating Post install config on {target} with ID {identifier}")
      results["step3"] = validator.check_config_inprogress(
        identifier=identifier,
        retries=30,
        delay=20,
      )

      STEP(f"Validating Firstboot Start on {target} with ID {identifier}")
      results["step4"] = validator.check_firstboot_start(
        identifier=identifier,
        retries=30,
        delay=20,
      )

      STEP(f"Validating Firstboot Complete on {target} with ID {identifier}")
      results["step5"] = validator.check_firstboot_complete(
        identifier=identifier,
        retries=30,
        delay=20,
      )

      STEP(f"Validating Install Success {target} with ID {identifier}")
      results["step6"] = validator.check_success(
        identifier=identifier,
        retries=30,
        delay=30,
      )
      INFO(results)
      df = pd.DataFrame(results)
      assert "ERROR: Not Found" not in results["step6"]["log"], \
        "Failed to validate install success {target} with ID {identifier}"
      INFO(tabulate.tabulate(df.T, headers="keys", tablefmt="github"))
    except AssertionError as ex:
      df = pd.DataFrame(results)
        # NOTE: Collect the fatal message after implementing POST API
      target.capture_screenshot()
      INFO(tabulate.tabulate(df.T, headers="keys", tablefmt="github"))
      raise ex

  def validate_install_failure_config_val(self, **kwargs):
    """
    Validate AHV Server installation failure with given error msg
    Args:
    Retruns:
    Raises:
    """
    target_name = kwargs.pop("target_name")
    target = TargetFactory(**kwargs)
    retries = kwargs.pop("retries", 30)
    delay = kwargs.pop("delay", 30)
    validator = ValidationWithCallback(**kwargs)
    identifier = target.get_target_identifier(cluster=self.cluster,
                                              target_name=target_name)
    STEP(f"Validating Installation finish on {target} with ID {identifier}")
    results = validator.check_installation_finish(
      identifier=identifier,
      retries=retries,
      delay=delay,
    )
    target.capture_screenshot()
    # error not found
    assert "ERROR: Not Found" in results['log'], \
      ("This installation was expected to fail "
       "at config validation, but it passed")
    INFO("Installation failed as expected")

  def clean_up(self, **kwargs):
    """
    Teardown
    Args:
    Retruns:
    Raises:
    """
    img_name = kwargs.pop("img_name", "AHV_SERVER")
    target_name = kwargs.pop("target_name", "ahv_server_1")
    target = TargetFactory(**kwargs)
    INFO(f"Deleting the Target: {target_name}")
    target.delete_target(cluster=self.cluster,
                         target_name=target_name)

    INFO(f"Deleting AHV Installer image {img_name}")
    target.delete_install_media(cluster=self.cluster,
                                img_name=img_name)


class AhvInstallerHelper(HostHelper):
  """AhvInstallerHelper class"""
  def __init__(self, **kwargs):
    """
    Args:
    Returns:
    Raises:
    """
    super(AhvInstallerHelper, self).__init__(**kwargs)
    self.host_helper = HostHelper(**kwargs)

  def validate_setup_compatibility(self, **kwargs):
    """
    Args:
    Returns:
    Raises:
    """
    INFO("No compatibility checks added yet!")
