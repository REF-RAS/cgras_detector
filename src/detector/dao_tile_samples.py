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

import os, datetime, time, shutil, numbers, yaml, json, traceback
import pandas as pd
from enum import Enum
from datetime import datetime as dt
# project modules
import cgras_datatools.db_tools as db_tools
from cgras_datatools.lock_tools import synchronized
from cgras_datatools.logging_tools import logger
from detector.database_file import DBFile
from detector.system_config import SystemConfig, SystemConfigNames

CONFIG:SystemConfig = SystemConfig(os.path.join(os.path.dirname(__file__), '../../config/system_config.yaml'))

class TileSamplesDAO:  
    def __init__(self, db_file:str, **kwargs):
        self.db_file = db_file

    @synchronized
    def query_to_export_sample_as_list_tuples(self) -> list:
        try:
            sql = 'SELECT tile_id, batch_id from captured_tile_sample WHERE export_time IS NULL AND status > 0'
            results_list = db_tools.query_for_list_of_dicts(self.db_file, sql)
            results = [(x['tile_id'], x['batch_id'],) for x in results_list]
            return results
        except Exception as e:
            logger.warning(f'query_to_export_sample_as_list_tuples: {e} {self.db_file}')
            return [] 
    
    @synchronized
    def update_export_time_of_tile_sample(self, tile_id:str, batch_id:str) -> bool:
        sql = 'UPDATE captured_tile_sample SET export_time = DATETIME("now", "localtime") WHERE tile_id = ? AND batch_id = ?'
        db_tools.update(self.db_file, sql, (tile_id, batch_id,))    
    
    @synchronized
    def export_tile_sample_as_dict(self, tile_id:str, batch_id:str, auto_update_export_time:bool=True):     
        with db_tools.create_connection(self.db_file) as conn:       
            try:
                sample_dict = {'tile_id': tile_id, 'batch_id': batch_id}
                c = conn.cursor() 
                # populate the tile information
                result = c.execute('SELECT species, spawn_time, settle_time, season FROM tile WHERE tile_id = ?', (tile_id,)).fetchone()
                if result is None:
                    return None              
                sample_dict['species'] = result[0]
                sample_dict['spawn_time'] = result[1]
                sample_dict['settle_time'] = result[2]
                sample_dict['season'] = result[3]
                # populate the num_tabs
                result = c.execute('SELECT tab_ncols, tab_nrows FROM season WHERE title = ?', (sample_dict['season'],)).fetchone()
                if result is None:
                    return None         
                sample_dict['num_tabs'] = [result[0], result[1]]        
                # populate the batch_time
                result = c.execute('SELECT start_time FROM batch WHERE batch_id = ?', (batch_id,)).fetchone()
                if result is None:
                    return None
                sample_dict['batch_time'] = result[0]
                sample_dict['importer'] = 'POLL_IMPORTER'
                sample_dict['operator'] = 'Unknown'
                # populate the image list
                results_list = c.execute('SELECT capture_x, capture_y, image_filename, metadata FROM captured_image WHERE tile_id = ? AND batch_id = ?', (tile_id, batch_id,)).fetchall()
                if results_list is None:
                    return None
                # images_folder_ = '/home/qcr/cgras_data/images/{tile_id}_{batch_id}/Original'
                captured_images_folder = str.format(CONFIG.get(SystemConfigNames.CGRAS_CAPTURED_IMAGES_FOLDER), 
                                                    tile_id=tile_id, batch_id=batch_id)
                sample_dict['image_files_parent_folder'] = captured_images_folder
                images_list = []
                for result in results_list:
                    image_dict = {'x': result[0], 'y': result[1], 'file': result[2], 'metadata': result[3]}  # metadata in yaml string format
                    images_list.append(image_dict)  
                sample_dict['images'] = images_list    
                # update the export time if applicable
                if auto_update_export_time:
                    self.update_export_time_of_tile_sample(tile_id, batch_id)
                # return the exported tile sample
                return sample_dict
            except Exception as e:
                logger.error(e)
                traceback.print_exc()
        return None


# ------------------------------------------------
def test_import_sample():
    CGRAS_DATA_FOLDER = '/home/qcr/cgras_data'
    DATABASE_FOLDER = os.path.join(CGRAS_DATA_FOLDER, 'database')
    db_file = os.path.join(DATABASE_FOLDER, 'coordinator.db')
    # data
    tile_id = '2024Oct-MIS5T13'
    batch_id = 'CG1_241219102421'
    # create IMPORT SAMPLE DAO
    IMPORT_SAMPLE_DAO = TileSamplesDAO(db_file)
    yaml_data = IMPORT_SAMPLE_DAO.export_tile_sample_as_dict(tile_id, batch_id)
    print(yaml_data)
    print(yaml.dump(yaml_data))
    return yaml_data

# The main program for testing the clearing
# of database tables and creating them
if __name__ == '__main__':
    test_import_sample()