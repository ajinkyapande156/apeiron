"""
Copyright (c) 2023 Nutanix Inc. All rights reserved.

Author: pritam.chatterjee@nutanix.com
Please refer to:
docs.python.org/3/library/xml.etree.elementtree.html#elementtree-parsing-xml
for adding method to parse xml
"""
import xml.etree.ElementTree as xml_parser
# pylint: disable=wrong-import-order, no-member, unused-variable
# pylint: disable=ungrouped-imports, no-self-use, fixme
# pylint: disable=anomalous-backslash-in-string, unused-import,
# pylint: disable=unnecessary-comprehension, unused-argument, broad-except
from framework.lib.nulog import INFO, WARN, ERROR
from libs.framework import mjolnir_entities as entities
from libs.feature.apc.factory \
  import ApcVmFactory


class DumpXml:
  """Class to perform VM libvirt xml related validation"""

  @staticmethod
  def get_hyperv_flags(**kwargs):
    """
    Method to get the hyperv flags set for the VM
    Kwargs:
    Returns:
      hyperv_flags(dict):
    Raises:
    """
    xml_dump = DumpXml._get_xml_dump(**kwargs)
    assert xml_dump, "Failed to get any data from virsh dump xml"
    root = xml_parser.fromstring(xml_dump)
    hyperv_ = root.findall("./features/hyperv/*")
    hyperv_flags = {}
    for feature in hyperv_:
      hyperv_flags[feature.tag] = feature.attrib['state']
    hyperv_clock = root.findall("./clock/timer/[@name='hypervclock']")
    if hyperv_clock:
      hyperv_flags[hyperv_clock[0].attrib['name']] = \
        hyperv_clock[0].attrib['present']
    return hyperv_flags

  @staticmethod
  def _get_xml_dump(vm_uuid=None, **kwargs):
    """
    Internal method to get the dump xml from host
    Args:
       vm_uuid(str):
    Kwargs:
    Returns:
    Raises:
    """
    if not vm_uuid:
      raise RuntimeError("VM uuid is not provided")
    apc_vm_acli = ApcVmFactory(api_type="acli")
    cluster = entities.ENTITIES.get("pe")
    host_uuid = apc_vm_acli.get(vm_name=vm_uuid)["host_uuid"]
    host = [host for host in cluster.hypervisors
            if host.uuid in host_uuid]
    assert len(host) == 1, "Failed to get the host details properly %s" % host
    INFO("VM %s is on host %s" % (vm_uuid, host[0].uuid))
    cmd = "virsh dumpxml %s" % vm_uuid
    res = host[0].execute(cmd)
    assert not res["status"], "Failed to execute dumpxml command"
    return res['stdout']
