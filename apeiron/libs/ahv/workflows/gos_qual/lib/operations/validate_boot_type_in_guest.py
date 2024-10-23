"""
Copyright (c) 2022 Nutanix Inc. All rights reserved.

Author: pritam.chatterjee@nutanix.com
"""
# pylint: disable=import-error, fixme, arguments-differ
try:
  from framework.lib.nulog import INFO, ERROR, WARN, DEBUG  # pylint: disable=unused-import
  EXECUTOR = "nutest"
except Exception:  # pylint: disable=broad-except
  from libs.ahv.framework.proxy_logging \
    import INFO, ERROR, WARN, DEBUG  # pylint: disable=unused-import
  EXECUTOR = "mjolnir"
from libs.ahv.workflows.gos_qual.lib.base.abstracts \
  import AbstractVerifier


class ValidateBootTypeInGuest(AbstractVerifier):
  """ValidateArch"""
  VALIDATORS = {
    "legacy": ["verify_uefi_boot"],
    "uefi": ["verify_uefi_boot"],
    "secureboot": ["verify_secure_boot"],
    "vtpm": ["verify_vtpm_boot"],
    "vtpm_secureboot": ["verify_secure_boot", "verify_vtpm_boot"],
    "credentialguard": ["verify_secure_boot", "verify_cg_boot"],
    "vtpm_credentialguard": ["verify_cg_boot",
                             "verify_vtpm_boot"]
  }

  def verify(self, **params):
    """
    Verify OS boot type
    Args:
    Returns:
    """
    DEBUG(self)
    extra_params = params.get("extra_params")
    expected = extra_params.get("boot")
    os = extra_params["modules"]["rpc"]
    assert expected in self.VALIDATORS, "Failed to verify boot, " \
                                        "should be one of: %s" % self.VALIDATORS
    for validate in self.VALIDATORS[expected]:
      # fix for bug ENG-495202
      if expected == "credentialguard":
        expected = "credentialguard_secureboot"
      validator = getattr(os, validate)
      actual = validator()
      assert actual in expected, "Failed to validate guest OS boot type " \
                                 "Expected: [%s] Found: [%s]" % (expected,
                                                                 actual)
    extra_params["detected_boot_type"] = expected
