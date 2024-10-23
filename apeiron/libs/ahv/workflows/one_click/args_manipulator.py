"""Copyright (c) 2021 Nutanix Inc. All rights reserved.

Author: vedant.dalal@nutanix.com
"""
#pylint: disable=broad-except, no-else-return
#pylint: disable=unnecessary-comprehension
import os
import json
import tabulate
import re

from bs4 import BeautifulSoup
from urllib.request import urlopen

from looseversion import LooseVersion
#pylint: disable=no-self-use,too-many-locals

from framework.interfaces.http.http import HTTP
from framework.lib.nulog import INFO, DEBUG, ERROR

from libs.ahv.workflows.one_click import branch_mapping, metadata
from libs.ahv.workflows.one_click.jita_v2_client import JitaClient
from libs.ahv.workflows.one_click.objects_branch import ObjectsUtil
from libs.ahv.workflows.one_click.jarvis_client import JarvisClient
from libs.workflows.generic.vm.vm_checks import (is_ahv_greater_than_equal_to,
                                                 is_aos_greater_than_equal_to)

class BuildVersion:
  """
  This class is used to compare different styles of versioning available
  for AHV and AOS.
  """
  def __init__(self, version_str):
    """
    Constructor method.

    Args:
    version_str (str): Build version string
    """
    self.version_str = version_str

  def __gt__(self, other):
    """
    Overload > operator to compare different versioning style of AOS and AHV.

    Args:
      other(BuildVersion): Object to be checked.

    Returns:
      str: largest version provided , None otherwise.

    """
    first_ver_type = self.get_build_type(self.version_str)
    second_ver_type = self.get_build_type(other.version_str)

    # If style of version str matches then directly compare
    # them using LooseVersion
    if first_ver_type == second_ver_type:
      try:
        return (self.version_str
                if LooseVersion(self.version_str) >
                LooseVersion(other.version_str)
                else other.version_str)
      except TypeError:
        # Looseversion can't compare str and int, for ex 6.9 and master
        if "ahv" in first_ver_type:
          return (self.version_str
                  if is_ahv_greater_than_equal_to(self.version_str,
                                                  other.version_str)
                  else other.version_str)
        elif "aos" in first_ver_type:
          return (self.version_str
                  if is_aos_greater_than_equal_to(self.version_str,
                                                  other.version_str)
                  else other.version_str)

    # If first version str is in new format then return it
    if first_ver_type == 'new_ahv':
      return self.version_str
    if second_ver_type == 'new_ahv':
      return other.version_str
    return None

  @staticmethod
  def get_build_type(version_str):
    """
    A method to get product type according to the versioning format.

    Args:
    version_str(str): Product version

    Returns:
    String containing the build type like aos, new_ahv, old_ahv

    Raises:
    NotImplementedError: Exception if versioning style is not matching.
    """
    # Update this build regex dictionary in case of a new product
    # or a change in version format.
    #
    # Assumptions made while building the regex:
    #
    # Old-AHV  - The start of the version is a date in the `yyyymmdd` format.
    #          - So length is equal to  8 characters.
    # New-AHV  - The minor version must contain a hyphen `-` at the end.
    # AOS      - The start of the version is not a date. So length is less
    #            than 8 characters and can contain multiple periods `.`.
    #            OR AOS can be master

    build_regex = {
      'old_ahv': r'^\d{8}\.\d+$',
      'new_ahv': r'^\d+(\.\d+)+-\d+$',
      'aos': r'^((?!\d{8}).+(\.\d+)+)|master',
    }

    for product, regex in build_regex.items():
      if re.match(regex, version_str):
        return product
    raise NotImplementedError('Product versioning style is not supported')

