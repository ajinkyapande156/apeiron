
"""Copyright (c) 2021 Nutanix Inc. All rights reserved.

Author: vedant.dalal@nutanix.com

This module contains all the metadata and constants.
"""
import datetime

TESTS = []

################################
# DO NOT TOUCH BELOW SECTION
################################
TEST_SET_CREATE = "POST"
TEST_SET_GET = "GET"
TEST_SET_DELETE = "DELETE"
TEST_SET_URL = "https://jita.eng.nutanix.com/api/v2/test_sets"
TEST_SET_CLONE = "https://jita.eng.nutanix.com/api/v1/agave_test_sets"
TEST_SET_CLONE_KEYS_TO_DELETE = {"_id", "id", "created_by", "updated_by",
                                 "created_at", "updated_at", "date_added",
                                 "date_updated", "duration"}
TEST_SET_PAYLOAD = {
  "tests": [
    {"name": test} for test in TESTS
  ],
  "name": "testset_name",
  "args_map": {},
  "agave_options": {}
}

JOB_PROFILE_CREATE = "POST"
JOB_PROFILE_GET = "GET"
TEST_SET_DELETE = "DELETE"
JOB_PROFILE_URL = "https://jita.eng.nutanix.com/api/v2/job_profiles"

JOB_PROFILE_PAYLOAD = {
  "v":3,
  "name":("ahv_reg_job_profile_"+
          str(datetime.datetime.now().strftime("%d-%m-%Y_%H:%M:%S"))),
  "description":"",
  "system_under_test":{
    "product":"aos",
    "branch":"master",
    "component":"main"
  },
  "emails":[
    "vedant.dalal@nutanix.com"
  ],
  "service":"AOS",
  "package_type":"tar",
  "test_service":"Nutest",
  "private":   False,
  "infra":[
    {
      "kind":"ON_PREM",
      "type":"cluster",
      "entries":[]
    }
  ],
  "services":[
    "NOS"
  ],
  "git":{
    "branch":"master",
    "repo":"main"
  },
  "build_selection":{
    "commit_must_be_newer":  False,
    "build_type":"release",
    "by_latest_build":  True
  },
  "skip_commit_id_validation": None,
  "image_branch": None,
  "image_build_type": None,
  "image_build_selection":"By Commit",
  "requested_hardware":{
    "hypervisor": None,
    "hypervisor_version": None,
    "imaging_options":{
      "redundancy_factor":"default"
    }
  },
  "resource_manager_json":{
    "NOS_CLUSTER":{}
  },
  "scheduling_options":{
    "skip_resource_spec_match":  False,
    "check_image_compatibility":  False,
    "force_imaging":  False,
    "upgrade":  False,
    "retry_imaging":0,
    "optimize_scheduling":  True,
    "task_priority":10
  },
  "allow_resource_sharing":  False,
  "plugin_tar_location": None,
  "plugin_commit": None,
  "test_sets":[
    {
      "$oid":"<testset_id>"
    }
  ],
  "test_framework":"nutest",
  "nutest_branch": "master",
  "nutest_commit": None,
  "patch_url": None,
  "nutest_egg_url": None,
  "test_tar_url": None,
  "sdk_installation_options":{},
  "skip_bad_tests":  False,
  "tester_tags":[],
  "run_tests_with_priorities":[],
  "run_tests_with_additional_tags":[],
  "auto_schedule_cron":  False,
  "tester_container_config": None,
  "demo_mode":  False,
  "plugins":{
    "pre_run":[],
    "post_run":[]
  }
}
JITA_DB_SEARCH_PARAMS = {
  "only": ("name,type"),
  "raw_query": {
    "name":{
      "$regex":"auto_cluster_prod_svc_merit_4f9785db810e",
      "$options":"i"
    }
  }
}
REPORT_GENERATION_KEYS_TO_DELETE = {"uuid", "matrix_start_time", "aos_version",
                                    "matrix_start_time_epoch",
                                    "aos_rel_branch", "ahv_version",
                                    "pe_version", "pc_version", "msp_version",
                                    "csi_version", "pipeline",
                                    "product_version", "commit_version",
                                    "objects_version", "ndk_version"}

JOB_CLONE_KEYS_TO_DELETE = {"last_triggered", "updated_at",
                            "task_timeout", "cluster_selection",
                            "scheduled_jobs", "created_at", "_id"}
PAYLOAD_KEYS_TO_DELETE = {"job_profile", "aos_version",
                          "ahv_version", "el_version",
                          "cluster_name", "pool_name",
                          "no_of_retries", "retry_interval",
                          "test_priority", "foundation_versions",
                          "post_upgrade_tests", "pre_upgrade_tests",
                          "lcm_url", "cluster_ip", "view_url",
                          "workload_name", "status", "product_type",
                          "task_id", "cluster_type", "workload_execution",
                          "cluster_name", "oss_version", "aos_version",
                          "workload_details"}
TRIGGER_METHOD = "POST"
TRIGGER_URL = "https://jita.eng.nutanix.com/api/v2/job_profiles/<id>/trigger"
TASK_POLL_METHOD = ""
TASK_POLL_URL = "https://jita.eng.nutanix.com/api/v2/agave_tasks"
TASK_DEPLOYMENT_URL = "https://jita.eng.nutanix.com/api/v2/reports/deployments"
TEST_RESULT_URL = ("https://jita.eng.nutanix.com/api/v2/"
                   "reports/agave_test_results")
