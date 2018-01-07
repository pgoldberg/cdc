"""Graphical User Interface"""
import datetime
import multiprocessing
import os
import queue
import subprocess
import sys
import tkinter as tk
from tkinter import messagebox, ttk
import webbrowser
# add to sys.path to make sure imports work if not frozen to .exe
if not getattr(sys, 'frozen', False):
    sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__)
    ))))
import cdc
from .. import gui, read, write
from . import helpers, progress, windows
from ..convert import ConversionThread

TIME_FORMAT = cdc.CONFIG.get('GUI', 'gui_log_timestamp', fallback='%H:%M:%S - %m-%d-%Y')

class MainApplication(tk.Frame):
    """Main GUI Window"""
    def __init__(self, parent, *args, **kwargs):
        # call super constructor
        tk.Frame.__init__(self, parent, *args, **kwargs)

        # set theme
        self.style = ttk.Style()
        self.style.theme_use('clam')
        # create green progress bars
        self.style.configure('green.Horizontal.TProgressbar',
                             foreground='green',
                             background='green')

        # set parent widget
        self.parent = parent

        # set window title and icon
        self.parent.title('Canary Data Converter v{}'.format(cdc.__version__))
        self.parent.wm_iconbitmap(os.path.join(cdc.cdc_dir, 'resources', 'Canary.ico'))

        #create header
        header = tk.Frame(self.parent, bg='white')
        header.grid(row=0, sticky='nsew')
        photo = tk.PhotoImage(file=os.path.join(cdc.cdc_dir, 'resources', 'logo.gif'))
        photo = photo.subsample(1, 1)
        label = tk.Label(header, image=photo, bg='white')
        label.image = photo
        label.pack(side='left')

        # indicate if running or window closed
        self.closed = False
        self.running = False
        self.joining_logthread = False

        # track the amount of errors, warnings and completed files
        self.error_count = 0
        self.warning_count = 0
        self.completed_count = 0

        # variable for about and help windows so only one can be open at a time
        self.about = None
        self.help = None

        # conversion thread and queue for communicating with thread
        self.conversion = None
        self.comm = None

        # create list for progress objects
        self.progressbars = []

        # create options dictionary
        self.options = {}

        # create main notebook (tabs at the top)
        self.note = ttk.Notebook(self.parent)
        self.input = tk.Frame(self.note)
        self.w_optiontab = tk.Frame(self.note)
        self.convert = tk.Frame(self.note)
        self.note.add(self.input, text='Input')
        self.note.add(self.w_optiontab, text='Output', state='disabled')
        self.note.add(self.convert, text='Convert', state='disabled')

        # create convert tab notebook
        self.convert_notebook = ttk.Notebook(self.convert)
        self.convert_notebook.pack(side='top', fill='both', expand=True)
        self.conversion_tab = tk.Frame(self.convert_notebook)
        self.queue_tab = tk.Frame(self.convert_notebook)
        self.completed_tab = tk.Frame(self.convert_notebook)
        self.warnings_tab = tk.Frame(self.convert_notebook)
        self.errors_tab = tk.Frame(self.convert_notebook)
        self.convert_notebook.add(self.conversion_tab, text='Conversion')
        self.convert_notebook.add(self.queue_tab, text='Queue')
        self.convert_notebook.add(self.completed_tab, text='Completed')
        self.convert_notebook.add(self.warnings_tab, text='Warnings')
        self.convert_notebook.add(self.errors_tab, text='Errors')

        # create frame for conversion options and populate it
        self.conv_options = {}
        self.convert_options = tk.Frame(self.conversion_tab)
        self.convert_options.pack(side='top')
        self.populate_convert_options()

        # create frame for overall progress and instantiate OverallProgress
        self.overall_progress_frame = tk.Frame(self.conversion_tab)
        self.overall_progress_frame.pack(side='top', fill='both', expand=True)
        self.overall_progress = None

        # create frame for the progress objects
        self.progress_canvas_frame = tk.Frame(self.conversion_tab)
        self.progress_canvas_frame.pack(side='top', fill='both', expand=True)
        self.progress_frame, self.progress_canvas = helpers.create_scrollable_frame(
            self.progress_canvas_frame
        )

        # create queue tab listbox and button
        queue_frame = tk.Frame(self.queue_tab)
        queue_listbox_frame = tk.Frame(queue_frame)
        self.queue_listbox = helpers.create_scrollable_listbox(
            queue_listbox_frame
        )
        queue_listbox_frame.pack(side='top', fill='both', expand=True)
        queue_button_frame = tk.Frame(queue_frame)
        self.clear_queue_button = ttk.Button(queue_button_frame,
                                             text='Clear Queue',
                                             command=self.clear_queue)
        self.clear_queue_button.pack(side='right', padx=2, pady=2)
        queue_button_frame.pack(side='bottom', fill='both')
        queue_frame.pack(side='top', fill='both', expand=True)

        # create listboxes for conversion tabs
        self.completed_listbox = helpers.create_scrollable_listbox(
            self.completed_tab
        )
        self.warnings_listbox = helpers.create_scrollable_listbox(
            self.warnings_tab
        )
        self.errors_listbox = helpers.create_scrollable_listbox(
            self.errors_tab
        )

        # create dictionary of conversion tabs for the progress objects
        self.conversion_tabs = {
            'notebook': self.convert_notebook,
            'progress_tab': self.conversion_tab,
            'queue_tab': self.queue_tab,
            'completed_tab': self.completed_tab,
            'errors_tab': self.errors_tab,
            'warnings_tab': self.warnings_tab,
            'progress': self.progress_frame,
            'queue': self.queue_listbox,
            'completed': self.completed_listbox,
            'warnings': self.warnings_listbox,
            'errors': self.errors_listbox,
            'progress_canvas': self.progress_canvas
        }

        # instance variables for reader and reader options
        self.Reader = None
        self.r_options = {}

        # get the reader classes
        self.reader_keys = read.GUI_KEYS

        # create dropdown for selecting input format
        self.reader = tk.StringVar()
        input_select = tk.Frame(self.input)
        input_select.pack(side='top')
        input_label = tk.Label(input_select, text='Select an Input Format:')
        input_label.pack(side='left', padx=(0, 20))
        input_menu = ttk.OptionMenu(input_select,
                                    self.reader, 'Select',
                                    *sorted(self.reader_keys.keys()),
                                    command=(lambda _: self.populate_input()))
        input_menu.pack(side='left')

        #create frame for the input options
        self.input_options = tk.Frame(self.input)
        self.input_options.pack(side='bottom', fill='both', expand=True)

        # instance variables for writer and writer options
        self.Writer = None
        self.w_options = {}

        # get the writer classes
        self.writer_keys = write.GUI_KEYS

        #create dropdown for selecting output format
        self.writer = tk.StringVar()
        output_select = tk.Frame(self.w_optiontab)
        output_select.pack(side='top')
        output_label = tk.Label(output_select, text='Select an Output Format:')
        output_label.pack(side='left', padx=(0, 20))
        output_menu = ttk.OptionMenu(output_select,
                                     self.writer, 'Select',
                                     *sorted(self.writer_keys.keys()),
                                     command=(lambda _: self.populate_output()))
        output_menu.pack(side='left')

        # create the frame for output options
        self.output_options = tk.Frame(self.w_optiontab)
        self.output_options.pack(side='bottom', fill='both', expand=True)

        # add notebook to the window with the grid geometry manager
        self.note.grid(row=1, sticky='nsew')

        # create menubar and add it to window
        menubar = tk.Menu(self.parent)
        filemenu = tk.Menu(menubar, tearoff=0)
        filemenu.add_command(label="Open Configuration File",
                             command=helpers.open_config)
        filemenu.add_command(label="Reset Configuration File",
                             command=helpers.reset_config)
        filemenu.add_command(label="Exit", command=self.close)
        menubar.add_cascade(label="File", menu=filemenu)
        helpmenu = tk.Menu(menubar, tearoff=0)
        helpmenu.add_command(label="Help", command=self.open_help)
        helpmenu.add_command(label="Open Manual",
                             command=lambda: webbrowser.open(
                                 'file:///{}'.format(
                                     os.path.realpath(os.path.join(cdc.cdc_dir, 'resources', 'help.html'))
                                 )
                             ))
        helpmenu.add_command(label="About", command=self.open_about)
        menubar.add_cascade(label="Help", menu=helpmenu)
        self.parent.config(menu=menubar)

        # create navbar at the bottom and the next/previous buttons
        self.nav = tk.Frame(self.parent)
        self.nav.grid(row=2, sticky='nsew', ipady=5)
        self.nextbutton = ttk.Button(self.nav,
                                     text='Next',
                                     command=self.nexttab)
        self.nextbutton.pack(side='right', padx=5)
        self.prevbutton = ttk.Button(self.nav,
                                     text='Previous',
                                     command=self.prevtab)
        self.prevbutton.pack(side='right')

        # create butons for opening help, output location, and log
        self.helpbutton = ttk.Button(self.nav,
                                     text='Help',
                                     command=self.open_help)
        self.helpbutton.pack(side='left', padx=5)
        self.destbutton = ttk.Button(self.nav,
                                     text='Open Output Location',
                                     command=self.open_dest)
        self.logbutton = ttk.Button(self.nav,
                                    text='Open Log',
                                    command=self.open_logs)

        # create instance variable to store log location
        self.log_location = None

        # update the buttons whenever the tab changes
        self.note.bind('<<NotebookTabChanged>>',
                       lambda _: self.update_buttons())

        # add weight to the grid cell for the main notebook so it resizes
        tk.Grid.rowconfigure(self.parent, 1, weight=1)
        tk.Grid.columnconfigure(self.parent, 0, weight=1)

    def open_dest(self):
        """Open output destination"""
        # if the output location is a directory, open it directory
        if ('output_dir' in self.w_options
                and self.w_options['output_dir'].get() != ''
                and os.path.isdir(self.w_options['output_dir'].get())):
            # webbrowser.open will open in platform's file explorer
            webbrowser.open(self.w_options['output_dir'].get())
        # popup error if can't open output destination
        else:
            messagebox.showerror('Error', 'Could not open output location.')

    def open_about(self):
        """Opens the about window"""
        # only open if self.about is None so only one is open at a time
        if self.about is None:
            # instantiate about window and set the window size with set_window
            self.about = windows.AboutWindow(self.parent)
            min_h = cdc.CONFIG.getint('GUI', 'about_min_height', fallback=360)
            min_w = cdc.CONFIG.getint('GUI', 'about_min_width', fallback=460)
            helpers.set_window(self.about, self.close_about, min_w, min_h)

            # grab_set makes it a modal dialog
            self.about.grab_set()

    def close_about(self):
        """Closes the about window"""
        # close about and set self.about to None so it can be opened again
        self.about.destroy()
        self.about = None

    def populate_convert_options(self):
        """Populates the conversion options"""
        # get number of cores
        cpus = multiprocessing.cpu_count()

        # if it's one, the user won't really have a choice
        if cpus == 1:
            self.conv_options['processes'] = tk.IntVar(value=1)
        # otherwise let them do number of cores minus 1
        else:
            self.conv_options['processes'] = tk.IntVar(value=cpus - 1)
        
        # register validation function
        vint = self.register(helpers.validate_int)
        
        # create the label and combo box
        tk.Label(
            self.convert_options,
            text='Select Number of Files to Process at a Time: '
        ).pack(side='left')
        process_menu = ttk.Combobox(self.convert_options,
                                    textvariable=self.conv_options['processes'],
                                    values=list(range(1, cpus + 1)),
                                    width=3,
                                    validate='key',
                                    validatecommand=(vint, '%S', '%P'))
        process_menu.pack(side='left')

        # add a separator to keep this separate from progress
        tk.Frame(self.conversion_tab,
                 relief='ridge',
                 height=3,
                 bg='#a6a9ad').pack(side='top', fill='x', pady=(4, 0))

    def nexttab(self):
        """Moves focus to the next tab in main notebook"""
        # get index of current tab
        cur_tab = self.note.index(self.note.select())

        # if on first tab, validate input options
        if cur_tab == 0:
            if helpers.validate_tab(self.Reader, self.r_options, 'reader'):
                # if options are valid, enable convert tab
                self.note.tab(self.w_optiontab, state='normal')
        # if on second tab, validate output options
        elif cur_tab == 1:
            if helpers.validate_tab(self.Writer, self.w_options, 'writer'):
                # if options are valid, enable convert tab
                self.note.tab(self.convert, state='normal')

        # go to next tab (won't work if tab is disabled)
        self.note.select(cur_tab + 1)

    def prevtab(self):
        """Moves focus to the previous tab in main notebook"""
        # get current tab index and go to the next one
        cur_tab = self.note.index(self.note.select())
        self.note.select(cur_tab - 1)

    def update_buttons(self):
        """Updates buttons based on context"""
        # if the conversion is running, pack Open Destination/Open Log buttons
        if self.running:
            self.destbutton.pack(side='left', padx=5)
            
            # only pack Open Log button if config file logfile option is True
            if cdc.CONFIG.getboolean('MAIN', 'create_logfile', fallback=True):
                self.logbutton.pack(side='left', padx=5)
        
        # get tab index
        cur_tab = self.note.index(self.note.select())
        
        # if on the second tab and conversion not running, validate first tab
        if cur_tab == 1 and not self.running:
            if not helpers.validate_tab(self.Reader, self.r_options, 'reader'):
                self.note.select(0)
                cur_tab = 0
        # if on third tab, change next button to Convert if running else Cancel
        elif cur_tab == 2:
            if self.joining_logthread:
                self.nextbutton.config(state='disabled')
            elif not self.running:
                self.nextbutton.config(text='Convert',
                                       command=self.run,
                                       state='normal')
            else:
                self.nextbutton.config(text='Cancel All', command=self.cancel)
            # return if on this tab so next button doesn't change commands
            return
        
        # set next button to go to next tab
        self.nextbutton.config(text='Next',
                               command=self.nexttab,
                               state='normal')
        
        # disable previous button if on first tab
        if cur_tab == 0:
            self.prevbutton.config(state='disabled')
        else:
            self.prevbutton.config(state='normal')

    def open_help(self):
        """Opens help window or HTML if there is no contextual help"""
        # close help if it's open
        if self.help is not None:
            self.close_help()
        
        # get current tab index
        cur_tab = self.note.index(self.note.select())
        if cur_tab == 0:
            # if user has selected reader, show explanation of options
            if self.Reader is not None:
                self.help = windows.HelpWindow(self,
                                               'option',
                                               self.Reader.UC_PROPS)
            # if user hasn't selected reader, show readers and descriptions
            else:
                self.help = windows.HelpWindow(self,
                                               'reader',
                                               self.reader_keys)
        elif cur_tab == 1:
            # if user has selected writer, show explanation of options
            if self.Writer is not None:
                self.help = windows.HelpWindow(self,
                                               'option',
                                               self.Writer.UC_PROPS)
            # if user hasn't selected writer, show writers and descriptions
            else:
                self.help = windows.HelpWindow(self,
                                               'writer',
                                               self.writer_keys)
        elif cur_tab == 2:
            # show conversion option help if on the 3rd tab
            self.help = windows.HelpWindow(self, 'conversion')
        
        # set the help window size with set_window
        min_h = cdc.CONFIG.getint('GUI', 'help_min_height', fallback=500)
        min_w = cdc.CONFIG.getint('GUI', 'help_min_width', fallback=540)
        helpers.set_window(self.help, self.close_help, min_w, min_h)

    def close_help(self):
        """Closes contextual help window"""
        # close help and set self.help to None so it can be opened again
        self.help.destroy()
        self.help = None

    def clear_queue(self):
        """Clears the queued files"""
        # disable the button
        self.clear_queue_button.config(state='disabled',
                                       text='Clearing Queue...')
        # if there is a conversion job running, clear the queue
        if self.conversion is not None:
            # iterate over waiting workers
            for worker in self.conversion.workers:
                # lower overall maximum bytes to not include cancelled workers
                if self.overall_progress is not None:
                    self.overall_progress.maximum -= worker['info']['metadata']['size']
               
                # log cancellation
                message = '{} | CANCELLED - {}'.format(datetime.datetime.now().strftime(TIME_FORMAT), worker['info']['metadata']['filename'])
                self.completed_listbox.insert('end', message)
                message = 'CANCELLED - {}'.format(
                    worker['info']['metadata']['filename']
                )
                gui.LOGGER.info(message)
            
            # reset overall progressbar maximum
            if self.overall_progress is not None:
                self.overall_progress.progressbar.config(
                    maximum=self.overall_progress.maximum
                )
           
            # clear the waiting workers list
            del self.conversion.workers[:]
           
            # clear queue listbox in GUI and update numbers on tabs
            self.queue_listbox.delete(0, 'end')
            self.convert_notebook.tab(self.queue_tab, text='Queue')
            amt_completed = self.completed_listbox.size()
            if amt_completed > 0:
                self.convert_notebook.tab(self.completed_tab,
                                          text='Completed ({})'.format(
                                              amt_completed
                                          ))
            
            # log that the queue was cleared
            gui.LOGGER.info('Cleared queue')

        # if there isn't a running conversion, say the queue is empty
        else:
            gui.LOGGER.warning('Queue is empty, could not clear it')
       
        # re-enable the button
        self.clear_queue_button.config(state='normal', text='Clear Queue')

    def cancel(self, close=False):
        """Cancels all conversion processes"""
        # disable the button
        self.nextbutton.config(text='Cancelling...', state='disabled')
        if self.conversion is not None:
            workers = list(self.conversion.running_workers) + list(self.conversion.workers)
            
            # cancel the conversion
            self.conversion.cancel()
            
            # log the cancellation
            for worker in workers:
                message = 'CANCELLED - {}'.format(worker['info']['metadata']['filename'])
                self.completed_listbox.insert('end', '{} | {}'.format(datetime.datetime.now().strftime(TIME_FORMAT), message))
            
            # delete all of the Progress instances
            for job in self.progressbars:
                job.pack_forget()
                job.update_files_left()
            
            # log the program finish messages
            self.log_finish(workers=workers)
        
        # remove the overall progress widget from GUI and reset it
        if self.overall_progress is not None:
            self.overall_progress.pack_forget()
        self.overall_progress = None
        
        # clear queue
        self.queue_listbox.delete(0, 'end')
        self.convert_notebook.tab(self.queue_tab, text='Queue')
        
        # set running variable to false
        self.running = False
        
        # if the window was closed, close the window
        if close:
            self.parent.destroy()
        # if not, prepare for another conversion
        else:
            if self.conversion is not None:
                del(self.conversion)
                self.conversion = None
            del(self.comm)
            self.comm = None
            self.update_buttons()

    def populate_input(self):
        """Populates the input options"""
        # set the self.Reader variable and populate options after selection
        self.Reader = self.reader_keys[self.reader.get()]
        self.r_options = helpers.populate_options(self.Reader,
                                                  self.input_options,
                                                  'Input')

    def populate_output(self):
        """Populates output options"""
        # set the self.Writer variable and populate options after selection
        self.Writer = self.writer_keys[self.writer.get()]
        self.w_options = helpers.populate_options(self.Writer,
                                                  self.output_options,
                                                  'Output')

    def run(self):
        """Starts the conversion"""
        # make sure all options are valid
        if not helpers.validate_tab(self.Reader, self.r_options, 'reader'):
            self.note.select(0)
        elif not helpers.validate_tab(self.Writer, self.w_options, 'writer'):
            self.note.select(1)
        # if they are valid, run the conversion
        else:
            try:
                self.conv_options['processes'].get()
            except:
                messagebox.showerror('Error', 'Must enter a number of processes.')
                return

            # set running to True, update buttons
            self.running = True
            self.update_buttons()

            # create overall_progress, pack it to the GUI
            self.overall_progress = progress.OverallProgress(
                self.overall_progress_frame
            )
            self.overall_progress.pack(side='top', fill='x', expand=True)

            # pack the progress frame
            self.progress_canvas_frame.pack(side='top',
                                            fill='both',
                                            expand=True)

            # copy options dictionary - very important
            options = dict(self.options)

            # add the reading and writing options to the dictionary
            options.update({**self.r_options,
                            **self.w_options,
                            **self.conv_options})
                            
            # extract all of the values from the tkinter variables
            tkinter_vars = (tk.StringVar,
                            tk.IntVar,
                            tk.BooleanVar,
                            tk.DoubleVar)
            for key, value in options.items():
                #print(key, value)
                if isinstance(value, tkinter_vars):
                    options[key] = value.get()

            # create communication queue
            self.comm = queue.Queue()

            # instantiate the conversion thread with catchall try/except
            try:
                self.conversion = ConversionThread(options,
                                                   self.Reader,
                                                   self.Writer,
                                                   self.comm)
            except SystemExit:
            	self.check_comm()
            	return
            except:
                # Report unhandled exceptions
                error = traceback.format_exc()
                excp = sys.exc_info()[1]

                message = 'There was an unhandled error while initiating the conversion:\n\n' + str(error) + "\n\n" + str(excp)
                messagebox.showerror('Error', message)
                gui.LOGGER.error(message)
                
                self.check_comm()
                self.callback(calcelled=True)
                return

            # store log location
            self.log_location = self.conversion.log_location

            # log interface, version, and os information
            gui.LOGGER.info('Canary Data Converter v{}'.format(cdc.__version__))
            gui.LOGGER.info('Running on Graphical User Interface')
            gui.LOGGER.info(cdc.os_string)

            # set start time for overall progress
            self.overall_progress.set_time()

            # spawn the conversion thread and start checking communication queue
            try:
                self.conversion.start()
                self.check_comm()
            # if an error is thrown, show a popup
            except:
                self.running = False
                self.update_buttons()
                message = 'There was an error while converting.'
                messagebox.showerror('Error', message)
                gui.LOGGER.error(message)
    
    def log_finish(self, process_time=None, workers=None):
        """Waits for all of the log_threads in the Progress objects to finish"""
        self.joining_logthread = True
        self.update_buttons()

        # destroy Progress objects and clear progressbar list
        for job in self.progressbars:
            if job.log_thread is not None and job.log_thread.is_alive():
                self.after(100, lambda: self.log_finish(process_time, workers))
                return
            else:
                job.update_files_left()
                job.destroy()
        del self.progressbars[:]

        if workers is not None:
            # log cancellation for queued items
            for worker in workers:
                message = 'CANCELLED - {}'.format(worker['info']['metadata']['filename'])
                gui.LOGGER.info(message)
        else:
            gui.LOGGER.info('FINISHED')

            if process_time is not None:
                time = helpers.create_time_label(seconds=process_time)
                time = time.replace(' remaining', '')
                gui.LOGGER.info('Processing Time: {}'.format(time))
        
        # close and remove handlers
        for handler in gui.LOGGER.handlers:
            if handler != cdc.CONSOLE_HANDLER:
                handler.close()
                gui.LOGGER.removeHandler(handler)

        self.joining_logthread = False
        self.update_buttons()

    def callback(self, cancelled=False, error_message=None, process_time=None):
        """Callback function for after the conversion is complete"""
        # set running variable to False and log the finished messages
        self.running = False

        # get the number of errors, warnings, and completed files
        errors = self.errors_listbox.size()
        completed = self.completed_listbox.size()
        warnings = self.warnings_listbox.size()
        new_errors = errors - self.error_count
        new_completed = completed - self.completed_count
        new_warnings = warnings - self.warning_count
        if not cancelled:
            self.nextbutton.config(text='Finishing...')
            self.log_finish(process_time)

            # show the approprate popup window based on errors and warnings
            if (errors - self.error_count > 0
                    and new_errors == new_completed):
                message = ('Canary Data Converter encountered errors while '
                           'processing and was unable to successfully process '
                           'your files. See the log for more information.')
                messagebox.showerror('Error', message)
            elif new_errors > 0:
                message = ('Canary Data Converter has processed your files, '
                           'although some had errors and were unable to be '
                           'processed. See the log for more information.')
                messagebox.showerror('Finished With Errors', message)
            elif new_warnings > 0:
                message = ('Canary Data Converter has processed your files, '
                           'although it encountered warnings while processing.')
                messagebox.showwarning('Finished With Warnings', message)
            else:
                message = 'The converter has finished processing your files.'
                messagebox.showinfo('Finished', message)
        else:
            # show error if there was one
            if error_message is not None:
                messagebox.showerror('Error', error_message)

        # if the GUI wasn't closed, reset it for another conversion
        if not self.closed:
            if self.conversion is not None:
                del(self.conversion)
                self.conversion = None

            # remove progress from GUI and update buttons
            if self.overall_progress is not None:
                self.overall_progress.pack_forget()
            self.progress_canvas_frame.pack_forget()
            self.overall_progress = None

            # update the number of errors, warnings, and completed files
            self.error_count = errors
            self.warning_count = warnings
            self.completed_count = completed
            self.update_buttons()

    def close(self):
        """Cancels the processes before closing the window to prevent errors"""
        # call the cancel method
        self.closed = True
        self.cancel(True)

    def create_progress(self, queues):
        """Creates Progress objects for individual conversion jobs"""
        # make sure GUI isn't closed
        if not self.closed:
            # unpack tuple and create Progress object
            progress_queue, msg_queue = queues
            job = progress.Progress(self.progress_frame,
                                    self.overall_progress,
                                    self.conversion,
                                    self.conversion_tabs,
                                    progress_queue,
                                    msg_queue)

            # add it to the list, update convert tabs, and start progress
            self.progressbars.append(job)
            job.update_files_left()
            job.start()

            # this is to make sure the scrollbar updates
            self.progress_canvas.configure(
                scrollregion=self.progress_canvas.bbox('all')
            )

    def check_comm(self):
        """Checks the communication queue between conversion thread and GUI"""
        # TKINTER ISN'T THREAD SAFE SO YOU MUST COMMUNICATE WITH QUEUE
        # return if not running
        if not self.running:
            return

        # get the message from the communication queue without blocking
        try:
            msg = self.comm.get_nowait()
        except queue.Empty:
            # if there's nothing in there, ignore the exception
            pass
        else:
            # if the message is 'callback' get the args and call callback
            if msg == 'callback':
                self.callback(*self.comm.get())

            # if the message is 'error' wait for the error and log it in GUI
            elif msg == 'error':
                log_time = datetime.datetime.now().strftime(TIME_FORMAT)
                error = self.comm.get()
                self.errors_listbox.insert('end', '{} | {}'.format(log_time, error))
                self.convert_notebook.tab(self.errors_tab, text='Errors ({})'.format(self.errors_listbox.size()))
                self.completed_listbox.insert('end', '{} | ERROR - {}'.format(log_time, error))

            # if it's an int, it's the maximum for the overall progress
            elif isinstance(msg, int):
                self.overall_progress.maximum = msg
                self.overall_progress.progressbar.config(maximum=msg)
                
            # otherwise it's the queues to create a Progress object
            else:
                self.create_progress(msg)

        # check it again in specified # of milliseconds as long as it's running
        if self.running:
            self.after(cdc.CONFIG.getint('GUI', 'comm_queue_refresh_rate', fallback=100), self.check_comm)

    def open_logs(self):
        """Open the log file"""
        # make sure there is a log file
        if self.log_location is not None:
            # open it with default editor depending on platform
            if sys.platform.startswith('darwin'):
                subprocess.call(('open', self.log_location))
            elif os.name == 'nt':
                os.startfile(self.log_location)
            elif os.name == 'posix':
                subprocess.call(('xdg-open', self.log_location))


