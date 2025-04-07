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
from detector.model import DETECT_DAO, AUTOMATED_TASK_EXECUTION, CALLBACK_MANAGER, CallbackTypes, STATE, SystemStates, logger, TaskStatusNames, PERSISTENT_STORE_DAO, PersistentStoreDAO

class MonitorTaskControlBlock():
    def __init__(self, app, prefix):
        self.app = app 
        self.prefix = prefix = prefix + 'ptc'
        self.update_store_id = prefix + 'update_store'
        # define widgets 
        self._toast = dbc.Toast(id=prefix+'toast', is_open=False, duration=5000, icon='primary', header='Message',
                                style={'position': 'fixed', 'top': '15%', 'left': '50%', 'width': 640, 'transform': 'translate(-50%, -50%)'})
        
        # mode dependent panels       
        self.button_panel = [
            html.P(' ', id=prefix+'button_panel_header', className='mt-2 mx-auto col-8 fw-bold'),
            dbc.Row([
                dbc.Button('Process the next Tile Sample', id={'type': prefix+'button', 'index': 'process_tile'}, color='primary', size='me', className='offset-1 col-4'), 
                dbc.Label('Execute the next tile sample in the queue', className='col-7'),
            ], className='mb-2'),
            dbc.Row([
                dbc.Button('Import New Tile Samples', id={'type': prefix+'button', 'index': 'import_sample'}, color='primary', size='me', className='offset-1 col-4'),  
                dbc.Label('Query for newly acquired tile samples', className='col-7'),
            ], className='mb-2'),
            dbc.Row([
                dbc.Button(id={'type': prefix+'button', 'index': 'automate_switch'}, color='warning', size='me', className='offset-1 col-4'),  
                dbc.Label('Task execution will be initiated by the system', className='col-7'),
            ], className='mb-2'),            
        ]
        # task monitor panel
        self._panel = dbc.Col([
                dcc.Store(id=self.update_store_id),
                dcc.Store(id=prefix+'task_execute_mode_store'),
                html.H4(dbc.Badge('TASK EXECUTION', className='ms-1 me-2', color='white', text_color='secondary')),
                html.P(' ', id=prefix+'mode_message_2', className='mt-2 mx-auto col-12'), 
                html.P(' ', id=prefix+'mode_message_1', className='mt-2 mx-auto col-12'),
                html.Div(self.button_panel, id=prefix+'button_panel', className='mx-auto col-10 border p-2', style={'visibility': 'hidden'}),
                self._toast,
            ], id=prefix+'main_panel', className='mx-auto text-center pb-2')

        # self.app.callback([Output(prefix+'task_execute_mode_store', 'data')],
        #                     [Input(prefix+'mode_dropdown', 'value')], 
        #     prevent_initial_call=True)(self._mode_dropdown_changed())

        self.app.callback([Output(prefix+'button_panel', 'style'),
                           Output(prefix+'button_panel_header', 'children'),
                           Output(prefix+'button_panel_header', 'style'),
                           Output(prefix+'mode_message_1', 'children'),
                           Output({'type': prefix+'button', 'index': 'automate_switch'}, 'children'),
                           Output({'type': prefix+'button', 'index': 'automate_switch'}, 'disabled'),
                           Output({'type': prefix+'button', 'index': 'process_tile'}, 'disabled'),
                           Output({'type': prefix+'button', 'index': 'import_sample'}, 'disabled'),],
            [Input(self.update_store_id, 'data')], prevent_initial_call=True)(self._update_content())
        
        self.app.callback([Output(prefix+'mode_message_2', 'children'),],
                            [Input(self.update_store_id, 'data')], prevent_initial_call=True)(self._update_info_message())
        
        self.app.callback([Output(self.prefix+'toast', 'is_open'),
                            Output(self.prefix+'toast', 'children'),
                            Output(self.prefix+'toast', 'header'),],
                            [Input({'type': prefix+'button', 'index': ALL}, 'n_clicks')], prevent_initial_call=True)(self._button_pressed())     
        
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
            if button_index is None:
                raise PreventUpdate
            elif button_index.endswith('process_tile'):
                CALLBACK_MANAGER.fire_event(CallbackTypes.PROCESS_TILE_CLICKED)
                return (True, 'Attempt to process the next pending tile sample if it exists', 'Process Tile')
            elif button_index.endswith('import_sample'):
                CALLBACK_MANAGER.fire_event(CallbackTypes.IMPORT_SAMPLE_CLICKED)
                return (True, 'Attempt to import new tile samples found in the image acquisition system', 'Import New Tile Samples')            
            elif button_index.endswith('automate_switch'):
                new_mode = not AUTOMATED_TASK_EXECUTION.value
                CALLBACK_MANAGER.fire_event(CallbackTypes.TASK_EXECUTE_MODE_CHANGED, new_mode)
                return (True, f'Task execution mode is changed to {"Automated" if AUTOMATED_TASK_EXECUTION.value else "Manual"}', 'Task Execution Mode Change')        
            else:               
                raise PreventUpdate
        return button_pressed
    
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
                    'Task Execution Mode: SUSPENDED',
                    {'color': 'red'},
                    'System suspended due to the execution of an image acquisition program',
                    '',
                    True, True, True,
                )
            elif is_menu_appear and not AUTOMATED_TASK_EXECUTION.value:
                return (
                    {'visibility': 'visible'},
                    'Task Execution Mode: MANUAL',
                    {'color': 'blue'},
                    'Execute a task manually by clicking on a button below',
                    'Switch to Automated Execution',
                    False, False, not enable_import_new_samples,
                )
            elif not AUTOMATED_TASK_EXECUTION.value:
                return (
                    {'visibility': 'visible'},
                    'Task Execution Mode: MANUAL',
                    {'color': 'blue'},
                    'The buttons are enabled after the current task is completed or aborted',
                    'Switch to Automated Execution',
                    False, True, True,
                )
            else:
                return (
                    {'visibility': 'visible'},
                    'Task Execution Mode: AUTOMATED',
                    {'color': 'purple'},
                    'Automated execution of tile sample processing and new tile sample import',
                    'Switch to Manual Execution',
                    False, True, True,
                )
        return update_content
    
    def _update_info_message(self):
        def update_info_message(timer):    
            if timer is not None and timer % 10 == 1:
                count = DETECT_DAO.count_tile_samples(TaskStatusNames.PENDING.value)
                if count == 0:
                    message = 'No tile sample pending analysis'
                else:
                    message = f'Number of tile samples pending analysis is {count}'
                return (message,)
            else:
                raise PreventUpdate
        return update_info_message
