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
import tools.file_tools as file_tools
from tools.lock_tools import synchronized
from tools.logging_tools import logger
from detector.database_manager import DBFileManager

# NOTE: The batch_time is an ISO 8601 date time string format '2025-05-29 14:16:00' and the batch_id is derived from the time and cgras_station_id or the importer_id

# the DDL for creating tables in the detect.db
DETECT_DDL = {
    'tile_sample':
    """
    CREATE TABLE IF NOT EXISTS tile_sample (
        id text PRIMARY KEY,
        tile_id text,
        batch_id text,         
        batch_time text,
        age integer DEFAULT -1,
        species text,
        season text,   
        settle_time text,   
        importer_id text,
        operator text,
        create_time text,
        status integer DEFAULT -1,
        priority text,
        remarks text DEFAULT '',
        UNIQUE (tile_id, batch_id)
    );
    """,
    
    'source_image':
    """
    CREATE TABLE IF NOT EXISTS source_image (
        id integer PRIMARY KEY AUTOINCREMENT,
        capture_id text,
        tile_sample_id text, 
        capture_x integer,
        capture_y integer,
        file_path text,       
        UNIQUE (capture_id),
        CONSTRAINT fk_tile_sample_id
            FOREIGN KEY (tile_sample_id) REFERENCES tile_sample (id) ON DELETE CASCADE
    );
    """,
    
    'task_record':
    """
    CREATE TABLE IF NOT EXISTS task_record (
        id integer PRIMARY KEY AUTOINCREMENT,
        task_type int,
        task_object text, 
        start_time text,
        used_time real,
        status int,
        remarks text,
        metadata text
    );
    """, 
    
    'yolo_model':
    """
    CREATE TABLE IF NOT EXISTS yolo_model (
        id integer PRIMARY KEY AUTOINCREMENT,
        name text,
        model_file_path text, 
        input_image_width integer,
        input_image_height interger,
        species text,
        start_day integer DEFAULT 0,
        end_day integer DEFAULT -1,
        coral_classes text,
        dead_coral_classes text,
        remarks text,
        UNIQUE (name)
    );
    """,

    'tile_sample_detect_stat':
    """
    CREATE TABLE IF NOT EXISTS tile_sample_detect_stat (
        tile_sample_id text PRIMARY KEY,
        tile_pixel_x integer,
        tile_pixel_y integer,
        coral_object_count integer DEFAULT 0,
        dead_coral_object_count integer DEFAULT 0,
        other_object_count integer DEFAULT 0,
        duplicates_removed integer DEFAULT 0,
        yaml_data text DEFAULT NULL,
        CONSTRAINT fk_tile_sample_id
            FOREIGN KEY (tile_sample_id) REFERENCES tile_sample (id) ON DELETE CASCADE
    );
    """,

    'health_model':
    """
    CREATE TABLE IF NOT EXISTS health_model (
        species text PRIMARY KEY,
        func_name text,
        func_def text DEFAULT NULL,
        UNIQUE(func_name)
    );
    """,

    'cache_tile_health_stat':
    """
    CREATE TABLE IF NOT EXISTS cache_tile_health_stat (
        tile_id text PRIMARY KEY,
        season text,
        species text,
        settle_time text,
        coral_count_start integer,
        age_start integer,
        coral_count_latest integer,
        dead_coral_count_latest integer,
        other_object_count_latest integer,
        age_latest integer,
        batch_time_latest text,
        loss_rate_whole real,
        loss_rate_recent real,
        num_samples integer DEFAULT 0,
        health_index real DEFAULT NULL,
        count_yaml_data text DEFAULT NULL
    );
    """,

    'detected_object':
    """
    CREATE TABLE IF NOT EXISTS detected_object (
        id integer PRIMARY KEY AUTOINCREMENT,
        tile_sample_id text,
        class_name text,
        class_category integer,
        centre_x real,
        centre_y real,
        corner_x1 real,
        corner_y1 real,
        size_x real,
        size_y real,
        CONSTRAINT fk_tile_sample_id
            FOREIGN KEY (tile_sample_id) REFERENCES tile_sample (id) ON DELETE CASCADE
    );
    """, 
    
    'error_flag':
    """
    CREATE TABLE IF NOT EXISTS error_flag (
        id integer PRIMARY KEY,
        level integer DEFAULT 0,
        update_time text,
        remarks text
    );
    """,    
}

# the constants defined for storing task types in the task_record table
class TaskTypes(Enum):
    DETECT_CORALS = 0 
    IMPORT_TILES = 1
    ASSESS_HEALTH = 2

# the constants defined for storing coral class_category in the detected_object table
class ObjectClassCategories(Enum):
    NOT_CORAL = 0
    CORAL = 1
    DEAD_CORAL = 2

# the constants defined for storing status in different tables
class StatusNames(Enum):
    UNKNOWN = -1
    PENDING = 0
    SUCCESS = 1
    FAILED = 2
    ABORTED = 3
    INVALID = 4  # Delete a tile sample puts it into INVALID

