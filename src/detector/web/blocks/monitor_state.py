# Copyright 2024 - Andrew Kwok Fai LUI, 
# Robotics and Autonomous Systems Group, REF, RI
# and the Queensland University of Technology

__author__ = 'Andrew Lui'
__copyright__ = 'Copyright 2024'
__license__ = 'GPL'
__version__ = '1.0'
__email__ = 'ak.lui@qut.edu.au'
__status__ = 'Development'

import psutil, random
# dash modules
import dash
from dash import html, dcc, Input, Output, State, dash_table, ctx
import dash_daq as daq
import dash_bootstrap_components as dbc
from dash.exceptions import PreventUpdate
# project modules
from detector.model import STATE, COORDINATOR_STATE, SystemStates

class MonitorStateBlock():
    def __init__(self, app, prefix):
        self.app = app 
        self.prefix = prefix = prefix + 'msb'
        self.update_store_id = prefix + 'update_store'
        # model variables
        self.banner_message = ''
        self.current_detect_message = None
        # define widgets 
        self._panel = dbc.Col([
                html.H4(dbc.Badge('SYSTEM MONITOR', className='ms-2 mb-4', color='white', text_color='secondary')),
                dcc.Store(id=self.update_store_id),
                dbc.Row([html.Div('Counting and Visualization State:', className='fs-6 col-6 text-end'),
                         dbc.Badge(id=prefix+'vis_state', className='fs-6 col-6 text-start', color='white', text_color='primary')
                    ], className='col-12 mb-2'),
                dbc.Row([html.Div('Image Acquisition State:', className='fs-6 col-6 text-end'),
                         dbc.Badge(id=prefix+'capturer_state', className='fs-6 col-6 text-start', color='white', text_color='primary')
                    ], className='col-12 mb-2'),                
                dbc.Row([html.Div('Number of CPU(s):', className='fs-6 col-6 text-end'),
                         dbc.Badge(f'{psutil.cpu_count()}', className='fs-6 col-6 text-start', color='white', text_color='secondary')
                    ], className='col-12 mb-2'),        
                dbc.Row([html.Div('CPU Percent:', className='fs-6 col-6 text-end'),
                         dbc.Progress(id=prefix+'cpu_percent', className='col-6 mt-1')
                    ], className='col-12 mb-2'),
                dbc.Row([html.Div('RAM Percent:', className='fs-6 col-6 text-end'),
                         dbc.Progress(id=prefix+'ram_percent', className='col-6 mt-1')
                    ], className='col-12 mb-2'),                
                                      
                html.P(' ', id=prefix+'state_message', className='mt-3 text-center'),
            ], className='mx-auto text-center')
    
        self.app.callback([Output(prefix+'vis_state', 'children'),
                           Output(prefix+'capturer_state', 'children'),
                           Output(prefix+'cpu_percent', 'value'),
                           Output(prefix+'cpu_percent', 'label'),
                           Output(prefix+'ram_percent', 'value'),
                           Output(prefix+'ram_percent', 'label'),                           
                            Output(self.prefix+'state_message', 'children')],
                        [Input(self.update_store_id, 'data')])(self._update_content())
        
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
    
    # the callback for table update
    def _update_content(self):
        def update_content(data):
            # obtain the states of the two platforms
            state:SystemStates = STATE.get()
            previous_state:SystemStates = STATE.get_previous_state()
            capturer_state = COORDINATOR_STATE.get()
            # query cpu percent and memory percent
            cpu_percent = psutil.cpu_percent()
            mem_percent = psutil.virtual_memory().percent        
            if state in [SystemStates.READY, SystemStates.AUTO_START, SystemStates.CLICK_START]:
                self.current_detect_message = None
                if previous_state not in [SystemStates.READY, SystemStates.AUTO_START, SystemStates.CLICK_START] or random.random() < 0.2:
                    self.banner_message = [
                        'I am consuming electricity but there is no coral babies to look after. Can you feel my guilt?',
                        'I am wasting my talent here. Got nothing to do. I should be nursing coral babies. ',
                        'I turn into a couch potato. Is it my destiny?'
                    ][random.randrange(0, 3)]
            elif state in [SystemStates.POLL_DETECT, SystemStates.POLL_SAMPLE]:
                if previous_state not in [SystemStates.POLL_DETECT, SystemStates.POLL_SAMPLE] or random.random() < 0.2:
                    self.banner_message = [
                        'I just asked my supervisor for more coral larvae but got nothing. I am feeling insecure.',
                        'No new coral again! Should I look elsewhere for coral babies?',
                        'Can we make corals more productive? '
                    ][random.randrange(0, 3)]
            elif state in [SystemStates.SUSPENDED]:
                self.current_detect_message = None
                self.banner_message = 'I am on leave now as the system is suspended. Ping me if you want but I am not reading messages.'
            else:
                if self.current_detect_message is None:
                    self.current_detect_message = [
                        'Leave me alone. I am working hard to keep large and small corals happy in the playpen.',
                        'The corals are too noisy. No more bandwidth to entertain you.',
                        'Shhh! The corals are sleeping and I am counting their tentacles.'
                    ][random.randrange(0, 3)]
                self.banner_message = self.current_detect_message
            return (state.name, capturer_state.name, cpu_percent, f'{cpu_percent} %', mem_percent, f'{mem_percent} %', 
                    self.banner_message,)
        return update_content 