# Copyright 2024 - Andrew Kwok Fai LUI, 
# Robotics and Autonomous Systems Group, REF, RI
# and the Queensland University of Technology

__author__ = 'Andrew Lui'
__copyright__ = 'Copyright 2024'
__license__ = 'GPL'
__version__ = '1.0'
__email__ = 'ak.lui@qut.edu.au'
__status__ = 'Development'

import psutil
# dash modules
import dash
from dash import html, dcc, Input, Output, State, dash_table, ctx
import dash_bootstrap_components as dbc
from dash.exceptions import PreventUpdate
# project modules
from detector.model import STATE, COORDINATOR_STATE, SystemStates, logger, CALLBACK_MANAGER, CallbackTypes
from detector.task_detection import DetectionTaskModel, ProgressStages

class MonitorExecuteProgressBlock():
    def __init__(self, app, prefix):
        self.app = app 
        self.prefix = prefix = prefix + 'mep'
        self.update_store_id = prefix + 'update_store'
        # model variables

        # define widgets 
        self._progress_bar = dbc.Progress([
                dbc.Progress(value=0, id=prefix+'progress_1', color="primary", bar=True),
                dbc.Progress(value=0, id=prefix+'progress_2', color="warning", bar=True),
                dbc.Progress(value=0, id=prefix+'progress_3', color="danger", bar=True),
                dbc.Progress(value=0, id=prefix+'progress_4', color="success", bar=True),
            ], className='mt-2')

        self._progress_label = dbc.Row([
            html.Span('Reconstruct', className='text-primary col-2'),
            html.Span('Locate Tile', className='text-warning col-2'),
            html.Span('Detect Objects', className='text-danger col-6'),
            html.Span('Record', className='text-success col-2'),
        ])
        
        self._abort_button = dbc.Button('Cancel', id=prefix+'cancel_task_button', color='warning', size='me', className='col-12')

        self._panel = dbc.Col([
                html.H4(dbc.Badge('JOB EXECUTION STATUS', className='ms-2 mb-4', color='white', text_color='secondary')),
                dcc.Store(id=self.update_store_id),
                dbc.Row([html.P(id=prefix+'progress_message')], className='col-12 m-3 fs-5'),                
                dbc.Row([
                    dbc.Col([dbc.Label(id=prefix+'progress_label')], className='col-5 text-start mt-2'),
                    dbc.Col([self._progress_bar, self._progress_label], className='col-5'),
                    dbc.Col([html.P(id=prefix+'progress_time')], className='col-1'),
                    dbc.Col([self._abort_button], className='col-1'),
                ], id=prefix+'progress_bar', className='m-2 p-2'),
            ], className='mx-auto text-center')
    
        self.app.callback([Output(prefix+'progress_message', 'children'),
                           Output(prefix+'progress_bar', 'style'),
                           Output(prefix+'progress_label', 'children'),
                           Output(prefix+'progress_time', 'children'),
                           Output(prefix+'progress_1', 'value'),
                           Output(prefix+'progress_2', 'value'),
                           Output(prefix+'progress_3', 'value'),
                           Output(prefix+'progress_4', 'value'),],
                        [Input(self.update_store_id, 'data')])(self._update_content())
        
        self.app.callback([Output(prefix+'cancel_task_button', 'n_clicks', allow_duplicate=True)],
                        [Input(prefix+'cancel_task_button', 'n_clicks')], prevent_initial_call=True)(self._cancel_button_pressed()) 
        
    def get_panel(self):
        return self._panel
    
    def register_trigger(self, trigger_id:str):
        # define callbacks for the datatable data
        self.app.callback([Output(self.update_store_id, 'data'),],
                            [Input(trigger_id, 'data')], prevent_initial_call=True, allow_duplicate=True)(self._update_panel())
        
    def _process_button_pressed(self):
        def process_button_pressed(button):
            return (True, 0,)
        return process_button_pressed
    
    def _update_panel(self):
        def update_panel(data):
            return (data,)
        return update_panel
    
    def _update_content(self):
        def update_content(data):
            progress = (0, 0, 0, 0)
            the_detection_task:DetectionTaskModel = STATE.get_var('the_detection_task')
            progress_message = None
            if the_detection_task is not None:
                progress_bar_style = {'visibility': 'visible'}
                progress_label = f'Finding Corals on the Tile Sample of ID "{the_detection_task.get_tile_sample_id()}"'
                progress_time = f'{int(the_detection_task.get_time_since_start())} sec'
                
                state:SystemStates = STATE.get()
                if state in [SystemStates.DETECT, SystemStates.WAIT_DETECT]:
                    sub_progress_model = the_detection_task.get_progress()
                    current_stage = sub_progress_model.get_current_stage()
                                     
                    if current_stage == ProgressStages.INIT:
                        progress_message = 'Getting ready for the analysis of coral babies'
                    elif current_stage == ProgressStages.RECO:
                        progress_message = 'Putting together images of coral babies into an album'
                        progress = (2.5, 0, 0, 0)
                    elif current_stage == ProgressStages.LOCTILE:
                        progress_message = 'Making sure the coral babies are staying within bounds'
                        progress = (5, 0, 0, 0)
                    elif current_stage == ProgressStages.OBJECT_DETECT:
                        sub_progress = sub_progress_model.get_progress_at_stage(ProgressStages.OBJECT_DETECT)   
                        if sub_progress is not None and sub_progress[1] > 0:
                            progress = (5, 5, int(sub_progress[0] / sub_progress[1] * 80), 0)
                        else:
                            progress = (5, 5, 0, 0)
                        progress_message = f'Counting coral babies in the images ({sub_progress[0]} of {sub_progress[1]})'
                    elif current_stage == ProgressStages.COLLECT_STAT:
                        progress_message = f'Saving data for bittersweet reminiscence when the corals are populating the reef'
                        progress = (5, 5, 80, 2)
                    # elif state == SystemStates.D_UPDATE_HEALTH_INDEX:
                    #     progress_message = f'Doing health checks on the coral babies'
                    #     progress = (5, 5, 80, 5)
                elif state == SystemStates.D_FLAGGED:
                    progress_bar_style = {'visibility': 'hidden'}
                    progress_message = f'The job has been aborted'
                    return (progress_message, progress_bar_style, None, None, 0, 0, 0, 0,)
                else:
                    progress_bar_style = {'visibility': 'hidden'}
                return (progress_message, progress_bar_style, progress_label, progress_time, progress[0], progress[1], progress[2], progress[3],)
            else:
                progress_bar_style = {'visibility': 'hidden'}
                progress_message = 'No job is being executed'
                return (progress_message, progress_bar_style, None, None, 0, 0, 0, 0,)

        return update_content 
    
    def _cancel_button_pressed(self):
        def abort_button_pressed(abort_button):
            if abort_button is None or abort_button > 1:
                raise PreventUpdate
            
            CALLBACK_MANAGER.fire_event(CallbackTypes.PROCESS_TILE_TO_CANCEL)
            return (0, )
        return abort_button_pressed