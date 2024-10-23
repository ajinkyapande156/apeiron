"""
Copyright (c) 2022 Nutanix Inc. All rights reserved.

Author: pritam.chatterjee@nutanix.com
"""


class PreVerificationFailed(Exception):
  """PreVerificationFailed class"""
  pass


class PostVerificationFailed(Exception):
  """PostVerificationFailed class"""
  pass


class TestFailed(Exception):
  """TestFailed class"""
  pass


class TestNotSupported(Exception):
  """TestNotSupported class"""
  pass
