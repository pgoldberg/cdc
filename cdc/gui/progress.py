"""The progress classes for the GUI"""
import datetime
import queue
import threading
import time
import tkinter as tk
from tkinter import ttk
import cdc
from .. import gui
from . import helpers

TIME_FORMAT = cdc.CONFIG.get('GUI', 'gui_log_timestamp', fallback='%H:%M:%S - %m-%d-%Y')

class OverallProgress(tk.Frame):
    """Overall progress for all conversion jobs"""
    def __init__(self, master, *args, **kwargs):
        # call super constructor
        tk.Frame.__init__(self, master, *args, **kwargs)

        # create instance variables for start time, max bytes, bytes completed
        self.timer = 0
        self.maximum = 0
        self.complete = 0

        # create progress bar and labels
        self.progresslabel = tk.Label(self, text='Overall Progress: ')
        self.timelabel = tk.Label(self)

        # make progress bar green
        self.progressbar = ttk.Progressbar(self, style='green.Horizontal.TProgressbar', maximum=0)

        # use grid (easier for this kind of thing)
        self.progresslabel.grid(column=0, row=0)
        self.progressbar.grid(column=0, row=2, sticky='ew')

        # add weight to grid columns
        self.grid_rowconfigure(2, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # add separator to GUI
        tk.Frame(self,
                 relief='ridge',
                 height=3,
                 bg='#a6a9ad').grid(column=0, row=3, sticky='ew', pady=(4, 0))

    def set_time(self):
        """Set start time"""
        # get start time and add the time remaining label to GUI
        self.timer = time.time()
        self.timelabel.grid(column=0, row=1)

    def step(self, amt):
        """Updates progress and time remaining"""
        # add amount processed to self.complete and update progressbar value
        self.complete += amt
        self.progressbar['value'] = self.complete

        # try to update percent in GUI, catch if the maximum isn't set
        try:
            self.progresslabel.config(text='Overall Progress: {}%'.format(
                int(self.complete / self.maximum * 100)
            ))
        except ZeroDivisionError:
            pass
        else:
            # get the time remaining and update label
            complete = self.complete / self.maximum
            elapsed = time.time() - self.timer
            self.timelabel.config(text=helpers.create_time_label(elapsed, complete))

    def reset(self):
        """Resets everything for new conversion"""
        # reset all variables and reset progressbar and labels
        self.timer = 0
        self.maximum = 0
        self.complete = 0
        self.progressbar.config(value=0, maximum=0)
        self.progresslabel.config(text='Overall Progress: ')

class Progress(tk.Frame):
    """Progress object for individual jobs"""

    def __init__(self, master, overall_progress, conversion, tabs, progress_queue, msg_queue, *args, **kwargs):
        # call super constructor
        tk.Frame.__init__(self, master, *args, **kwargs)

        # store the overall progress object, conversion thread, tabs, and queues
        self.overall_progress = overall_progress
        self.conversion = conversion
        self.tabs = tabs
        self.progress_queue = progress_queue
        self.msg_queue = msg_queue
        self.log_thread = None

        # list to store warnings
        self.warnings = []

        # instance variables to store last amount progressed and progress dict
        self.last_amt = 0
        self.finished_prog = None

        # variables to indicate completion and store filename
        self.complete = False
        self.filename = None
        self.error_logged = False

        # create progress label, time label, and buttons
        self.progresslabel = tk.Label(self)
        self.timelabel = tk.Label(self)
        self.barbuttonframe = tk.Frame(self)
        self.progressbar = ttk.Progressbar(
            self.barbuttonframe,
            style='green.Horizontal.TProgressbar'
        )
        self.cancelbutton = tk.Button(self.barbuttonframe, text='Cancel', command=self.cancel)
        self.pausebutton = tk.Button(self.barbuttonframe, text='Pause', command=self.pause)

    def start(self):
        """Starts updating progress"""
        # get the progress dict without blocking with get_nowait
        try:
            prog = self.progress_queue.get_nowait()
        except queue.Empty:
            # if it's empty, try again after config file refresh rate
            rate = cdc.CONFIG.getint('PROGRESS', 'gui_refresh_rate', fallback=100)
            self.after(rate, self.start)
        else:
            # put filename in progress label and set max size of progressbar
            self.filename = prog['filename']
            self.progresslabel.config(text='{} | Progress:'.format(self.filename))
            self.progressbar.config(maximum=prog['size'])

            # pack the labels and buttons
            self.progresslabel.pack(side='top')
            self.timelabel.pack(side='top')
            self.progressbar.pack(side='left', fill='x', expand=True)
            self.barbuttonframe.pack(side='top', fill='x', expand=True)
            self.cancelbutton.pack(side='right', padx=3)
            self.pausebutton.pack(side='right', padx=(3, 0))

            # add a separator
            tk.Frame(self,
                    relief='ridge',
                    height=1,
                    bg='#a6a9ad').pack(side='top',
                                        fill='x',
                                        expand=True,
                                        pady=(4, 0))
            self.pack(side='top', fill='both', expand=True)

            # update files left and start updating progress
            self.update_files_left()
            self.step_prog()

    def pause(self):
        """For pausing a conversion job"""
        # put pause in the msg_queue to pause process, log it, update button
        self.msg_queue.put('pause')
        gui.LOGGER.info('Paused {}'.format(self.filename))
        self.pausebutton.config(text='Resume', command=self.resume)

    def resume(self):
        """Resume conversion job after pausing"""
        # put resume into msg_queue to resume progress, log it, update button
        self.msg_queue.put('resume')
        gui.LOGGER.info('Resumed {}'.format(self.filename))
        self.pausebutton.config(text='Pause', command=self.pause)

    def cancel(self, log=True):
        """Cancel a conversion job"""
        # check that it didn't already finish

        if not self.complete:
            # set it to complete to stop reporting progress
            self.complete = True

            # put the cancel message into the msg_queue to stop the process
            self.msg_queue.put('cancel')

            # get progress dict without blocking
            try:
                prog = self.progress_queue.get_nowait()
            except queue.Empty:
                pass
            else:
                # remove the bytes from the overall progress
                self.overall_progress.maximum -= prog['size']
                self.overall_progress.progressbar.config(maximum=self.overall_progress.maximum)
                self.overall_progress.complete -= prog['progress']

                # step it again to update the progress (use 0 as bytes value)
                self.overall_progress.step(0)

            # remove this widget from GUI
            self.pack_forget()

            # add to completed tab
            self.tabs['completed'].insert('end', '{} | CANCELLED - {}'.format(datetime.datetime.now().strftime(TIME_FORMAT), self.filename))

            # log it unless specified not to
            if log:
                gui.LOGGER.info('CANCELLED - {}'.format(self.filename))

            # update files left
            self.update_files_left()

    def step_prog(self):
        """Periodic calls to update progress"""
        # don't call if the job is complete
        if not self.complete:
            # process the progress queue
            self.process_queue()

            # call this again after the specified refresh rate
            rate = cdc.CONFIG.getint('PROGRESS', 'gui_refresh_rate', fallback=100)
            self.after(rate, self.step_prog)
    
    def populate_queue(self):
        """Populate the queue tab"""
        # clear the listbox
        self.tabs['queue'].delete(0, 'end')

        # add all of the waiting workers
        for worker in self.conversion.workers:
            self.tabs['queue'].insert('end', worker['info']['metadata']['filename'])

    def update_files_left(self):
        """Updates files left displayed in notebook tab"""
        # (re)populate the queue
        self.populate_queue()

        # update number of files being converted by number of widgets packed to
        # conversion tab
        files_left = len(self.tabs['progress'].pack_slaves())
        if files_left > 0:
            self.tabs['notebook'].tab(self.tabs['progress_tab'],
                                      text='Conversion ({})'.format(files_left))
        else:
            self.tabs['notebook'].tab(self.tabs['progress_tab'],
                                      text='Conversion')
        self.tabs['progress_canvas'].configure(
            scrollregion=self.tabs['progress_canvas'].bbox('all')
        )

        # update other tabs by listbox size with size() method
        amt_warnings = self.tabs['warnings'].size()
        if amt_warnings > 0:
            self.tabs['notebook'].tab(self.tabs['warnings_tab'],
                                      text='Warnings ({})'.format(
                                          amt_warnings
                                      ))
        amt_errors = self.tabs['errors'].size()
        if amt_errors > 0:
            self.tabs['notebook'].tab(self.tabs['errors_tab'],
                                      text='Errors ({})'.format(
                                          amt_errors
                                      ))
        amt_completed = self.tabs['completed'].size()
        if amt_completed > 0:
            self.tabs['notebook'].tab(self.tabs['completed_tab'],
                                      text='Completed ({})'.format(
                                          amt_completed
                                      ))
        amt_queue = self.tabs['queue'].size()
        if amt_queue > 0:
            self.tabs['notebook'].tab(self.tabs['queue_tab'],
                                      text='Queue ({})'.format(
                                          amt_queue
                                      ))
        else:
            self.tabs['notebook'].tab(self.tabs['queue_tab'], text='Queue')

    def process_queue(self):
        """Updates progress by checking progress_queue"""
        # create this bool to set when queue is done
        done = False

        # list to hold progress dictionaries
        progs = []

        # get all of the progress dictionaries from the progress_queue
        while True:
            # make sure the process isn't done
            if self.complete:
                break

            # get progress dict without waiting and append to list
            try:
                prog = self.progress_queue.get_nowait()
            except queue.Empty:
                break
            else:
                progs.append(prog)

        for prog in progs:
            # if it gets a string, it's the sentinel message
            if isinstance(prog, str):
                # set done to true and set the progress dict to the last one
                done = True

                # set complete to true
                self.complete = True
                if self.finished_prog is not None:
                    prog = self.finished_prog
                else:
                    return
            # if it gets a list, it's a list of all the warnings
            elif isinstance(prog, list):
                # add warnings to instance variable so they can be logged later
                self.warnings.extend(prog)

                # add the warnings to the GUI Warnings tab
                self.tabs['warnings'].insert('end', *prog)
                self.update_files_left()
                continue
            else:
                # set finished progress dict if there is no error
                if prog['error'] is None:
                    self.finished_prog = prog

            # update the overall progress
            self.overall_progress.step(prog['progress'] - self.last_amt)

            # if process finished, there are no errors, and
            # sentinel message received
            if prog['state'] == 'Finished' and prog['error'] is None and done:
                # create and spawn the log_thread
                self.log_thread = threading.Thread(target=self.log_completion, args=(prog,))
                self.log_thread.daemon = True
                self.log_thread.start()

                # if total records processed in progress dict
                if 'processed' in prog:
                    # add to completed listbox
                    message = 'SUCCESS - {} | {} records processed'.format(prog['filename'], prog['processed'])
                    self.tabs['completed'].insert('end', '{} | {}'.format(
                        datetime.datetime.now().strftime(TIME_FORMAT),
                        message
                    ))
                else:
                    # add to completed listbox
                    message = 'SUCCESS - {}'.format(prog['filename'])
                    self.tabs['completed'].insert('end', '{} | {}'.format(
                        datetime.datetime.now().strftime(TIME_FORMAT),
                        message
                    ))

                # remove the widget, update files left
                self.pack_forget()
                self.update_files_left()

            # if there was an error
            elif prog['error'] is not None:
                # don't spawn thread if one error was already logged,
                # just log this error too
                if self.error_logged:
                    self.log_completion(prog, True)
                # if an error hasn't been logged, create/spawn log_thread
                else:
                    self.error_logged = True
                    self.log_thread = threading.Thread(target=self.log_completion, args=(prog, True,))
                    self.log_thread.daemon = True
                    self.log_thread.start()

                    # remove widget
                    self.pack_forget()

                    # remove from overall progress
                    self.overall_progress.maximum -= prog['size']
                    self.overall_progress.progressbar.config(maximum=self.overall_progress.maximum)
                    self.overall_progress.complete -= prog['progress']

                    # call step to update overall progress
                    self.overall_progress.step(0)

                    # add file to completed listbox
                    self.tabs['completed'].insert('end', '{} | ERROR - {}'.format(datetime.datetime.now().strftime(TIME_FORMAT), self.filename))

                # insert the error in the errors listbox
                self.tabs['errors'].insert('end',
                                            '{} | {}: {}'.format(
                                                datetime.datetime.now().strftime(TIME_FORMAT),
                                                prog['error']['filename'],
                                                prog['error']['message']
                                            ))

                # update tabs and break loop
                self.update_files_left()

            # if not special case, update the progress and store last amount
            else:
                self.progressbar['value'] = prog['progress']
                self.last_amt = prog['progress']
                
            # get time remaining and update labels
            complete = prog['progress'] / prog['size']
            if prog['timer'] is not None:
                elapsed = time.time() - prog['timer']
                self.timelabel.config(text=helpers.create_time_label(
                    elapsed,
                    complete
                ))
            self.progresslabel.config(
                text='{} | {} | Progress: {}%'.format(
                    prog['filename'],
                    prog['state'],
                    int(100 * complete)
                )
            )

    def log_completion(self, prog, error=False):
        """Logs the warnings and final messages"""
        # log all of the warnings
        for warning in self.warnings:
            gui.LOGGER.warning(' | '.join(warning.split(' | ')[1:]))
        
        # log the error if there was one
        if error:
            # log it if it has stack info or not
            if prog['error']['stack'] is None:
                gui.LOGGER.error('{}, {}'.format(prog['error']['filename'], prog['error']['message']))
            else:
                gui.LOGGER.error('{}, {}:\n{}'.format(prog['error']['filename'], prog['error']['message'], prog['error']['stack']))

        # otherwise log success
        else:
            # if total records processed in progress dict
            if 'processed' in prog:
                # log success
                message = 'SUCCESS - {} | {} records processed'.format(prog['filename'], prog['processed'])
                gui.LOGGER.info(message)
            else:
                # log success
                message = 'SUCCESS - {}'.format(prog['filename'])
                gui.LOGGER.info(message)

            # if the output path is in the progress dict, log it
            if 'output_path' in prog:
                gui.LOGGER.info('{} output to {}'.format(prog['filename'], prog['output_path']))
