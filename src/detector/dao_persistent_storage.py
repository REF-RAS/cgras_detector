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

import os, datetime, time, shutil, numbers, yaml, json
import pandas as pd
from enum import Enum
from datetime import datetime as dt
# project modules
import tools.db_tools as db_tools
from tools.lock_tools import synchronized
from tools.logging_tools import logger
from detector.database_file import DBFile

PERSISTENT_STORE_DDL = {
    'general_config':
    """
    CREATE TABLE IF NOT EXISTS general_config (
        name text PRIMARY KEY,
        value text
    );
    """,
}

class PersistentStoreDAO:
    CONFIG_SELECTED_SEASON = 'selected_season'              # string type
    
    # AUTO_EXECUTE_OFF = 0
    # AUTO_EXECUTE_ON = 1
    
    def __init__(self, db_file:str, **kwargs):
        self.db_file = db_file

    @synchronized
    def set_config_value(self, name:str, value):
        try:
            value = json.dumps(value)
        except:
            return None
        with db_tools.create_connection(self.db_file) as conn:
            c = conn.cursor()
            c.execute('REPLACE INTO general_config (name, value) VALUES (?, ?)', (name, value))
            conn.commit()
        return name   
    
    @synchronized
    def get_config_value(self, name:str, default=None):     
        with db_tools.create_connection(self.db_file) as conn:       
            c = conn.cursor() 
            result = c.execute('SELECT value FROM general_config WHERE name = ?', (name,)).fetchone()
            if result is None:
                return default
            value = result[0]
            try:
                value = json.loads(value)
            except Exception as ex:
                return default
            return value
    
    @synchronized
    def delele_config(self, name:str):
        with db_tools.create_connection(self.db_file) as conn:
            c = conn.cursor()
            c.execute('DELETE FROM general_config WHERE NAME = ?', (name,))
            conn.commit()        
            
    def list_config_all(self):
        results = db_tools.query_for_list_of_dicts(self.db_file, 'SELECT * FROM general_config')        
        return results
    
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

def test_persistent_store():
    CGRAS_HOME = '/home/qcr/cgras_data'
    DATABASE_FOLDER = os.path.join(CGRAS_HOME, 'database')
    DETECT_DBFM = DBFile(DATABASE_FOLDER, 'detector.db', PERSISTENT_STORE_DDL)
    PERSISTENT_STORE_DAO = PersistentStoreDAO(DETECT_DBFM.db_file)
    PERSISTENT_STORE_DAO.set_config_value('test_a', True)
    PERSISTENT_STORE_DAO.set_config_value('test_b', [True, False])
    PERSISTENT_STORE_DAO.set_config_value('test_c', 1)
    PERSISTENT_STORE_DAO.set_config_value('test_d', 'ABC')
    PERSISTENT_STORE_DAO.set_config_value('test_e', 1.23)
    PERSISTENT_STORE_DAO.set_config_value('test_f', {'ABC': 1.23})
    results = PERSISTENT_STORE_DAO.list_config_all()
    print(results)
    print(v:=PERSISTENT_STORE_DAO.get_config_value('test_a'), type(v))
    print(v:=PERSISTENT_STORE_DAO.get_config_value('test_b'), type(v))
    print(v:=PERSISTENT_STORE_DAO.get_config_value('test_c'), type(v))
    print(v:=PERSISTENT_STORE_DAO.get_config_value('test_d'), type(v))
    print(v:=PERSISTENT_STORE_DAO.get_config_value('test_e'), type(v))
    print(v:=PERSISTENT_STORE_DAO.get_config_value('test_f'), type(v))   
    PERSISTENT_STORE_DAO.set_config_value('test_a', False)
    print(v:=PERSISTENT_STORE_DAO.get_config_value('test_a'), type(v))
    PERSISTENT_STORE_DAO.delele_config('test_a')
    PERSISTENT_STORE_DAO.delele_config('test_b')
    PERSISTENT_STORE_DAO.delele_config('test_c')
    results = PERSISTENT_STORE_DAO.list_config_all()
    print(results)
    print(v:=PERSISTENT_STORE_DAO.get_config_value('test_a'), type(v))
    print(v:=PERSISTENT_STORE_DAO.get_config_value('test_b'), type(v))
    print(v:=PERSISTENT_STORE_DAO.get_config_value('test_c'), type(v))   
    PERSISTENT_STORE_DAO.delele_config('test_d')
    PERSISTENT_STORE_DAO.delele_config('test_e')
    PERSISTENT_STORE_DAO.delele_config('test_f')        

# The main program for testing the clearing
# of database tables and creating them
if __name__ == '__main__':
    # manage_tables()
    test_persistent_store()