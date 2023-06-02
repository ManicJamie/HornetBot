import os
import importlib
import re

__globals = globals()

modules = []
for file in os.listdir(os.path.dirname(__file__)):
    mod_name = file[:-3]   # strip .py at the end
    if not re.match(r'^__', file): # filter out dunder modules (this module!)
        modules.append(mod_name)
        __globals[mod_name] = importlib.import_module('.' + mod_name, package=__name__)

modules_commands = []
for m in modules:
    modules_commands += __globals[m].module_commands