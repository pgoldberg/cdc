"""Contains superclass for writing files"""
import os

from ..utils.ucprop import UCPropMixin

class Write(UCPropMixin, object):
    """Superclass for writing files"""

    # required class variables
    GUI_LABELS = []
    CLI_LABELS = []
    DESCRIPTION = ''

    def __init__(self, options, read_file):
        # create instance variables for options and reader object
        self.options = options
        self.read_file = read_file
    
    def get_safe_path(self, path):
        """Returns a path that won't cause overwriting"""
        # store the old path
        old_path = path
        # count to append to filename
        count = 1
        # list of the basename separated by a period (to ignore extension)
        basename = os.path.basename(path).split('.')
        # run as long as the path exists already
        while os.path.exists(path):
            # copy basename list to alter it while saving original
            name = basename[:]
            # add number to the end of the name before the extension
            name[-2] = '{} ({})'.format(name[-2], count)
            # join it back together
            name = '.'.join(name)
            # join the full path
            path = os.path.join(self.options['output_dir'], name)
            # increment the count
            count += 1
        # # if it was changed, log a warning
        # if old_path != path:
        #     self.read_file.put_warning(self.read_file.info['metadata']['filename'], 'Output filename changed to {} to prevent overwriting.'.format(os.path.basename(path)))
        # set the output path in the progress dict so it can be logged
        self.read_file.progress['output_path'] = path
        # return the path
        return path
