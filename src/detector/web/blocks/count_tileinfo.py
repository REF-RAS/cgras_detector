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
from detector.model import AIMSTILE_DAO, DETECT_DAO

class CoralCountTileInfoBlock():
    def __init__(self, app, prefix):
        self.app = app 
        self.prefix = prefix = prefix + 'drs_'
        self.update_info_id = prefix + 'update_info'
        # --- define widgets 
        self._title_badge = dbc.Badge(id=self.prefix+'_tile_id_message', className='ms-1 me-2', color='white', text_color='primary')
        self._tileinfo_datatable = dash_table.DataTable(id=prefix+'tileinfo_datatable', row_selectable=False, cell_selectable=False)
        self._detect_summary_datatable = dash_table.DataTable(id=prefix+'detect_summary_datatable', row_selectable=False, cell_selectable=False)
        self._update_info_store = dcc.Store(id=self.update_info_id)
        self._panel = html.Div([
            self._update_info_store,
            html.H3(self._title_badge),
            dbc.Row([
                dbc.Col([
                    html.H4(dbc.Badge('INFO', className='ms-1 me-2', color='white', text_color='secondary')),
                    self._tileinfo_datatable], className='col-6'),
                dbc.Col([ 
                    html.H4(dbc.Badge('SAMPLE STATISTICS', className='ms-1 me-2', color='white', text_color='secondary')),
                    self._detect_summary_datatable], className='col-6'),                
                ], className='mx-auto col-12'),
            ], 
            className='text-center')
    
        self.app.callback([Output(self.prefix+'tileinfo_datatable', 'data'),
                           Output(self.prefix+'detect_summary_datatable', 'data'),
                           Output(self.prefix+'_tile_id_message', 'children')],
            [Input(self.update_info_id, 'data')], prevent_initial_call=True, allow_duplicate=True)(self._update_datatable())   
        
    def register_trigger(self, trigger_id:str):
        # define callbacks for the datatable data
        self.app.callback([Output(self.update_info_id, 'data')],
            [Input(trigger_id, 'data')], prevent_initial_call=True, allow_duplicate=True)(self._update_panel())   
        
    def get_panel(self):
        return self._panel
    
    def _get_model(self, tile_id):
        tile_model = AIMSTILE_DAO.get_tile_info_as_df(tile_id) 
        tile_sample_stat_model = DETECT_DAO.get_tile_sample_stat_as_df(tile_id)
        message = f'TILE ID: {tile_id}'
        return tile_model, tile_sample_stat_model, message

    # callback
    def _update_datatable(self):
        def update_datatable(tile_id):
            if tile_id is None:
                raise PreventUpdate
            tile_model, tile_sample_stat_model, message = self._get_model(tile_id)
            return (tile_model.to_dict('records'), tile_sample_stat_model.to_dict('records'), message,)
        return update_datatable 
    
    def _update_panel(self):
        def update_panel(tile_id):
            if tile_id is None:
                raise PreventUpdate
            return (tile_id,)
        return update_panel 