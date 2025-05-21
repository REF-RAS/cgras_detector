# Copyright 2024 - Andrew Kwok Fai LUI, 
# Robotics and Autonomous Systems Group, REF, RI
# and the Queensland University of Technology

__author__ = 'Andrew Lui'
__copyright__ = 'Copyright 2024'
__license__ = 'GPL'
__version__ = '1.0'
__email__ = 'ak.lui@qut.edu.au'
__status__ = 'Development'

import time
# dash modules
import dash
from dash import html, dcc, Input, Output, State, dash_table, ctx, ALL
import dash_bootstrap_components as dbc
from dash.exceptions import PreventUpdate
from detector.model import DETECT_DAO, AUTOMATED_TASK_EXECUTION, CALLBACK_MANAGER, CallbackTypes, STATE, SystemStates, logger, SampleStatusNames, PERSISTENT_STORE_DAO, PersistentStoreDAO

class MonitorTaskControlBlock():
    def __init__(self, app, prefix):
        self.app = app 
        self.prefix = prefix = prefix + 'ptc'
        self.update_store_id = prefix + 'update_store'
        # define widgets 
        self._toast = dbc.Toast(id=prefix+'toast', is_open=False, duration=5000, icon='primary', header='Message',
                                style={'position': 'fixed', 'top': '30%', 'left': '30%', 'width': 640, 'transform': 'translate(-50%, -50%)'})
        
        self.button_panel = html.Div([
                        dbc.Row([    
                            dbc.Col(dbc.Button('Process the next Tile Sample', id={'type': prefix+'button', 'index': 'process_tile'}, 
                                            color='primary', className='w-100'), className='col-4'),
                            dbc.Col(f'Execute the next tile sample in the queue', className='col-8')
                        ], className='text-start mb-3', style={'height': '40px'}),
                        
                        dbc.Row([    
                            dbc.Col(dbc.Button('Import a New Tile Sample', id={'type': prefix+'button', 'index': 'import_sample'}, 
                                            color='primary', className='w-100'), className='col-4'),
                            dbc.Col(f'Query for a new tile sample', className='col-8')
                        ], className='text-start mb-3', style={'height': '40px'}),                        
                         
        ], id=prefix+'button_panel', className='mx-auto col-10 p-2', style={'visibility': 'hidden'})
        
        # task monitor panel
        self._panel = dbc.Col([
                dcc.Store(id=self.update_store_id),
                dcc.Store(id=prefix+'task_execute_mode_store'),
                html.H4(dbc.Badge('JOB CONTROL', className='ms-2 mb-4', color='white', text_color='secondary')),
                html.Div([
                   dbc.Button(' ', id=prefix+'mode_button', className='me-4', color='light', style={'width': '320px'}),
                ], className='mb-4 mx-auto col-12'), 
                html.P(' ', id=prefix+'mode_message', className='mt-2 mx-auto col-12'),
                self.button_panel,
                self._toast,
            ], id=prefix+'main_panel', className='mx-auto text-center pb-2')

        # self.app.callback([Output(prefix+'task_execute_mode_store', 'data')],
        #                     [Input(prefix+'mode_dropdown', 'value')], 
        #     prevent_initial_call=True)(self._mode_dropdown_changed())

        self.app.callback([Output(prefix+'button_panel', 'style'),
                           Output(prefix+'mode_message', 'children'),
                           Output(prefix+'mode_button', 'children'),
                           Output(prefix+'mode_button', 'color'),
                           Output(prefix+'mode_button', 'disabled'),
                           Output({'type': prefix+'button', 'index': 'process_tile'}, 'disabled'),
                           Output({'type': prefix+'button', 'index': 'import_sample'}, 'disabled'),],
            [Input(self.update_store_id, 'data')], prevent_initial_call=True)(self._update_content())
        
        self.app.callback([Output(prefix+'mode_message_2', 'children'),],
                            [Input(self.update_store_id, 'data')], prevent_initial_call=True)(self._update_info_message())
        
        self.app.callback([Output(self.prefix+'toast', 'is_open'),
                            Output(self.prefix+'toast', 'children'),
                            Output(self.prefix+'toast', 'header'),
                            Output({'type': prefix+'button', 'index': ALL}, 'n_clicks')],
                            [Input({'type': prefix+'button', 'index': ALL}, 'n_clicks')], prevent_initial_call=True)(self._button_pressed())    
        
        self.app.callback([Output(prefix+'mode_button', 'n_clicks')],
                            [Input(prefix+'mode_button', 'n_clicks')], prevent_initial_call=True)(self._mode_button_pressed())           
        
    def get_panel(self):
        return self._panel
    
    def register_trigger(self, trigger_id:str):
        # define callbacks for the datatable data
        self.app.callback([Output(self.update_store_id, 'data'),],
            [Input(trigger_id, 'data')], prevent_initial_call=True, allow_duplicate=True)(self._update_panel())
        
    def _button_pressed(self):
        def button_pressed(*args):
            button_id = ctx.triggered_id if ctx.triggered_id is not None else {}
            button_index = button_id.get('index', None)
            return_n_click_list = args[0]
            default_n_click_list = (None, None,)
            if button_index is None:
                raise PreventUpdate
            elif button_index.endswith('process_tile'):
                if return_n_click_list[0] != None and return_n_click_list[0] > 1:
                    time.sleep(1.0)
                    return (dash.no_update, dash.no_update, dash.no_update, default_n_click_list)
                CALLBACK_MANAGER.fire_event(CallbackTypes.PROCESS_TILE_CLICKED)
                return (True, 'Attempt to process the next pending tile sample if it exists', 'Process Tile', default_n_click_list)
            elif button_index.endswith('import_sample'):
                if return_n_click_list[1] != None and return_n_click_list[1] > 1:
                    time.sleep(1.0)
                    return (dash.no_update, dash.no_update, dash.no_update, default_n_click_list)
                CALLBACK_MANAGER.fire_event(CallbackTypes.IMPORT_SAMPLE_CLICKED)
                return_n_click_list[1] = None
                return (True, 'Attempt to import new tile samples found in the image acquisition system', 'Import New Tile Samples', default_n_click_list)            
            else:               
                raise PreventUpdate
        return button_pressed

    def _mode_button_pressed(self):
        def mode_button_pressed(n_clicks):
            if n_clicks != None and n_clicks > 1:
                time.sleep(1.0)
                return (0, )
            new_mode = not AUTOMATED_TASK_EXECUTION.value
            CALLBACK_MANAGER.fire_event(CallbackTypes.TASK_EXECUTE_MODE_CHANGED, new_mode)
            return (0, )        
        return mode_button_pressed

    def _update_panel(self):
        def update_panel(timer):
            if not timer:
                raise PreventUpdate
            return (timer, )
        return update_panel
        
    def _update_content(self):
        def update_content(timer):
            current_state = STATE.get_state()
            is_menu_appear = current_state in [SystemStates.CLICK_START]
            enable_import_new_samples = PERSISTENT_STORE_DAO.get_config_value(PersistentStoreDAO.TILE_IMPORT_ENABLED, default=False)
            if current_state in [SystemStates.SUSPENDED]:
                return (
                    {'visibility': 'visible'},
                    'System suspended due to the execution of an image acquisition program.',
                    'SUSPENDED Mode',
                    'dark',
                    True, True, True,
                )
            elif is_menu_appear and not AUTOMATED_TASK_EXECUTION.value:
                return (
                    {'visibility': 'visible'},
                    'Click a button below to execute a job manually. Click the above button to toggle execution mode.',
                    'MANUAL Execution Mode',
                    'success',
                    False, False, not enable_import_new_samples,
                )
            elif not AUTOMATED_TASK_EXECUTION.value:
                return (
                    {'visibility': 'visible'},
                    'The buttons are enabled after the current task is completed or aborted. Click the above button to toggle execution mode.',
                    'MANUAL Execution Mode',
                    'success',
                    False, True, True,
                )
            else:
                return (
                    {'visibility': 'visible'},
                    'Automated job execution enabled. Click the above button to toggle execution mode.',
                    'AUTOMATED Execution Mode',
                    'warning',
                    False, True, True,
                )
        return update_content
    
    def _update_info_message(self):
        def update_info_message(timer):    
            if timer is not None and timer % 10 == 1:
                count = DETECT_DAO.count_tile_samples(SampleStatusNames.QUEUED.value)
                if count == 0:
                    message = 'No tile sample pending analysis'
                else:
                    message = f'Number of tile samples pending analysis is {count}'
                return (message,)
            else:
                raise PreventUpdate
        return update_info_message
