"""Contains class for writing plain text files"""
import os
from encodings.aliases import aliases
import datetime
import cdc
from .write import Write

class WriteTXT(Write):
    """.txt Writer"""
    # required class variables for interface labels and description
    GUI_LABELS = ['Plain Text']
    CLI_LABELS = ['txt', 'text', 'plain_text']
    DESCRIPTION = 'All files with the ".txt" extension.'

    # UC_PROPS class variable with the base class UC_PROPS added
    UC_PROPS = Write.UC_PROPS + [
        {'flag': '--outdir',
         'name': '--output-directory',
         'label': 'Folder',
         'action': 'store',
         'default': None,
         'type': str,
         'help': 'Choose the directory to write the converted files to',
         'var': 'output_dir',
         'outtype': 'dir',
         'position': -1001,
         'required': False},
        {'flag': '--filename',
         'name': '--output-filename',
         'label': 'Output Filename',
         'action': 'store',
         'default': None,
         'gui_default': '',
         'type': str,
         'help': 'The name for your output file(s)',
         'var': 'output_filename',
         'position': -1000,
         'required': False},
        {'flag': '--wenc',
         'name': '--w-encoding',
         'label': 'Encoding',
         'action': 'store',
         'default': 'utf8',
         'type': str,
         'help': 'Choose what encoding to use for writing the output file. utf8 is the default, which will work for most files.',
         'var': 'w_encoding',
         'gui_choices': sorted(aliases.keys()),
         'position': 1,
         'required': True},
        {'flag': '--ibl',
         'name': '--ignore-blank-lines',
         'label': 'Ignore Blank Lines',
         'action': 'store_true',
         'default': False,
         'help': 'Choose whether to ignore blank lines when writing file',
         'var': 'ignore_blank_lines',
         'position': 2,
         'required': False},
        # {'flag': '--mll',
        #  'name': '--min-line-length',
        #  'label': 'Minimum Line Length',
        #  'action': 'store',
        #  'default': None,
        #  'type': int,
        #  'help': 'Choose a minimum line length where lines greater than this value are ignored',
        #  'var': 'min_line_len',
        #  'position': 4,
        #  'required': False},
        {'flag': '--lc',
         'name': '--lowercase',
         'label': 'Lowercase',
         'action': 'store_true',
         'default': False,
         'help': 'Write the output file in all lowercase',
         'var': 'lowercase',
         'position': 3,
         'required': False},
        {'flag': '--unwrap',
         'name': '--text-unwrap',
         'label': 'Text Unwrapping',
         'action': 'store_true',
         'gui_default': False,
         'default': False,
         'help': 'This option attempts to remove end-of-lines that do not represent ends of sentences, common in word-wrapped documents. Enabling can improve sentence boundary detection.',
         'var': 'text_unwrap',
         'position': 4,
         'required': False},
        {'flag': '--wrap',
         'name': '--text-wrap',
         'label': 'Text Wrapping',
         'action': 'store',
         'gui_default': 40,
         'default': None,
         'type': int,
         'help': 'Wrap text with the specified line length (in characters).',
         'var': 'text_wrap',
         'position': 5,
         'required': False},
    ]

    # sort the UC_PROPS on the position key
    UC_PROPS = sorted(UC_PROPS, key=lambda k: k['position'])

    def __init__(self, options, read_file):
        super().__init__(options, read_file)

        # if the filename was provided, make sure the extension is there
        if self.options['output_filename'] is not None and len(self.options['output_filename']):
            if self.options['output_filename'].split('.')[-1] != 'txt':
                self.options['output_filename'] += '.txt'
        # else create the filename from input
        else:
            # get input filename
            filename = self.read_file.info['metadata']['filename']
            # make sure you make the extension .txt
            namelist = filename.split('.')
            namelist[-1] = 'txt'
            # join it back together
            filename = '.'.join(namelist)
            # set the output filename
            self.options['output_filename'] = filename

        self.wrap = None
        if self.options["text_wrap"]:
            import textwrap
            self.wrap = textwrap.TextWrapper(self.options["text_wrap"])

        self.unwrapper = None
        if self.options["text_unwrap"]:
            from ..utils.textunwrapper.unwrapper import RuleBasedUnwrapper
            self.unwrapper = RuleBasedUnwrapper()
            #print(self.unwrapper)
       
        
    def write_dir(self):
        """Writes file(s) to a directory"""
        # count files so we can distinguish multiple output files
        count = 1
        # iterate through records yielded by reader generator
        for info in self.read_file.read_data():
            # add numbers to output filename for multiple file output
            name = self.options['output_filename'].split('.')
            name[-2] = '{} ({})'.format(name[-2], count)
            name = '.'.join(name)
            path = os.path.join(self.options['output_dir'], name)

            # make sure you aren't overwriting
            path = self.get_safe_path(path)

            # get buffer size
            buffer = cdc.CONFIG.getint('WRITE', 'OutputBufferSize', fallback=8192)
            
            try:
                # open output file for writing
                with open(path, 'w', buffer, encoding=self.options['w_encoding']) as file:
                    # run it through process_data generator and write line-by-line
                    file.write(self.get_document(info))

                # increment count for the next file
                count += 1
            except:
                os.remove(path)
                raise

    def process_data(self, info):
        """Generator for processing the data with the UC_PROPS"""

        # go through the lines and perform any in-place modifications
        for i, line in enumerate(info['data']):
            # process user-specified properties  
            if self.options['lowercase']:
                info['data'][i] = line.lower()

		# Remove blank lines
        if self.options['ignore_blank_lines']:
            info["data"] = [line for line in info["data"] if line.strip()]

        # text wrapping
        if self.wrap:
            info["data"] = self.wrap.wrap(''.join(info['data']))
            info["data"] = [line + "\n" for line in info["data"]]	# should not need to do this

        if self.unwrapper:
            # do not include the first line
            unwrapped = self.unwrapper.process(''.join(info['data'][1:]))
            info["data"] = [info["data"][0]] + self.unwrapper.render(unwrapped, "reflow").splitlines(True)
            
        return info

    def get_document(self, info):
        document = ''.join(self.process_data(info)['data'])
        return document


