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
from cgras.detector.model import APP_FILE_MANAGER

 
class DiskspaceBlock():
    def __init__(self, app, prefix):
        self.app = app 
        self.prefix = prefix = prefix + 'dsb_'
        # --- define widgets 
        # diskspace display panel
        _diskspace_datatable = dash_table.DataTable(id=prefix+'diskspace_table')
        self.diskspace_panel = html.Div([
            html.H4(dbc.Badge('DISK SPACE', className='ms-1 me-2', color='white', text_color='secondary')),
            dbc.Row([_diskspace_datatable], className='mx-auto'),
            ], className='mx-auto text-center')
        
    def get_panel(self):
        return self.diskspace_panel
        
    def register_trigger(self, trigger_id:str):
        # callback for the diskspace panel display
        self.app.callback(Output(self.prefix+'diskspace_table', 'data'),
            [Input(trigger_id, 'data')], prevent_initial_call=False)(self._update_diskspace_table())   
        
    # generate the model for the diskspace table display
    def _define_diskspace_model(self):
        total, used, free = shutil.disk_usage(APP_FILE_MANAGER.cgras_data_folder)
        model = pd.DataFrame(columns=('Parameters', 'Values'))
        model.loc[1] = ['Total', f'{total // (2**30)} GB']
        model.loc[2] = ['Used', f'{used // (2**30)} GB']
        model.loc[3] = ['Free', f'{free // (2**30)} GB']        
        return model

    # callback for the diskspace table
    def _update_diskspace_table(self):
        def update_diskspace_table(data):
            model = self._define_diskspace_model()
            if model is None:
                raise PreventUpdate
            return model.to_dict('records')
        return update_diskspace_table 