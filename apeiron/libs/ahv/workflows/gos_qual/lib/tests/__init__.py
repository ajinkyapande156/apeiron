# """
# Copyright (c) 2021 - 2022 Nutanix Inc. All rights reserved.
#
# Author: pritam.chatterjee@nutanix.com
# """
# import importlib
# import inspect
# import os
# import pkgutil
#
#
# TESTS = dict()
#
#
# def predicate(mod):
#   if inspect.isclass(mod) and not mod.__subclasses__() and issubclass(mod, AbstractTest):
#     return True
#   return False
#
# import pdb; pdb.set_trace()
# for (module_loader, name, ispkg) in pkgutil.iter_modules([os.path.dirname(__file__)]):
#   # TODO:
#   #  1. __package__ in hardcored in import_module.
#   #  2. This implementation is specific to python2
#   mod = importlib.import_module("." + name,
#                                 "mjolnir.workflows.guest_os_qualification.lib.qual_tests")
#   classes = [impl[1] for impl in inspect.getmembers(mod, predicate=predicate)]
#   if classes:
#     TESTS[name] = classes[0]
