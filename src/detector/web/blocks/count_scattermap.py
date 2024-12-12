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
from tools.logging_tools import logger
from detector.model import DETECT_DAO, ObjectClassCategories


class CountScatterMapBlock():
    def __init__(self, app, prefix:str):
        self.app = app 
        self.prefix = prefix = prefix + 'csm_'
        self.update_trigger_id = 'tile_sample_id_update_trigger'
        # default charting parameters
        self.default_style = {'visibility': 'hidden'}
        self.default_config = {'staticPlot': True}        
        # model variables
        self.current_tile_id = None
        self.coral_trend_model = self.output_model = None
        self.latest_graph = None
        self.class_options = None
        self.figures_list = []
        # a fixed discrete color map
        self.scatter_plot_discrete_colour_map = {} 
        for i, cat in enumerate(ObjectClassCategories):
            self.scatter_plot_discrete_colour_map[cat.name] = px.colors.qualitative.G10[i]
        # define widgets
        _sample_select_datatable = dash_table.DataTable(id=prefix+'sample_select_datatable', row_selectable=False, cell_selectable=True, style_cell={'fontSize': 14})
        self._panel = html.Div(id=prefix+'top_panel', children=[
                dcc.Store(self.update_trigger_id),
                html.H4(dbc.Badge('SCATTER PLOT OF OBJECTS ON THE TILE', className='ms-1 me-2', color='white', text_color='secondary')),
                html.P('Assume 1:1 aspect ratio', className='fs-6'),
                dbc.Row([
                    dbc.Col([
                            html.P('Click and select a sample below to compare with the latest sample', style={'margin-top': '120px'}),
                            _sample_select_datatable,
                        ], className='col-2', style={'background-color': '#dddddd'}),
                    dbc.Col(id=prefix+'chart_panel', className='col-10'),                    
                ], className='mx-auto col-12'),            
            ], className='text-center')
        
        self.app.callback([Output(self.prefix+f'chart_panel', 'children', allow_duplicate=True)],
                        [Input(self.prefix+'sample_select_datatable', 'active_cell')], prevent_initial_call=True)(self._update_chart_panel())     
        
            
    def register_trigger(self, trigger_id:str):
        # build the output list
        output_list = [Output(self.prefix+f'top_panel', 'style', allow_duplicate=True),  
                        Output(self.prefix+'sample_select_datatable', 'data', allow_duplicate=True),
                        Output(self.prefix+'sample_select_datatable', 'active_cell', allow_duplicate=True),
                        Output(self.prefix+'sample_select_datatable', 'selected_cells', allow_duplicate=True),]
        input_list = [Input(trigger_id, 'data') ]
        # define callbacks for the datatable data
        self.app.callback(output_list, input_list, prevent_initial_call=True, allow_duplicate=True)(self._update_panel())
        
        
    def get_panel(self):
        return self._panel
    
    def get_figures_as_list(self):
        return self.figures_list

    def _get_coral_trend_model(self, tile_id):
        coral_trend_model = DETECT_DAO.get_coral_count_trend_as_df(tile_id) 
        coral_trend_model['batch_time'] = pd.to_datetime(coral_trend_model['batch_time']).dt.date
        coral_trend_model['batch_time'] = coral_trend_model.apply(lambda row: f'{row["batch_time"]} ({row["age"]} days old)', axis=1)
        output_model = coral_trend_model[['batch_time']]
        output_model.columns = ['Sample Date']
        if len(output_model) > 0:
            output_model = output_model.head(-1)  # remove the last row
        return coral_trend_model, output_model

    
    def _generate_scatter_plot(self, tile_sample_id, title:str=None):
        detected_object_df = DETECT_DAO.query_detected_objects(tile_sample_id)
        detected_object_df['class_category'] = detected_object_df['class_category'].apply(lambda cell: ObjectClassCategories(cell).name)
        
        fig = px.scatter(detected_object_df, x='centre_x', y='centre_y', color='class_category', width=480, height=520, title=title, color_discrete_map=self.scatter_plot_discrete_colour_map)
        fig.update_layout(
                margin=dict(l=5, r=5, t=60, b=5),
                plot_bgcolor='rgba(64, 64, 64, 1)',
                title=dict(font=dict(size=16, weight='bold')),
                legend=dict(orientation='h', yanchor='bottom', y=-0.20, xanchor='left', x=0.00),
        )
        fig.update_xaxes(title='X Location', showgrid=False, range=[0, 1])
        fig.update_yaxes(title='Y Location', showgrid=False, range=[1, 0])
        
        graph = dcc.Graph(figure=fig, config=self.default_config, style={'visibility': 'visible'})
        return graph, fig
    
    def _update_panel(self):
        def update_panel(tile_id):
            if tile_id is None:
                raise PreventUpdate
            # the update is due to a new tile_id selected
            if self.current_tile_id is None or tile_id != self.current_tile_id:
                self.current_tile_id = tile_id
                # update the coral_trend_model
                self.coral_trend_model, self.output_model = self._get_coral_trend_model(tile_id)
                self.latest_graph = None
                
            if len(self.coral_trend_model) > 0:
                return [{}, self.output_model.to_dict('records'), None, []]   
            else:
                return [{'visibility': 'hidden'}, self.output_model.to_dict('records'), None, []]                 
        return update_panel
    
    def _update_chart_panel(self):
        def update_chart_panel(active_cell):
            compare_graph = None
            if len(self.coral_trend_model) > 0:
                if self.latest_graph is None:
                    latest_index = len(self.coral_trend_model) - 1
                    the_sample = self.coral_trend_model.iloc[latest_index]        
                    title = f'Objects on the tile on {the_sample["batch_time"]} (Latest)'
                    self.latest_graph, fig = self._generate_scatter_plot(the_sample['tile_sample_id'], title)
                    self.figures_list = [fig]
                if active_cell is not None:
                    compare_to_index = active_cell['row']
                    the_sample = self.coral_trend_model.iloc[compare_to_index] 
                    title = f'Objects on the tile on {the_sample["batch_time"]}'
                    compare_graph, fig = self._generate_scatter_plot(the_sample['tile_sample_id'], title)
                    self.figures_list.append(fig)
                    
                chart_panel = dbc.Row([
                    dbc.Col(self.latest_graph, className='col-6'),
                    dbc.Col(compare_graph, className='col-6'),
                ])
                return [chart_panel]   
            else:
                return [None]              
        return update_chart_panel
