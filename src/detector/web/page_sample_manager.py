# Copyright 2024 - Andrew Kwok Fai LUI, 
# Robotics and Autonomous Systems Group, REF, RI
# and the Queensland University of Technology

__author__ = 'Andrew Lui'
__copyright__ = 'Copyright 2024'
__license__ = 'GPL'
__version__ = '1.0'
__email__ = 'ak.lui@qut.edu.au'
__status__ = 'Development'

import pandas as pd
import dash
from dash import html, dcc, callback, Input, Output, State, ctx, dash_table
import dash_bootstrap_components as dbc
# project modules
from dash.exceptions import PreventUpdate
from tools.logging_tools import logger
from detector.web.blocks import TileSampleImportFileBlock, TileSampleTable, TileSampleSearchBlock, EnableTileSamplesImportBlock

dash.register_page(__name__)

# -- define the GUI components of this page
class SampleManagerPage():
    def __init__(self, app):
        self.app = app
        prefix = 'sample_manage_'
        self.tile_sample_import_panel = TileSampleImportFileBlock(app, prefix)
        self.pending_sample_table = TileSampleTable(app, prefix, allow_priority=True, allow_reprocess=False)
        self.tile_sample_retrieve_panel = EnableTileSamplesImportBlock(app, prefix)
        self.tile_sample_search_panel = TileSampleSearchBlock(app, prefix)
        self.processed_sample_table = TileSampleTable(app, prefix + 'btm_', allow_priority=False, allow_reprocess=True, allow_reload=True, allow_view=True)

        self._define_page()
    
    def layout(self, validate=False):
        return self._layout

    def _define_page(self):
        # connect the system interval timer to the pending_sample_table and the tile_sample_retrieve_panel
        self.pending_sample_table.register_trigger('dashapp_interval_store')
        self.tile_sample_retrieve_panel.register_trigger('dashapp_interval_store')
        # connect the tile_sample_search_panel output to the input of processed_tile_sample_edit_table
        self.processed_sample_table.register_trigger(self.tile_sample_search_panel.get_search_trigger_id())

        # putting the components together 
        rows = html.Div(id='scan-body', children =[
            dbc.Row(html.H3(children = 'Sample Processing Manager', className='mt-3 mb-3')),
            dbc.Row(html.H4(children = 'Import of Tile Samples', className='text-center mt-5 mb-3')),
            dbc.Row([dbc.Col(self.tile_sample_retrieve_panel.get_panel(), className='col-6 border'), 
                     dbc.Col(self.tile_sample_import_panel.get_panel(), className='col-6 border')
                     ], className='mx-auto'),
            dbc.Row(html.H4( children = 'Queued Samples (Pending Analysis)', className='text-center mt-5 mb-3')),
            dbc.Row([dbc.Col(self.pending_sample_table.get_panel(), className='col-12 border'), 
                     ], className='mx-auto'),
            dbc.Row(html.H4(children = 'Processed Samples', className='text-center mt-5 mb-3')),
            dbc.Row([dbc.Col(self.tile_sample_search_panel.get_panel(), className='col-12 border'), 
                     ], className='mx-auto', style={'white-space': 'nowrap', 'overflow': 'hidden'}),        
            dbc.Row([dbc.Col(self.processed_sample_table.get_panel(), className='col-12 border'), 
                     ], className='mx-auto mp-6', style={'padding-bottom': '80px'}),                   
        ], className='mx-auto col-10')
        self._layout = dbc.Container(rows, fluid=True)