class ArgsManipulator():
  """
  This class contains all the common helper methods that are used for
  parsing the JSON files, namely the Jobs JSON and the Product Meta
  JSON(ahv.json).
  """
  def __init__(self):
    """
    Constructor method.

    """
    self.jarvis_client = JarvisClient(
      username="svc.ahv-qa", password="6TcU84qZiZHTvFu!#jDD"
    )
    self.jita_client = JitaClient(
      username="svc.ahv-qa", password="6TcU84qZiZHTvFu!#jDD"
    )

  @staticmethod
  def version_comparator(first_str, second_str):
    """
    A simple comparator method which compares two string containing
    AOS version

    Args:
      first_str(str): First AOS version string
      second_str(str): Second AOS version string

    Returns:
      String containing the version which is greater than the other.
    """
    if (first_str and second_str) is not None:
      return BuildVersion(first_str) > BuildVersion(second_str)
    if (first_str and second_str) is None:
      return (first_str
              if second_str is None
              else second_str)
    return None

  @staticmethod
  def pretty_print(headers, print_list):
    """
    A simple method to pretty print the matrix generated.

    Args:
      headers(list): List containing the headers of the matrix
      print_list(list): List(Matrix) to be printed
    """
    table = tabulate.tabulate(print_list, headers=headers, tablefmt="grid")
    INFO("Matrix: %s%s" % (os.linesep, table))

  @staticmethod
  def log_matrix_printer(headers, print_list):
    """
    A method to iteratively print the matrices.

    Args:
      headers(list): Headers for the matrix
      print_list(list): List(Matrix) to be printed
    """
    DEBUG(f"Headers: {headers}\nPrint list: {print_list}")
    for each_list in print_list:
      if "LCM Version" in headers:
        INFO("LCM Version: "+each_list[0][headers.index("LCM Version")])
      if "Foundation Build" in headers:
        INFO("Foundation Build: "+
             each_list[0][headers.index("Foundation Build")])
      # INFO("Platform: "+each_list[0][headers.index("Platform")])

      ArgsManipulator.pretty_print(headers=headers, print_list=each_list)

  def json_to_list_converter(self, upgrade_dict, headers): # pylint: disable=no-self-use
    """
    A method to convert upgrade json to list for printing/emailing purpose

    Args:
      upgrade_dict(dict): Upgrade Dictionary
      headers(list): Headers for the Matrix

    Returns:
      upgrade_list(list): Upgrade List
    """
    # INFO(json.dumps(upgrade_dict))
    upgrade_list = [None] * len(upgrade_dict.keys())

    for each in upgrade_dict.keys():
      upgrade_list[int(each)] = [None]*len(upgrade_dict[each].keys())
      for in_each in upgrade_dict[each].keys():
        upgrade_list[int(each)][int(in_each)] = [None]*len(headers)

    for each in upgrade_dict.keys():
      for in_each in upgrade_dict[each].keys():
        for i in range(len(headers)):  # pylint: disable=consider-using-enumerate
          temp = str(headers[i]).replace(" ", "_")
          upgrade_list[int(each)][int(in_each)][i] = ""
          if temp in upgrade_dict[str(each)][str(in_each)].keys():
            upgrade_list[int(each)][int(in_each)][i] = str(
              upgrade_dict[str(each)][str(in_each)][temp]
            )
          # else:
          #   INFO("Key not found: "+temp)
    return upgrade_list

  def fetch_and_update_dependencies(self, objects_prod_meta, objects_version):
    """
    A method to manipulate the args_override as per the user input

    Args:
      objects_prod_meta(dict): Objects Product Meta.
      objects_version(str): Objects Version.

    Returns:
      update_dict(dict): Dict to be updated in jobs.
    """
    update_dict = {}
    if objects_prod_meta.get(objects_version):
      aos_version = objects_prod_meta[objects_version]["nos"]
      pc_version = objects_prod_meta[objects_version]["pc"]
      msp_version = objects_prod_meta[objects_version]["msp_version"]
      nos_url = objects_prod_meta[objects_version].get("nos_url")
      pc_build_url = objects_prod_meta[objects_version].get("pc_build_url")

      update_dict.update({
        "aos_version": aos_version,
        "pc_version": pc_version,
        "msp_version": msp_version
      })

      if nos_url is not None:
        update_dict.update({
          "nos_url": nos_url
        })

      if pc_build_url is not None:
        update_dict.update({
          "pc_build_url": pc_build_url
        })

    return update_dict

  def manipulate_objects_args_override(self, jobs, product_meta, msp_version,
                                       objects_version, image_tag,
                                       product_version):
    """
    A method to manipulate the args_override as per the user input

    Args:
      jobs(dict): Jobs.
      product_meta(dict): Product Meta.
      msp_version(str): MSP Version.
      objects_version(str): Objects Version.
      image_tag(str): Image Tag.
      product_version(str): Product Version.

    Returns:
      args_override(dict): Args Override Dict for Testset.

    """
    args_override = {}
    objects_util = ObjectsUtil()

    objects_manager_rc = ""
    objects_manager_version = (objects_version if objects_version != "poseidon"
                               else "master")
    image_tag_oss_version = ("buckets-"+str(objects_version) if
                             objects_version != "poseidon" else "poseidon")
    image_tag = objects_util.get_objects_image_tag(
      product_branch=image_tag_oss_version,
      product_version=product_version
    )
    if product_version != "latest":
      objects_manager_rc = product_version
      args_override.update({
        "oss_deployments~0~image_tag": "",
        "oss_deployments~0~new_registry": ""
      })
    else:
      args_override.update({
        "oss_deployments~0~image_tag": str(image_tag),
        "oss_deployments~0~new_registry": "artifactory"
      })

    if jobs.get("msp_artifactory_url"):
      args_override.update({
        "msp_artifactory_url": jobs.get("msp_artifactory_url")
      })
    elif (product_meta.get(objects_version) and
          product_meta[objects_version].get("msp_artifactory_url")):
      INFO(str(product_meta[objects_version].get("msp_artifactory_url")))
      args_override.update({
        "msp_artifactory_url": (
          product_meta[objects_version].get("msp_artifactory_url")
        )
      })
    else:
      args_override.update({
        "msp_artifactory_url": ""
      })

    args_override.update({
      "msp_controller_version": msp_version,
      "objects_manager_version": objects_manager_version,
      "objects_manager_rc": objects_manager_rc,
      "replace_objects_manager": True,
      "replace_msp_controller": True
    })
    INFO(json.dumps(args_override))
    return args_override

  def fetch_latest_packaged_build(self, branch_name):
    """
    A method to convert upgrade json to list for printing/emailing purpose

    Args:
      branch_name(str): Branch Name.

    Returns:
      ahv_version(str): AHV version.
    """
    INFO("Fetching the latest packaged build from the Dashboard")
    ahv_builds = self.get_all_packaged_ahv_builds(branch_name=branch_name)
    return ahv_builds[0] if len(ahv_builds) > 0 else None

  def get_all_packaged_ahv_builds(self, branch_name, only_bundled=False):
    """
    Get all the packaged AHV builds
    Args:
      branch_name(str): AHV Branch name
      only_bundled(bool): Return only bundled builds
    Returns:
      ahv_builds(list): List of AHV Builds
    """
    ahv_builds = []
    URL = ("http://ahv-dashboard.eng.nutanix.com/?tab=rel_branches&subtab="+#pylint: disable=invalid-name
           str(branch_name))
    response = HTTP().get(URL)
    page_content = response.text

    # Parse the page content using BeautifulSoup
    soup = BeautifulSoup(page_content, 'html.parser')
    # Find all anchor tags
    anchor_tags = soup.find_all('a')

    # Bundled builds have GoldImages in URL
    href_list = ["GoldImages"]
    if not only_bundled:
      href_list.append("ahv-build")

    # Return the reachable build URLs
    for tag in anchor_tags:
      if any(href in tag.get('href', ' ') for href in href_list):
        try:
          response = HTTP().head(url=tag['href'], allow_redirects=True)
          ahv_builds.append(tag['href'].strip("/").split("/")[-1])
        except Exception as ex:
          # It is a common scenario, URL is not reachable but build is ready
          INFO(f"Could not reach URL: {tag['href']}, error: {ex}")
    return ahv_builds

  def get_prev_bundled_ahv(self, ahv_version, ahv_branch):
    """
    Get the prev bundled AHV for a particular AHV Branch
    Args:
      ahv_version(string): AHV Version for which we need prev bundled AHV
      ahv_branch(string): AHV Branch
    Returns:
      ahv_build(string): The latest packaged AHV Build which is older than
                         the AHV Version. None if it doesn't exist
    """
    ahv_builds = self.get_all_packaged_ahv_builds(ahv_branch, only_bundled=True)
    INFO(f"Bundled AHV Builds: {ahv_builds}")
    for ahv_build in ahv_builds:
      greater_ahv = self.version_comparator(ahv_build, ahv_version)
      if greater_ahv == ahv_version and ahv_version != ahv_build:
        return ahv_build
    return None

  def add_dest_ahv_based_on_branch(self, ahv_branch, ahv_version):
    """
    Add latest release AHV, latest master AHV, latest AHV from same branch,
    latest staging AHV from same branch, latest staging branch AHV.

    Args:
      ahv_branch(str): AHV branch name on AHV dashboard.
      ahv_version(str): AHV version.

    Returns:
      dest_ahv_list(list): List of tuple of destination AHV.
    """
    dest_ahv_list = []
    # Find the latest master build and add it to list
    latest_master = self.fetch_latest_packaged_build(branch_name="master")
    if ahv_version != latest_master:
      dest_ahv_list.append(
        (self.get_el_version(latest_master)+
         ".nutanix."+latest_master,
         "dest_ahv")
      )
    if ahv_branch != "master":
      # Find the latest build in same branch and add it to list
      if branch_mapping.BRANCH_MAPPING.get(ahv_branch):
        if branch_mapping.BRANCH_MAPPING[ahv_branch].get("branch_name"):
          br_name = branch_mapping.BRANCH_MAPPING[ahv_branch].get("branch_name")
          latest_same_br = self.fetch_latest_packaged_build(branch_name=br_name)

          if ahv_version != latest_same_br:
            dest_ahv_list.append(
              (self.get_el_version(latest_same_br)+
               ".nutanix."+latest_same_br,
               "dest_ahv")
            )

      # Find the latest build in linked staging branch and add it to list
      if branch_mapping.BRANCH_MAPPING.get(ahv_branch):
        if branch_mapping.BRANCH_MAPPING[ahv_branch].get("staging_branch"):
          br_name = (branch_mapping.BRANCH_MAPPING[ahv_branch].get(
            "staging_branch"
          ))
          latest_staging_br = self.fetch_latest_packaged_build(
            branch_name=br_name
          )

          if ahv_version != latest_staging_br:
            dest_ahv_list.append(
              (self.get_el_version(latest_staging_br)+
               ".nutanix."+latest_staging_br,
               "dest_ahv")
            )

    return dest_ahv_list

  def get_ahv_aos_mapping(self, base_url="http://ahv-dashboard.eng.nutanix."\
                          "com/?tab=rel_branches&subtab=",
                          branch=""):
    """
    A method to fetch the AHV-AOS Mapping

    Args:
      base_url(str): Base URL of AHV Dashboard
      branch(str): AHV Dashboard Branch name

    Returns:
      ahv_aos_mapping(list): List of tuples containing ahv-aos mapping.
                            Each tuple contains two elements, first element
                            is ahv_version(str), second string is list of
                            aos versions mapped to the ahv version.
                            Second item can be none as well.
    """
    print("Finding ahv aos mapping for branch: %s" % branch)
    url = base_url + branch

    page_content = HTTP().get(url).content
    soup = BeautifulSoup(page_content, 'html.parser')
    ahv_aos_mapping = []
    table = soup.findAll('table')[1]
    table_body = table.find('tbody')
    rows = table_body.find_all('tr')

    for row in rows:
      cols = row.find_all('td')
      cols = [ele.text.strip() for ele in cols]
      ahv_version = re.findall("[0-9]{8}[.][0-9]+", cols[0])[0]
      aos_ver_list = cols[1].split(",")
      aos_ver_list = [ele.strip().replace("(", "").replace(")", "")
                      for ele in aos_ver_list]
      ahv_aos_mapping.append((ahv_version, aos_ver_list))

    return ahv_aos_mapping

  def user_input_manipulator(self, user_input_jobs,#pylint: disable=dangerous-default-value
                             default_jobs=metadata.DEFAULT_JOBS):
    """
    A method to manipulate the user input and default jobs json]

    Args:
      user_input_jobs(json): User Input Jobs json
      default_jobs(dict): Default JSON

    Returns:
      updated_jobs(json): Updated Jobs json
    """
    if user_input_jobs.get("test_suite") == "min_build_qual":
      user_input_jobs.update(metadata.MIN_QUAL_JOBS)
    updated_jobs = self.update(
      dic_to_update=default_jobs, update_from=user_input_jobs
    )

    return updated_jobs

  def jobs_manipulator(self, jobs, jobs_upgrade):
    """
    A method to manipulate the jobs json for each type of execution

    Args:
      jobs(json): Main Jobs json
      jobs_upgrade(json): Json containing upgrade details

    Returns:
      updated_jobs(json): Updated Jobs Json
    """
    for i in metadata.JOB_JSON_KEYS_TO_DELETE:
      if jobs.get(i) is not None:
        del jobs[i]
    INFO("Jobs JSON after deletion: "+json.dumps(jobs))
    updated_jobs = jobs_upgrade
    INFO("Updated Jobs: "+json.dumps(updated_jobs))
    if "jobs" in updated_jobs.keys():
      for i in range(len(updated_jobs["jobs"])):
        _to_update = updated_jobs["jobs"][i]
        INFO("To Update: "+json.dumps(_to_update))
        updated_jobs["jobs"][i] = self.update(
          dic_to_update=jobs, update_from=_to_update
        )
    else:
      _to_update = updated_jobs
      INFO("To Update: "+json.dumps(_to_update))
      updated_jobs = self.update(
        dic_to_update=jobs, update_from=_to_update
      )
    INFO("Final Jobs: "+json.dumps(updated_jobs))
    return updated_jobs

  def is_string_a_url(self, string):
    """
    A method to verify if the given string is a URL or not.

    Args:
      string(str): given string to be checked.

    Returns:
      is_url(bool): True/False
    """
    # regex = ("((http|https)://)(www.)?" +
    #          "[a-zA-Z0-9@:%._\\+~#?&//=]" +
    #          "{2,256}\\.[a-z]" +
    #          "{2,6}\\b([-a-zA-Z0-9@:%" +
    #          "._\\+~#?&//=]*)")
    # pat = re.compile(regex)

    # # If the string is empty
    # # return false
    # if str is None:
    #   return False

    # # Return if the string
    # # matched the ReGex
    # if re.search(pat, string):#pylint: disable=simplifiable-if-statement
    #   return True
    # else:
    #   return False
    # baseclient = BaseRestClient()
    # req = baseclient.head(string)
    # return req.status_code < 400

    if ".json" in string[-5:]:
      return True

    return False

  def get_el_version(self, ahv_version):
    """
    A method to get the el version for an AHV version

    Args:
      ahv_version(str): AHV version

    Returns:
      el_version(str): El version
    """
    if "-" in ahv_version:
      el_version = "el8"
    else:
      el_version = ("el8" if (self.version_comparator(
        ahv_version, "20220304.1003283"
      ) == ahv_version and
                              ahv_version[:4] >= "2022") else
                    ("el7" if ahv_version[:4] > "2018" else "el6"))

    return el_version

  def sort_ahv_versions(self, list_of_ahv):
    """
    A method to sort a list of AHV versions

    Args:
      list_of_ahv(list): List of AHV versions to be sorted.

    Returns:
      list_of_ahv(list): Sorted List of AHV versions
    """
    list_len = len(list_of_ahv)
    for i in range(list_len):
      for j in range(0, list_len-i-1):
        if list_of_ahv[j] == self._get_newer_ahv(
            list_of_ahv[j], list_of_ahv[j+1]
        ):
          list_of_ahv[j], list_of_ahv[j+1] = list_of_ahv[j+1], list_of_ahv[j]

    return list_of_ahv

  def get_index_to_insert(self, list_of_ahv, ahv_to_insert):
    """
    A method to fetch the index to insert a particular AHV version in the sorted
    list of AHV versions.

    Args:
      list_of_ahv(list): List of AHV versions to be searched to insert.
      ahv_to_insert(str): AHV version to be inserted.

    Returns:
      index(int): Index where to insert the given AHV version.
    """
    ahv_len = len(list_of_ahv)
    INFO("Length of List of AHV: "+str(ahv_len))
    for i in range(ahv_len-1):
      if (ahv_to_insert == self._get_newer_ahv(
          list_of_ahv[i], ahv_to_insert
        ) and list_of_ahv[i+1] == self._get_newer_ahv(
          list_of_ahv[i+1], ahv_to_insert
        )):
        return i+1
    return ahv_len

  def create_prod_meta(self, ahv_version, ahv_branch):
    """
    A method to create AHV Product Meta for a given AHV version.

    Args:
      ahv_version(str): AHV version
      ahv_branch(str): AHV Branch corresponding to the AHV Version

    Returns:
      ahv_upgrade_prod_meta(dict): AHV Product Meta
    """
    INFO(f"AHV Build provided by user: {ahv_version}")
    ahv_prod_meta = json.loads(urlopen(
      metadata.PRODUCT_META_FILE
    ).read().decode())

    if "-" in ahv_version or len(ahv_version.split(".")[0]) < 8:
      # New AHV Format
      # For new AHV Format, prod meta has only ahv_version without build
      # Eg - 10.0 and not 10.0-123
      ahv_ver_key = ahv_version.split("-")[0]
    else:
      # Old AHV Format
      ahv_ver_key = f"{self.get_el_version(ahv_version)}.nutanix.{ahv_version}"

    ahv_list = [ahv for ahv in ahv_prod_meta.keys()]
    sorted_ahv_list = self.sort_ahv_versions(ahv_list)
    INFO(f"Prod meta sorted AHV list: {sorted_ahv_list}")

    if not ahv_prod_meta.get(ahv_ver_key):
      # If ahv_version is not present in Prod meta, the upgrade paths would be
      # same as the prev_ahv(in sorted list) upgrade_path + the prev_ahv itself
      index = self.get_index_to_insert(sorted_ahv_list, ahv_ver_key)
      INFO(f"Index of {ahv_ver_key} in {sorted_ahv_list}: [{index}]")
      sorted_ahv_list.insert(index, ahv_ver_key)
      INFO(f"Latest sorted AHV list: {sorted_ahv_list}")
      if index != 0:
        prev_ahv = sorted_ahv_list[index-1]
        upgrade_from_list = ahv_prod_meta[prev_ahv].get("upgrade_from", [])
        upgrade_from_list.append(prev_ahv)
        ahv_prod_meta.update({
          ahv_ver_key: {
            "upgrade_from": upgrade_from_list
          }
        })
      else:
        ERROR("Unable to create Prod Meta for the given version."\
             "Please use/create a correct product meta and input"\
             " via test_args")

    if ahv_prod_meta.get(ahv_ver_key) and ahv_branch is not None:
      prev_bundled_ahv = self.get_prev_bundled_ahv(ahv_version, ahv_branch)
      INFO(f"Prev bundled AHV: {prev_bundled_ahv}")
      if prev_bundled_ahv is not None:
        ahv_prod_meta[ahv_ver_key]["upgrade_from"].append(prev_bundled_ahv)
    return ahv_prod_meta

  def update_prod_meta(self, prod_meta, ahv_version):
    """
    Update product meta for AHV/AOS
    Args:
      prod_meta(dict): Product Meta
      ahv_version(str): AHV Version under qual
    Returns:
      prod_meta(dict): Updated prod meta
    """
    # For new AHV versions, the product meta doesn't have full AHV Version
    # Instead only AHV version is present, Eg. - 10.0 instead of 10.0-123
    # So, to hack this around, we can add a new key el8.nutanix.ahv_ver in
    # prod_meta key
    if "-" in ahv_version:
      if ahv_version.split("-")[0] in prod_meta.keys():
        ahv_ver_key = f"el8.nutanix.{ahv_version}"
        prod_meta.update({
          ahv_ver_key : prod_meta[ahv_version.split("-")[0]]
        })
    else:
      ahv_ver_key = f"{self.get_el_version(ahv_version)}.nutanix.{ahv_version}"

    # For 11.0 prod meta might look like -
    # "11.0": {
    #   "upgrade_from": [
    #     "10.0"
    #   ]
    # }
    # The methods which consume this upgrade_from list need full ahv version
    # along with build. el8.nutanix.10.0-622

    upd_upgrade_from = []
    for ahv_ver in prod_meta[ahv_ver_key]["upgrade_from"]:
      if len(ahv_ver.split("-")[0]) < 8:
        # New AHV Format
        if "-" in ahv_ver:
          # Build number already present
          upd_upgrade_from.append(f"el8.nutanix.{ahv_ver}")
        else:
          # Get all the bundled AHV builds
          ahv_builds = self.get_all_packaged_ahv_builds(branch_name=ahv_ver)
          INFO(f"AHV Builds: {ahv_builds}")
          # Add all the AHV Builds which are less than current ahv_version build
          for ahv_build in ahv_builds:
            # Make sure to add older AHV Build than ahv_version under test
            # in upgrade_from list
            if (self.version_comparator(ahv_build, ahv_version) == ahv_version
                and ahv_build != ahv_version):
              upd_upgrade_from.append(f"el8.nutanix.{ahv_build}")
      else:
        upd_upgrade_from.append(ahv_ver)

    prod_meta[ahv_ver_key]["upgrade_from"] = upd_upgrade_from
    INFO(f"Prod Meta: {prod_meta}")
    INFO(f"For {ahv_ver_key}, upgrade_from list: {upd_upgrade_from}")
    return prod_meta

  def update(self, dic_to_update, update_from):
    """
    A recursive method which updates values of a nested dictionary
    of varying depth.

    Args:
      dic_to_update(dict): Dictionary in which the values have to be updated.
      update_from(dict): Dictionary from which the values have to be searched
               and updated.

    Returns:
      dic_to_update(dict): Dictionary with the updated values.
    """
    if isinstance(update_from, list):
      for val in update_from:
        self.update(dic_to_update, val)
    elif isinstance(update_from, dict):
      for key in update_from.keys():
        if self.find_key(dic_to_update, key, update_from[key]) is not None:
          dic_to_update = self.find_key(dic_to_update, key, update_from[key])
        else:
          dic_to_update.update({str(key): update_from[key]})
    return dic_to_update

  def find_key(self, dic_to_update, key, value):
    """
    A recursive method to find and replace value 'value' of a key 'key'
    in the dictionary 'dic_to_update'.

    Args:
      dic_to_update(dict): Dictionary in which the key has to be
                           searched and replaced.
      key(str): Key which has to be searched & updated in the
              dictionary.
      value(str): Value which has to be updated in given key 'key'.

    Returns:
      dic_to_update(dict): Dictionary with updated values.
    """
    if isinstance(dic_to_update, list):
      for val in dic_to_update:
        return self.find_key(val, key, value)
    elif isinstance(dic_to_update, dict):
      if key in dic_to_update.keys():
        dic_to_update[key] = value
        return dic_to_update
      for each_key in dic_to_update.keys():
        return self.find_key(dic_to_update[each_key], key, value)
    else:
      return None


  def get_num_of_free_nodes(self, node_pool_name, platform=None):
    """
    A method to calculate the number of free nodes in the node pool

    Args:
      node_pool_name(str): Node Pool Name.
      platform(str): Platform/Model name (Optional).

    Returns:
      free_nodes(int): Number of free nodes
    """
    free_nodes = 0

    node_pool_id = self.jarvis_client.get_node_pool_id(
      node_pool_name=node_pool_name
    )

    node_details = self.jarvis_client.get_node_details_from_pool(
      node_pool_id=node_pool_id
    )

    for node_detail in node_details:
      if (node_detail["is_enabled"] and
          (node_detail["cluster_owner"] is None)
          and (node_detail["cluster_name"] is None)):
        INFO("cluster_owner: "+str(node_detail["cluster_owner"]))
        if platform is not None:
          if node_detail["hardware"]["model"] == platform:
            free_nodes += 1
        else:
          free_nodes += 1

    return free_nodes

  def _get_newer_ahv(self, version1, version2):
    """
    Get the newer AHV version among the two versions
    Args:
      version1(str): First AHV Version
      version2(str): Second AHV Version
    Returns:
      newer_version(str): Newwer of the two AHV Versions
    """
    # For new AHV format versions, when only ahv_version is present
    # Eg - 10.0 and not full ahv_version with build - 10.0-123
    # The version_comparator will not be able to identify this as new ahv
    # and the comparator will return inaccurate results
    # To overcome this, adding a dummy build no. 1 to newer AHV versions for
    # accurate comparisons.
    # And for old-format AHV, el{x}.nutanix. needs to be removed from prefix
    ahv_ver1 = version1
    ahv_ver2 = version2

    if "el" in version1:
      ahv_ver1 = version1.split("nutanix.")[1]
    if "el" in version2:
      ahv_ver2 = version2.split("nutanix.")[1]

    if len(ahv_ver1.split(".")[0]) < 8 and "-" not in ahv_ver1:
      ahv_ver1 = f"{ahv_ver1}-1"
    if len(ahv_ver2.split(".")[0]) < 8 and "-" not in ahv_ver2:
      ahv_ver2 = f"{ahv_ver2}-1"

    if ahv_ver1 == self.version_comparator(ahv_ver1, ahv_ver2):
      return version1
    else:
      return version2
