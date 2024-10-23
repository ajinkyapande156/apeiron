"""
Copyright (c) 2022 Nutanix Inc. All rights reserved.

Author: vedant.dalal@nutanix.com

Test Generics Module.
"""
#pylint: disable=too-many-locals,too-many-branches,too-many-statements,too-many-lines,protected-access
from urllib.request import urlopen
import json
import copy
import uuid
import time
from datetime import datetime
import sys

from threading import RLock, Thread

from framework.lib.nulog import INFO, STEP, ERROR
from libs.ahv.workflows.one_click.jita_v2_client \
  import JitaClient
from libs.ahv.workflows.one_click import metadata
from libs.ahv.workflows.one_click.args_manipulator \
  import ArgsManipulator
from libs.ahv.workflows.one_click.emailer import \
  Emailer
from libs.ahv.workflows.one_click.objects_branch \
  import ObjectsUtil
from libs.ahv.workflows.one_click.feat_manager \
  import FeatManager
from libs.ahv.workflows.one_click.matrix_generator \
  import MatrixGenerator
from libs.ahv.workflows.one_click.jarvis_client import \
  JarvisClient
from libs.ahv.workflows.one_click.rdm_client import \
  RDMClient
from libs.ahv.workflows.one_click.task_manager.\
  task_manager import TaskManager
from libs.ahv.workflows.one_click import database
from libs.ahv.workflows.one_click.executor import \
  Executor
from libs.ahv.workflows.one_click.deployment_manager \
  import DeploymentManager
from libs.ahv.workflows.one_click.report_generator \
  import ReportGenerator
from libs.ahv.workflows.one_click.elk_client \
  import ELKClient

sys.setrecursionlimit(2500)

