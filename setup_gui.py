import struct
import sys
import os
from cx_Freeze import setup, Executable

if 'bdist_msi' in sys.argv:
    sys.argv += ['--initial-target-dir', r'[ProgramFilesFolder]Canary Data Converter']

PYTHON_64BIT_PATH = r"C:\\Program Files\\Python35"
PYTHON_32BIT_PATH = r"C:\\Users\\SX980\AppData\\Local\\Programs\\Python\\Python36-32\\"

cur_path = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(cur_path, 'cdc', 'resources', 'version.txt'), 'r') as vfile:
    version = vfile.read()

packages = ['cdc', 'cdc.write', 'cdc.read', 'cdc.gui', 'cdc.cli', 'cdc.utils']
includes = ['configparser', 'subprocess', 'tkinter']
excludes = ['build', 'dist', '.git', 'cdc\output', 'misc']

base = None
include_files = ['cdc\\']
if sys.platform == "win32":
    base = "Win32GUI"

if struct.calcsize("P") == 4:
    include_files += [os.path.join(PYTHON_32BIT_PATH, "DLLs", "tcl86t.dll"), os.path.join(PYTHON_32BIT_PATH, "DLLs", "tk86t.dll")]
    os.environ['TCL_LIBRARY'] = os.path.join(PYTHON_32BIT_PATH, "tcl", "tcl8.6")
    os.environ['TK_LIBRARY'] = os.path.join(PYTHON_32BIT_PATH, "tcl", "tk8.6")
else:
    include_files += [os.path.join(PYTHON_64BIT_PATH, "DLLs", "tcl86t.dll"), os.path.join(PYTHON_64BIT_PATH, "DLLs", "tk86t.dll")]
    os.environ['TCL_LIBRARY'] = os.path.join(PYTHON_64BIT_PATH, "tcl", "tcl8.6")
    os.environ['TK_LIBRARY'] = os.path.join(PYTHON_64BIT_PATH, "tcl", "tk8.6")

shortcut_table = [
    ("DesktopShortcut",        # Shortcut
     "DesktopFolder",          # Directory_
     "Canary Data Converter",     # Name
     "TARGETDIR",              # Component_
     "[TARGETDIR]CanaryDC.exe",   # Target
     None,                     # Arguments
     None,                     # Description
     None,                     # Hotkey
     None,                     # Icon
     None,                     # IconIndex
     None,                     # ShowCmd
     'TARGETDIR'               # WkDir
     ),
                  
    ("ProgramMenuShortcut",        # Shortcut
     "ProgramMenuFolder",          # Directory_
     "Canary Data Converter",     # Name
     "TARGETDIR",              # Component_
     "[TARGETDIR]CanaryDC.exe",   # Target
     None,                     # Arguments
     None,                     # Description
     None,                     # Hotkey
     None,                     # Icon
     None,                     # IconIndex
     None,                     # ShowCmd
     'TARGETDIR'               # WkDir
     ),

    ]

msi_data = {
    'Shortcut': shortcut_table
}

bdist_msi_options = {
    'data': msi_data,
    'initial_target_dir': r'[ProgramFilesFolder]Canary Data Converter'
}

setup(
    name = "Canary Data Converter",
    version = version,
    options = {"build_exe": {"includes": includes, "include_files": include_files, 'packages': packages, 'include_msvcr': True, 'excludes': excludes}, 'bdist_msi': bdist_msi_options},
    description = "cx_Freeze Tkinter script",
    executables = [
        Executable('cdc\gui\\__main__.py', base=base, targetName='CanaryDC.exe', icon='cdc\\resources\Canary.ico'),
        Executable('cdc\\cli\\__main__.py', base=None, targetName='CanaryDC-cli.exe', icon='cdc\\resources\Canary.ico')
    ]
)
