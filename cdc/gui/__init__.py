import configparser
import importlib
import logging
import os
import sys
# append outer directory to path so toplevel package can import in other files
# don't need to do it if frozen into exe
if not getattr(sys, 'frozen', False):
    sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# all list for all of the package's modules
__all__ = []

# path to the gui config file (this is what holds last opened directories)
CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'gui.ini')

# open the GUI config file
CONFIG = configparser.ConfigParser()
CONFIG.read(CONFIG_PATH)

# create the GUI package logger constant
LOGGER = logging.getLogger('log')

# dynamically add files to __all__
# get all of the files in this directory
for f in os.listdir(os.path.dirname(__file__)):
    # make sure it's a module
    file_list = f.split('.')
    if f.startswith('_') or 'py' not in file_list[-1]:
        continue
    # get rid of extension
    file = file_list[0]
    # import module
    mod = importlib.import_module('cdc.gui.{}'.format(file))
    # append to all
    __all__.append(file)
