"""
Copyright (c) 2021 Nutanix Inc. All rights reserved.

Author: vedant.dalal@nutanix.com

This module contains all Objects Product Util methods.
"""

import json
import re
from framework.interfaces.http.http import HTTP

from framework.lib.nulog import INFO

class ObjectsUtil():
  """
  A class containing Objects Utility methods.
  """

  def __init__(self):
    """
    Constructor Method.
    """
    self.ENDOR_DYN_WEBSERVER = "endor.dyn.nutanix.com"#pylint: disable=invalid-name

  @staticmethod
  def get_available_branches(url):
    """
    A method to get available branches from the provided url.

    Args:
      url(str): URL.

    Returns:
      branches(str): Branches.

    Raises:
      Exception: Failed to fetch.
    """
    res = HTTP().get(url)
    if not res.ok:
      raise Exception("Failed to fetch %s: %s" %  (url, res.content))
    branches = []
    if "<table>" in res.text:
      for line in res.text.split("\n"):
        match = re.search(r'(href=")([0-9a-zA-Z-._]+)', line)
        if match:
          branch = match.group()
          branches.append(branch.split('"')[1])
    return branches

  def find_suitable_webserver(self):
    """
    A method to return web-server which ever is accessible.

    Returns:
      webserver(str): Webserver.
    """
    # TODO: Check webserver is accessible
    webserver = self.ENDOR_DYN_WEBSERVER
    return webserver

  def resolve_product_version_to_commit(self, product_branch=None,
                                        product_version=None):
    """
    Get branch details for the given tag.

    Args:
      product_branch(str): posiedon branch name example : buckets-3.4
      product_version(str): release tag name example: latest, rc_1

    Returns:
      dict, example:
      {u'status': u'available', u'name': u'aoss_service_manager.tar.xz',
      u'url': u'http://builds.dyn.nutanix.com/poseidon-builds/buckets_manager/'
      u'buckets-3.4/1acb396010192e4ea702d22f1cb41a468052b3eb/release/'
      u'aoss_service_manager.tar.xz', u'image': u'aoss_service_manager.tar.xz',
      u'flag_list': [], u'version': u'latest', u'update_library_list': [],
      u'tag_list': [],
      u'shasum': u'32932a5d3d479f73d9f7f837b6d1cc6fc41a2f35b15964f65844d0b047'}

    Raises:
      Exception: Failed to fetch.
    """
    # Get build web-server.
    web_server = self.find_suitable_webserver()

    # Get details from metadata.json
    metadata_url = ("http://%s/builds/poseidon-builds/buckets_manager" %
                    web_server)

    # Get available braches
    available_branches = self.get_available_branches(url=metadata_url)
    if product_branch not in available_branches:
      raise Exception("'%s' branch not available in webserver" %product_branch)

    metadata_url = metadata_url + "/%s/metadata.json" %product_branch
    response = HTTP().get(metadata_url, allow_redirects=True)
    if not response.ok:
      raise Exception("Failed to fetch metadata.json file: %s" %
                      response.content)
    branch_js = json.loads(response.content)
    for v in branch_js['image_list']:#pylint: disable=invalid-name
      if product_version == v['version']:
        aoss_tar_url = v["image_details"][0]["url"] if 'image_details' in v \
          else v['url']
        INFO(aoss_tar_url)
        return aoss_tar_url.split('/')[-3]

    raise Exception("No tag maches with the given tag : %s" %product_version)

  def get_objects_image_tag(self, product_branch, product_version):
    """
    A method to get the objects commit image tag.

    Args:
      product_branch(str): Product Branch.
      product_version(str): Product Version.

    Returns:
      image_tag(str): Image Tag.

    """
    if product_version == "latest":
      resolved_commit = self.resolve_product_version_to_commit(
        product_branch, product_version
      )
      if product_branch == "poseidon":
        return "poseidon_build_release"
      return "{}.opt.{}".format(product_branch, resolved_commit[:12])
    return ""
