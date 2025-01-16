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

import os, datetime, time, shutil, contextlib
from enum import Enum
from datetime import datetime as dt
# project modules
import cgras_datatools.db_tools as db_tools
import cgras_datatools.file_tools as file_tools
from cgras_datatools.lock_tools import synchronized
from cgras_datatools.logging_tools import logger

# This class is used by the database DBFile class to manage the backup of the database file
# It makes daily backup file, and remove those older than a prescribed days, but keep some of those permanently following a cycle of days
class BackupFileManager():
    DATE_FORMAT = '%Y%b%d'
    RECORD_FILENAME = '.permanent_backup.csv'
    def __init__(self, the_folder:str, the_file:str, **kwargs):
        self.the_folder = the_folder
        self.the_file = the_file
        # check validity of input parameters
        assert self.the_folder is not None and os.path.isdir(self.the_folder), 'Parameter (the_folder) is None or the folder does not exist'
        # assert self.the_file is not None and os.path.isfile(os.path.join(self.the_folder, self.the_file)), 'Parameter (the_file_list) is None or the file does not exist'
        # extract other input parameters
        self.daily_backup_keep_days = kwargs.get('daily_backup_keep_days', 7)   # days
        self.permanant_backup_cycle_days = kwargs.get('permanant_backup_cycle_days', 30)   # days
        # load the hidden record file
        self.permanant_backup_file_list = []
        self.permanent_backup_dt_list = []
        self.permanent_backup_dt_latest = None
        with contextlib.suppress(Exception):
            with open(os.path.join(the_folder, self.RECORD_FILENAME)) as infile:
                for line in infile:
                    line = line.strip()
                    filename_parts = line.split('_')
                    if len(filename_parts) < 2:
                        continue
                    if filename_parts[1] != the_file:
                        self.permanant_backup_file_list.append(line)
                        continue
                    self.permanant_backup_file_list.append(line)
                    dt = datetime.datetime.strptime(filename_parts[0], self.DATE_FORMAT).date()
                    self.permanent_backup_dt_list.append(dt)
                    if self.permanent_backup_dt_latest is None or dt > self.permanent_backup_dt_latest:
                        self.permanent_backup_dt_latest = dt

        # make the daily backup
        self._make_daily_backup(self.the_folder, self.the_file)
        # remove the old backup files except those considered 
        self._remove_daily_backup_except_permanent(self.the_folder, self.the_file)
        # save the latest list of permanant backup to the file
        try:
            with open(os.path.join(the_folder, self.RECORD_FILENAME), 'w') as outfile:
                for line in self.permanant_backup_file_list:
                    outfile.write(f'{line}\n')
        except:
            ...

    def _generate_backup_filename(self, the_file:str, date_str:str=None) -> str:
        if date_str is None:
            today_dt = datetime.date.today()
            date_str = today_dt.strftime(self.DATE_FORMAT)
        return f'{date_str}_{the_file}'

    # make a backup to the file indexed by today's date    
    def _make_daily_backup(self, the_folder, the_file, use_move=False):
        daily_backup_filename = self._generate_backup_filename(the_file)
        daily_backup_path = os.path.join(the_folder, daily_backup_filename)
        if os.path.isfile(daily_backup_path):
            return
        the_file_path = os.path.join(the_folder, the_file)
        if not os.path.isfile(the_file_path):
            return
        if use_move:
            shutil.move(the_file_path, daily_backup_path)        
        else:
            shutil.copyfile(the_file_path, daily_backup_path)

    # remove daily backup files older than daily_backup_keep_days 
    def _remove_daily_backup_except_permanent(self, the_folder, the_file):
        today_dt = datetime.date.today()
        # backup files to be deleted: all files older than daily_backup_keep_days AND not a permanant backup (older than 30 days)
        # the permanently kept backup: iterate all files in the folder 
        backup_files = [f for f in os.listdir(the_folder) if os.path.isfile(os.path.join(the_folder, f)) and f.endswith(the_file)]
        backup_files_to_remove = []
        backup_file_to_remove_latest = backup_file_to_remove_latest_dt = None
        # iterate through the backup files of the_file and sort the older than daily_backup_keep_days to a list and record the latest one
        for f in backup_files:
            filename_parts = f.split('_')
            if len(filename_parts) < 2:  # if the filename is not of the correct format, ignore
                continue
            if filename_parts[1] != the_file:
                continue            
            # evaluate the date of the backup file and determine if it is older than daily_backup_keep_days 
            try:
                f_dt = datetime.datetime.strptime(filename_parts[0], self.DATE_FORMAT).date()
                f_days_old = (today_dt - f_dt).days
                if f_days_old > self.daily_backup_keep_days:
                    if f not in self.permanant_backup_file_list:         # ignore the file if it is a permanant backup file    
                        backup_files_to_remove.append(f)
                        if backup_file_to_remove_latest is None or f_dt > backup_file_to_remove_latest_dt:
                            backup_file_to_remove_latest = f
                            backup_file_to_remove_latest_dt = f_dt
            except Exception as e:
                continue
        # check if the latest one should be considered as a permanant backup
        if backup_file_to_remove_latest is not None and (self.permanent_backup_dt_latest is None or (backup_file_to_remove_latest_dt - self.permanent_backup_dt_latest).days > self.permanant_backup_cycle_days):
            backup_files_to_remove.remove(backup_file_to_remove_latest)
            self.permanant_backup_file_list.append(backup_file_to_remove_latest)
            self.permanent_backup_dt_list.append(backup_file_to_remove_latest_dt)
            self.permanent_backup_dt_latest = backup_file_to_remove_latest_dt
        # remove the filtered backup files
        for f in backup_files_to_remove:
            try:
                os.remove(os.path.join(the_folder, f))
                logger.info(f'BackFileManager: removed backup file: {os.path.join(the_folder, f)}')
            except:
                logger.warning(f'BackupFileManager unable to remove old backup file: {f}')

