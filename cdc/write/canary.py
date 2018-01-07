"""Contains class for writing files in Canary's format"""
import time, datetime
import copy
import random

import cdc
from .text import WriteDelimTXT
from ..utils import ucprop

class WriteCanary(WriteDelimTXT):
    """Canary Writer"""
    # required class variables for interface labels and description
    GUI_LABELS = ['Canary']
    CLI_LABELS = ['canary']
    DESCRIPTION = 'The file format used by Canary, a user-friendly information extraction tool. These files are plain text files, with a ".txt" extension.'

    ID_FIELDS = [field.strip() for field in cdc.CONFIG.get('write.canary', 'Autodetect_HeaderList', fallback='Autodetect, NOTE_ID, Report_Number, Record_Id, Encounter_Number, Accession, Accession_Number, Microbiology_Number, *time').split(',')]

    # UC_PROPS plus those inherited
    UC_PROPS = [
        {'flag': '--id',
         'name': '--id-field',
         'label': 'Field for Record ID',
         'action': 'store',
         'default': ID_FIELDS[0],
         'type': str,
         'gui_help': 'The metadata field from the input file to use for record identification.',
         'help': 'The metadata field from the input file to use for record identification. Some available choices are: {}.'.format(', '.join([choice.lower() for choice in ID_FIELDS])),
         'gui_choices': ID_FIELDS,
         'var': 'id_field',
         'required': True,
         'position': 0}
    ] + copy.deepcopy(WriteDelimTXT.UC_PROPS)

    # Change the delimiter prop we inherit
    ucprop.update_ucprop(UC_PROPS, "--outdelim", {"flag": "--canary-delim", "name": "--canary-delimiter", "default": "*|#*|#*|#1*|#*|#*|#", "var": "canary_delim"})
    
    # sort UC_PROPS
    UC_PROPS = sorted(UC_PROPS, key=lambda k: k['position'])

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # find the ID field
        if (self.options['id_field'].lower() == 'autodetect'):
                # if it's autodetect, get the possible id fields
            self.options['id_field'] = [choice.lower() for choice in self.ID_FIELDS]
            # delete autodetect from the list
            self.options['id_field'].remove('autodetect')

            # go through possible fields
            for field in self.options['id_field']:
                # if there's an asterisk in front of it, we're generating the id
                if field[0] == '*':
                    # if it's the time (all there is right now), set the 
                    # id_field entry
                    if field[1:] == "time":
                        self.options['id_field'] = field
                    break
                # if the field is in the metadata, then we've found out id field
                if field in self.read_file.info['metadata']:
                    self.options['id_field'] = field
                    break
        # if the user specified it, set it
        else:
            self.options['id_field'] = self.options['id_field'].lower()

            
    def get_timestamp_id(self):
        """Return an ID based on the time and a random number."""
        return datetime.datetime.now().strftime('%H%M%S%f') + str(random.randint(100000, 999999))  # time and random 6 digit number

    def process_data(self, info):
        """Generator for processing the data with the UC_PROPS"""
        # This writer is based on the delimited text writer
        # What it specifically does is customize the delimiter for each record
        # Then we store this in 'concat_delim' which is the variable used by WriteDelimTXT

        # if id field is the time, get the time and add it to the delimiter
        if self.options['id_field'] == '*time':
            self.options['concat_delim'] = '{}{}'.format(self.get_timestamp_id(), self.options['canary_delim'])
        # if id field is in metadata, add value to delimiter
        elif self.options['id_field'] in info['metadata'] and info['metadata'][self.options['id_field']].strip() != '':
            self.options['concat_delim'] = '{}{}'.format(info['metadata'][self.options['id_field']], self.options['canary_delim'])
        # if there is no id, use time and report a warning
        elif self.options['id_field'] not in info['metadata'] or info['metadata'][self.options['id_field']].strip() == '':
            time_id = self.get_timestamp_id()
            self.options['concat_delim'] = '{}{}'.format(time_id, self.options['canary_delim'])

            if 'line' in info:
                self.read_file.put_warning(info['metadata']['filename'], 'Could not find record ID, using {} instead'.format(time_id), info['line'])
            else:
                self.read_file.put_warning(info['metadata']['filename'], 'Could not find record ID, using {} instead'.format(time_id))

        return super().process_data(info)
