'''Logging module for Mjolnir'''
# pylint: disable=invalid-name, global-statement
LOGGER_INFO = None
LOGGER_ERROR = None
LOGGER_DEBUG = None
LOGGER_WARN = None


class MjolnirLogger(object):
  """Class to initiaise the logging varibales for a test"""
  def __init__(self, info, error, debug, warn):
    """
      Initialises the logging variables

      Args:
        info(object): Info object of logger
        error(object): Error object of logger
        debug(object): Debug object of logger
        warn(object): Warn object of logger
    """
    self.info = info
    self.error = error
    self.debug = debug
    self.warn = warn
    self.set_logging_vars()

  def set_logging_vars(self):
    '''Updates the global logging variables'''
    global LOGGER_INFO
    global LOGGER_ERROR
    global LOGGER_DEBUG
    global LOGGER_WARN

    LOGGER_INFO = self.info
    LOGGER_ERROR = self.error
    LOGGER_DEBUG = self.debug
    LOGGER_WARN = self.warn

def INFO(msg):
  """
    Logs an info messsage

    Args:
      msg (str): The message to be logged

    Raises:
      exception: If logging variable is not set
  """
  try:
    LOGGER_INFO(msg)
  except:
    raise Exception("Logging variables not set")

def ERROR(msg):
  """
    Logs an error messsage

    Args:
      msg (str): The message to be logged

    Raises:
      exception: If logging variable is not set
  """
  try:
    LOGGER_ERROR(msg)
  except:
    raise Exception("Logging variables not set")

def DEBUG(msg):
  """
    Logs a debug messsage

    Args:
      msg (str): The message to be logged

    Raises:
      exception: If logging variable is not set
  """
  try:
    LOGGER_DEBUG(msg)
  except:
    raise Exception("Logging variables not set")

def WARN(msg):
  """
    Logs an info messsage

    Args:
      msg (str): The message to be logged

    Raises:
      exception: If logging variable is not set
  """
  try:
    LOGGER_WARN(msg)
  except:
    raise Exception("Logging variables not set")

def STEP(msg):
  """
    Prints test steps

    Args:
      msg(str): Message to be logged
  """
  line_styling = "-----------------------------------------------------------"
  INFO(line_styling)
  INFO(msg)
  INFO(line_styling)