TEST_REPORT_URL = "https://jita.eng.nutanix.com/results?task_ids="
TASK_DEPLOYMENT_PAYLOAD = {
  "raw_query":{
    "task_id":{
      "$in":[
        {
          "$oid":"<agave_task_id>"
        }
      ]
    }
  },
  "only":("status,created_at,updated_at,logs,task_id,resource_specs,"
          "matching_resources,provision_request_id,allocated_resources,"
          "start_time,end_time,retain_resources")
}
TEST_RESULT_PAYLOAD = {
  "raw_query": {
    "agave_task_id": {
      "$in": [
        {
          "$oid": "<agave_task_id>"
        }
      ]
    }
  },
  "only": ("test,agave_task_id,start_time,end_time,run_duration,status,"
           "comments,stage,exception_summary,jira_tickets,deployment_id,"
           "cmd_executed,container_details,spec_hash,test_log_url,"
           "tester_log_url,scheduler_logs,plugin_log_url,created_by,AgaveTask,"
           "status_transitions,stages,allocated_resources,time_breakup,"
           "retain_resources"),
  "start": 0,
  "limit": 20,
  "sort": "agave_task_id,status"
}
PRODUCT_META_FILE = (
  "http://phx-ep-filer-build-prod-1.corp.nutanix.com/builds"
  "/product-meta-cci-builds/master/latest/software/ahv.json"
)
AOS_PROD_META_URL = (
  "http://phx-builds.corp.nutanix.com/product-meta"
  "-cci-builds/master/latest/software/aos.json"
)
BUCKETS_MNGR_PROD_META_URL = (
  "http://phx-builds.corp.nutanix.com/product-meta"
  "-cci-builds/master/latest/software/buckets_manager.json"
)
BUCKETS_SVC_PROD_META_URL = (
  "http://phx-builds.corp.nutanix.com/product-meta-cci-builds"
  "/master/latest/software/buckets_service.json"
)
IGNORE_AOS_UPGRADE = ["6.1.1.5", "5.17.1.3", "2020.09.16", "5.16"]
JITA_CLUSTER_DB_PAYLOAD = {
  "type":"$NOS_CLUSTER",
  "name":"name",
  "fetch_from_jarvis":True
}
PC_PRODUCT_META_URL = ("http://phx-builds.corp.nutanix.com/product-meta-cci-"
                       "builds/master/latest/software/pc.json")
AOS_PRODUCT_META_URL = ("http://phx-builds.corp.nutanix.com/product-meta-cci-"
                        "builds/master/latest/software/aos.json")
JITA_CLUSTER_URL = "https://jita.eng.nutanix.com/api/v2/clusters"
AHV_UPGRADE_HEADERS = ["Source AHV", "Destination AHV",
                       "Source AOS", "Platform", "Start Time", "End Time",
                       "Total Time", "Status", "Result",
                       "Reason", "Jita URL"]
AHV_AOS_UPGRADE_HEADERS = ["Source AHV", "Source AOS",
                           "Destination AHV", "Destination AOS",
                           "Platform", "Start Time", "End Time", "Total Time",
                           "Status", "Result", "Reason",
                           "Jita URL"]
DEPLOYMENT_PATH_HEADERS = ["Source AHV", "Source AOS",
                           "Foundation Build", "Platform", "Start Time",
                           "End Time", "Total Time", "Status", "Result",
                           "Reason", "Jita URL"]
NGD_DEPLOYMENT_PATH_HEADERS = ["Source AHV", "Source AOS",
                               "Driver", "Platform", "Start Time",
                               "End Time", "Total Time", "Status", "Result",
                               "Reason", "Jita URL"]
AHV_FEAT_HEADERS = ["Source AHV", "Source AOS", "Feat", "Feat Index",
                    "Platform", "Start Time", "End Time", "Total Time",
                    "Status", "Result", "Reason", "Jita URL"]
CSI_DEPLOYMENT_HEADERS = ["Source CSI", "Source AOS", "Source PC", "Feat",
                          "Feat Index", "Platform", "Kubernetes Platform",
                          "Start Time", "End Time", "Total Time", "Status",
                          "Result", "Reason", "Jita URL"]
NDK_DEPLOYMENT_HEADERS = ["Source NDK", "Source CSI", "Source AOS",
                          "Source PC", "Feat",
                          "Feat Index", "Platform", "Kubernetes Platform",
                          "Start Time", "End Time", "Total Time", "Status",
                          "Result", "Reason", "Jita URL"]
NDK_UPGRADE_HEADERS = ["Source NDK", "Source CSI", "Source AOS",
                       "Source PC", "Destination NDK", "Platform",
                       "Kubernetes Platform", "Start Time", "End Time",
                       "Total Time", "Status", "Result", "Reason", "Jita URL"]
NDK_CSI_UPGRADE_HEADERS = ["Source NDK", "Source CSI", "Source AOS",
                           "Source PC", "Destination NDK", "Destination CSI",
                           "Platform", "Kubernetes Platform", "Start Time",
                           "End Time", "Total Time", "Status", "Result",
                           "Reason", "Jita URL"]
NDK_PC_UPGRADE_HEADERS = ["Source NDK", "Source CSI", "Source AOS",
                          "Source PC", "Destination NDK", "Destination PC",
                          "Platform", "Kubernetes Platform", "Start Time",
                          "End Time", "Total Time", "Status", "Result",
                          "Reason", "Jita URL"]
NDK_AOS_UPGRADE_HEADERS = ["Source NDK", "Source CSI", "Source AOS",
                           "Source PC", "Destination NDK", "Destination AOS",
                           "Platform", "Kubernetes Platform", "Start Time",
                           "End Time", "Total Time", "Status", "Result",
                           "Reason", "Jita URL"]
NDK_AOS_PC_CSI_UPGRADE_HEADERS = ["Source NDK", "Source CSI", "Source AOS",
                                  "Source PC", "Destination NDK", "Platform",
                                  "Kubernetes Platform", "Start Time",
                                  "End Time", "Total Time", "Status", "Result",
                                  "Reason", "Jita URL"]
CSI_DEPLOYMENT_PATH_HEADERS = ["Source CSI", "Source AOS", "Source PC",
                               "Platform", "Kubernetes Platform",
                               "Start Time", "End Time", "Total Time",
                               "Status", "Result", "Reason", "Jita URL"]
CSI_UPGRADE_HEADERS = ["Source CSI", "Source AOS", "Source PC",
                       "Destination CSI", "Destination AOS",
                       "Destination PC", "Platform", "Kubernetes Platform",
                       "Start Time", "End Time", "Total Time", "Status",
                       "Result", "Reason", "Jita URL"]
CSI_AOS_UPGRADE_HEADERS = ["Source CSI", "Source AOS", "Source PC",
                           "Destination CSI", "Destination AOS",
                           "Platform", "Kubernetes Platform",
                           "Start Time", "End Time", "Total Time", "Status",
                           "Result", "Reason", "Jita URL"]
CSI_PC_UPGRADE_HEADERS = ["Source CSI", "Source AOS", "Source PC",
                          "Destination CSI",
                          "Destination PC", "Platform", "Kubernetes Platform",
                          "Start Time", "End Time", "Total Time", "Status",
                          "Result", "Reason", "Jita URL"]
OBJECTS_DEPLOYMENT_HEADERS = ["Source Objects", "Source AOS", "Source PC",
                              "Feat", "Feat Index", "Platform",
                              "Start Time", "End Time", "Total Time", "Status",
                              "Result", "Reason", "Jita URL"]
