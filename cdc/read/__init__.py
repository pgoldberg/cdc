"""The reader package for Canary Data Converter"""
import importlib
import inspect
import os

from .read import Read

# all list for all of the package's modules
__all__ = []
# GUI keys dictionary that maps reader's GUI_LABEL list to class object
GUI_KEYS = {}
# CLI keys dictionary that maps reader's CLI_LABEL list to class object
CLI_KEYS = {}

class ReaderError(Exception):
    pass

# dynamically retrieve readers
# get all of the files in this directory
for f in os.listdir(os.path.dirname(__file__)):

    # ignore the __init__ file and ensure it's a valid module
    if f.startswith('_') or not f.endswith('py'):
        continue
    
    # remove extension
    file = f.split('.')[0]

    # import the module with importlib
    mod = importlib.import_module('cdc.read.{}'.format(file))
    
    # add the module to the __all__ list
    __all__.append(file)
    
    # now iterate over the module's variables and get the classes
    for k, v in vars(mod).items():
        # if it isn't a class, continue
        # make sure you don't add base class, because that can't actually read
        if not inspect.isclass(v) or not issubclass(v, Read) or k == 'Read':
            continue
        
        #print("Found Reader:", v)
        
        # map labels to class
        GUI_KEYS.update({label: v for label in v.GUI_LABELS})
        CLI_KEYS.update({label: v for label in v.CLI_LABELS})
