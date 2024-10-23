"""Copyright (c) 2021 Nutanix Inc. All rights reserved.

Author: vedant.dalal@nutanix.com

This module contains all the functions which helps in sending
an email to the test executor.
"""
import socket
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from framework.lib.nulog import ERROR, INFO
from libs.ahv.workflows.one_click \
  import metadata
from libs.ahv.workflows.one_click \
  import database
from libs.ahv.workflows.one_click.args_manipulator \
  import ArgsManipulator

SMTP_SERVER = "mailrelay.dyn.nutanix.com"
SMTP_PORT = 25
FROM_ADDRESS = "no-reply-ahv-qa@nutanix.com"

class Emailer():
  """
  Class containing methods to send email
  """
  def __init__(self):
    """
    Constructor Method
    """
    self.args_manipulator = ArgsManipulator()

  def send_mail(self, action, mail_type, out_key=None, in_key=None):
    """
    Method to send a Email for Reporting.

    Args:
      action(str): Suite to be executed
                   (e.g ahv_upgrade/ahv_aos_upgrade/deployment_path)
      mail_type(str): Mail Type to be sent.
      out_key(str): Key for the outer loop for DB.
      in_key(str): Key for the inner loop for DB.
    """
    # html_table = None
    # html_table = self._get_html_table_from_dict(
    #   data_list=upgrade_list,
    #   headers=headers
    # )
    return
    INFO("Action: "+str(action))
    INFO("mail_type: "+str(mail_type))
    INFO("out_key: "+str(out_key))
    INFO("in_key: "+str(in_key))
    _html_str = self._html_adder()
    _result = None
    if mail_type == "end":
      if database.matrices[action][out_key][in_key].get("Result"):
        _result = str(database.matrices[action][out_key][in_key]["Result"])
    if "upgrade" in action and "ahv" in action:
      src_ahv = str(database.matrices[action][out_key][in_key]
                    ["Source_AHV"])
      dst_ahv = str(database.matrices[action][out_key][in_key]
                    ["Destination_AHV"])
      subject = metadata.EMAIL_SUBJECTS["upgrade"][mail_type].format(
        src=src_ahv.split(".")[2]+"."+src_ahv.split(".")[3],
        dst=dst_ahv.split(".")[2]+"."+dst_ahv.split(".")[3],
        result=_result,
        action=action.replace("_", " ")
      )
    elif "csi" in action:
      subject = metadata.EMAIL_SUBJECTS["csi_deployment"][mail_type].format(
        ahv=str(database.matrices[action][out_key][in_key]
                ["Source_CSI"]),
        aos=str(database.matrices[action][out_key][in_key]
                ["Source_AOS"]),
        pc=str(database.matrices[action][out_key][in_key]
               ["Source_PC"]),
        result=_result,
        action=action.replace("_", " ")
      )
    elif "ndk" in action:
      subject = metadata.EMAIL_SUBJECTS["ndk_deployment"][mail_type].format(
        ndk=str(database.matrices[action][out_key][in_key]
                ["Source_NDK"]),
        csi=str(database.matrices[action][out_key][in_key]
                ["Source_CSI"]),
        aos=str(database.matrices[action][out_key][in_key]
                ["Source_AOS"]),
        pc=str(database.matrices[action][out_key][in_key]
               ["Source_PC"]),
        result=_result,
        action=action.replace("_", " ")
      )
    elif "objects" in action:
      subject = metadata.EMAIL_SUBJECTS["objects_deployment"][mail_type].format(
        objects=str(database.matrices[action][out_key][in_key]
                    ["Source_Objects"]),
        aos=str(database.matrices[action][out_key][in_key]
                ["Source_AOS"]),
        pc=str(database.matrices[action][out_key][in_key]
               ["Source_PC"]),
        result=_result,
        action=action.replace("_", " ")
      )
    elif "deployment_path" in action:
      src_ahv = str(database.matrices[action][out_key][in_key]
                    ["Source_AHV"])
      subject = metadata.EMAIL_SUBJECTS["deployment"][mail_type].format(
        ahv=src_ahv.split(".")[2]+"."+src_ahv.split(".")[3],
        aos=str(database.matrices[action][out_key][in_key]
                ["Source_AOS"]),
        found=str(database.matrices[action][out_key][in_key].get(
          "Foundation_Build", "default"
        )),
        result=_result,
        action=action.replace("_", " ")
      )
    elif "msp" in action:
      subject = metadata.EMAIL_SUBJECTS["upgrade"][mail_type].format(
        src=str(database.matrices[action][out_key][in_key]
                ["Source_MSP"]),
        dst=str(database.matrices[action][out_key][in_key]
                ["Destination_MSP"]),
        result=_result,
        action=action.replace("_", " ")
      )
    elif "ahv" in action:
      subject = metadata.EMAIL_SUBJECTS["deployment"][mail_type].format(
        ahv=str(database.matrices[action][out_key][in_key]
                ["Source_AHV"]),
        aos=str(database.matrices[action][out_key][in_key]
                ["Source_AOS"]),
        found=str(database.matrices[action][out_key][in_key].get(
          "Foundation_Build", "default"
        )),
        result=_result,
        action=action.replace("_", " ")
      )
    else:
      src_ahv = str(database.matrices[action][out_key][in_key]
                    ["ahv"])
      subject = metadata.EMAIL_SUBJECTS["guest_os_qual"][mail_type].format(
        ahv=src_ahv.split(".")[2]+"."+src_ahv.split(".")[3],
        aos=str(database.matrices[action][out_key][in_key]
                ["aos"]),
        result=_result,
        action=action.replace("_", " ")
      )
    # subject = "Testing"
    self.send_email(subject=subject, html=_html_str,
                    to_addresses=metadata.EMAIL_SENDER_LIST)

  def send_email(self, subject, html=None, text=None, to_addresses=None, #pylint: disable=too-many-locals,no-self-use
                 cc_addresses=None, bcc_addresses=None):
    """Helper to send email. This would send only multipart/alternative
    content-type message with text/html and text/plain content types nested in
    it. This would use "from" address as "no-reply-object-store-qa@nutanix.com"

    Args:
    subject(str): Subject
    html(str): (Optional) The html content for the email
    text(str): (Optional) The plain text content for the email
    to_addresses(list): (Optional) List of "To" email addresses.
                        Default: ['object-store-qa@nutanix.com']
    cc_addresses(list): (Optional) List of "Cc" email addresses.
    bcc_addresses(list): (Optional) List of "bcc" email addresses.
    """
    return
    if not to_addresses:
      to_addresses = ['vedant.dalal@nutanix.com']
    cc_addresses = cc_addresses or []
    bcc_addresses = bcc_addresses or []

    msg = MIMEMultipart("alternative")
    msg["To"] = ", ".join(to_addresses)
    msg["From"] = FROM_ADDRESS
    msg["Subject"] = subject
    if cc_addresses:
      msg["CC"] = ", ".join(cc_addresses)
    if bcc_addresses:
      msg["BCC"] = ", ".join(bcc_addresses)

    if html:
      msg.attach(MIMEText(html, "html"))
    if text:
      msg.attach(MIMEText(text, "plain"))
    server = None
    try:
      server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
      recipients = to_addresses + cc_addresses + bcc_addresses
      refused = server.sendmail(FROM_ADDRESS, recipients, msg.as_string())
      towards = set(recipients)
      refused = set(refused)
      INFO('EMAILER: Sent email to :%s' % list(towards - refused))
    except smtplib.SMTPException as ex:
      ERROR("EMAILER: Failed to send email. Error:\n%s" % ex)
    except socket.gaierror as gaierr:
      ERROR("EMAILER: Failed to send email. GaiError:\n%s" % gaierr)
    finally:
      if server:
        server.quit()

  def _get_html_table_from_dict(self, data_list, headers): #pylint: disable=no-self-use
    """
    Given a dictionary, it returns back the html necessary to represent
    the data as a table. The keys of the dictionary are used as column
    headings. The values of the dictionary can be a scalar value or it
    can be a list or tuple representing multiple rows. These values
    are used to fill 'td' in the html table.

    Args:
      data_list(list): List containing lists of the Data.
      headers(list): List containing the name of headers on top of Table.

    Returns:
      html(str): html string
    """
    return
    html = '<table><tr>'
    for header in headers:
      html += '<th>'+str(header)+'</th>'
    html += '</tr>'
    for combination in data_list:
      html += '<tr>'
      for key in combination:
        if str(key).find(metadata.TEST_REPORT_URL):
          html += '<td>'+str(key)+'</td>'
        else:
          html += '<td><a href="'+str(key)+'">'+str(key)+'</a></td>'
      html += '</tr>'
    html += '</table>'
    return html

  def _html_adder(self):
    """
    Method to add the generated HTML Table to the pre-built HTML

    Returns:
      html(str) = HTML string.
    """
    HEADER_MAPPING = { #pylint: disable=invalid-name
      "csi": {
        "general": metadata.CSI_DEPLOYMENT_HEADERS,
        "csi_upgrade": metadata.CSI_UPGRADE_HEADERS,
        "csi_pc_upgrade": metadata.CSI_PC_UPGRADE_HEADERS,
        "csi_aos_upgrade": metadata.CSI_AOS_UPGRADE_HEADERS
      },
      "objects": {
        "general": metadata.OBJECTS_DEPLOYMENT_HEADERS,
        "objects_deployment": metadata.OBJECTS_DEPLOYMENT_PATH_HEADERS,
        "objects_upgrade": metadata.OBJECTS_UPGRADE_HEADERS
      },
      "ndk": {
        "general": metadata.NDK_DEPLOYMENT_HEADERS
      },
      "ahv": {
        "ahv_upgrade": metadata.AHV_UPGRADE_HEADERS,
        "ahv_aos_upgrade": metadata.AHV_AOS_UPGRADE_HEADERS,
        "multi_level_ahv_upgrade": metadata.AHV_AOS_UPGRADE_HEADERS,
        "deployment_path": metadata.DEPLOYMENT_PATH_HEADERS,
        "general": metadata.AHV_FEAT_HEADERS,
        "level_2_ahv_upgrade": metadata.AHV_AOS_UPGRADE_HEADERS,
        "level_3_ahv_upgrade": metadata.AHV_AOS_UPGRADE_HEADERS,
        "ngd_ahv_upgrade": metadata.AHV_UPGRADE_HEADERS,
        "ngd_ahv_aos_upgrade": metadata.AHV_UPGRADE_HEADERS,
      },
      "ahv_upgrade": {
        "general": metadata.AHV_UPGRADE_HEADERS
      },
      "ahv_aos_upgrade": {
        "general": metadata.AHV_AOS_UPGRADE_HEADERS
      },
      "multi_level_ahv_upgrade": {
        "general": metadata.AHV_AOS_UPGRADE_HEADERS
      },
      "deployment_path": {
        "general": metadata.DEPLOYMENT_PATH_HEADERS
      },
      "msp_pc_upgrade": {
        "general": metadata.MSP_PC_UPGRADE_HEADERS
      },
      "else": {
        "general": metadata.GOS_QUAL_HEADERS
      }
    }
    html_before_body = ('<!DOCTYPE html><html><head><style type="text/css">'
                        'table, th, td {text-align: center;border: 1px'
                        ' solid black;border-collapse: collapse;}th,td{padding'
                        '-left: 4px;padding-right: 4px;}</style></head><body>')
    html_after_body = '</body></html>'
    _html_for_suite_header = '<br><hr><b><center>{suite}<center></b><hr><br>'

    suite_list = list(database.matrices.keys())
    INFO(" Before Suite List for Report Generation: "+ str(suite_list))
    for element in metadata.REPORT_GENERATION_KEYS_TO_DELETE:
      if element in suite_list:
        suite_list.remove(element)
    INFO("Suite List for Report Generation: "+ str(suite_list))

    html = html_before_body
    for suite in suite_list:
      INFO("Suite Name: "+suite)
      header = None
      for hkey in HEADER_MAPPING:
        INFO("Key: "+str(hkey))
        if hkey in suite:
          INFO("match key: "+str(hkey)+". suite: "+suite)
          if HEADER_MAPPING[hkey].get(suite):
            header = HEADER_MAPPING[hkey][suite]
          else:
            header = HEADER_MAPPING[hkey]["general"]
          break

      if not header:
        header = HEADER_MAPPING["else"]["general"]
      INFO(header)
      _header_html = _html_for_suite_header.format(
        suite=suite.replace("_", " ").upper()
      )

      table_list = self.args_manipulator.json_to_list_converter(
        upgrade_dict=database.matrices[suite],
        headers=header
      )
      if len(table_list) > 0:
        html += _header_html
      for each_table in table_list:
        html += self._get_html_table_from_dict(
          data_list=each_table,
          headers=header
        )

    html += html_after_body
    return html

    # _html_for_ahv_header = '<br><hr><b><center>AHV Upgrade<center>'
    # '</b><hr><br>'
    # _html_for_ahv_aos_header = '<br><hr><b><center>AHV-AOS Upgrade'
    # '<center></b>'\
    #                            '<hr><br>'
    # _html_for_deployment_header = '<br><hr><b><center>Deployment Path'
    # '<center>'\
    #                               '</b><hr><br>'
    # _html_for_ngd_header = '<br><hr><b><center>NGD Upgrade<center>'\
    #                               '</b><hr><br>'
    # _html_for_gos_qual_header = '<br><hr><b><center>Guest OS ' \
    #                             'Qualification<center>'\
    #                               '</b><hr><br>'
    # html = html_before_body
    # table_list = self.args_manipulator.json_to_list_converter(
    #   upgrade_dict=database.matrices["ahv_upgrade"],
    #   headers=metadata.AHV_UPGRADE_HEADERS
    # )
    # if len(table_list) > 0:
    #   html += _html_for_ahv_header
    # for each_table in table_list:
    #   html += self._get_html_table_from_dict(
    #     data_list=each_table,
    #     headers=metadata.AHV_UPGRADE_HEADERS
    #   )

    # table_list = self.args_manipulator.json_to_list_converter(
    #   database.matrices["ahv_aos_upgrade"],
    #   headers=metadata.AHV_AOS_UPGRADE_HEADERS
    # )
    # if len(table_list) > 0:
    #   html += _html_for_ahv_aos_header
    # for each_table in table_list:
    #   html += self._get_html_table_from_dict(
    #     data_list=each_table,
    #     headers=metadata.AHV_AOS_UPGRADE_HEADERS
    #   )

    # table_list = self.args_manipulator.json_to_list_converter(
    #   database.matrices["deployment_path"],
    #   headers=metadata.DEPLOYMENT_PATH_HEADERS
    # )
    # if len(table_list) > 0:
    #   html += _html_for_deployment_header
    # for each_table in table_list:
    #   html += self._get_html_table_from_dict(
    #     data_list=each_table,
    #     headers=metadata.DEPLOYMENT_PATH_HEADERS
    #   )

    # table_list = self.args_manipulator.json_to_list_converter(
    #   database.matrices["ngd_ahv_upgrade"],
    #   headers=metadata.NGD_AHV_UPGRADE_HEADERS
    # )
    # if len(table_list) > 0:
    #   html += _html_for_ngd_header
    # for each_table in table_list:
    #   html += self._get_html_table_from_dict(
    #     data_list=each_table,
    #     headers=metadata.NGD_AHV_UPGRADE_HEADERS
    #   )

    # table_list = self.args_manipulator.json_to_list_converter(
    #   database.matrices["guest_os_qual"],
    #   headers=metadata.GOS_QUAL_HEADERS
    # )
    # if len(table_list) > 0:
    #   html += _html_for_gos_qual_header
    # for each_table in table_list:
    #   html += self._get_html_table_from_dict(
    #     data_list=each_table,
    #     headers=metadata.GOS_QUAL_HEADERS
    #   )
    # html += html_after_body
    # # INFO(html)
    # return html
