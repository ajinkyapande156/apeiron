"""
Copyright (c) 2024 Nutanix Inc. All rights reserved.
Author: rishabh.kumar@nutanix.com

Library to store and retrieve VM config to and from the CVMs
This would be used in pre upgrade and post upgrade tests
"""
#pylint: disable=broad-except
import json
from framework.lib.nulog import INFO, ERROR


class VMConfigCollector:
  """
  VM Config Collector class
  """
  def __init__(self, cluster, **kwargs):
    """
    Init method
    Args:
      cluster(object): NuTest Cluster object
      kwargs(dict): Keyword args
    """
    self.cluster = cluster
    self.file_path = kwargs.get("file_path",
                                "/home/nutanix/data/mjolnir/vm_info.json")

  def store_vm_info_cvm(self, vm_info):
    """
    Store VM info on CVMs
    Args:
      vm_info(dict): VM info
    Raises:
      Exception(exception): If vm_info could not be written to any of the CVM
    """
    errors = []
    is_data_written = False
    for svm in self.cluster.svms:
      dir_created = False
      try:
        svm.execute("mkdir data/mjolnir")
        dir_created = True
      except Exception as ex:
        ERROR(ex)
        if "file exists" in str(ex).lower():
          dir_created = True
        else:
          errors.append(ex)

      if dir_created:
        INFO("Store VM config: %s at {%s} on CVM: %s" \
              % (vm_info, self.file_path, svm.ip))
        json_data = json.dumps(vm_info, indent=2)
        cmd = "echo \'%s\' > %s" % (json_data, self.file_path)
        try:
          svm.execute(cmd)
          is_data_written = True
        except Exception as ex:
          ERROR(ex)
          errors.append(ex)

    if not is_data_written:
      raise Exception("Could not write VM config data to any of the CVM\n" \
                      "ERRORS: %s" % errors)

  def get_vm_info_cvm(self):
    """
    Retrieve the VM info present on CVM for post upgrade test
    Returns:
      vm_data(dict): If VM data is retrieved from any of the CVM
    Raises:
      Exception(exception): If VM data cannot be retrieved from any of the CVM
    """
    errors = []
    for svm in self.cluster.svms:
      try:
        INFO("Retrieve VM config data from: {%s} on CVM: %s" \
              % (self.file_path, svm.ip))
        raw_data = svm.execute("cat %s" % self.file_path)
        vm_data = raw_data["stdout"]
        vm_data = json.loads(vm_data)
        INFO("VM Data retrieved: %s" % vm_data)
        return vm_data
      except Exception as ex:
        ERROR(ex)
        errors.append(ex)
    raise Exception("Could not get VM data from any of the CVM\n" \
                    "ERRORS: %s" % errors)
