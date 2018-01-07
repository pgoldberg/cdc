"""Command-Line Interface"""
import os
import sys
# add to sys.path to make sure imports work
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
import argparse
import logging
import multiprocessing
import queue
import subprocess
import threading
import time
import tkinter as tk
import cdc
from ..convert import ConversionThread
from .. import cli, config, gui, read, write

class CommandLineInterface(object):
    def __init__(self):
        """Main function for setting up parser"""
        # wrap in try/except to catch KeyboardInterrupt
        try:
            # create argument parser
            self.parser = argparse.ArgumentParser()

            # create events for the progress and conversion threads
            self.cancelled = threading.Event()
            self.running = threading.Event()
            self.running.set()

            # create variables for progress thread and GUI
            self.progress_thread = None
            self.gui = None

            # create list for queues
            self.queues = []

            # variable to indicate if queues are being processed
            self.processing_queues = False

            # create variable to store conversion thread
            self.conversion = None

            # get reader and writer class dicts
            reader_keys = read.CLI_KEYS
            writer_keys = write.CLI_KEYS

            # add some arguments that aren't received dynamically
            # input and ouput formats
            self.parser.add_argument('--input-format', '--in', '-i', '--input', action='store', dest='input-format', type=str, default=None, help="Format to convert from", choices=reader_keys.keys())

            self.parser.add_argument('--output-format', '-o', '-out', '-output', action='store', dest='output-format', type=str, default=None, help="Format to convert to", choices=writer_keys.keys())

            # add processes option
            # set default to 1 less than total cores (unless single-core)
            processes = multiprocessing.cpu_count() - 1
            if not processes > 0:
                processes = 1
            self.parser.add_argument('--cpu-processes', '--process', '--processes', action='store', default=processes, type=int, help='The number of files to process at a time', dest='processes')

            # add option to launch gui
            self.parser.add_argument('--gui', '-g', action='store_true', default=False, help='Launch the graphical user interface', dest='launch_gui')

            # option to report progress
            self.parser.add_argument('--report-progress', '-p', '--show-progress', '--progress', action='store_true', default=False, help='Report on the command line', dest='report_progress')

            # option to open the config file
            self.parser.add_argument('--open-config-file', '--config', '-c', action='store_true', default=False, help='Open the configuration file', dest='open_config')

            # option to reset config file to default
            self.parser.add_argument('--reset-config-file', '--reset-config', '--reset', '-r', action='store_true', default=False, help='Reset the configuration file to default', dest='reset_config') 

            # option to suppress all output to stdout
            self.parser.add_argument('--quiet', '-q', action='store_true', default=False, help='Suppress all output to standard out', dest='quiet')

            # option to output version number
            self.parser.add_argument('--version', '-v', action='version', help='Get Canary Data Converter version number', version='Canary Data Converter v{}'.format(cdc.__version__))

            # add options for every reader
            for reader in list(set(reader_keys.values())):
                self.cli_options(reader)

            # add options for every writer
            for writer in list(set(writer_keys.values())):
                self.cli_options(writer)

            # parse the arguments
            args = self.parser.parse_args()

            # convert namespace to dict for easy integration between interfaces
            self.options = vars(args)

            # check if quiet option set, add console handler to logger if not
            if not self.options['quiet']:
                cli.LOGGER.addHandler(cdc.CONSOLE_HANDLER)
                
            # launch gui if gui option is set
            if self.options['launch_gui']:
                self.launch_gui()
            # open config file if that option was set
            elif self.options['open_config']:
                open_config()
            # reset config file if that option was set
            elif self.options['reset_config']:
                config.create_config()
            # otherwise, run conversion
            else:
                # create communication queue to communicate w/ conversion thread
                self.comm = queue.Queue()

                # make sure there was an input format provided
                if self.options['input-format']:
                    # get reader class
                    Reader = reader_keys[self.options['input-format']]
                    
                    # validate the reader options
                    validate_options(Reader, self.options, 'reader')
                # if no input format provided, log error and exit
                else:
                    cli.LOGGER.error('Must enter input format.')
                    sys.exit()

                # make sure there was an output format provided
                if self.options['output-format']:
                    # get writer class
                    Writer = writer_keys[self.options['output-format']]

                    # validate writer options
                    validate_options(Writer, self.options, 'writer')
                # if no output format provided, log error and exit
                else:
                    cli.LOGGER.error('Must enter output format.')
                    sys.exit()

                # instantiate conversion thread
                self.conversion = ConversionThread(self.options, Reader, Writer, self.comm)

                # set daemon to true so it terminates when main thread does
                # this is important for ctrl+c to cancel
                self.conversion.daemon = True

                # log interface, version, and os information
                cli.LOGGER.info('Canary Data Converter v{}'.format(cdc.__version__))
                cli.LOGGER.info('Running on Command-Line Interface')
                cli.LOGGER.info(cdc.os_string)

                # spawn thread
                self.conversion.start()

                # start checking the communication queue
                self.check_comm()

        except KeyboardInterrupt:
            # if KeyboardInterrupt, call cancel to safely terminate processes
            self.cancel()
    
    def check_comm(self):
        """Check communication queue"""
        # keep checking queue as long as the program is running
        while self.running.is_set():
            # delay progress reporting by config file spec
            time.sleep(cdc.CONFIG.getint('CLI', 'comm_queue_refresh_rate', fallback=100) / 1000)

            # get without waiting
            try:
                msg = self.comm.get_nowait()
            except queue.Empty:
                # just continue loop if empty, the main thread should be busy
                pass
            else:
                # if the callback message is set
                if msg == 'callback':
                    # call callback method and block until args are received
                    self.callback(*self.comm.get())
                    
                    # return to stop checking communication queue
                    return
                # ignore if it's an int or string, that's for the GUI
                elif isinstance(msg, (int, str)):
                    continue
                # if not a special case, create progress with queues
                else:
                    # if reporting progress, remove console handler
                    if self.options['report_progress']:
                        cli.LOGGER.removeHandler(cdc.CONSOLE_HANDLER)
                    
                    # create progress for the queues
                    self.create_progress(msg)
    
    def cancel(self):
        # log keyboard interrupt
        cli.LOGGER.info('Keyboard interrupt')

        # set cancelled event
        self.cancelled.set()
        
        # if there is a running conversion, cancel it
        if self.conversion is not None:
            self.conversion.cancel()
        # if gui is running, close it
        elif self.gui:
            self.gui.close()
        # clear running event
        if self.running.is_set():
            self.running.clear()

    def create_progress(self, queues):
        """Creates Progress objects for individual conversion jobs"""
        # unpack queues tuple
        progress_queue, msg_queue = queues

        # add queues to lists
        self.queues.append(queues)

        # if not already processing queues
        if not self.processing_queues:
            # processing_queues to True so it doesn't call the function again
            self.processing_queues = True

            # create progress thread
            self.progress_thread = threading.Thread(target=process_queues, args=(self.queues, self.running, self.cancelled, self.options['report_progress'],))

            # set daemon to True so it terminates when main thread does
            self.progress_thread.daemon = True

            # spawn thread
            self.progress_thread.start()

    def callback(self, cancelled=False, error_message=None, process_time=None):
        """Callback function after finishing conversion"""
        # clear running event
        self.running.clear()

        # let the progress thread finish processing queues
        if self.progress_thread is not None:
            try:
                while self.progress_thread.is_alive():
                    time.sleep(0.1)
            except KeyboardInterrupt:
                # call cancel if KeyboardInterrupt is received
                self.cancel()

        # log finished message and timestamp
        cli.LOGGER.info('FINISHED')
        if process_time is not None:
            label = gui.helpers.create_time_label(seconds=process_time)
            label = label.replace(' remaining', '')
            cli.LOGGER.info('Processing Time: {}'.format(label))
            
        # close and remove logger handlers
        for handler in cli.LOGGER.handlers:
            # don't remove the console handler
            if handler != cdc.CONSOLE_HANDLER:
                handler.close()
                cli.LOGGER.removeHandler(handler)

    def cli_options(self, chosen_class):
        """Adds user-customizable properties to argument parser"""
        # iterate over the chosen class's UC_PROPS
        for prop in chosen_class.UC_PROPS:

            # add arguments based on what's in property
            if 'type' and 'choices' in prop:
                try:
                    self.parser.add_argument(prop['flag'],
                                        prop['name'],
                                        action=prop['action'],
                                        default=prop['default'],
                                        type=prop['type'],
                                        choices=prop['choices'],
                                        help=prop['help'],
                                        dest=prop['var'])
                # catch Argument errors in case there are some with same name
                except argparse.ArgumentError:
                    continue
            elif 'type' in prop:
                try:
                    self.parser.add_argument(prop['flag'],
                                        prop['name'],
                                        action=prop['action'],
                                        default=prop['default'],
                                        type=prop['type'],
                                        help=prop['help'],
                                        dest=prop['var'])
                # catch Argument errors in case there are some with same name
                except argparse.ArgumentError:
                    continue
            else:
                try:
                    self.parser.add_argument(prop['flag'],
                                        prop['name'],
                                        action=prop['action'],
                                        default=prop['default'],
                                        help=prop['help'],
                                        dest=prop['var'])
                # catch Argument errors in case there are some with same name
                except argparse.ArgumentError:
                    continue
    
    def launch_gui(self):
        """Launch the GUI from the CLI"""
        root, self.gui = gui.application.main()
        gui.application.start_gui(root, self.gui)

