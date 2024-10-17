# Copyright 2024 - Andrew Kwok Fai LUI, 
# Robotics and Autonomous Systems Group, REF, RI
# and the Queensland University of Technology

__author__ = 'Andrew Lui'
__copyright__ = 'Copyright 2024'
__license__ = 'GPL'
__version__ = '1.0'
__email__ = 'ak.lui@qut.edu.au'
__status__ = 'Development'

import sys, random
from cgras.tools import db_tools
from cgras.detector.model import DETECT_DAO


def add_new_cache_tile_health_stat():   
    DETECT_DAO.update_cache_tile_health_stat(
        tile_id = '2023Dec-P00002',
        season = '2023Dec',
        species = 'gorgonia flabellum', 
        settle_time = '2023-11-13', 
        coral_count_start = 2000, 
        age_start = 5, 
        coral_count_latest = 1700, 
        dead_coral_count_latest = 0,
        other_object_count_latest = 0, 
        age_latest = 50, 
        batch_time_latest = '2024-1-2', 
        loss_rate_whole = -0.015, 
        loss_rate_recent = -0.015, 
        num_samples = 4, 
        health_index = 0.1, 
        count_data = '')
    
    DETECT_DAO.update_cache_tile_health_stat(
        tile_id = '2023Dec-P00003',
        season = '2023Dec',
        species = 'acropora palmata', 
        settle_time = '2023-11-13', 
        coral_count_start = 1800, 
        age_start = 5, 
        coral_count_latest = 1600, 
        dead_coral_count_latest = 0,
        other_object_count_latest = 0, 
        age_latest = 50, 
        batch_time_latest = '2024-1-2', 
        loss_rate_whole = -0.012, 
        loss_rate_recent = -0.012, 
        num_samples = 3, 
        health_index = 0.4, 
        count_data = '')
    
    DETECT_DAO.update_cache_tile_health_stat(
        tile_id = '2023Dec-P00004',
        season = '2023Dec',
        species = 'gorgonia flabellum', 
        settle_time = '2023-11-14', 
        coral_count_start = 1400, 
        age_start = 4, 
        coral_count_latest = 1300, 
        dead_coral_count_latest = 0,
        other_object_count_latest = 0, 
        age_latest = 42, 
        batch_time_latest = '2023-12-28', 
        loss_rate_whole = -0.010, 
        loss_rate_recent = -0.018, 
        num_samples = 4, 
        health_index = 0.5, 
        count_data = '')
    
    DETECT_DAO.update_cache_tile_health_stat(
        tile_id = '2023Dec-P00005',
        season = '2023Dec',
        species = 'gorgonia flabellum', 
        settle_time = '2023-11-14', 
        coral_count_start = 1450, 
        age_start = 4, 
        coral_count_latest = 920, 
        dead_coral_count_latest = 0,
        other_object_count_latest = 0, 
        age_latest = 42, 
        batch_time_latest = '2023-12-28', 
        loss_rate_whole = -0.025, 
        loss_rate_recent = -0.026, 
        num_samples = 4, 
        health_index = 0.5, 
        count_data = '')

def remove_cache_tile_health_stat(tile_id):
    db_tools.update(DETECT_DAO.db_file, 'DELETE FROM cache_tile_health_stat WHERE tile_id == ?', (tile_id,))



if __name__ == '__main__':
    # remove_cache_tile_health_stat('2023Dec-P0002')
    # remove_cache_tile_health_stat('2023Dec-P0003')
    # remove_cache_tile_health_stat('2023Dec-P0004')
    # remove_cache_tile_health_stat('2023Dec-P0005')    
    
    add_new_cache_tile_health_stat()
