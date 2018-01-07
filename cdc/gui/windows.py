"""Windows for the GUI"""
import multiprocessing
import os
import tkinter as tk
from tkinter import ttk
import webbrowser
import cdc
from . import helpers
from .. import read, write

class HelpWindow(tk.Toplevel):
    """Contextual help window"""
    def __init__(self, master, help_type, info=None, *args, **kwargs):
        # call toplevel super constructor
        tk.Toplevel.__init__(self, master, *args, **kwargs)

        # set window title and icon
        self.wm_iconbitmap(os.path.join(cdc.cdc_dir, 'resources', 'Canary.ico'))
        self.wm_title('Help')
        
        # store the info to put in help window
        self.info = info

        # create logo
        logo = tk.Frame(self, bg='white')
        logo.pack(side='left', fill='y')
        photo = tk.PhotoImage(file=os.path.join(cdc.cdc_dir, 'resources', 'side_logo.gif'))
        photo = photo.subsample(1, 1)
        label = tk.Label(logo, image=photo, bg='white')
        label.image = photo
        label.pack(side='left')

        # create main frame for content
        self.main_frame = tk.Frame(self)

        # call function for outputting different types of help
        if help_type == 'option':
            self.option()
        elif help_type == 'reader':
            self.handler('input')
        elif help_type == 'writer':
            self.handler('output')
        elif help_type == 'conversion':
            self.conversion()

        # pack the main frame
        self.main_frame.pack(side='right', fill='both', expand=True)

        # create a button frame for opening full manual and closing window
        button_frame = tk.Frame(self.main_frame)
        ttk.Button(button_frame,
                  text='Open Full Manual',
                  command=lambda: webbrowser.open(
                      'file:///{}'.format(os.path.realpath(os.path.join(cdc.cdc_dir, 'resources', 'help.html')))
                      )).pack(side='right', padx=5)
        ttk.Button(button_frame, text='Close', command=self.destroy).pack(side='right')
        button_frame.pack(side='bottom', fill='both', ipady=5)

    def handler(self, handler_type):
        """Add handlers to help window"""
        # create subheader for handler title
        subheader = tk.Frame(self.main_frame)
        title_frame = tk.Frame(subheader)
        title_frame.pack(side='top', fill='x')
        desc_frame = tk.Frame(subheader)
        desc_frame.pack(side='top', fill='x')
        tk.Label(title_frame, text='Select an {} Format'.format(handler_type.title()), font=(None, 16)).pack(side='left')
        tk.Label(desc_frame, text='Select your {} format from the list of supported formats:'.format(handler_type)).pack(side='left')
        subheader.pack(side='top', fill='x', pady=10)

        # create a scrollable textbox to display options
        scroll_frame = tk.Frame(self.main_frame)
        scroll_frame.pack(side='top', fill='both', expand=True)
        text = helpers.create_scrollable_textbox(scroll_frame)

        # create fonts for format names and descriptions
        text.tag_configure('name', font=('Helvetica', 10, 'bold'), rmargin=20)
        text.tag_configure('desc', font=('Helvetica', 10), rmargin=20)

        # iterate over the info and add the descriptions
        for item in self.info.keys():
            text.insert('end', '{}: '.format(item), 'name')
            text.insert('end', '{}\n\n'.format(self.info[item].DESCRIPTION), 'desc')

        # disable textbox so the user can't edit the it
        # note: you must reset state to 'normal' before adding more to textbox
        text.config(state='disabled')

    def option(self):
        """Add options to help window"""
        # create lists for the sources and options
        sources = []
        options = []

        # create bools to figure out if it's input or output options
        intype = False
        outtype = False

        # iterate over info
        for item in self.info:
            # check if it's a source and whether it's input or output
            if 'intype' in item:
                # add to sources and set intype bool
                sources.append(item)
                intype = True
            elif 'outtype' in item:
                # add to sources and set outtype bool
                sources.append(item)
                outtype = True
            else:
                # add to options dict if not an input/output source
                options.append(item)

        # if it's input or output options
        if intype or outtype:
            # create a subheader and labels
            subheader = tk.Frame(self.main_frame)
            title_frame = tk.Frame(subheader)
            desc_frame = tk.Frame(subheader)

            # add label and input type based on if it's input or output options
            if intype:
                tk.Label(title_frame, text='Select an input source', font=(None, 16)).pack(side='left')
                tk.Label(desc_frame, text='Choose where to read the documents from').pack(side='left')
            elif outtype:
                tk.Label(title_frame, text='Select an output location', font=(None, 16)).pack(side='left')
                tk.Label(desc_frame, text='Choose where to write the documents to').pack(side='left')

            # add everything to gui
            title_frame.pack(side='top', fill='x')
            desc_frame.pack(side='top', fill='x')
            subheader.pack(side='top', fill='x', pady=10)

            # create labels for the sources
            self.labelize(sources)

        # if there are options
        if options:
            # create subheader for options
            subheader = tk.Frame(self.main_frame)
            title_frame = tk.Frame(subheader)
            title_frame.pack(side='top', fill='x')
            desc_frame = tk.Frame(subheader)
            desc_frame.pack(side='top', fill='x')

            # add label text depending on whether inptu/output options
            if intype:
                tk.Label(title_frame, text='Input Options', font=(None, 16)).pack(side='left')
                tk.Label(desc_frame, text='Options for reading in documents').pack(side='left')
            elif outtype:
                tk.Label(title_frame, text='Output Options', font=(None, 16)).pack(side='left')
                tk.Label(desc_frame, text='Options for writing documents').pack(side='left')

            # add subheader to GUI
            subheader.pack(side='top', fill='x', pady=10)

            # create labels for options
            self.labelize(options)
    
    def conversion(self):
        """Add conversion options to help window"""
        # create subheader with labels for conversion options and description
        subheader = tk.Frame(self.main_frame)
        title_frame = tk.Frame(subheader)
        title_frame.pack(side='top', fill='x')
        desc_frame = tk.Frame(subheader)
        desc_frame.pack(side='top', fill='x')
        tk.Label(title_frame, text='Conversion Options', font=(None, 16)).pack(side='left')
        tk.Label(desc_frame, text='Options for running conversion').pack(side='left')

        # get number of cores to display recommended number of processes
        cpus = multiprocessing.cpu_count()
        if cpus > 1:
            cpus -= 1

        # create an options list to call the labelize method
        options = [
            {
                'label': 'Number of Files to Process at a Time',
                'help': 'Choose the number of files to process at once. The default (recommended) number is one fewer file than the total number of CPU cores on your machine. For you, that number is {}.'.format(cpus)
            }
        ]

        # add subheader to GUI
        subheader.pack(side='top', fill='x', pady=10)

        # create labels for options
        self.labelize(options)

    def labelize(self, lst):
        """Create scrollable textbox for options"""
        # create scrollable textbox
        scroll_frame = tk.Frame(self.main_frame)
        scroll_frame.pack(side='top', fill='both', expand=True)
        text = helpers.create_scrollable_textbox(scroll_frame)

        # create fonts for options
        text.tag_configure('bold', font=('Helvetica', 10, 'bold'), rmargin=20)
        text.tag_configure('desc', font=('Helvetica', 10), rmargin=20)

        # iterate over list and add names and descriptions
        for item in lst:
            text.insert('end', '{}: '.format(item['label']), 'bold')
            if 'gui_help' in item:
                text.insert('end', '{}\n'.format(item['gui_help']), 'desc')
            else:
                text.insert('end', '{}\n'.format(item['help']), 'desc')

        # disable textbox so the user can't edit the it
        # note: you must reset state to 'normal' before adding more to textbox
        text.config(state='disabled')


