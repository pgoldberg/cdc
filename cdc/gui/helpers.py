"""Helper functions for GUI"""
import os
import subprocess
import sys
import tkinter as tk
from tkinter import messagebox
from .. import config
from . import widgets

def populate_options(chosen_class, frame, label):
    """Populates the options (UC_PROPS) for the given class"""
    # destroy all of the widgets currently in the frame
    for widget in frame.winfo_children():
        widget.destroy()
    # create frames for input source/output location
    location_frame = tk.Frame(frame)
    location_frame.pack(side='top', pady=10, fill='x')
    # create scrollable options frame
    canvas_frame = tk.Frame(frame)
    canvas_frame.pack(side='top', padx=(15, 0), fill='both', expand=True)
    options_frame, _ = create_scrollable_frame(canvas_frame)
    # create options dictionary
    options = {}
    # create lists to store the input sources/output locations
    intypes = []
    outtypes = []
    # create label
    label_frame = tk.Frame(options_frame)
    label_frame.pack(side='top', fill='both', pady=(0, 10))
    tk.Label(label_frame,
             text='{} Options'.format(label),
             font=(None, 12)).pack(side='left', fill='both')
    # go through the UC_PROPS variable for the class
    for prop in chosen_class.UC_PROPS:
        # if it's an input source, add it to list and add var to options dict
        if 'intype' in prop:
            options[prop['var']] = None
            intypes.append(prop)
        # if it's an output source, add it to list
        elif 'outtype' in prop:
            options[prop['var']] = None
            outtypes.append(prop)
        # if there are choices, create a dropdown menu
        elif 'gui_choices' in prop or 'choices' in prop:
            widgets.DropDown(options_frame, prop, options).pack(side='top', fill='both', pady=10)
        # if it has a type, create entry object
        elif 'type' in prop:
            # if it's required, just make an entry with a label
            if prop['required']:
                widgets.EntryLabel(options_frame,
                           prop,
                           options).pack(side='top',
                                         fill='both',
                                         pady=10,
                                         padx=(0, 5))
            # if it's optional, add a checkbox to enable option
            else:
                widgets.EntryOption(options_frame,
                            prop,
                            options).pack(side='top',
                                          fill='both',
                                          padx=(0, 5))
        # if it is a boolean, just create a checkbox
        elif isinstance(prop['default'], bool):
            # create check button and add variable to options dictionary
            options[prop['var']] = tk.BooleanVar(value=prop['default'])
            check_frame = tk.Frame(options_frame)
            check_frame.pack(side='top', fill='both')
            tk.Checkbutton(check_frame,
                           text=prop['label'],
                           variable=options[prop['var']]).pack(side='left',
                                                               pady=10)
    # create input source/output location dropdown
    if intypes:
        widgets.SourceDropDown(location_frame, intypes, options, 'Input Source').pack(side='top')
    elif outtypes:
        widgets.SourceDropDown(location_frame, outtypes, options, 'Output Location').pack(side='top')
    # return the options dictionary
    return options

def validate_tab(Handler, options, handler_type):
    """Validates a tab's options"""
    # make sure a handler is provided
    if Handler is not None:
        # bool for if the user needs to enter an input/output source
        source = False
        # create list of options user needs to do
        todo = []
        # iterate through UC_PROPS for handler
        for prop in Handler.UC_PROPS:
            # if input source/output location, set source to True
            if 'intype' in prop or 'outtype' in prop:
                if options[prop['var']] is not None and options[prop['var']].get().strip() != '':
                    source = True
            # else if it's a required option, add it to todo
            elif prop['required']:
                if options[prop['var']] is None or options[prop['var']].get().strip() == '':
                    todo.append(prop['label'])
        # if no source provided, prepend it to todo (so it shows up first)
        if not source:
            if handler_type == 'reader':
                todo.insert(0, 'Input Source')
            elif handler_type == 'writer':
                todo.insert(0, 'Output Location')
        # if there's anything todo, create the message and show the error
        if todo:
            if len(todo) > 2:
                todo[-1] = 'and {}'.format(todo[-1])
                message = (', ').join(todo)
            else:
                message = ' and '.join(todo)
            messagebox.showerror('Error', 'Error: must enter {}.'.format(message))
            # return false because it is not complete
            return False
        # return True if it makes it through
        return True
    # if no handler, show error message to select in input/output format
    else:
        if handler_type == 'reader':
            messagebox.showerror('Error', 'Error: must select Input Format')
        elif handler_type == 'writer':
            messagebox.showerror('Error', 'Error: must select Output Format')
        # return false because it is not complete
        return False

def set_window(win, fun, width, height):
    """Set window size and close function"""
    # set minsize
    win.minsize(width=width, height=height)
    win.geometry('{}x{}'.format(width, height))
    # set window close function
    win.protocol("WM_DELETE_WINDOW", fun)