class TestGenerics():
  """
  A class containing methods to trigger and generate 1-click Framework.
  """
  def __init__(self):
    '''
    Constructor method
    '''
    self.matrices = {
      "ahv_upgrade": [],
      "ahv_aos_upgrade": [],
      "deployment_path": []
    }
    self.feat_dict_mapping = {
      "csi": metadata.CSI_FEAT_JOBS,
      "ndk": metadata.CSI_FEAT_JOBS,
      "objects": metadata.OBJECTS_FEAT_JOBS,
      "ahv": metadata.AHV_FEAT_JOBS
    }
    self._resource_manager = {}
    self._global_lock = RLock()
    self._resource_lock = RLock()
    self._ahv_upgrade_lock = RLock()
    self._ahv_aos_upgrade_lock = RLock()
    self._deployment_path_lock = RLock()
    self._gos_qual_lock = RLock()
    self.ahv_upgrade_dict = {}
    self.ahv_aos_upgrade_dict = {}
    self.deployment_path_dict = {}
    self.emailer = Emailer()
    self._ahv_upgrade_executor = Executor()
    self._ahv_aos_executor = Executor()
    self._deployment_executor = Executor()
    self.object_util = ObjectsUtil()
    self.task_manager = None
    self.ahv_task_manager = None
    self.ahv_aos_task_manager = None
    self.dep_path_task_manager = None
    self.jita = JitaClient(username="svc.ahv-qa",
                           password="6TcU84qZiZHTvFu!#jDD")
    self.jarvis = JarvisClient(
      username="svc.ahv-qa",
      password="6TcU84qZiZHTvFu!#jDD"
    )
    self.report_generator = ReportGenerator()
    self.rdm = RDMClient(
      username="svc.ahv-qa",
      password="6TcU84qZiZHTvFu!#jDD"
    )
    self.args_manipulator = ArgsManipulator()
    self.matrix_generator = MatrixGenerator()
    self.deployment_manager = DeploymentManager()
    self.elk_db_name = "one_click_index_db"
    self.db_conn = ELKClient(
      username="elastic",
      password="sa.Z<FPnvRODb_^-"
    )

  def test_container(self, test_args):
    """
    Method to execute whole test suite.

    Args:
      test_args(dict): Test Arguments passed to the test.
    """
    csi_product_meta = None
    ndk_product_meta = None
    objects_product_meta = None
    INFO("Jobs provided by user: "+str(test_args["jobs"]))
    INFO("Jobs Data Type: "+str(type(test_args["jobs"])))

    if isinstance(test_args["jobs"], dict):
      jobs_json = test_args["jobs"]
      jobs_master = self.args_manipulator.user_input_manipulator(
        user_input_jobs=jobs_json
      )
    else:
      if self.args_manipulator.is_string_a_url(
          string=test_args.get("jobs")
      ):
        jobs_master = self.args_manipulator.user_input_manipulator(
          user_input_jobs=json.loads(urlopen(test_args["jobs"]).read().decode())
        )
      else:
        ERROR("Jobs Provided in the test args is not a correct URL"\
              "Checking if the string is a dictionary.")
        INFO("Convert the string Jobs Dict to dict.")
        jobs_master = self.args_manipulator.user_input_manipulator(
          user_input_jobs=json.loads(test_args.get("jobs"))
        )

    _matrix_id = None
    if jobs_master.get("uuid"):
      _matrix_id = jobs_master.get("uuid")
    else:
      _matrix_id = uuid.uuid1()
    _start_time = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
    INFO("Test UUID: "+str(_matrix_id))
    with self._global_lock:
      database.matrices.update(
        {
          "uuid": str(_matrix_id),
          "matrix_start_time": _start_time,
          "matrix_start_time_epoch": str(time.time())
        }
      )
    _index_dict = {
      "uuid": database.matrices["uuid"],
      "matrix_start_time": database.matrices["matrix_start_time"],
      "matrix_start_time_epoch": database.matrices["matrix_start_time_epoch"]
    }

    ahv_product_meta = {}
    ahv_aos_product_meta = {}
    if jobs_master.get("product") == "ahv":
      metadata.DEFAULT_JOBS["email_ids"] = ["ahv-hypervisor-qa@nutanix.com"]
      if "ahv_product_meta" in test_args.keys():
        if self.args_manipulator.is_string_a_url(
            test_args.get("ahv_product_meta")
        ):
          ahv_product_meta = json.loads(
            urlopen(test_args["ahv_product_meta"]).read().decode())
        else:
          ERROR("AHV Product Meta in the test args is not a correct URL."\
                "Creating own custome Prod Meta")
          ahv_product_meta = self.args_manipulator.create_prod_meta(
            ahv_version=jobs_master["ahv_version"],
            ahv_branch=jobs_master.get("ahv_branch")
          )
      else:
        ahv_product_meta = self.args_manipulator.create_prod_meta(
          ahv_version=jobs_master["ahv_version"],
          ahv_branch=jobs_master.get("ahv_branch")
        )

      if "ahv_aos_product_meta" in test_args.keys():
        if self.args_manipulator.is_string_a_url(
            string=test_args.get("ahv_aos_product_meta")
        ):
          ahv_aos_product_meta = json.loads(
            urlopen(test_args["ahv_aos_product_meta"]).read().decode())
        else:
          ERROR("AHV+AOS Product Meta in the test args is not a correct URL."\
                "Creating own custom Product Meta")
          ahv_aos_product_meta = copy.deepcopy(ahv_product_meta)
      else:
        ahv_aos_product_meta = copy.deepcopy(ahv_product_meta)

      # Update the product meta in format expected by other methods
      ahv_product_meta = self.args_manipulator.update_prod_meta(
        prod_meta=ahv_product_meta, ahv_version=jobs_master["ahv_version"]
      )
      ahv_aos_product_meta = self.args_manipulator.update_prod_meta(
        prod_meta=ahv_aos_product_meta, ahv_version=jobs_master["ahv_version"]
      )

    if jobs_master.get("commit_version"):
      with self._global_lock:
        database.matrices.update(
          {
            "commit_version": str(jobs_master.get("commit_version"))
          }
        )
        _index_dict.update({
          "commit_version": str(jobs_master.get("commit_version"))
        })

    if jobs_master.get("product") == "msp":
      if "msp_product_meta" in test_args.keys():
        msp_product_meta = json.loads(
          urlopen(test_args["msp_product_meta"]).read().decode()
        )

    if jobs_master.get("product") == "csi":
      if test_args.get("csi_product_meta"):
        csi_product_meta = json.loads(
          urlopen(test_args["csi_product_meta"]).read().decode()
        )

    if jobs_master.get("product") == "ndk":
      if test_args.get("ndk_product_meta"):
        ndk_product_meta = json.loads(
          urlopen(test_args["ndk_product_meta"]).read().decode()
        )

    if jobs_master.get("product") in ["objects"]:
      objects_version = jobs_master.get("objects_version")
      image_tag_oss_version = ("buckets-"+str(objects_version) if
                               objects_version != "poseidon" else "poseidon")
      commit_id = self.object_util.resolve_product_version_to_commit(
        product_branch=image_tag_oss_version,
        product_version=jobs_master.get("product_version")
      )
      with self._global_lock:
        database.matrices.update(
          {
            "commit_version": str(commit_id)
          }
        )
        _index_dict.update({
          "commit_version": str(commit_id)
        })
      if jobs_master.get("commit_version"):
        with self._global_lock:
          database.matrices.update(
            {
              "commit_version": str(jobs_master.get("commit_version"))
            }
          )
          _index_dict.update({
            "commit_version": str(jobs_master.get("commit_version"))
          })
      if test_args.get("objects_product_meta"):
        objects_product_meta = json.loads(
          urlopen(test_args["objects_product_meta"]).read().decode()
        )
      INFO(f"Objects product meta: {objects_product_meta}")
      jobs_to_update = self.args_manipulator.fetch_and_update_dependencies(
        objects_version=jobs_master.get("objects_version"),
        objects_prod_meta=objects_product_meta
      )
      INFO(f"Jobs to update: {json.dumps(jobs_to_update)}")
      jobs_master.update(jobs_to_update)
      if (jobs_master.get("feat_execution_") or
          jobs_master.get("objects_deployment_")):
        args_override = (
          self.args_manipulator.manipulate_objects_args_override(
            jobs=jobs_master,
            product_meta=objects_product_meta,
            msp_version=jobs_master.get("msp_version"),
            objects_version=jobs_master.get("objects_version"),
            image_tag="123",
            product_version=jobs_master.get("product_version")
          )
        )
        INFO(f"Args override: {json.dumps(args_override)}")
        jobs_master.update({
          "args_override": args_override
        })

    if jobs_master.get("aos_rel_branch"):
      with self._global_lock:
        database.matrices.update(
          {
            "aos_rel_branch": jobs_master.get("aos_rel_branch")
          }
        )
        _index_dict.update({
          "aos_rel_branch": jobs_master.get("aos_rel_branch")
        })

    if jobs_master.get("pipeline"):
      with self._global_lock:
        database.matrices.update(
          {
            "pipeline": jobs_master.get("pipeline")
          }
        )
        _index_dict.update({
          "pipeline": jobs_master.get("pipeline")
        })

    if "email_ids" in jobs_master.keys():
      metadata.EMAIL_SENDER_LIST = jobs_master["email_ids"]

    for version in metadata.VERSION_LIST:
      if jobs_master.get(version):
        with self._global_lock:
          _index_dict.update({
            version: jobs_master[version]
          })
          database.matrices.update({
            version: jobs_master[version]
          })

    INFO(f"Index dict: {json.dumps(_index_dict)}")
    # self.db_conn.create_index(db_name=self.elk_db_name)
    if jobs_master.get("product") == "msp":
      self.elk_db_name = "msp_apeiron_index_db"
    if jobs_master.get("product") == "csi":
      self.elk_db_name = "csi_apeiron_index_db"
    if jobs_master.get("product") == "objects":
      self.elk_db_name = "objects_apeiron_index_db"
    if jobs_master.get("product") == "ndk":
      self.elk_db_name = "ndk_apeiron_index_db"

    INFO("Jobs: "+json.dumps(jobs_master))

    INFO("Check if cluster is provided, Add to resource_manager if present")
    if "cluster_name" in jobs_master.keys():
      INFO("Adding the clusters to the resource manager.")
      self.deployment_manager.add_cluster_to_resource_manager(
        cluster_list=jobs_master["cluster_name"]
      )

    # Thread Generation and Initiation.
    if jobs_master.get("ahv_upgrade_"):
      _ahv_upgrade_thread = Thread(target=self._ahv_upgrade,
                                   args=(
                                     copy.deepcopy(jobs_master),
                                     copy.deepcopy(ahv_product_meta)
                                   )
                                  )
    if jobs_master.get("ahv_aos_upgrade_"):
      _ahv_aos_upgrade_thread = Thread(target=self._ahv_aos_upgrade,
                                       args=(
                                         copy.deepcopy(jobs_master),
                                         copy.deepcopy(ahv_aos_product_meta)
                                       )
                                      )

    if jobs_master.get("msp_pc_upgrade_"):
      _msp_pc_upgrade_thread = Thread(target=self._msp_pc_upgrade,
                                      args=(
                                        copy.deepcopy(jobs_master),
                                        copy.deepcopy(msp_product_meta)
                                      )
                                      )

    if jobs_master.get("multi_level_upgrade_"):
      _multi_level_upgrade_thread = Thread(target=self._multi_level_upgrade,
                                           args=(
                                             copy.deepcopy(jobs_master),
                                             copy.deepcopy(ahv_aos_product_meta)
                                           )
                                          )

    if jobs_master.get("level_2_upgrade_"):
      INFO("Level 2 Upgrade")
      _level2_jobs = copy.deepcopy(jobs_master)
      _level2_jobs.update(metadata.LEVEL_2_AHV_UPGRADE_JOBS_CHANGE)
      _level2_ahv_upgrade_thread = Thread(target=self._multi_level_upgrade,
                                          args=(
                                            copy.deepcopy(_level2_jobs),
                                            copy.deepcopy(ahv_product_meta),
                                            "level_2_ahv_upgrade"
                                          )
                                          )

    if jobs_master.get("level_3_upgrade_"):
      INFO("Level 3 Upgrade")
      _level3_jobs = copy.deepcopy(jobs_master)
      _level3_jobs.update(metadata.LEVEL_3_AHV_UPGRADE_JOBS_CHANGE)
      _level3_ahv_upgrade_thread = Thread(target=self._multi_level_upgrade,
                                          args=(
                                            copy.deepcopy(_level3_jobs),
                                            copy.deepcopy(ahv_product_meta),
                                            "level_3_ahv_upgrade"
                                          )
                                          )

    if jobs_master.get("deployment_path_"):
      _dep_path_thread = Thread(target=self._deployment_path,
                                args=(
                                  copy.deepcopy(jobs_master),
                                )
                               )

    if jobs_master.get("ngd_ahv_upgrade_"):
      _ngd_ahv_upgrade_jobs = copy.deepcopy(jobs_master)
      _ngd_ahv_upgrade_jobs.update(
        metadata.NGD_AHV_UPGRADE_JOBS_CHANGE
      )
      _ngd_ahv_upgrade_thread = Thread(target=self._ahv_upgrade,
                                       args=(
                                         copy.deepcopy(_ngd_ahv_upgrade_jobs),
                                         copy.deepcopy(ahv_product_meta),
                                         "ngd_ahv_upgrade"
                                       )
                                      )

    if jobs_master.get("ngd_sanity_qual_"):
      _ngd_sanity_thread = Thread(target=self._ngd_deployment,
                                  args=(
                                    copy.deepcopy(jobs_master),
                                    copy.deepcopy(ahv_product_meta),
                                    "gpu_sanity_qual",
                                    metadata.NGD_SANITY_QUAL_JOBS
                                  )
                                 )

    if jobs_master.get("ngd_host_qual_"):
      _ngd_host_thread = Thread(target=self._ngd_deployment,
                                args=(
                                  copy.deepcopy(jobs_master),
                                  copy.deepcopy(ahv_product_meta),
                                  "gpu_host_qual",
                                  metadata.NGD_HOST_QUAL_JOBS
                                )
                               )

    if jobs_master.get("ngd_management_qual_"):
      _ngd_management_thread = Thread(target=self._ngd_deployment,
                                      args=(
                                        copy.deepcopy(jobs_master),
                                        copy.deepcopy(ahv_product_meta),
                                        "gpu_management_qual",
                                        metadata.NGD_MANAGEMENT_QUAL_JOBS
                                      )
                                     )

    if jobs_master.get("ngd_ahv_aos_upgrade_"):
      _ngd_ahv_aos_upgrade_jobs = copy.deepcopy(jobs_master)
      _ngd_ahv_aos_upgrade_jobs.update(
        metadata.NGD_AHV_AOS_UPGRADE_JOBS_CHANGE
      )
      _ngd_ahv_aos_upgrade_thread = Thread(target=self._ahv_aos_upgrade,
                                           args=(
                                             copy.deepcopy(
                                               _ngd_ahv_aos_upgrade_jobs
                                             ),
                                             copy.deepcopy(
                                               ahv_aos_product_meta
                                             ),
                                             "ngd_ahv_aos_upgrade"
                                           )
                                          )
    if jobs_master.get("gos_qual_"):
      _gos_qual_jobs = copy.deepcopy(metadata.GOS_QUAL_JOBS_CHANGE)
      _gos_qual_jobs.update(jobs_master)
      _gos_qual_thread = Thread(target=self._gos_qual,
                                args=(
                                  copy.deepcopy(_gos_qual_jobs),
                                )
                                )

    if jobs_master.get("virtio_"):
      INFO("Virtio")
      _virtio_jobs = copy.deepcopy(jobs_master)
      _virtio_jobs.update(metadata.VIRTIO_JOBS_CHANGE)
      _virtio_thread = Thread(target=self._gos_qual,
                              args=(
                                copy.deepcopy(_virtio_jobs),
                                "virtio"
                              )
                             )

    if jobs_master.get("gos_upgrade_"):
      INFO("GOS Upgrade")
      _gos_upgrade_jobs = copy.deepcopy(jobs_master)
      _gos_upgrade_jobs.update(metadata.GOS_UPGRADE_JOBS_CHANGE)
      _gos_upgrade_thread = Thread(target=self._gos_qual,
                                   args=(
                                     copy.deepcopy(_gos_upgrade_jobs),
                                     "gos_upgrade"
                                   )
                                  )

    if jobs_master.get("pxe_"):
      INFO("PXE")
      _pxe_jobs = copy.deepcopy(jobs_master)
      _pxe_jobs.update(metadata.PXE_JOBS_CHANGE)
      _pxe_thread = Thread(target=self._gos_qual,
                           args=(
                             copy.deepcopy(_pxe_jobs),
                             "pxe"
                           )
                          )

    if jobs_master.get("csi_functional_"):
      _csi_dep_path_thread = Thread(target=self._csi_deployment,
                                    args=(
                                      copy.deepcopy(jobs_master),
                                      copy.deepcopy(csi_product_meta),
                                      "csi_functional_qual"
                                    )
                                   )

    if jobs_master.get("csi_deployment_path_"):
      _csi_deployment_path_thread = Thread(target=self._csi_deployment_path,
                                           args=(
                                             copy.deepcopy(jobs_master),
                                             copy.deepcopy(csi_product_meta),
                                             "csi_deployment_path"
                                           )
                                          )

    if jobs_master.get("csi_pc_upgrade_"):
      _csi_pc_upgrade_thread = Thread(target=self._csi_pc_upgrade,
                                      args=(
                                        copy.deepcopy(jobs_master),
                                        copy.deepcopy(csi_product_meta),
                                        "csi_pc_upgrade"
                                      )
                                     )

    if jobs_master.get("csi_aos_upgrade_"):
      _csi_aos_upgrade_thread = Thread(target=self._csi_aos_upgrade,
                                       args=(
                                         copy.deepcopy(jobs_master),
                                         copy.deepcopy(csi_product_meta),
                                         "csi_aos_upgrade"
                                       )
                                      )

    if jobs_master.get("csi_upgrade_"):
      _csi_upgrade_thread = Thread(target=self._csi_upgrade,
                                   args=(
                                     copy.deepcopy(jobs_master),
                                     copy.deepcopy(csi_product_meta),
                                     "csi_upgrade"
                                   )
                                  )

    if jobs_master.get("ndk_upgrade_"):
      _ndk_upgrade_thread = Thread(target=self._ndk_upgrade,
                                   args=(
                                     copy.deepcopy(jobs_master),
                                     copy.deepcopy(ndk_product_meta),
                                     "ndk_upgrade"
                                   )
                                  )

    if jobs_master.get("ndk_csi_upgrade_"):
      _ndk_csi_upgrade_thread = Thread(target=self._ndk_csi_upgrade,
                                       args=(
                                         copy.deepcopy(jobs_master),
                                         copy.deepcopy(ndk_product_meta),
                                         "ndk_csi_upgrade"
                                       )
                                      )

    if jobs_master.get("ndk_pc_upgrade_"):
      _ndk_pc_upgrade_thread = Thread(target=self._ndk_pc_upgrade,
                                      args=(
                                        copy.deepcopy(jobs_master),
                                        copy.deepcopy(ndk_product_meta),
                                        "ndk_pc_upgrade"
                                      )
                                      )

    if jobs_master.get("ndk_aos_upgrade_"):
      _ndk_aos_upgrade_thread = Thread(target=self._ndk_aos_upgrade,
                                       args=(
                                         copy.deepcopy(jobs_master),
                                         copy.deepcopy(ndk_product_meta),
                                         "ndk_aos_upgrade"
                                       )
                                      )

    if jobs_master.get("objects_upgrade_"):
      _objects_upgrade_thread = Thread(target=self._objects_upgrade,
                                       args=(
                                         copy.deepcopy(jobs_master),
                                         copy.deepcopy(objects_product_meta),
                                         "objects_upgrade"
                                       )
                                      )

    if jobs_master.get("objects_deployment_"):
      _objects_dep_thread = Thread(target=self._objects_deployment,
                                   args=(
                                     copy.deepcopy(jobs_master),
                                     copy.deepcopy(objects_product_meta),
                                     "objects_deployment"
                                   )
                                  )

    if jobs_master.get("csi_error_injection_"):
      _csi_ei_jobs = copy.deepcopy(jobs_master)
      _csi_ei_jobs.update(metadata.CSI_EI_JOBS_CHANGE)
      _csi_ei_thread = Thread(target=self._csi_deployment,
                              args=(
                                copy.deepcopy(_csi_ei_jobs),
                                copy.deepcopy(csi_product_meta),
                                "csi_error_injection"
                              )
                             )
    prod_meta_mapping = {
      "csi": csi_product_meta,
      "ndk": ndk_product_meta,
      "objects": objects_product_meta
    }
    if (jobs_master.get("product") in ["csi", "objects", "ndk", "ahv"] and
        jobs_master.get("feat_execution_")):
      _feat_manager = FeatManager()
      print(test_args[str(jobs_master.get("product"))+"_feat_dict"])
      csi_feat_dict = json.loads(
        urlopen(
          test_args[str(jobs_master.get("product"))+"_feat_dict"]
        ).read().decode()
      )
      suite_dict = {}
      suite_dict = _feat_manager.fetch_suite_details(
        feat_dict=csi_feat_dict,
        pipeline=jobs_master.get("pipeline")
      )
      _thread_dict = {}

      for suite in suite_dict.keys():
        worker_num = _feat_manager.get_num_of_workers(
          suite=suite,
          suite_dict=suite_dict
        )
        metadata.CSI_FEAT_JOBS["jobs"][0].update({
          "workers": worker_num
        })

        _feat_jobs = copy.deepcopy(
          self.feat_dict_mapping.get(jobs_master.get("product"))
        )
        _product_meta = copy.deepcopy(
          prod_meta_mapping.get(jobs_master.get("product"))
        )
        INFO(jobs_master)
        if jobs_master.get("product") in ["objects"]:
          _thread_dict.update({
            str(jobs_master.get("product"))+"_"+str(suite): Thread(
              target=self._objects_feat_execution,
              args=(
                copy.deepcopy(jobs_master),
                copy.deepcopy(_product_meta),
                copy.deepcopy(suite_dict),
                copy.deepcopy(str(jobs_master.get("product"))+"_"+str(suite))
              )
            )
          })
        elif jobs_master.get("product") in ["ahv"]:
          _thread_dict.update({
            str(jobs_master.get("product"))+"_"+str(suite): Thread(
              target=self._ahv_feat_execution,
              args=(
                copy.deepcopy(jobs_master),
                copy.deepcopy(_product_meta),
                copy.deepcopy(suite_dict),
                copy.deepcopy(str(jobs_master.get("product"))+"_"+str(suite))
              )
            )
          })
        else:
          _thread_dict.update({
            str(jobs_master.get("product"))+"_"+str(suite): Thread(
              target=self._csi_deployment,
              args=(
                copy.deepcopy(jobs_master),
                copy.deepcopy(_product_meta),
                copy.deepcopy(_feat_jobs),
                copy.deepcopy(suite_dict),
                copy.deepcopy(str(jobs_master.get("product"))+"_"+str(suite))
              )
            )
          })

    if jobs_master.get("feat_execution_"):
      for thread in _thread_dict:
        time.sleep(1)
        _thread_dict[thread].start()
    if jobs_master.get("deployment_path_"):
      _dep_path_thread.start()
    if jobs_master.get("ngd_sanity_qual_"):
      _ngd_sanity_thread.start()
    if jobs_master.get("ngd_host_qual_"):
      _ngd_host_thread.start()
    if jobs_master.get("ngd_management_qual_"):
      _ngd_management_thread.start()
    if jobs_master.get("csi_deployment_path_"):
      _csi_deployment_path_thread.start()
    if jobs_master.get("csi_pc_upgrade_"):
      _csi_pc_upgrade_thread.start()
    if jobs_master.get("csi_aos_upgrade_"):
      _csi_aos_upgrade_thread.start()
    if jobs_master.get("ndk_upgrade_"):
      _ndk_upgrade_thread.start()
    if jobs_master.get("ndk_csi_upgrade_"):
      _ndk_csi_upgrade_thread.start()
    if jobs_master.get("ndk_aos_upgrade_"):
      _ndk_aos_upgrade_thread.start()
    if jobs_master.get("ndk_pc_upgrade_"):
      _ndk_pc_upgrade_thread.start()
    if jobs_master.get("csi_upgrade_"):
      _csi_upgrade_thread.start()
    if jobs_master.get("objects_upgrade_"):
      _objects_upgrade_thread.start()
    if jobs_master.get("objects_deployment_"):
      _objects_dep_thread.start()
    if jobs_master.get("csi_functional_"):
      _csi_dep_path_thread.start()
    if jobs_master.get("csi_error_injection_"):
      time.sleep(5)
      _csi_ei_thread.start()
    if jobs_master.get("ahv_aos_upgrade_"):
      _ahv_aos_upgrade_thread.start()
    if jobs_master.get("ahv_upgrade_"):
      _ahv_upgrade_thread.start()
    if jobs_master.get("multi_level_upgrade_"):
      _multi_level_upgrade_thread.start()
    if jobs_master.get("msp_pc_upgrade_"):
      _msp_pc_upgrade_thread.start()
    if jobs_master.get("level_2_upgrade_"):
      _level2_ahv_upgrade_thread.start()
    if jobs_master.get("level_3_upgrade_"):
      _level3_ahv_upgrade_thread.start()
    if jobs_master.get("ngd_ahv_aos_upgrade_"):
      _ngd_ahv_aos_upgrade_thread.start()
    if jobs_master.get("ngd_ahv_upgrade_"):
      _ngd_ahv_upgrade_thread.start()
    if jobs_master.get("gos_qual_"):
      _gos_qual_thread.start()
    if jobs_master.get("virtio_"):
      time.sleep(60)
      _virtio_thread.start()
    if jobs_master.get("gos_upgrade_"):
      time.sleep(60)
      _gos_upgrade_thread.start()
    if jobs_master.get("pxe_"):
      time.sleep(60)
      _pxe_thread.start()

    self.db_conn.ingest_data_with_id(data=_index_dict, op_type="create",
                                     db_name=self.elk_db_name,
                                     data_id=_index_dict["uuid"])

    if jobs_master.get("feat_execution_"):
      for thread in _thread_dict:
        _thread_dict[thread].join()
    if jobs_master.get("deployment_path_"):
      _dep_path_thread.join()
    if jobs_master.get("ngd_sanity_qual_"):
      _ngd_sanity_thread.join()
    if jobs_master.get("ngd_host_qual_"):
      _ngd_host_thread.join()
    if jobs_master.get("ngd_management_qual_"):
      _ngd_management_thread.join()
    if jobs_master.get("csi_deployment_path_"):
      _csi_deployment_path_thread.join()
    if jobs_master.get("csi_pc_upgrade_"):
      _csi_pc_upgrade_thread.join()
    if jobs_master.get("csi_upgrade_"):
      _csi_upgrade_thread.join()
    if jobs_master.get("objects_upgrade_"):
      _objects_upgrade_thread.join()
    if jobs_master.get("objects_deployment_"):
      _objects_dep_thread.join()
    if jobs_master.get("csi_aos_upgrade_"):
      _csi_aos_upgrade_thread.join()
    if jobs_master.get("ndk_upgrade_"):
      _ndk_upgrade_thread.join()
    if jobs_master.get("ndk_csi_upgrade_"):
      _ndk_csi_upgrade_thread.join()
    if jobs_master.get("ndk_aos_upgrade_"):
      _ndk_aos_upgrade_thread.join()
    if jobs_master.get("ndk_pc_upgrade_"):
      _ndk_pc_upgrade_thread.join()
    if jobs_master.get("csi_functional_"):
      _csi_dep_path_thread.join()
    if jobs_master.get("csi_error_injection_"):
      _csi_ei_thread.join()
    if jobs_master.get("ahv_aos_upgrade_"):
      _ahv_aos_upgrade_thread.join()
    if jobs_master.get("ahv_upgrade_"):
      _ahv_upgrade_thread.join()
    if jobs_master.get("multi_level_upgrade_"):
      _multi_level_upgrade_thread.join()
    if jobs_master.get("msp_pc_upgrade_"):
      _msp_pc_upgrade_thread.join()
    if jobs_master.get("level_2_upgrade_"):
      _level2_ahv_upgrade_thread.join()
    if jobs_master.get("level_3_upgrade_"):
      _level3_ahv_upgrade_thread.join()
    if jobs_master.get("ngd_ahv_aos_upgrade_"):
      _ngd_ahv_aos_upgrade_thread.join()
    if jobs_master.get("ngd_ahv_upgrade_"):
      _ngd_ahv_upgrade_thread.join()
    if jobs_master.get("gos_qual_"):
      _gos_qual_thread.join()
    if jobs_master.get("virtio_"):
      _virtio_thread.join()
    if jobs_master.get("gos_upgrade_"):
      _gos_upgrade_thread.join()
    if jobs_master.get("pxe_"):
      _pxe_thread.join()

    #Release Clusters
    self.deployment_manager.release_clusters(jobs=jobs_master)

    #Report Generator
    self.report_generator.generate_and_send_report(
      product=jobs_master["product"],
      main_version=str(jobs_master["product"])+"_version"
    )
    INFO("Final Matrix: "+json.dumps(database.matrices))

  def test_workload_container(self, test_args):
    """
    Method to execute whole test suite.

    Args:
      test_args(dict): Test Arguments passed to the test.
    """
    INFO("Jobs provided by user: "+str(test_args["jobs"]))

    #fetch and manipulate the jobs received
    if isinstance(test_args["jobs"], dict):
      jobs_json = json.loads(test_args["jobs"])
      INFO(str(type(jobs_json)))
      INFO(jobs_json["aos_version"])
      jobs_master = self.args_manipulator.user_input_manipulator(
        user_input_jobs=json.loads(jobs_json),
        default_jobs=metadata.WORKLOAD_DEFAULT_JOBS
      )
    else:
      if self.args_manipulator.is_string_a_url(
          string=test_args.get("jobs")
      ):
        jobs_master = self.args_manipulator.user_input_manipulator(
          user_input_jobs=json.loads(
            urlopen(test_args["jobs"]).read().decode()
          ),
          default_jobs=metadata.WORKLOAD_DEFAULT_JOBS
        )
      else:
        ERROR("Jobs Provided in the test args is not a correct URL"\
              "Checking if the string is a dictionary.")
        INFO("Convert the string Jobs Dict to dict.")
        jobs_master = self.args_manipulator.user_input_manipulator(
          user_input_jobs=json.loads(test_args.get("jobs")),
          default_jobs=metadata.WORKLOAD_DEFAULT_JOBS
        )
    INFO("Final Jobs: "+json.dumps(jobs_master))
    INFO("Workload Triggered for Task ID: "+jobs_master.get("task_id"))
    _start_time = datetime.now().strftime("%d-%m-%Y %H:%M:%S")

    with self._global_lock:
      database.matrices.update(
        {
          "uuid": str(jobs_master.get("task_id")),
          "matrix_start_time": _start_time,
          "matrix_start_time_epoch": str(time.time()),
          "execution_data": []
        }
      )

    # update the apeiron DB with the status as triggered.

    apeiron_db_query = {
      "doc": {
        "apeiron_start_time": database.matrices.get("matrix_start_time"),
        "apeiron_start_time_epoch": database.matrices.get(
          "matrix_start_time_epoch"
        ),
        "execution_data": database.matrices["execution_data"],
        "status": "triggered"
      },
      "detect_noop": False
    }
    elk_update = self.db_conn.elk_update_query(
      index_name="workload_execution",
      elk_func="_update",
      payload=apeiron_db_query,
      data_id=database.matrices["uuid"]
    )

    if not elk_update:
      ERROR("Unable to update Apeiron DB.")
      ERROR("Please check the logs and retry.")

    else:
      INFO("Apeiron DB update successfull.")

      INFO("Check if the cluster IP exists in Apeiron DB.")
      cluster_ip_query = {
        "query": {
          "bool": {
            "must": [
              {
                "match": {
                  "_id": jobs_master.get("cluster_ip").replace(".", "_")
                }
              }
            ]
          }
        }
      }
      cluster_details = self.db_conn.query_elk(
        index_name="cluster_registration",
        query_dict=cluster_ip_query
      )
      if not cluster_details:
        ERROR("Cluster Details not found in Apeiron DB for IP: "+
              jobs_master.get("cluster_ip"))
      else:
        INFO("Updating jobs with cluster details")
        jobs_master.update({
          "cluster_details": cluster_details[0]
        })
        INFO("Check if the workload names exists in Apeiron DB.")
        wk_details = []
        for wk_name in jobs_master.get("workload_name"):
          wk_name_query = {
            "query": {
              "bool": {
                "must": [
                  {
                    "match": {
                      "_id": wk_name
                    }
                  }
                ]
              }
            }
          }
          wk_detail = self.db_conn.query_elk(
            index_name="objects_workload_registration",
            query_dict=wk_name_query
          )
          wk_detail.extend(self.db_conn.query_elk(
            index_name="ahv_workload_registration",
            query_dict=wk_name_query
          ))
          if not wk_detail:
            ERROR("Workload Details not found in Apeiron DB for workload "\
                 "name: "+wk_name)
            break
          wk_details.append(wk_detail[0])

        INFO("Check if the workload_Details contains all workloads")
        if len(wk_details) != len(jobs_master.get("workload_name")):
          ERROR("Workload details have some missing value.")
        else:
          INFO("Updating the workload details in Jobs")
          jobs_master.update({
            "workload_details": wk_details
          })

          INFO("Triggering the executor")
          _workload_executor = Executor()

          _workload_executor.workload_executor(
            jobs=jobs_master
          )

          INFO("Update the final data to the Apeiron DB.")
          apeiron_db_query = {
            "doc": {
              "execution_data": database.matrices["execution_data"],
              "status": "completed"
            },
            "detect_noop": False
          }
          elk_update = self.db_conn.elk_update_query(
            index_name="workload_execution",
            elk_func="_update",
            payload=apeiron_db_query,
            data_id=database.matrices["uuid"]
          )
          if not elk_update:
            ERROR("Unable to update Apeiron DB.")
            ERROR("Please check the logs and retry.")

          else:
            INFO("Apeiron DB update successfull.")

  def _msp_pc_upgrade(self, jobs, msp_product_meta, suite=None):
    """
    Method to generate and execute possible MSP PC upgrade paths.

    Args:
      jobs(json): Jobs Master JSON containing the input.
      msp_product_meta(json): MSP Product Meta file.
      suite(str): Suite Name.
    """
    _msp_pc_upgrade_slave = 1
    if not suite:
      suite = "msp_pc_upgrade"
    database.matrices.update({
      suite: {}
    })
    INFO("MSP PC Upgrade: Check if cluster is provided,"
         " Add to resource_manager if present")
    if "cluster_name" in jobs["upgrade"]["msp_pc_upgrade"].keys():
      INFO("Adding the clusters to the resource manager.")
      self.deployment_manager.add_cluster_to_resource_manager(
        cluster_list=jobs["upgrade"]["msp_pc_upgrade"]["cluster_name"],
        suite=suite
      )
    INFO(jobs["upgrade"]["msp_pc_upgrade"])
    _msp_pc_upgrade_jobs = self.args_manipulator.jobs_manipulator(
      jobs=jobs,
      jobs_upgrade=jobs["upgrade"]["msp_pc_upgrade"]
    )

    INFO("MSP PC Upgrade Jobs: "+str(_msp_pc_upgrade_jobs))
    for i in range(len(_msp_pc_upgrade_jobs["jobs"])):
      _job_to_execute = _msp_pc_upgrade_jobs["jobs"][i]

      if "workers" in _job_to_execute.keys():
        _msp_pc_upgrade_slave = _job_to_execute["workers"]

      self.msp_pc_task_manager = TaskManager(
        quotas={
          str(suite)+"_slave": {
            "num_workers": _msp_pc_upgrade_slave
          }
        },
        worker_poolsize=_msp_pc_upgrade_slave,
        timeout=96000000
      )

      STEP("Generating MSP-PC Upgrade Matrix")
      self.msp_pc_upgrade_dict = self.matrix_generator.msp_pc_upgrade(
        msp_product_meta=msp_product_meta,
        jobs=_job_to_execute,
        suite=suite
      )
      database.matrices[str(suite)] = copy.deepcopy(self.msp_pc_upgrade_dict)
      _msp_pc_upgrade_print_list = self.args_manipulator.json_to_list_converter(
        upgrade_dict=database.matrices[str(suite)],
        headers=metadata.MSP_PC_UPGRADE_HEADERS
      )
      INFO("MSP PC LIST: "+str(_msp_pc_upgrade_print_list))
      self.args_manipulator.log_matrix_printer(
        headers=metadata.MSP_PC_UPGRADE_HEADERS,
        print_list=_msp_pc_upgrade_print_list
      )
      # INFO(json.dumps(database.matrices["ahv_upgrade"]))
      time.sleep(2)

      # ENTER THE DATABASE WITH THE GENERATED MATRIX
      for out_key in database.matrices[str(suite)]:
        for in_key in database.matrices[str(suite)][str(out_key)].keys():
          self.db_conn.ingest_data_with_id(
            db_name="msp_apeiron_db",
            data=database.matrices[str(suite)][str(out_key)][str(in_key)],
            data_id=(database.matrices[str(suite)][str(out_key)][str(in_key)]
                     ["row_id"]),
            op_type="create"
          )

      for out_key in self.msp_pc_upgrade_dict:
        in_key_list = self.msp_pc_upgrade_dict[out_key].keys()
        in_key_int_list = []
        for key in in_key_list:
          in_key_int_list.append(int(key))
        in_key_int_list.sort()
        in_key_int_list.reverse()
        INFO("MSP PC Upgrade: Number of Upgrade Paths: "+str(in_key_int_list))

        while True:
          with self._ahv_upgrade_lock:
            in_key = in_key_int_list.pop()
            INFO("MSP PC Upgrade: Adding Keys to Executor: ("+str(out_key)+
                 ", "+str(in_key)+")")
        # for in_key in self.ahv_upgrade_dict[out_key].keys():
            _msp_pc_upgrade_executor = Executor()
            self.msp_pc_task_manager.add(
              _msp_pc_upgrade_executor.msp_pc_executor,
              headers=metadata.MSP_PC_UPGRADE_HEADERS,
              jobs=_job_to_execute,
              action=suite,
              out_key=str(out_key),
              in_key=str(in_key),
              quota_type=str(suite)+"_slave"
            )
            time.sleep(10)
            if jobs.get("pool_name"):
              time.sleep(120)

            if not in_key_int_list:
              self.msp_pc_task_manager.complete_run(
                wait_for_inflight_tasks_to_schedule=True,
                wait_time=1,
                timeout=7200000)
              break

  def _ahv_upgrade(self, jobs, ahv_product_meta, suite=None):
    """
    Method to generate and execute possible AHV upgrade paths.

    Args:
      jobs(json): Jobs Master JSON containing the input.
      ahv_product_meta(json): AHV Product Meta file.
      suite(str): Suite Name.
    """
    _ahv_upgrade_slave = 1
    if not suite:
      suite = "ahv_upgrade"
    database.matrices.update({
      suite: {}
    })
    INFO("AHV Upgrade: Check if cluster is provided,"
         " Add to resource_manager if present")
    if "cluster_name" in jobs["upgrade"]["ahv_upgrade"].keys():
      INFO("Adding the clusters to the resource manager.")
      self.deployment_manager.add_cluster_to_resource_manager(
        cluster_list=jobs["upgrade"]["ahv_upgrade"]["cluster_name"],
        suite=suite
      )
    INFO(jobs["upgrade"]["ahv_upgrade"])
    _ahv_upgrade_jobs = self.args_manipulator.jobs_manipulator(
      jobs=jobs,
      jobs_upgrade=jobs["upgrade"]["ahv_upgrade"]
    )

    INFO("AHV Upgrade Jobs: "+str(_ahv_upgrade_jobs))
    for i in range(len(_ahv_upgrade_jobs["jobs"])):
      _job_to_execute = _ahv_upgrade_jobs["jobs"][i]

      if "workers" in _job_to_execute.keys():
        _ahv_upgrade_slave = _job_to_execute["workers"]

      self.ahv_task_manager = TaskManager(
        quotas={
          str(suite)+"_slave": {
            "num_workers": _ahv_upgrade_slave
          }
        },
        worker_poolsize=_ahv_upgrade_slave,
        timeout=96000000
      )

      STEP("Generating AHV Upgrade Matrix")
      self.ahv_upgrade_dict = self.matrix_generator.ahv_upgrade(
        ahv_product_meta=ahv_product_meta,
        jobs=_job_to_execute,
        suite=suite
      )
      database.matrices[str(suite)] = copy.deepcopy(self.ahv_upgrade_dict)
      _ahv_upgrade_print_list = self.args_manipulator.json_to_list_converter(
        upgrade_dict=database.matrices[str(suite)],
        headers=metadata.AHV_UPGRADE_HEADERS
      )
      self.args_manipulator.log_matrix_printer(
        headers=metadata.AHV_UPGRADE_HEADERS,
        print_list=_ahv_upgrade_print_list
      )
      # INFO(json.dumps(database.matrices["ahv_upgrade"]))
      time.sleep(2)
      # ENTER THE DATABASE WITH THE GENERATED MATRIX
      for out_key in database.matrices[str(suite)]:
        for in_key in database.matrices[str(suite)][str(out_key)].keys():
          self.db_conn.ingest_data_with_id(
            db_name="one_click_db",
            data=database.matrices[str(suite)][str(out_key)][str(in_key)],
            data_id=(database.matrices[str(suite)][str(out_key)][str(in_key)]
                     ["row_id"]),
            op_type="create"
          )

      for out_key in self.ahv_upgrade_dict:
        in_key_list = self.ahv_upgrade_dict[out_key].keys()
        in_key_int_list = []
        for key in in_key_list:
          in_key_int_list.append(int(key))
        in_key_int_list.sort()
        in_key_int_list.reverse()
        INFO("AHV Upgrade: Number of Upgrade Paths: "+str(in_key_int_list))

        while True:
          with self._ahv_upgrade_lock:
            in_key = in_key_int_list.pop()
            INFO("AHV Upgrade: Adding Keys to Executor: ("+str(out_key)+
                 ", "+str(in_key)+")")
        # for in_key in self.ahv_upgrade_dict[out_key].keys():
            _ahv_upgrade_executor = Executor()
            self.ahv_task_manager.add(
              _ahv_upgrade_executor.clone_and_execute_job_and_send_mail,
              headers=metadata.AHV_UPGRADE_HEADERS,
              jobs=_job_to_execute,
              action=suite,
              out_key=str(out_key),
              in_key=str(in_key),
              quota_type=str(suite)+"_slave"
            )
            time.sleep(10)
            if jobs.get("pool_name"):
              time.sleep(120)

            if not in_key_int_list:
              self.ahv_task_manager.complete_run(
                wait_for_inflight_tasks_to_schedule=True,
                wait_time=1,
                timeout=7200000)
              break

      # _ahv_upgrade_tm = TaskManager(
      #   quotas={"ahv_upgrade":{"num_workers":_ahv_upgrade_workers}},
      #   worker_poolsize=_ahv_upgrade_workers,
      #   timeout=96000000
      # )

      # while True:
      #   with self._ahv_upgrade_lock:
      #     combination_to_test = self.ahv_upgrade_list.pop()

      #   _ahv_upgrade_tm.add(self._clone_and_execute_job_and_send_mail,
      #     test_list=combination_to_test,
      #     headers=metadata.AHV_UPGRADE_HEADERS,
      #     jobs=_ahv_upgrade_jobs[i],
      #     action="ahv_upgrade",
      #     quotas="ahv_upgrade_slave"
      #   )

      #   if not self.ahv_upgrade_list:
      #     _ahv_upgrade_tm.complete_run(True, 1, 720000)
      #     break

  def _ahv_aos_upgrade(self, jobs, ahv_product_meta, suite=None):
    """
    Method to generate and execute possible AHV upgrade paths.

    Args:
      jobs(json): Jobs Master JSON containing the input.
      ahv_product_meta(json): AHV Product Meta file.
      suite(str): Suite Name.
    """
    _ahv_aos_upgrade_slave = 1
    if not suite:
      suite = "ahv_aos_upgrade"
    database.matrices.update({
      suite: {}
    })

    INFO("AHV+AOS Upgrade: Check if cluster is provided,"
         " Add to resource_manager if present")
    if "cluster_name" in jobs["upgrade"]["ahv_aos_upgrade"].keys():
      INFO("Adding the clusters to the resource manager.")
      self.deployment_manager.add_cluster_to_resource_manager(
        cluster_list=jobs["upgrade"]["ahv_aos_upgrade"]["cluster_name"],
        suite=suite
      )
    # INFO(json.dumps(ahv_product_meta))
    _ahv_aos_upgrade_jobs = self.args_manipulator.jobs_manipulator(
      jobs=jobs,
      jobs_upgrade=jobs["upgrade"]["ahv_aos_upgrade"]
    )
    INFO("AHV+AOS Upgrade Jobs: "+str(_ahv_aos_upgrade_jobs))
    # ahv_product_meta = json.loads(urlopen("http://phx-ep-filer"
    # "-build-prod-1.corp.nutanix.com/builds/product-meta-cci-builds/master/
    # latest/software/ahv.json").read().decode())
    for i in range(len(_ahv_aos_upgrade_jobs["jobs"])):
      _job_to_execute = _ahv_aos_upgrade_jobs["jobs"][i]

      if "workers" in _job_to_execute.keys():
        _ahv_aos_upgrade_slave = _job_to_execute["workers"]

      self.ahv_aos_task_manager = TaskManager(
        quotas={
          str(suite)+"_slave": {
            "num_workers": _ahv_aos_upgrade_slave
          }
        },
        worker_poolsize=_ahv_aos_upgrade_slave,
        timeout=96000000
      )

      STEP("AHV+AOS Upgrade: Generating AHV-AOS Upgrade Matrix")
      self.ahv_aos_upgrade_dict = self.matrix_generator.ahv_aos_upgrade(
        ahv_product_meta=ahv_product_meta,
        jobs=_job_to_execute,
        suite=suite
      )
      database.matrices[str(suite)] = copy.deepcopy(
        self.ahv_aos_upgrade_dict)
      _ahv_aos_print_list = self.args_manipulator.json_to_list_converter(
        upgrade_dict=database.matrices[str(suite)],
        headers=metadata.AHV_AOS_UPGRADE_HEADERS
      )
      self.args_manipulator.log_matrix_printer(
        headers=metadata.AHV_AOS_UPGRADE_HEADERS,
        print_list=_ahv_aos_print_list
      )
      time.sleep(1)
      # ENTER THE DATABASE WITH THE GENERATED MATRIX
      INFO("Add the matrix to database.")
      for out_key in database.matrices[str(suite)]:
        for in_key in database.matrices[str(suite)][str(out_key)].keys():
          self.db_conn.ingest_data_with_id(
            db_name="one_click_db",
            data=database.matrices[str(suite)][str(out_key)][str(in_key)],
            data_id=(database.matrices[str(suite)][str(out_key)][str(in_key)]
                     ["row_id"]),
            op_type="create"
          )
      for out_key in self.ahv_aos_upgrade_dict:
        in_key_list = self.ahv_aos_upgrade_dict[out_key].keys()
        in_key_int_list = []
        for key in in_key_list:
          in_key_int_list.append(int(key))
        in_key_int_list.sort()
        in_key_int_list.reverse()
        INFO("AHV+AOS Upgrade: Number of Upgrade Paths: "+str(in_key_int_list))

        while True:
          with self._ahv_aos_upgrade_lock:
            in_key = in_key_int_list.pop()
            INFO("AHV+AOS Upgrade: Adding Keys to Executor: ("+str(out_key)+
                 ", "+str(in_key)+")")
        # for in_key in self.ahv_upgrade_dict[out_key].keys():
            _ahv_aos_executor = Executor()
            self.ahv_aos_task_manager.add(
              _ahv_aos_executor.clone_and_execute_job_and_send_mail,
              headers=metadata.AHV_AOS_UPGRADE_HEADERS,
              jobs=_job_to_execute,
              action=suite,
              out_key=str(out_key),
              in_key=str(in_key),
              quota_type=str(suite)+"_slave"
            )
            time.sleep(10)

            if not in_key_int_list:
              self.ahv_aos_task_manager.complete_run(
                wait_for_inflight_tasks_to_schedule=True,
                wait_time=1,
                timeout=7200000)
              break

      # INFO(json.dumps(self.matrices["ahv_aos_upgrade"]))
      # self.args_manipulator.pretty_print(
      # headers=metadata.AHV_AOS_UPGRADE_HEADERS,
      # print_list=self.matrices["ahv_aos_upgrade"])
      # self.ahv_aos_upgrade_list.reverse()
      # _ahv_aos_upgrade_tm = TaskManager(
      #   quotas={"ahv_aos_upgrade":{"num_workers":_ahv_aos_upgrade_workers}},
      #   worker_poolsize=_ahv_aos_upgrade_workers,
      #   timeout=96000000
      # )

      # while True:
      #   with self._ahv_upgrade_lock:
      #     combination_to_test = self.ahv_aos_upgrade_list.pop()

      #     _ahv_aos_upgrade_tm.add(self._clone_and_execute_job_and_send_mail,
      #       test_list=combination_to_test,
      #       headers=metadata.AHV_AOS_UPGRADE_HEADERS,
      #       jobs=_ahv_aos_upgrade_jobs[i],
      #       action="ahv_aos_upgrade",
      #       quotas="ahv_aos_upgrade"
      #     )

      #   if not self.ahv_aos_upgrade_list:
      #     break

  def _multi_level_upgrade(self, jobs, ahv_product_meta, suite=None):
    """
    Method to generate and execute possible AHV upgrade paths.

    Args:
      jobs(json): Jobs Master JSON containing the input.
      ahv_product_meta(json): AHV Product Meta file.
      suite(str): Suite Name.
    """
    _multi_level_upgrade_slave = 1
    if not suite:
      suite = "multi_level_ahv_upgrade"
    database.matrices.update({
      suite: {}
    })

    INFO("Multi Level Upgrade: Check if cluster is provided,"
         " Add to resource_manager if present")
    if "cluster_name" in jobs["upgrade"]["multi_level_upgrade"].keys():
      INFO("Adding the clusters to the resource manager.")
      self.deployment_manager.add_cluster_to_resource_manager(
        cluster_list=jobs["upgrade"]["multi_level_upgrade"]["cluster_name"],
        suite=suite
      )
    # INFO(json.dumps(ahv_product_meta))
    _multi_level_upgrade_jobs = self.args_manipulator.jobs_manipulator(
      jobs=jobs,
      jobs_upgrade=jobs["upgrade"]["multi_level_upgrade"]
    )
    INFO("Multi Level Upgrade Jobs: "+str(_multi_level_upgrade_jobs))
    # ahv_product_meta = json.loads(urlopen("http://phx-ep-filer"
    # "-build-prod-1.corp.nutanix.com/builds/product-meta-cci-builds/master/
    # latest/software/ahv.json").read().decode())
    for i in range(len(_multi_level_upgrade_jobs["jobs"])):
      _job_to_execute = _multi_level_upgrade_jobs["jobs"][i]

      if "workers" in _job_to_execute.keys():
        _multi_level_upgrade_slave = _job_to_execute["workers"]

      _multi_level_upgrade_task_manager = TaskManager(#pylint: disable=invalid-name
        quotas={
          str(suite)+"_slave": {
            "num_workers": _multi_level_upgrade_slave
          }
        },
        worker_poolsize=_multi_level_upgrade_slave,
        timeout=96000000
      )

      STEP("AHV+AOS Upgrade: Generating AHV-AOS Upgrade Matrix")
      multi_level_upgrade_dict = self.matrix_generator.multi_level_upgrade(
        ahv_product_meta=ahv_product_meta,
        jobs=_job_to_execute,
        suite=suite
      )
      database.matrices[str(suite)] = copy.deepcopy(
        multi_level_upgrade_dict)
      _multi_level_print_list = self.args_manipulator.json_to_list_converter(
        upgrade_dict=database.matrices[str(suite)],
        headers=metadata.AHV_AOS_UPGRADE_HEADERS
      )
      self.args_manipulator.log_matrix_printer(
        headers=metadata.AHV_AOS_UPGRADE_HEADERS,
        print_list=_multi_level_print_list
      )
      time.sleep(1)
      INFO("Add the matrix to database.")
      for out_key in database.matrices[str(suite)]:
        for in_key in database.matrices[str(suite)][str(out_key)]:
          self.db_conn.ingest_data_with_id(
            db_name="one_click_db",
            data=database.matrices[str(suite)][str(out_key)][str(in_key)],
            data_id=(database.matrices[str(suite)][str(out_key)][str(in_key)]
                     ["row_id"]),
            op_type="create"
          )

      for out_key in multi_level_upgrade_dict:
        in_key_list = multi_level_upgrade_dict[out_key].keys()
        in_key_int_list = []
        for key in in_key_list:
          in_key_int_list.append(int(key))
        in_key_int_list.sort()
        in_key_int_list.reverse()
        INFO("AHV+AOS Upgrade: Number of Upgrade Paths: "+str(in_key_int_list))

        while True:
          with self._ahv_aos_upgrade_lock:
            in_key = in_key_int_list.pop()
            INFO("AHV+AOS Upgrade: Adding Keys to Executor: ("+str(out_key)+
                 ", "+str(in_key)+")")
        # for in_key in self.ahv_upgrade_dict[out_key].keys():
            _multi_level_executor = Executor()
            _multi_level_upgrade_task_manager.add(
              _multi_level_executor.clone_and_execute_job_and_send_mail,
              headers=metadata.AHV_AOS_UPGRADE_HEADERS,
              jobs=_job_to_execute,
              action=suite,
              out_key=str(out_key),
              in_key=str(in_key),
              quota_type=str(suite)+"_slave"
            )
            time.sleep(10)

            if not in_key_int_list:
              _multi_level_upgrade_task_manager.complete_run(
                wait_for_inflight_tasks_to_schedule=True,
                wait_time=1,
                timeout=7200000)
              break

  def _csi_deployment(self, jobs, prod_meta, suite_jobs, suite_dict,
                      suite=None):
    """
    Method to generate and execute possible AHV upgrade paths.

    Args:
      jobs(json): Jobs Master JSON containing the input.
      prod_meta(dict): Product Meta.
      suite_jobs(dict): Suite Jobs.
      suite_dict(dict): Suite Dictionary.
      suite(str): Suite Name.
    """
    _product_meta_gen_mapping = {
      "csi": self.matrix_generator.csi_deployment,
      "objects": self.matrix_generator.objects_deployment,
      "ndk": self.matrix_generator.ndk_deployment,
      "ahv": self.matrix_generator.ahv_feat_execution
    }
    _product_header_mapping = {
      "csi": metadata.CSI_DEPLOYMENT_HEADERS,
      "ndk": metadata.NDK_DEPLOYMENT_HEADERS,
      "objects": metadata.OBJECTS_DEPLOYMENT_HEADERS,
      "ahv": metadata.AHV_FEAT_HEADERS
    }
    _product_db_map = {
      "csi": "csi_apeiron_db",
      "objects": "objects_apeiron_db",
      "ndk": "ndk_apeiron_db",
      "ahv": "one_click_db"
    }

    if not suite:
      suite = "csi_deployment_path"
    database.matrices.update({
      suite: {}
    })

    headers = _product_header_mapping.get(
      suite,
      _product_header_mapping.get(
        jobs.get("product"), metadata.CSI_DEPLOYMENT_HEADERS
      )
    )
    INFO(headers)
    INFO(str(suite)+": Check if cluster is provided,"
         " Add to resource_manager if present")

    # INFO("Deployment Pat: "+str(jobs))
    _deployment_path_jobs = self.args_manipulator.jobs_manipulator(
      jobs=jobs,
      jobs_upgrade=suite_jobs
    )
    if "cluster_name" in _deployment_path_jobs.keys():
      INFO("Adding the clusters to the resource manager.")
      self.deployment_manager.add_cluster_to_resource_manager(
        cluster_list=_deployment_path_jobs["cluster_name"],
        suite=suite
      )

    INFO(str(suite)+": "+str(_deployment_path_jobs))
    for i in range(len(_deployment_path_jobs["jobs"])):
      _job_to_execute = _deployment_path_jobs["jobs"][i]

      STEP("Generating "+str(suite)+" Matrix")
      self.deployment_path_dict = _product_meta_gen_mapping.get(
        suite, _product_meta_gen_mapping[jobs.get(
          "product", self.matrix_generator.csi_deployment
        )]
      )(
        jobs=_job_to_execute,
        prod_meta=prod_meta,
        suite_dict=suite_dict,
        suite=suite
      )
      database.matrices[str(suite)] = copy.deepcopy(
        self.deployment_path_dict
      )
      _dep_path_print_list = self.args_manipulator.json_to_list_converter(
        upgrade_dict=database.matrices[str(suite)],
        headers=headers
      )
      self.args_manipulator.log_matrix_printer(
        headers=headers,
        print_list=_dep_path_print_list
      )

      if _job_to_execute.get("email_ids"):
        for email in _job_to_execute["email_ids"]:
          if email not in metadata.EMAIL_SENDER_LIST:
            metadata.EMAIL_SENDER_LIST.append(email)
      INFO("Add the matrix to database.")
      for out_key in database.matrices[str(suite)]:
        for in_key in database.matrices[str(suite)][str(out_key)]:
          self.db_conn.ingest_data_with_id(
            db_name=_product_db_map.get(jobs.get("product"), "csi_apeiron_db"),
            data=database.matrices[str(suite)][str(out_key)][str(in_key)],
            data_id=(database.matrices[str(suite)][str(out_key)][str(in_key)]
                     ["row_id"]),
            op_type="create"
          )
      _thread_dict = {}
      for out_key in self.deployment_path_dict:
        in_key_list = self.deployment_path_dict[out_key].keys()
        in_key_int_list = []
        for key in in_key_list:
          in_key_int_list.append(int(key))
        in_key_int_list.sort()
        in_key_int_list.reverse()
        INFO(str(suite)+": Number of Upgrade Paths: "+str(in_key_int_list))

        while True:
          with self._deployment_path_lock:
            in_key = in_key_int_list.pop()
            INFO(str(suite)+": Adding Keys to Executor: ("+str(out_key)+
                 ", "+str(in_key)+")")
            _deployment_executor = Executor()

            _thread_dict.update({
              str(suite+"_"+str(out_key)+"_"+str(in_key)): Thread(
                target=_deployment_executor.clone_and_execute_job_and_send_mail,
                args=(
                  copy.deepcopy(headers),
                  copy.deepcopy(_job_to_execute),
                  copy.deepcopy(suite),
                  copy.deepcopy(str(out_key)),
                  copy.deepcopy(str(in_key))
                )
              )
            })

            if not in_key_int_list:
              break

      for thread in _thread_dict:
        time.sleep(10)
        _thread_dict[thread].start()

      for thread in _thread_dict:
        _thread_dict[thread].join()

  def _csi_deployment_path(self, jobs, prod_meta, suite=None):
    """
    Method to generate and execute possible AHV upgrade paths.

    Args:
      jobs(json): Jobs Master JSON containing the input.
      prod_meta(dict): Product Meta
      suite(str): Suite Name.
    """
    if suite is None:
      suite = "csi_deployment_path"

    _deployment_executor = Executor()
    _pre_executor = TestGenerics()

    _pre_executor._generic_pre_executor(
      jobs=copy.deepcopy(jobs),
      prod_meta=copy.deepcopy(prod_meta),
      suite_jobs=copy.deepcopy(metadata.CSI_DEPLOYMENT_PATH_JOBS),
      suite=copy.deepcopy(suite),
      matrix_generator=self.matrix_generator.csi_deployment_path,
      headers=copy.deepcopy(metadata.CSI_DEPLOYMENT_PATH_HEADERS),
      db_name="csi_apeiron_db",
      executor=_deployment_executor.clone_and_execute_job_and_send_mail
    )

  def _csi_pc_upgrade(self, jobs, prod_meta, suite=None):
    """
    Method to generate and execute possible AHV upgrade paths.

    Args:
      jobs(json): Jobs Master JSON containing the input.
      prod_meta(dict): Product Meta
      suite(str): Suite Name.
    """
    if suite is None:
      suite = "csi_pc_upgrade"

    _deployment_executor = Executor()
    _pre_executor = TestGenerics()

    _pre_executor._generic_pre_executor(
      jobs=copy.deepcopy(jobs),
      prod_meta=copy.deepcopy(prod_meta),
      suite_jobs=copy.deepcopy(metadata.CSI_PC_UPGRADE_JOBS),
      suite=copy.deepcopy(suite),
      matrix_generator=self.matrix_generator.csi_pc_upgrade,
      headers=copy.deepcopy(metadata.CSI_PC_UPGRADE_HEADERS),
      db_name="csi_apeiron_db",
      executor=_deployment_executor.msp_pc_executor
    )

  def _csi_upgrade(self, jobs, prod_meta, suite=None):
    """
    Method to generate and execute possible AHV upgrade paths.

    Args:
      jobs(json): Jobs Master JSON containing the input.
      prod_meta(dict): Product Meta
      suite(str): Suite Name.
    """
    if suite is None:
      suite = "csi_upgrade"

    _deployment_executor = Executor()
    _pre_executor = TestGenerics()

    _pre_executor._generic_pre_executor(
      jobs=copy.deepcopy(jobs),
      prod_meta=copy.deepcopy(prod_meta),
      suite_jobs=copy.deepcopy(metadata.CSI_UPGRADE_JOBS),
      suite=copy.deepcopy(suite),
      matrix_generator=self.matrix_generator.csi_upgrade,
      headers=copy.deepcopy(metadata.CSI_UPGRADE_HEADERS),
      db_name="csi_apeiron_db",
      executor=_deployment_executor.msp_pc_executor
    )

  def _csi_aos_upgrade(self, jobs, prod_meta, suite=None):
    """
    Method to generate and execute possible AHV upgrade paths.

    Args:
      jobs(json): Jobs Master JSON containing the input.
      prod_meta(dict): Product Meta
      suite(str): Suite Name.
    """
    _pre_executor = TestGenerics()
    if suite is None:
      suite = "csi_pc_upgrade"

    _deployment_executor = Executor()

    _pre_executor._generic_pre_executor(
      jobs=copy.deepcopy(jobs),
      prod_meta=copy.deepcopy(prod_meta),
      suite_jobs=copy.deepcopy(metadata.CSI_AOS_UPGRADE_JOBS),
      suite=copy.deepcopy(suite),
      matrix_generator=self.matrix_generator.csi_aos_upgrade,
      headers=copy.deepcopy(metadata.CSI_AOS_UPGRADE_HEADERS),
      db_name="csi_apeiron_db",
      executor=_deployment_executor.msp_pc_executor
    )

  def _objects_upgrade(self, jobs, prod_meta, suite="objects_upgrade"):
    """
    Method to generate and execute possible Objects upgrade paths.

    Args:
      jobs(json): Jobs Master JSON containing the input.
      prod_meta(dict): Product Meta
      suite(str): Suite Name.
    """
    _deployment_executor = Executor()
    _pre_executor = TestGenerics()
    _object_upgrade_jobs = copy.deepcopy(metadata.OBJECTS_UPGRADE_JOBS)

    if jobs.get("max_clusters"):
      _object_upgrade_jobs.update({
        "workers": jobs.get("max_clusters")
      })

    if jobs.get("suite_args") and jobs["suite_args"].get("objects_upgrade"):
      _object_upgrade_jobs.update(
        jobs["suite_args"].get("objects_upgrade")
      )

    _pre_executor._generic_pre_executor(
      jobs=copy.deepcopy(jobs),
      prod_meta=copy.deepcopy(prod_meta),
      suite_jobs=copy.deepcopy(_object_upgrade_jobs),
      suite=copy.deepcopy(suite),
      matrix_generator=self.matrix_generator.objects_upgrade,
      headers=copy.deepcopy(metadata.OBJECTS_UPGRADE_HEADERS),
      db_name="objects_apeiron_db",
      executor=_deployment_executor.msp_pc_executor,
      pool_executor=_deployment_executor.clone_and_execute_job_and_send_mail
    )

  def _objects_feat_execution(self, jobs, prod_meta, suite_dict,
                              suite="objects_feat_execution"):
    """
    Method to generate and execute possible Objects upgrade paths.

    Args:
      jobs(json): Jobs Master JSON containing the input.
      prod_meta(dict): Product Meta.
      suite_dict(dict): Suite Dictionary.
      suite(str): Suite Name.
    """
    time.sleep(10)
    _deployment_executor = Executor()
    _feat_manager = FeatManager()
    _pre_executor = TestGenerics()
    suite_name_full_list = suite.split("_")
    worker_num = _feat_manager.get_num_of_workers(
      suite="_".join(suite_name_full_list[1:]),
      suite_dict=suite_dict
    )
    _object_feat_execution_jobs = copy.deepcopy(metadata.OBJECTS_FEAT_JOBS)
    _object_feat_execution_jobs.update({
      "workers": worker_num
    })

    if jobs.get("max_clusters"):
      _object_feat_execution_jobs.update({
        "workers": jobs.get("max_clusters")
      })

    if (jobs.get("suite_args") and
        jobs["suite_args"].get("objects_feat_execution")):
      _object_feat_execution_jobs.update(
        jobs["suite_args"].get("objects_feat_execution")
      )

    _pre_executor._generic_pre_executor(
      jobs=copy.deepcopy(jobs),
      prod_meta=copy.deepcopy(prod_meta),
      suite_jobs=copy.deepcopy(_object_feat_execution_jobs),
      suite=copy.deepcopy(suite),
      matrix_generator=self.matrix_generator.objects_feat_execution,
      headers=copy.deepcopy(metadata.OBJECTS_DEPLOYMENT_HEADERS),
      db_name="objects_apeiron_db",
      executor=_deployment_executor.msp_pc_executor,
      suite_dict=copy.deepcopy(suite_dict),
      pool_executor=_deployment_executor.clone_and_execute_job_and_send_mail,
      time_interval=180
    )

  def _ahv_feat_execution(self, jobs, prod_meta, suite_dict,
                          suite="ahv_feat_execution"):
    """
    Method to generate and execute possible Objects upgrade paths.

    Args:
      jobs(json): Jobs Master JSON containing the input.
      prod_meta(dict): Product Meta.
      suite_dict(dict): Suite Dictionary.
      suite(str): Suite Name.
    """
    _deployment_executor = Executor()
    _pre_executor = TestGenerics()
    _feat_manager = FeatManager()
    suite_name_full_list = suite.split("_")
    worker_num = _feat_manager.get_num_of_workers(
      suite="_".join(suite_name_full_list[1:]),
      suite_dict=suite_dict
    )
    metadata.AHV_FEAT_JOBS.update({
      "workers": worker_num
    })

    if jobs.get("max_clusters"):
      metadata.AHV_FEAT_JOBS.update({
        "workers": jobs.get("max_clusters")
      })

    _pre_executor._generic_pre_executor(
      jobs=copy.deepcopy(jobs),
      prod_meta=copy.deepcopy(prod_meta),
      suite_jobs=copy.deepcopy(metadata.AHV_FEAT_JOBS),
      suite=copy.deepcopy(suite),
      matrix_generator=self.matrix_generator.ahv_feat_execution,
      headers=copy.deepcopy(metadata.AHV_FEAT_HEADERS),
      db_name="one_click_db",
      executor=_deployment_executor.clone_and_execute_job_and_send_mail,
      suite_dict=copy.deepcopy(suite_dict),
      pool_executor=_deployment_executor.clone_and_execute_job_and_send_mail,
      time_interval=180
    )

  def _objects_deployment(self, jobs, prod_meta, suite_dict,
                          suite="objects_deployment"):
    """
    Method to generate and execute possible Objects upgrade paths.

    Args:
      jobs(json): Jobs Master JSON containing the input.
      prod_meta(dict): Product Meta.
      suite_dict(dict): Suite Dictionary.
      suite(str): Suite Name.
    """
    _deployment_executor = Executor()
    _pre_executor = TestGenerics()

    _object_deployment_jobs = copy.deepcopy(metadata.OBJECTS_DEPLOYMENT_JOBS)

    if jobs.get("suite_args") and jobs["suite_args"].get("objects_deployment"):
      _object_deployment_jobs.update(
        jobs["suite_args"].get("objects_deployment")
      )

    _pre_executor._generic_pre_executor(
      jobs=copy.deepcopy(jobs),
      prod_meta=copy.deepcopy(prod_meta),
      suite_jobs=copy.deepcopy(_object_deployment_jobs),
      suite=copy.deepcopy(suite),
      matrix_generator=self.matrix_generator.objects_deployment,
      headers=copy.deepcopy(metadata.OBJECTS_DEPLOYMENT_PATH_HEADERS),
      db_name="objects_apeiron_db",
      executor=_deployment_executor.clone_and_execute_job_and_send_mail,
      suite_dict=copy.deepcopy(suite_dict),
      pool_executor=_deployment_executor.clone_and_execute_job_and_send_mail,
    )

  def _ngd_deployment(self, jobs, prod_meta, suite="ngd_deployment", #pylint: disable=dangerous-default-value
                      suite_jobs=metadata.NGD_SANITY_QUAL_JOBS):
    """
    Method to generate and execute possible Objects upgrade paths.

    Args:
      jobs(json): Jobs Master JSON containing the input.
      prod_meta(dict): Product Meta.
      suite(str): Suite Name.
      suite_jobs(str): NGD test suites.
    """
    _deployment_executor = Executor()

    self._generic_pre_executor(
      jobs=jobs,
      prod_meta=prod_meta,
      suite_jobs=suite_jobs,
      suite=suite,
      matrix_generator=self.matrix_generator.ngd_deployment,
      headers=metadata.NGD_DEPLOYMENT_PATH_HEADERS,
      db_name="one_click_db",
      executor=_deployment_executor.clone_and_execute_job_and_send_mail,
      suite_dict=None,
      pool_executor=_deployment_executor.clone_and_execute_job_and_send_mail,
    )

  def _ndk_upgrade(self, jobs, prod_meta, suite="ngd_upgrade", #pylint: disable=dangerous-default-value
                   suite_jobs=metadata.NDK_SANITY_QUAL_JOBS):
    """
    Method to generate and execute possible Objects upgrade paths.

    Args:
      jobs(json): Jobs Master JSON containing the input.
      prod_meta(dict): Product Meta.
      suite(str): Suite Name.
      suite_jobs(str): NGD test suites.
    """
    _deployment_executor = Executor()
    INFO("NDK Upgrade")
    self._generic_pre_executor(
      jobs=jobs,
      prod_meta=prod_meta,
      suite_jobs=suite_jobs,
      suite=suite,
      matrix_generator=self.matrix_generator.ndk_upgrade,
      headers=metadata.NDK_UPGRADE_HEADERS,
      db_name="ndk_apeiron_db",
      executor=_deployment_executor.clone_and_execute_job_and_send_mail,
      suite_dict=None,
      pool_executor=_deployment_executor.clone_and_execute_job_and_send_mail,
    )

  def _ndk_aos_upgrade(self, jobs, prod_meta, suite="ndk_aos_upgrade", #pylint: disable=dangerous-default-value
                       suite_jobs=metadata.NDK_SANITY_QUAL_JOBS):
    """
    Method to generate and execute possible Objects upgrade paths.

    Args:
      jobs(json): Jobs Master JSON containing the input.
      prod_meta(dict): Product Meta.
      suite(str): Suite Name.
      suite_jobs(str): NGD test suites.
    """
    _deployment_executor = Executor()
    INFO("NDK Upgrade")
    self._generic_pre_executor(
      jobs=jobs,
      prod_meta=prod_meta,
      suite_jobs=suite_jobs,
      suite=suite,
      matrix_generator=self.matrix_generator.ndk_aos_upgrade,
      headers=metadata.NDK_AOS_UPGRADE_HEADERS,
      db_name="ndk_apeiron_db",
      executor=_deployment_executor.clone_and_execute_job_and_send_mail,
      suite_dict=None,
      pool_executor=_deployment_executor.clone_and_execute_job_and_send_mail,
    )

  def _ndk_csi_upgrade(self, jobs, prod_meta, suite="ndk_csi_upgrade", #pylint: disable=dangerous-default-value
                       suite_jobs=metadata.NDK_SANITY_QUAL_JOBS):
    """
    Method to generate and execute possible Objects upgrade paths.

    Args:
      jobs(json): Jobs Master JSON containing the input.
      prod_meta(dict): Product Meta.
      suite(str): Suite Name.
      suite_jobs(str): NGD test suites.
    """
    _deployment_executor = Executor()
    INFO("NDK CSI Upgrade")
    self._generic_pre_executor(
      jobs=jobs,
      prod_meta=prod_meta,
      suite_jobs=suite_jobs,
      suite=suite,
      matrix_generator=self.matrix_generator.ndk_csi_upgrade,
      headers=metadata.NDK_CSI_UPGRADE_HEADERS,
      db_name="ndk_apeiron_db",
      executor=_deployment_executor.clone_and_execute_job_and_send_mail,
      suite_dict=None,
      pool_executor=_deployment_executor.clone_and_execute_job_and_send_mail,
    )

  def _ndk_pc_upgrade(self, jobs, prod_meta, suite="ndk_pc_upgrade", #pylint: disable=dangerous-default-value
                      suite_jobs=metadata.NDK_SANITY_QUAL_JOBS):
    """
    Method to generate and execute possible Objects upgrade paths.

    Args:
      jobs(json): Jobs Master JSON containing the input.
      prod_meta(dict): Product Meta.
      suite(str): Suite Name.
      suite_jobs(str): NGD test suites.
    """
    _deployment_executor = Executor()
    INFO("NDK PC Upgrade")
    self._generic_pre_executor(
      jobs=jobs,
      prod_meta=prod_meta,
      suite_jobs=suite_jobs,
      suite=suite,
      matrix_generator=self.matrix_generator.ndk_pc_upgrade,
      headers=metadata.NDK_PC_UPGRADE_HEADERS,
      db_name="ndk_apeiron_db",
      executor=_deployment_executor.clone_and_execute_job_and_send_mail,
      suite_dict=None,
      pool_executor=_deployment_executor.clone_and_execute_job_and_send_mail,
    )

  def _generic_pre_executor(self, jobs, prod_meta, suite_jobs, suite,
                            matrix_generator, headers, db_name, executor,
                            time_interval=0, **kwargs):
    """
    Method to generate and execute possible AHV upgrade paths.

    Args:
      jobs(json): Jobs Master JSON containing the input.
      prod_meta(dict): Product Meta.
      suite_jobs(dict): Suite Jobs.
      suite(str): Suite Name.
      matrix_generator(str): Matrix Generator Module,
      headers(list): Headers.
      db_name(str): DB Name.
      executor(str): Executor Module.
      time_interval(int): Time Interval
    """
    database.matrices.update({
      suite: {}
    })
    INFO("Headers: "+str(headers))
    INFO(str(suite)+": Check if cluster is provided,"
         " Add to resource_manager if present")

    # INFO("Deployment Pat: "+str(jobs))
    _generic_jobs = self.args_manipulator.jobs_manipulator(
      jobs=jobs,
      jobs_upgrade=suite_jobs
    )
    if "cluster_name" in _generic_jobs.keys():
      INFO("Adding the clusters to the resource manager.")
      if _generic_jobs.get("cluster_node_map"):
        for node_size in _generic_jobs.get("cluster_node_map").keys():
          self.deployment_manager.add_cluster_to_resource_manager(
            cluster_list=_generic_jobs["cluster_node_map"][node_size],
            nodes=int(node_size),
            suite=suite
          )
      else:
        self.deployment_manager.add_cluster_to_resource_manager(
          cluster_list=_generic_jobs["cluster_name"],
          suite=suite
        )

    INFO(str(suite)+" jobs: "+str(_generic_jobs))

    STEP("Generating "+str(suite)+" Matrix")
    _generated_matrix_dict = matrix_generator(
      prod_meta=prod_meta,
      jobs=jobs,
      suite=suite,
      suite_dict=kwargs.get("suite_dict")
    )
    database.matrices[str(suite)] = copy.deepcopy(
      _generated_matrix_dict
    )
    _terminal_print_list = self.args_manipulator.json_to_list_converter(
      upgrade_dict=database.matrices[str(suite)],
      headers=headers
    )
    self.args_manipulator.log_matrix_printer(
      headers=headers,
      print_list=_terminal_print_list
    )

    if _generic_jobs.get("email_ids"):
      for email in _generic_jobs["email_ids"]:
        if email not in metadata.EMAIL_SENDER_LIST:
          metadata.EMAIL_SENDER_LIST.append(email)
    INFO("Add the matrix to database.")
    for out_key in database.matrices[str(suite)]:
      for in_key in database.matrices[str(suite)][str(out_key)]:
        self.db_conn.ingest_data_with_id(
          db_name=db_name,
          data=database.matrices[str(suite)][str(out_key)][str(in_key)],
          data_id=(database.matrices[str(suite)][str(out_key)][str(in_key)]
                   ["row_id"]),
          op_type="create"
        )

    _workers = jobs.get("workers", 3)
    _task_manager = TaskManager(
      quotas={
        str(suite)+"_slave": {
          "num_workers": _workers
        }
      },
      worker_poolsize=_workers,
      timeout=960000000000000000
    )

    for out_key in _generated_matrix_dict:
      in_key_list = _generated_matrix_dict[out_key].keys()
      in_key_int_list = []
      for key in in_key_list:
        in_key_int_list.append(int(key))
      in_key_int_list.sort()
      in_key_int_list.reverse()
      INFO(str(suite)+": Number of Upgrade Paths: "+str(in_key_int_list))

      while True:
        with self._global_lock:
          in_key = in_key_int_list.pop()
          INFO(str(suite)+": Adding Keys to Executor: ("+str(out_key)+
               ", "+str(in_key)+")")
          if (not (database.matrices[str(suite)][str(out_key)]
                   [str(in_key)]).get("Status") or
              (database.matrices[str(suite)][str(out_key)][str(in_key)]
               ["Status"]) != "completed"):
            if (not database.matrices[str(suite)][str(out_key)]
                [str(in_key)].get("enable_direct_pool_execution")):
              _task_manager.add(
                executor,
                headers=copy.deepcopy(headers),
                jobs=copy.deepcopy(_generic_jobs),
                action=copy.deepcopy(suite),
                out_key=copy.deepcopy(str(out_key)),
                in_key=copy.deepcopy(str(in_key)),
                quota_type=str(suite)+"_slave"
              )
            else:
              _task_manager.add(
                kwargs.get("pool_executor"),
                headers=copy.deepcopy(headers),
                jobs=copy.deepcopy(_generic_jobs),
                action=copy.deepcopy(suite),
                out_key=copy.deepcopy(str(out_key)),
                in_key=copy.deepcopy(str(in_key)),
                quota_type=str(suite)+"_slave"
              )
            time.sleep(30)
            time.sleep(time_interval)

          if not in_key_int_list:
            _task_manager.complete_run(
              wait_for_inflight_tasks_to_schedule=True,
              wait_time=1, timeout=7200000000000000
            )
            break

  def _deployment_path(self, jobs, suite=None):
    """
    Method to generate and execute possible AHV upgrade paths.

    Args:
      jobs(json): Jobs Master JSON containing the input.
      suite(str): Suite Name.
    """
    _deployment_path_slave = 1

    if not suite:
      suite = "deployment_path"
    database.matrices.update({
      suite: {}
    })

    INFO("Deployment Path: Check if cluster is provided,"
         " Add to resource_manager if present")
    if "cluster_name" in jobs["deployment"]["deployment_path"].keys():
      INFO("Adding the clusters to the resource manager.")
      self.deployment_manager.add_cluster_to_resource_manager(
        cluster_list=jobs["deployment"]["deployment_path"]["cluster_name"],
        suite=suite
      )
    # INFO("Deployment Pat: "+str(jobs))
    _deployment_path_jobs = self.args_manipulator.jobs_manipulator(
      jobs=jobs,
      jobs_upgrade=jobs["deployment"]["deployment_path"]
    )

    INFO("Deployment Jobs: "+str(_deployment_path_jobs))
    for i in range(len(_deployment_path_jobs["jobs"])):
      _job_to_execute = _deployment_path_jobs["jobs"][i]

      if "workers" in _job_to_execute.keys():
        _deployment_path_slave = _job_to_execute["workers"]

      self.dep_path_task_manager = TaskManager(
        quotas={
          str(suite)+"_slave": {
            "num_workers": _deployment_path_slave
          }
        },
        worker_poolsize=_deployment_path_slave,
        timeout=96000000
      )

      STEP("Generating Deployment Path Matrix")
      self.deployment_path_dict = self.matrix_generator.deployment_path(
        jobs=_job_to_execute,
        suite=suite
      )
      database.matrices[str(suite)] = copy.deepcopy(
        self.deployment_path_dict
      )
      _dep_path_print_list = self.args_manipulator.json_to_list_converter(
        upgrade_dict=database.matrices[str(suite)],
        headers=metadata.DEPLOYMENT_PATH_HEADERS
      )
      self.args_manipulator.log_matrix_printer(
        headers=metadata.DEPLOYMENT_PATH_HEADERS,
        print_list=_dep_path_print_list
      )
      INFO("Add the matrix to database.")
      for out_key in database.matrices[str(suite)]:
        for in_key in database.matrices[str(suite)][str(out_key)]:
          self.db_conn.ingest_data_with_id(
            db_name="one_click_db",
            data=database.matrices[str(suite)][str(out_key)][str(in_key)],
            data_id=(database.matrices[str(suite)][str(out_key)][str(in_key)]
                     ["row_id"]),
            op_type="create"
          )

      for out_key in self.deployment_path_dict:
        in_key_list = self.deployment_path_dict[out_key].keys()
        in_key_int_list = []
        for key in in_key_list:
          in_key_int_list.append(int(key))
        in_key_int_list.sort()
        in_key_int_list.reverse()
        INFO("Deployment Path: Number of Upgrade Paths: "+str(in_key_int_list))

        while True:
          with self._deployment_path_lock:
            in_key = in_key_int_list.pop()
            INFO("Deployment Path: Adding Keys to Executor: ("+str(out_key)+
                 ", "+str(in_key)+")")
        # for in_key in self.ahv_upgrade_dict[out_key].keys():
            _deployment_executor = Executor()
            self.dep_path_task_manager.add(
              _deployment_executor.clone_and_execute_job_and_send_mail,
              headers=metadata.DEPLOYMENT_PATH_HEADERS,
              jobs=_job_to_execute,
              action=suite,
              out_key=str(out_key),
              in_key=str(in_key),
              quota_type=str(suite)+"_slave"
            )
            time.sleep(10)

            if not in_key_int_list:
              self.dep_path_task_manager.complete_run(
                wait_for_inflight_tasks_to_schedule=True,
                wait_time=1, timeout=7200000
              )
              break

  def _ngd_upgrade(self, jobs, ahv_product_meta, suite="ngd_upgrade"): #pylint: disable=too-many-locals
    """
    Method to generate and execute possible AHV upgrade paths.

    Args:
      jobs(json): Jobs Master JSON containing the input.
      ahv_product_meta(json): AHV Product Meta file.
      suite(str): Suite name.(OPTIONAL)
    """
    _ngd_ahv_upgrade_slave = 1
    INFO("NGD AHV Upgrade: Check if cluster is provided,"
         " Add to resource_manager if present")
    if "cluster_name" in jobs["ngd"]["ahv_upgrade"].keys():
      INFO("Adding the clusters to the resource manager.")
      self.deployment_manager.add_cluster_to_resource_manager(
        cluster_list=jobs["ngd"]["ahv_upgrade"]["cluster_name"],
        suite=suite
      )
    INFO(jobs["ngd"]["ahv_upgrade"])
    _ngd_ahv_upgrade_jobs = self.args_manipulator.jobs_manipulator(
      jobs=jobs,
      jobs_upgrade=jobs["ngd"]["ahv_upgrade"]
    )

    INFO("AHV Upgrade Jobs: "+str(_ngd_ahv_upgrade_jobs))
    for i in range(len(_ngd_ahv_upgrade_jobs["jobs"])):
      _job_to_execute = _ngd_ahv_upgrade_jobs["jobs"][i]

      if "workers" in _job_to_execute.keys():
        _ngd_ahv_upgrade_slave = _job_to_execute["workers"]

      _ngd_task_manager = TaskManager(
        quotas={
          "ngd_ahv_upgrade_slave": {
            "num_workers": _ngd_ahv_upgrade_slave
          }
        },
        worker_poolsize=_ngd_ahv_upgrade_slave,
        timeout=96000000
      )

      STEP("Generating NGD AHV Upgrade Matrix")
      ngd_ahv_upgrade_dict = self.matrix_generator.ngd_upgrade(
        ahv_product_meta=ahv_product_meta,
        jobs=_job_to_execute
      )
      database.matrices["ngd_ahv_upgrade"] = copy.deepcopy(
        ngd_ahv_upgrade_dict
      )
      _ngd_upgrade_print_list = self.args_manipulator.json_to_list_converter(
        upgrade_dict=database.matrices["ngd_ahv_upgrade"],
        headers=metadata.NGD_AHV_UPGRADE_HEADERS
      )
      self.args_manipulator.log_matrix_printer(
        headers=metadata.NGD_AHV_UPGRADE_HEADERS,
        print_list=_ngd_upgrade_print_list
      )
      # INFO(json.dumps(database.matrices["ahv_upgrade"]))

      for out_key in ngd_ahv_upgrade_dict:
        in_key_list = ngd_ahv_upgrade_dict[out_key].keys()
        in_key_int_list = []
        for key in in_key_list:
          in_key_int_list.append(int(key))
        in_key_int_list.sort()
        in_key_int_list.reverse()
        INFO("AHV Upgrade: Number of Upgrade Paths: "+str(in_key_int_list))

        while True:
          with self._ahv_upgrade_lock:
            in_key = in_key_int_list.pop()
            INFO("AHV Upgrade: Adding Keys to Executor: ("+str(out_key)+
                 ", "+str(in_key)+")")
        # for in_key in self.ahv_upgrade_dict[out_key].keys():
            _ngd_ahv_upgrade_executor = Executor()
            _ngd_task_manager.add(
              _ngd_ahv_upgrade_executor.clone_and_execute_job_and_send_mail,
              headers=metadata.NGD_AHV_UPGRADE_HEADERS,
              jobs=_job_to_execute,
              action="ngd_ahv_upgrade",
              out_key=str(out_key),
              in_key=str(in_key),
              quota_type="ngd_ahv_upgrade_slave"
            )
            time.sleep(10)

            if not in_key_int_list:
              _ngd_task_manager.complete_run(
                wait_for_inflight_tasks_to_schedule=True,
                wait_time=1,
                timeout=7200000)
              break

  def _gos_qual(self, jobs, suite=None): #pylint: disable=too-many-locals
    """
    Guest OS qualification main thread
    Args:
      jobs(str): master jobs json file contents
      suite(str): Suite Name
    """
    if not suite:
      suite = "guest_os_qual"
    database.matrices.update({
      suite: {}
    })

    INFO("Guest OS Qualification: Check if cluster is provided,"
         " Add to resource_manager if present")
    if jobs["guest_os_qual"].get("cluster_name"):
      INFO("Adding the clusters to the resource manager.")
      self.deployment_manager.add_cluster_to_resource_manager(
        cluster_list=jobs["guest_os_qual"].get("cluster_name"),
        suite=suite
      )
    gos_qual_jobs = self.args_manipulator.jobs_manipulator(
      jobs=jobs,
      jobs_upgrade=jobs.get("guest_os_qual")
    )
    INFO("Guest OS Qualification Jobs: " + str(gos_qual_jobs))
    for _, job in enumerate(gos_qual_jobs.get("jobs")):
      _job_to_execute = job
      INFO(json.dumps(_job_to_execute))
      _gos_qual_slave = _job_to_execute.get("workers", 3)
      # _batch_size = get_batch_size.get_batch_size(
      #   clusters=database.resource_manager.keys()
      # )
      _batch_size = _job_to_execute.get(
        "batch_size", metadata.GOS_BATCH_SIZE_MAPPING.get(
          suite, 10
        )
      )
      INFO("Batch Size: "+str(_batch_size))
      # _batch_size = _job_to_execute.get("batch_size", 3)
      _gos_qual_task_manager = TaskManager(
        quotas={
          str(suite)+"_slave": {
            "num_workers": _gos_qual_slave
          }
        },
        worker_poolsize=_gos_qual_slave,
        timeout=96000000
      )

      STEP("Generating Guest OS qualification Matrix")
      # Using the run_id given by one-click framework
      self.gos_qual_dict = self.matrix_generator.guest_os_qual(
        _job_to_execute,
        run_id=str(database.matrices["uuid"]),
        action=suite)

      database.matrices[str(suite)] = copy.deepcopy(self.gos_qual_dict)

      gos_qual_print_list = self.args_manipulator.json_to_list_converter(
        upgrade_dict=database.matrices[str(suite)],
        headers=metadata.GOS_QUAL_HEADERS
      )

      # customized pretty_print
      self.args_manipulator.log_matrix_printer(
        headers=metadata.GOS_QUAL_HEADERS,
        print_list=gos_qual_print_list
      )

      # INFO(json.dumps(database.matrices["ahv_upgrade"]))
      time.sleep(2)
      # ENTER THE DATABASE WITH THE GENERATED MATRIX
      for out_key in database.matrices[str(suite)]:
        for in_key in database.matrices[str(suite)][str(out_key)].keys():
          self.db_conn.ingest_data_with_id(
            db_name="one_click_db",
            data=database.matrices[str(suite)][str(out_key)][str(in_key)],
            data_id=(database.matrices[str(suite)][str(out_key)][str(in_key)]
                     ["row_id"]),
            op_type="create"
          )

      for out_key in self.gos_qual_dict:
        in_key_list = self.gos_qual_dict[out_key].keys()
        in_key_int_list = list(map(int, in_key_list))
        #
        # for key in in_key_list:
        #   in_key_int_list.append(int(key))
        in_key_int_list.sort()
        in_key_int_list.reverse()
        INFO(
          "Guest OS Qualification: Number of Guest OSes" +
          str(len(in_key_int_list)))
        while True:
          with self._gos_qual_lock:
            in_key = in_key_int_list.pop()
            temp_counter = copy.deepcopy(_batch_size)-1
            while temp_counter and in_key_int_list:
              in_key_int_list.pop()
              temp_counter -= 1
            INFO("Guest OS Qualification: Adding Keys to Executor: "
                 "(" + str(out_key) +
                 ", " + str(in_key) + ")")
            # self.gos_task_manager.add(
            #   self.executor.execute_gos_qual,
            #   headers=metadata.GOS_QUAL_HEADERS,
            #   jobs=_job_to_execute,
            #   action="guest_os_qual",
            #   out_key=str(out_key),
            #   in_key=str(in_key),
            #   quota_type="deployment_path_slave"
            # )
            _gos_qual_executor = Executor()
            _gos_qual_task_manager.add(
              _gos_qual_executor.clone_and_execute_job_and_send_mail,
              headers=metadata.GOS_QUAL_HEADERS,
              action=suite,
              jobs=_job_to_execute,
              out_key=str(out_key),
              in_key=str(in_key),
              batch_size=_batch_size-temp_counter,
              quota_type=str(suite)+"_slave"
            )
            time.sleep(10)

            if not in_key_int_list:
              _gos_qual_task_manager.complete_run(
                wait_for_inflight_tasks_to_schedule=True,
                wait_time=1, timeout=7200000
              )
              INFO("Not in-flight or pending qualification, exiting")
              break
