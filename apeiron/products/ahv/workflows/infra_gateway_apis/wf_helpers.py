"""
Copyright (c) 2024 Nutanix Inc. All rights reserved.

Author: pritam.chatterjee@nutanix.com
"""
import re
import threading
import time

from pprint import pformat
from framework.lib.nulog import INFO, STEP
from framework.exceptions.nutest_error import NuTestError
from workflows.acropolis.ahv.acro_host_helper import get_co_hosts, get_hc_hosts
from workflows.acropolis.ahv_management.scheduler_test_lib import \
  SchedulerTestLib
from libs.framework.mjolnir_executor import use_executor
from libs.gateway.gateway_interface import (
  GatewayClientInterface)

#pylint: disable=no-member,unused-variable,no-self-use,broad-except
#pylint: disable=invalid-name,bare-except,keyword-arg-before-vararg

class BaseHelper:
  """Base class"""
  def __init__(self, cluster=None):
    """
    Create object
    Args:
       cluster(object):
    Returns:
    """
    self.cluster = cluster
    INFO("Initializing GatewayClientInterface")
    self.gw_client = GatewayClientInterface(self.cluster)
    self.scheduler_lib = SchedulerTestLib(self.cluster)
    self.hc_host = get_hc_hosts(self.cluster)[0]
    self.co_host = None
    co_hosts = get_co_hosts(self.cluster)
    if co_hosts:
      self.co_host = co_hosts[0]
    INFO(f"Checking connection to {self.hc_host.ip}")
    INFO(pformat(self.gw_client.get_host_version(
      self.hc_host.ip,
      cert_type="Acropolis")))
    INFO("Initializing Complete")