OBJECTS_DEPLOYMENT_PATH_HEADERS = ["Source Objects", "Source AOS", "Source PC",
                                   "Deployment Case", "Platform",
                                   "Start Time", "End Time", "Total Time",
                                   "Status", "Result", "Reason", "Jita URL"]
OBJECTS_UPGRADE_HEADERS = ["Source Objects", "Source AOS", "Source PC",
                           "Destination Objects", "Destination AOS",
                           "Destination PC", "Platform",
                           "Start Time", "End Time", "Total Time", "Status",
                           "Result", "Reason", "Jita URL",
                           "Deployment_Jita_URL"]
GOS_QUAL_HEADERS = ["ahv", "aos", "vendor", "os", "type",
                    "arch", "bits", "boot", "Platform", "Start Time",
                    "End Time", "Total Time", "Status",
                    "Result", "Reason", "Jita URL", "Dashboard URL"]
IGNORE_IMAGING_ACTIONS = ["guest_os_qual", "pxe", "virtio", "gos_upgrade",
                          "csi", "objects", "ndk"]
STATIC_IGNORE_IMAGING_ACTIONS = ["guest_os_qual", "pxe", "virtio",
                                 "gos_upgrade", "csi", "objects", "ndk"]
IGNORE_PRE_POST_UPGRADE = ["guest_os_qual", "deployment_path", "pxe",
                           "virtio", "gos_upgrade"]
GOS_ACTIONS = ["guest_os_qual", "pxe", "virtio", "gos_upgrade"]
EMAIL_SENDER_LIST = ["vedant.dalal@nutanix.com"]
EMAIL_SUBJECTS = {
  "upgrade": {
    "cluster_imaging": ("Cluster Imaging  for v{src} --> v{dst} Path."
                        " [{action}]"),
    "pu_end": ("Post Upgrade Test Executed for v{src} --> v{dst} Path."
               " [{action}]"),
    "start": "Started Execution for v{src} --> v{dst} Path. [{action}]",
    "mid": "Time Extended for v{src} --> v{dst} Path. [{action}]",
    "end": "v{src} --> v{dst} path got {result}. [{action}]",
    "pre_upgrade": "Pre Upgrade Tests executed for v{src} --> v{dst} path."
                   " [{action}]",
    "post_upgrade": "Post Upgrade Tests executed for v{src} --> v{dst} path."
                    " [{action}]"
  },
  "deployment": {
    "cluster_imaging": "Cluster Imaging  for v{ahv} & {aos} Path. [{action}]",
    "start": ("Started Execution for v{ahv} & {aos} on Foundation-{found}."
              " [{action}]"),
    "pu_end": ("Post Upgrade Test Executed for v{src} --> v{dst} Path."
               " [{action}]"),
    "mid": "Time Extended for v{ahv} & {aos} Path. [{action}]",
    "end": "v{ahv} & {aos} path got {result}. [{action}]"
  },
  "csi_deployment": {
    "cluster_imaging": ("[{action}] Cluster Imaging  for csi.{ahv} & {aos} & "
                        "{pc} Path."),
    "start": "[{action}] Started Execution for csi.{ahv} & {aos} & {pc}",
    "pu_end": ("Post Upgrade Test Executed for v{src} --> v{dst} Path."
               " [{action}]"),
    "mid": "Time Extended for v{ahv} & {aos} & {pc} Path. [{action}]",
    "end": "[{action}] csi.{ahv} & {aos} & {pc} path got {result}"
  },
  "ndk_deployment": {
    "cluster_imaging": ("[{action}] Cluster Imaging  for ndk.{ndk} & csi.{csi}"
                        " & {aos} & {pc} Path."),
    "start": "[{action}] Started Execution for ndk.{ndk} & csi.{csi} & {aos}"
             " & {pc}",
    "pu_end": ("Post Upgrade Test Executed for v{src} --> v{dst} Path."
               " [{action}]"),
    "mid": "Time Extended for v{csi} & {aos} & {pc} Path. [{action}]",
    "end": "[{action}] ndk.{ndk} & csi.{csi} & {aos} & {pc} path got {result}"
  },
  "objects_deployment": {
    "cluster_imaging": ("[{action}] Cluster Imaging  for buckets-{objects}"
                        " & {aos}  & {pc} Path."),
    "start": ("[{action}] Started Execution for buckets-{objects} & {aos}"
              " & {pc}"),
    "pu_end": ("Post Upgrade Test Executed for v{src} --> v{dst} Path."
               " [{action}]"),
    "mid": "Time Extended for v{objects} & {aos} & {pc} Path. [{action}]",
    "end": "[{action}] buckets-{objects} & {aos} & {pc} path got {result}",
    "pre_upgrade": ("Objects pre upgrade tests executed for "
                    "Source Obj: {objects}, Source AOS: {aos}, "
                    "Source PC: {pc}"),
    "post_upgrade": ("Objects post upgrade tests executed for "
                     "Source Obj: {objects}, Source AOS: {aos}, "
                     "Source PC: {pc}")
  },
  "guest_os_qual": {
    "cluster_imaging": "Cluster Imaging started",
    "start": ("Started execution for one batch"),
    "mid": "Time Extended for Guest OS qualification",
    "end": "Execution completed for one batch"
  }
}
VERSION_LIST = ["pc_version", "msp_version", "pe_version", "ahv_version",
                "aos_version", "csi_version", "product_version",
                "commit_version", "objects_version", "ndk_version"]
