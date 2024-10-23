"""
Copyright (c) 2024 Nutanix Inc. All rights reserved.

Author: vedant.dalal@nutanix.com

This module contains all GPU Host Driver Fetching Automation.
"""

import copy
from framework.lib.nulog import INFO
from libs.ahv.workflows.one_click.objects_branch \
  import ObjectsUtil

class GPUHostDriverUtil():
  """
  A class containing all the GPU Host Driver Utility.
  """

  def __init__(self):
    """
    Constructor Method.
    """
    self.ENDOR_DYN_WEBSERVER = "endor.dyn.nutanix.com"#pylint: disable=invalid-name

  def fetch_host_driver_url(self, ahv_version, jobs):
    """
    A method to fetch the host driver url

    Args:
      ahv_version(str): AHV Version.
      jobs(str): Jobs (Dictionary containing all kwargs inputted by user).

    Returns:
      host_driver_url_list(list): Host Driver URL
    """
    INFO(jobs)
    host_driver_url_list = []
    # Get build web-server.
    web_server = self.ENDOR_DYN_WEBSERVER

    # Get details of all the folders
    ahv_rpms_url = ("http://{webserver}/builds/ahv-builds/{ahv}/RPMS/".format(
      webserver=web_server,
      ahv=ahv_version
    ))

    rpms_folders = ObjectsUtil().get_available_branches(url=ahv_rpms_url)
    host_drivers_dir = copy.deepcopy(rpms_folders)
    for each_dir in rpms_folders:
      if each_dir.startswith("nvidia-vgpu-"):
        INFO(each_dir)
      else:
        host_drivers_dir.remove(each_dir)

    # Get details of all the files for each host driver folders
    for each_driver in host_drivers_dir:
      driver_dir_url = ("http://{webserver}/builds/ahv-builds/{ahv}/RPMS/"
                        "{driver}/").format(
                          webserver=web_server,
                          ahv=ahv_version,
                          driver=each_driver
                        )
      driver_folders = ObjectsUtil().get_available_branches(
        url=driver_dir_url
      )

      # Get details of all the files in the each_driver folder
      for each_file in driver_folders:
        if (each_file.startswith("lcm_nvidia_{ahv}".format(ahv=ahv_version))
            and each_file.endswith(".tar.gz")):
          INFO(each_file)
          host_driver_url_list.append({
            each_driver: ("http://{webserver}/builds/ahv-builds/{ahv}/RPMS/"
                          "{driver}/{file}").format(
                            webserver=web_server,
                            ahv=ahv_version,
                            driver=each_driver,
                            file=each_file
                          )
          })

    return host_driver_url_list