class HostHelper(BaseHelper):
  """HostHelper class"""

  @use_executor
  def validate_get_passwd_info(self, **kwargs):
    """"
    Validate passwd info
    Args:
    Returns:
    Raises:
    """
    host = self.hc_host
    INFO("Testing host %s" % host.ip)
    response = self.gw_client.get_passwd_info(host.ip,
                                              kwargs.get('user'),
                                              cert_type=
                                              kwargs.get('cert_type'))
    INFO(pformat(response))
    # TODO: validate the schema

  @use_executor
  def validate_get_hostname(self, **kwargs):
    """"
    Validate hostname
    Args:
    Returns:
    Raises:
    """
    host = self.hc_host
    INFO("Testing host %s" % host.ip)
    response = self.gw_client.get_hostname(host.ip,
                                           cert_type=
                                           kwargs.get('cert_type'))
    INFO(pformat(response))
    if 'hostname' in response and response['hostname']:
      INFO(f"The key 'hostname' exists and its value is: "
           f"{response['hostname']}")
    else:
      raise NuTestError(f"Either the key 'hostname' does not exist or "
                        f"its value is empty/None.")

  @use_executor
  def validate_get_host_version(self, **kwargs):
    """"
    Validate host version
    Args:
    Returns:
    Raises:
    """
    host = self.hc_host
    INFO("Testing host %s" % host.ip)
    response = self.gw_client.get_host_version(host.ip,
                                               cert_type=
                                               kwargs.get('cert_type'))
    INFO(pformat(response))

    if not response.get('build', '').isdigit():
      raise NuTestError(f"'build' must contain only digits.")
    # Validate 'version' - must follow 'number.number' format
    version_pattern = re.compile(r'^\d+(\.\d+)+$')
    if not version_pattern.match(response.get('version', '')):
      raise NuTestError(f"'version' must be in the format 'number.number'.")

    INFO(f"Validation passed.")

  @use_executor
  def validate_update_ovs_iface(self, **kwargs):
    """"
    Validate iface
    Args:
    Returns:
    Raises:
    """
    host = self.hc_host
    if kwargs.get('co_host', False):
      host = self.co_host
    INFO("Testing host %s" % host.ip)
    self.create_bridge_hepler(host.ip, **kwargs)
    iface = kwargs.get('payload')['bridge']
    response = self.gw_client.update_ovs_iface(host.ip, iface,
                                               payload=kwargs.get('payload'),
                                               cert_type=
                                               kwargs.get('cert_type'))
    INFO(pformat(response))

  def validate_default_certs_configured(self, **kwargs):
    """"
    Validate default certs on configured node
    Args:
    Returns:
    Raises:
    """
    node = self.hc_host
    INFO("Testing host %s" % node.ip)
    try:
      INFO("Get OVS interface should fail")
      response = self.gw_client.get_ovs_iface(node.ip,
                                              kwargs.get('iface', 'br0'),
                                              cert_type=kwargs.get('cert_type')
                                              )
      INFO(pformat(response))
    except Exception as e:
      INFO(f"Get OVS interface failed as expected: {e}")
    else:
      raise NuTestError("Expect the GET request to be failed")

    try:
      INFO("Create bridge should fail")
      self.create_bridge_hepler(node.ip, **kwargs)
    except Exception as e:
      INFO(f"Create bridge failed as expected: {e}")
    else:
      raise NuTestError("Expect the POST request to be failed")

    try:
      INFO("Update the OVS interface should fail")
      iface = kwargs.get('payload')['bridge']
      response = self.gw_client.update_ovs_iface(node.ip, iface,
                                                 payload=
                                                 kwargs.get('payload'),
                                                 cert_type=
                                                 kwargs.get('cert_type'))
      INFO(pformat(response))
    except Exception as e:
      INFO(f"Update the OVS interface failed as expected: {e}")
    else:
      raise NuTestError("Expect the PUT request to be failed")

  def validate_unconfigured(self, **kwargs):
    """"
    Validate iface
    Args:
    Returns:
    Raises:
    """
    node = self.hc_host
    try:
      INFO('Remove node %s(%s)' % (node.name, node.uuid))
      self.scheduler_lib.remove_node(node=node, force=True)
      node_removed = True

      INFO("Testing host %s" % node.ip)
      INFO("Get OVS Interface should succeed")
      response = self.gw_client.get_ovs_iface(node.ip,
                                              kwargs.get('iface', 'br0'),
                                              cert_type=kwargs.get('cert_type')
                                              )
      INFO(pformat(response))

      INFO("Create bridge should succeed")
      self.create_bridge_hepler(node.ip, **kwargs)

      INFO("Update the OVS interface should succeed")
      iface = kwargs.get('payload')['bridge']
      response = self.gw_client.update_ovs_iface(node.ip, iface,
                                                 payload=
                                                 kwargs.get('payload'),
                                                 cert_type=
                                                 kwargs.get('cert_type'))
      INFO(pformat(response))
      # TODO: validate the schema
    except Exception as e:
      raise NuTestError(f"An error occurred: {e}")
    finally:
      if node_removed:
        STEP('Add node %s(%s)' % (node.name, node.uuid))
        self.scheduler_lib.add_node(node)

  @use_executor
  def validate_get_ovs_iface(self, **kwargs):
    """"
    Validate iface
    Args:
    Returns:
    Raises:
    """
    host = self.hc_host
    if kwargs.get('co_host', False):
      host = self.co_host
    INFO("Testing host %s" % host.ip)
    br = kwargs.get('iface', 'br0')
    response = self.gw_client.get_ovs_iface(host.ip,
                                            br,
                                            cert_type=kwargs.get('cert_type'))
    INFO(pformat(response))
    # validate the schema
    if response['name'] != br:
      raise NuTestError(f"The iface name {response['name']} "
                        f"does not match expected name {br}")

  def validate_concurrent_get_ovs_iface(self, **kwargs):
    """"
    Validate iface
    Args:
    Returns:
    Raises:
    """
    host = self.hc_host
    if kwargs.get('co_host', False):
      host = self.co_host
    iface = kwargs.get('iface', 'br0')
    cert_type = kwargs.get('cert_type')
    INFO("Testing host %s" % host.ip)
    def gw_th():
      start_time = time.time()
      while time.time() - start_time < 120:
        # Restart gatway
        INFO("Stop gateway service")
        self.hc_host.execute("systemctl stop ahv-gateway")
        time.sleep(20)
        INFO("Start gateway service")
        self.hc_host.execute("systemctl start ahv-gateway")
        time.sleep(120) # Sleep 2 minutes
    def worker(results, ip, iface, cert_type):
      INFO(f"{threading.current_thread().name} is starting.")
      start_time = time.time()
      while time.time() - start_time < 120:
        try:
          self.gw_client.get_ovs_iface(ip, iface,
                                       cert_type=cert_type)
          INFO(f"{threading.current_thread().name} get ovs iface succeeded.")
          time.sleep(10)  # Sleep to simulate work or prevent busy-waiting
        except Exception as e:
          error_message = str(e)
          INFO(error_message)
          if not re.search(r'(Errno 61|504|Errno 111|' \
                           r'Failed to establish a new connection|' \
                           r'Connection refused)', error_message):
            results.append("error")
            break

    # Creating and starting threads
    threads = []
    results = []
    for i in range(5):
      thread_name = f"Thread-{i+1}"
      thread = threading.Thread(target=worker,
                                args=(results, host.ip, iface, cert_type),
                                name=thread_name)
      threads.append(thread)
      thread.start()
    thread_gw = threading.Thread(target=gw_th)
    threads.append(thread_gw)
    thread_gw.start()

    # Wait for all threads to complete
    for thread in threads:
      thread.join()

    if results.count("error"):
      raise NuTestError("No all threads have successful get requests")

  def create_bridge_hepler(self, ip, **kwargs):
    """"
    Validate iface creation
    Args:
      ip(str): the host ip
    Returns:
    Raises:
    """
    br = kwargs.get('payload')['bridge']
    try:
      self.gw_client.get_ovs_iface(ip, br,
                                   cert_type=kwargs.get('cert_type'))
    except Exception as e:
      INFO("bridge %s not found" % br)
      INFO("Create the bridge")
      # if not found, create the bridge
      bridge = {
        "name": br,
        "multicast_snooping": {
          "enabled": True
        }
      }
      self.gw_client.create_bridge(ip, payload=bridge,
                                   cert_type=kwargs.get('cert_type'))

  @use_executor
  def validate_create_ovs_iface(self, **kwargs):
    """"
    Validate iface creation
    Args:
    Returns:
    Raises:
    """
    host = self.hc_host
    if kwargs.get('co_host', False):
      host = self.co_host
    INFO("Testing host %s" % host.ip)
    self.create_bridge_hepler(host.ip, **kwargs)
    response = self.gw_client.create_ovs_iface(host.ip,
                                               kwargs.get('payload'),
                                               cert_type=
                                               kwargs.get('cert_type'))
    INFO(pformat(response))

  @use_executor
  def validate_concurrent_create_ovs_iface(self, **kwargs):
    """"
    Validate iface creation
    Args:
    Returns:
    Raises:
    """
    host = self.hc_host
    if kwargs.get('co_host', False):
      host = self.co_host
    payload = kwargs.get('payload')
    cert_type = kwargs.get('cert_type')
    INFO("Testing host %s" % host.ip)
    self.create_bridge_hepler(host.ip, **kwargs)
    def worker(results, ip, payload, cert_type):
      INFO(f"{threading.current_thread().name} is starting.")
      try:
        response = self.gw_client.create_ovs_iface(ip, payload,
                                                   cert_type=cert_type)
      except Exception as e:
        results.append("error")
        raise NuTestError("Failed to create ovs interface") from e
      else:
        results.append('success')
      INFO(pformat(response))
      time.sleep(2)
      print(f"{threading.current_thread().name} has finished.")

    # Creating and starting threads
    threads = []
    results = []
    for i in range(2):
      thread_name = f"Thread-{i+1}"
      thread = threading.Thread(target=worker,
                                args=(results, host.ip, payload, cert_type),
                                name=thread_name)
      threads.append(thread)
      thread.start()

    # Wait for all threads to complete
    for thread in threads:
      thread.join()
    # Only one thread should succeed
    successful_creations = results.count("success")
    if successful_creations != 1:
      raise NuTestError("Only one thread is expected" + \
                        "to create the interface successfully.")
    # TODO: validate the schema

  @use_executor
  def validate_create_bridge(self, **kwargs):
    """"
    Validate iface creation
    Args:
    Returns:
    Raises:
    """
    INFO(kwargs)
    host = self.hc_host
    if kwargs.get('co_host', False):
      host = self.co_host
    INFO("Testing host %s" % host.ip)
    response = self.gw_client.create_bridge(host.ip,
                                            payload=kwargs.get('bridge'),
                                            cert_type=kwargs.get('cert_type'))
    INFO(pformat(response))

  @use_executor
  def validate_concurrent_create_bridge(self, **kwargs):
    """"
    Validate iface creation
    Args:
    Returns:
    Raises:
    """
    host = self.hc_host
    if kwargs.get('co_host', False):
      host = self.co_host
    bridge = kwargs.get('bridge')
    cert_type = kwargs.get('cert_type')
    INFO("Testing host %s" % host.ip)
    def worker(results, ip, bridge, cert_type):
      print(f"{threading.current_thread().name} is starting.")
      try:
        response = self.gw_client.create_bridge(ip, payload=bridge,
                                                cert_type=cert_type)
      except Exception as e:
        results.append("error")
        raise NuTestError("Failed to create ovs interface") from e
      else:
        results.append('success')
      INFO(pformat(response))
      time.sleep(2)
      print(f"{threading.current_thread().name} has finished.")

    # Creating and starting threads
    threads = []
    results = []
    for i in range(2):
      thread_name = f"Thread-{i+1}"
      thread = threading.Thread(target=worker,
                                args=(results, host.ip, bridge, cert_type),
                                name=thread_name)
      threads.append(thread)
      thread.start()

    # Wait for all threads to complete
    for thread in threads:
      thread.join()
    # Only one thread should succeed
    successful_creations = results.count("success")
    if successful_creations != 1:
      raise NuTestError("Only one thread is expected" + \
                        "to create the interface successfully.")
    # TODO: validate the schema

class InfraGatewayWfHelper(HostHelper):
  """InfraGatewayWfHelper class"""
  def validate_setup_compatibility(self, **kwargs):
    """
    setup validations
    Args:
    Returns:
    Raises:
    """
    INFO(kwargs)
    INFO("No validations added")
