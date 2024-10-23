"""
Copyright (c) 2023 Nutanix Inc. All rights reserved.

Author: pritam.chatterjee@nutanix.com
"""
# pylint: disable=bad-continuation, invalid-name
ORDERED_PROCESSOR_MODELS = [
  "naples",
  "rome",
  "sandybridge",
  "ivybridge",
  "haswell",
  "broadwell",
  "skylake-client",
  "skylake-server",
  "cascadelake-server",
  "icelake-client",
  "icelake-server"
]

INTEL_CPU_MODELS = [
   "sandybridge",
   "ivybridge",
   "haswell",
   "broadwell",
   "skylake-client",
   "skylake-server",
   "cascadelake-server",
   "icelake-client",
   "icelake-server"
]

AMD_PROCESSOR_MODELS = [
   "naples",
   "rome",
]

DEFAULT_v3_CPU_MODEL_INTEL = "Broadwell"
DEFAULT_v3_CPU_MODEL_AMD = "NAPLES"

APC_GFLAG_FILE = "/home/nutanix/config/acropolis.gflags"
