"""Tkinter widgets for GUI"""
import multiprocessing
import os
import queue
import time
import tkinter as tk
from tkinter import ttk, filedialog
import webbrowser
import cdc
from cdc import gui
from cdc.gui import helpers

class EntryOption(tk.Frame):
    """Optional entry with a checkbox that controls state of Entry widget"""
    def __init__(self, master, prop, options, *args, **kwargs):
        # call super constructor
        tk.Frame.__init__(self, master, *args, **kwargs)
        # create tkinter boolean var
        self.check = tk.BooleanVar()
        # store property info
        self.prop = prop
        # instantiate options dictionary entry
        options[self.prop['var']] = None

        # create entry and checkbutton with toggle_entry command
        self.entry = tk.Entry(self, state='disabled',)
        tk.Checkbutton(
            self,
            text=prop['label'],
            variable=self.check,
            command=lambda: self.toggle_entry(options)
        ).pack(side='left', pady=10, padx=(0, 20), fill='both')

        # if it has a default, set it to true and toggle entry
        if ('gui_default' in prop and prop['gui_default'] is not None) or prop['default'] is not None:
            self.check.set(True)
            self.toggle_entry(options)
            self.check.set(False)
            self.toggle_entry(options)

        # pack entry to frame
        self.entry.pack(side='left', fill='x', expand=True)

    def toggle_entry(self, options):
        """Disable entry if unchecked, enable entry if checked"""
        # disable entry if check isn't set
        if not self.check.get():
            self.entry.config(state='disabled', variable=None)
            options[self.prop['var']] = None
        # if check is set, enable entry
        else:
            if self.prop['type'] == str:
                # create tkinter var in options dict for value
                options[self.prop['var']] = tk.StringVar()
                # set default value
                if 'gui_default' in self.prop and self.prop['gui_default'] is not None:
                    options[self.prop['var']].set(self.prop['gui_default'])
                elif self.prop['default'] is not None:
                    options[self.prop['var']].set(self.prop['default'])
                else:
                    options[self.prop['var']].set("")

                # enable entry and set variable
                self.entry.config(state='normal', textvariable=options[self.prop['var']])

            elif self.prop['type'] == int:
                # create tkinter var in options dict for value
                options[self.prop['var']] = tk.IntVar()
                # set default value
                if 'gui_default' in self.prop and self.prop['gui_default'] is not None:
                    options[self.prop['var']].set(self.prop['gui_default'])
                elif self.prop['default'] is None:
                    options[self.prop['var']].set(1)
                else:
                    options[self.prop['var']].set(self.prop['default'])
                # enable entry and set variable
                self.entry.config(state='normal', textvariable=options[self.prop['var']])
                # validate integer entry
                vint = self.register(helpers.validate_int)
                self.entry.config(validate='key', validatecommand=(vint, '%S', '%P'))
            elif self.prop['type'] == float:
                # create tkinter var in options dict for value
                options[self.prop['var']] = tk.DoubleVar()
                # set default value
                if 'gui_default' in self.prop and self.prop['gui_default'] is not None:
                    options[self.prop['var']].set(self.prop['gui_default'])
                elif self.prop['default'] is None:
                    options[self.prop['var']].set(1.0)
                else:
                    options[self.prop['var']].set(self.prop['default'])
                # enable entry and set variable
                self.entry.config(state='normal', textvariable=options[self.prop['var']])
                # validate integer entry
                vfloat = self.register(helpers.validate_float)
                self.entry.config(validate='key', validatecommand=(vfloat, '%S', '%P'))

class DropDown(tk.Frame):
    """Dropdown for options with choices"""
    def __init__(self, master, prop, options, *args, **kwargs):
        # call frame super constructor
        tk.Frame.__init__(self, master, *args, **kwargs)
        # create tkinter var in options dict
        options[prop['var']] = tk.StringVar()
        if 'gui_default' in prop and prop['gui_default'] is not None:
            options[prop['var']].set(prop['gui_default'])
        elif prop['default'] is not None:
            options[prop['var']].set(prop['default'])
        # create label
        tk.Label(self, text=prop['label']).pack(side='left', padx=(0, 20))
        # get the choices for the dropdown
        if 'gui_choices' in prop:
            values = prop['gui_choices']
        elif 'choices' in prop:
            values = prop['choices']
        else:
            values = []
        # create combobox dropdown menu
        self.dropdown = ttk.Combobox(self, textvariable=options[prop['var']], values=values)
        self.dropdown.pack(side='left')

class EntryLabel(tk.Frame):
    """Just an Entry widget with a label"""
    def __init__(self, master, prop, options, *args, **kwargs):
        # call super constructor
        tk.Frame.__init__(self, master, *args, **kwargs)
        # add tkinter var to options dictionary
        options[prop['var']] = tk.StringVar()
        # create label and entry
        tk.Label(self, text=prop['label']).pack(side='left', padx=(0, 20))
        self.entry = ttk.Entry(self, textvariable=options[prop['var']])
        # set default
        if 'gui_default' in prop and prop['gui_default'] is not None:
            options[prop['var']].set(prop['gui_default'])
        elif prop['default'] is not None:
            options[prop['var']].set(value=prop['default'])
        # pack entry
        self.entry.pack(side='left', fill='x', expand=True)

