# Copyright 2023 - Andrew Kwok Fai LUI, Centre for Robotics
# and the Queensland University of Technology
#
__author__ = 'Andrew Lui'
__copyright__ = 'Copyright 2023, The CGRAS Project'
__license__ = 'GPL'
__version__ = '0.0.1'
__email__ = 'ak.lui@qut.edu.au'
__status__ = 'Development'

import plotly.express as px
import plotly.graph_objects as go
# dash modules
import dash
from dash import html, dcc, callback, Input, Output, State, dash_table, ctx
import dash_bootstrap_components as dbc
from dash.exceptions import PreventUpdate
# project modules
import detector.model as model
from detector.model import STATE

dash.register_page(__name__)

# project panel components
from detector.web.blocks import AlertFunction
# interactive panels
from detector.web.minipages.minipage_idle import IdleMinipage
from detector.web.minipages.minipage_taskgen import TaskGenMinipage
from detector.web.minipages.minipage_detect import DetectMinipage

# -- define the GUI components on this page
class AdminConsolePage():
    def __init__(self, app):
        self.app = app
        self.status_monitor_dash_name = 'minipage_example_status_monitor_store'
        self.alert_function_dash_name = 'minipage_example_alert_function'

        self.interaction_panel = InteractionPanel(self.app)
        self.alert_function = AlertFunction(self.app, self.alert_function_dash_name)
        self._define_page()
    
    def layout(self, validate=False):
        return self._layout

    def _define_page(self):
        # row_status_monitor = dbc.Row(self.status_monitor_panel.panel(), className='mt-4')
        row_alert_function = self.alert_function.get_panel()
        row_console = dbc.Row(self.interaction_panel.panel(), className='mt-4')
        
        # -- putting the GUI components together 
        rows = html.Div(id='scan-body',children = [
            dcc.Interval(id='minipage_example_interval', interval=1000, n_intervals=0), 
            dcc.Store(id='minipage_example_status_monitor_store'),
            dcc.Store(id='minipage_example_interaction_store'),
            # row_status_monitor,
            row_console,
            row_alert_function
        ])
        self._layout = dbc.Container(rows, fluid=True)
        
        # -- define callbacks
        self.app.callback(    
            [Output('minipage_example_status_monitor_store', 'value'),
             Output('minipage_example_interaction_store', 'value'),
            Output('minipage_example_alert_function', 'value'),],
            Input('dashapp_interval_store', 'n_intervals'))(self._console_interval())  
    
    # -- the interval starting callback
    def _console_interval(self):
        def console_interval(n):
            return (1, 1, 1,)
        return console_interval

# -- PANEL: the Console Panel
class InteractionPanel():
    def __init__(self, app):
        self.app = app
        # the minipages
        self._idle_state_panel = IdleMinipage(self.app)        
        self._taskgen_state_panel = TaskGenMinipage(self.app)     
        self._detect_state_panel = DetectMinipage(self.app)     
        # the definition of this panel
        self._define_panel()
        # stateful variable        
        self._previous_state = None

    def panel(self):
        return self._panel
    
    def invalidate(self):
        self._previous_state = None
                
    def _define_panel(self):
        self._panel = html.Div([
            dcc.Store('minipage_example_interaction_minipage_store'),
            html.Div(id='minipage_example_interaction_body')])
        
        # - define callbacks
        self.app.callback(    
            [Output('minipage_example_interaction_body', 'children'),
             Output('minipage_example_interaction_minipage_store', 'value'),],
            [Input('minipage_example_interaction_store', 'value'),])(self._update_console_panel())   
    
    # -- the callback function
    def _update_console_panel(self):
        def update_console_panel(value):
            # changed_state_since_last = model.CONSOLE_STATE.has_changed_state('page_admin_console')
            state = STATE.get_state()
            validate = False 
            return_panel = None
            if self._previous_state is None or self._previous_state != state :
                validate = True
                self._previous_state = state
            if state == model.SystemStates.IDLE:
                return_panel = self._idle_state_panel.panel(validate)     
            elif state == model.SystemStates.TASKGEN:
                return_panel = self._taskgen_state_panel.panel(validate)             
            elif state in [model.SystemStates.DETECT, model.SystemStates.COUNT]:
                return_panel = self._detect_state_panel.panel(validate) 

                return_panel = html.Div()
            return (return_panel, 1,)
        return update_console_panel