"""This module spawns the conversion thread and the processes for each job"""
import datetime
import logging
import multiprocessing
import os
import queue
import sys
import time
import timeit
import threading
import traceback
import cdc
from . import read

LOG_TIME_FORMAT = cdc.CONFIG.get('MAIN', 'logfile_timestamp', fallback='%Y-%m-%d-%H.%M.%S')

class ConversionThread(threading.Thread):
    """Class representing a new thread for the conversion"""
    def __init__(self, options, Reader, Writer, comm):
        super(ConversionThread, self).__init__()
        self.comm = comm
        self.options = options
        self.Reader = Reader
        self.Writer = Writer
        self.msg_queues = []
        self.progress_queues = []
        self.cancelled = False
        self.logger = logging.getLogger('log')
        self.logfile = None
        self.log_location = None
        self.total_size = 0
        self.workers = []
        self.running_workers = []

        # create logfile if output location is a directory and config file option is True
        if 'output_dir' in self.options and self.options['output_dir'] is not None:
            if not os.path.isdir(self.options['output_dir']):
                self.error('Invalid output location: "%s"' % (os.path.abspath(self.options['output_dir'])), exit_thread=True)
                sys.exit()

            if cdc.CONFIG.getboolean('MAIN', 'create_logfile', fallback=True):
                self.log_location = os.path.join(options['output_dir'], 'canary_conversion_{}.log'.format(datetime.datetime.now().strftime(LOG_TIME_FORMAT)))
                self.logfile = logging.FileHandler(self.log_location)
                self.logfile.setLevel(logging.INFO)
                formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
                self.logfile.setFormatter(formatter)
                self.logger.addHandler(self.logfile)

    def run(self):
        """Method to wrap the whole run_conversion method in a try/except"""
        try:
            self.run_conversion()
        except KeyboardInterrupt:
            return
        except:
            # get traceback info and log exit error
            error = traceback.format_exc()
            self.error('Error occurred while processing. See logs for more info.', stack_info=error, exit_thread=True)
            return

    def run_conversion(self):
        """Runs the conversion"""
        # log the beginning of conversion and user-specified options
        self.logger.info('STARTING CONVERSION')
        self.log_options()
        start = timeit.default_timer()

        # get user-specified number of processes to spawn
        if 'processes' in self.options and self.options['processes'] is not None:
            processes = self.options['processes']
        else:
            # if user didn't specify, use number of cores minus 1
            processes = multiprocessing.cpu_count() - 1
        
        # instantiate lists for waiting workers and running workers
        self.workers = []
        self.running_workers = []

        # handle single-file input
        if 'input_file' in self.options and self.options['input_file'] is not None:
            # create a queue for reporting progress and one for sending messages
            msg_queue = multiprocessing.Queue()
            self.msg_queues.append(msg_queue)
            progress_queue = multiprocessing.Queue()
            self.progress_queues.append(progress_queue)

            try:
                # instantiate reader and track total bytes
                read_file = self.Reader(self.options, self.options['input_file'], progress_queue, msg_queue)
                self.total_size += read_file.progress['size']
            except read.ReaderError as excp:
                self.error('Unable to create Reader for {}: {}'.format(self.options['input_file'], str(excp)))
            except:
                # get traceback info and log any errors
                error = traceback.format_exc()
                excp = sys.exc_info()[1]
                
                self.error('Unable to create Reader for {}: {}'.format(self.options['input_file'], excp), stack_info=error, exit_thread=True)
                return
            else:
                # append worker dictionary with info for this process
                self.workers.append({
                    'info': read_file.info,
                    'queues': (progress_queue, msg_queue),
                    'process': multiprocessing.Process(target=convert, args=(self.options, read_file, self.Writer,))
                })
        
        # handle directory input
        elif ('input_dir' in self.options and self.options['input_dir'] is not None) or ('input_dir_subdir' in self.options and self.options['input_dir_subdir'] is not None):
            infiles = []
            try:
                # handle "Single Folder" option
                if 'input_dir' in self.options and self.options['input_dir'] is not None:
                    # get all files in directory
                    for basename in os.listdir(self.options['input_dir']):
                        filename = os.path.join(self.options['input_dir'], basename)
                        # ensure it's a valid file before adding to list
                        if os.path.isfile(filename) and filename.split('.')[-1].lower() in self.Reader.EXTENSIONS:
                            infiles.append(filename)
                
                # handle "Folders and Subfolders" option
                else:
                    # go through folders and subfolders
                    for root, _, files in os.walk(self.options['input_dir_subdir']):
                        for basename in files:
                            filename = os.path.join(root, basename)
                            # ensure it's a valid file before adding to list
                            if os.path.isfile(filename) and filename.split('.')[-1].lower() in self.Reader.EXTENSIONS:
                                infiles.append(filename)
            except FileNotFoundError:
                # log exit error if FileNotFoundError is raised
                self.error('Could not open files in specified input directory', exit_thread=True)
                return
            # log the number of infiles found
            self.logger.info('Found {} files'.format(len(infiles)))
            # log exit error if no valid infiles are found
            if infiles == []:
                self.error('Could not open any files in specified input directory', exit_thread=True)
                return
            # iterate over infiles and create processes
            for index, file in enumerate(infiles):
                # create a queue for reporting progress and one for sending messages
                msg_queue = multiprocessing.Queue()
                self.msg_queues.append(msg_queue)
                progress_queue = multiprocessing.Queue()
                self.progress_queues.append(progress_queue)

                # set input_file option to the current file being processed
                self.options['input_file'] = file

                # save original output filename before altering
                name = self.options['output_filename']

                # add number to output filename to handle multiple files
                if self.options['output_filename'] is not None:
                    self.options['output_filename'] = '{} ({})'.format(name, index + 1)
                try:
                    # instantiate reader and track total bytes
                    read_file = self.Reader(self.options, self.options['input_file'], progress_queue, msg_queue)
                    self.total_size += read_file.progress['size']
                except read.ReaderError as excp:
                    self.error('Unable to create Reader for {}: {}'.format(file, str(excp)))
                except:
                    # get traceback info and log exit error
                    error = traceback.format_exc()
                    excp = sys.exc_info()[1]
                    self.error('Unable to create Reader for {}: {}'.format(file, excp), stack_info=error)
                else:
                    # create worker dictionary and add to waiting workers
                    self.workers.append({
                        'info': read_file.info,
                        'queues': (progress_queue, msg_queue),
                        'process': multiprocessing.Process(target=convert, args=(self.options, read_file, self.Writer,))
                    })
                    # reset output filename to the original without the number
                    self.options['output_filename'] = name
        # communicate total bytes to main thread for overall progress
        self.comm.put(self.total_size)

        # below is the logic for spawning the processes
        # this loop will continue as long as there are workers queued
        while self.workers:
            # this for-loop will run if there is space to spawn another worker
            for i in range(processes - len(self.running_workers)):
                # check again to make sure there are workers left
                if self.workers:
                    # pop the next worker out of waiting list
                    worker = self.workers.pop(0)

                    # send queues to main thread to start progress reporting
                    queues = worker['queues']
                    self.comm.put(queues)

                    # log that processing is starting
                    self.logger.info('Processing {}'.format(worker['info']['metadata']['conversion_id']))

                    # spawn process if the conversion hasn't been cancelled
                    if not self.cancelled:
                        worker['process'].start()

                    # add worker to list of running workers
                    self.running_workers.append(worker)
                else:
                    break
            
            # Wait for a slot for a new worker.
            # iterate over running workers to check that they are running
            for i, worker in enumerate(self.running_workers):
                # if worker is finished, remove it from running_workers
                if not worker['process'].is_alive():
                    del self.running_workers[i]
                    # break out of for-loop so a new process can be spawned
                    break

            # avoid busy-waiting
            time.sleep(0.5)

        # this loop will just block until all running workers are finished
        while self.running_workers:
            # iterate over copy of list so we can remove from the original list
            for worker in self.running_workers[:]:
                # remove from (original) list if finished
                if not worker['process'].is_alive():
                    if self.cancelled:
                        break
                    self.running_workers.remove(worker)

            # Check if we are finished
            if self.cancelled or not self.running_workers:
                break

            # Avoid busy-waiting
            time.sleep(0.5)

        stop = timeit.default_timer()
        process_time = stop - start
        
        # call callback function through queue
        # done through queue because tkinter is not thread safe
        self.comm.put('callback')
        self.comm.put((self.cancelled, None, process_time))
    
    def log_options(self):
        """Logs the user-specified options"""
        message = '\nINPUT OPTIONS:\n'
        message += '{} Reader\n'.format(self.Reader.GUI_LABELS[0])
        # iterate over UC_PROPS and append values to message
        for prop in self.Reader.UC_PROPS:
            if self.options[prop['var']] is not None:
                message += '{}: {}\n'.format(prop['label'], self.options[prop['var']])
        # log message
        self.logger.info(message)

        message = '\nOUTPUT OPTIONS:\n'
        message += '{} Writer\n'.format(self.Writer.GUI_LABELS[0])
        # iterate over UC_PROPS and append values to message
        for prop in self.Writer.UC_PROPS:
            if self.options[prop['var']] is not None:
                message += '{}: {}\n'.format(prop['label'], self.options[prop['var']])
        # log message
        self.logger.info(message)
        
        message = '\nCONVERSION OPTIONS:\n'
        # iterate over conversion options and append values to message
        message += 'Processes: {}\n'.format(self.options['processes'])
        # log message
        self.logger.info(message)

    def error(self, message, stack_info=None, exit_thread=False):
        """Sends error to main thread and exits this thread"""
        # send the error to the GUI to be logged there
        self.comm.put('error')
        self.comm.put('{}. See the log for more details.'.format(message))

        # add traceback info if provided
        if stack_info is not None:
            message = '{}:\n\n{}'.format(message, stack_info)
    
        # log the error
        self.logger.error(message)

        # if exiting the thread, remove the FileHandler and callback
        if exit_thread:
            # stop logging to logfile
            if self.logfile is not None:
                self.logger.removeHandler(self.logfile)
            
            # callback to main thread
            self.comm.put('callback')
            self.comm.put((True, message))
    
    def cancel(self):
        """Cancel all conversion jobs"""
        self.cancelled = True
        # clear the queue to prevent spawning new processes
        del self.workers[:]

        # cancel the running workers
        for worker in self.running_workers:
            worker['process'].terminate()
            worker['process'].join()
        # delete running workers list
        del self.running_workers[:]

