# Copyright 2024 - Andrew Kwok Fai LUI, 
# Robotics and Autonomous Systems Group, REF, RI
# and the Queensland University of Technology

__author__ = 'Andrew Lui'
__copyright__ = 'Copyright 2024'
__license__ = 'GPL'
__version__ = '1.0'
__email__ = 'ak.lui@qut.edu.au'
__status__ = 'Development'

import base64, io, traceback, shutil
from collections import OrderedDict
from datetime import datetime
from base64 import b64encode
import pandas as pd
# dash modules
import dash
from dash import html, dcc, Input, Output, State, dash_table, ctx
import dash_bootstrap_components as dbc
from dash.exceptions import PreventUpdate
import tools.file_tools as file_tools
from tools.logging_tools import logger
from detector.model import APP_FILE_MANAGER, AIMSTILE_DAO


class TileInfoImportFileBlock():
    def __init__(self, app, prefix):
        self.app = app
        self.prefix = prefix = prefix + 'tii_'
        self.worksheet_names = ['Tile', 'Species']
        self.import_mode = ['Replace All', 'Add New']
        self.default_excel_columns = OrderedDict([
            ('PIT_ID', 'pit_id'),
            ('SPECIES', 'species'),
            ('SEASON', 'season'),
            ('SETTLEMENT_TIME', 'settle_time'),            
            ('SPAWNING_TIME', 'spawn_time'),
        ])
        # define widgets
        message_alert = dbc.Alert('Nothing is happening', id=prefix+'message_alert', dismissable=True, duration=5000, is_open=False, className='col-12')
        confirm_dialog = dcc.ConfirmDialog(id=prefix+'confirm_dialog',
            message='All existing tile identification will be replaced! Are you sure you want to continue?',)
        
        tile_excel_upload_area = dcc.Upload(id=prefix+'file_import_area', children=html.Div([
            'Drag and Drop or ', html.A('Select an Excel or CSV file')]), style={
            'width': '90%', 'height': '60px', 'lineHeight': '60px',
            'borderWidth': '1px', 'borderStyle': 'dashed', 'borderRadius': '5px',
            'textAlign': 'center', 'margin': '10px'}, multiple=False)
        
        self.tile_info_import_panel = dbc.Col([
                dcc.Store(id=prefix+'tile_import_success'),
                dcc.Store(id=prefix+'tile_import_content'),
                confirm_dialog,
                html.H4(dbc.Badge('IMPORT TILE ID LIST', className='ms-1 me-2', color='white', text_color='secondary')),
                html.P('Select the worksheets of the excel file to be imported.', style={'display': 'inline-block'}),
                # dcc.Checklist(self.worksheet_names, self.worksheet_names, id='tile_upload_worksheet_checklist', 
                #                                      inline=True, labelClassName='ms-3 me-3', inputClassName='m-1', style={'display': 'inline-block'}),
                dcc.Dropdown(self.import_mode, self.import_mode[0], id=prefix+'mode_dropdown', className='col-4 d-inline-block', searchable=False, clearable=False),
                tile_excel_upload_area,
                html.P('Warning! If the mode is "Replace All", the current tile identification and species data will be deleted and replaced by the imported', className='text-danger'),
                dbc.Button('Download Tile ID List (Excel)', id=prefix+'download_excel_button', color='secondary', className='mb-3'), 
                dcc.Download(id=prefix+'download_excel_file'),
                message_alert,
            ], className='mx-auto text-center')
        
        self.app.callback([Output(prefix+'message_alert', 'is_open'),
                           Output(prefix+'message_alert', 'children'),
                           Output(prefix+'tile_import_success', 'data'),],
            [Input(prefix+'confirm_dialog', 'submit_n_clicks'),
             State(prefix+'tile_import_content', 'data')], 
            prevent_initial_call=True)(self._file_import_confirmed())
     
        self.app.callback([Output(prefix+'confirm_dialog', 'displayed'),
                           Output(prefix+'tile_import_content', 'data'),
                            Output(prefix+'file_import_area', 'contents'),  # essential to clear the uploaded_content to accept another upload file
                            Output(prefix+'file_import_area', 'filename'),],   # essential to clear the uploaded_content to accept another upload file
            [Input(prefix+'file_import_area', 'contents'),
                State(prefix+'file_import_area', 'filename'),
                State(prefix+'file_import_area', 'last_modified'),
                State(prefix+'mode_dropdown', 'value')
                # State('tile_upload_worksheet_checklist', 'value')
            ], 
            prevent_initial_call=True)(self._file_import_received())
        
        self.app.callback([Output(self.prefix+'download_excel_file', 'data')],
            [Input(self.prefix+'download_excel_button', 'n_clicks'),], prevent_initial_call=True)(self._download_excel_selected())    
        
    def get_panel(self):
        return self.tile_info_import_panel
    
    def get_success_trigger_id(self):
        return self.prefix+'tile_import_success'

    # the callback for import AIMS tile identification confirm dialog
    def _file_import_confirmed(self): 
        def file_import_confirmed(submit_n_clicks, uploaded):
            if submit_n_clicks:
                error_list = self.process_uploaded_excel_file(uploaded['mode'], uploaded['content'], None, uploaded['filename'], uploaded['last_modified'])
                message = 'update tile identification is successful'
                if len(error_list) > 0:
                    message = error_list
                return (True, message, True) 
        return file_import_confirmed  
     
    # the callback for import AIMS tile excel file
    def _file_import_received(self): 
        def file_import_received(contents, filename, last_modified, mode):       
            uploaded = {'content': contents, 'filename': filename, 'last_modified': last_modified, 'mode': mode}
            return (True, uploaded, None, None)  
        return file_import_received 

    # --- upload file processing
    # extract data from an excel file in a http request form, which may be coming from a web upload, by first
    # converting it into byte array and then call the main function
    def process_uploaded_excel_file(self, mode, contents, sheet_list=None, filename=None, last_modified=None):
        content_type, content_string = contents.split(',')
        decoded = base64.b64decode(content_string)
        return self.process_excel_file(mode, decoded, sheet_list, filename, last_modified)
        
    # extract data from an excel file in byte array form 
    def process_excel_file(self, mode, decoded, sheet_list=None, filename=None, last_modified=None):
        sheet_list = ['Species', 'Tile']
        error_list = []
        try:
            suffix = file_tools.get_suffix(filename, include_period=False)
            if suffix in ['xls', 'xlsx']:  
                df_dict = pd.read_excel(io.BytesIO(decoded), sheet_name=None)
                # goes through the worksheets in the excel file, and report error if one of the required worksheets not exists
                for sheet_name in sheet_list:
                    if sheet_name not in df_dict:
                        error_list.append(f'The required worksheet {sheet_name} not in the excel file')
                        break
                else:
                    # species_df, tile_df = df_dict['Species'], df_dict['Tile']
                    # species_df = species_df.reset_index()
                    tile_df = df_dict['Tile']
                    replace_all = mode == 'Replace All'
                    # clean up the dataframe imported from excel
                    try:
                        tile_df = tile_df[self.default_excel_columns.keys()]
                        tile_df.rename(columns=self.default_excel_columns, inplace=True)
                    except Exception as e:
                        error_list.append(f'One or more required columns not in the excel file: {e}')
                        return error_list 
                    import_error_list = AIMSTILE_DAO.import_from_dataframes(tile_df, replace_all)
                    if import_error_list:
                        error_list.extend(import_error_list)
            else:
                error_list.append(f'The suffix of {filename} is not xls or xlsx')
        except Exception as e:
            logger.error(f'Error: {traceback.format_exc()}')
            error_list.append(f'error in reading excel file or worksheet: {e}')
        return error_list
    
    # callback
    def _download_excel_selected(self):
        def download_excel_selected(n_clicks):
            if not n_clicks:
                raise PreventUpdate
            # build multiple sheets excel 
            with io.BytesIO() as output:
                writer = pd.ExcelWriter(output, engine='xlsxwriter')
                tile_df = AIMSTILE_DAO.list_all_tiles()
                tile_df = tile_df[list(self.default_excel_columns.values())]
                tile_df.columns = list(self.default_excel_columns.keys())
                tile_df.to_excel(writer, sheet_name=f'Tile', index=False)
                writer.close()
                output.seek(0)
                # wrap up the excel file and send for download
                output_encoded = b64encode(output.getvalue()).decode()
                today_str = datetime.today().strftime('%Y-%m-%d')
                data = dict(content=output_encoded, filename=f'Tiles-{today_str}.xlsx', base64=True)            
                return (data,)
        return download_excel_selected