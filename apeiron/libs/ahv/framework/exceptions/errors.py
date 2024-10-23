"""
Copyright (c) 2022 Nutanix Inc. All rights reserved.

Author: pritam.chatterjee@nutanix.com
"""
#pylint:disable=unnecessary-pass, redefined-builtin

class TimeoutError(Exception):
  """TimeoutError"""
  pass

class EntityNotFoundError(Exception):
  """EntityNotFound"""
  pass

class IpNotFoundError(Exception):
  """IpNotFound"""
  pass

class TaskFailedError(Exception):
  """TaskFailed"""
  pass

########################
# Vm  ops errors
########################
class VmOpError(Exception):
  """VmOpError"""
  pass

########################
# Misc errors
########################
class UnsupportedParamError(Exception):
  """When unsupported params are passed through test config or otherwise"""
  pass

class VMVerificationError(Exception):
  """When some VM Verifications fail"""
  pass
