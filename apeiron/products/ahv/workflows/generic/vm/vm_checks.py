"""
Checks/validations related to VMs
"""
#pylint: disable=no-else-return, inconsistent-return-statements, protected-access
import re
from datetime import datetime

from framework.lib.nulog import INFO
from workflows.acropolis.upgrade.ahv_newformat_version \
  import get_ahv_ver_new_or_old_format


def is_vm_supported(cluster, features=""):
  """
  Check if VM creation is supported on the cluster based on
  software and hardwre available
  Args:
    cluster(object): NuTest Cluster object
    features(str): Comma separated list of VM features
  Returns:
    (bool): True if VM creation is supported, False otherwise
  """
  if "vtpm" in features:
    if not is_vtpm_supported(cluster):
      return False
  if "credential_guard" in features:
    if not is_cg_supported(cluster):
      return False

  return True

def is_lm_supported(cluster, features="", boot_type=""):
  """
  Check if VM Migration is supported on the cluster based on
  software and hardwre available
  Args:
    cluster(object): NuTest Cluster object
    features(str): Comma separated list of VM features
    boot_type(str): VM boot type
  Returns:
    (bool): True if VM Migration is supported, False otherwise
  """
  if "credential_guard" in features:
    if not is_cg_lm_supported(cluster):
      return False

  if ("hardware_virtualization" in features and "secure" not in boot_type):
    if not is_hw_virt_lm_supported(cluster):
      return False

  if "cpu_passthru" in features:
    INFO("Live migration is not supported for CPU Passthrough VMs")
    return False

  if cluster._metadata["nodes_cache"]["nodes_count"] == 1:
    INFO("Live migration is not supported on 1 node cluster")
    return False

  return True

def is_vtpm_supported(cluster):
  """
  Check if vTPM VM creation is supported on the cluster
  vTPM supported started from - AOS 6.5.1 with AHV 20220304.242
  Args:
    cluster(object): NuTest Cluster object
  Returns:
    is_supported(bool): True if supported, False otherwise
  """
  min_support_ahv_version = "20220304.242"
  min_support_aos_version = "6.5.1"
  aos_versions = get_aos_versions(cluster)
  ahv_versions = get_ahv_versions(cluster)
  is_supported = True

  for ahv_version in ahv_versions:
    if not is_ahv_greater_than_equal_to(ahv_version, min_support_ahv_version):
      INFO("vTPM VM creation is not supported on this cluster as AHV version:"\
           " %s is less than min supported AHV version: %s" \
           % (ahv_version, min_support_ahv_version))
      return False

  for aos_version in aos_versions:
    if not is_aos_greater_than_equal_to(aos_version, min_support_aos_version):
      INFO("vTPM VM creation is not supported on this cluster as AOS version:"\
           " %s is less than min supported AOS version: %s" \
           % (aos_version, min_support_aos_version))
      return False

  return is_supported

def is_cg_supported(cluster):
  """
  Check if CG VM creation is supported on the cluster
  CG is supported starting from - AOS 6.7 with AHV 20230302.207 on non Intel
  cluster
  Args:
    cluster(object): NuTest Cluster object
  Returns:
    is_supported(bool): True if supported, False otherwise
  """
  models = cluster.metadata_helper.get_hardware_models()
  non_intel = False
  for model in models:
    if "nx" not in model.lower():
      INFO("Found non intel nodes on the cluster")
      non_intel = True
      break
  if not non_intel:
    return True

  min_support_ahv_version = "20230302.207"
  min_support_aos_version = "6.7"
  aos_versions = get_aos_versions(cluster)
  ahv_versions = get_ahv_versions(cluster)
  is_supported = True

  for ahv_version in ahv_versions:
    if not is_ahv_greater_than_equal_to(ahv_version, min_support_ahv_version):
      INFO("CG VM creation is not supported on this cluster as AHV version:"\
           " %s is less than min supported AHV version: %s" \
           % (ahv_version, min_support_ahv_version))
      return False

  for aos_version in aos_versions:
    if not is_aos_greater_than_equal_to(aos_version, min_support_aos_version):
      INFO("CG VM creation is not supported on this cluster as AOS version:"\
           " %s is less than min supported AOS version: %s" \
           % (aos_version, min_support_aos_version))
      return False

  return is_supported

