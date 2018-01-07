"""Module that allows the gui package to be run as a python script"""
import os
import sys
# add outer directory to path (if not frozen) so toplevel package can import
if not getattr(sys, 'frozen', False):
    sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
import cdc
from cdc import gui
from cdc.gui.application import main, start_gui

# if user wants logging, add logger - this is really for testing
if '--log' in sys.argv and cdc.CONSOLE_HANDLER not in gui.LOGGER.handlers:
    gui.LOGGER.addHandler(cdc.CONSOLE_HANDLER)
# if the user doesn't want the logs, clear the handlers
elif '--log' not in sys.argv:
    del gui.LOGGER.handlers[:]

# call the main function to launch GUI
start_gui(*main())
