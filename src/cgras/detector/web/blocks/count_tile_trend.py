# Copyright 2024 - Andrew Kwok Fai LUI, 
# Robotics and Autonomous Systems Group, REF, RI
# and the Queensland University of Technology

__author__ = 'Andrew Lui'
__copyright__ = 'Copyright 2024'
__license__ = 'GPL'
__version__ = '1.0'
__email__ = 'ak.lui@qut.edu.au'
__status__ = 'Development'

import shutil
import pandas as pd
# dash modules
import dash
from dash import html, dcc, Input, Output, State, dash_table, ctx
import dash_bootstrap_components as dbc
import plotly.express as px
import plotly.graph_objects as go
from dash.exceptions import PreventUpdate
from cgras.tools.logging_tools import logger
from cgras.detector.model import DETECT_DAO

class CountTileTrendBlock():
    def __init__(self, app, prefix):
        self.app = app 
        self.prefix = prefix = prefix + 'tdt_'
        # model variables
        self.trend_figure = None
        # define widgets 
        _coral_count_datatable = dash_table.DataTable(id=prefix+'coral_count_datatable', row_selectable=False, cell_selectable=False)
        

        self.chart_message = html.P('No trend chart is shown because this tile has fewer than 2 samples')
        
        self._panel = html.Div([
            html.H4(dbc.Badge('CORAL COUNT TREND', className='ms-1 me-2', color='white', text_color='secondary')),
            dbc.Row([
                dbc.Col([_coral_count_datatable], className='col-3'),
                dbc.Col(id=prefix+'chart_panel', className='col-9'),                
                ], className='mx-auto col-12'),
            ],
            id=prefix+'main_panel', className='col-12 text-center')
        
    def register_trigger(self, trigger_id:str):
        # define callbacks for the datatable data
        self.app.callback([Output(self.prefix+'coral_count_datatable', 'data'),
                           Output(self.prefix+'chart_panel', 'children'),                           
                           Output(self.prefix+'main_panel', 'style'),],
            [Input(trigger_id, 'data')], prevent_initial_call=True, allow_duplicate=True)(self._update_datatable()) 
    
    def get_figures_as_list(self):
        return [self.trend_figure]
        
    def get_panel(self):
        return self._panel

    def _get_coral_trend_model(self, tile_id):
        coral_trend_model = DETECT_DAO.get_coral_count_trend_as_df(tile_id) 
        coral_trend_model['batch_time'] = pd.to_datetime(coral_trend_model['batch_time']).dt.date
        coral_trend_model['batch_time'] = coral_trend_model.apply(lambda row: f'{row["batch_time"]} ({row["age"]} days)', axis=1)
        table_model = coral_trend_model[['batch_time', 'coral_object_count']]
        table_model.columns = ['Date', '# Corals']
        return coral_trend_model, table_model

    # callback for the diskspace table
    def _update_datatable(self):
        def update_datatable(tile_id):
            if tile_id is None:
                raise PreventUpdate
            # config = {'staticPlot': True}
            config = {}
            # generate the coral trend tabl
            coral_trend_model, table_model = self._get_coral_trend_model(tile_id)
            self.trend_figure = px.line(coral_trend_model, x='age', y='coral_object_count')            
            # generate the chart illustrating coral trends
            if len(table_model) == 0:
                return (table_model.to_dict('records'), None,  {'visibility': 'hidden'})
            elif len(table_model) <= 1:
                return (table_model.to_dict('records'), self.chart_message, {})

            self.trend_figure.update_traces(line=dict(color='rgb(255, 0, 0)', width=4))
            self.trend_figure.update_xaxes(title='Age (days since settlement)', visible=True, showticklabels=True, showgrid=True, gridwidth=1, gridcolor='LightGrey', range=[0, coral_trend_model.iloc[-1]['age']])
            self.trend_figure.update_yaxes(title='Coral count', visible=True, showticklabels=True, showgrid=True, gridwidth=1, gridcolor='LightGrey')
            # fig.update_layout(yaxis_visible=True, yaxis_showticklabels=True)
            self.trend_figure.update_layout(plot_bgcolor='rgb(255, 255, 225)')
            chart_graph = dcc.Graph(figure=self.trend_figure, config=config, style={'height': 'auto'})

            return (table_model.to_dict('records'), chart_graph, {})
        return update_datatable 