def is_cg_lm_supported(cluster):
  """
  Check if Credential Guard VM Live Migration is supported or not
  Args:
    cluster(object): NuTest cluster object
  Returns:
    is_supported(bool): True if supported, False otherwise
  """
  min_support_ahv_version = "20230302.100001"
  min_support_aos_version = "6.8"
  aos_versions = get_aos_versions(cluster)
  ahv_versions = get_ahv_versions(cluster)
  is_supported = True

  for ahv_version in ahv_versions:
    if not is_ahv_greater_than_equal_to(ahv_version, min_support_ahv_version):
      INFO("CG VM Live migration is not supported on this cluster as "\
           "AHV version: %s is less than min supported AHV version: %s" \
           % (ahv_version, min_support_ahv_version))
      return False

  for aos_version in aos_versions:
    INFO("aos version: %s" % aos_version)
    if not is_aos_greater_than_equal_to(aos_version, min_support_aos_version):
      INFO("CG VM Live migration is not supported on this cluster as "\
           "AOS version: %s is less than min supported AOS version: %s" \
           % (aos_version, min_support_aos_version))
      return False

  # Hardware check, NX nodes with G5 or below don't support CG VMs Migration
  models = cluster.metadata_helper.get_hardware_models()
  for model in models:
    match = re.match(".*-.*-G[1-5]", model)
    match1 = re.match("NX-[^-]*$", model)
    if match or match1:
      INFO("CG VM Live Migration is not supported on model: %s" % model)
      return False

  return is_supported

def is_hw_virt_lm_supported(cluster):
  """
  Check if HW_Virt enabled VM Live Migration is supported or not
  Args:
    cluster(object): NuTest cluster object
  Returns:
    is_supported(bool): True if supported, False otherwise
  """
  min_support_ahv_version = "10.0-1"
  min_support_aos_version = "6.9"
  aos_versions = get_aos_versions(cluster)
  ahv_versions = get_ahv_versions(cluster)
  is_supported = True

  for ahv_version in ahv_versions:
    if not is_ahv_greater_than_equal_to(ahv_version, min_support_ahv_version):
      INFO("HW_Virt VM Live migration is not supported on this cluster as "\
           "AHV version: %s is less than min supported AHV version: %s" \
           % (ahv_version, min_support_ahv_version))
      return False

  for aos_version in aos_versions:
    INFO("aos version: %s" % aos_version)
    if not is_aos_greater_than_equal_to(aos_version, min_support_aos_version):
      INFO("HW_Virt VM Live migration is not supported on this cluster as "\
           "AOS version: %s is less than min supported AOS version: %s" \
           % (aos_version, min_support_aos_version))
      return False

  # Hardware check, NX nodes with G5 or below don't support HW_Virt
  # VMs Migration
  models = cluster.metadata_helper.get_hardware_models()
  for model in models:
    match = re.match(".*-.*-G[1-5]", model)
    match1 = re.match("NX-[^-]*$", model)
    if match or match1:
      INFO("HW_Virt VM Live Migration is not supported on model: %s" % model)
      return False

  return is_supported

def get_aos_versions(cluster):
  """
  Get the unique aos versions on a cluster
  Args:
    cluster(object): NuTest Cluster object
  Returns:
    aos_versions(list): List of unique AOS versions
  """
  aos_versions = set()
  for svm in cluster.svms:
    res = svm.execute("cat /etc/nutanix/release_version")
    if "master" in res["stdout"]:
      aos_versions.add("master")
    else:
      aos_versions.add(res["stdout"].split("-")[-3])
  return list(aos_versions)

def get_ahv_versions(cluster):
  """
  Get the unique ahv versions on a cluster
  Args:
    cluster(object): NuTest Cluster object
  Returns:
    ahv_versions(list): List of unique AHV versions
  """
  ahv_versions = set()
  for host in cluster.hypervisors:
    ahv_ver = get_ahv_ver_new_or_old_format(cluster=cluster, host=host)
    ahv_versions.add(ahv_ver)
  return list(ahv_versions)

def is_ahv_new(ahv_version):
  """
  Check if AHV Version is in new format - <version>-<buil_num>
  Args:
    ahv_version(string): AHV Version
  Returns:
    True if ahv version is in new format
  """
  return "-" in ahv_version

