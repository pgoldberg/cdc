"""Canary Data Converter - an extendable conversion tool"""
import configparser
import importlib
import logging
import os
import platform
import sys

# get cdc package directory
cdc_dir = os.path.dirname(os.path.abspath(__file__))

# get version number from file
with open(os.path.join(cdc_dir, 'resources', 'version.txt'), 'r') as version:
    __version__ = version.read()

# store platform info
os_system = platform.system()
os_release = platform.release()
os_version = platform.version()
python_version = "%s (%s)" % (platform.python_version(), sys.version)
os_string = 'Operating System: {} (Release: {}; Version: {}) Python Version: {}'.format(os_system, os_release, os_version, python_version)

# all list for all of the package's modules
__all__ = []

# read in config file
CONFIG = configparser.ConfigParser()
CONFIG.read(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'canarydc.ini'))

# create logger
logger = logging.getLogger('log')
logger.setLevel(logging.INFO)
# create a console handler that writes to stdout
CONSOLE_HANDLER = logging.StreamHandler()
CONSOLE_HANDLER.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
CONSOLE_HANDLER.setFormatter(formatter)
# clear the logger handers
del logger.handlers[:]

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
    mod = importlib.import_module('cdc.{}'.format(file))
    # append to all
    __all__.append(file)