class SourceDropDown(tk.Frame):
    """Dropdown for selecting an input/output source"""
    def __init__(self, master, intypes, options, type_str, *args, **kwargs):
        # call super constructor
        tk.Frame.__init__(self, master, *args, **kwargs)
        # create tkinter var for input/output source
        self.source = tk.StringVar()
        # create label and dropdown
        tk.Label(self, text='Select an {}:'.format(type_str)).pack(side='left', padx=(0, 20))
        self.menu = ttk.OptionMenu(self,
                                   self.source,
                                   'Select',
                                   *[intype['label'] for intype in intypes],
                                   command=(lambda choice: OpenFile(
                                       master,
                                       *[intype for intype in intypes
                                         if intype['label'] == choice],
                                       options
                                   ).pack(side='top', fill='x', expand=True)))
        self.menu.pack(side='left')

class OpenFile(tk.Frame):
    """Creates frame for opening a file or folder"""
    def __init__(self, master, prop, options, *args, **kwargs):
        # create variable for whether it's for input or output
        self.intype = 'intype' in prop
        # destroy any existing OpenFile widget
        for widget in master.winfo_children():
            if isinstance(widget, OpenFile):
                widget.destroy()
        # call super constructor
        tk.Frame.__init__(self, master, *args, **kwargs)

        # Set all input/output source paths to None
        for key in options.keys():
            #print(key)
            #if key.startswith('input') or key.startswith('output'):
            if key in ["input_dir_subdir", "input_dir", "input_file", "output_dir"]:
                options[key] = None

        # create tkinter variable for input/output source
        options[prop['var']] = tk.StringVar()
        
        # if it's an input source type
        if 'intype' in prop:
            # if it's a directory ADD OTHER INPUT TYPES HERE (I.E. DATABASE)
            if prop['intype'] == 'dir':
                # create entry and button
                entry = ttk.Entry(self, textvariable=options[prop['var']])
                entry.pack(side='left', padx=(10, 5), fill='x', expand=True)
                button = ttk.Button(self,
                                    text='Select Input Folder',
                                    command=(lambda: self.open_dir(
                                        options[prop['var']]
                                    )))
                button.pack(side='right', padx=(10, 5))
            # if it's a file ADD OTHER INPUT TYPES HERE (I.E. DATABASE)
            elif prop['intype'] == 'file':
                # create entry and button
                entry = ttk.Entry(self, textvariable=options[prop['var']])
                entry.pack(side='left', padx=(10, 5), fill='x', expand=True)
                button = ttk.Button(self,
                                    text='Select Input File',
                                    command=(lambda: self.open_file(
                                        options[prop['var']]
                                    )))
                button.pack(side='right', padx=(10, 5))
        # if it's an output location type
        elif 'outtype' in prop:
             # if it's a directory ADD OTHER OUTPUT TYPES HERE (I.E. DATABASE)
            if prop['outtype'] == 'dir':
                # create button and entry
                entry = ttk.Entry(self, textvariable=options[prop['var']])
                entry.pack(side='left', padx=(10, 5), fill='x', expand=True)
                button = ttk.Button(self,
                                    text='Select Output Folder',
                                    command=(lambda: self.open_dir(
                                        options[prop['var']]
                                    )))
                button.pack(side='right', padx=(10, 5))

    def open_dir(self, var):
        """Open a file dialog for opening a directory"""
        # create variable to store directory to open on
        initialdir = None
        # get last directory opened and set initialdir
        if self.intype:
            initialdir = gui.CONFIG.get('FILEDIALOG', 'indir', fallback=None)
        elif not self.intype:
            initialdir = gui.CONFIG.get('FILEDIALOG', 'outdir', fallback=None)
        # open file dialog
        dirpath = filedialog.askdirectory(initialdir=initialdir)
        # set variable to directory path
        var.set(dirpath)
        # add dirpath to gui config file
        if dirpath.strip() != '':
            if 'FILEDIALOG' not in gui.CONFIG:
                gui.CONFIG['FILEDIALOG'] = {}
            if self.intype:
                gui.CONFIG['FILEDIALOG']['indir'] = dirpath
            else:
                gui.CONFIG['FILEDIALOG']['outdir'] = dirpath
            # write it to the config file
            with open(gui.CONFIG_PATH, 'w') as configfile:
                gui.CONFIG.write(configfile)


    def open_file(self, var):
        """Open a file dialog for opening an individual file"""
         # create variable to store directory to open on
        initialdir = None
        # get last directory opened and set initialdir
        initialdir = gui.CONFIG.get('FILEDIALOG', 'indir', fallback=None)
        # open file dialog
        filepath = filedialog.askopenfilename(initialdir=initialdir)
        # set variable to directory path
        var.set(filepath)
        # add initialdir to gui config file
        if filepath.strip() != '':
            if 'FILEDIALOG' not in gui.CONFIG:
                gui.CONFIG['FILEDIALOG'] = {}
            gui.CONFIG['FILEDIALOG']['indir'] = os.path.dirname(os.path.abspath(filepath))
            # write it to the config file
            with open(gui.CONFIG_PATH, 'w') as configfile:
                gui.CONFIG.write(configfile)
