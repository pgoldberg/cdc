import configparser
import os

def create_config():
    config = configparser.ConfigParser(allow_no_value=True)

    config['MAIN'] = {}
    config.set('MAIN', '# General settings')
    config.set('MAIN', '; This setting enables/disables log file creation in the output folder')
    config['MAIN']['create_logfile'] = 'True'
    config.set('MAIN', '; This setting is the time format for the logfile name. See datetime docs for strftime for formatting details.')
    config['MAIN']['logfile_timestamp'] = '%%Y-%%m-%%d-%%H.%%M.%%S'
    config['CLI'] = {}
    config.set('CLI', '# CLI settings')
    config.set('CLI', '; Check the CLI communication queue every n milliseconds')
    config.set('CLI', 'comm_queue_refresh_rate', '100')
    config['GUI'] = {}
    config.set('GUI', '# GUI settings')
    config.set('GUI', '; The following settings determine the default size of the main window')
    config['GUI']['main_def_height'] = '600'
    config['GUI']['main_def_width'] = '600'
    config.set('GUI', '; The following settings determine the minimum sizes of all windows')
    config['GUI']['main_min_height'] = '500'
    config['GUI']['main_min_width'] = '530'
    config['GUI']['help_min_height'] = '500'
    config['GUI']['help_min_width'] = '540'
    config['GUI']['about_min_height'] = '400'
    config['GUI']['about_min_width'] = '460'
    config.set('GUI', '; This setting is the time format for the GUI log entries. See datetime docs for strftime for formatting details.')
    config['GUI']['gui_log_timestamp'] = '%%H:%%M:%%S - %%m-%%d-%%Y'
    config.set('GUI', '; Check the GUI communication queue every n milliseconds')
    config.set('GUI', 'comm_queue_refresh_rate', '100')
    config['PROGRESS'] = {}
    config.set('PROGRESS', '# Settings related to progress updates in the GUI')
    config.set('PROGRESS', '; Rate to update progress, measured in lines of the input file (updates progress every n lines)')
    config['PROGRESS']['report_rate'] = '10000'
    config.set('PROGRESS', '; Update the GUI progress bars every n milliseconds')
    config['PROGRESS']['gui_refresh_rate'] = '100'
    config.set('PROGRESS', '; Update the CLI progress every n milliseconds')
    config['PROGRESS']['cli_refresh_rate'] = '100'
    config.set('PROGRESS', '; The number of warnings to send to the main process at a time')
    config['PROGRESS']['warning_list_size'] = '1000'
    config['WRITE'] ={}
    config.set('WRITE', '# Settings related to writing')
    config.set('WRITE', '; Writing buffer size')
    config['WRITE']['OutputBufferSize'] = '8192'
    config['write.canary'] = {}
    config.set('write.canary', '# Settings related to the Canary writer')
    config.set('write.canary', '; Possible ID fields for Canary format (comma-delimited list)')
    config['write.canary']['Autodetect_HeaderList'] = ', '.join(['Autodetect', 'NOTE_ID', 'Report_Number', 'Record_Id', 'Encounter_Number', 'Accession', 'Accession_Number', 'Microbiology_Number', "*time"])
    config['read.rpdr'] = {}
    config.set('read.rpdr', '# Settings related to the RPDR reader')
    config.set('read.rpdr', '; Possible text fields for RPDR format (comma-delimited list)')
    config['read.rpdr']['Text_Fields'] = ', '.join(['Report_Text', 'Comments', 'Organism_Text'])
    config['read.epic'] = {}
    config.set('read.epic', '# Settings related to the Epic Text reader')
    config.set('read.epic', '; Possible text fields for Epic Text  (comma-delimited list)')
    config['read.epic']['Text_Fields'] = ', '.join(['NOTE_TEXT'])
    config.set('read.epic', '; Possible ID fields for Epic Text to distinguish between records (comma-delimited list)')
    config['read.epic']['Autodetect_Epic_ID'] = ', '.join(['Autodetect', 'NOTE_ID'])
    filedir = os.path.abspath(os.path.dirname(__file__))
    with open(os.path.join(filedir, 'canarydc.ini'), 'w') as configfile:
        config.write(configfile)

if __name__ == '__main__':
    create_config()