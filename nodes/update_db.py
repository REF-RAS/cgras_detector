#!/usr/bin/env python3

# Copyright 2024 - Andrew Kwok Fai LUI, 
# Robotics and Autonomous Systems Group, REF, RI
# and the Queensland University of Technology

__author__ = 'Andrew Lui'
__copyright__ = 'Copyright 2024'
__license__ = 'GPL'
__version__ = '1.0'
__email__ = 'ak.lui@qut.edu.au'
__status__ = 'Development'

import os, sys, json, traceback
from detector.database_file import DBFile
from cgras_datatools import db_tools
from detector.model import APP_FILE_MANAGER, DETECT_DBFM, DetectorDAO, logger

DETECT_DBFILE = os.path.join(APP_FILE_MANAGER.database_folder, 'detector.db')

# function to change database table definitions based on release 0.6.0 to a new release
def run_update_table_definitions_060():
    sql_list = [
        # 'ALTER TABLE detected_object RENAME COLUMN contour_size TO contour_area',
        'ALTER TABLE detected_object ADD COLUMN contour_area real DEFAULT NULL',
        'ALTER TABLE detected_object ADD COLUMN confidence real DEFAULT NULL',
        'ALTER TABLE detected_object ADD COLUMN metadata text DEFAULT NULL'  
    ]
    for sql in sql_list:
        try:
            logger.info(f'Update: {sql}')
            db_tools.update(DETECT_DBFILE, sql)
        except:
            logger.warning(f'Error occurred in DB table update')
            traceback.print_exc()
    logger.info(f'Update DB tables completed')

# ------------------------------------------------
# The main program for running a command line 
# program for executing sql statements
if __name__ == '__main__':
    run_update_table_definitions_060()
