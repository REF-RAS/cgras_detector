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
from tools.logging_tools import global_logger
from detector.model import STATE, SystemStates

from detector.web.blocks import HealthViewTable

dash.register_page(__name__)

# -- define the GUI components of this page
class CoralHealthPage():
    def __init__(self, app, refresh_cycle=5):
        self.app = app
        prefix = self.prefix = 'coral_health_'
        self.dashapp_interval_store_id = prefix + 'update_store'
        # model variables
        self.refresh_cycle = refresh_cycle
        if self.refresh_cycle is None or type(self.refresh_cycle) not in (float, int):
            self.refresh_cycle = 5
        # the component blocks
        self.health_view_table_panel = HealthViewTable(app, prefix)
        # define the page
        self._define_page()
    
    def layout(self):
        self.health_view_table_panel.refresh()
        return self._layout

    def _define_page(self):
        # connect the system interval timer to the pending_sample_table and the tile_sample_retrieve_panel
        self.health_view_table_panel.register_trigger(self.dashapp_interval_store_id)
        
        # putting the GUI components together 
        self._panel = html.Div(id='scan-body',children = [
            dcc.Store(id=self.dashapp_interval_store_id),
            dbc.Row(html.H3(children = 'Coral Health Dashboard', className='mt-3 mb-3')),
            dbc.Row([self.health_view_table_panel.get_panel(), ], className='mx-auto col-12'),

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
            return (1,)
        return update_all  
