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
from cgras.detector.model import AIMSTILE_DAO, DETECT_DAO


def add_settle_time_to_tile_sample():
    tile_df = AIMSTILE_DAO.list_all_tiles()
    print(tile_df)
    sql = 'UPDATE tile_sample SET settle_time = ? WHERE tile_id = ?'
    for index, row in tile_df.iterrows():
        db_tools.update(DETECT_DAO.db_file, sql, (row['settle_time'], row['tile_id']))


if __name__ == '__main__':
    add_settle_time_to_tile_sample()
