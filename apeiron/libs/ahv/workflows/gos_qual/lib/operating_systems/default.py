"""
Copyright (c) 2021 Nutanix Inc. All rights reserved.

Author: pritam.chatterjee@nutanix.com
"""
# pylint: disable=import-error, no-self-use, fixme, unused-import
# pylint: disable=arguments-differ, no-else-raise
# pylint: disable=inconsistent-return-statements
import time
import re
from socket import error as SocketError
try:
  from framework.lib.nulog import INFO, ERROR, STEP, \
    WARN, DEBUG  # pylint: disable=unused-import

  EXECUTOR = "nutest"
except Exception:  # pylint: disable=broad-except
  from libs.ahv.framework.proxy_logging \
    import INFO, ERROR, STEP, WARN  # pylint: disable=unused-import

  EXECUTOR = "mjolnir"
from libs.ahv.workflows.gos_qual.lib.base.abstracts \
  import AbstractOperatingSystem
from libs.ahv.workflows.gos_qual.lib.base.utilities \
  import retry
from libs.workflows.screenshot.vm_screenshot \
  import Screenshot


class Default(AbstractOperatingSystem):
  """
  Base class for providing guest OS interface
  based in SSH and RPC
  """
  SUPPORTED_FEATURES = {
    "hotplug_vnic": True,
    "hotremove_vnic": True,
    "hotplug_scsi_vdisk": True,
    "hotplug_sata_vdisk": True,
    "hotplug_pci_vdisk": False,
    "coldplug_scsi_vdisk": True,
    "coldplug_sata_vdisk": True,
    "coldplug_pci_vdisk": False,
    "hotremove_vdisk": True,
    "hotplug_num_vcpu": True,
    "hotremove_num_vcpu": False,
    "hotplug_num_core_per_vcpu": False,
    "hotremove_num_core_per_vcpu": False,
    "hotplug_vmem": True,
    "hotremove_vmem": False
  }

  def __init__(self, ip=None,
               username=None,
               password=None,
               conn_provider=None):
    """
    Guest OS specific class
    Args:
      ip(str): IP address of guest OS
      username(str): username for guest OS
      password(str): password for guest OS
      conn_provider(object): SSH provider of RPC provider
    """
    self.username = username
    self.password = password
    self.ip = ip
    self.conn = conn_provider
    # self.set_connection_type(conn_provider)

  def apply_os_workaround(self):
    """
    Apply workaround for incorrect driver binding
    Args:
    Returns:
    """
    INFO("Not needed as for this OS type")

  def vm_poweroff(self, vm):
    """
    Perform poweroff operations via product rest api
    Args:
       vm(object): nutest rest api vm object
    Returns:
    """
    return vm.power_off()

  def verify_os_boot(self, vm=None):
    """
    Verify if the rpc agent is setup properly
    in the guest OS
    Args:
      vm(object): optional
    Returns:
      output(dict): stdout
    """
    retries = 120
    interval = 15
    INFO("Verifying if the VM booted successfully and is accessible")
    while True:
      try:
        res = self.conn.get_guest_os_info()
        return res
      except Exception as ex:  # pylint: disable=broad-except
        if retries <= 0:
          if vm:
            DEBUG("VM SCREENSHOT IN PROGRESS")
            Screenshot().take_screenshot(vm)
          raise ex
        retries = retries - 1
        WARN("Wait for VM to boot up, retries remaining: %s" % retries)
        time.sleep(interval)

  def verify_os_boot_post_reboot(self, vm, **kwargs):
    """
    Verify if the rpc agent is setup properly
    in the guest OS after vm reboot/poweroff-poweron
    Args:
      vm(object): vm object
      kwargs(dict): VM power on params
    Returns:
      output(dict): stdout
    """
    total_timeout = 900
    reboot_timeout = 300
    start = time.time()
    INFO("Verifying if the VM booted successfully and is accessible "
         "after vm was rebooted")
    while True:
      try:
        res = self.conn.get_guest_os_info()
        return res
      except Exception as ex:  # pylint: disable=broad-except
        end = time.time()
        if end - start >= total_timeout:
          DEBUG("VM SCREENSHOT IN PROGRESS")
          Screenshot().take_screenshot(vm)
          raise ex
        elif end - start >= reboot_timeout:
          DEBUG("VM SCREENSHOT IN PROGRESS")
          Screenshot().take_screenshot(vm)
          WARN("Rebooting the VM as a workaround")
          vm.power_cycle()
          vm.power_on(wait_for_ip=True, **kwargs)
          reboot_timeout += 300
        INFO("Retrying to connect after 2 secs")
        time.sleep(2)

  def verify_os_boot_with_io(self, **kwargs):
    """
    Verify if OS has boot successfully by writing and reading
    a file inside the guest OS
    Args:
      kwargs(dict): optional args for execute method
    Returns:
      output(tuple): stdin, stdout, stderr
    """
    cmd = "echo 'success' > /tmp/install"
    self.conn.execute(cmd, **kwargs)
    cmd = "cat /tmp/install"
    return self.conn.execute(cmd, **kwargs)

  def verify_uefi_boot(self, **kwargs):
    """
    Verify if OS has boot into uefi mode
    Args:
      kwargs(dict): optional args for execute method
    Returns:
      output(tuple): stdin, stdout, stderr
    """
    cmd = "[ -d /sys/firmware/efi ] && echo uefi || echo legacy"
    return self.conn.execute(cmd, **kwargs).strip()

  def verify_secure_boot(self, **kwargs):
    """
    Verify if OS has boot into secure boot mode
    Args:
      kwargs(dict): optional args for execute method
    Returns:
      output(tuple): stdin, stdout, stderr
    """
    cmd = "mokutil --sb-state"
    try:
      out = self.conn.execute(cmd, **kwargs)
      if "SecureBoot enabled" in out.strip():
        return "secureboot"
    except AssertionError:
      return "Not supported"

  def verify_vtpm_boot(self):
    """
    Verify if OS has booted with vtpm enabled
    Args:
    Returns:
      output(tuple): stdin, stdout, stderr
    """
    # FIXME: Need to implement for windows and linux
    return "vtpm"

  def verify_cg_boot(self):
    """
    Verify if OS has booted with credential guard enabled
    Args:
    Returns:
      output(tuple): stdin, stdout, stderr
    """
    # FIXME: Need to implement for windows and linux
    return "credentialguard"

  def reboot(self):
    """
    Reboot guest OS
    Args:
    Returns:
    """
    cmd = "reboot"
    return self.conn.run_shell_command_handsoff(cmd)

  def shutdown(self):
    """
    Shutdown guest OS
    Args:
    Returns:
    """
    cmd = "shutdown"
    return self.conn.run_shell_command_handsoff(cmd)

  def get_guest_cpu(self):
    """
    Get guest OS cpu info. num_vcps * cores_per_cpu
    Args:
    Returns:
    """
    res = self.conn.get_guest_os_info()
    return res["num_cpu"]

  def get_guest_vcpu(self):
    """
    Get guest OS vcpu info.
    Args:
    Returns:
    """
    cmd = "cat /proc/cpuinfo | grep 'physical id' | uniq -c | wc -l"
    vcpus = self.conn.execute(cmd)
    return int(vcpus)

  def get_guest_memory(self):
    """
    Get guest OS memory info.
    Args:
    Returns:
    """
    res = self.conn.get_guest_os_info()
    mem = res["memory"]
    mem = int(mem.strip("MB"))
    return str(mem)

  def get_nics(self):
    """
    Get network interfaces
    Args:
    Returns:
      nics(list)
    """
    cmd = "ip addr | grep BROADCAST | awk '/^./ {print $2}' | " \
          "tr --delete :"
    res = self.conn.execute(cmd)
    nics = res.strip().split("\n")
    return nics

  def parse_interface_ipv4(self, inf):
    """
    Parse the interface IP from ip addr command o/p
    Args:
      inf(str): interface name e.g. eth1
    Returns:
      inf_ip(str): interface ip or None
    """
    # NOTE: Only Oel is using this method. But it can be used for all linux
    #       to avoid dependency on grep -A4 commands which is not consistent
    def get_inf_details():
      """
      Local method to get the interface details
      Args:
      Returns:
        inf_details(list):
      """
      # NOTE: Can move this outside the method as well when stable enough
      cmd = "ip addr"
      out = self.conn.execute(cmd)
      out = out.split('\n')  # some filtering
      out = [line.strip() for line in out if line]
      inf_details = []
      for line in out:
        # 1st interface details incoming
        if re.match(r'^\d+:', line):
          inf_details.append([line])
        else:
          inf_details[-1].append(line)
      return inf_details

    inf_details = get_inf_details()
    for inf_d in inf_details:
      if inf in inf_d[0]:
        for j in inf_d[1:]:
          if "inet " in j:
            return j.split()[1].split("/")[0].strip()

  def get_nics_with_ips(self):
    """
    Get network interfaces with their ips
    Args:
    Returns:
      nic_ips(dict)
    """
    nics = self.get_nics()
    # removes bridge interfaces
    nics = [i for i in nics if "virbr" not in i]
    nic_ips = {}
    retries = 10
    wait = 3
    for nic in nics:
      nic_ips[nic] = None
      while retries:
        cmd = "ip addr | grep -A4  %s | grep inet | grep -v inet6 | " \
              "awk '{print $2}' | cut -d'/' -f1" % nic
        ip = self.conn.execute(cmd).strip()
        if ip and ip not in ["No stdout"]:
          nic_ips[nic] = ip
          break
        WARN("Did not get IP yet, trying DHCLIENT as workaround")
        self.conn.execute("dhclient -I %s" % nic)
        retries = retries - 1
        time.sleep(wait)
    return nic_ips

  def get_threads_per_core(self):
    """
    Return number of threads per core
    Args:
    Returns:
      threads(int)
    """
    processor_count = int(self.get_guest_cpu())
    cores_per_cpu = int(
      self.conn.execute("cat /proc/cpuinfo | grep 'processor' | "
                        "uniq |awk '/^./ {print $4}' | sort | "
                        "uniq | wc -l"))
    vcpu_count = self.get_guest_vcpu()
    return processor_count / (vcpu_count * cores_per_cpu)

  def bring_cpu_online(self):
    """
    Try to bring cpu/cores online after hot add
    Args:
    Returns:
    """
    # FIXME. Add proper polling for 3 mins to detect cpu changes
    timeout = 60
    INFO("Graceful period of %s secs to pickup new added cpu" % timeout)
    time.sleep(timeout)

  def bring_mem_online(self):
    """
    Try to bring memory online after hot add
    Args:
    Returns:
    """
    # FIXME. Add proper polling for 3 mins to detect cpu changes
    timeout = 120
    INFO("Graceful period of %s secs to pickup new added memory" % timeout)
    time.sleep(timeout)

  def configure_rp_filter(self):
    """
    Configure rp filter from within guest OS to accept new IPs
    Args:
    Returns:
      output(bool):
    """
    cmd = \
      "sed -i '/net.ipv4.conf.default.rp_filter/c\\net.ipv4.conf.default" \
      ".rp_filter=2' /etc/sysctl.conf"
    (rv, stdout, stderr) = self.conn.run_shell_command_sync(
      cmd)
    assert rv == 0, "Failed to execute %s. (rv=%s,stdout=%s,stderr=%s)" % \
                    (cmd, rv, stdout, stderr)

    cmd = "echo net.ipv4.conf.all.rp_filter = 2 >> " \
          "/etc/sysctl.conf"
    (rv, stdout, stderr) = self.conn.run_shell_command_sync(
      cmd)
    assert rv == 0, "Failed to execute %s. (rv=%s,stdout=%s,stderr=%s)" % \
                    (cmd, rv, stdout, stderr)

    cmd = "/sbin/sysctl -e -p"
    (rv, stdout, stderr) = self.conn.run_shell_command_sync(
      cmd)
    assert rv == 0, "Failed to execute %s. (rv=%s,stdout=%s,stderr=%s)" % \
                    (cmd, rv, stdout, stderr)

    self.conn.run_shell_command_sync("sync")
    assert rv == 0, "Failed to execute 'sync' command. \
      (rv=%s,stdout=%s,stderr=%s)" % (rv, stdout, stderr)

  def bring_vnics_online(self):
    """
    Try to bring vnics online after hot add
    Args:
    Returns:
    """
    INFO("Not required for this guest OS")

  def get_os_architecture(self):
    """
    Get Guest OS architecture
    Args:
    Returns:
    """
    cmd = "uname -i"
    out = self.conn.execute(cmd)
    return out.strip().split("_")[0]

  def get_os_bits(self):
    """
    Get Guest OS architecture
    Args:
    Returns:
    """
    cmd = "uname -i"
    out = self.conn.execute(cmd)
    return out.strip().split("_")[1]

  def get_kernel_info(self):
    """
    Get Guest OS kernel
    Args:
    Returns:
    """
    cmd = "uname -r"
    out = self.conn.execute(cmd)
    return out.strip()

  def configure_tftp_env(self, **kwargs):
    """
    Manage and bringing up tftp boot env for linux
    by adding the required installation source files
    on tftp server
    Args:
    Returns:
    """
    INFO("Downloading OS installation files to tftp server")
    inst_img = kwargs.get("cdrom")
    extra_params = kwargs.get("extra_params")
    os = extra_params.get("os")
    cmd = "curl '%s' -o /root/source.iso" % inst_img
    task_id = self.conn.run_shell_command_handsoff(cmd)
    self.conn.wait_handsoff_task_complete(task_id, 600)

    self.conn.execute(cmd)
    INFO("Download complete, mounting the image to copying install files")
    cmd = "mount -t iso9660 /root/source.iso /mnt/%s -o loop,ro" % os
    self.conn.execute(cmd)
    cmd = "ls -ltr /mnt"
    self.conn.execute(cmd)

    INFO("Mounted successfully, copying files")
    cmd = "mkdir -p /var/ftp/%s" % os
    self.conn.execute(cmd)
    cmd = "cp -r /mnt/%s /var/ftp/" % os
    task_id = self.conn.run_shell_command_handsoff(cmd)
    self.conn.wait_handsoff_task_complete(task_id, 600)
    cmd = "ls -ltr /var/ftp/%s" % os
    self.conn.execute(cmd)

    # based on legacy or uefi, change the settings below
    if self._is_uefi(**kwargs):
      INFO("Performing UEFI specific configuration for pxe boot")
      # cmd = "rm -rf /var/lib/tftp/uefi"
      # self.conn.execute(cmd)
      # cmd = 'mkdir -p /var/lib/tftp/uefi'
      # self.conn.execute(cmd)
      # cmd = "mkdir -p /mnt/%s" % os
      self._copy_initrd_vmlinuz(mode="efi", **kwargs)
      self._copy_shim_grub(**kwargs)
    else:
      INFO("Performing LEGACY specific configuration for pxe boot")
      self._copy_initrd_vmlinuz(**kwargs)
    INFO("Tftp environment configuration completed")

  def configure_dnsmasq_env(self, **kwargs):
    """
    Configure dnsmasq for pointing to initrd & kernel image and installation
    source files on tftp server
    Args:
    Returns:
    """
    if self._is_uefi(**kwargs):
      self._configure_dnsmasq_env_for_uefi(**kwargs)
    else:
      self._configure_dnsmasq_env_for_legacy(**kwargs)

    cmd = 'ps -ef | grep dnsmasq | grep -v grep | awk "{print $2}"'
    (_, stdout, _) = self.conn.run_shell_command_sync(
      cmd)
    ps = [i.split()[1] for i in stdout.split("\n") if i]
    cmd = "kill -9 %s" % " ".join(ps)
    self.conn.execute(cmd)

    cmd = "systemctl restart dnsmasq.service"
    self.conn.execute(cmd)
    cmd = "systemctl status dnsmasq.service"
    return self.conn.execute(cmd)

  def verify_syslog_conflicts(self):
    """
    Verify for any conflict messages in syslogs
    Args:
    Returns:
    Raises:
    """
    cmd = "dmesg | grep conflict"
    (_, stdout, _) = self.conn.run_shell_command_sync(cmd)
    assert stdout == 'No stdout', "Conflicts detected in dmesg: %s" % stdout

  def set_disk_online(self):
    """Check status of each disk on Windows.
          In case they are offline, convert them and
          make them online"""
    # fixme : need to implement
    INFO("Not required for linux")

  @retry(times=3, interval=5, exceptions=(ValueError, TypeError, SocketError))
  def get_boot_disk(self):
    """
    Get the disk_name which is the boot disk on Linux OS,
    retries for default 3 times
    Args:

    Returns:
      str: disk name on UVM which is the boot disk

    """
    cmd = "df -h| grep /boot"
    (_, stdout, _) = self.conn.run_shell_command_sync(cmd)
    stdout = stdout.split()
    return re.search(r'(^[a-z\/]+)', stdout[0]).groups(1)[0]

  @retry(times=3, interval=5, exceptions=(ValueError, TypeError, SocketError))
  def get_disk_drives(self):
    """
    Get all disk drives, on Linux OS, retries for default 3 times
    Returns:
    """
    cmd = "lsblk | grep disk"
    (_, stdout, _) = self.conn.run_shell_command_sync(cmd)
    stdout = stdout.split()
    return ["/dev/" + d for d in stdout
            if re.search(r'^[a-z]+', d) and d not in ["disk"]]

  @retry(times=3, interval=5, exceptions=(ValueError, TypeError, SocketError))
  def run_io_integrity(self, **params):
    """
    Run io integrity within Guest

    Returns:
      None
    """
    vdisk_file = params.get("vdisk_file")
    file_size_gb = params.get("file_size_gb")
    time_limit_secs = params.get("time_limit_secs")
    INFO("Running IO integrity")
    task = self.conn.run_io_integrity_test_async(vdisk_file=vdisk_file,
                                                 file_size_gb=file_size_gb,
                                                 time_limit_secs=
                                                 time_limit_secs)
    result = self.conn.wait_task_complete(task, time_limit_secs * 3)
    INFO("Task complete: result=%d, vm.ip=%s, task=%s, args=%s" % \
           (result, task.vm_ip, task.task_str, task.task_args))
    assert result == 0, "IO integrity test result error."

  def get_errored_devices(self):
    """
    Method to get the devices in not OK state
    Args:
    Kargs:
    Returns:
      stdout(bool):
    """
    WARN("Not impletemented for Linux OS yet, stay tuned.")

  def install_fio(self):
    """
    Install fio on VM
    """
    INFO("Install fio on VM...")
    cmd = "sudo apt-get install fio -y"
    (rv, stdout, stderr) = self.conn.run_shell_command_sync(cmd)
    assert rv == 0, "Failed to execute %s. (rv=%s,stdout=%s,stderr=%s)" % \
                    (cmd, rv, stdout, stderr)

  def run_fio(self, **kwargs):
    """
    Run fio workload on VM
    Args:
      kwargs(dict): Params to run fio workload
    Raises:
      Exception: If fio does not start running on the VM
    """
    self.install_fio()
    iodepth = kwargs.get("iodepth", "10")
    rw = kwargs.get("rw", "randrw")
    size = kwargs.get("size", "4096m")
    verify = kwargs.get("verify", "md5")
    runtime = kwargs.get("runtime", "86400s")
    bs = kwargs.get("bs", "4k")
    ioengine = "libaio"
    name = "fio_test"
    cmd = "fio --name=%s --iodepth=%s --rw=%s --size=%s --verify=%s "\
          "--bs=%s --runtime=%s --direct=1 --ioengine=%s --time_based" \
          % (name, iodepth, rw, size, verify, bs, runtime, ioengine)

    self.conn.run_shell_command_async(cmd)
    self.verify_process(process_name="fio")

  def install_dirty_harry(self):
    """
    Install dirty harry on VM
    Returns:
    Raises:
      (Exception): If dirty harry installation fails
    """
    INFO("Installation of Dirty Harry...")
    cmd = "wget http://endor.dyn.nutanix.com/acro_images/"\
          "automation/ahv_guest_os/Misc/harry"
    (rv, stdout, stderr) = self.conn.run_shell_command_sync(cmd)
    assert rv == 0, "Failed to execute %s. (rv=%s,stdout=%s,stderr=%s)" % \
                    (cmd, rv, stdout, stderr)

    cmd = "chmod +x harry"
    (rv, stdout, stderr) = self.conn.run_shell_command_sync(cmd)
    assert rv == 0, "Failed to execute %s. (rv=%s,stdout=%s,stderr=%s)" % \
                    (cmd, rv, stdout, stderr)

  def run_dirty_harry(self, **kwargs):
    """
    Run dirty harry workload on VM

    Args:
      (kwargs): Params to run dirty harry workload on VM

    Raises:
      Exception: If Dirty Harry does not start running on the VM
    """
    self.install_dirty_harry()
    INFO("Starting Dirty Harry Workload")

    num_vcpu = kwargs.get("num_vcpu", 1)
    mem_to_dirty_mb = int(kwargs.get("mem_to_dirty", 1024) / 1024)
    dirty_rate_mb = kwargs.get("dirty_rate_mb", 1000)
    cmd = "./harry -n %s -m %s -l %s" \
          % (num_vcpu, mem_to_dirty_mb, dirty_rate_mb)

    self.conn.run_shell_command_async(cmd)
    time.sleep(2)
    self.verify_process(process_name="harry")

  def verify_process(self, **kwargs):
    """
    Verify if a process is running inside the guest
    Args:
      kwargs(dict): Keyword args
    Returns:
      None
    """
    process_name = kwargs.get("process_name")
    cmd = "ps -fC %s" % process_name
    status, stdout, stderr = self.conn.run_shell_command_sync(cmd)

    INFO("Task status=%s, stdout=%s, stderr=%s" % (status, stdout, stderr))
    if status != 0:
      self.conn.run_shell_command_sync("uptime -s")
    assert status == 0, "Process %s not running inside guest" % process_name

  def disable_auto_upgrades(self):
    """
    Method to disable automatic updating of guest OS
    Args:
    Kwargs:
    Returns:
    """
    INFO("Linux is cool. Nothing required")

  def get_hsm_card_names(self):
    """
    Method to get hsm card names in guest
    Args:
    Returns:
      hsm_cards(list):
    """
    cmd = 'lspci | grep "Hardware Security Module"'
    result = self.conn.execute(cmd)
    return [res for res in result.split('\n') if res]

  def _is_uefi(self, **kwargs):
    """
    Internel method for checking if the pxe client will boot in
    legacy or uefi mode
    Args:
    Returns:
      result(bool)
    """
    return kwargs.get("uefi_boot")

  def _copy_shim_grub(self, **kwargs):
    """
    Internal method to copy shim and grub efi files for UEFI pxe boot
    Args:
    Returns:
    """
    extra_params = kwargs.get("extra_params")
    os = extra_params.get("os")
    bits = extra_params.get("bits")
    cmd = "rm -rf /root/shim"
    self.conn.execute(cmd)
    cmd = "mkdir /root/shim"
    self.conn.execute(cmd)
    cmd = 'find /mnt/%s/ -name shim-* | grep %s' % (os,
                                                    bits)
    (_, stdout, _) = self.conn.run_shell_command_sync(cmd)
    shim_rpm = stdout.strip()
    shim_rpm = [rpm for rpm in shim_rpm.split() if
                rpm.split('-')[1] == 'x' + str(extra_params.get('bits'))]
    assert len(shim_rpm) == 1, "Detected ambiguous rpms, unable to decide " \
                               "which one to use %s" % shim_rpm
    shim_rpm = shim_rpm[0]
    cmd = 'cp %s /root/shim/' % shim_rpm
    self.conn.execute(cmd)
    cmd = "cd /root/shim/; rpm2cpio /root/shim/shim-* | cpio -dimv"
    self.conn.execute(cmd)
    cmd = "cp /root/shim/boot/efi/EFI/redhat/shimx64.efi " \
          "/var/lib/tftpboot/uefi/"
    self.conn.execute(cmd)

    cmd = "rm -rf /root/grub2"
    self.conn.execute(cmd)
    cmd = "mkdir /root/grub2"
    self.conn.execute(cmd)
    cmd = 'find /mnt/%s/ -name grub2-efi-* | grep %s | grep -v %s ' \
          '| grep -v %s' % (os,
                            bits,
                            "cdboot",
                            "modules")
    (_, stdout, _) = self.conn.run_shell_command_sync(cmd)
    grub_rpm = stdout.strip()
    grub_rpm = [rpm for rpm in grub_rpm.split() if
                rpm.split('-')[2] == 'x' + str(extra_params.get('bits'))]
    assert len(grub_rpm) == 1, "Detected ambiguous rpms, unable to decide " \
                               "which one to use %s" % grub_rpm
    grub_rpm = grub_rpm[0]
    cmd = 'cp %s /root/grub2/' % grub_rpm
    self.conn.execute(cmd)
    cmd = "cd /root/grub2/; rpm2cpio /root/grub2/grub2-efi-* | cpio -dimv"
    self.conn.execute(cmd)
    cmd = "cp /root/grub2/boot/efi/EFI/redhat/grubx64.efi " \
          "/var/lib/tftpboot/uefi/"
    self.conn.execute(cmd)
    cmd = "chmod -R +777 /var/lib/tftpboot/uefi/"
    self.conn.execute(cmd)
    cmd = "ls -ltr /var/lib/tftpboot/uefi/"
    self.conn.execute(cmd)

  def _copy_initrd_vmlinuz(self, mode="bios", **kwargs):
    """
    Internel method for checking taking care of uefi and legacy based files
    required
    Args:
      mode(str): efi or bios
    Returns:
    """
    extra_params = kwargs.get("extra_params")
    os = extra_params.get("os")
    INFO("Files copied to shared location, now copying initrd and "
         "kernel images")
    tftp_root = "pxelinux"
    if mode == "efi":
      tftp_root = "uefi"
    cmd = "mkdir -p /var/lib/tftpboot/%s/images/%s" % (tftp_root,
                                                       os)
    self.conn.execute(cmd)
    cmd = "cp /mnt/%s/images/pxeboot/{vmlinuz,initrd.img} " \
          "/var/lib/tftpboot/%s/images/%s" % (os, tftp_root,
                                              os)
    self.conn.execute(cmd)

  def _configure_dnsmasq_env_for_legacy(self, **kwargs):
    """
    Internal method Configure dnsmasq for pointing to initrd & kernel
    image and installation
    source files on tftp server
    Args:
    Returns:
    """
    extra_params = kwargs.get("extra_params")
    modules = extra_params.get("modules")
    os = extra_params.get("os")
    pxe_conf = "/var/lib/tftpboot/pxelinux/pxelinux.cfg/default"
    initrd_txt = r'  append initrd=images/%s/initrd.img ' \
                 'ip=dhcp inst.repo=ftp://%s/%s' % (
                   os, modules["pxe_vm"].ip, os)
    INFO("Updating initrd location and tftp ip in pxe config")
    cmd = 'sed -i "s@^  append.*@%s@g" %s' % (initrd_txt, pxe_conf)
    self.conn.execute(cmd)

    INFO("Updating kernel location in pxe config")
    kernel_txt = r'  kernel images/%s/vmlinuz' % os
    cmd = 'sed -i "s@^  kernel.*@%s@g" %s' % (kernel_txt, pxe_conf)
    self.conn.execute(cmd)
    cmd = 'cat %s' % pxe_conf
    self.conn.execute(cmd)

    INFO("Updating the tftp root info in dnsmasq config")
    dnsmasq_conf = "/etc/dnsmasq.conf"
    tftp_root = r'tftp-root=/var/lib/tftpboot/pxelinux'
    cmd = 'sed -i "s@^tftp-root=.*@%s@g" %s' % (tftp_root, dnsmasq_conf)
    self.conn.execute(cmd)
    dhcp_boot = r'dhcp-boot=pxelinux.0'
    cmd = 'sed -i "s@^dhcp-boot=.*@%s@g" %s' % (dhcp_boot, dnsmasq_conf)
    self.conn.execute(cmd)
    pxe_service = r'pxe-service=x86PC,\"Network Boot\",pxelinux'
    cmd = 'sed -i "s@^pxe-service=.*@%s@g" %s' % (pxe_service, dnsmasq_conf)
    self.conn.execute(cmd)
    cmd = "cat %s" % dnsmasq_conf
    self.conn.execute(cmd)

  def _configure_dnsmasq_env_for_uefi(self, **kwargs):
    """
    Internal method Configure dnsmasq for pointing to initrd & kernel
    image and installation
    source files on tftp server
    Args:
    Returns:
    """
    extra_params = kwargs.get("extra_params")
    modules = extra_params.get("modules")
    os = extra_params.get("os")
    INFO("Updating initrdefi location and tftp ip in pxe config")
    pxe_conf = "/var/lib/tftpboot/uefi/grub.cfg"
    initrdefi_txt = r'  initrdefi images/%s/initrd.img' % os
    cmd = 'sed -i "s@^  initrdefi.*@%s@g" %s' % (initrdefi_txt, pxe_conf)
    self.conn.execute(cmd)

    INFO("Updating linuxefi location in pxe config")
    linuxefi_txt = r'  linuxefi images/%s/vmlinuz ip=dhcp ' \
                   r'inst.repo=ftp://%s/%s' % (
                     os, modules["pxe_vm"].ip, os)
    cmd = 'sed -i "s@^  linuxefi.*@%s@g" %s' % (linuxefi_txt, pxe_conf)
    self.conn.execute(cmd)

    INFO("Updating the tftp root info in dnsmasq config")
    dnsmasq_conf = "/etc/dnsmasq.conf"
    tftp_root = r'tftp-root=/var/lib/tftpboot/uefi'
    cmd = 'sed -i "s@^tftp-root=.*@%s@g" %s' % (tftp_root, dnsmasq_conf)
    self.conn.execute(cmd)
    dhcp_boot = r'dhcp-boot=shimx64.efi'
    cmd = 'sed -i "s@^dhcp-boot=.*@%s@g" %s' % (dhcp_boot, dnsmasq_conf)
    self.conn.execute(cmd)
    pxe_service = r'pxe-service=x86PC,\"Network Boot\",shimx64.efi'
    cmd = 'sed -i "s@^pxe-service=.*@%s@g" %s' % (pxe_service, dnsmasq_conf)
    self.conn.execute(cmd)
    cmd = "cat %s" % dnsmasq_conf
    self.conn.execute(cmd)
