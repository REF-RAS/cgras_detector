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

import os, datetime, time, shutil
from enum import Enum
from datetime import datetime as dt
# project modules
import tools.db_tools as db_tools
import tools.file_tools as file_tools
from tools.lock_tools import synchronized
from tools.logging_tools import logger

 
# This class models the management and backup of db files and the folder that contains the files
class DBFileManager():
    def __init__(self, database_folder:str, db_filename:str, ddb_commands:dict):
        assert database_folder is not None and db_filename is not None, 'Parameters either (database_folder, db_filename) is None'
        assert ddb_commands is not None, 'Parameter (ddb_comamnds) is None'
        assert ddb_commands is not None, 'Parameter (ddb_commands) is not the expected dict type with table names as keys and DDL commands as values'
        if not os.path.isdir(database_folder):
            raise AssertionError(f'{type(self).__name__}: Parameter (database_folder) is not an existing directory')
        # input parameters
        self.ddb_commands = ddb_commands
        self.table_names = ddb_commands.keys()
        self.db_filename = db_filename
        try:
            self.db_parent_folder = os.path.realpath(database_folder)
            self.db_file = os.path.realpath(os.path.join(database_folder, db_filename))
            
            logger.info(f'DBFileManager: Setup db_file "{self.db_file}"')
            # - test if the db_file exists, if not, create one
            if not os.path.isfile(self.db_file):
                self.create_tables()
            else:
                # - making a backup of the database file if it has not been made this day
                # self._make_daily_backup()
                ...
        except Exception as e:
            raise AssertionError(f'system database setup error: {e}')
    
    # ------- manage the sqlite3 database files    
    def _make_daily_backup(self):
        today = datetime.date.today()
        date_str = today.strftime("%Y%m%d")
        daily_backup_filename = f'{date_str}_{self.db_filename}'
        daily_backup_path = os.path.join(self.db_parent_folder, daily_backup_filename)
        if os.path.isfile(daily_backup_path):
            return
        shutil.copyfile(self.db_file, daily_backup_path)
    
    def make_backup(self, label='S', use_move=False):
        now = datetime.now()
        time_str = now.strftime("%Y%m%d-%H%M%S")
        daily_backup_filename = f'{time_str}-{label}_{self.db_filename}' 
        daily_backup_path = os.path.join(self.db_parent_folder, daily_backup_filename)
        if os.path.isfile(daily_backup_path):
            return
        if use_move:
            shutil.move(self.db_file, daily_backup_path)        
        else:
            shutil.copyfile(self.db_file, daily_backup_path)               
        
    def get_backup_files(self):
        file_info_dict = dict()
        for f in os.listdir(self.db_parent_folder):
            fpath = os.path.join(self.db_parent_folder, f)
            if not os.path.isfile(fpath) :
                continue
            if f == self.db_filename or self.db_filename not in f:
                continue 
            backup_date, _ = f.split('_', 1)
            file_info_dict[backup_date] = f
        return file_info_dict
    
    def restore_backup(self, backup_filename):
        backup_filepath = os.path.join(self.db_parent_folder, backup_filename)
        if not os.path.isfile(backup_filepath) :
            return
        # make a backup of the existing db_file
        self.make_backup(label='RES', use_move=True)
        # make a copy of the backup file and save as db_file
        shutil.copyfile(backup_filepath, self.db_file)

    # ------- manage the sqlite3 database files        
    def drop_tables(self, table_list=None):
        """ A convenient function for dropping all tables by executing the given script
        
        :param table_list: A list containing the names of the tables to be dropped, or a string of a single table name, or None for all tables
        :return: The error as a string if any
        """
        os.makedirs(file_tools.get_parent(self.db_file), exist_ok=True)
        if table_list is None:
            table_list = self.table_names
        elif type(table_list) == str:
            table_list = [table_list]
        for table in table_list:
            db_tools.update(self.db_file, f'DROP TABLE IF EXISTS {table}')        

    def create_tables(self, table_list=None):
        """ A convenient function for creating all database tables for the bagfiles capturer
        
        :param table_list: A list containing the names of the tables to be created, or a string of a single table name, or None for all tables
        :return: The error as a string if any
        """
        count = 0
        error_list = []
        os.makedirs(file_tools.get_parent(self.db_file), exist_ok=True)
        if table_list is None:
            table_list = self.ddb_commands.keys()
        elif type(table_list) == str:
            table_list = [table_list]
            
        for table_name in table_list:
            create_sql = self.ddb_commands.get(table_name, None)
            if create_sql is None:
                logger.warning(f'{__file__} (create_tables): No DDL SQL script has been specified for the given table name {table_name}')
                continue
            result = db_tools.update_with_script_no_exception(self.db_file, create_sql)
            if result is None:
                logger.info(f'{__file__} (create_tables): successful in the execution of {create_sql}')
                count += 1
            else:
                error_list.append(result)
                logger.warning(f'{__file__} (create_tables): error {result} in in the execution of {create_sql}')
        if len(error_list) == 0:
            return None
        return '\n'.join(error_list)

    def clear_tables(self):
        """ A convenient function for clearing the data of the tables in the database using the commands in CLEAR_TABLE_SQL 

        :param db_file: The path to the sqlite db file
        :return: The error as a string if any
        """
        for table in self.table_names:
            db_tools.update(self.db_file, f'DELETE FROM {table}')

    def clear_all_tables(self):
        """ A convenient function for clearing the data of all tables in the database

        :param db_file: The path to the sqlite db file
        :return: The error as a string if any
        """
        table_names_list = db_tools.list_table_names(self.db_file)
        for table_name in table_names_list:
            db_tools.clear_table(self.db_file, table_name)

    def list_tables_name(self) -> list:
        """ Return a list of table names in this database

        :return: A list of table names
        :rtype: list
        """
        return db_tools.list_table_names(self.db_file)

    def dump_all_tables(self, limit:int=50):
        """ A convenient function for printing the data of all tables to the screen

        :param db_file: The path to the sqlite db file
        :return: The error as a string if any
        """
        table_names_list = db_tools.list_table_names(self.db_file)
        for table_name in table_names_list:
            logger.info(f'Table: {table_name}')
            logger.info(f'{db_tools.dump_table_df(self.db_file, table_name, limit)}')



# ------------------------------------------------
# the test program
TEST_DDL = {
    'tile':
    """
    CREATE TABLE IF NOT EXISTS tile (
        tile_id text PRIMARY KEY,
        pit_id text,
        species_id integer,
        settle_time real,
        season text,
        metadata text,
        UNIQUE (tile_id),
        UNIQUE (pit_id),
        FOREIGN KEY (species_id) REFERENCES species (id)
    );
    """,
    'species':
    """
    CREATE TABLE IF NOT EXISTS species (
        id integer PRIMARY KEY,
        name text,
        UNIQUE (name)
    );
    """
}

if __name__ == '__main__':  
    CGRAS_HOME = '/home/qcr/cgras_data'
    DATABASE_FOLDER = os.path.join(CGRAS_HOME, 'database')
    DETECTOR_DBFM = DBFileManager(DATABASE_FOLDER, 'detector.db', TEST_DDL)
    DETECTOR_DBFM.dump_all_tables()

