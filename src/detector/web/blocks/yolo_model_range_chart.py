# Copyright 2024 - Andrew Kwok Fai LUI, 
# Robotics and Autonomous Systems Group, REF, RI
# and the Queensland University of Technology

__author__ = 'Andrew Lui'
__copyright__ = 'Copyright 2024'
__license__ = 'GPL'
__version__ = '1.0'
__email__ = 'ak.lui@qut.edu.au'
__status__ = 'Development'

import base64, io, yaml
import dash
import numpy as np
import pandas as pd
from dash import html, dcc, callback, Input, Output, State, dash_table, ctx
import dash_bootstrap_components as dbc
import plotly.express as px
import plotly.graph_objects as go

# project modules
from dash.exceptions import PreventUpdate
from tools.logging_tools import global_logger
from detector.model import DETECT_DAO, CONFIG, SystemConfigNames

class YoloModelRangeChartBlock():
    def __init__(self, app, prefix):
        self.app = app
        self.prefix = prefix = prefix + 'ymrc_'
        self.default_max_end_day = CONFIG.get(SystemConfigNames.MAX_CORAL_AGE)
        # --- define widgets
        self._model = self.get_default_chart_model()
        
        self.chart_panel = html.Div([
                dcc.Store(id=prefix+'update_chart_store'),
                html.H4(dbc.Badge('', className='ms-1 me-2', color='white', text_color='secondary')),
                html.P('', style={'display': 'inline-block'}),
                dcc.Graph(id=prefix+'chart', style={'visibility': 'hidden'}),
            ], className='text-center')   
                 
        self.app.callback([Output(self.prefix+'chart', 'figure'),
                           Output(self.prefix+'chart', 'config'),
                           Output(self.prefix+'chart', 'style'),],
            [Input(self.prefix+'update_chart_store', 'data')], prevent_initial_call=False, allow_duplicate=True)(self._update_chart())
    
    def get_panel(self):
        return self.chart_panel
    
    def register_update_chart_trigger(self, trigger_id:str):
        self.app.callback([Output(self.prefix+'update_chart_store', 'data'),],
            [Input(trigger_id, 'data')], prevent_initial_call=False, allow_duplicate=True)(self._trigger_update_chart())
    
    def get_default_chart_model(self):
        model = DETECT_DAO.list_yolo_model()
        model.start_day.fillna(value=0, inplace=True)
        model['end_day'] = model['end_day'].apply(lambda x: self.default_max_end_day if x == -1 else x)
        model['x'] = model.apply(lambda row: (row['end_day'] + row['start_day']) // 2, axis=1)
        model['e'] = model.apply(lambda row: (row['x'] - row['start_day']), axis=1)
        model.insert(0, 'y', range(0, len(model)))
        model['y'] = model['y'] / len(model) + (1.0 / (1 + len(model)))
        return model
    
    def _trigger_update_chart(self):
        def trigger_update_chart(store):
            return (store,)
        return trigger_update_chart

    # the callback for updating the datatable
    def _update_chart(self):
        def update_chart(store):
            config = {'staticPlot': True}
            model = self.get_default_chart_model()
            fig = px.scatter(model, x='x', y='y', color='species', text='name', error_x='e', range_x=[0, self.default_max_end_day], 
                               range_y=[0, 1])
            if len(model) > 0:
                fig.update_xaxes(title='Age Range Covered by the Model (Days)', visible=True, showticklabels=True)
                fig.update_layout(yaxis_visible=False, yaxis_showticklabels=False, plot_bgcolor='rgb(225, 225, 225)')
                fig.update_traces(textposition='top center')
                fig.data[0].error_x.thickness = 12
                return (fig, config, {'visibility': 'visible'})
            else:
                return (fig, config, {'visibility': 'hidden'})
            
        return update_chart