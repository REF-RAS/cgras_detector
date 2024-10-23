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
from detector.model import AIMSTILE_DAO

class TileStatBlock():
    def __init__(self, app, prefix):
        self.app = app
        self.prefix = prefix = prefix + 'ts_'
        # --- define widgets
        _tilestat_datatable = dash_table.DataTable(id=prefix+'tile_stat_table')

        self.tile_stat_panel = dbc.Col([
                html.H4(dbc.Badge('TILE ID STATISTICS', className='ms-1 me-2', color='white', text_color='secondary')),
                dbc.Row([_tilestat_datatable], className='mx-auto col-12'),
            ], className='mx-auto text-center')
        
    def get_panel(self):
        return self.tile_stat_panel
        
    def register_trigger(self, trigger_id:str):
        self.app.callback(Output(self.prefix+'tile_stat_table', 'data'),
            [Input(trigger_id, 'data')], prevent_initial_call=False)(self._update_tile_stat_table())  
        
    def _define_tilestat_model(self):   
        return AIMSTILE_DAO.query_tile_stat()
        
    # callback for the tile stat table
    def _update_tile_stat_table(self):
        def update_tile_stat_table(data):
            model = self._define_tilestat_model()
            if model is None:
                raise PreventUpdate
            return model.to_dict('records')
        return update_tile_stat_table  
    