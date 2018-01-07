"""The writer package for Canary Data Converter"""
import importlib
import inspect
import os

from .write import Write

# all list for all of the package's modules
__all__ = []
# GUI keys dictionary that maps writer's GUI_LABEL list to class object
GUI_KEYS = {}
# CLI keys dictionary that maps writer's CLI_LABEL list to class object
CLI_KEYS = {}

# dynamically retrieve writers
# get all of the files in this directory
for f in os.listdir(os.path.dirname(__file__)):
    # ignore the __init__ file
    if f.startswith('_') or not f.endswith('py'):
        continue
    
    # remove extension
    file = f.split('.')[0]

    # import the module with importlib
    mod = importlib.import_module('cdc.write.{}'.format(file))
    
    # add the module to the __all__ list
    __all__.append(file)
    
    # now iterate over the module's variables and get the classes
    for k, v in vars(mod).items():
        # if it isn't a class, continue
        # make sure you don't add base class, because that can't actually write
        if not inspect.isclass(v) or not issubclass(v, Write) or k == 'Write':
            continue
        
        # map labels to class
        GUI_KEYS.update({label: v for label in v.GUI_LABELS})
        CLI_KEYS.update({label: v for label in v.CLI_LABELS})
