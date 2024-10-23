"""Copyright (c) 2023 Nutanix Inc. All rights reserved.

Author: vedant.dalal@nutanix.com
"""
BRANCH_MAPPING = {
  "9.0": {
    "branch_name": "astronomix-release-9.0.0",
    "staging_branch": "astronomix-staging",
    "staging_branch_map": "9.0_staging"
  },
  "9.0_staging": {
    "branch_name": "astronomix-staging-9.0",
    "staging_branch": "astronomix-staging",
    "staging_branch_map": "9_staging"
  },
  "9_staging": {
    "branch_name": "astronomix-staging"
  },
  "8.1": {
    "branch_name": "cacofonix-release-8.1",
    "staging_branch": "cacofonix-staging",
    "staging_branch_map": "8_staging"
  },
  "8_staging": {
    "branch_name": "cacofonix-staging",
  },
  "8.0": {
    "branch_name": "cacofonix-release-8.0",
    "staging_branch": "cacofonix-staging",
    "staging_branch_map": "8_staging"
  }
}