def main():
    """Function to launch GUI"""

    # Set up dummy output streams if none available in GUI mode
    try:
        sys.stdout.write("\n")
        sys.stdout.flush()
    except (AttributeError, IOError):
        class dummyStream:
            ''' dummyStream behaves like a stream but does nothing. '''
            def __init__(self): pass
            def write(self,data): pass
            def read(self,data): pass
            def flush(self): pass
            def close(self): pass

        # and now redirect all default streams to this dummyStream:
        sys.stdout = dummyStream()
        sys.stderr = dummyStream()
        sys.stdin = dummyStream()
        sys.__stdout__ = dummyStream()
        sys.__stderr__ = dummyStream()
        sys.__stdin__ = dummyStream()
        
    # THIS IS NECESSARY FOR CREATING .exe TO PREVENT MULTIPROCESSING ERRORS
    if getattr(sys, 'frozen', False):
        multiprocessing.freeze_support()

    # Create main Tk window and set size
    root = tk.Tk()
    min_h = cdc.CONFIG.getint('GUI', 'main_min_height', fallback=500)
    min_w = cdc.CONFIG.getint('GUI', 'main_min_width', fallback=530)
    root.minsize(min_w, min_h)
    def_h = cdc.CONFIG.getint('GUI', 'main_def_height', fallback=600)
    def_w = cdc.CONFIG.getint('GUI', 'main_def_width', fallback=600)
    root.geometry('{}x{}'.format(def_w, def_h))

    # withdraw to center on screen
    root.withdraw()

    # instantiate GUI
    app = MainApplication(root)

    # show the application in window with grid geometry manager
    app.grid(sticky='nsew')

    # set function for when window is closed
    root.protocol("WM_DELETE_WINDOW", app.close)

    # the following logic is to center window on screen
    root.update_idletasks()
    width = root.winfo_screenwidth()
    height = root.winfo_screenheight()
    size = tuple(int(_) for _ in root.geometry().split('+')[0].split('x'))
    x = width / 2 - size[0] / 2
    y = height / 2 - size[1] / 2
    root.geometry('%dx%d+%d+%d' % (size + (x, y)))

    # show window and start main loop
    root.deiconify()
    return root, app

def start_gui(root, app):
    # global try/except for KeyboardInterrupt
    try:
        root.mainloop()
    except KeyboardInterrupt:
        # log keyboard interrupt
        gui.LOGGER.info('Keyboard interrupt')
        app.close()

if __name__ == '__main__':
    main()
