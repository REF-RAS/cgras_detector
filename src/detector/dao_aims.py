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
import pandas as pd
from datetime import datetime as dt
# project modules
import tools.db_tools as db_tools
from tools.lock_tools import synchronized
from tools.logging_tools import global_logger
from detector.database_manager import DBFileManager
 
# the DDL for creating tables in the tile.db
AIMSTILE_DDL = {
    'tile':
    """
    CREATE TABLE IF NOT EXISTS tile (
        tile_id text PRIMARY KEY,
        pit_id text,
        species text,
        spawn_time text,
        settle_time text,
        season text,
        metadata text DEFAULT NULL,
        FOREIGN KEY (season) REFERENCES season (title)
    );
    """,

    'season':
    """
    CREATE TABLE IF NOT EXISTS season (
        title text PRIMARY KEY,
        is_active integer,
        create_date text,
        start_date text,
        end_date text,
        tab_ncols integer DEFAULT -1,
        tab_nrows integer DEFAULT -1
    );
    INSERT INTO season (title, is_active, start_date, end_date, create_date, tab_ncols, tab_nrows) VALUES ("2023Dec", 1, "2023-11-1", "2023-12-31", DATE("now"), 20, 8);
    """
}
 
# This class is the data access object for the bagfile capturer
# The tile id is auto-generated from the pit_id and season
class AIMSTileDAO():
    def __init__(self, db_file):
        self.db_file = db_file

    @staticmethod
    def pit_id_to_tile_id(pit_id:str, season_title:str) -> str:
        """ return the tile_id based on the PIT id and the associated season

        :param pit_id: _description_
        :param season: _description_
        :return: _description_
        """
        return f'{season_title}-{pit_id}'
    
    # validation of the database
    @synchronized
    def validate_db(self):
        """ return True if there is at least one current season and one tile for the operation

        :return: True if the tile.db can support the operation of the system
        """
        with db_tools.create_connection(self.db_file) as conn:       
            c = conn.cursor() 
            result = c.execute('SELECT COUNT(*) FROM tile').fetchone()
            if not result or result[0] == 0:
                return False
            result = c.execute('SELECT COUNT(*) FROM season WHERE is_active = 1').fetchone()
            if not result or result[0] == 0:
                return False            
        return True
    
    # --- table: tile

    # add a record to the tile table, with the parameter species is normallized to lower case
    @synchronized
    def add_tile(self, pit_id:str, species:str, spawn_time:str, settle_time:str, season:str, metadata=None):
        tile_id = self.pit_id_to_tile_id(pit_id, season)
        sql = 'INSERT INTO tile (tile_id, pit_id, species, spawn_time, settle_time, season, metadata) VALUES (?, ?, ?, ?, ?, ?, ?)'
        return db_tools.update(self.db_file, sql, (tile_id, pit_id, species.lower(), spawn_time, settle_time, season, metadata,))
    
    # return the number of records in the tile table
    @synchronized
    def count_tiles(self):
        return db_tools.count_rows(self.db_file, 'tile')
    
    # return the record of the given tile id as a dict or a dataframe
    @synchronized
    def get_tile(self, tile_id:str, to_dataframe:bool=False) -> dict:
        sql = 'SELECT * FROM tile WHERE tile_id = ?'
        if to_dataframe:
            return db_tools.query(self.db_file, sql, (tile_id,))
        return db_tools.query_for_dict(self.db_file, sql, (tile_id,))
    
    # return a dataframe structured as a info table of the given tile id
    @synchronized
    def get_tile_info_as_df(self, tile_id:str) -> pd.DataFrame:
        tile_info = self.get_tile(tile_id)
        model = pd.DataFrame(columns=('Tile ID', tile_id))
        if tile_info is not None:
            model.loc[1] = ['PIT Tag ID', tile_info['pit_id']]
            model.loc[2] = ['Species', tile_info['species']]
            model.loc[3] = ['Season', tile_info['season']]                
            model.loc[4] = ['Settled On', tile_info['settle_time']]
            model.loc[5] = ['Spawned On', tile_info['spawn_time']]
        return model
    
    # return a dict object containing a record of a tile given the PIT id
    @synchronized    
    def query_tile_by_pit_of_this_season(self, pit_id:str) -> dict:
        sql = 'SELECT * FROM tile WHERE pit_id = ? and season = (SELECT DISTINCT(title) FROM season WHERE is_active = 1)'
        return db_tools.query_for_dict(self.db_file, sql, (pit_id,))   
    
    # return the minimum and the maximum settle_time of a season or all seasons
    @synchronized    
    def query_tile_settle_time_range(self, season_title:str=None) -> dict:
        if season_title is None:        
            sql = 'SELECT MIN(settle_time), MAX(settle_time) FROM tile'
            result = db_tools.query_for_dict(self.db_file, sql,)
        else:
            sql = 'SELECT MIN(settle_time), MAX(settle_time) FROM tile WHERE season = ?'
            result = db_tools.query_for_dict(self.db_file, sql, (season_title,))            
        return result
    
    # return a list of all tiles or tiles of a season
    @synchronized
    def list_all_tiles(self, season_title:str=None) -> list:
        if season_title is None:
            sql = 'SELECT * FROM tile'
            return db_tools.query(self.db_file, sql,) 
        else:
            sql = 'SELECT * FROM tile WHERE season = ?'
            return db_tools.query(self.db_file, sql, (season_title,))      
    
    # return a list of all tiles of the active season
    @synchronized
    def list_all_tiles_of_active_season(self) -> list:   
        active_season = self.get_active_season()
        if active_season is not None:        
            return self.list_all_tiles(active_season['title'])
        return None
    
    # remove all records of the tile table
    @synchronized
    def clear_tile_table(self):
        return db_tools.clear_table(self.db_file, 'tile')    

    # return a dataframe structured as a info table of all the tiles in the table
    @synchronized
    def query_tile_stat(self):
        model = pd.DataFrame(columns=('Parameters', 'Values'))
        model.loc[1] = ['Num Species', self.count_species()]
        model.loc[2] = ['Num Tiles', self.count_tiles()]
        active_season = self.get_active_season()
        result = self.query_tile_settle_time_range(active_season['title'])
        model.loc[3] = ['Oldest Tile', result['MIN(settle_time)']]
        model.loc[4] = ['Latest Tile', result['MAX(settle_time)']]
        species_list = self.list_species()
        model.loc[5] = ['Species', ', '.join(species_list)]
        return model

    # return the number of unique species found in the table 
    @synchronized
    def count_species(self) -> list:
        return len(self.list_species()) 
    
    # return a list of all unique species found in the table 
    @synchronized
    def list_species(self):
        sql = 'SELECT DISTINCT(species) FROM tile'
        result = db_tools.query_for_list(self.db_file, sql,)
        return result 
    
    # return True if the given species is found in the table
    @synchronized
    def exist_species(self, species) -> bool:
        sql = 'SELECT COUNT(*) FROM tile WHERE species = ?'
        result = db_tools.query_for_object(self.db_file, sql, (species,))
        return result >= 1   
    
    # --- high level processing
    
    # add tile records from a dataframe to the tile table, and the dataframe contains columns 'pit_id', 'species', 'season', 'settle_time', 'spawn_time'
    @synchronized
    def import_from_dataframes(self, tile_df:pd.DataFrame, replace_all:bool=True):
        error_list = []
        if replace_all:
            self.clear_tile_table()
        # ignore the other columns except these five keys
        tile_df = tile_df[['pit_id', 'species', 'season', 'settle_time', 'spawn_time']]
        # normalize the data
        tile_df['species_name'] = tile_df['species_name'].str.lower()
        tile_df['spawn_time'] = tile_df['spawn_time'].astype('string')
        tile_df['settle_time'] = tile_df['settle_time'].astype('string')
        # iterate through each row of the dataframe, this is inefficient but necessary for gracefully ignore duplicate rows
        for index, row in tile_df.iterrows():
            try:                
                # set None if the value is not of the required type
                row['spawn_time'] = None if type(row['spawn_time']) != str else row['spawn_time']
                row['settle_time'] = None if type(row['settle_time']) != str else row['settle_time']               
                self.add_tile(row['pit_id'], row['species'], row['spawn_time'], row['settle_time'], row['season'])
            except (Exception, Warning) as e:
                global_logger.warning(e)
                error_list.append(f'{e.__class__.__name__} at row {index}: {e} ')
        return error_list if len(error_list) > 0 else None
    
    # --- table: season

    # add a record to the season table
    @synchronized
    def add_season(self, title:str, is_active:bool, start_date:str, end_date:str, tab_ncols:int, tab_nrows:int):
        if '-' in title:
            raise AssertionError(f'{type(self).__name__}.add_season: season title cannot contain the dash "-" character')
        sql = 'INSERT INTO season (title, is_active, start_date, end_date, tab_ncols, tab_nrows, create_date) VALUES (?, ?, ?, ?, ?, ?, DATE("now"))'
        is_active = 1 if is_active else 0
        return db_tools.update(self.db_file, sql, (title, is_active, start_date, end_date, tab_ncols, tab_nrows,))

    # return the number of season defined in the season table
    @synchronized
    def count_season(self) -> int:
        return db_tools.count_rows(self.db_file, 'season')    
    
    # return a list of titles of the seasons in the table
    @synchronized
    def list_seasons(self) -> list:
        sql = 'SELECT title FROM season ORDER BY title DESC'
        result = db_tools.query_for_list(self.db_file, sql,)
        return result 
    
    # return the record of the season given the title
    @synchronized
    def get_season(self, season_title:str) -> dict:
        sql = 'SELECT * FROM season WHERE title = ?'
        result = db_tools.query_for_dict(self.db_file, sql, (season_title,))
        return result 

    # delete all records in the season table
    @synchronized
    def clear_season_table(self):
        return db_tools.clear_table(self.db_file, 'season')
    
    # reset the active flag of all seasons in the table to False
    @synchronized
    def set_no_active_season(self):
        sql = 'UPDATE SEASON SET is_active = 0'
        return db_tools.update(self.db_file, sql) 
    
    # return the record of the active season if there is one
    @synchronized
    def get_active_season(self):
        sql = 'SELECT * FROM season WHERE is_active = 1'
        result = db_tools.query_for_dict(self.db_file, sql,)
        return result 

    # return the title of the active season if there is one
    @synchronized
    def get_active_season_title(self):
        sql = 'SELECT title FROM season WHERE is_active = 1'
        result = db_tools.query_for_object(self.db_file, sql,)
        return result 

    # set a season given its title to active
    @synchronized
    def set_active_season(self, season_title:str):
        with db_tools.create_connection(self.db_file) as conn: 
            conn.isolation_level = None  # to turn off auto-commit (may be unnecessary, minor issue, to check)
            self.set_no_active_season()
            sql = 'UPDATE SEASON SET is_active = 1 WHERE title = ?'
            return db_tools.update(self.db_file, sql, (season_title,)) 
    
    # return a dataframe structured as a info table of all the active season in the table
    @synchronized
    def get_active_season_info_as_df(self) -> pd.DataFrame:
        season_info = self.get_active_season()
        model = pd.DataFrame(columns=('Active Season', season_info['title']))
        if season_info is not None:
            model.loc[1] = ['Period', f'{season_info["start_date"]} to {season_info["end_date"]}']
            model.loc[2] = ['Tab Grid Dim', f'{season_info["tab_ncols"]} cols x {season_info["tab_nrows"]} rows']           
            model.loc[3] = ['Created On', season_info['create_date']]
        return model

