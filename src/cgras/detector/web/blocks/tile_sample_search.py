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
from collections import OrderedDict
import pandas as pd
# dash modules
import dash
from dash import html, dcc, Input, Output, State, dash_table, ctx
import dash_bootstrap_components as dbc
from dash.exceptions import PreventUpdate
from cgras.tools.logging_tools import logger
from cgras.detector.model import APP_FILE_MANAGER, DETECT_DAO
from cgras.detector.dao_detect import StatusNames

class TileSampleSearchBlock():
    def __init__(self, app, prefix):
        self.app = app 
        self.prefix = prefix = prefix + 'tss_'
        self.search_trigger_id = prefix + 'tile_sample_list'
        # define widgets
        tile_id_textbox = dcc.Input(id=prefix+'tile_id_input', type='text', placeholder='Tile ID', className='', style={'width': '240px'})
        batch_id_textbox = dcc.Input(id=prefix+'batch_id_input', type='text', placeholder='Batch ID', className='ms-2', style={'width': '240px'})
        # the period filter
        self.period_options = [
            {'label': 'Past Day', 'value': -1},
            {'label': 'Past Week', 'value': -7},
            {'label': 'Past Month', 'value': -31},
            {'label': 'The Season', 'value': 0},
        ]
        period_dropdown = dcc.Dropdown(options=self.period_options, id=prefix+'period_dropdown', 
                                       searchable=False, clearable=False, className='ms-2', maxHeight=80, style={'width': '160px', 'zIndex': 10})
        # the status filter
        self.status_options = [
            {'label': 'All Status', 'value': StatusNames.UNKNOWN.value},
            {'label': 'Failed', 'value': StatusNames.FAILED.value},
            {'label': 'Aborted', 'value': StatusNames.ABORTED.value},
            {'label': 'Success', 'value': StatusNames.SUCCESS.value},]
        status_dropdown = dcc.Dropdown(options=self.status_options, id=prefix+'status_dropdown', 
                                       searchable=False, clearable=False, className='ms-2', maxHeight=80, style={'width': '160px', 'zIndex': 10})  
        # the page size filter
        self.pagesize_options = [
            {'label': 'Recent 10', 'value': 10},
            {'label': 'Recent 25', 'value': 25},
            {'label': 'Recent 100', 'value': 100},
            {'label': 'Recent 250', 'value': 250},]
        pagesize_dropdown = dcc.Dropdown(options=self.pagesize_options, id=prefix+'pagesize_dropdown', 
                                       searchable=False, clearable=False, className='ms-2', maxHeight=80, style={'width': '160px', 'zIndex': 10})
      
        self.tile_sample_search_panel = dbc.Col([
                dcc.Store(id=self.search_trigger_id),
                html.H4(dbc.Badge('SEARCH PROCESSED TILE SAMPLES', className='ms-1 me-2', color='white', text_color='secondary')),
                dbc.Row(children=[
                    html.Span('Filters: ', className='col-2'),
                    tile_id_textbox, 
                    batch_id_textbox,
                    period_dropdown,
                    status_dropdown,
                    pagesize_dropdown,
                ]),
                dbc.Row(children=[
                    html.Span(' ', className='col-2'),
                    dbc.Button('Refresh', id=prefix+'refresh_button', n_clicks=0, className='', color='primary', size='sm', style={'width': '160px'}),
                    dbc.Button('Reset', id=prefix+'reset_filter_button', n_clicks=0, className='ms-4', color='secondary', size='sm', style={'width': '160px'})
                ], className='mt-2 mb-5'),
                
            ], className='mx-auto text-center')
        
        self.app.callback([Output(prefix+'tile_id_input', 'value', allow_duplicate=True),
                           Output(prefix+'batch_id_input', 'value', allow_duplicate=True),
                           Output(prefix+'period_dropdown', 'value', allow_duplicate=True),
                           Output(prefix+'pagesize_dropdown', 'value', allow_duplicate=True),
                           Output(prefix+'status_dropdown', 'value', allow_duplicate=True),],
                            [
                            Input(prefix+'reset_filter_button', 'n_clicks'),
                            ], prevent_initial_call='initial_duplicate')(self._reset_filter_button_clicked())  

        self.app.callback([Output(prefix+'tile_sample_list', 'data')],
                            [
                            Input(prefix+'refresh_button', 'n_clicks'),
                            State(prefix+'tile_id_input', 'value'),
                            State(prefix+'batch_id_input', 'value'),
                            State(prefix+'period_dropdown', 'value'),
                            State(prefix+'pagesize_dropdown', 'value'),
                            State(prefix+'status_dropdown', 'value'),                            
                            ], prevent_initial_call='initial_duplicate')(self._refresh_table_clicked())  

    def get_search_trigger_id(self):
        return self.search_trigger_id

    def _reset_filter_button_clicked(self):
        def clear_filter_button_clicked(n_clicks):
            return ('', '', 0, 10, StatusNames.UNKNOWN.value)
        return clear_filter_button_clicked
    
    def _refresh_table_clicked(self):
        def refresh_table_clicked(refresh_button, tile_id, batch_id, the_period, the_pagesize, the_status):
            button_id = ctx.triggered_id if not None else 'No clicks yet'
            # set default value at initialization
            the_status = None if the_status == StatusNames.UNKNOWN.value or the_status is None else the_status
            the_period = None if the_period == 0 else the_period
            the_pagesize = 10 if the_pagesize is None else the_pagesize
            # build the query structure
            query = [the_status, tile_id, batch_id, the_period, the_pagesize, ]
            return (query,)
        return refresh_table_clicked
    
    def get_panel(self):
        return self.tile_sample_search_panel