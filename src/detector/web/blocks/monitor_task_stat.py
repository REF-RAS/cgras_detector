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
from detector.model import DETECT_DAO

class MonitorTaskStatBlock():
    def __init__(self, app, prefix):
        self.app = app
        self.prefix = prefix = prefix + 'mtsb_'
        # define style
        style_data_conditional = [
            {'if': {'row_index': 0},
                'backgroundColor': '#FFFF99',
                'font-weight': 'bold'},]
        # define widgets
        _datatable = dash_table.DataTable(id=prefix+'datatable', style_data_conditional=style_data_conditional, style_cell={'fontSize': 14})

        self.tile_stat_panel = dbc.Col([
                html.H4(dbc.Badge('STATISTICS', className='ms-2 mb-4', color='white', text_color='secondary')),
                dbc.Row([_datatable], className='mx-auto col-12'),
            ], className='mx-auto text-center')
        
    def get_panel(self):
        return self.tile_stat_panel
        
    def register_trigger(self, trigger_id:str):
        self.app.callback(Output(self.prefix+'datatable', 'data'),
            [Input(trigger_id, 'data')], prevent_initial_call=False)(self._update_tile_stat_table())  
        
    def _update_model(self):   
        return DETECT_DAO.get_task_records_stat_as_df()
        
    # callback for the tile stat table
    def _update_tile_stat_table(self):
        def update_tile_stat_table(data):
            model = self._update_model()
            if model is None:
                raise PreventUpdate
            return model.to_dict('records')
        return update_tile_stat_table  
    