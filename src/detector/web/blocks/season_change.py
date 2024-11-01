# Copyright 2024 - Andrew Kwok Fai LUI, 
# Robotics and Autonomous Systems Group, REF, RI
# and the Queensland University of Technology

__author__ = 'Andrew Lui'
__copyright__ = 'Copyright 2024'
__license__ = 'GPL'
__version__ = '1.0'
__email__ = 'ak.lui@qut.edu.au'
__status__ = 'Development'

import base64, io, traceback, shutil, datetime
import pandas as pd
# dash modules
import dash
from dash import html, dcc, Input, Output, State, dash_table, ctx
import dash_bootstrap_components as dbc
from dash.exceptions import PreventUpdate
import tools.file_tools as file_tools
from tools.logging_tools import logger
from detector.model import AIMSTILE_DAO


class SpawningSeasonChangeBlock():
    def __init__(self, app, prefix):
        self.app = app
        self.prefix = prefix = prefix + 'stb_'
        # --- define widgets
        message_alert = dbc.Alert('Nothing is happening', id=prefix+'message_alert', dismissable=True, duration=5000,
                                 is_open=False, className='col-12')
        confirm_dialog = dcc.ConfirmDialog(id=prefix+'confirm_dialog',
            message='All operations will be in the context of the changed spawning season?',)
        
        # define create new spawning season modal
        season_title_input = dbc.Row([
            dbc.Label('Season Title', html_for=prefix+'title_input', width=2),
            dbc.Col(dbc.Input(type='text', id=prefix+'title_input', placeholder='Enter season title (e.g. 2024Nov)'), width=10),
        ], className='mb-3',)
        
        season_date_range_input = dbc.Row([
            dbc.Label('Season Title', html_for=prefix+'date_range_input', width=2),
            dbc.Col(dcc.DatePickerRange(
                id=prefix+'date_range_input',
                min_date_allowed=datetime.date(2024, 1, 1),
                max_date_allowed=datetime.date(2050, 12, 31),
                initial_visible_month=datetime.datetime.today().strftime('%Y-%m-%d')), width=10),
        ], className='mb-3',) 
        
        blocks_dim_input = dbc.Row([
            dbc.Label('Block Dimension', html_for=prefix+'title_input', width=2),
            dbc.Col(dbc.Input(type='number', id=prefix+'block_nrols_input', placeholder='Enter # columns'), width=3),
            dbc.Col(dbc.Input(type='number', id=prefix+'block_nrows_input', placeholder='Enter # rows'), width=3),
        ], className='mb-3',)        
        
        define_season_form = dbc.Form([season_title_input, season_date_range_input, blocks_dim_input])       

        define_season_modal = dbc.Modal(id=prefix+'create_modal', children=[
                dbc.ModalHeader(dbc.ModalTitle(children='Define Spawning Season', id=prefix+'create_modal_title')),
                dbc.ModalBody(children=[html.P(id=prefix+'create_modal_textbox', className='text-danger'),
                                        html.P('Enter the title and the date range of the new spawning season. The title must not contain a dash.', style={}),
                                        define_season_form,
                                        html.Div(id=prefix+'create_modal_button_panel', children=[
                                            dbc.Button('Define New Season', id=prefix+'create_confirm_button', n_clicks=0, className='me-3'), 
                                            dbc.Button('Cancel', id=prefix+'create_cancel_button', n_clicks=0, color='secondary'),], 
                                        className='text-center, mt-3', style={'display': 'block'}),
                                        ]),
            ], size='xl', is_open=False,)  
        
        season_list, active_season = self.query_spawning_seasons()
        
        self._season_select_panel = html.Div([
            html.H4(dbc.Badge('SELECTED SPAWNING SEASON', className='ms-1 me-2', color='white', text_color='secondary')),
            html.P('Use the dropdown to change the spawning season for subsequent operations on this system.', style={'display': 'inline-block'}),
            dcc.Dropdown(season_list, active_season, id=prefix+'season_list_dropdown', className='col-4 d-inline-block', searchable=False, clearable=False),
            html.P('Click the below button to define a new spawning season.', style={}),
            dbc.Button('Define New Season', id=prefix+'create_button', color='primary', className='mb-3'), 
            message_alert,
        ])
        
        self._season_table_panel = html.Div([
            html.H4(dbc.Badge('SEASON INFO', className='ms-1 me-2', color='white', text_color='secondary')),
            dash_table.DataTable(id=prefix+'datatable', style_cell={'fontSize': 14}),
        ])
        
        self._the_panel = html.Div([
                dcc.Store(id=prefix+'season_changed_store'),
                confirm_dialog,
                define_season_modal,
                dbc.Row([
                    dbc.Col(self._season_select_panel, className='col-6'),
                    dbc.Col(self._season_table_panel, className='col-6'),
                ], className='col-12')
            ], className='text-center pb-3')
        
        
        
        self.app.callback([Output(prefix+'message_alert', 'is_open', allow_duplicate=True),
                           Output(prefix+'message_alert', 'children', allow_duplicate=True),
                           Output(prefix+'datatable', 'data'),],
            [Input(prefix+'confirm_dialog', 'submit_n_clicks'),
             State(prefix+'season_list_dropdown', 'value')], 
            prevent_initial_call='initial_duplicate')(self._season_changed_confirmed())
     
        self.app.callback([Output(prefix+'confirm_dialog', 'displayed'),
                           Output(prefix+'confirm_dialog', 'message'),
                           ],
            [Input(prefix+'season_list_dropdown', 'value')], 
            prevent_initial_call=True)(self._change_season_received())
        
        self.app.callback([Output(prefix+'season_list_dropdown', 'options'),
                           Output(prefix+'season_list_dropdown', 'value'),],
            [Input(prefix+'season_changed_store', 'data')], 
            prevent_initial_call=True)(self._update_season_list())  
        
        self.app.callback([Output(prefix+'create_modal', 'is_open', allow_duplicate=True),],
                            [Input(prefix+'create_button', 'n_clicks')], 
            prevent_initial_call=True)(self._create_button_pressed())
        
        # callback setup for the tile sample import area and confirm dialog
        self.app.callback([Output(prefix+'message_alert', 'is_open'),
                           Output(prefix+'message_alert', 'children'),
                           Output(prefix+'create_modal', 'is_open', allow_duplicate=True),
                           Output(prefix+'season_changed_store', 'data'),],
                        [Input(prefix+'create_confirm_button', 'n_clicks'),
                        Input(prefix+'create_cancel_button', 'n_clicks'),
                        State(prefix+'title_input', 'value'),
                        State(prefix+'date_range_input', 'start_date'),
                        State(prefix+'date_range_input', 'end_date'),
                        State(prefix+'block_nrols_input', 'value'),
                        State(prefix+'block_nrows_input', 'value'),                       
                        ], 
            prevent_initial_call=True)(self._create_season_confirmed())
        
    def get_panel(self):
        return self._the_panel
    
    def get_success_trigger_id(self):
        return self.prefix+'tile_import_success'
    
    def query_spawning_seasons(self):
        season_list = AIMSTILE_DAO.get_season_titles_list()
        active_season_title = AIMSTILE_DAO.get_active_season_title()
        return (season_list, active_season_title)

    # the callback for change season confirmed
    def _season_changed_confirmed(self): 
        def season_changed_confirmed(submit_n_clicks, season):
            message = None
            show_message = False
            if submit_n_clicks:
                result = AIMSTILE_DAO.set_active_season(season)
                show_message = True
                message = 'changed active spawning season is successful'
                if result == 0:
                    message = f'unable to change spawning season to "{season}"'
            # get the info of the active season as a dataframe
            model = AIMSTILE_DAO.get_active_season_info_as_df()
            if model is None:
                return (show_message, message, None)                    
            return (show_message, message, model.to_dict('records')) 
            
        return season_changed_confirmed  
     
    # the callback for changed season dropdown event
    def _change_season_received(self): 
        def change_season_received(season):       
            message = f'All operations will be in the context of the spawning season "{season}". Confirm?'
            return (True, message,)  
        return change_season_received 
    
    def _update_season_list(self): 
        def update_season_list(update):       
            if update:
                return self.query_spawning_seasons() 
        return update_season_list  
    
    def _create_button_pressed(self): 
        def create_button_pressed(submit_n_clicks):    
            if submit_n_clicks:
                return (True,)
            return (False,)
        return create_button_pressed  

    def _create_season_confirmed(self): 
        def create_season_confirmed(confirm_button, cancel_button, title:str, start_date:str, end_date:str, blocks_ncols:int, blocks_nrows:int):
            button_id = ctx.triggered_id if not None else 'No clicks yet'                
            if button_id.endswith('create_confirm_button'):
                if blocks_ncols is None or blocks_nrows is None or blocks_ncols <= 0 or blocks_nrows <= 0:
                    return (True, 'Error: the block dimension must be a positive integer', False, False)                    
                if title == None:
                    return (True, 'Error: the season title cannot be empty', False, False)
                if '-' in title:
                    return (True, 'Error: the season title cannot contains the dash "-" character', False, False)                
                if start_date == None or end_date == None:
                    return (True, 'Error: the date range is not specified', False, False)      
                if AIMSTILE_DAO.add_season(title, False, start_date, end_date, blocks_ncols, blocks_nrows) > 0:
                    AIMSTILE_DAO.set_no_active_season()
                    AIMSTILE_DAO.set_active_season(title)
                return (True, f'added and change the active season to {title}', False, True)    
            else:
                return (False, None, False, False)
            ...
        return create_season_confirmed