def process_queues(queues, running, cancelled, show_progress):
    """Process all progress queues and output progress"""
    # This is different from the GUI, it processes all queues in same function
    # create progress dict to store progress for each file
    progress_dict = {}

    # variable that tells program to return at the end
    stop = False

    # process as long as it hasn't been cancelled
    while not cancelled.is_set():
        # wait for the refresh rate
        time.sleep(cdc.CONFIG.getint('PROGRESS', 'cli_refresh_rate', fallback=100) / 1000)

        # create message variable
        message = ''

        # iterate over queues
        for progress_queue, msg_queue in queues:
            # create done variable to check for sentinel message
            done = False

            # run as long as cancelled is sent
            while not cancelled.is_set():
                # get progress dict without waiting
                try:
                    prog = progress_queue.get_nowait()
                    # if it's a string, it's the sentinel message
                    if isinstance(prog, str):
                        # set done variable to true
                        done = True

                        # the sentinel message is the conversion_id, so get the last progress dictionary from the progress_didct
                        prog = progress_dict[prog]
                    elif isinstance(prog, list):
                        for warning in prog:
                            # check for a line number and log the warning
                            cli.LOGGER.warning(' | '.join(warning.split(' | ')[1:]))
                        break
                    else:
                        # store progress dict in progress_dict of all queues
                        if prog['conversion_id'] not in progress_dict:
                            progress_dict[prog['conversion_id']] = prog
                # catch empty queue
                except queue.Empty:
                    if not running.is_set():
                        stop = True
                    # break loop to process other queues
                    break
                else:
                    # if finished and there is no error and queue is done
                    if prog['state'] == 'Finished' and prog['error'] is None and done:
                        # log success, files processed if provided
                        if 'processed' in prog:
                            cli.LOGGER.info('SUCCESS - {} | {} records processed'.format(prog['filename'], prog['processed']))
                        else:
                            cli.LOGGER.info('SUCCESS - {}'.format(prog['filename']))

                        # log output path
                        if 'output_path' in prog:
                            cli.LOGGER.info('{} output to {}'.format(prog['filename'], prog['output_path']))
                    # if there was an error
                    elif prog['error'] is not None:
                        # log error, stack info if provided
                        if prog['error']['stack'] is None:
                            cli.LOGGER.error('{}, {}'.format(prog['error']['filename'], prog['error']['message']))
                        else:
                            cli.LOGGER.error('{}, {}:\n{}'.format(prog['error']['filename'], prog['error']['message'], prog['error']['stack']))

                        # set error to None so that it doesn't get logged again
                        prog['error'] = None

                    # update the progress_dict of all progress dictionaries
                    progress_dict[prog['conversion_id']].update(prog)
                    
        # if user chose to have progress reported
        if show_progress:
            # iterate over progress dictionaries for each file
            for value in progress_dict.values():
                # only display if running or error
                if value['state'] == 'Running' or value['state'] == 'Error' or value['state'] == 'Reading' or value['state'] == 'Writing':
                    # get percent and add to message
                    try:
                        pct = int(value['progress'] / value['size'] * 100)
                    except ZeroDivisionError:
                        pct = 0
                    
                    # add to the message string
                    message += '{} - {} - {}%\n'.format(value['filename'], value['state'], pct)
            
            # clear terminal (this should work cross-platform)
            # VERY BUGGY, there aren't great cross-platform alternatives
            os.system('cls' if os.name == 'nt' else 'clear')

            # print message
            print(message, end='')

        # return if no longer running
        if stop:
            return