PRODUCT_DB_MAPPING = {
  "ahv": {
    "index": "one_click_index_db",
    "main": "one_click_db"
  },
  "csi": {
    "index": "csi_apeiron_index_db",
    "main": "csi_apeiron_db"
  },
  "msp": {
    "index": "msp_apeiron_index_db",
    "main": "msp_apeiron_db"
  }
}
PRESERVE_ON_FAILURE_REASONS = ["LCM update failed", "UVM is powered off"]
WORKLOAD_DEFAULT_JOBS = {
  "job_profile": "Apeiron_objects_workload_base_JP",
  "no_of_retries": "240000000000",
  "retry_interval": "900",
}
DEFAULT_JOBS = {
  "email_ids": ["vedant.dalal@nutanix.com"],
  "no_of_retries": "24000000",
  "retry_interval": "600",
  "top_rows_for_buckets": 2,
  "preserve_cluster_on_failure": True,
  "upgrade": {
    "ahv_upgrade": {
      "jobs": [
        {
          "job_profile": "ahv_upgrade_base_job_profile_vd_cluster"
        }
      ]
    },
    "msp_pc_upgrade": {
      "jobs": [
        {
          "pc_enabled": True,
          "dep_job_profile": "msp_pc_deployment_base_jp_copy",
          "job_profile": "msp_pc_upgrade_base_jp"
        }
      ]
    },
    "ahv_aos_upgrade": {
      "jobs": [
        {
          "job_profile": "ahv_aos_upgrade_base_job_profile_multinode"\
                          "_cluster"
        }
      ]
    },
    "multi_level_upgrade": {
      "jobs":[
        {
          "job_profile": "apeiron_multi_level_upgrade_base_JP"
        }
      ]
    }
  },
  "ngd": {
    "ahv_upgrade": {
      "jobs": [
        {
          "job_profile": "1_click_ngd_ahv_upgrade_base_jp",
        }
      ]
    }
  },
  "deployment": {
    "deployment_path": {
      "jobs": [
        {
          "job_profile": "1_click_dep_path_base_jp",
          "foundation_builds": [
            "http://endor.dyn.nutanix.com/releases/Foundation-5.4/"\
            "foundation-5.4.tar.gz",
            "http://endor.dyn.nutanix.com/releases/Foundation-5.3/"\
            "foundation-5.3.tar.gz",
            "http://endor.dyn.nutanix.com/releases/Foundation-5.2/"\
            "foundation-5.2.tar.gz"
          ],
        }
      ]
    },
    "csi_deployment_path": {
      "jobs": [
        {
          "job_profile": "csi_functional_all_apeiron",
          "pc_enabled": True,
        }
      ]
    }
  },
  "guest_os_qual": {
    "jobs": [
      {
        "job_profile": "Apeiron_Guest_OS_Qualification_Tier1_master"
      }
    ]
  }
}
HYP_URL = "http://endor.dyn.nutanix.com/builds/ahv-builds/{hyp}/iso/"\
          "AHV-DVD-x86_64-{hyp_full}.iso"
LTS = "6.5"
STS = "5.20"
PLATFORM_LIST = ["NX", "AMD", "HPE", "DELL"]
PRE_POST_UPGRADE_HEADERS = {
  "pre_upgrade": ["Pre Upgrade Result", "Pre Upgrade Jita URL"],
  "post_upgrade": ["Post Upgrade Result", "Post Upgrade Jita URL"]
}
DEFAULT_POST_UPGRADE = {
  "p0_tc": [],
  "p0_ts": [],
  "po_jp": [],

  "p1_tc": [],
  "p1_ts": [],
  "p1_jp": [],

  "p2_tc": [],
  "p2_ts": [],
  "p2_jp": [],

  "el7_path_for_exhaustive_test": 1,
  "el6_path_for_exhaustive_test": 1,

  "p0_execution_percent": 60,
  "p1_execution_percent": 35,
  "p2_execution_percent": 5
}

PU_JOB_PROFILE_PAYLOAD = {
  "v":3,
  "name":("ahv_reg_job_profile_"+
          str(datetime.datetime.now().strftime("%d-%m-%Y_%H:%M:%S"))),
  "description":"",
  "system_under_test":{
    "product":"aos",
    "branch":"master",
    "component":"main"
  },
  "emails":[
    "vedant.dalal@nutanix.com"
  ],
  "service":"AOS",
  "package_type":"tar",
  "test_service":"Nutest",
  "private":   False,
  "infra":[
    {
      "kind":"ON_PREM",
      "type":"cluster",
      "entries":[]
    }
  ],
  "services":[
    "NOS"
  ],
  "git":{
    "branch":"master",
    "repo":"main"
  },
  "build_selection":{
    "commit_must_be_newer":  False,
    "build_type":"release",
    "by_latest_build":  True
  },
  "skip_commit_id_validation": None,
  "image_branch": None,
  "image_build_type": None,
  "image_build_selection":"By Commit",
  "requested_hardware":{
    "hypervisor": None,
    "hypervisor_version": None,
    "imaging_options":{
      "redundancy_factor":"default"
    }
  },
  "resource_manager_json":{
    "NOS_CLUSTER":{}
  },
  "scheduling_options":{
    "skip_resource_spec_match":  False,
    "check_image_compatibility":  False,
    "force_imaging":  False,
    "upgrade":  False,
    "retry_imaging":0,
    "optimize_scheduling":  True,
    "task_priority":10
  },
  "allow_resource_sharing":  False,
  "plugin_tar_location": None,
  "plugin_commit": None,
  "test_sets":[
    {
      "$oid":"<testset_id>"
    }
  ],
  "test_framework":"nutest",
  "nutest_branch": "master",
  "nutest_commit": None,
  "patch_url": None,
  "nutest_egg_url": None,
  "test_tar_url": None,
  "sdk_installation_options":{},
  "skip_bad_tests":  False,
  "tester_tags":[],
  "run_tests_with_priorities":[],
  "run_tests_with_additional_tags":[],
  "auto_schedule_cron":  False,
  "tester_container_config": None,
  "demo_mode":  False,
  "plugins":{
    "pre_run":[],
    "post_run":[]
  }
}

JOB_JSON_KEYS_TO_DELETE = ["upgrade", "deployment", "frodo", "vgpu", "gos",
                           "ngd", "guest_os_qual"]
GOS_TESTARGS_TO_DELETE = ["Plaform", "Jita URL", "Result", "Reason", "Status",
                          "jobs", "cluster_name", "Total_Time",
                          "Dashboard URL", "Start Time", "End Time",
                          "Start_Time", "End_Time"]
AOS_MAPPING = {
  4: "danube-{x}-stable",
  5: "euphrates-{x}-stable",
  6: "fraser-{x}-stable",
  7: "ganges-{x}-stable"
}

FOUNDATION_MAPPING = {
  "el6": {
    "Foundation_URL": "http://endor.dyn.nutanix.com/releases/Foundation-5.1/"\
                      "foundation-5.1.tar.gz",
  }
}

###################################
#    JARVIS APIs and Params       #
###################################

JARVIS_NODE_POOL_URL = "https://jarvis.eng.nutanix.com/api/v1/pools"
JARVIS_V2_NODE_POOL_URL = "https://jarvis.eng.nutanix.com/api/v2/pools"
JARVIS_CLUSTER_URL = "https://jarvis.eng.nutanix.com/api/v1/clusters"
JARVIS_IMAGE_REQUEST_URL = "https://jarvis.eng.nutanix.com/api/v1/"\
                           "image_requests"