# ------------------------------------------------
# The test functions

# test the import of an excel file that contains tiles in the required format
def test_excel_import():
    CGRAS_HOME = '/home/qcr/cgras_data'
    DATABASE_FOLDER = os.path.join(CGRAS_HOME, 'database')
    AIMSTILE_DBFM = DBFileManager(DATABASE_FOLDER, 'tile.db', AIMSTILE_DDL)
    AIMSTile_DAO = AIMSTileDAO(AIMSTILE_DBFM.db_file)
    IMPORT_FILE = os.path.join(os.path.dirname(__file__), '../../../docs/AIMS_Tiles.xlsx')
    AIMSTILE_DBFM.dump_all_tables()
    
    # species_df = pd.read_excel(IMPORT_FILE, sheet_name='Species', index_col=None)
    # species_df = species_df.reset_index()
    tile_df = pd.read_excel(IMPORT_FILE, sheet_name='Tile', index_col=None)   
    error_list = AIMSTile_DAO.import_from_dataframes(tile_df)
    if error_list is not None:
        print(error_list)

    sql = 'SELECT * FROM tile WHERE settle_date > "2024-11-13"'
    results = db_tools.query_for_list_of_dicts(AIMSTILE_DBFM.db_file, sql,)  
    print(results) 

# test the reset of all the tables in this database
def test_reset_tables():
    CGRAS_HOME = '/home/qcr/cgras_data'
    DATABASE_FOLDER = os.path.join(CGRAS_HOME, 'database')
    AIMSTILE_DBFM = DBFileManager(DATABASE_FOLDER, 'tile.db', AIMSTILE_DDL)
    AIMSTILE_DBFM.drop_tables()
    AIMSTILE_DBFM.dump_all_tables()
    AIMSTILE_DBFM.create_tables()    
    AIMSTILE_DBFM.dump_all_tables()
    
# test the drop and re-create table(s) given their names
def test_recreate_table():
    CGRAS_HOME = '/home/qcr/cgras_data'
    DATABASE_FOLDER = os.path.join(CGRAS_HOME, 'database')
    AIMSTILE_DBFM = DBFileManager(DATABASE_FOLDER, 'tile.db', AIMSTILE_DDL)
    AIMSTILE_DBFM.drop_tables(['season'])
    # AIMSTILE_DBFM.dump_all_tables()
    AIMSTILE_DBFM.create_tables(['season'])    
    AIMSTILE_DBFM.dump_all_tables()    
    
if __name__ == '__main__':
    # test_excel_import()
    # test_reset_tables()
    test_recreate_table()