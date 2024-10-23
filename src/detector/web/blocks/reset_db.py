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
from detector.model import DETECT_DBFM, AIMSTILE_DBFM

 
class ResetDBBlock():
    def __init__(self, app, prefix):
        self.app = app 
        self.prefix = prefix = prefix + 'rdb_'
        self.reset_success_trigger_id = prefix+'reset_success'
        # --- define widgets 
        reset_table_confirm_dialog = dcc.ConfirmDialog(id=prefix+'confirm_dialog',
            message='All data in the database will be cleared! Are you sure you want to continue?',)     
        
        message_alert = dbc.Alert('The database is cleared', id=prefix+'message_alert', dismissable=True, duration=5000,
                                 is_open=False, className='col-12')

        # database reset panel
        self.reset_db_panel = html.Div([
            dcc.Store(id=self.reset_success_trigger_id),
            reset_table_confirm_dialog,
            html.H4(dbc.Badge('RESET DB TABLES', className='ms-1 me-2', color='white', text_color='secondary')),
            html.P('Press the button to reset the database', className='mt-3'),
            dbc.Button('Drop and Create Tables', id=prefix+'reset_button', color='danger', className=''), 
            html.P('Warning! All the DB tables will be deleted and then created', className='mt-3 text-danger'),
            html.P('(You will be required to confirm thrice)', className='mt-3 text-danger'),
            message_alert,
            ], className='text-center')

        self.app.callback([Output(prefix+'confirm_dialog', 'displayed'),
                           Output(prefix+'confirm_dialog', 'submit_n_clicks')],
                            [Input(prefix+'reset_button', 'n_clicks')], 
            prevent_initial_call=True)(self._reset_button_pressed())
        
        self.app.callback([ Output(prefix+'confirm_dialog', 'displayed', allow_duplicate=True),
                            Output(prefix+'message_alert', 'is_open', allow_duplicate=True),
                           Output(prefix+'message_alert', 'children', allow_duplicate=True),
                           Output(prefix+'confirm_dialog', 'submit_n_clicks', allow_duplicate=True),
                           Output(self.reset_success_trigger_id, 'data',)],
                        [Input(prefix+'confirm_dialog', 'submit_n_clicks')], 
            prevent_initial_call=True)(self._confirm_button_pressed())
        
        self.app.callback([Output(prefix+'confirm_dialog', 'displayed', allow_duplicate=True),],
                        [Input(prefix+'confirm_dialog', 'cancel_n_clicks')], 
            prevent_initial_call=True)(self._cancel_button_pressed())        
        
    def get_panel(self):
        return self.reset_db_panel
    
    def get_success_trigger_id(self):
        return self.reset_success_trigger_id
        
    def _reset_button_pressed(self):
        def reset_button_pressed(reset_button):
            return (True, 0,)
        return reset_button_pressed
    
    def _confirm_button_pressed(self):
        def confirm_button_pressed(submit_n_clicks):
            if submit_n_clicks == 0:
                return (False, False, '', 0, False)
            if submit_n_clicks <= 2:
                return (True, False, '', submit_n_clicks, False)
            else:
                DETECT_DBFM.drop_tables()
                AIMSTILE_DBFM.drop_tables()
                
                error_str = DETECT_DBFM.create_tables()     
                if error_str is None:
                   error_str = AIMSTILE_DBFM.create_tables()    
                if error_str is None:
                    return (False, True, f'Successfully reset the database tables to a blank state', 0, True)
                else:
                    return (False, True, f'Error in creating tables: {error_str}', 0, False)
        return confirm_button_pressed 
      
    def _cancel_button_pressed(self):
        def cancel_button_pressed(cancel_n_clicks):
            return (False,)
        return cancel_button_pressed 