class WriteDelimTXT(WriteTXT):
    """.txt Writer"""

     # required class variables for interface labels and description
    GUI_LABELS = ['Delimited Plain Text']
    CLI_LABELS = ['delim_txt']
    DESCRIPTION = 'Plain text files (with the ".txt" extension) that contain several documents separated by a delimiter.'

    # UC_PROPS class variable with the ones inherited from WriteTXT
    UC_PROPS = [
        {'flag': '--outdelim',
         'name': '--output-delimiter',
         'label': 'Delimiter',
         'action': 'store',
         'default': '===',
         'type': str,
         'help': 'Output a single file containing all records separated by a delimiter',
         'var': 'concat_delim',
         'required': True,
         'position': -1}
    ] + WriteTXT.UC_PROPS

    # sort UC_PROPS
    UC_PROPS = sorted(UC_PROPS, key=lambda k: k['position'])

    # nothing special for constructor, just inherit it

    def write_dir(self):
        """Write file to a directory"""
        # build path and make sure it's safe to write to
        path = os.path.join(self.options['output_dir'], self.options['output_filename'])
        path = self.get_safe_path(path)
        # get buffer size
        buffer = cdc.CONFIG.getint('WRITE', 'OutputBufferSize', fallback=8192)
        try:
            # open file for writing
            with open(path, 'w', buffer, encoding=self.options['w_encoding']) as file:
                # iterate through records in input file
                for info in self.read_file.read_data():
                    # run it through process_data generator and write line-by-line
                    file.write(self.get_document(info))
        except:
            os.remove(path)
            raise

    def process_data(self, info):
        """Generator for processing the data with the UC_PROPS"""
        # process the lines with the super-generator
        info = super().process_data(info)
        # if the user didn't provide a delimiter, yield default
        if self.options['concat_delim'] is None:
            info['data'].insert(0, '===\n')
        # otherwise yield the user-provided delimiter
        else:
            info['data'].insert(0, '{}\n'.format(self.options['concat_delim']))
        return info