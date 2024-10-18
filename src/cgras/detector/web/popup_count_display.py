# Copyright 2024 - Andrew Kwok Fai LUI, 
# Robotics and Autonomous Systems Group, REF, RI
# and the Queensland University of Technology

__author__ = 'Andrew Lui'
__copyright__ = 'Copyright 2024'
__license__ = 'GPL'
__version__ = '1.0'
__email__ = 'ak.lui@qut.edu.au'
__status__ = 'Development'

import pandas as pd
import dash
from dash import html, dcc, callback, Input, Output, State, clientside_callback
import dash_bootstrap_components as dbc
# project modules
from dash.exceptions import PreventUpdate
from cgras.tools.logging_tools import logger
from cgras.detector.web.blocks import CoralCountTileInfoBlock, CountTileTrendBlock, CountHeatmapBlock, CountScatterMapBlock

dash.register_page(__name__)

# -- define the GUI components of this page
class CountDisplayPopup():
    def __init__(self, app):
        self.app = app
        prefix = self.prefix = 'count_display_popup'
        # model variables
        self.current_tile_id = None
        # create block components
        self.update_trigger_id = self.prefix+'update_trigger'
        self.tile_id_store_id = self.prefix+'tile_id_store'
        self.tile_detect_info = CoralCountTileInfoBlock(app, prefix)
        self.coral_count_trend = CountTileTrendBlock(app, prefix)
        self.heatmap_compare = CountHeatmapBlock(app, prefix)
        self.count_scatter_plot = CountScatterMapBlock(app, prefix)
        self._define_page()
    
    def layout(self, tile_id=None):
        if tile_id is not None:
            self.tile_id_store.__setattr__('data', tile_id)
        return self._layout
    
    def _define_page(self):
        # define widgets
        self.tile_id_store = dcc.Store(id=self.tile_id_store_id)
        # putting the components together 
        rows = html.Div(children = [
            html.Div(id=self.prefix+'_dummy_div'),
            dcc.Store(id=self.update_trigger_id), 
            self.tile_id_store,
            dbc.Row([html.H4(id=self.prefix+'title', children='Coral Detection Results', className='mt-3 mb-3 col-10'),
                     dbc.Col(
                            dbc.Button('Print', id=self.prefix+'print_button', color='light', size='sm', className='mt-3 mx-auto'),
                        className='col-2 text-end', align='right')
                     ]),
            dbc.Row([
                dbc.Col([
                        self.tile_detect_info.get_panel(),
                        dbc.Row(className='mt-4'),                       
                        self.coral_count_trend.get_panel(),
                        dbc.Row(className='mt-4'),                        
                        self.count_scatter_plot.get_panel(),   
                        dbc.Row([self.heatmap_compare.get_panel()], className='mx-auto col-12, mt-4'), 
                ], id=self.prefix+'_panel', className='col-12', style={'visibility': 'visible'}), 
            ], className='mx-auto col-12'),
        ])
        
        self._layout = dbc.Container(rows, fluid=True)
        # link up trigger events of the components
        self.tile_detect_info.register_trigger(self.update_trigger_id)
        self.coral_count_trend.register_trigger(self.update_trigger_id)
        self.heatmap_compare.register_trigger(self.update_trigger_id)  
        self.count_scatter_plot.register_trigger(self.update_trigger_id)
       
        self.app.callback([Output(self.update_trigger_id, 'data'),
                           Output(self.prefix+'_panel', 'style'),],
            [Input(self.prefix+'_dummy_div', 'children'),
             State(self.tile_id_store_id, 'data')], prevent_initial_call=False, allow_duplicate=True)(self._update())      

        self.app.clientside_callback("""
                function() {
                    window.print();
                    return window.dash_clientside.no_update
                }
            """,
            Output(self.prefix+'title', 'children'),
            Input(self.prefix+'print_button', 'n_clicks'),
            prevent_initial_call=True
        )

    def _update(self):
        def update(timer, tile_id):
            if tile_id is None:
                raise PreventUpdate
            return (tile_id, {'visibility': 'visible'},)
        return update