class AboutWindow(tk.Toplevel):
    """About window"""
    def __init__(self, master, *args, **kwargs):
        # call super constructor
        tk.Toplevel.__init__(self, master, *args, **kwargs)

        # add icon and title to window
        self.wm_iconbitmap(os.path.join(cdc.cdc_dir, 'resources', 'Canary.ico'))
        self.wm_title('About')

        # add logo
        logo = tk.Frame(self, bg='white')
        logo.pack(side='left', fill='both')
        photo = tk.PhotoImage(file=os.path.join(cdc.cdc_dir, 'resources', 'side_logo.gif'))
        photo = photo.subsample(1, 1)
        label = tk.Label(logo, image=photo, bg='white')
        label.image = photo
        label.pack(side='left')

        # create main frame
        main_frame = tk.Frame(self)
        main_frame.pack(side='right', fill='both', expand=True)

        # create header
        header = tk.Frame(main_frame)
        header.pack(side='top', fill='x')

        # add title to header
        title_frame = tk.Frame(header)
        title = tk.Label(title_frame,
                         text='Canary Data Converter',
                         font=(None, 16))

        # pack title
        title.pack(side='left')
        title_frame.pack(side='top', fill='both', expand=True)

        # create version label
        ver_frame = tk.Frame(header)
        ver_label = tk.Label(ver_frame,
                             text='Version {}'.format(cdc.__version__))

        # pack version label
        ver_label.pack(side='left')
        ver_frame.pack(side='top', fill='both', expand=True)

        # create link
        link_frame = tk.Frame(header)
        link = tk.Label(link_frame, text='canary.bwh.harvard.edu', cursor='hand1')

        # bind click to opening link (this is how to make hyperlink in tkinter)
        link.bind('<Button-1>',
                  lambda _: webbrowser.open(
                      'http://canary.bwh.harvard.edu'
                  ))

        # pack link
        link.pack(side='left')
        link_frame.pack(side='top', fill='both', expand=True)

        # read about text file
        with open(os.path.join(cdc.cdc_dir, 'resources', 'about.txt'), 'r') as about_file:
            about_text = about_file.read()

        # add system info
        about_text += "\n---\n%s" % (cdc.os_string)

        # create textbox and add text from file
        text = helpers.create_scrollable_textbox(main_frame)
        text.insert('end', about_text)

        # disable textbox so the user can't edit the it
        # note: you must reset state to 'normal' before adding more to textbox
        text.config(state='disabled')
