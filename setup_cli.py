import os
from setuptools import setup

cur_path = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(cur_path, 'cdc', 'resources', 'version.txt'), 'r') as vfile:
    version = vfile.read()
 
setup(
    name = "Canary Data Converter",
    packages = ["cdc", "cdc.cli", "cdc.read", "cdc.write", "cdc.gui", "cdc.utils"],
    entry_points = {
        "console_scripts": ['canarydc = cdc.cli.application:main']
        },
    description = "Canary Data Converter",
    author = "Peter Goldberg",
    author_email = "canary@bwh.harvard.edu",
    url = "http://canary.bwh.harvard.edu",
    include_package_data=True,
    package_data = {
        'cdc': ['canarydc.ini', 'resources\\*']
    },
    version = version
    )