"""Copyright (c) 2023 Nutanix Inc. All rights reserved.

Author: vedant.dalal@nutanix.com
"""

BUCKETS = {
  "gos": {
    "post_upgrade": {
      "gos_qual": {
        "p2": [
          "GOS_BVT_Pipeline"
        ]
      }
    }
  },
  "graphics": {},
  "host_checks": {
    "post_upgrade": {
      "itlb-multihit-mitigation": {
        "p2": [
          "itmitigation"
        ]
      }
    },
    "pre_upgrade": {
      "itlb-multihit-mitigation": {
        "p0": [
          "itmitigation_pre_upgrade"
        ]
      }
    }
  },
  "networking": {},
  "security": {},
  "storage": {
    "post_upgrade": {
      "frodo": {
        "p2": [
          "Frodo_BVT_Tests_Pipeline"
        ]
      }
    }
  },
  "upgrade": {},
  "vm_sanity": {
    "pre_upgrade": {
      "vm_sanity_qual": {
        "p0": [
          "Consolidated_pre_upgrade_restv2"
        ]
      }
    },
    "post_upgrade": {
      "vm_sanity_qual": {
        "p0": [
          "Consolidated_post_upgrade_restv2"
        ]
      }
    }
  }
}
