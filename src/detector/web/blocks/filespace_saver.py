# Copyright 2024 - Andrew Kwok Fai LUI, 
# Robotics and Autonomous Systems Group, REF, RI
# and the Queensland University of Technology

__author__ = 'Andrew Lui'
__copyright__ = 'Copyright 2024'
__license__ = 'GPL'
__version__ = '1.0'
__email__ = 'ak.lui@qut.edu.au'
__status__ = 'Development'

import shutil
import pandas as pd
# dash modules
import dash
from dash import html, dcc, Input, Output, State, dash_table, ctx
import dash_bootstrap_components as dbc
from dash.exceptions import PreventUpdate
from detector.model import APP_FILE_MANAGER

class FileSpaceSaver():
    def __init__(self, app, prefix):
        self.app = app 
        self.prefix = prefix = prefix + 'fss_'
        # define widgets 
        self.filespace_saver_panel = html.Div([
            html.H4(dbc.Badge('FILE SPACE SAVER', className='ms-1 me-2', color='white', text_color='secondary')),
            ], className='col-6 text-center')
    
    def get_panel(self):
        return self.filespace_saver_panel