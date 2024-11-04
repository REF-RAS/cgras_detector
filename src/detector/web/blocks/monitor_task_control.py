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
import dash_daq as daq
import dash_bootstrap_components as dbc
from dash.exceptions import PreventUpdate
from detector.model import DETECT_DAO, PERSISTENT_STORE_DAO, CALLBACK_MANAGER, CallbackTypes, STATE, SystemStates, logger, StatusNames

class MonitorTaskControlBlock():
    def __init__(self, app, prefix):
        self.app = app 
        self.prefix = prefix = prefix + 'ptc'
        self.update_store_id = prefix + 'update_store'
        # model variables
        current_task_execute_mode = PERSISTENT_STORE_DAO.get_task_execute_mode(default=PERSISTENT_STORE_DAO.AUTO_EXECUTE_OFF)
        # define widgets 
        message_alert = dbc.Alert( id=prefix+'message_alert', dismissable=True, duration=5000, is_open=False, className='col-12', color='light')
        self.task_execute_mode_options = [
                {'label': 'OFF', 'value': PERSISTENT_STORE_DAO.AUTO_EXECUTE_OFF},
                {'label': 'ON', 'value': PERSISTENT_STORE_DAO.AUTO_EXECUTE_ON},]
        
        task_execute_mode_select = dcc.Dropdown(self.task_execute_mode_options, value=current_task_execute_mode, id=prefix+'mode_dropdown', 
                                                className='mx-auto col-8 fs-4', searchable=False, clearable=False)

        # database reset panel
        self._panel = dbc.Col([
                dcc.Store(id=self.update_store_id),
                dcc.Store(id=prefix+'task_execute_mode_store'),
                html.H4(dbc.Badge('AUTOMATED TASK EXECUTION', className='ms-1 me-2', color='white', text_color='secondary')),
                html.Div([task_execute_mode_select], className='mt-3 mx-auto'),
                html.P(id=prefix+'mode_message', className='mt-2 mx-auto col-12'),
                html.Div([
                    html.P('List of Executable Tasks', className='mt-2 mx-auto col-8 fw-bold'),
                    dbc.Row([
                        dbc.Button('Process a Tile Sample', id=prefix+'process_tile_button', color='secondary', size='sm', className='offset-1 col-4'), 
                        dbc.Label('Querying any pending tile sample ...', id=prefix+'process_tile_info', className='col-7'),
                    ], className='mb-2'),
                    dbc.Row([
                        dbc.Button('Update Health Indices', id=prefix+'update_health_button', color='secondary', size='sm', className='offset-1 col-4'), 
                        dbc.Label(id=prefix+'update_health_info', className='col-7'),
                    ], className='mb-2'),
                    dbc.Row([
                        dbc.Button('Import New Tile Samples', id=prefix+'import_tiles_button', color='secondary', size='sm', className='offset-1 col-4'),  
                        dbc.Label(id=prefix+'import_tiles_info', className='col-7'),
                    ], className='mb-2'),

                ], id=prefix+'manual_task_menu', className='mx-auto col-10 border p-2'),
                message_alert,
            ], id=prefix+'main_panel', className='mx-auto text-center pb-2')

        self.app.callback([Output(prefix+'task_execute_mode_store', 'data')],
                            [Input(prefix+'mode_dropdown', 'value')], 
            prevent_initial_call=True)(self._mode_dropdown_changed())

        self.app.callback([Output(prefix+'mode_dropdown', 'value')],
                            [Input(prefix+'main_panel', 'children')], 
            prevent_initial_call=True)(self._main_panel_loaded())

        self.app.callback([Output(prefix+'manual_task_menu', 'style'),
                           Output(prefix+'mode_message', 'children')],
            [Input(self.update_store_id, 'data')],)(self._update_content())
        
        self.app.callback([Output(prefix+'process_tile_info', 'children'),
                           Output(prefix+'update_health_info', 'children'),
                           Output(prefix+'import_tiles_info', 'children'),],
            [Input(self.update_store_id, 'data')],)(self._update_info_message())
        
        self.app.callback([Output(prefix+'message_alert', 'is_open'),
                           Output(prefix+'message_alert', 'children')],
                            [Input(prefix+'process_tile_button', 'n_clicks'),
                             Input(prefix+'update_health_button', 'n_clicks'),
                             Input(prefix+'import_tiles_button', 'n_clicks'),
                             ], 
            prevent_initial_call=True)(self._manual_button_pressed())     
        
    def get_panel(self):
        return self._panel
    
    def register_trigger(self, trigger_id:str):
        # define callbacks for the datatable data
        self.app.callback([Output(self.update_store_id, 'data'),],
            [Input(trigger_id, 'data')], prevent_initial_call=True, allow_duplicate=True)(self._update_panel())
        
    def _manual_button_pressed(self):
        def process_button_pressed(process_tile_button, update_health_button, import_tiles_button):
            button_id = ctx.triggered_id if not None else 'No clicks yet'
            if button_id.endswith('process_tile_button'):
                CALLBACK_MANAGER.fire_event(CallbackTypes.PROCESS_TILE_CLICKED)
                return (True, 'Attempt to process the next pending tile sample if it exists')
            return (False, None,)
        return process_button_pressed
    
    def _update_panel(self):
        def update_panel(timer):
            if not timer:
                raise PreventUpdate
            return (timer, )
        return update_panel
    
    def _main_panel_loaded(self):
        def main_panel_loaded(children):
            task_execute_mode = PERSISTENT_STORE_DAO.get_task_execute_mode(default=PERSISTENT_STORE_DAO.AUTO_EXECUTE_OFF)
            return (task_execute_mode, )
        return main_panel_loaded
    
    def _update_content(self):
        def update_content(timer):
            task_execute_mode = PERSISTENT_STORE_DAO.get_task_execute_mode(default=PERSISTENT_STORE_DAO.AUTO_EXECUTE_OFF)
            is_menu_appear = STATE.get_state() in [SystemStates.CLICK_START]
            if is_menu_appear and task_execute_mode == PERSISTENT_STORE_DAO.AUTO_EXECUTE_OFF:
                style = {'visibility': 'visible'}
                message = 'Execute a task manually by clicking on a button below'
            elif task_execute_mode == 0:
                style = {'visibility': 'hidden'} 
                message = 'A task menu will appear after the current task is completed or aborted'
            else:
                style = {'visibility': 'hidden'} 
                message = 'Automated execution of tile sample processing and new tile sample import'
            return (style, message,)
        return update_content
    
    def _update_info_message(self):
        def update_info_message(timer):    
            if timer is not None and timer % 10 == 1:
                count = DETECT_DAO.count_tile_samples(StatusNames.PENDING.value)
                if count == 0:
                    message = 'No tile sample pending analysis'
                else:
                    message = f'Number of tile sample pending analysis is {count}'
                return (message, None, None,)
            else:
                raise PreventUpdate
        return update_info_message
    
    def _mode_dropdown_changed(self):
        def mode_dropdown_changed(mode):
            PERSISTENT_STORE_DAO.update_task_execute_mode(mode)
            CALLBACK_MANAGER.fire_event(CallbackTypes.TASK_EXECUTE_MODE_CHANGED, mode)
            return (mode, )
        return mode_dropdown_changed
