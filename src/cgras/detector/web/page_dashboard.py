# Copyright 2024 - Andrew Kwok Fai LUI, 
# Robotics and Autonomous Systems Group, REF, RI
# and the Queensland University of Technology

__author__ = 'Andrew Lui'
__copyright__ = 'Copyright 2024'
__license__ = 'GPL'
__version__ = '1.0'
__email__ = 'ak.lui@qut.edu.au'
__status__ = 'Development'

import dash
from dash import html, dcc, Input, Output
import dash_bootstrap_components as dbc
# project modules
from dash.exceptions import PreventUpdate
from cgras.tools.logging_tools import logger
from cgras.detector.model import STATE, SystemStates

from cgras.detector.web.blocks import ProcessTaskControlBlock, MonitorStateBlock, MonitorExecuteProgressBlock, MonitorRecentTaskTableBlock, MonitorTaskStatBlock

dash.register_page(__name__)

# -- define the GUI components of this page
class DashboardPage():
    def __init__(self, app, refresh_cycle=1):
        self.app = app
        prefix = self.prefix = 'dashboard_'
        self.dashapp_interval_store_id = prefix + 'update_store'
        # model variables
        self.refresh_cycle = refresh_cycle
        if self.refresh_cycle is None or type(self.refresh_cycle) not in [float, int]:
            self.refresh_cycle = 1
        # the component blocks
        self.process_task_control_panel = ProcessTaskControlBlock(app, prefix)
        self.monitor_state_panel = MonitorStateBlock(app, prefix)
        self.monitor_execute_progress_panel = MonitorExecuteProgressBlock(app, prefix)
        self.monitor_recent_task_table_panel = MonitorRecentTaskTableBlock(app, prefix) 
        self.monitor_task_stat_panel = MonitorTaskStatBlock(app, prefix)
        # define the page
        self._define_page()
    
    def layout(self, validate=False):
        return self._layout

    def _define_page(self):
        # connect the system interval timer to the pending_sample_table and the tile_sample_retrieve_panel
        self.process_task_control_panel.register_trigger(self.dashapp_interval_store_id)
        self.monitor_state_panel.register_trigger(self.dashapp_interval_store_id)
        self.monitor_execute_progress_panel.register_trigger(self.dashapp_interval_store_id)      
        self.monitor_recent_task_table_panel.register_trigger(self.dashapp_interval_store_id)
        self.monitor_task_stat_panel.register_trigger(self.dashapp_interval_store_id)
        
        # putting the GUI components together 
        self._panel = html.Div(id='scan-body',children = [
            dcc.Store(id=self.dashapp_interval_store_id),
            dbc.Row(html.H4(children = 'Image Analysis and Task Execution Dashboard', className='mt-3 mb-3')),
            dbc.Row([
                dbc.Col(self.process_task_control_panel.get_panel(), className='col-6 border'),
                dbc.Col(self.monitor_state_panel.get_panel(), className='col-6 border'),
                ], className='mx-auto col-12'),
            dbc.Row([
                dbc.Col(self.monitor_execute_progress_panel.get_panel(), className='col-12 border'),
                ], className='mx-auto col-12 mt-3'), 
            dbc.Row([
                dbc.Col(self.monitor_recent_task_table_panel.get_panel(), className='col-9 border'),
                dbc.Col(self.monitor_task_stat_panel.get_panel(), className='col-3 border'),
                ], className='mx-auto col-12 mt-3'),           
        ])
        self._layout = dbc.Container(self._panel, fluid=True)

        # callback setup for the overall dashboard update using the dashapp interval store
        self.app.callback([Output(self.dashapp_interval_store_id, 'data', allow_duplicate=True)],
            [Input('dashapp_interval_store', 'data')], prevent_initial_call=True)(self._update_all())     

    # the callback for all update
    def _update_all(self):
        def update_all(n):
            if (n-1) % self.refresh_cycle != 0:
                raise PreventUpdate
            return (n,)
        return update_all  
