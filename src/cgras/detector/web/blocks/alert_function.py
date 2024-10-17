# Copyright 2024 - Andrew Kwok Fai LUI, 
# Robotics and Autonomous Systems Group, REF, RI
# and the Queensland University of Technology

__author__ = 'Andrew Lui'
__copyright__ = 'Copyright 2024'
__license__ = 'GPL'
__version__ = '1.0'
__email__ = 'ak.lui@qut.edu.au'
__status__ = 'Development'


# dash modules
import dash
from dash import html, dcc, Input, Output, State, dash_table, ctx
import dash_bootstrap_components as dbc
from dash.exceptions import PreventUpdate

#### PANEL for interacting with the scanning task
class AlertFunction():
    def __init__(self, app, prefix):
        self.app = app
        self._panel = None
        self.alert_message = ''
        self.function_id = prefix + 'trigger_id'
        self.modal_id = prefix + 'modal'
        self.modal_message_id = prefix + 'alert_message'
        self._define_panel()
        
    def get_panel(self):
        return self._panel
    
    def _define_panel(self): 
        self._panel = html.Div([
            dcc.Store(self.function_id),
            dbc.Modal([dbc.ModalHeader(dbc.ModalTitle('Notification')),
                dbc.ModalBody(id=self.modal_message_id),
            ], id=self.modal_id, is_open=False,)])
        
        self.app.callback(    
                [Output(self.modal_message_id, 'children'),
                Output(self.modal_id, 'is_open'),],
                [Input(self.function_id, 'value'),
                 State(self.modal_id, 'is_open')])(self._modal_activated())   
        
    def _modal_activated(self):
        def modal_activated(value, is_open):
            if value == 0:
                return '', False
            if is_open and self.alert_message:
                return self.alert_message, True  
            if self.alert_message is None:
                return '', False
            return self.alert_message, True 
        return modal_activated
        
