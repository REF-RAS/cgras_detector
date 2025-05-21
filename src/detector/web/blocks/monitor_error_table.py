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
from dash.dash_table.Format import Format, Padding
from dash.exceptions import PreventUpdate
from detector.model import DETECT_DAO, CONFIG, SystemConfigNames
from detector.models import DetectorExceptionCodes
from cgras_datatools.logging_tools import logger

class MonitorErrorTableBlock():
    def __init__(self, app, prefix):
        self.app = app 
        self.prefix = prefix = prefix + 'metb_'
        # model variable
        
        # define widgets 
        self._columns = [
                        {'name': 'Issues', 'id': 'remarks', 'type': 'text', 'editable': False},                                               
                    ]
              
        self._style_data_conditional = [
                {'if': {
                    'filter_query': '{level} = 0',
                    'column_id': 'remarks'
                }, 'backgroundColor': '#ffffff', 'color': 'rgb(128, 0, 0)'},
                {'if': {
                    'filter_query': '{level} > 0',
                    'column_id': 'remarks'
                }, 'backgroundColor': '#ffffff', 'color': 'rgb(64, 0, 0)'},  
                {'if': {
                    'filter_query': '{remarks} contains "file"',
                    'column_id': 'remarks'
                }, 'backgroundColor': '#ffffff', 'color': 'rgb(96, 0, 0)'},                                       
                ]
        
        self._datatable = dash_table.DataTable(columns=self._columns,
                                               id=prefix+'datatable', style_header={}, fill_width=True, 
                                               style_data_conditional=self._style_data_conditional,
                                               style_cell={'textAlign': 'left', 'whiteSpace': 'normal', 'height': 'auto', 'fontSize': 14},
                                               cell_selectable=False, row_selectable='single')
                
        self.the_panel = html.Div([
                html.H4(dbc.Badge('PROCESSING AND SYSTEM ISSUES', className='mx-auto col-10', color='white', text_color='secondary')), 
                # html.P('Click on the circle to dismiss an issue', style={'fontSize': 12}),
                dbc.Row([ self._datatable], className='text-start p-2'),
                dcc.Store(id=prefix+'row_remove_store'),            
                ], className='mx-auto text-center')
        
        self.app.callback([Output(prefix+'datatable', 'data', allow_duplicate=True),
                          Output(prefix+'datatable', 'selected_rows', allow_duplicate=True)],
                            [Input(prefix+'datatable', 'selected_rows'),
                             State(prefix+'datatable', 'data')], prevent_initial_call=True)(self._selected_rows())  
        
    def get_panel(self):
        return self.the_panel
        
    def register_trigger(self, trigger_id:str):
        self.app.callback(Output(self.prefix+'datatable', 'data'),
            [Input(trigger_id, 'data')], prevent_initial_call=False)(self._update_table())  
               
    def _update_model(self):   
        def update_remarks(row):
            error_code = row['id']
            error_str = DetectorExceptionCodes(error_code).name
            error_obj = '' if row['object'] is None else row['object']
            return f'{row["update_time"]} {error_str} ({error_obj}): {row["remarks"]}'
        
        model = DETECT_DAO.list_error_flags()
        if not model.empty:
            model['remarks'] = model.apply(update_remarks, axis=1, result_type='reduce')
        return model
          
    # callback for the table
    def _update_table(self):
        def update_tile_stat_table(store):
            model = self._update_model()
            if model is None:
                raise PreventUpdate
            return model.to_dict('records')
        return update_tile_stat_table  
    
    def _selected_rows(self):
        def style_selected_rows(selected_rows, model):
            if selected_rows is None:
                return dash.no_update
            row_index = selected_rows[0]
            id = model[row_index]['id']
            obj = model[row_index]['object']
            DETECT_DAO.unset_error_flag(id, obj)
            model.pop(row_index)
            return (model, [],)
        return style_selected_rows