def validate_options(Handler, options, handler_type):
    """Validate the options provided in the CLI"""
    # source variable if user needs to provide an input/output source
    source = False

    # list of options the user needs to provide
    todo = []
    
    # iterate over Handler's UC_PROPS
    for prop in Handler.UC_PROPS:
        # check that user provided input/output source
        if 'intype' in prop or 'outtype' in prop:
            if options[prop['var']] is not None and options[prop['var']].strip() != '':
                # if provided, set variable to True
                source = True
        # make sure required properties are set
        elif prop['required']:
            if options[prop['var']] is None or options[prop['var']].strip() == '':
                # otherwise add to todo list
                todo.append(prop['name'])
                
    # if input source/output location not provided, prepend to todo
    if not source:
        if handler_type == 'reader':
            todo.insert(0, 'input source')
        elif handler_type == 'writer':
            todo.insert(0, 'output location')

    # if there are things to do, log a message and exit
    if todo:
        if len(todo) > 2:
            todo[-1] = 'and {}'.format(todo[-1])
            message = (', ').join(todo)
        else:
            message = ' and '.join(todo)
        cli.LOGGER.error('Must enter {}.'.format(message))
        sys.exit()

def open_config():
    """Open configuration file"""
    # get config file path
    filedir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    filepath = os.path.join(filedir, 'canarydc.ini')

    # open in default editor, these conditionals make it work cross-platform
    if sys.platform.startswith('darwin'):
        subprocess.call(('open', filepath))
    elif os.name == 'nt':
        os.startfile(filepath)
    elif os.name == 'posix':
        subprocess.call(('xdg-open', filepath))

def main():
    """Main function to launch CLI"""

    # This is needed for freezing the CLI version on Windows
    multiprocessing.freeze_support()

    # if no arguments provided, add -h to show help
    if len(sys.argv) == 1:
        sys.argv.append('-h')
        
    # instantiate CLI
    interface = CommandLineInterface()

if __name__ == '__main__':
    main()
