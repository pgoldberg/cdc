"""Contains superclass for reading in files"""
import datetime
import multiprocessing
import os
import queue
import random
import sys
import time

import cdc
from .. import read
from ..utils.ucprop import UCPropMixin

# time format for warnings
TIME_FORMAT = cdc.CONFIG.get('GUI', 'gui_log_timestamp', fallback='%H:%M:%S - %m-%d-%Y')

class Read(UCPropMixin, object):
    """Superclass for reading in files"""

    def __init__(self, options, file_location, progress_queue=None, msg_queue=None):
        # create instance variables for options and queues
        self.options = options
        self.progress_queue = progress_queue
        self.msg_queue = msg_queue
        self.warnings = []
        # get the report rate from the config file
        self.report_rate = cdc.CONFIG.getint('PROGRESS', 'report_rate', fallback=10000)
        # create info dictionary - this is used to communicate with writer
        self.info = {
            'data': None,
            'metadata': {
                'location': file_location,
                'conversion_id': str(random.randint(1, 999999))
            }
        }
        # create progress dictionary - used to send progress to main process
        self.progress = {
            'filename': None,
            'conversion_id': self.info['metadata']['conversion_id'],
            'size': 0,
            'progress': 0,
            'state': 'Waiting',
            'warning': None,
            'error': None,
            'timer': None
        }

    def check_msg_queue(self, message=None):
        """Checks msg_queue for messages to cancel, pause, resume, etc."""
        if self.msg_queue is not None:
            if message is None:
                # check for a message without waiting, return if there's nothing
                try:
                    msg = self.msg_queue.get_nowait()
                except queue.Empty:
                    return
            else:
                msg = message
            # if the message is to cancel, report progress and exit process
            if msg == 'cancel':
                if self.progress_queue is not None:
                    self.progress['state'] = 'Cancelled'
                    self.progress_queue.put(self.progress)
                sys.exit()
            # if it's an error, exit the process
            elif msg == 'error':
                # send the sentinel message
                self.progress_queue.put(self.info['metadata']['conversion_id'])
                sys.exit()
            # if paused, set state to Paused and report progress
            elif msg == 'pause':
                if self.progress_queue is not None:
                    self.progress['state'] = 'Paused'
                    self.progress_queue.put(self.progress)
                # this will block until a message is received, pausing process
                resume_msg = self.msg_queue.get()
                # if the message is to resume, report progress, set state to Running
                if resume_msg == 'resume':
                    if self.progress_queue is not None:
                        self.progress['state'] = 'Running'
                        self.progress_queue.put(self.progress)
                # else, check the message
                else:
                    self.check_msg_queue(message=resume_msg)

    def put_warning(self, filename, message, line=None):
        """Adds a warning"""
        time_str = datetime.datetime.now().strftime(TIME_FORMAT)
        # create string and add to warnings list
        if line is not None:
            warning = '{} | {}, line {}: {}'.format(time_str, filename, line, message)
        else:
            warning = '{} | {}: {}'.format(time_str, filename, message)
        self.warnings.append(warning)
        if len(self.warnings) == cdc.CONFIG.getint('PROGRESS', 'warning_list_size', fallback=1000):
            self.progress_queue.put(self.warnings)
            self.warnings = []

    def put_error(self, filename, message, stack_info=None):
        """Adds an error"""
        # put progress into the queue
        self.prog_wait()

        if self.progress_queue is not None:
            # set state to Error
            self.progress['state'] = 'Error'

            # put warnings in the queue so they get logged
            self.progress_queue.put(self.warnings)
            self.warnings = []
            
            # copy progress dict
            progress = dict(self.progress)

            # add error to progress dict
            progress['error'] = {
                'filename': filename,
                'message': message,
                'stack': stack_info
            }

            # report progress
            self.progress_queue.put(progress)
        raise read.ReaderError(message)
    
    def file_gen(self, file):
        """A generator based off of enumerate that checks for messages and reports progress periodically"""
        # iterate over lines in file
        try:
            for index, line in enumerate(file):
                # check 
                if index % self.report_rate == 0:
                    # check messages
                    self.check_msg_queue()
                    # flush read-ahead buffer to allow use of tell()
                    file.flush()
                    # get position in file and add to progress dict
                    self.progress['progress'] = file.tell()
                    try:
                        self.progress_queue.put_nowait(self.progress)
                    except (queue.Full, AttributeError):
                        pass
                # yield index and line
                yield index, line
        except UnicodeDecodeError as e:
            # There was an error decoding the data
            self.put_error(self.info["metadata"]["location"], str(e) + " (Did you choose the correct encoding?)")
        except:
            raise
            
            
    def refresh_file_prog(self, file):
        # flush read-ahead buffer to allow use of tell()
        file.flush()
        # get position in file and add to progress dict
        self.progress['progress'] = file.tell()

    def prog_nowait(self):
        """Report progress and check for messages without waiting"""
        if type(multiprocessing.current_process()) == multiprocessing.Process:
            self.check_msg_queue()
        if self.progress_queue is not None:
            try:
                self.progress_queue.put_nowait(self.progress)
            except queue.Full:
                pass

    def prog_wait(self):
        """Report progress and block until it can be reported"""
        if type(multiprocessing.current_process()) == multiprocessing.Process:
            self.check_msg_queue()
        if self.progress_queue is not None:
            self.progress_queue.put(self.progress)