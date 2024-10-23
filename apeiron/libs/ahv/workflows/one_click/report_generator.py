"""
Copyright (c) 2021 Nutanix Inc. All rights reserved.

Author: vedant.dalal@nutanix.com

Report Generator Module.
"""
import copy

from framework.lib.nulog import INFO, STEP

from libs.ahv.workflows.one_click import metadata
from libs.ahv.workflows.one_click import database as db
from libs.ahv.workflows.one_click.emailer import Emailer

class ReportGenerator():
  """
  A class containing methods to generate Report.
  """

  def __init__(self):
    """
    Constuctor Method
    """
    self.emailer = Emailer()
    self.initial_html_str = '<html><head><style>.tablestyle {border: 2px'\
                        ' solid;font-family: Arial, sans-serif;}.'\
                        'tablestyle td {border: 1px solid;}.tablestyle'\
                        ' td h4 {margin-bottom: 0;}.colcenter {text'\
                        '-align: center;} </style></head><body>'\

    self.html_table_str = '<table cellpadding="10" id="maintab" class="'\
                     'tablestyle"><tr><td rowspan="1" class="'\
                     'colcenter"><h3>Execution Details</h3></td><td class'\
                     '="colcenter"><h3> Suite Name </h3></td><td '\
                     'class="colcenter"><h3> Execution Percent </h3>'\
                     '</td><td class="colcenter"><h3> Success Percent'\
                     ' </h3></td><td class="colcenter"> <h3> Failure '\
                     'Percent </h3></td><td class="colcenter"><h3> Failed '\
                     'Jobs URL </h3></td></tr><tr><td rowspan="{suite_num}"'\
                     ' class="colcenter"><h2>{product}</h2>{platform}<h2>'\
                     '{main_version}</h2>'\
                     '{versions}<p>{reason}</p></td></tr>'

    self.html_suite_str = '<tr><td class="colcenter"><h4 class="colcenter">'\
                          '{suite}</h4></td><td class="colcenter">{exec_pct}'\
                          '</td><td class="colcenter">{success_pct}</td>'\
                          '<td class="colcenter">{fail_pct}'\
                          '</td><td class="colcenter"><a href="{fail_url}">'\
                          'view ></a></td></tr>'

    self.html_table_end = '</table><br><br>'

    self.final_html_str = '</body></html>'

  def generate_and_send_report(self, product, main_version): #pylint: disable=too-many-locals,too-many-statements,too-many-branches
    """
    A method to generate the report and send the email

    Args:
      product(str): Product Name.
      main_version(str): Main Product Version.
    """
    STEP("Generating the Comprehensive Execution Report.")
    _html_str = self.initial_html_str
    html_dict = {}
    platform_list = [None]
    if product == "ahv":
      platform_list = copy.deepcopy(metadata.PLATFORM_LIST)
    for each_platform in platform_list:
      INFO("Platform: "+str(each_platform))
      plat_total = 0
      plat_succeeded = 0
      plat_executed = 0
      plat_failed = 0
      plat_failed_task_id = ""
      table_mid_html = ""
      suite_count = 1
      reason = ""
      html_dict.update(
        {
          each_platform: {}
        }
      )
      summary_dict = {}
      suite_list = list(db.matrices.keys())
      INFO(" Before Suite List for Report Generation: "+ str(suite_list))
      for element in metadata.REPORT_GENERATION_KEYS_TO_DELETE:
        if element in suite_list:
          if element in metadata.VERSION_LIST:
            summary_dict.update({
              element: db.matrices[element]
            })
          suite_list.remove(element)
      INFO("Suite List for Report Generation: "+ str(suite_list))
      for suite in suite_list:
        html_dict[each_platform].update({
          suite: {}
        })

      for suite in html_dict[each_platform].keys():
        suite_count += 1
        result = self.get_execution_data(
          action=suite,
          platform=each_platform
        )

        INFO(suite.replace("_", " ")+" result: "+str(result))

        if result[0] > 0:
          exec_pct = str(int(100.0 * result[1]/result[0]))+"%"+(
            " ("+str(result[1])+"/"+str(result[0])+")"
          )
          success_pct = str(int(100.0 * result[2]/result[0]))+"%"+(
            " ("+str(result[2])+"/"+str(result[0])+")"
          )
          fail_pct = str(int(100.0 * result[3]/result[0]))+"%"+(
            " ("+str(result[3])+"/"+str(result[0])+")"
          )
        else:
          exec_pct = success_pct = fail_pct = "Failed"

        if result[4]:
          failed_url = metadata.TEST_REPORT_URL+str(result[4])
        else:
          failed_url = ""

        table_mid_html += self.html_suite_str.format(
          suite=suite.replace("_", " ").upper(),
          exec_pct=exec_pct,
          success_pct=success_pct,
          fail_pct=fail_pct,
          fail_url=failed_url
        )

        plat_total += result[0]
        plat_succeeded += result[2]
        plat_executed += result[1]
        plat_failed += result[3]
        plat_failed_task_id += result[4]

      if plat_total > 0:
        total_exec_pct = str(int(100.0 * plat_executed/plat_total))+"%"+(
          " ("+str(plat_executed)+"/"+str(plat_total)+")"
        )
        total_success_pct = str(int(100.0 * plat_succeeded/plat_total))+"%"+(
          " ("+str(plat_succeeded)+"/"+str(plat_total)+")"
        )
        total_fail_pct = str(int(100.0 * plat_failed/plat_total))+"%"+(
          " ("+str(plat_failed)+"/"+str(plat_total)+")"
        )
      else:
        reason = "Not executed (Hardware not available)"
        total_exec_pct = total_success_pct = total_fail_pct = "Failed"

      if plat_failed_task_id:
        total_failed_url = metadata.TEST_REPORT_URL+str(plat_failed_task_id)
      else:
        total_failed_url = ""

      platform_to_print = ""
      if each_platform is not None:
        platform_to_print = "<h2>{platform}</h2>".format(
          platform=each_platform
        )
      dependencies_str = ""
      for version_key in summary_dict:
        if version_key != main_version:
          dependencies_str += "<h3>{version}</h3>".format(
            version=db.matrices[version_key]
          )

      table_start_html = self.html_table_str.format(
        suite_num=suite_count+1,
        platform=platform_to_print,
        product=product.upper(),
        main_version=db.matrices[main_version],
        versions=dependencies_str,
        reason=reason
      )

      table_mid_html += self.html_suite_str.format(
        suite="TOTAL",
        exec_pct=total_exec_pct,
        success_pct=total_success_pct,
        fail_pct=total_fail_pct,
        fail_url=total_failed_url
      )

      _html_str += table_start_html + table_mid_html + self.html_table_end
    STEP("Comprehensive Report Generated, Sending Email.")
    _html_str += self.final_html_str
    subject = ("Apeiron Execution Report: [Product - "+str(product).upper() +
               "] [version - " + str(db.matrices[main_version])+"]")
    self.emailer.send_email(subject=subject, html=_html_str,
                            to_addresses=metadata.EMAIL_SENDER_LIST)

  def get_execution_data(self, action, platform=None): #pylint: disable=no-self-use
    """
    A method to fetch the execution data.

    Args:
      action(str): Action
      platform(str): Platform Name

    Returns:
      result(tup): Tuple containing ahv_total, ahv_executed, ahv_succeeded,
                   ahv_failed
    """
    ahv_total = 0
    ahv_executed = 0
    ahv_succeeded = 0
    ahv_failed = 0
    failed_task_id_list = []
    INFO("Get Exec data: Action: "+action+". Plat: "+str(platform))
    for out_key in db.matrices[action].keys():#pylint: disable=too-many-nested-blocks
      if platform is None or platform in (db.matrices[action][out_key]
                                          ["0"]["Platform"]):
        for in_key in db.matrices[action][out_key].keys():
          if db.matrices[action][out_key][in_key].get("test_result_count"):
            ahv_total += (db.matrices[action][out_key][in_key]
                          ["test_result_count"]["Total"])
            if db.matrices[action][out_key][in_key]["Status"] == "completed":
              ahv_executed += (db.matrices[action][out_key][in_key]
                               ["test_result_count"]["Total"])
              ahv_succeeded += (db.matrices[action][out_key][in_key]
                                ["test_result_count"]["Succeeded"])
              ahv_failed += (db.matrices[action][out_key][in_key]
                             ["test_result_count"]["Failed"])
              if "Failed" in db.matrices[action][out_key][in_key]["Result"]:
                failed_task_id_list.append(
                  db.matrices[action][out_key][in_key]["Jita_URL"].split("=")[1]
                )

    result = (ahv_total, ahv_executed, ahv_succeeded, ahv_failed,
              ",".join(failed_task_id_list))
    # INFO("Fetched Execution Data: "+str(result))
    return result