JARVIS_IMAGE_REQUEST_PAYLOAD = {
  "datacenter": {
    "hyperv": {},
    "vsphere": {},
    "kvm": {}
  },
  "cluster_name": "auto_cluster_prod_kern_qian_f393dededb72",
  "nos_version": "fraser-6.1.2-stable",
  "hyp_type": "kvm",
  "hyp_version": "20201105.30007",
  "redundancy_factor": "default",
  "build_type": "release",
  "foundation_overrides": []
}
JARVIS_SPECIAL_POOLS = ['global-pool']
src_ahv_map = {#pylint: disable=invalid-name
  "ahv_upgrade": "Source_AHV",
  "ahv_aos_upgrade": "Source_AHV",
  "deployment_path": "Source_AHV",
  "multi_level_ahv_upgrade": "Source_AHV",
  "level_2_ahv_upgrade": "Source_AHV",
  "level_3_ahv_upgrade": "Source_AHV",
  "ngd_ahv_upgrade": "Source_AHV",
  "ngd_ahv_aos_upgrade": "Source_AHV",
  "guest_os_qual": "ahv",
  "pxe": "ahv",
  "virtio": "ahv",
  "gos_upgrade": "ahv"
}

src_aos_map = {#pylint: disable=invalid-name
  "ahv_upgrade": "Source_AOS",
  "ahv_aos_upgrade": "Source_AOS",
  "deployment_path": "Source_AOS",
  "csi_functional_qual": "Source_AOS",
  "objects_upgrade": "Source_AOS",
  "csi_error_injection": "Source_AOS",
  "multi_level_ahv_upgrade": "Source_AOS",
  "level_2_ahv_upgrade": "Source_AOS",
  "level_3_ahv_upgrade": "Source_AOS",
  "ngd_ahv_upgrade": "Source_AOS",
  "ngd_ahv_aos_upgrade": "Source_AOS",
  "msp_pc_upgrade": "Source_AOS",
  "guest_os_qual": "aos",
  "pxe": "aos",
  "virtio": "aos",
  "gos_upgrade": "aos"
}
###################################
#    RDM APIs and Payload         #
###################################
RDM_SCHEDULED_DEPLOYMENT_URL = "https://rdm.eng.nutanix.com/api/v1/"\
                               "scheduled_deployments"
RDM_DEPLOYMENT_URL = "https://rdm.eng.nutanix.com/api/v1/deployments"
FETCH_PC_BUILD_URL = "https://rdm.eng.nutanix.com/artifacts?tags="\
                     "PC_SMOKE_PASSED&product=pc&branch=fraser-"\
                     "{pc_version}-stable-pc-0"
PC_URL = "http://endor.dyn.nutanix.com/builds/pc-builds/fraser-"\
         "{pc_version}-stable-pc-0/{githash}/{gbn}/x86_64/release/"
PC_BUILD_URL = {
  "pc.2023.1.0.1": "http://endor.dyn.nutanix.com/releases/pc.2023.1.0.1/"\
    "b6e8129a6120da6a25ad411d042a684c4da3c625/PC/PC-Deployment-Package/",
  "pc.2023.1.0.2": "http://endor.dyn.nutanix.com/releases/pc.2023.1.0.2/"\
    "559164b8e4614ef8b48af4f37223df652527cb64/PC/PC-Deployment-Package/",
  "pc.2022.6": "http://endor.dyn.nutanix.com/releases/pc.2022.6/"\
    "9111aeedf0090ae7572ef9611b1535c3c7b986bc/PC/PC-Deployment-Package/",
  "pc.2023.3": "http://endor.dyn.nutanix.com/releases/pc.2023.3/"\
    "b66385df1d08a332080945342346ab391dd4525f/1692749032/PC/PC-Deployment"\
    "-Package/",
  "pc.2023.3.0.1": "http://endor.dyn.nutanix.com/releases/pc.2023.3.0.1/"\
    "c9464cb085a670a29fa72696f9dbd887a56f6756/1700551385/PC/PC-Deployment"\
    "-Package/",
  "master": "http://endor.dyn.nutanix.com/builds/pc-builds/master/latest/"\
    "release/",
  "pc.2023.4": "http://endor.dyn.nutanix.com///builds/pc-builds/fraser-2023"\
    ".4-stable-pc-0/latest/x86_64/release/",
  "pc.2024.1": "http://endor.dyn.nutanix.com/builds/pc-builds/fraser-2024."\
    "1-stable-pc-0/latest/x86_64/release/",
  "pc.2023.5": "http://endor.dyn.nutanix.com///builds/pc-builds/fraser-2023"\
    ".5-stable-pc-0/latest/x86_64/release/",
  "pc.2021.5": "http://endor.dyn.nutanix.com/releases/pc.2021.5/"\
    "a48467616ee7c603e3cee3174779cf24bea227cb/PC/PC-Deployment-Package/",
  "pc.2022.4.0.2": "http://endor.dyn.nutanix.com/releases/pc.2022.4.0.2/"\
    "8456fd5bd36cde3ec6facfc57d064a1825d90cd4/PC/PC-Deployment-Package/",
  "pc.2022.9": "http://endor.dyn.nutanix.com/releases/pc.2022.9/"\
    "fc7c83daa381c7a81d3e183c95b255069966e5fc/PC/PC-Deployment-Package/",
  "pc.2022.6.0.3": "http://endor.dyn.nutanix.com/releases/pc.2022.6.0.3/"\
    "3bee36fe994b19d348eaeca95358089b000bfec1/PC/PC-Deployment-Package/",
  "pc.2020.9.0.1": "http://endor.dyn.nutanix.com/releases/pc.2020.9.0.1/"\
    "d649e9be3d39c6c564fd68f4ec674ef0ad78f55b/PC/PC-Deployment-Package/"
}
RDM_DEPLOYMENT_PAYLOAD = {
  "name": "vedant_dalal_1644494310931",
  "duration": 290,
  "max_wait_time_till_allocation": 48,
  "tags": [
    "svc_ahv_qa"
  ],
  "comment": "",
  "retry": 0,
  "client_timezone_offset": -330,
  "resource_specs": [
    {
      "type": "$NOS_CLUSTER",
      "name": "shy-dream-60499093",
      "is_new": True,
      "resources": {
        "infra": {
          "kind": "ON_PREM"
        },
        "type": "node_pool",
        "entries": []
      },
      "set_cluster_external_ip_address": False,
      "set_external_data_services_ip_address": False,
      "image_resource": True,
      "auto_generate_cluster_name": True,
      "is_nested_base_cluster": False,
      "hardware": {
        "min_host_gb_ram": 16,
        "all_flash_cluster": False,
        "svm_gb_ram": 32,
        "svm_num_vcpus": 10,
        "cluster_min_nodes": 3,
        "must_run_on_hardware_models": []
      },
      "software": {
        "nos": {
          "version": "master",
          "build_type": "release",
          "redundancy_factor": "default"
        },
        "hypervisor": {
          "version": "branch_symlink",
          "type": "ahv"
        }
      },
      "register_prism_to_vcenter": False,
      "network": {
        "dc_local": True,
        "subnet_local": True
      },
      "enable_network_segmentation": False,
      "use_fast_foundation": False,
      "enable_large_partitions": False,
      "rdma_passthrough": False,
      "enable_lacp": False,
      "dod_config": {
        "enable": False,
        "enable_sudo_restriction": False,
        "allow_nutanix_for_sudo_exec": False
      },
      "use_foundation_vm": False,
      "datacenter": {
        "use_host_names": True
      }
    }
  ]
}

