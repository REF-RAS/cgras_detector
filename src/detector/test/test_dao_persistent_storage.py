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

import os
from json import dumps

from detector.database_file import DBFile
from detector.dao_persistent_storage import PERSISTENT_STORE_DDL, PersistentStoreDAO

def sample_db_file():
    CURRENT_FOLDER = os.path.dirname(__file__)
    DB_FILE = os.path.join(CURRENT_FOLDER, 'test.db')
    return CURRENT_FOLDER, DB_FILE

def test_create_db():
    CURRENT_FOLDER, DB_FILE = sample_db_file()
    PS_DBFM = DBFile(CURRENT_FOLDER, 'test.db', PERSISTENT_STORE_DDL)
    # delete the db file if exists
    try:
        os.remove(PS_DBFM.db_file)
    except:
        ...
    # create tables
    PS_DBFM.create_tables()
    table_name_list = PS_DBFM.list_tables_name()
    assert len(table_name_list) == 1
    assert 'persistent_store' in table_name_list
    # drop tables
    PS_DBFM.drop_tables()
    table_name_list = PS_DBFM.list_tables_name()
    assert len(table_name_list) == 0
    assert 'persistent_store' not in table_name_list
    
def test_persistent_storage():
    CURRENT_FOLDER, DB_FILE = sample_db_file()
    PS_DBFM = DBFile(CURRENT_FOLDER, 'test.db', PERSISTENT_STORE_DDL)
    PERSISTENT_DAO = PersistentStoreDAO(PS_DBFM.db_file)
    # reset the tables
    PS_DBFM.drop_tables()
    PS_DBFM.create_tables()   
    # test list config
    config_df = PERSISTENT_DAO.list_config_all()
    assert config_df == []
    # test set config
    PERSISTENT_DAO.set_config_value('APPLE', 0.01)
    PERSISTENT_DAO.set_config_value('BANANA', 200)
    PERSISTENT_DAO.set_config_value('CITRUS', 'ABC')
    config_df = PERSISTENT_DAO.list_config_all()
    assert len(config_df) == 3
    assert PERSISTENT_DAO.get_config_value('APPLE') == 0.01
    assert PERSISTENT_DAO.get_config_value('BANANA') == 200
    assert PERSISTENT_DAO.get_config_value('CITRUS') == 'ABC' 
    # test data structure
    PERSISTENT_DAO.set_config_value('PEAR', [0, 1, 2, 3, 4])
    assert str(PERSISTENT_DAO.get_config_value('PEAR')) == str([0, 1, 2, 3, 4])
    PERSISTENT_DAO.set_config_value('TEA', [0, 1.2, 'ABC', True, False])
    assert str(PERSISTENT_DAO.get_config_value('TEA')) == str([0, 1.2, 'ABC', True, False])    
    # test non-existent
    assert PERSISTENT_DAO.get_config_value('VEGE') == None
    # test delete config
    PERSISTENT_DAO.delele_config('VEGE')
    PERSISTENT_DAO.delele_config('CITRUS')
    PERSISTENT_DAO.delele_config('PEAR')
    config_df = PERSISTENT_DAO.list_config_all()
    assert len(config_df) == 3
    
if __name__ == '__main__':
    test_create_db()
    test_persistent_storage()