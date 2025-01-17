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
from dash import html, dcc, Input, Output, State, dash_table, ctx, ALL
import dash_bootstrap_components as dbc
from dash.exceptions import PreventUpdate
from detector.model import DETECT_DAO

class ResetStatDBTableBlock():
    def __init__(self, app, prefix):
        self.app = app 
        self.prefix = prefix = prefix + 'rsdbt_'
        self.button_pressed_store_id = prefix+'button_id_store'

        # define a toast for feedback  
        self._toast = dbc.Toast(id=prefix+'toast', is_open=False, duration=5000, icon='danger', header='Message',
                                style={'position': 'fixed', 'top': '15%', 'left': '50%', 'width': 640, 'transform': 'translate(-50%, -50%)'})
        # define the modal for confirmation of user actions
        self._user_confirm_modal = dbc.Modal([
                    dbc.ModalHeader(dbc.ModalTitle('Clear Statistics', id=prefix+'confirm_modal_title')),
                    html.Div([html.P('The selected statistics will be clear. Are you sure?', id=prefix+'confirm_modal_message'),
                                dbc.Button('Confirm', id={'type': prefix+'action', 'index': 'confirm'},), 
                                dbc.Button('Cancel', id={'type': prefix+'action', 'index': 'cancel'}, color='secondary')
                            ]
                        , className='d-grid gap-2 col-8 mx-auto', style={'padding': '6px'})
                        ], id=prefix+'confirm_modal', is_open=False)

        # database reset panel
        self.reset_db_panel = html.Div([
                dcc.Store(id=self.button_pressed_store_id),
                html.H4(dbc.Badge('CLEAR STATISTICS', className='ms-1 me-2', color='white', text_color='secondary')),
                html.P('Click on the button to clear the statistics', className='mt-3'),
                dbc.Button('Clear Task Records', id=prefix+'clear_task_records_button', color='warning'), 
                html.P('Warning! The selected statistics will be deleted permanantly', className='mt-3 text-danger'),
                self._toast,
                self._user_confirm_modal,
            ], className='text-center')

        self.app.callback([Output(prefix+'confirm_modal', 'is_open', allow_duplicate=True),
                           Output(self.button_pressed_store_id, 'data',)],
                            [Input(prefix+'clear_task_records_button', 'n_clicks')], 
            prevent_initial_call=True)(self._button_pressed())
        
        self.app.callback([ Output(prefix+'confirm_modal', 'is_open', allow_duplicate=True),
                            Output(prefix+'toast', 'is_open', allow_duplicate=True),
                           Output(prefix+'toast', 'children', allow_duplicate=True)],
                        [State(self.button_pressed_store_id, 'data'),
                         Input({'type': prefix+'action', 'index': ALL}, 'n_clicks')], prevent_initial_call=True)(self._cb_confirm_modal_pressed())     
        
    def get_panel(self):
        return self.reset_db_panel
        
    def _button_pressed(self):
        def button_pressed(button_id):
            button_id = ctx.triggered_id if ctx.triggered_id is not None else 'No clicks yet'
            if button_id.endswith('clear_task_records_button'):
                return (True, button_id)
            return (False, None)
        return button_pressed
    
    def _cb_confirm_modal_pressed(self):
        def cb_confirm_modal_pressed(button_id, *args):
            button_id = ctx.triggered_id if ctx.triggered_id is not None else {}
            button_index = button_id.get('index', None)
            if button_index.endswith('confirm'):
                # TODO: uncomment it later
                DETECT_DAO.clear_all_task_records() 
                message = 'The task records statistics have been cleared'
                return (False, True, message,)
            else:
                return (False, False, None,)
        return cb_confirm_modal_pressed 
      
