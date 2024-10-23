"""
Copyright (c) 2022 Nutanix Inc. All rights reserved.

Author: pritam.chatterjee@nutanix.com
"""
# pylint: disable=import-error, fixme, no-self-use, arguments-differ
try:
  from framework.lib.nulog import INFO  # pylint: disable=unused-import

  EXECUTOR = "nutest"
except Exception:  # pylint: disable=broad-except
  from libs.ahv.framework.proxy_logging \
    import INFO  # pylint: disable=unused-import

  EXECUTOR = "mjolnir"
from libs.ahv.workflows.gos_qual.lib.base.abstracts \
  import AbstractVerifier


class ValidateBootTypeOnVm(AbstractVerifier):
  """ValidateArch"""
  VALIDATORS = {
    "legacy": ["_verify_legacy_boot"],
    "uefi": ["_verify_uefi_boot"],
    "secureboot": ["_verify_secure_boot"],
    "vtpm": ["_verify_vtpm_boot"],
    "vtpm_secureboot": ["_verify_secure_boot", "_verify_vtpm_boot"],
    "credentialguard": ["_verify_secure_boot", "_verify_cg_boot"],
    "vtpm_credentialguard": ["_verify_cg_boot",
                             "_verify_vtpm_boot"]
  }

  def verify(self, **params):
    """
    Verify VM boot type
    Args:
    Returns:
    """
    extra_params = params.get("extra_params")
    vm_name = extra_params.get("vm_name")
    modules = extra_params.get("modules")
    expected = extra_params.get("boot")
    assert expected in self.VALIDATORS, "Failed to verify boot, " \
                                        "should be one of: %s" % self.VALIDATORS
    for validate in self.VALIDATORS[expected]:
      # fix for bug ENG-495202
      if expected == "credentialguard":
        expected = "credentialguard_secureboot"
      validator = getattr(self, validate)
      cache = modules.get("cache")
      acli_vm = cache.get_entity(entity_type="acli_vm", name=vm_name)
      config = acli_vm.get()["config"]
      boot_config = config.get("boot")
      boot_config.update(config.get("vtpm_config", {}))
      validator(boot_config)
      # assert actual in expected, "Failed to validate guest OS boot type " \
      #                            "Expected: [%s] Found: [%s]" % (expected,
      #                                                            actual)

  def _verify_legacy_boot(self, vm_config):
    """
    Verify VM boot type
    Args:
      vm_config(dict):
    Returns:
    """
    assert not vm_config.get("uefi_boot"), "Failed to validate Legacy boot " \
                                           "config for VM"
    INFO("Legacy validation successful!")

  def _verify_uefi_boot(self, vm_config):
    """
    Verify VM boot type
    Args:
      vm_config(dict):
    Returns:
    """
    assert vm_config.get("uefi_boot"), "Failed to validate UEFI boot " \
                                       "config for VM"
    INFO("UEFI validation successful!")

  def _verify_secure_boot(self, vm_config):
    """
    Verify VM boot type
    Args:
      vm_config(dict):
    Returns:
    """
    assert vm_config.get("secure_boot"), "Failed to validate secureboot boot " \
                                         "config for VM"
    INFO("Secureboot validation successful!")

  def _verify_vtpm_boot(self, vm_config):
    """
    Verify VM boot type
    Args:
      vm_config(dict):
    Returns:
    """
    assert vm_config.get("is_enabled"), "Failed to validate vTPM boot " \
                                        "config for VM"
    assert vm_config.get("vtpm_disk_spec"), "Failed to validate vTPM boot " \
                                            "config for VM"
    INFO("vTPM validation successful!")

  def _verify_cg_boot(self, vm_config):
    """
    Verify VM boot type
    Args:
      vm_config(dict):
    Returns:
    """
    assert vm_config.get("windows_credential_guard"), \
      "Failed to validate CG boot " \
      "config for VM"
    INFO("CG validation successful!")
