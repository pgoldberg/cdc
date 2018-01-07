"""Contains class for reading in plain text files"""
import os
import queue
import time
from encodings.aliases import aliases

import cdc
from .read import Read

class ReadTXT(Read):
    """.txt Reader"""

    # required class variables for extensions, interface labels, and description
    EXTENSIONS = ['txt']
    GUI_LABELS = ['Plain Text']
    CLI_LABELS = ['txt']
    DESCRIPTION = 'All files with the ".txt" extension.'

    # UC_PROPS class variable with the base class UC_PROPS added
    UC_PROPS = Read.UC_PROPS + [
        {'flag': '--indirsubdir',
         'name': '--input-dir-subdir',
         'label': 'Folder and Subfolders',
         'action': 'store',
         'default': None,
         'type': str,
         'help': 'Choose a directory that contains subfolders with files to be converted',
         'var': 'input_dir_subdir',
         'intype': 'dir',
         'position': -1000,
         'required': False},
        {'flag': '--indir',
         'name': '--input-dir',
         'label': 'Single Folder',
         'action': 'store',
         'default': None,
         'type': str,
         'help': 'Choose a directory that contains all files to be converted',
         'var': 'input_dir',
         'intype': 'dir',
         'position': -999,
         'required': False},
        {'flag': '--infile',
         'name': '--input-file',
         'label': 'File',
         'action': 'store',
         'default': None,
         'type': str,
         'help': 'Choose a single file to convert',
         'var': 'input_file',
         'intype': 'file',
         'position': -998,
         'required': False},
        {'flag': '--renc',
         'name': '--r-encoding',
         'label': 'Encoding',
         'action': 'store',
         'default': 'utf8',
         'type': str,
         'help': ('Choose what encoding to use for reading the input file. '
                 'utf8 is the default, which will work for most files.'),
         'var': 'r_encoding',
         'gui_choices': sorted(aliases.keys()),
         'position': 4,
         'required': True}
    ]
    # sort the UC_PROPS on the position key
    UC_PROPS = sorted(UC_PROPS, key=lambda k: k['position'])

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Ensure that the input is a file
        if not os.path.isfile(self.info['metadata']['location']):
            self.put_error(self.info['metadata']['location'], "Not a valid file path.")
            return

        self.info['data'] = []
        self.info['metadata'].update({
                'filename': os.path.basename(self.info['metadata']['location']),
                'filepath': self.info['metadata']['location'],
                'size': os.path.getsize(self.info['metadata']['location']),
                'conversion_id': os.path.abspath(self.info['metadata']['location'])
        })
        self.progress.update({
            'filename': self.info['metadata']['filename'],
            'size': self.info['metadata']['size'],
            'conversion_id': os.path.abspath(self.info['metadata']['location'])
        })
        
        # check that the file is not empty
        if not self.progress['size'] > 0:
            # put_error will put a progress dict in, so don't put another in
            self.put_error(self.info['metadata']['filename'], 'File has no content.')
        else:
            # if there's no error, report the progress
            self.prog_wait()

    def read_data(self):
        """Generator to yield lines in file"""
        # open the file using with statement to avoid having to close file
        with open(self.info['metadata']['filepath'],
                  'r',
                  encoding=self.options['r_encoding']) as file:
            # set state to Reading
            self.progress['state'] = 'Reading'
            # put the progress dict without waiting
            self.prog_nowait()
            # iterate through lines in file
            for index, line in self.file_gen(file):
                # add the line to the info dictionary
                self.info['data'].append(line)
            # set the state to writing
            self.progress['state'] = 'Writing'
            # flush the read-ahead buffer, get position, report progress
            file.flush()
            self.progress['progress'] = file.tell()
            # let it block if it needs to, this message must go through
            self.prog_wait()
            # yield the info dictionary
            # although this seems weird as a generator that only yields once,
            # it's necessary so that the writers work with all readers
            yield self.info


class ReadDelimTXT(ReadTXT):
    """.txt Reader"""

    # required class variables, extensions are inherited from ReadTXT
    GUI_LABELS = ['Delimited Plain Text']
    CLI_LABELS = ['delim_txt']
    DESCRIPTION = 'Plain text files (with the ".txt" extension) that contain several documents separated by a delimiter.'

    # add UC_PROPS to inherited ones
    UC_PROPS = ReadTXT.UC_PROPS + [
        {'flag': '-indelim',
         'name': '--input-delimiter',
         'label': 'Delimiter',
         'action': 'store',
         'default': None,
         'type': str,
         'help': 'The separator between each document in your input file',
         'var': 'sep_delim',
         'required': True,
         'position': 3}
    ]

    # sort UC_PROPS on position key
    UC_PROPS = sorted(UC_PROPS, key=lambda k: k['position'])

    def read_data(self):
        """Generator to yield lines from each document in file"""
        # open file
        with open(self.info['metadata']['filepath'],
                  'r',
                  encoding=self.options['r_encoding']) as file:
            # count the number of records for the logs
            count = 0
            # set the start time and set state to Running
            self.progress['timer'] = time.time()
            self.progress['state'] = 'Running'
            # put the progress without waiting
            self.prog_nowait()
            # list to store lines in document
            lines = []
            # keep track of line numbers for warning reporting
            self.info['line'] = 1
            # read file line-by line
            for index, line in self.file_gen(file):
                # check for a delimiter
                if self.options['sep_delim'] in line:
                    # if there are lines to be yielded
                    if lines:
                        # increment the record count
                        count += 1
                        # put the lines in the dictionary and yield whole thing
                        self.info['data'] = lines
                        yield self.info
                        # update line number for warning reporting
                        self.info['line'] = index + 2
                        # clear lines list, but don't delete them from memory
                        lines = []
                # if the delimiter isn't there, add the line
                else:
                    lines.append(line)
            # increment the count if there are lines to yield
            if lines:
                count += 1
            # update progress
            self.progress['state'] = 'Finished'
            self.progress['processed'] = count
            # flush read-ahead buffer, get position in file, report progress
            file.flush()
            self.progress['progress'] = file.tell()
            # let this one block if it needs to
            self.prog_wait()
            # if there are lines to yield, yield them
            if lines:
                self.info['data'] = lines
                yield self.info
