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
from detector.model import DETECT_DAO

class ResetStatDBTableBlock():
    def __init__(self, app, prefix):
        self.app = app 
        self.prefix = prefix = prefix + 'rsdbt_'
        self.button_pressed_store_id = prefix+'button_id_store'
        # --- define widgets 
        reset_table_confirm_dialog = dcc.ConfirmDialog(id=prefix+'confirm_dialog',
            message='The selected statistics will be clear. Are you sure?', )     
        
        message_alert = dbc.Alert('The statistics is cleared', id=prefix+'message_alert', dismissable=True, duration=5000,
                                 is_open=False, className='col-12')

        # database reset panel
        self.reset_db_panel = html.Div([
                dcc.Store(id=self.button_pressed_store_id),
                reset_table_confirm_dialog,
                html.H4(dbc.Badge('CLEAR STATISTICS', className='ms-1 me-2', color='white', text_color='secondary')),
                html.P('Click on the button to clear the statistics', className='mt-3'),
                dbc.Button('Clear Task Records', id=prefix+'clear_task_records_button', color='warning'), 
                html.P('Warning! The selected statistics will be deleted permanantly', className='mt-3 text-danger'),
                message_alert,
            ], className='text-center')

        self.app.callback([Output(prefix+'confirm_dialog', 'displayed'),
                           Output(self.button_pressed_store_id, 'data',)],
                            [Input(prefix+'clear_task_records_button', 'n_clicks')], 
            prevent_initial_call=True)(self._button_pressed())
        
        self.app.callback([ Output(prefix+'confirm_dialog', 'displayed', allow_duplicate=True),
                            Output(prefix+'message_alert', 'is_open', allow_duplicate=True),
                           Output(prefix+'message_alert', 'children', allow_duplicate=True)],
                        [Input(prefix+'confirm_dialog', 'submit_n_clicks'),
                         State(self.button_pressed_store_id, 'data')], 
            prevent_initial_call=True)(self._dialog_confirmed())
        
        self.app.callback([Output(prefix+'confirm_dialog', 'displayed', allow_duplicate=True),],
                        [Input(prefix+'confirm_dialog', 'cancel_n_clicks')], 
            prevent_initial_call=True)(self._dialog_cancelled())        
        
    def get_panel(self):
        return self.reset_db_panel
        
    def _button_pressed(self):
        def button_pressed(button_id):
            button_id = ctx.triggered_id if not None else 'No clicks yet'
            # logger.warning(f'table button: {row_index_list} {button_id}')
            if button_id.endswith('clear_task_records_button'):
                return (True, button_id)
            return (False, None)
        return button_pressed
    
    def _dialog_confirmed(self):
        def dialog_confirmed(submit_n_clicks, button_id):
            if submit_n_clicks is None:
                return (False, False, None,)
            if button_id.endswith('clear_task_records_button'):
                DETECT_DAO.clear_all_task_records() 
                message = 'The task records statistics have been cleared'
                return (False, True, message)

        return dialog_confirmed 
      
    def _dialog_cancelled(self):
        def dialog_cancelled(cancel_n_clicks):
            return (False,)
        return dialog_cancelled 