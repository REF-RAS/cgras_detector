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

import os, sys
from detector.database_file import DBFile
from tools import db_tools
from detector.model import APP_FILE_MANAGER, DETECT_DBFM
import tools.db_tools

COORDINATOR_DBFILE = os.path.join(APP_FILE_MANAGER.database_folder, 'coordinator.db')
COORDINATOR_DBFM = DBFile(APP_FILE_MANAGER.database_folder, 'coordinator.db', {})
DETECT_DBFILE = os.path.join(APP_FILE_MANAGER.database_folder, 'detector.db')


# The function that supports interactive execution of sql statements 
def run_db():
    while True:
        print(f'''
        (E): Exit
        (1): COORDINATOR
        (2): DETECT
        (3): Setup Database
        ''')
        command = input('Select DB: ')
        if command == 'E':
            sys.exit(0)
        elif command == '1':
            db_file = COORDINATOR_DBFILE
        elif command == '2':
            db_file = DETECT_DBFILE
        elif command == '3':
            DETECT_DBFM.create_tables()
            continue

        print(f'''
        (E): Exit
        (Q): Run Query
        (U): Run Update
        ''')

        command = input('Command: ')
        if command == 'E':
            sys.exit(0)
        if db_file == DETECT_DBFILE:
            table_names = DETECT_DBFM.list_tables_name()
        else:
            table_names = COORDINATOR_DBFM.list_tables_name()
        print(f'Table names: {table_names}')
        if command == 'Q':
            while True:
                sql = input('Enter SQL: ')
                if not sql: break
                try:
                    df = db_tools.query(db_file, sql)
                    print(df)
                except Exception as e:
                    print(f'Error: {e}')
        elif command == 'U':
            while True:
                sql = input('Enter SQL: ')
                if not sql: break
                try:
                    result = db_tools.update(db_file, sql)
                    print(result)
                except Exception as e:
                    print(f'Error: {e}')

# ------------------------------------------------
# The main program for running a command line 
# program for executing sql statements
if __name__ == '__main__':
        run_db()