# This class models the management and backup of db files and the folder that contains the files
class DBFile():
    def __init__(self, database_folder:str, db_filename:str, ddl_commands:dict):
        assert database_folder is not None and db_filename is not None, 'Parameters either (database_folder, db_filename) is None'
        assert ddl_commands is not None, 'Parameter (ddl_commands) is None'
        assert type(ddl_commands) in (list, dict), 'Parameter (ddl_commands) is not the expected dict type with table names as keys and DDL commands as values'
        if not os.path.isdir(database_folder):
            raise AssertionError(f'{type(self).__name__}: Parameter (database_folder) is not an existing directory')
        # input parameters: convert ddl commands in a list to a single dict
        if isinstance(ddl_commands, list):
            self.ddl_commands = dict()
            for ddl_dict in ddl_commands:
                if not isinstance(ddl_dict, dict):
                    raise AssertionError(f'Parameter (ddl_commands) is a list but one of the list item is not a dict')
                self.ddl_commands.update(ddl_dict)
        else:
            self.ddl_commands = ddl_commands
        # input parameters
        self.table_names = self.ddl_commands.keys()
        self.db_filename = db_filename
        try:
            self.db_parent_folder = os.path.realpath(database_folder)
            self.db_file = os.path.realpath(os.path.join(database_folder, db_filename))
            
            logger.info(f'DBFile: setup db_file "{self.db_file}"')
            # - test if the db_file exists, if not, create one
            if not os.path.isfile(self.db_file):
                self.create_tables()
        except Exception as e:
            raise AssertionError(f'DBFile: system database setup error: {e}')
        # handle backup of database files
        self.backup_manager = BackupFileManager(self.db_parent_folder, db_filename)

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
            table_list = self.ddl_commands.keys()
        elif type(table_list) == str:
            table_list = [table_list]
            
        for table_name in table_list:
            create_sql = self.ddl_commands.get(table_name, None)
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
    DETECTOR_DBFM = DBFile(DATABASE_FOLDER, 'detector.db', TEST_DDL)
    DETECTOR_DBFM.dump_all_tables()

