"""
Copyright (c) 2021 Nutanix Inc. All rights reserved.

Author: pritam.chatterjee@nutanix.com
"""
import os

if os.getenv("NUTEST_PATH"):
  BASE_DIR = os.getenv("NUTEST_PATH")
  GUEST_SCHEMA_LOC = "workflows/acropolis/mjolnir/ahv/workflows" \
                     "/gos_qual/configs/guests.json"
  TEST_SCHEMA_LOC = "workflows/acropolis/mjolnir/ahv/workflows/gos_qual/" \
                    "configs/qualification_tests.json"
else:
  BASE_DIR = os.getenv("PYTHONPATH")
  GUEST_SCHEMA_LOC = "ahv/workflows/gos_qual/configs/guests.json"
  TEST_SCHEMA_LOC = "ahv/workflows/gos_qual/configs/qualification_tests.json"
GUEST_SCHEMA = os.path.join(BASE_DIR, GUEST_SCHEMA_LOC)
TEST_SCHEMA = os.path.join(BASE_DIR, TEST_SCHEMA_LOC)
DEFAULT_GOS_CONN = "ssh"
RHCERT_USERNAME = "pritam.chatterjee"
RHCERT_PASSWORD = "Nutanix.123"
OEMDRV_BASED_VENDORS = ["redhat", "almalinux", "rockylinux", "centos",
                        "oracle", "centos_stream"]
SUPPORTED_VENDORS = {
  "redhat": {
    "OSRelease": "Red Hat Enterprise Linux",
    "tier": 1,
  },
  "microsoft": {
    "OSRelease": "Windows",
    "tier": 1,
    "enterprise":
      {
        "windows8":
          {
            "max_vcpu": 2,
            "min_vcpu": 1
          },
        "windows8_1":
          {
            "max_vcpu": 2,
            "min_vcpu": 1
          }
      }
  },
  "ubuntu": {
    "OSRelease": "Ubuntu",
    "tier": 2
  },
  "almalinux": {
    "OSRelease": "AlmaLinux",
    "tier": 3
  },
  "solaris": {
    "OSRelease": "Solaris",
    "tier": 3
  },
  "debian": {
    "OSRelease": "Debian",
    "tier": 3
  },
  "suse": {
    "OSRelease": "SUSE Linux Enterprise Server",
    "tier": 2
  },
  "oracle": {
    "OSRelease": "Oracle Linux",
    "tier": 2
  },
  "centos": {
    "OSRelease": "CentOS Linux",
    "tier": 2
  },
  "centos_stream": {
    "OSRelease": "CentOS Linux",
    "tier": 2
  },
  "rockylinux": {
    "OSRelease": "RockyLinux",
    "tier":3
  },
  "hypervisors": {
    "OSRelease": "AHV Nested virtualization",
    "tier": 3
  },
}
FEATURES = {
  "VTPM" : {
    "Not_Supported_Guests": ["windows8", "windows8_1",
                             "windowsserver2012", "windowsserver2012r2"]
  }
}

# Elastic stack related URLS
ELK_USERNAME = "elastic"
ELK_PASSWORD = "FU92nLcLwDfoOG93fdLe"
ELK_BASE_URL = "https://10.40.121.35:9200"
ELK_DEFAULT_DB = "gos_qualification"
ELK_CREATE_ENTRY = "_doc?pretty"

#WINDOWS DRIVER PATH
INF_PATH = "C:\\Windows\\INF\\"
MACHINE = "machine"

#VIRTIO
STATE = "STATE"
VERSION = "VERSION"
IS_RUNNING = "IS_RUNNING"
IS_SIGNED = "IS_SIGNED"
NAME = "NAME"
LINKDATE = "LINKDATE"
PATH = "PATH"
FILE = "FILE"
GWMI_EXCEPTION = "gwmi : Call was canceled by the message filter."
AMD64 = "amd64"
X64 = "x64"
VIRTIO_120 = "1.2.0"
DRIVER_PATH = {
  "windowsserver2008r2": "Windows Server 2008 R2",
  "windowsserver2012": "Windows Server 2012",
  "windowsserver2012r2": "Windows Server 2012 R2",
  "windowsserver2016": "Windows Server 2016",
  "windowsserver2019": "Windows Server 2019",
  "windowsserver2022": "Windows Server 2022",
  "windowsserver2022_preview": "Windows Server 2022",
  "windows11": "Windows 11",
  "windows11_22H2": "Windows 11",
  "windows10": "Windows 10",
  "windows10_22H2": "Windows 10",
  "windows8_1": "Windows 8.1",
  "windows8": "Windows 8",
  "windows7": "Windows 7 (Legacy)",
}

VIRTIO_DRIVERS = {
  "balloon": {NAME: "Nutanix VirtIO Balloon Driver", FILE: "balloon.inf"},
  "netkvm": {NAME: "Nutanix VirtIO Ethernet Adapter", FILE: "netkvm.inf"},
  "vioscsi": {NAME: "Nutanix VirtIO SCSI pass-through controller",
              FILE: "vioscsi.inf"},
  # "viostor":{NAME: ""},
  # "virtioserial":{NAME: "Nutanix VirtIO Serial Driver", FILE: "vioser.inf"},
  # "virtrng":{NAME: "Nutanix VirtIO RNG Device", FILE: "viorng.inf"},
  "qemufwcfg": {NAME: "QEMU FWCfg Device", FILE: "qemufwcfg.inf"}
}

VIRTIO_DRIVERS_121 = {
  "balloon": {NAME: "Nutanix VirtIO Balloon Driver", FILE: "balloon.inf"},
  "netkvm": {NAME: "Nutanix VirtIO Ethernet Adapter", FILE: "netkvm.inf"},
  "vioscsi": {NAME: "Nutanix VirtIO SCSI pass-through controller",
              FILE: "vioscsi.inf"},
  # "viostor":{NAME: "Nutanix VirtIO SCSI controller", FILE: "viostor.inf"},
  # "fwcfg":{NAME: "QEMU FwCfg Device", FILE: "fwcfg.inf"},
  "qemufwcfg": {NAME: "QEMU FWCfg Device (null driver)", FILE: "qemufwcfg.inf"}
}

#PXE
INSTALL_WIM = r"E:\sources\install.wim"
BOOT_WIM = r"E:\sources\boot.wim"
LINUX_BOOT_EXCLUDE = ["credentialguard", "vtpm", "vtpm_secureboot",
                      "vtpm_credentialguard"]

NUTEST_CONV_MAP = dict()
VM_CACHE = {}
REMOVE_ACTIONS = ["remove"]