class CoralObject():
    """ CoralObject models an object in the tile images detected by an object detection model. It comprises locational information including the index in the image grid, the index of the blob in each image,
        the bounding box in the blob. It also contains locational information in the tile frame of reference includig bounding box and centre. It contains the class id and the class name string of the object.
    """
    def __init__(self, preserve_fraction=False, **kwargs):
        """ the constructor

        :param preserve_fraction: determine if fractions in the parameters are truncated to integers, defaults to False
        :type preserve_fraction: bool, optional
        """
        # populates the model parameters from keyword input parameters
        self.blob_row_index = kwargs.get('blob_row_index', None)    # the row and column index of the blob where this coral object was detected
        self.blob_col_index = kwargs.get('blob_col_index', None)    
        self.image_row_index = kwargs.get('image_row_index', None)  # the row and column index of the image where this coral object was detected
        self.image_col_index = kwargs.get('image_col_index', None)
        self.cls_id =  kwargs.get('cls_id', None)                   # the class id of the coral object as specified in the detection model
        self.cls_name = kwargs.get('cls_name', None)                # the class name of the coral object
        self.class_category = kwargs.get('class_category', 0)                   # the object is considered a coral 
        self.bbox_in_blob = kwargs.get('bbox_in_blob', None)        # the bounding box of the coral object in the image blob space (x1, y1, x2, y2)
        self.bbox = kwargs.get('bbox', None)                        # the bounding box of the coral object in the tile space
        self.centre = kwargs.get('centre', None)                    # the centre of the coral object in the file space
        self.size = kwargs.get('size', None)                        # the size of the coral object (xdim, ydim)
        self.bbox_normalized = kwargs.get('bbox_normalized', None)  # the normalized bounding box of the coral object in the tile space
        self.centre_normalized = kwargs.get('centre_normalized', None) # the normalized centre of the coral object in the tile space    
        self.size_normalized = kwargs.get('size_normalized', None) # the normalized size of the coral object in the tile space              
        self.invalidated = False
        if not preserve_fraction:
            self._convert_to_int()
        
    def _convert_to_int(self):
        """ internal function for converting some parameters to int type using truncation
        """
        self.bbox_in_blob = self._convert_list_to_int(self.bbox_in_blob) if self.bbox_in_blob is not None else self.bbox_in_blob
        self.bbox = self._convert_list_to_int(self.bbox) if self.bbox is not None else self.bbox
        self.size = self._convert_list_to_int(self.size) if self.size is not None else self.size
        self.centre = self._convert_list_to_int(self.centre) if self.centre is not None else self.centre
        
    @staticmethod
    def _convert_list_to_int(value_list:list) -> list:
        """ internal function for converting the numbers in a list to integers

        :param value_list: the list of numbers
        :type value_list: list
        :return: a new list containing the same numbers truncated to integers
        :rtype: list
        """
        return [int(x) for x in value_list]
    
    def __repr__(self):
        """ Print the content of this coral object

        """
        inv_str = '[INV]' if self.invalidated else '[VAD]' 
        bbox_int = [int(x) for x in self.bbox]
        centre_int = [int(x) for x in self.centre]
        centre_in_blob = (self.bbox_in_blob[0] + self.size[0] // 2, self.bbox_in_blob[1] + self.size[1] // 2)
        area = int(self.size[0] * self.size[1])
        result = f'{inv_str} {self.image_col_index, self.image_row_index, self.blob_col_index, self.blob_row_index} ({self.cls_name}) bbox ({bbox_int}) centre ({centre_int})'
        if self.centre_normalized is not None:
            result += f'({self.centre_normalized[0]:.5f}, {self.centre_normalized[0]:.5f}) blob ({centre_in_blob}) area ({area})'
        else:
            result += f' blob ({centre_in_blob}) area ({area})'
        return result
    

# Model the data access object for the tables in this database 
class DetectorDAO():
    def __init__(self, db_file:str, **kwargs):
        self.db_file = db_file

    # functions for validate the database
    # return True if there is at least one tile, one tank, one station, and one pattern for the operation
    @synchronized
    def validate_db(self):
        with db_tools.create_connection(self.db_file) as conn:       
            c = conn.cursor() 
            result = c.execute('SELECT COUNT(*) FROM general_config').fetchone()
            if not result or result[0] == 0:
                return False         
        return True

    # - table: tile_sample

    # a function to compute the id of a tile_sample given its tile_id and the batch_id
    @staticmethod
    def compute_tile_sample_id(tile_id:str, batch_id:str) -> str:
        tile_sample_id = f'{tile_id}-{batch_id}'
        return tile_sample_id
    
    # add a record to the tile_sample table, with species normalized to lower case
    @synchronized
    def add_tile_sample(self, tile_id:str, batch_id:str, batch_time:str, age:int, species:str, season:str, settle_time:str, importer_id:str='', operator:str='', status:int=StatusNames.PENDING.value):
        sql = 'INSERT INTO tile_sample (id, tile_id, batch_id, batch_time, age, species, season, settle_time, importer_id, operator, status, create_time, priority) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, DATETIME("now"), DATETIME("now"))'
        tile_sample_id = self.compute_tile_sample_id(tile_id, batch_id)
        return db_tools.update(self.db_file, sql, (tile_sample_id, tile_id, batch_id, batch_time, age, species.lower(), season, settle_time, importer_id, operator, status))
    
    # return True if a record of tile_sample exists given the tile_id and the batch_id
    @synchronized
    def exist_tile_sample(self, tile_id:str, batch_id:str) -> dict:
        sql = 'SELECT * FROM tile_sample WHERE id = ?'
        tile_sample_id = self.compute_tile_sample_id(tile_id, batch_id)
        result = db_tools.query_for_object(self.db_file, sql, (tile_sample_id,))
        return True if result is not None else False
    
    # return the number of records of tile sample given a particular status
    @synchronized
    def count_tile_samples(self, status:int=StatusNames.PENDING.value) -> int:
        if isinstance(status, StatusNames):
            status = status.value
        sql = 'SELECT COUNT(*) FROM tile_sample WHERE status = ?'
        result = db_tools.query_for_object(self.db_file, sql, (status,))
        return result if result is not None else 0
    
    # return a record of tile sample given the id of the tile_sample as a dixt
    @synchronized
    def get_tile_sample(self, tile_sample_id:str) -> dict:
        sql = 'SELECT * FROM tile_sample WHERE id = ?'
        return db_tools.query_for_dict(self.db_file, sql, (tile_sample_id,))
    
    # return the list of unique season found in the table
    @synchronized
    def list_seasons_in_tile_sample(self) -> list:
        sql = 'SELECT DISTINCT(season) FROM tile_sample ORDER BY batch_time DESC'
        return db_tools.query_for_list(self.db_file, sql)              

    # return a list of records of tile sample of which the tile id is as given, and the number of records is bounded by the limit parameter
    @synchronized
    def get_tile_sample_of_tile_id(self, tile_id:str, limit:int=1) -> dict:
        return db_tools.query_for_list_of_dicts(self.db_file, 'SELECT * FROM tile_sample WHERE tile_id = ? LIMIT ?', (tile_id, limit))
    
    # return a list of unique tile_id found in the tile_sample table
    @synchronized
    def get_distinct_tile_id_as_list(self, season) -> list:    
        tile_id_list = db_tools.query_for_list(self.db_file, 'SELECT DISTINCT(tile_id) FROM tile_sample WHERE season = ?', (season,))
        return tile_id_list

    # return a dataframe of records given the season title, the status, and maximum records to return
    @synchronized
    def list_tile_samples(self, season_title:str=None, status:int=StatusNames.PENDING.value, limit=None) -> pd.DataFrame:
        if status is not None:
            sql = 'SELECT * FROM tile_sample WHERE status = ?'
            param_list = [status] 
        else:
            sql = 'SELECT * FROM tile_sample'
            param_list = []                
        
        if season_title:
            if param_list:
                sql += ' AND season = ?'
            else:
                sql += ' WHERE season = ?'
            param_list.append(season_title)
        if limit is None or not isinstance(limit, numbers.Number):
            sql += ' ORDER BY priority ASC'
        else:
            sql = ' ORDER BY priority ASC LIMIT ?'
            param_list.append(limit)
        return db_tools.query(self.db_file, sql, tuple(param_list)) 
        
    # returns the record of the next pending tile sample, if exists, as a dict
    @synchronized
    def query_next_pending_tile_sample(self) -> dict:
        sql = 'SELECT * FROM tile_sample WHERE status = ? ORDER BY priority ASC LIMIT 1'
        return db_tools.query_for_dict(self.db_file, sql, (StatusNames.PENDING.value,))                        
    
    # delete all records int he tile_sample table
    @synchronized
    def clear_tile_sample_table(self):
        return db_tools.clear_table(self.db_file, 'tile_sample')    
    
    # update the importer and the oeprator of a tile_sample record given its id
    @synchronized
    def update_importer(self, tile_sample_id:str, importer_id:str, operator:str=None):
        sql = 'UPDATE tile_sample SET importer_id = ?, operator = ? WHERE id = ?'
        return db_tools.update(self.db_file, sql, (importer_id, operator, tile_sample_id))   
    
    # update the status of the tile_sample given its tile_sample_id 
    @synchronized
    def update_tile_sample_status(self, tile_sample_id:str, status:int, remarks:str=None):
        with db_tools.create_connection(self.db_file) as conn:
            c = conn.cursor()
            if remarks is None:
                c.execute('UPDATE tile_sample SET status = ? WHERE id = ?', (status, tile_sample_id,))
            else:
                c.execute('UPDATE tile_sample SET status = ?, remarks = ? WHERE id = ?', (status, remarks, tile_sample_id,))
            return True  
        
    @synchronized
    def clear_tile_sample_data(self, tile_sample_id:str):
        with db_tools.create_connection(self.db_file) as conn:
            c = conn.cursor()
            c.execute('DELETE FROM tile_sample_detect_stat WHERE tile_sample_id = ?', (tile_sample_id,))
            c.execute('DELETE FROM detected_object WHERE tile_sample_id = ?', (tile_sample_id,))
            return True
    
    # delete the record of tile_sample given the id
    @synchronized
    def delete_tile_sample(self, tile_sample_id:str):
        ######
        sql = 'DELETE FROM tile_sample WHERE id = ?'
        return db_tools.update(self.db_file, sql, (tile_sample_id,))   
    
    # update the priority field of a tile_sample record given its id
    @synchronized
    def set_top_priority(self, tile_sample_id:str):
        sql = 'UPDATE tile_sample SET priority = (SELECT DATETIME(MIN(priority), "-1 minute") FROM tile_sample WHERE status = ?) WHERE id = ?'
        status = StatusNames.PENDING
        return db_tools.update(self.db_file, sql, (status.value, tile_sample_id,))   
    
    # return the records from a query based on search keys including season, status, tile_Id, batch_id, and the period
    
    @synchronized
    def query_processed_tile_samples(self, season_title:str=None, status:int=None, tile_id:str=None, batch_id:str=None, the_period:int=None, limit:int=None) -> pd.DataFrame:
        # go through each input parameters and, if defined, included in the query
        param_list = []
        if status is not None:
            if type(status) in [list, tuple]:
                status_list = ','.join('?' * len(status))
                sql = f'SELECT * FROM tile_sample WHERE status IN ({status_list})'
                param_list.extend(status)            
            else:
                sql = 'SELECT * FROM tile_sample WHERE status = ?'
                param_list.append(status)
        else:
            sql = 'SELECT * FROM tile_sample WHERE status NOT IN (?, ?)'
            param_list.append(StatusNames.PENDING.value)
            param_list.append(StatusNames.INVALID.value)
        if season_title:
            sql += ' AND season = ?'
            param_list.append(season_title)            
        if tile_id:
            sql += ' AND tile_id LIKE ?'
            param_list.append(f'%{tile_id}%')
        if batch_id:
            sql += ' AND batch_id LIKE ?'
            param_list.append(f'%{batch_id}%')
        if the_period != 0:
            sql += ' AND create_time >= DATE("now", ?)'
            param_list.append(f'{the_period} days')
        sql += ' ORDER BY priority DESC'
        if type(limit) == int:
            sql += ' LIMIT ?'
            param_list.append(limit)
        return db_tools.query(self.db_file, sql, tuple(param_list))      
    
    # - table: source_image
    @synchronized
    def add_source_image(self, capture_id:str, tile_sample_id:str, capture_x:int, capture_y:int, file_path:str) -> int:
        with db_tools.create_connection(self.db_file) as conn:
            c = conn.cursor()
            c.execute('INSERT INTO source_image (capture_id, tile_sample_id, capture_x, capture_y, file_path) '
                      'VALUES (?, ?, ?, ?, ?)', 
                      (capture_id, tile_sample_id, capture_x, capture_y, file_path,))
            conn.commit()
            id = c.lastrowid
        return id
    
    @synchronized
    def query_source_images_of_tile_sample(self, tile_sample_id:str) -> dict:
        sql = 'SELECT * FROM source_image WHERE tile_sample_id = ?'
        return db_tools.query_for_list_of_dicts(self.db_file, sql, (tile_sample_id,))
    
    @synchronized
    def delete_source_images_of_tile_sample(self, tile_sample_id:str) -> int:
        sql = 'DELETE FROM source_image WHERE tile_sample_id = ?'
        return db_tools.update(self.db_file, sql, (tile_sample_id,))  
    
    # composite operation: validate yaml file for a new tile sample
    @synchronized
    def validate_tile_sample_import(self, yaml_data:dict):
        error_list = []
        # load and validate the data in the yaml config file which has been converted to a YamlConfig object
        tile_id = yaml_data.get('tile_id', None)
        batch_id = yaml_data.get('batch_id', None)
        batch_time = yaml_data.get('batch_time', None)
        age = yaml_data.get('age', -1)
        species = yaml_data.get('species', None)
        season = yaml_data.get('season', None)
        importer_id = yaml_data.get('importer_id', 'Unknown')
        operator = yaml_data.get('operator', 'Unknown') 
        images_dict = dict()
        image_files_parent_folder = yaml_data.get('image_files_parent_folder', None)
        yaml_images_list = yaml_data.get('images', None)
        # validate the first tier data
        if tile_id is None or batch_id is None or yaml_images_list is None:
            error_list.append(f'One of the mandatory fields (tile_id, batch_id, and images) is missing in the yaml file')
            return error_list
        # iterate through the images list in the yaml file
        max_x, max_y = -1, -1
        for index, yaml_images in enumerate(yaml_images_list):
            x, y = yaml_images.get('x', None), yaml_images.get('y', None)
            max_x, max_y = max(max_x, x), max(max_y, y)
            filepath = yaml_images.get('file', None)
            if image_files_parent_folder:
                filepath = os.path.join(image_files_parent_folder, filepath)
            if x is None or y is None or filepath is None:
                error_list.append(f'An image entry must include these fields (x, y, file) and one of them is missing at entry {index}') 
            else:
                if not os.path.isfile(filepath):
                    error_list.append(f'The file path given for image at ({x},{y}) does not exist: {filepath}')
                else: 
                    images_dict[(x, y)] = filepath
        # adding the images_dict to the yaml data
        # yaml_data['images_dict'] = images_dict
        # validate the images list
        if max_x == -1 or max_y == -1:
            error_list.append(f'An image entry must include these fields (x, y, file) and one of them is missing at entry {index}') 
        if (max_x + 1) * (max_y + 1) != len(images_dict):
            error_list.append(f'Some image index (x, y) is missing: the indices are expected to span from (0, 0) to ({max_x, max_y})')
        # start adding image data to list of lists
        if self.exist_tile_sample(tile_id, batch_id):
            error_list.append(f'The (tile_id={tile_id}, batch_id={batch_id}) pair already exists)')
        for index_y in range(max_y + 1):    
            for index_x in range(max_x + 1): 
                if (index_x, index_y) not in images_dict:
                    error_list.append(f'The image index ({index_x, index_y}) is missing from the images list') 
        if error_list:
            model = pd.DataFrame(columns=('#', 'Errors'))
            for index, error in enumerate(error_list):
                model.loc[index + 1] = [index, error]
            return False, model
        else:
            model = pd.DataFrame(columns=('Parameters', 'Values'))
            model.loc[1] = ['tile_id', tile_id]
            model.loc[2] = ['batch_id', batch_id]
            model.loc[3] = ['batch_time', batch_time]
            model.loc[4] = ['species', species]
            model.loc[5] = ['season', season]            
            model.loc[6] = ['capture grid dim', f'{max_x + 1} x {max_y + 1}']
            model.loc[7] = ['num images', len(images_dict)]
            return True, model
                
    # composite operation: import yaml file for a new tile sample
    @synchronized
    def import_tile_sample_yaml(self, yaml_data:dict) -> bool:
        error_list = []
        # load and validate the data in the yaml config file which has been converted to a YamlConfig object
        tile_id = yaml_data.get('tile_id', None)
        batch_id = yaml_data.get('batch_id', None)
        batch_time = yaml_data.get('batch_time', None)
        age = yaml_data.get('age', -1)
        species = yaml_data.get('species', None)
        season = yaml_data.get('season', None)
        settle_time = yaml_data.get('settle_time', None)
        importer_id = yaml_data.get('importer_id', 'Unknown')
        operator = yaml_data.get('operator', 'Unknown') 
        image_files_parent_folder = yaml_data.get('image_files_parent_folder', None)
        yaml_images_list = yaml_data.get('images', None)
        try:
            tile_sample_id = self.compute_tile_sample_id(tile_id, batch_id)
            self.add_tile_sample(tile_id, batch_id, batch_time, age, species, season, settle_time, importer_id, operator)
            self.delete_source_images_of_tile_sample(tile_sample_id)
            for index, yaml_images in enumerate(yaml_images_list):
                x, y = yaml_images.get('x', None), yaml_images.get('y', None)
                filepath = yaml_images.get('file', None)
                if image_files_parent_folder is not None:
                    filepath = os.path.join(image_files_parent_folder, filepath)
                capture_id = yaml_images.get('capture_id', f'{tile_sample_id}-{x}-{y}')
                self.add_source_image(capture_id, tile_sample_id, x, y, filepath)
            return True
        except Exception as e:
            logger.warning(e)
            return False
        
    # - composite operation: obtain sample info for a tile id
    @synchronized
    def get_tile_sample_stat_as_df(self, tile_id:str) -> pd.DataFrame:
        model = pd.DataFrame(columns=('', 'Values'))
        model.loc[1] = ['Total Samples', 0]
        # retrieve date range of samples
        sql = 'SELECT MIN(batch_time) AS min, MAX(batch_time) as max FROM tile_sample WHERE tile_id = ?'
        date_range = db_tools.query_for_dict(self.db_file, sql, (tile_id,))
        if date_range['min'] is not None:
            model.loc[2] = ['Oldest Sample', date_range['min']]
            model.loc[3] = ['Latest Sample', date_range['max']]
            current_index = 4
        else:
            current_index = 2
        # retrieve count statistics of the status
        sql = 'SELECT status, COUNT(*) AS count FROM tile_sample WHERE tile_id = ? GROUP BY status ORDER BY status'
        count_list = db_tools.query_for_list_of_dicts(self.db_file, sql, (tile_id,))
        total = 0
        for index, count_dict in enumerate(count_list):
            total += count_dict['count']
            model.loc[index + current_index] = [f'# {StatusNames(count_dict["status"]).name} Status', count_dict['count']]
        model.loc[1] = ['Total Samples', total]
        return model
    
    # - composite operation: obtain the coral count trend table
    @synchronized
    def get_coral_count_trend_as_df(self, tile_id:str) -> pd.DataFrame: 
        sql = 'SELECT T.batch_time, T.age, S.coral_object_count, S.tile_sample_id \
            FROM tile_sample_detect_stat S, tile_sample T WHERE T.tile_id = ?  \
            AND S.tile_sample_id = T.id ORDER BY T.batch_time ASC'
        return db_tools.query(self.db_file, sql, (tile_id,)) 
        
    # - table: yolo_model
    @synchronized
    def add_yolo_model(self, name:str, model_file_path:str, species:str, start_day:int, end_day:int, input_image_width:int, input_image_height:int, 
                       coral_classes:list, dead_coral_classes:list, remarks:str) -> int:
        coral_classes = [] if coral_classes is None else coral_classes
        coral_classes = yaml.dump(coral_classes, Dumper=yaml.Dumper)
        dead_coral_classes = [] if dead_coral_classes is None else dead_coral_classes
        dead_coral_classes = yaml.dump(dead_coral_classes, Dumper=yaml.Dumper)        
        with db_tools.create_connection(self.db_file) as conn:
            c = conn.cursor()
            c.execute('INSERT INTO yolo_model (name, model_file_path, species, start_day, end_day, input_image_width, input_image_height, coral_classes, dead_coral_classes, remarks) '
                      'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)', 
                      (name, model_file_path, species, start_day, end_day, input_image_width, input_image_height, coral_classes, dead_coral_classes, remarks,))
            conn.commit()
            id = c.lastrowid
        return id
    
    @synchronized
    def list_yolo_model(self) -> pd.DataFrame:
        sql = 'SELECT * FROM yolo_model ORDER BY species ASC, start_day ASC'
        return db_tools.query(self.db_file, sql)    
    
    @synchronized
    def query_yolo_model(self, species, days_since_settle) -> list:
        sql = 'SELECT * FROM yolo_model WHERE species = ? AND (? >= start_day) AND (end_day == -1 or ? <= end_day) ORDER BY start_day ASC'
        result_list = db_tools.query_for_list_of_dicts(self.db_file, sql, (species, days_since_settle, days_since_settle,))  
        for result in result_list:
            try:
                result['coral_classes'] = yaml.load(result['coral_classes'], Loader=yaml.Loader)
            except:
                result['coral_classes'] = []
            try:
                result['dead_coral_classes'] = yaml.load(result['dead_coral_classes'], Loader=yaml.Loader)
            except:
                result['dead_coral_classes'] = []        
        return result_list
    
    @synchronized
    def get_yolo_model(self, name) -> list:
        sql = 'SELECT * FROM yolo_model WHERE name = ?'
        result = db_tools.query_for_dict(self.db_file, sql, (name,))  
        try:
            result['coral_classes'] = yaml.load(result['coral_classes'], Loader=yaml.Loader)
        except:
            result['coral_classes'] = []
        try:
            result['dead_coral_classes'] = yaml.load(result['dead_coral_classes'], Loader=yaml.Loader)
        except:
            result['dead_coral_classes'] = []  
        return result
    
    @synchronized
    def delete_yolo_model(self, name:str) -> int:
        sql = 'DELETE FROM yolo_model WHERE name = ?'
        return db_tools.update(self.db_file, sql, (name,))   
    
    @synchronized
    def update_yolo_model(self, name:str, species:str, start_day:int, end_day:int) -> int:
        sql = 'UPDATE yolo_model SET species = ?, start_day = ?, end_day = ? WHERE name = ?'
        return db_tools.update(self.db_file, sql, (species, start_day, end_day, name,))  

    # composite operation: validate yaml file for a new yolo model
    @synchronized
    def validate_yolo_model_file_import(self, yaml_data:dict) -> tuple:
        error_list = []
        # load and validate the data in the yaml config file which has been converted to a YamlConfig object
        name = yaml_data.get('name', None)
        file = yaml_data.get('file', None)
        species = yaml_data.get('species', None)
        valid_start_day = yaml_data.get('valid_start_day', None)
        valid_end_day = yaml_data.get('valid_end_day', None)
        if valid_start_day is None or not isinstance(valid_start_day, numbers.Number):
            valid_start_day = yaml_data['valid_end_day'] = 0
        if valid_end_day is None or not isinstance(valid_end_day, numbers.Number):
            valid_end_day = yaml_data['valid_end_day'] = -1        

        input_image_width = yaml_data.get('input_image_width', None)
        input_image_height = yaml_data.get('input_image_height', None)
        coral_classes = yaml_data.get('coral_classes', [])  
        dead_coral_classes = yaml_data.get('dead_coral_classes', [])  
        remarks = yaml_data.get('remarks', None)         
        # validate data
        if name is None or file is None or species is None:
            error_list.append(f'One of the mandatory fields (name, file, species) is missing in the yaml file')
        if input_image_width is None or input_image_height is None or not isinstance(input_image_width, numbers.Integral) or not isinstance(input_image_height, numbers.Integral):
            error_list.append(f'One of the mandatory fields (input_image_width, input_image_height) is missing or not a number in the yaml file')
             
        if error_list:
            model = pd.DataFrame(columns=('#', 'Errors'))
            for index, error in enumerate(error_list):
                model.loc[index + 1] = [index, error]
            return False, model
        else:
            model = pd.DataFrame(columns=('Parameters', 'Values'))
            model.loc[1] = ['name', name]
            model.loc[2] = ['file', file]
            model.loc[3] = ['species', species]
            model.loc[4] = ['valid period', self.get_period_str(valid_start_day, valid_end_day)]
            model.loc[5] = ['input image size', f'{input_image_width}(W) x {input_image_height}(H)']
            row_index = 6
            if len(coral_classes) == 0:
                model.loc[row_index] = ['coral classes', 'not set']
            else:
                for index, cls_name in enumerate(coral_classes):
                    if index == 0:
                        model.loc[row_index] = ['coral classes', f'{cls_name}']
                    else:
                        model.loc[row_index] = ['', f'{cls_name}'] 
                    row_index += 1
                    
            if len(dead_coral_classes) == 0:
                model.loc[row_index] = ['dead coral classes', 'not set']
            else:
                for index, cls_name in enumerate(dead_coral_classes):
                    if index == 0:
                        model.loc[row_index] = ['dead coral classes', f'{cls_name}']
                    else:
                        model.loc[row_index] = ['', f'{cls_name}'] 
                    row_index += 1            
            if remarks is not None:
                model.loc[row_index] = ['remarks', remarks]   
            return True, model
    
    @staticmethod
    def get_period_str(valid_start_day, valid_end_day):
        valid_start_day = 0 if valid_start_day is None else valid_start_day
        valid_end_day = -1 if valid_end_day is None else valid_end_day
        if valid_start_day == 0 and valid_end_day == -1:
            period = 'the whole period'
        elif valid_start_day == 0:
            period = f'from start to day {valid_end_day}'
        elif valid_end_day == -1:
            period = f'from day {valid_start_day} to the end'
        else:
            period = f'from day {valid_start_day} to day {valid_end_day}'
        return period
    
    # composite operation: import yaml file for a yolo model
    @synchronized
    def import_yolo_model_yaml(self, yaml_data:dict, default_start_day:int, default_end_day:int) -> bool:
        error_list = []
        # load and validate the data in the yaml config file which has been converted to a YamlConfig object
        name = yaml_data.get('name', None)
        model_file_path = yaml_data.get('file', None)
        species = yaml_data.get('species', None)
        valid_start_day = yaml_data.get('valid_start_day', default_start_day)
        valid_end_day = yaml_data.get('valid_end_day', default_end_day)
        input_image_width = yaml_data.get('input_image_width')
        input_image_height = yaml_data.get('input_image_height')  
        coral_classes = yaml_data.get('coral_classes', []) 
        dead_coral_classes = yaml_data.get('dead_coral_classes', []) 
        remarks = yaml_data.get('remarks', None)  
        try:
            with db_tools.create_connection(self.db_file) as conn: 
                conn.isolation_level = None  # to turn off auto-commit (may be unnecessary, minor issue, to check)
                if self.add_yolo_model(name, model_file_path, species, valid_start_day, valid_end_day, input_image_width, input_image_height, 
                                       coral_classes, dead_coral_classes, remarks) > 0:
                    return True
            logger.warning(f'Failed to add yolo model to the database')
            return False
        except Exception as e:
            logger.warning(e)
            return False
        
    # - table: detected_objet
    @synchronized
    def add_detected_object(self, tile_sample_id:str, class_name:str, class_category:int, centre_x:float, centre_y:float, 
                            corner_x1:float, corner_y1:float, size_x:float, size_y:float) -> int:
        with db_tools.create_connection(self.db_file) as conn:
            c = conn.cursor()
            c.execute('INSERT INTO detected_object (tile_sample_id, class_name, class_category, centre_x, centre_y, corner_x1, corner_y1, size_x, size_y) '
                      'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)', 
                      (tile_sample_id, class_name, class_category, centre_x, centre_y, corner_x1, corner_y1, size_x, size_y,))
            conn.commit()
            id = c.lastrowid
        return id
    
    @synchronized
    def add_detected_object_from_coral_object(self, tile_sample_id:str, coral_object:CoralObject):
        centre_x, centre_y = coral_object.centre_normalized[0], coral_object.centre_normalized[1]
        corner_x1, corner_y1 = coral_object.bbox_normalized[0], coral_object.bbox_normalized[1]
        size_x, size_y = coral_object.size_normalized[0], coral_object.size_normalized[1] 
        return self.add_detected_object(tile_sample_id, coral_object.cls_name, coral_object.class_category, 
                                        centre_x, centre_y, corner_x1, corner_y1, size_x, size_y)        
        
    @synchronized
    def delete_detected_objects_of_tile_sample(self, tile_sample_id:str) -> int:
        sql = 'DELETE FROM detected_object WHERE tile_sample_id = ?'
        return db_tools.update(self.db_file, sql, (tile_sample_id,))  
    
    @synchronized
    def query_detected_objects(self, tile_sample_id:str, object_classes=None, class_category:int=None) -> pd.DataFrame:
        param_list = [tile_sample_id]
        sql = 'SELECT * FROM detected_object WHERE tile_sample_id = ? '
        if object_classes is not None:
            if type(object_classes) in [list, tuple]:
                classes_list = ','.join('?' * len(object_classes))
                sql += f' AND class_name IN ({classes_list})'
                param_list.extend(object_classes)            
            else:
                sql += ' AND class_name = ?'
                param_list.append(object_classes)
        if class_category is not None and (type(class_category) == bool or isinstance(class_category, numbers.Number)):
            sql += f' AND class_category = ?'
            param_list.append(class_category)  
        return db_tools.query(self.db_file, sql, tuple(param_list))
    
    @synchronized
    def query_detected_objects_as_coral_objects(self, tile_sample_id:str, object_classes=None, class_category:int=None) -> list:
        detected_object_list = self.query_detected_objects(tile_sample_id, object_classes, class_category).to_dict('records')
        coral_object_list = []
        for detected_object in detected_object_list:
            # create the object from db results
            coral_object = CoralObject(
                cls_name = detected_object['class_name'],
                class_category = detected_object['class_category'],
                centre = (detected_object['centre_x'], detected_object['centre_y'],),
                bbox_normalized = (detected_object['corner_x1'], detected_object['corner_y1'], detected_object['corner_x1'] + detected_object['size_x'], detected_object['corner_y1'] + detected_object['size_y']),
                centre_normalized = (detected_object['centre_x'], detected_object['centre_y'],),
                size_normalized = (detected_object['size_x'], detected_object['size_y'],),
            )
            coral_object_list.append(coral_object)
        return coral_object_list
    
    @synchronized
    def list_detected_classes(self, tile_sample_id:str=None) -> pd.DataFrame:
        if tile_sample_id is None:
            sql = 'SELECT class_name FROM detected_object'
            return db_tools.query_for_list(self.db_file, sql)          
        else:
            sql = 'SELECT class_name FROM detected_object WHERE tile_sample_id = ?'
            return db_tools.query_for_list(self.db_file, sql, (tile_sample_id,))         


    # - table: tile sample stat
    @synchronized
    def update_tile_sample_detect_stat(self, tile_sample_id:str, tile_pixel_x, tile_pixel_y, coral_object_count, dead_coral_object_count, 
                                       other_object_count, duplicates_removed, yaml_data) -> int:
        sql = 'REPLACE INTO tile_sample_detect_stat(tile_sample_id, tile_pixel_x, tile_pixel_y, coral_object_count, dead_coral_object_count, \
            other_object_count, duplicates_removed, yaml_data) VALUES (?, ?, ?, ?, ?, ?, ?, ?)'
        return db_tools.update(self.db_file, sql, (tile_sample_id, tile_pixel_x, tile_pixel_y, coral_object_count, dead_coral_object_count, 
                                                   other_object_count, duplicates_removed, yaml_data))

    @synchronized
    def get_tile_sample_detect_stat(self, tile_sample_id:str) -> dict:
        sql = 'SELECT * FROM tile_sample_detect_stat WHERE tile_sample_id = ?'
        return db_tools.query_for_dict(self.db_file, sql, (tile_sample_id,))      


    # - composite operation: update cac
    #he
    @synchronized
    def get_detect_stat_of_tile_id(self, tile_id:str) -> list:
        sql = 'SELECT * FROM tile_sample_detect_stat S LEFT OUTER JOIN tile_sample T ON S.tile_sample_id = T.id WHERE T.tile_id = ? ORDER BY T.batch_time ASC'
        stat_list = db_tools.query_for_list_of_dicts(self.db_file, sql, (tile_id,))
        return stat_list

    @synchronized
    def update_basic_cache_tile_health_stat(self, tile_id, season, species, settle_time):
        return db_tools.update(self.db_file, 'REPLACE INTO cache_tile_health_stat(tile_id, season, species, settle_time) VALUES (?, ?, ?, ?)', (tile_id, season, species, settle_time))

    @synchronized
    def update_cache_tile_health_stat(self, tile_id, season, species, settle_time, coral_count_start, age_start, coral_count_latest, dead_coral_count_latest,
                                            other_object_count_latest, age_latest, batch_time_latest, loss_rate_whole, loss_rate_recent, num_samples, health_index, count_data):
        count_data = yaml.dump(count_data, Dumper=yaml.Dumper)
        sql = 'REPLACE INTO cache_tile_health_stat (tile_id, season, species, settle_time, coral_count_start, age_start, coral_count_latest, dead_coral_count_latest, other_object_count_latest, \
                age_latest, batch_time_latest, loss_rate_whole, loss_rate_recent, num_samples, health_index, count_yaml_data) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)'
        db_tools.update(self.db_file, sql, (tile_id, season, species, settle_time, coral_count_start, age_start, coral_count_latest, dead_coral_count_latest,
                                            other_object_count_latest, age_latest, batch_time_latest, loss_rate_whole, loss_rate_recent, num_samples, health_index, count_data)) 

    @synchronized
    def add_tile_df_to_cache_tile_health(self, tile_df:list=None):
        for index, row in tile_df.iterrows():
            sql = 'INSERT OR REPLACE INTO cache_tile_health_stat (tile_id, season, species, settle_time) SELECT ?, ?, ?, ? WHERE NOT EXISTS \
                (SELECT * FROM cache_tile_health_stat WHERE tile_id = ?)'
            db_tools.update(self.db_file, sql, (row['tile_id'], row['season'], row['species'], row['settle_time'], row['tile_id'],))

    @synchronized
    def list_all_cache_tile_health(self, season:str=None) -> list:
        if season is None:
            sql = 'SELECT * FROM cache_tile_health_stat ORDER BY tile_id ASC'
            return db_tools.query(self.db_file, sql,) 
        else:
            sql = 'SELECT * FROM cache_tile_health_stat WHERE season = ? ORDER BY tile_id ASC'
            return db_tools.query(self.db_file, sql, (season,))
        
    @synchronized
    def list_tiles_in_cache_tile_health(self, season_title:str=None) -> list:
        if type(season_title) == str:
            sql = 'SELECT MIN(settle_time) AS settle_time, tile_id, species FROM cache_tile_health_stat WHERE season = ? GROUP BY tile_id ORDER BY tile_id ASC'
            return db_tools.query(self.db_file, sql, (season_title,))   
        else:
            sql = 'SELECT MIN(settle_time) AS settle_time, tile_id, species FROM cache_tile_health_stat GROUP BY tile_id ORDER BY tile_id ASC'
            return db_tools.query(self.db_file, sql)  

    # - table: health_model
    @synchronized
    def list_health_model(self) -> pd.DataFrame:
        sql = 'SELECT * FROM health_model ORDER BY species ASC'
        return db_tools.query(self.db_file, sql)    
    
    
    @synchronized
    def get_health_model(self, species) -> dict:
        sql = 'SELECT * FROM health_model WHERE species = ?'
        result = db_tools.query_for_dict(self.db_file, sql, (species,))   
        return result
    
    @synchronized
    def delete_health_model(self, species:str) -> int:
        sql = 'DELETE FROM health_model WHERE species = ?'
        return db_tools.update(self.db_file, sql, (species,))   
    
    @synchronized
    def exist_health_model_func_name(self, func_name) -> bool:
        sql = 'SELECT COUNT(*) FROM health_model WHERE func_name = ?'
        result = db_tools.query_for_object(self.db_file, sql, (func_name,))
        return result >= 1
    
    # composite operation: validate yaml file for a new health model
    @synchronized
    def validate_health_model_file_import(self, yaml_data:dict) -> tuple:
        error_list = []
        # load and validate the data in the yaml config file which has been converted to a YamlConfig object
        species = yaml_data.get('species', None)
        func_name = yaml_data.get('func_name', None)
        func_def = yaml_data.get('func_def', None)        
        # validate data
        if species is None or func_name is None or func_def is None:
            error_list.append(f'One of the mandatory fields (species, func_name, func_def) is missing in the yaml file')
             
        if error_list:
            model = pd.DataFrame(columns=('#', 'Errors'))
            for index, error in enumerate(error_list):
                model.loc[index + 1] = [index, error]
            return False, model
        else:
            model = pd.DataFrame(columns=('Parameters', 'Values'))
            model.loc[1] = ['func_name', func_name]
            model.loc[2] = ['species', species]
            model.loc[3] = ['func_def', func_def]
            return True, model
        
    # composite operation: import yaml file for a health model
    @synchronized
    def import_health_model_yaml(self, yaml_data:dict) -> bool:
        # load and validate the data in the yaml config file which has been converted to a YamlConfig object
        species = yaml_data.get('species', None)
        func_name = yaml_data.get('func_name', None)
        func_def = yaml_data.get('func_def', None)   
        try:
            with db_tools.create_connection(self.db_file) as conn: 
                conn.isolation_level = None  # to turn off auto-commit (may be unnecessary, minor issue, to check)
                c = conn.cursor()
                c.execute('REPLACE INTO health_model (species, func_name, func_def) VALUES (?, ?, ?)', (species, func_name, func_def,))
                conn.commit()
                return True
        except Exception as e:
            logger.warning(f'Failed to add health model to the database')
            return False

    # - table: source_image
    @synchronized
    def add_task_record(self, task_type:int, task_object:str, start_time:str, used_time:float, status:int, remarks:str=None, metadata=None) -> int:
        with db_tools.create_connection(self.db_file) as conn:
            c = conn.cursor()
            if metadata is not None:
                metadata = yaml.dump(metadata, Dumper=yaml.Dumper)
            c.execute('INSERT INTO task_record (task_type, task_object, start_time, used_time, status, remarks, metadata) '
                      'VALUES (?, ?, ?, ?, ?, ?, ?)', 
                      (task_type, task_object, start_time, used_time, status, remarks, metadata,))
            conn.commit()
            id = c.lastrowid
        return id

    @synchronized
    def list_recent_task_records(self, limit=None) -> pd.DataFrame:
        if limit is None:
            sql = 'SELECT task_type, task_object, start_time, used_time, status, remarks FROM task_record ORDER BY start_time DESC'
            return db_tools.query(self.db_file, sql)  
        else:
            sql = 'SELECT task_type, task_object, start_time, used_time, status, remarks FROM task_record ORDER BY start_time DESC LIMIT ?'
            return db_tools.query(self.db_file, sql, (limit,))
    
    @synchronized
    def clear_all_task_records(self):
        sql = 'DELETE FROM task_record'
        return db_tools.update(self.db_file, sql)   

    # - composite operation: obtain task record statistics
    @synchronized
    def get_task_records_stat_as_df(self) -> pd.DataFrame:
        model = pd.DataFrame(columns=('', 'Values'))
        row_index = 1
        # number of tasks completed
        sql = 'SELECT task_type, COUNT(*) as count FROM task_record GROUP BY task_type ORDER BY task_type'
        num_task_stat_list = db_tools.query_for_list_of_dicts(self.db_file, sql)
        for num_task_stat in num_task_stat_list:
            task_name = TaskTypes(num_task_stat['task_type']).name
            model.loc[row_index] = [f'{task_name} Task Count', num_task_stat['count']]
            row_index += 1
        # mean duration of DETECT_CORAL task
        sql = 'SELECT AVG(used_time) as mean_duration FROM task_record WHERE task_type = ? AND status = ?'
        mean_duration = db_tools.query_for_object(self.db_file, sql, (TaskTypes.DETECT_CORALS.value, StatusNames.SUCCESS.value))
        if mean_duration is not None:
            model.loc[row_index] = ['DETECT_CORALS Mean Time', f'{mean_duration:.1f} s']
            row_index += 1
        return model
    
    # - table: error flag
    @synchronized
    def set_error_flag(self, id:int, remarks:str, level:int=0) -> int:
        sql = 'REPLACE INTO error_flag(id, update_time, remarks, level) VALUES (?, DATETIME("now"), ?, ?)'
        return db_tools.update(self.db_file, sql, (id, remarks, level,))    

    @synchronized
    def list_error_flags(self) -> int:
        sql = 'SELECT * FROM error_flag ORDER BY update_time DESC'
        return db_tools.query(self.db_file, sql)
    
    @synchronized
    def unset_error_flag(self, id:int) -> int:
        sql = 'DELETE FROM error_flag WHERE id = ?'
        return db_tools.update(self.db_file, sql, (id,))       

    @synchronized
    def clear_error_flags(self) -> int:
        sql = 'DELETE FROM error_flag'
        return db_tools.update(self.db_file, sql)  

# ------------------------------------------------
def manage_tables():
    CGRAS_HOME = '/home/qcr/cgras_data'
    DATABASE_FOLDER = os.path.join(CGRAS_HOME, 'database')
    DETECT_DBFM = DBFileManager(DATABASE_FOLDER, 'detector.db', DETECT_DDL)
    DETECT_DAO = DetectorDAO(DETECT_DBFM.db_file)
    # DETECT_DBFM.drop_tables([''])
    tables_name = DETECT_DBFM.list_tables_name()
    logger.info(f'tables: {tables_name}')
    DETECT_DBFM.create_tables(['error_flag'])
    DETECT_DBFM.dump_all_tables()       

# The main program for testing the clearing
# of database tables and creating them
if __name__ == '__main__':
    manage_tables()

