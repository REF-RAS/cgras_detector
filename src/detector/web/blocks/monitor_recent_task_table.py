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
from detector.model import DETECT_DAO, TaskStatusNames, TaskTypes

class MonitorRecentTaskTableBlock():
    def __init__(self, app, prefix, max_records=100, page_size=10):
        self.app = app
        self.prefix = prefix = prefix + 'mlttb_'
        self.max_records = max_records
        self.page_size = page_size
        # --- define widgets
        self._columns = [
                        #{'name': 'Task Type', 'id': 'task_type', 'type': 'text', 'editable': False},
                         {'name': 'Tile Sample ID', 'id': 'task_object', 'type': 'text', 'editable': False},
                         {'name': 'Start Time', 'id': 'start_time', 'type': 'datetime', 'editable': False},
                         {'name': 'Duration (s)', 'id': 'used_time', 'type': 'text', 'editable': False},
                         {'name': 'Status', 'id': 'status', 'type': 'text', 'editable': False},  
                         {'name': 'Remarks', 'id': 'remarks', 'type': 'text', 'editable': False},                                                 
                         ]

        style_data_conditional = [{'if': {
                    'filter_query': '{status} contains "FAIL"',
                    'column_id': 'status'
                }, 'backgroundColor': '#ffffff', 'color': 'rgb(255, 0, 0)'} ]
       
        _the_datatable = dash_table.DataTable(id=prefix+'datatable', columns=self._columns, style_cell={'fontSize': 14}, cell_selectable=False, row_selectable=False,
                                              page_current=0, page_size=self.page_size, style_data_conditional=style_data_conditional)
        
        self._the_panel = dbc.Col([
                html.H4(dbc.Badge('STATUS OF RECENT JOBS', className='ms-1 me-2', color='white', text_color='secondary')),
                dbc.Row([_the_datatable], className='mx-auto col-12'),
            ], className='mx-auto text-center')
        
    def get_panel(self):
        return self._the_panel
        
    def register_trigger(self, trigger_id:str):
        self.app.callback(Output(self.prefix+'datatable', 'data'),
            [Input(trigger_id, 'data')], prevent_initial_call=False)(self._update_table())  
        
    def _update_model(self):   
        model = DETECT_DAO.list_recent_task_records(self.max_records)
        return model
    
    def _refine_model(self, model):
        model['task_type'] = model['task_type'].apply(lambda x: TaskTypes(x).name) 
        model['status'] = model['status'].apply(lambda x: TaskStatusNames(x).name) 
        return model
        
    # callback for the table
    def _update_table(self):
        def update_tile_stat_table(store):
            model = self._update_model()
            model = self._refine_model(model)
            if model is None:
                raise PreventUpdate
            return model.to_dict('records')
        return update_tile_stat_table  
    