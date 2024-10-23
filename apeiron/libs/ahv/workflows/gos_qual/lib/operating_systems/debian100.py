"""
Copyright (c) 2021 Nutanix Inc. All rights reserved.

Author: pritam.chatterjee@nutanix.com
"""
# pylint: disable=import-error
import time
try:
  from framework.lib.nulog import INFO, ERROR, STEP, WARN  # pylint: disable=unused-import
  EXECUTOR = "nutest"
except Exception: # pylint: disable=broad-except
  from libs.ahv.framework.proxy_logging import \
    INFO, ERROR, STEP, WARN # pylint: disable=unused-import
  EXECUTOR = "mjolnir"
from libs.ahv.workflows.gos_qual.lib.\
  operating_systems.default import Default


class Debian100(Default):
  """Debain10.0 class"""
  def bring_cpu_online(self):
    """
    Try to bring cpu/cores online after hot add
    Args:
    Returns:
    Raises:
    """
    INFO("Graceful period of 30 secs to pickup newly added CPUs")
    time.sleep(30)
    bring_cpus_online = """
      for CPU_DIR in /sys/devices/system/cpu/cpu[0-9]*
      do
        CPU=${CPU_DIR##*/}
        echo "Found cpu: '${CPU_DIR}' ..."
        CPU_STATE_FILE="${CPU_DIR}/online"
        if [ -f "${CPU_STATE_FILE}" ]; then
          if grep -qx 1 "${CPU_STATE_FILE}"; then
            echo -e "\t${CPU} already online"
          else
            echo -e "\t${CPU} is new cpu, onlining cpu ..."
            echo 1 > "${CPU_STATE_FILE}"
          fi
        else
          echo -e "\t${CPU} already configured prior to hot-add"
        fi
      done
      """
    task_id = self.conn.run_user_code_handsoff("bash",
                                               "cpu_up.sh",
                                               bring_cpus_online)
    time.sleep(2)
    rv, _, err = self.conn.query_handsoff_task_result(task_id)

    assert rv == 0, "Fail to bring up CPUs, (rv=%s,stderr:%s)" % (rv, err)

  def bring_mem_online(self):
    """
    Try to bring memory online after hot add
    Args:
    Returns:
    Raises:
    """
    timeout = 120
    INFO("Graceful period of %s secs to pickup new added memory" % timeout)
