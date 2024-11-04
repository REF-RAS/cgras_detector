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

import os, datetime, time, shutil, numbers, yaml
import pandas as pd
from enum import Enum
from datetime import datetime as dt
# project modules
import tools.db_tools as db_tools
from tools.lock_tools import synchronized
from tools.logging_tools import logger
from detector.database_file import DBFile

PERSISTENT_STORE_DDL = {
    'persistent_store':
    """
    CREATE TABLE IF NOT EXISTS persistent_store (
        name text PRIMARY KEY,
        value text
    );
    """,
}

class PersistentStoreDAO:
    CONFIG_TASK_EXECUTE_MODE = 'task_execute_mode'          # int type
    CONFIG_TILES_IMPORT_ENABLED = 'tiles_import_enabled'    # bool type
    CONFIG_SELECTED_SEASON = 'selected_season'              # string type
    
    AUTO_EXECUTE_OFF = 0
    AUTO_EXECUTE_ON = 1
    
    def __init__(self, db_file:str, **kwargs):
        self.db_file = db_file

    @synchronized
    def set_config_value(self, name:str, value):
        with db_tools.create_connection(self.db_file) as conn:
            c = conn.cursor()
            c.execute('REPLACE INTO general_config (name, value) VALUES (?, ?)', (name, value))
            conn.commit()
        return name   
    
    @synchronized
    def get_config_value(self, name:str, default=None, to_type=None):     
        with db_tools.create_connection(self.db_file) as conn:       
            c = conn.cursor() 
            result = c.execute('SELECT value FROM general_config WHERE name = ?', (name,)).fetchone()
            if result is None:
                return default
            value = result[0]
            try:
                if to_type == int:
                    return int(value)
                elif to_type == float:
                    return float(value)      
                elif to_type == bool:
                    return bool(value)               
            except Exception as ex:
                return default
            return value
        
    def update_task_execute_mode(self, new_mode):
        self.set_config_value(self.CONFIG_TASK_EXECUTE_MODE, new_mode)
    
    def get_task_execute_mode(self, default=None) -> int:
        return self.get_config_value(self.CONFIG_TASK_EXECUTE_MODE, default, to_type=int)
    
    def update_tiles_import_enabled(self, enabled:bool):
        self.set_config_value(self.CONFIG_TILES_IMPORT_ENABLED, 'True' if enabled else '')
    
    def get_tiles_import_enabled(self, default=False) -> bool:
        return self.get_config_value(self.CONFIG_TILES_IMPORT_ENABLED, default, to_type=bool)
    
# ------------------------------------------------
def manage_tables():
    CGRAS_HOME = '/home/qcr/cgras_data'
    DATABASE_FOLDER = os.path.join(CGRAS_HOME, 'database')
    DETECT_DBFM = DBFile(DATABASE_FOLDER, 'detector.db', PERSISTENT_STORE_DDL)
    DETECT_DBFM.drop_tables(['general_config'])
    tables_name = DETECT_DBFM.list_tables_name()
    logger.info(f'tables: {tables_name}')
    DETECT_DBFM.create_tables(['persistent_store'])
    DETECT_DBFM.dump_all_tables()       

# The main program for testing the clearing
# of database tables and creating them
if __name__ == '__main__':
    manage_tables()