RDM_PC_DEPLOYMENT_PAYLOAD = {
  "type": "$PRISM_CENTRAL",
  "name": "icy-base-59376217",
  "is_new": True,
  "software": {
    "prism_central": {
      "build_url": "http://endor.dyn.nutanix.com///builds/pc-builds/"\
      "fraser-2023.2-stable-pc-0/84f92f60386ed921beb8123e4cac8c3562d1ff2d/"\
      "1679935664/x86_64/release/"
    }
  },
  "scaleout": {
    "num_instances": 1,
    "enable_anc": False,
    "pcvm_size": "small",
    "enable_cmsp": False
  },
  "provider": {
    "host": "soft-shadow-89218131"
  },
  "dependencies": [
    "soft-shadow-89218131"
  ],
  "prism_elements": [
    {
      "host": "soft-shadow-89218131"
    }
  ]
}

RDM_SELENIUM_VM_PAYLOAD = {
  "type": "$SELENIUM_VM",
  "name": "summer-tree-30015988",
  "is_new": True,
  "hardware": {
    "vcpus": 2,
    "ram": "4G",
    "cores_per_vcpu": 2
  },
  "software": {
    "build_url": (
      "http://hoth.corp.nutanix.com/objects-qa/regression-files/"\
      "docker_selenium.qcow2"
    )
  },
  "network": {
    "use_tagged_vlan": False,
    "vlan_id": 0
  },
  "provider": {
    "host": "jolly-river-46025261"
  },
  "dependencies": [
    "jolly-river-46025261"
  ]
}

RDM_IMAGING_PAYLOAD = {
  "name":"svc_ahv_qa_1656302858381",
  "duration":15,
  "max_wait_time_till_allocation":15,
  "tags":["svc_ahv_qa"],
  "comment":"",
  "retry":0,
  "client_timezone_offset":-330,
  "resource_specs":[
    {
      "type":"$NOS_CLUSTER",
      "name":"auto_cluster_prod_svc_ahv_qa_4f2090dce2c8",
      "is_new":False,
      "resources":{
        "type":"static_resources",
        "infra":{
          "kind":"ON_PREM"
        },
        "entries":[
          {
            "type":"$NOS_CLUSTER",
            "name":"auto_cluster_prod_svc_ahv_qa_4f2090dce2c8"
          }
        ]
      },
      "set_cluster_external_ip_address":True,
      "set_external_data_services_ip_address":True,
      "image_resource":True,
      "skip_cluster_creation":False,
      "hardware":{"svm_gb_ram":32, "svm_num_vcpus":10},
      "software":{
        "nos":{
          "version":"euphrates-5.15-stable",
          "build_type":"release",
          "redundancy_factor":"default"
        },
        "hypervisor":{
          "version":"20220304.198",
          "type":"ahv"
        }
      },
      "register_prism_to_vcenter":False,
      "network":{"dc_local":True, "subnet_local":True},
      "enable_network_segmentation":False,
      "use_fast_foundation":False,
      "enable_large_partitions":False,
      "rdma_passthrough":False,
      "enable_lacp":False,
      "dod_config":{
        "enable":False,
        "enable_sudo_restriction":False,
        "allow_nutanix_for_sudo_exec":False
      },
      "use_foundation_vm":False,
      "datacenter":{
        "use_host_names":True
      }
    }
  ]
}

GLOBAL_POOL_DEPLOYMENT_RES = {
  "type": "node_pool",
  "infra": {
    "kind": "PRIVATE_CLOUD",
    "params": {
      "category": "general",
      "coupon":"nimble-tench"
    }
  }
}

RDM_FAILURE_MSG_1 = "Failed to allocate resources for scheduled deployment"
RDM_FAILURE_MSG_2 = "Not enough free nodes exist in the pool."
###################################
# Opensearch APIs and Credentials #
###################################
OPENSEARCH_BASE_URL = "https://1.1.1.1:9200"
OPENSEARCH_INGESTION_URL = "https://1.1.1.1:9200/{db_name}/_doc"
OPENSEARCH_INDEX_CREATION_URL = "https://1.1.1.1:9200/{db_name}"
OPENSEARCH_USERNAME = "dummy"
OPENSEARCH_PASSWORD = "dummy"
###################################
#    ELK APIs and Payload         #
###################################
ELK_BASE_URL = "https://10.40.121.35:9200"
INGESTION_URL = "https://10.40.121.35:9200/{db_name}/_doc"
INDEX_CREATION_URL = "https://10.40.121.35:9200/{db_name}"

