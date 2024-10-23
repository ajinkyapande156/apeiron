"""
Copyright (c) 2022 Nutanix Inc. All rights reserved.

Author: pritam.chatterjee@nutanix.com
"""
# pylint: disable=import-error
import inspect
import traceback

try:
  from framework.nulog import INFO, ERROR
  EXECUTOR = "nutest"
except Exception:  # pylint: disable=broad-except
  from libs.ahv.framework.proxy_logging \
    import INFO, ERROR
  EXECUTOR = "mjolnir"
from libs.ahv.workflows.gos_qual.lib import operations
from libs.ahv.workflows.gos_qual.lib.base.abstracts \
  import AbstractTest
from libs.ahv.workflows.gos_qual.lib.base.utilities \
  import get_module_classes
from libs.ahv.workflows.gos_qual.lib.base.abstracts \
  import AbstractVerifier
from libs.ahv.workflows.gos_qual.lib.base.gos_errors \
  import PreVerificationFailed, PostVerificationFailed, TestFailed


class BaseTest(AbstractTest):
  """BaseTest class"""
  TAGS = []
  PRE_OPERATIONS = []
  POST_OPERATIONS = []
  DEFAULT_PARAMS = []

  @classmethod
  def get_tags(cls):
    """
    Get tags for the test
    Args:
    Returns:
      Tags(list): list of tags for the given test
    """
    return cls.TAGS

  @classmethod
  def get_default_params(cls):
    """
    Get default params for the test
    Args:
    Returns:
    """
    return cls.DEFAULT_PARAMS

  @classmethod
  def get_pre_operations(cls):
    """
    Get default pre operations for the test
    Args:
    Returns:
    """
    return cls.PRE_OPERATIONS

  @classmethod
  def get_post_operations(cls):
    """
    Get default post operations for the test
    Args:
    Returns:
    """
    return cls.POST_OPERATIONS

  @classmethod
  def execute_pre_operations(cls, ops, **kwargs):
    """
    Operations to be executed before the test execution starts
    Args:
      ops(str):
    Returns:
    """
    pre_ops = ops
    cls._execute_operations(pre_ops, **kwargs)

  @classmethod
  def execute_post_operations(cls, ops, **kwargs):
    """
    Operations to be executed after the test execution starts
    Args:
      ops(str):
    Returns:
    """
    post_ops = ops
    cls._execute_operations(post_ops, **kwargs)

  @classmethod
  def teardown(cls, *args, **kwargs):
    """
    Cleanup for the tests
    Args:
    Returns:
    """
    pass

  @classmethod
  def _execute_operations(cls, ops, **params):
    """
    Execute operations
    Args:
      ops(str): Name of operation module to be executed
    kwargs:
    Returns:
    Raises:
    """
    available = \
      get_module_classes(operations,
                         predicate=lambda x: inspect.isclass(
                           x) and not x.__subclasses__()
                         and issubclass(x, AbstractVerifier))
    for op in ops:
      INFO("Executing: %s" % op)
      try:
        available[op]().verify(**params)
      except KeyError:
        ERROR(traceback.format_exc())
        ERROR("Verifier not found: %s" % op)
      except PreVerificationFailed as ex:
        ERROR(traceback.format_exc())
        ERROR(ex)
      except PostVerificationFailed as ex:
        raise ex
      except Exception:
        ERROR(traceback.format_exc())
        raise TestFailed
