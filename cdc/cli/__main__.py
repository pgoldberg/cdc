"""Module that allows the CLI package to be run as a Python script"""
import os
import sys

# add outer directory to path so toplevel package can import
if not getattr(sys, 'frozen', False):
    sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import cdc
#from .application import main
from cdc.cli.application import main

# Launch CLI
main()