PU_JP_PAYLOAD = {
  "private": False,
  "services": [
    "NOS"
  ],
  "plugins": {
    "post_run": [],
    "pre_run": []
  },
  "auto_schedule_cron": False,
  "build_selection": {
    "commit_must_be_newer": False,
    "by_latest_smoked": True
  },
  "git": {
    "repo": "main",
    "branch": "master"
  },
  "service": "AOS",
  "system_under_test": {
    "product": "aos",
    "component": "main",
    "branch": "master"
  },
  "created_by": "6127a51f8e79ce9a1b5326f8",
  "test_sets": [
    {
      "$oid": "627b939a2bc0c40a584098b3"
    }
  ],
  "run_tests_with_priorities": [],
  "requested_hardware": {
    "hypervisor_version": None,
    "hypervisor": None,
    "imaging_options": {
      "redundancy_factor": "default"
    }
  },
  "description": "",
  "allow_resource_sharing": False,
  "infra": [
    {
      "kind": "ON_PREM",
      "type": "cluster",
      "entries": [
      ]
    }
  ],
  "run_tests_with_additional_tags": [],
  "test_framework": "nutest",
  "tester_tags": [],
  "skip_bad_tests": False,
  "image_build_selection": "By Commit",
  "skip_invalid_config_tests": False,
  "emails": [],
  "name": "1_click_pipeline_base_JP",
  "scheduling_options": {
    "optimize_scheduling": True,
    "force_imaging": False,
    "task_priority": 10,
    "skip_resource_spec_match": True,
    "upgrade": False,
    "retry_imaging": 0,
    "check_image_compatibility": False
  },
  "package_type": "tar",
  "resource_manager_json": {
    "NOS_CLUSTER": {}
  },
  "created_by_user": {
    "$oid": "6127a51f8e79ce9a1b5326f8"
  },
  "demo_mode": False,
  "sdk_installation_options": {},
  "v": 3,
  "test_service": "Nutest"
}

###################################
#           GUEST OS QUAL         #
###################################

GUEST_OS_RESULT_QUERY = {
  "query": {
    "bool": {
      "must": []
    }
  }
}
GOS_RESULT_UPDATE_KEYS = [
  "run_id.keyword", "os.keyword", "boot.keyword", "type.keyword",
  "arch.keyword", "bits.keyword"
]
GOS_QUAL_JOBS_CHANGE = {
  "classifier":"one-click-gos-qual",
  "filters":  {
    "type": "enterprise,standard,server"
  }
}
VIRTIO_JOBS_CHANGE = {
  "guest_selection_mode":"virtio",
  "test_selection_mode":"virtio",
  "classifier":"one-click-virtio",
  "filters":  {
    "vendor": "microsoft"
  }
}
GOS_UPGRADE_JOBS_CHANGE = {
  "test_selection_mode":"gos_upgrade",
  "classifier":"one-click-gos-qual-upgrades",
  "filters":  {
    "type": "enterprise,standard,server",
    "boot": "vtpm_secureboot"
  }
}
PXE_JOBS_CHANGE = {
  "test_selection_mode":"pxe",
  "classifier":"one-click-gos-qual-pxe",
  "filters": {"os":"windows10_22H2", "type":"enterprise",
              "boot": "vtpm_secureboot, legacy"}
}
GOS_BATCH_SIZE_MAPPING = {
  "virtio": 5,
  "guest_os_qual": 10,
  "gos_upgrade": 10,
  "pxe": 10
}
GOS_CLASSIFIER_MAPPING = {
  "guest_os_qual": "one-click-gos-qual",
  "virtio": "one-click-virtio",
  "pxe": "one-click-gos-qual-pxe",
  "gos_upgrade": "one-click-gos-qual-upgrades"
}

###################################
#           NGD CONSTANTS         #
###################################
GPU_MODELS = ["Tesla_M60", "Tesla_T4_compute", "Tesla_M10",
              "Quadro_RTX_6000/8000_compute", "Ampere_100",
              "Ampere_40", "Tesla_V100_compute", "Tesla_P40_compute",
              "Tesla_V100D_compute", "Ampere_10", "Ampere_30", "Ampere_16",
              "Ampere_100_80G", "Quadro_RTX_6000/8000_active"]
NGD_AHV_UPGRADE_HEADERS = ["Source AHV", "Destination AHV",
                           "Source AOS", "GPU Model", "Platform", "Start Time",
                           "End Time", "Total Time", "Status", "Result",
                           "Reason", "Jita URL"]
NGD_AHV_UPGRADE_JOBS_CHANGE = {
  "upgrade": {
    "ahv_upgrade": {
      "jobs": [
        {
          "job_profile": "ngd_upgrade_oneclick_base_jp"
        }
      ]
    },
  }
}
NGD_AHV_AOS_UPGRADE_JOBS_CHANGE = {
  "upgrade": {
    "ahv_aos_upgrade": {
      "jobs": [
        {
          "job_profile": "ngd_upgrade_oneclick_base_jp"
        }
      ]
    }
  }
}

NGD_SANITY_QUAL_JOBS = {
  "job_profile": "Apeiron_GPU_Sanity_Qualification_JP",
  "email_ids": ["ahv-hypervisor-qa@nutanix.com"]
}

NGD_HOST_QUAL_JOBS = {
  "job_profile": "Apeiron_GPU_Host_Qualification_JP",
  "email_ids": ["ahv-hypervisor-qa@nutanix.com"]
}

NGD_MANAGEMENT_QUAL_JOBS = {
  "job_profile": "Apeiron_GPU_Management_Qualification_JP",
  "email_ids": ["ahv-hypervisor-qa@nutanix.com"]
}

NDK_SANITY_QUAL_JOBS = {}

CSI_EI_JOBS_CHANGE = {
  "deployment": {
    "csi_deployment_path": {
      "jobs": [
        {
          "job_profile": "csi_ei_base_apeiron_jp",
          "pc_enabled": True
        }
      ]
    }
  }
}

CSI_FEAT_JOBS = {
  "jobs": [
    {
      "enable_direct_pool_execution": True,
      "pc_enabled": True,
      "email_ids": ["cnds-qa@nutanix.com"],
      "pool_name": ["global-pool"],
      "global_pool_coupon": "carmine-lobster"
    }
  ]
}
AHV_FEAT_JOBS = {
  "email_ids": ["ahv-hypervisor-qa@nutanix.com"]
}

CSI_DEPLOYMENT_PATH_JOBS = {
  "enable_direct_pool_execution": True,
  "pc_enabled": True,
  "email_ids": ["cnds-qa@nutanix.com"],
  "job_profile": "csi_deploy"
}

CSI_PC_UPGRADE_JOBS = {
  "pc_enabled": True,
  "email_ids": ["cnds-qa@nutanix.com"],
  "job_profile": "csi_deploy",
  "dep_job_profile": "csi_upgrade"
}

CSI_AOS_UPGRADE_JOBS = {
  "pc_enabled": True,
  "email_ids": ["cnds-qa@nutanix.com"],
  "job_profile": "csi_deploy",
  "dep_job_profile": "csi_upgrade"
}

CSI_UPGRADE_JOBS = {
  "pc_enabled": True,
  "email_ids": ["cnds-qa@nutanix.com"],
  "job_profile": "csi_deploy",
  "dep_job_profile": "csi_upgrade"
}