def create_scrollable_frame(parent):
    """Returns a canvas and a child frame that has a scrollbar"""
    # create canvas
    canvas = tk.Canvas(parent, highlightthickness=0)
    canvas.pack(side='left', fill='both', expand=True)
    # create frame
    scrollable_frame = tk.Frame(canvas)
    # create scrollbar
    scrollbar = tk.Scrollbar(parent, command=canvas.yview)
    scrollbar.pack(side='right', fill='y')
    #  create window with frame to make scrollable
    window = canvas.create_window((0, 0), window=scrollable_frame, anchor='nw')
    # add scrollbar set command to canvas
    canvas.configure(yscrollcommand=scrollbar.set)
    # function to scroll the canvas
    def scroll(event):
        """Configure scrolling"""
        # scroll the canvas
        canvas.configure(scrollregion=canvas.bbox('all'))
        canvas.itemconfig(window, width=event.width)
    # bind the configure event to the scroll function
    canvas.bind('<Configure>', scroll)
    # return scrollable frame and the canvas
    return scrollable_frame, canvas

def create_scrollable_listbox(parent):
    """Returns a listbox that has a scrollbar"""
    # create listbox and vertical/horizontal scrollbars
    # add scrollbars to parent frame so that they don't cover listbox
    listbox = tk.Listbox(parent, activestyle='none', selectmode='single')
    vert_scrollbar = tk.Scrollbar(parent)
    listbox.config(yscrollcommand=vert_scrollbar.set)
    vert_scrollbar.config(command=listbox.yview)
    vert_scrollbar.pack(side='right', fill='y')
    horiz_scrollbar = tk.Scrollbar(parent, orient='horizontal')
    listbox.config(xscrollcommand=horiz_scrollbar.set)
    horiz_scrollbar.config(command=listbox.xview)
    horiz_scrollbar.pack(side='bottom', fill='x')
    listbox.pack(side='top', fill='both', expand=True)
    # return listbox
    return listbox

def create_scrollable_textbox(parent):
    """Returns a listbox that has a scrollbar"""
    # create textbox and scrollbar
    text = tk.Text(parent, wrap='word', cursor='arrow', takefocus=0)
    scrollbar = tk.Scrollbar(text)
    text.config(yscrollcommand=scrollbar.set)
    scrollbar.config(command=text.yview)
    scrollbar.pack(side='right', fill='y')
    text.pack(side='left', fill='both', expand=True)
    # return textbox
    return text

def create_time_label(elapsed=None, complete=None, seconds=None):
    """Calculate time remaining and create label"""
    if seconds is not None:
        remaining = int(round(seconds))
    else:
        # calculate time remaining
        try:
            total = elapsed / complete
            remaining = int(total - elapsed)
        # catch ZeroDivisionError if no bytes have been processed
        except ZeroDivisionError:
            return ''
    # convert seconds to hours, minutes and seconds
    if remaining >= 3600:
        hours = int(remaining / 3600)
        minutes = int(round(remaining % 3600 / 60))
        if hours > 1:
            hour_label = '{} hours'.format(hours)
        else:
            hour_label = '1 hour'
        if minutes == 1:
            minute_label = '1 minute'
        else:
            minute_label = '{} minutes'.format(minutes)
        # return label
        return '{} and {} remaining'.format(hour_label, minute_label)
    # convert seconds to minutes and seconds
    elif remaining >= 60:
        minutes = int(remaining / 60)
        seconds = remaining % 60
        if minutes > 1:
            minute_label = '{} minutes'.format(minutes)
        else:
            minute_label = '1 minute'
        if seconds == 1:
            second_label = '1 second'
        else:
            second_label = '{} seconds'.format(seconds)
        # return label
        return '{} and {} remaining'.format(minute_label, second_label)
    # create seconds label
    else:
        if remaining == 1:
            second_label = '1 second'
        else:
            second_label = '{} seconds'.format(remaining)
        # return label
        return '{} remaining'.format(second_label)

def open_config():
    """Opens the config file"""
    # tell the user they'll have to restart the program
    messagebox.showinfo('Note', ('After editing the configuration file, you'
                                 ' must restart\nCanary Data Converter for '
                                 'all changes to take effect.'))
    # get the directory of the config file
    filedir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    # join the path with the filename
    filepath = os.path.join(filedir, 'canarydc.ini')

    # open it with default text editor based on the platform
    if sys.platform.startswith('darwin'):
        subprocess.call(('open', filepath))
    elif os.name == 'nt':
        os.startfile(filepath)
    elif os.name == 'posix':
        subprocess.call(('xdg-open', filepath))

def reset_config():
    """Resets config file to default"""
    # tell user they'll need to restart program
    messagebox.showinfo('Note', ('You must restart Canary Data Converter for '
                                 'all changes to take effect.'))
    config.create_config()

def validate_int(S, P):
    """Validates that an entry is an integer"""
    try:
        # make sure that it doesn't start with a zero
        if P[0] == '0':
            # ring computer bell
            # \a is the cross-platform alarm sound
            #print('\a', end='')
            return False
    except:
        pass
    # try to cast it as an int and make sure it works
    try:
        int(S)
        return True
    except ValueError:
        # if it doesn't work, ring bell and return False
        # \a is the cross-platform alarm sound
        #print('\a', end='')
        return False

def validate_float(S, P):
    """Validates that an entry is an integer"""
    try:
        # make sure that it doesn't start with a zero
        if P[0] == '0':
            # ring computer bell
            # \a is the cross-platform alarm sound
            #print('\a', end='')
            return False
    except:
        pass
    # try to cast it as a float and make sure it works
    try:
        float(S)
        return True
    except ValueError:
        # if it doesn't work, ring bell and return False
        # \a is the cross-platform alarm sound
        #print('\a', end='')
        return False