def convert(options, read_file, Writer):
    """Sends information to proper writer (currently only writes to a directory
    but there may be future functions for writing to a database"""

    # check for messages in case an error came up during reader instantiation
    read_file.check_msg_queue()

    try:
        # call the write_dir function if writing to a directory
        if 'output_dir' in options and options['output_dir'] is not None:
            write_dir(options, read_file, Writer)
            
        # put rest of the warnings in the queue
        read_file.progress_queue.put(read_file.warnings)
    # catch KeyboardInterrupt, SystemExit, and read.ReaderError to avoid unwanted error messages
    except (KeyboardInterrupt, SystemExit, read.ReaderError):
        pass
    # handle any other errors and log them
    except:
        error = traceback.format_exc()
        excp = sys.exc_info()[1]

        read_file.put_error(read_file.info['metadata']['conversion_id'], 'Unhandled error occurred while processing: "%s" See log for more info.' % str(excp), stack_info=error)
    else:
        # check the message queue one last time to make sure nothing went wrong
        read_file.check_msg_queue()

        # VERY IMPORTANT THAT THIS NEXT PART HAPPENS
        # set the state to finished and report the progress
        read_file.progress['state'] = 'Finished'
        read_file.prog_wait()

    # send sentinel message
    read_file.progress_queue.put(read_file.info['metadata']['conversion_id'])

def write_dir(options, read_file, Writer):
    """Instantiates writer for directory output"""
    # instantiate writer
    outfile = Writer(options, read_file)
    try:
        # start processing
        outfile.write_dir()
    except FileNotFoundError:
        read_file.put_error(read_file.info['metadata']['conversion_id'], 'Could not find output folder.')