def old_ahv_version_comparator(ahv_version, target_ahv_version):
  """
  Check if AHV Version is greater than or equal to the target AHV Version
  Args:
    ahv_version(str): Version to check
    target_ahv_version(str): AHV Version against which the comparison is done
  Returns:
    (bool): True if greater than or equal to, False otherwise
  """
  ahv_version_date = ahv_version.split(".")[0]
  ahv_version_date = datetime.strptime(ahv_version_date, "%Y%m%d")
  ahv_version_build = int(ahv_version.split(".")[1])

  target_ahv_version_date = target_ahv_version.split(".")[0]
  target_ahv_version_date = datetime.strptime(target_ahv_version_date, "%Y%m%d")
  target_ahv_version_build = int(target_ahv_version.split(".")[1])

  ahv_greater_than_equal_to = False
  if ahv_version_date > target_ahv_version_date:
    ahv_greater_than_equal_to = True
  elif ahv_version_date == target_ahv_version_date:
    if ahv_version_build >= target_ahv_version_build:
      ahv_greater_than_equal_to = True

  return ahv_greater_than_equal_to

def new_ahv_version_comparator(ahv_version, target_ahv_version):
  """
  Check if AHV Version is greater than or equal to the target AHV Version
  Args:
    ahv_version(str): Version to check
    target_ahv_version(str): AHV Version against which the comparison is done
  Returns:
    (bool): True if greater than or equal to, False otherwise
  """
  src_ahv_ver_list = ahv_version.split("-")[0].split(".")
  src_ahv_ver_build = int(ahv_version.split("-")[1])

  tgt_ahv_ver_list = target_ahv_version.split("-")[0].split(".")
  tgt_ahv_ver_build = int(target_ahv_version.split("-")[1])

  if ahv_version.split("-")[0] == target_ahv_version.split("-")[0]:
    return src_ahv_ver_build >= tgt_ahv_ver_build

  min_len = min(len(src_ahv_ver_list), len(tgt_ahv_ver_list))
  for index in range(0, min_len):
    if int(src_ahv_ver_list[index]) > int(tgt_ahv_ver_list[index]):
      return True
    elif int(src_ahv_ver_list[index]) < int(tgt_ahv_ver_list[index]):
      return False

  # Comparison reaches here if both the lists had same numbers till now.
  # At this point, return the list with greater length.
  return len(src_ahv_ver_list) >= len(tgt_ahv_ver_list)

def is_ahv_greater_than_equal_to(ahv_version, target_ahv_version):
  """
  Check if AHV Version is greater than or equal to the target AHV Version
  Args:
    ahv_version(str): Version to check
    target_ahv_version(str): AHV Version against which the comparison is done
  Returns:
    (bool): True if greater than or equal to, False otherwise
  """
  # Both old versions
  if not is_ahv_new(ahv_version) and not is_ahv_new(target_ahv_version):
    return old_ahv_version_comparator(ahv_version, target_ahv_version)
  # ahv_version - old, target_ahv_version - new
  elif not is_ahv_new(ahv_version) and is_ahv_new(target_ahv_version):
    return False
  # ahv_version - new, target_ahv_version - old
  elif is_ahv_new(ahv_version) and not is_ahv_new(target_ahv_version):
    return True
  # both new
  else:
    return new_ahv_version_comparator(ahv_version, target_ahv_version)

def is_aos_greater_than_equal_to(aos_version, target_aos_version):
  """
  Check if AOS version is greater than or equal to the target AOS version
  Args:
    aos_version(str): AOS Version to check
    target_aos_version(str): AOS Version against which the comparison is done
  Returns:
    (bool): True if greater than or equal to, False otherwise
  """
  aos_ver_li = aos_version.split(".")
  target_aos_ver_li = target_aos_version.split(".")
  if aos_ver_li[0] == "master":
    return True
  elif target_aos_ver_li[0] == "master":
    return False
  else:
    min_len = min(len(aos_ver_li), len(target_aos_ver_li))
    for index in range(0, min_len):
      if int(aos_ver_li[index]) > int(target_aos_ver_li[index]):
        return True
      elif int(aos_ver_li[index]) < int(target_aos_ver_li[index]):
        return False
    # Comparison reaches here when both the lists are equal. At this point
    # whichever list's len is greater that value is greater
    return len(aos_ver_li) >= len(target_aos_ver_li)
