# Copyright 2024 - Andrew Kwok Fai LUI, 
# Robotics and Autonomous Systems Group, REF, RI
# and the Queensland University of Technology

__author__ = 'Andrew Lui'
__copyright__ = 'Copyright 2024'
__license__ = 'GPL'
__version__ = '1.0'
__email__ = 'ak.lui@qut.edu.au'
__status__ = 'Development'

import shutil, zipfile, io
from base64 import b64encode
import pandas as pd
# dash modules
import dash
from dash import html, dcc, Input, Output, State, dash_table, ctx
import dash_bootstrap_components as dbc
import plotly.express as px
import plotly.graph_objects as go
from dash.exceptions import PreventUpdate
from tools.logging_tools import global_logger
from detector.model import APP_FILE_MANAGER, AIMSTILE_DAO, DETECT_DAO
from detector.models.visualize import CoralObjectMapModel, CoralObjectMapModelHelper

class CountResultDownloadBlock():
    def __init__(self, app, prefix):
        self.app = app 
        self.prefix = prefix = prefix + 'tdm_'
        self.tile_id_store_id = prefix+'tile_id_store'
        # model variables
        self.get_trend_figure_func = None
        self.get_heatmap_figures_list_func = None
        get_scatterplot_figures_list_func = None
        # define widgets
        self._count_show_button = dbc.Button('Coral Count Report', id=prefix+'popup_button', color='light', 
                                             href='', external_link=True, target='count_view')
        dropdown = dbc.DropdownMenu(label='Download Data and Report', children=[            
            html.P('Select the format of the data or report to download', className="text-muted px-4 mt-4"),
            dbc.DropdownMenuItem('Data', header=True),
            dbc.DropdownMenuItem('Count Data (Excel)', id=prefix+'download_excel'),
            dbc.DropdownMenuItem('Figure Images (ZIP)', id=prefix+'download_figures'),
            dbc.DropdownMenuItem(divider=True),
            dbc.DropdownMenuItem('Print', header=True),
            self._count_show_button,
        ])
        
        self._panel = html.Div([
            dcc.Store(id=self.tile_id_store_id),
            dropdown,
            dcc.Download(id=prefix+'download_figures_zip_file'),
            ], 
            id=prefix+'main_panel', className='mx-auto')
        
    def register_trigger(self, trigger_id:str):
        # define callback
        self.app.callback([Output(self.tile_id_store_id, 'data'),
                           Output(self.prefix+'popup_button', 'href'),
                            Output(self.prefix+'main_panel', 'style'),],
            [Input(trigger_id, 'data')], prevent_initial_call=True, allow_duplicate=True)(self._update_tile_id()) 
        
    def set_download_figures_funcs(self, get_trend_figure_func, get_heatmap_figures_list_func, get_scatterplot_figures_list_func):
        self.get_trend_figure_func = get_trend_figure_func
        self.get_heatmap_figures_list_func = get_heatmap_figures_list_func
        self.get_scatterplot_figures_list_func = get_scatterplot_figures_list_func
        # define callback
        self.app.callback([Output(self.prefix+'download_figures_zip_file', 'data', allow_duplicate=True)],
            [Input(self.prefix+'download_figures', 'n_clicks'),
             State(self.tile_id_store_id, 'data')], prevent_initial_call=True, allow_duplicate=True)(self._download_figures_selected())   
        
        self.app.callback([Output(self.prefix+'download_figures_zip_file', 'data')],
            [Input(self.prefix+'download_excel', 'n_clicks'),
             State(self.tile_id_store_id, 'data')], prevent_initial_call=True, allow_duplicate=True)(self._download_excel_selected())           
        
        
    def get_panel(self):
        return self._panel
    
    # callback for the diskspace table
    def _update_tile_id(self):
        def update_tile_id(tile_id):
            if tile_id is None:
                raise PreventUpdate
            coral_trend_model = DETECT_DAO.get_coral_count_trend_as_df(tile_id) 
            href = f'/popup_count_display?tile_id={tile_id}'
            if len(coral_trend_model) == 0:
                return (tile_id, None, {'visibility': 'hidden'},)
            return (tile_id, href, {'visibility': 'visible'},)
        return update_tile_id

    # callback
    def _download_figures_selected(self):
        def update_datatable(n_clicks, tile_id):
            if not n_clicks or not tile_id:
                raise PreventUpdate
            image_filebytes_list = []
            image_filename_list = []
            # retrieve figures from the trend panel
            if self.get_trend_figure_func is not None:
                fig_list = self.get_heatmap_figures_list_func()
                if fig_list:
                    trend_fig = fig_list[0]
                    img_bytes = trend_fig.to_image(format='png')
                    image_filebytes_list.append(img_bytes)
                    image_filename_list.append(f'{tile_id}_trend_chart.png')
            # retrieve figures from the heatmap panel
            if self.get_heatmap_figures_list_func is not None:            
                fig_list = self.get_heatmap_figures_list_func()
                for index, heatmap_fig in enumerate(fig_list):
                    img_bytes = heatmap_fig.to_image(format='png')
                    title = heatmap_fig.to_dict()['layout']['title']['text']
                    image_filebytes_list.append(img_bytes)
                    image_filename_list.append(f'{tile_id}_heatmap_{index}.png')
            # retrieve figures from the scatter plot panel
            if self.get_scatterplot_figures_list_func:
                fig_list = self.get_scatterplot_figures_list_func()
                for index, heatmap_fig in enumerate(fig_list):
                    img_bytes = heatmap_fig.to_image(format='png')
                    title = heatmap_fig.to_dict()['layout']['title']['text']
                    image_filebytes_list.append(img_bytes)
                    image_filename_list.append(f'{tile_id}_scatterplot_{index}.png')                      
                    
            zip_encoded = self.generate_zip(image_filebytes_list, image_filename_list)
            zip_encoded = b64encode(zip_encoded).decode()
            data = dict(content=zip_encoded, filename=f'{tile_id}_charts.zip', base64=True)            
            return (data,)
        return update_datatable 
    
    def generate_zip(self, image_filebytes_list, image_filename_list):
        sink = io.BytesIO()
        with zipfile.ZipFile(sink, mode='w') as zf:
            for image_filebyte, image_filename in zip(image_filebytes_list, image_filename_list):
                zf.writestr(image_filename, image_filebyte)
        zf.close()
        return sink.getvalue()

    # callback
    def _download_excel_selected(self):
        def download_excel_selected(n_clicks, tile_id):
            if not n_clicks or not tile_id:
                raise PreventUpdate
            # build multiple sheets excel 
            with io.BytesIO() as output:
                writer = pd.ExcelWriter(output, engine='xlsxwriter')
                # retrieve the tile info
                tile_info_df = AIMSTILE_DAO.get_tile(tile_id, to_dataframe=True)
                tile_info_df.to_excel(writer, sheet_name='TileInfo', index=False)
                
                coral_count_trend_df = DETECT_DAO.get_coral_count_trend_as_df(tile_id)
                coral_count_trend_df.to_excel(writer, sheet_name='CoralCountTrend', index=False)

                # go through each tile sample id and retrieve the coral detection
                for index, row in coral_count_trend_df.iterrows():
                    tile_sample_id = row['tile_sample_id']
                    detected_objects_df = DETECT_DAO.query_detected_objects(tile_sample_id)
                    detected_objects_df.to_excel(writer, sheet_name=f'Detect-{row["batch_time"][:11]}', index=False)
                latest_tile_sample_id = coral_count_trend_df.iloc[-1]['tile_sample_id']
                vt_model = CoralObjectMapModel(latest_tile_sample_id)
                count_map = vt_model.compute_object_count_map(CoralObjectMapModelHelper.VISCLASS_CORAL['value'])
                count_map_df = pd.DataFrame(data=count_map)
                count_map_df.to_excel(writer, sheet_name=f'CountMap-{coral_count_trend_df.iloc[-1]["batch_time"][:11]}', index=False)
                writer.close()
                output.seek(0)
                # wrap up the excel file and send for download
                output_encoded = b64encode(output.getvalue()).decode()
                data = dict(content=output_encoded, filename=f'{tile_id}_data.xlsx', base64=True)            
                return (data,)
            
        return download_excel_selected