OBJECTS_FEAT_JOBS = {
  "pc_enabled": True,
  "email_ids": ["niranjan.bhosale@nutanix.com", "sreenu.pidugu@nutanix.com"],
  "dep_job_profile": "Apeiron_Objects_Regression_Deployment_JP",
  "platforms": ["NX"],
  "disable_pu_bucket": True,
  "suite_based_resource_manager": True
}

OBJECTS_DEPLOYMENT_JOBS = {
  "pc_enabled": True,
  "workers": 3,
  "email_ids": ["niranjan.bhosale@nutanix.com", "sreenu.pidugu@nutanix.com"],
  "job_profile": "Apeiron_Objects_Regression_Deployment_JP",
  "platforms": ["NX"],
  "disable_pu_bucket": True,
  "suite_based_resource_manager": True
}

OBJECTS_UPGRADE_JOBS = {
  "workers": 5,
  "job_profile": "apeiron_upgrade_JP",
  "dep_job_profile": "apeiron_deployment_test_JP",
  "pc_enabled": True,
  "email_ids": ["anuradha.n@nutanix.com", "niranjan.bhosale@nutanix.com", \
                "sreenu.pidugu@nutanix.com"],
  "platforms": ["NX"],
  "disable_pu_bucket": False,
  "suite_based_resource_manager": True
}

LEVEL_2_AHV_UPGRADE_JOBS_CHANGE = {
  "multi_level_upgrade_": True,
  "levels": 2
}

LEVEL_3_AHV_UPGRADE_JOBS_CHANGE = {
  "multi_level_upgrade_": True,
  "levels": 3
}

######## CLI TRIGGER CONSTANTS #########
MIN_QUAL_JOBS = {
  "product": "ahv",
  "ahv_upgrade_": True,
  "ahv_aos_upgrade_": True,
  "deployment_path_": True,
  "gos_qual_": True,
  "email_ids": ["ahv-hypervisor-qa@nutanix.com"],
  "pool_name": [
    "ahv-hypervisor-qa",
    "global-pool"
  ],
  "max_clusters": 3,
  "platforms": ["NX"],
  "lcm_url": ["http://download.nutanix.com/lcm/qa-staging/lcm-release/release"],
  "skip_nos_supported_check": True,
  "workers": 3,
  "disable_pu_bucket": True,
  "filters":{
    "os":("windows11_22H2, windows10_22H2, windowsserver2022_preview,"
          "windowsserver2019, rhel8.8, rhel9.2"),
    "type":"enterprise, standard, server",
    "boot":"legacy, uefi, secureboot, vtpm_credentialguard"
  },
  "deployment": {
    "deployment_path": {
      "jobs": [
        {
          "job_profile": "1_click_dep_path_platform_base_jp",
          "foundation_builds": [
            "http://endor.dyn.nutanix.com/releases/Foundation-5.4/"\
            "foundation-5.4.tar.gz",
            "http://endor.dyn.nutanix.com/releases/Foundation-5.5/"\
            "foundation-5.5.tar.gz"
          ],
        }
      ]
    }
  }
}

#################### OBJECTS ##############################
POST_RUN_PLUGIN = {
  "metadata":{
    "kind":"test"
  },
  "args":{
    "branch":"buckets-4.1"
  },
  "name":"UpdateBranchPlugin",
  "stage":"post_run",
  "description": ("Updates the branch info of the test result document"
                  " with the info provided in args")
}

#################### MAPPINGS #############################
PIPELINE = {
  "daily": ["daily"],
  "weekly": ["daily", "weekly"],
  "bi-weekly": ["daily", "weekly", "bi-weekly"]
}

SRC_AHV_MAP = {
  "ahv_upgrade": "Source_AHV",
  "ahv_aos_upgrade": "Source_AHV",
  "deployment_path": "Source_AHV",
  "multi_level_ahv_upgrade": "Source_AHV",
  "level_2_ahv_upgrade": "Source_AHV",
  "level_3_ahv_upgrade": "Source_AHV",
  "ngd_ahv_upgrade": "Source_AHV",
  "ngd_ahv_aos_upgrade": "Source_AHV",
  "guest_os_qual": "ahv",
  "pxe": "ahv",
  "virtio": "ahv",
  "gos_upgrade": "ahv"
}

SRC_AOS_MAP = {
  "ahv_upgrade": "Source_AOS",
  "ahv_aos_upgrade": "Source_AOS",
  "deployment_path": "Source_AOS",
  "csi_functional_qual": "Source_AOS",
  "csi_error_injection": "Source_AOS",
  "multi_level_ahv_upgrade": "Source_AOS",
  "level_2_ahv_upgrade": "Source_AOS",
  "level_3_ahv_upgrade": "Source_AOS",
  "ngd_ahv_upgrade": "Source_AOS",
  "ngd_ahv_aos_upgrade": "Source_AOS",
  "msp_pc_upgrade": "Source_PE",
  "guest_os_qual": "aos",
  "pxe": "aos",
  "virtio": "aos",
  "gos_upgrade": "aos"
}

PRODUCT_SRC_AOS_MAP = {
  "csi": "Source_AOS",
  "objects": "Source_AOS",
  "ahv": "Source_AOS",
  "msp": "Source_AOS"
}

PRODUCT_INDEX_DB_MAP = {
  "csi": "csi_apeiron_index_db",
  "objects": "objects_apeiron_index_db",
  "ahv": "one_click_index_db",
  "msp": "msp_apeiron_index_db"
}

PRODUCT_MAIN_DB_MAP = {
  "csi": "csi_apeiron_db",
  "objects": "objects_apeiron_db",
  "ahv": "one_click_db",
  "msp": "msp_apeiron_db"
}

########### MSP UPGRADE CONSTS ############################

MSP_PC_UPGRADE_HEADERS = ["Source MSP", "Source PC", "Source AOS",
                          "Objects Version", "Destination MSP",
                          "Destination PC", "Destination AOS",
                          "Platform", "Start Time", "End Time", "Total Time",
                          "Status", "Result", "Reason",
                          "Jita URL"]

MSP_OSS_MAPPING = {
  "2.4.0": "3.3",
  "2.4.0.1": "3.3",
  "2.4.1": "3.4.0.1",
  "2.4.1.1": "3.4.0.1",
  "2.4.2": "3.5",
  "2.4.2.1": "3.5",
  "2.4.3": "3.5",
  "2.4.3.1": "3.5",
  "2.4.3.2": "3.5"
}

########### DEPLOYMENT CONSTANTS ###########
CLUSTER_REQUEST_RETRY_DELAY = 300
