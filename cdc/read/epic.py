"""Contains class for reading in RPDR files"""
import queue
import time
import traceback
import cdc
from .text import ReadTXT

class ReadEpicText(ReadTXT):
    """Epic Text Reader"""

    # required class variables, EXTENSIONS is inherited
    GUI_LABELS = ['Epic Text']
    CLI_LABELS = ['epic_text', 'epic']
    DESCRIPTION = 'Files from the Epic medical record software. These files are plain text files with a ".txt" extension.'
    # get the possible text fields from the config file
    TEXT_FIELDS = [field.lower().strip() for field in cdc.CONFIG.get('read.epic', 'Text_Fields', fallback='NOTE_TEXT').split(',')]

    ID_FIELDS = [field.strip() for field in cdc.CONFIG.get('read.epic', 'Autodetect_Epic_ID', fallback='Autodetect, NOTE_ID').split(',')]

    # Add UC_PROPS to ones from ReadTXT
    UC_PROPS = [
        {'flag': '--epicid',
         'name': '--epic-id-field',
         'label': 'Epic ID Field',
         'action': 'store',
         'default': ID_FIELDS[0],
         'type': str,
         'help': 'The ID field to use in order to distinguish between the different records in the input file.',
         'choices': [choice.lower() for choice in ID_FIELDS],
         'gui_choices': ID_FIELDS,
         'var': 'epic_id',
         'required': True,
         'position': -1
        },
        {'flag': '--nohdr',
         'name': '--no-header',
         'label': 'Create Record Headers',
         'action': 'store_false',
         'default': True,
         'help': 'Do not add header to output files',
         'gui_help': 'Create record headers using the data in the Epic Text records.',
         'var': 'create_header',
         'position': 0,
         'required': False}
    ] + ReadTXT.UC_PROPS

    # sort UC_PROPS
    UC_PROPS = sorted(UC_PROPS, key=lambda k: k['position'])

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # instantiate text field variable
        self.text_field = None
        # the fields variable stores the metadata field titles in the file
        self.fields = []
        # open the file to validate file and get fields
        try:
            with open(self.info['metadata']['filepath'], 'r', encoding=self.options['r_encoding']) as file:
                # read line-by-line, the first two lines with text is all we need
                for line in file:
                    # skip any blank lines
                    if line.strip() == '':
                        continue
                    else:
                        # store first line so we can ignore it later
                        self.first_line = line
                        # read in metadata fields and break loop
                        self.fields = [field.lower().strip().replace(u'\ufeff', '') for field in line.split('\t')]
                        break
        except UnicodeDecodeError:
            self.put_error(self.info['metadata']['filename'], 'Unable to decode file with given encoding.')
        except:
            error = traceback.format_exc()
            self.put_error(self.info['metadata']['filename'], 'Unable to decode file with given encoding.', error)
        # make sure there was a tab-delimited list, otherwise report error
        if len(self.fields) <= 1:
            self.put_error(self.info['metadata']['filename'], 'Not a valid Epic Text file')
        # if there wasn't an error, continue
        else:
            # update metadata fields
            self.info['metadata'].update({field: None for field in self.fields})
            # figure out the text field
            for field in self.TEXT_FIELDS:
                if field in self.fields:
                    self.text_field = field
                    break
            # warn user if couldn't find text field
            if self.text_field is None:
                self.put_warning(self.info['metadata']['filename'], 'Could not determine file\'s text field.')
            # find the ID field - necessary for epic since there's no delimiter
            if (self.options['epic_id'] == 'Autodetect'
                or self.options['epic_id'] == 'autodetect'):
                # if it's autodetect, get the possible id fields
                self.options['epic_id'] = [choice.lower() for choice in self.ID_FIELDS]
                # delete autodetect from the list
                self.options['epic_id'].remove('autodetect')
                # find the field and set it in the options dictionary
                for field in self.options['epic_id']:
                    if field in self.fields:
                        self.options['epic_id'] = field
                        break
                # if it couldn't find it, report an error
                # the id is necessary to distinguish between files
                if isinstance(self.options['epic_id'], list):
                    self.put_error(self.info['metadata']['filename'], 'Could not determine file\'s ID field.')
            # if it isn't autodetect, the user chose the id themselves
            else:
                # make the id all lowercase (because the fields are lowercase)
                self.options['epic_id'] = self.options['epic_id'].lower()
            

    def read_data(self):
        """Generator to yield lines from each document in file"""
        # check for messages before starting
        self.check_msg_queue()
        # open the file
        with open(self.info['metadata']['filepath'],
                  'r',
                  encoding=self.options['r_encoding']) as file:
            # count the number of records
            count = 0
            # where we'll store the lines for each record
            lines = []
            # start the time and set state to Running
            self.progress['timer'] = time.time()
            self.progress['state'] = 'Running'
            # put the progress without waiting
            try:
                self.progress_queue.put_nowait(self.progress)
            except queue.Full:
                pass
            # create generator so we can skip the first line and get first entry
            generator = enumerate(file)
            # iterate through lines in file
            for index, line in generator:
                # skip first line and blank lines
                if line.strip() == '' or line == self.first_line:
                    continue
                # save the first line, we need to save last one to compare ids
                else:
                    last = self.read_helper(index, line)
                    break
            # if the user wants a header, give em a header
            if self.options['create_header']:
                # create a header with metadata (but get rid of text and line #)
                lines.append('{}\n'.format('\t'.join([value for key, value in last.items() if key != self.text_field and key != 'line'])))
            # add the line to the lines list
            lines.append(last[self.text_field])
            # keep going through generator
            for index, line in generator:
                # append blank lines, they'll be removed by writer if told to
                if line.strip() == '':
                    lines.append(line)
                    # continue with loop
                    continue
                # get line dictionary
                line_dict = self.read_helper(index, line)
                # if it's time to report progress/check message queues, do it
                if index % self.report_rate == 0:
                    # check messages
                    self.check_msg_queue()
                    # flush read-ahead buffer and get position in file
                    file.flush()
                    self.progress['progress'] = file.tell()
                    # report progress without waiting
                    try:
                        self.progress_queue.put_nowait(self.progress)
                    except queue.Full:
                        pass
                # check if it's a new record
                if last and line_dict[self.options['epic_id']] != last[self.options['epic_id']]:
                    # yield lines if there are any
                    if lines:
                        # increment number of records
                        count += 1
                        # delete the text from metadata and update the metadata
                        # you have to update metadata so it's for last record
                        del last[self.text_field]
                        self.info['metadata'].update(last)
                        # set lines for info dictionary and yield it
                        self.info['data'] = lines
                        yield self.info
                        # clear lines list
                        lines = []
                        # if they want a header, create one
                        if self.options['create_header']:
                            lines.append('{}\n'.format('\t'.join([value for key, value in line_dict.items() if key != self.text_field and key != 'line'])))
                        # add text from this line, because this is a new record
                        lines.append('{}\n'.format(line_dict[self.text_field]))
                # if it's not a new record, add the line
                else:
                    lines.append('{}\n'.format(line_dict[self.text_field]))
                last = line_dict
            # if there are still lines to be yielded, increment count
            if lines:
                count += 1
            # set state to finished and add count to progress dict
            self.progress['state'] = 'Finished'
            self.progress['processed'] = count
            # flush read-ahead buffer and get position in file
            file.flush()
            self.progress['progress'] = file.tell()
            # report progress - wait for this one
            self.progress_queue.put(self.progress)
            # if there are lines to yield, add them to info dict, update
            # metadata, and yield the dictionary
            if lines:
                del last[self.text_field]
                self.info['metadata'].update(last)
                self.info['data'] = lines
                yield self.info

    def read_helper(self, index, line):
        """Helper that processes the lines"""
        values = [value.strip() for value in line.split('\t')]
        if len(values) != len(self.fields):
            self.put_warning(self.info['metadata']['filename'], 'Line does not match header', index + 1)
        line_dict = dict(zip(self.fields, values))
        return line_dict
