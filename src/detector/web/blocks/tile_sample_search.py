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
from cgras_datatools.logging_tools import logger
from detector.model import DETECT_DAO
from detector.dao_detect import SampleStatusNames

class TileSampleSearchBlock():
    def __init__(self, app, prefix):
        self.app = app 
        self.prefix = prefix = prefix + 'tss_'
        self.search_clicked_trigger_id = prefix + 'search_query_store'
        self.external_trigger_id = prefix + 'external_trigger_store'
        # define widgets
        tile_id_textbox = dcc.Input(id=prefix+'tile_id_input', type='text', placeholder='Tile ID', className='', style={'width': '240px'})
        batch_id_textbox = dcc.Input(id=prefix+'batch_id_input', type='text', placeholder='Batch ID', className='ms-2', style={'width': '240px'})
        # the period filter
        self.period_options = [
            {'label': 'Past Day', 'value': -1},
            {'label': 'Past Week', 'value': -7},
            {'label': 'Past Month', 'value': -31},
            {'label': 'All Time', 'value': 0},
        ]
        period_dropdown = dcc.Dropdown(id=prefix+'period_dropdown', 
                                       searchable=False, clearable=False, className='ms-2', style={'width': '240px', 'zIndex': 10})
        # the status filter
        self.status_options = [
            {'label': 'All', 'value': SampleStatusNames.ALL.value},
            {'label': 'Rejected or Flagged', 'value': SampleStatusNames.REJECTED.value},
            {'label': 'Done', 'value': SampleStatusNames.DONE.value},
            # {'label': 'Flagged', 'value': SampleStatusNames.FLAGGED.value},
            # {'label': 'Rejected', 'value': SampleStatusNames.REJECTED.value},
        ]
        status_dropdown = dcc.Dropdown(options=self.status_options, id=prefix+'status_dropdown', 
                                       searchable=False, clearable=False, className='ms-2', style={'width': '240px', 'zIndex': 10})  
        # the page size filter
        self.pagesize_options = [
            {'label': 'Recent 10', 'value': 10},
            {'label': 'Recent 25', 'value': 25},
            {'label': 'Recent 100', 'value': 100},
            {'label': 'Recent 250', 'value': 250},]
        pagesize_dropdown = dcc.Dropdown(options=self.pagesize_options, id=prefix+'pagesize_dropdown', 
                                       searchable=False, clearable=False, className='ms-2', maxHeight=200, style={'width': '160px', 'zIndex': 10})
      
        self.tile_sample_search_panel = html.Div([
                dcc.Store(id=self.search_clicked_trigger_id),
                html.H4(dbc.Badge('SEARCH PROCESSED TILE SAMPLES', className='ms-1 me-2', color='white', text_color='secondary')),
                dbc.Row(children=[
                    html.Span('Filters: ', className='col-2'),
                    tile_id_textbox, 
                    batch_id_textbox,
                    period_dropdown,
                    status_dropdown,
                    pagesize_dropdown,
                    dbc.Button('Reset', id=prefix+'reset_filter_button', n_clicks=0, className='ms-4', color='secondary', size='sm', style={'width': '80px', 'marginLeft': '20px'}),
                    dcc.Store(id=self.external_trigger_id),
                ]),
                
            ], id=prefix+'main_panel', className='mx-auto text-center', style={'zIndex': 10})
        
        self.app.callback([Output(prefix+'tile_id_input', 'value', allow_duplicate=True),
                           Output(prefix+'batch_id_input', 'value', allow_duplicate=True),
                           Output(prefix+'period_dropdown', 'options', allow_duplicate=True),
                           Output(prefix+'period_dropdown', 'value', allow_duplicate=True),
                           Output(prefix+'pagesize_dropdown', 'value', allow_duplicate=True),
                           Output(prefix+'status_dropdown', 'value', allow_duplicate=True),
                           # Output(prefix+'refresh_button', 'n_clicks', allow_duplicate=True),
                           ],
                            [
                            Input(prefix+'reset_filter_button', 'n_clicks'),
                            Input(prefix+'main_panel', 'children'),
                            ], prevent_initial_call='initial_duplicate')(self._reset_filter_button_clicked())  

        self.app.callback([Output(prefix+'search_query_store', 'data')],
                            [
                            # Input(prefix+'refresh_button', 'n_clicks'),
                            Input(prefix+'tile_id_input', 'value'),
                            Input(prefix+'batch_id_input', 'value'),
                            Input(prefix+'period_dropdown', 'value'),
                            Input(prefix+'pagesize_dropdown', 'value'),
                            Input(prefix+'status_dropdown', 'value'),  
                            Input(self.external_trigger_id, 'data'),                           
                            ], prevent_initial_call=True)(self._refresh_table_clicked())  

     
    def get_panel(self):
        return self.tile_sample_search_panel

    def register_trigger(self, trigger_id:str):
        # define callbacks for the datatable data
        self.app.callback([Output(self.external_trigger_id, 'data', allow_duplicate=True)],
            [Input(trigger_id, 'data')], prevent_initial_call=True, allow_duplicate=True)(self._external_triggered())

    def get_search_clicked_trigger_id(self):
        return self.search_clicked_trigger_id

    def _reset_filter_button_clicked(self):
        def reset_filter_button_clicked(n_clicks, _):
            period_options = self.period_options
            season_titles_list = DETECT_DAO.list_seasons_in_tile_sample()
            for season_title in season_titles_list:
                period_options.append({'label': f'{season_title} Season', 'value': season_title})
            value = 0
            return ('', '', period_options, value, 10, SampleStatusNames.ALL.value,)
        return reset_filter_button_clicked
    
    def _refresh_table_clicked(self):
        def refresh_table_clicked(tile_id, batch_id, the_period, the_pagesize, the_status, store):
            button_id = ctx.triggered_id if ctx.triggered_id is not None else 'No clicks yet'
            # set default value at initialization
            if the_status == SampleStatusNames.REJECTED:
                the_status = [SampleStatusNames.REJECTED, SampleStatusNames.FLAGGED]
            else:
                the_status = None if the_status == SampleStatusNames.ALL.value or the_status is None else the_status
            the_pagesize = 10 if the_pagesize is None else the_pagesize
            if isinstance(the_period, str):
                season = the_period
                the_period = 0
            else:
                season = None
            # build the query structure
            query = [season, the_status, tile_id, batch_id, the_period, the_pagesize,]
            return (query,)
        return refresh_table_clicked
    
    def _external_triggered(self):
        def external_triggered(store):
            return (store,)
        return external_triggered

    
    