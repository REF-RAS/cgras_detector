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
from dash import html, dcc, callback, Input, Output, State, dash_table, ctx
import dash_bootstrap_components as dbc
# project modules
from dash.exceptions import PreventUpdate
from cgras_datatools.logging_tools import logger
from detector.model import DETECT_DAO

class HealthModelFileImportBlock():
    def __init__(self, app, prefix):
        self.app = app
        prefix = prefix + 'hmfi_'
        self.import_success_trigger_id = prefix + 'import_success'
        # --- define widgets
        self._toast = dbc.Toast(id=prefix+'toast', is_open=False, duration=5000, icon='danger', 
                                style={'position': 'fixed', 'top': '10%', 'left': '50%', 'width': 640, 'transform': 'translate(-50%, -50%)'})
        # define tile sample spec import panel
        self.file_upload_area = dcc.Upload(id=prefix+'file_import_area', children=html.Div([
            'Drag and Drop or ', html.A('Select a health model file specification yaml file')]), style={
            # 'width': '400px', 
            'height': '60px', 'lineHeight': '60px',
            'borderWidth': '1px', 'borderStyle': 'dashed', 'borderRadius': '5px',
            'textAlign': 'center', 'margin': '10px'}, multiple=False)
        
        # define confirm panel in a modal
        self.confirm_modal = dbc.Modal(id=prefix+'confirm_modal', children=[
                dbc.ModalHeader(dbc.ModalTitle(id=prefix+'confirm_modal_title')),
                dbc.ModalBody(children=[html.P(id=prefix+'confirm_modal_textbox', className='text-danger'),
                                        dash_table.DataTable(id=prefix+'confirm_modal_table', style_cell={
                                            'textAlign': 'left', 'whiteSpace': 'normal', 'height': 'auto',},),                
                                            html.Div(id=prefix+'confirm_modal_button_panel', children=[
                                            dbc.Button('Confirm', id=prefix+'confirm_button', n_clicks=0, className='me-3'), 
                                            dbc.Button('Cancel', id=prefix+'cancel_button', n_clicks=0, color='secondary'),], 
                                        className='text-center, mt-3', style={'display': 'block'}, ),
                                        ]),
            ], size='xl', is_open=False,)  
        
        self.file_upload_panel = html.Div([
                dcc.Store(self.import_success_trigger_id),
                dcc.Store(id=prefix+'imported_content'),
                html.H4(dbc.Badge('IMPORT HEALTH MODEL FILE SPEC', className='ms-1 me-2', color='white', text_color='secondary')),
                html.P('Select the yaml file that specifies a health model for coral health evaluation.', style={'display': 'inline-block'}),
                self.file_upload_area,
                self._toast ,
                self.confirm_modal,
            ], className='text-center')   
                 
        # --- setup callbacks
        # callback setup for confirm import
        self.app.callback([Output(prefix+'toast', 'is_open'),
                           Output(prefix+'toast', 'children'),
                           Output(prefix+'import_success', 'data'),
                           Output(prefix+'confirm_modal', 'is_open', allow_duplicate=True),],
                        [Input(prefix+'confirm_button', 'n_clicks'),
                        Input(prefix+'cancel_button', 'n_clicks'),
                        State(prefix+'imported_content', 'data')], 
            prevent_initial_call=True)(self._file_import_confirmed())
     
        self.app.callback([Output(prefix+'confirm_modal', 'is_open', allow_duplicate=True),
                           Output(prefix+'confirm_modal_title', 'children'),
                           Output(prefix+'confirm_modal_table', 'data'),
                           Output(prefix+'confirm_modal_textbox', 'children'),
                           Output(prefix+'confirm_modal_button_panel', 'style'),
                           Output(prefix+'imported_content', 'data'),
                            Output(prefix+'file_import_area', 'contents'),  # essential to clear the uploaded_content to accept another upload file
                            Output(prefix+'file_import_area', 'filename'),],   # essential to clear the uploaded_content to accept another upload file
            [   Input(prefix+'file_import_area', 'contents'),
                State(prefix+'file_import_area', 'filename'),
                State(prefix+'file_import_area', 'last_modified'),
                # State('tile_upload_worksheet_checklist', 'value')
            ], 
            prevent_initial_call=True)(self._file_import_received())
    
    def get_panel(self):
        return self.file_upload_panel
    
    def get_import_success_trigger_id(self):
        return self.import_success_trigger_id

    # define callback functions
    def _file_import_confirmed(self): 
        def file_import_confirmed(confirm_button, cancel_button, yaml_data):
            button_id = ctx.triggered_id if ctx.triggered_id is not None else 'No clicks yet'
            if button_id.endswith('confirm_button'):
                default_start_day = 0
                result = DETECT_DAO.import_health_model_yaml(yaml_data)
                if result:
                    message = 'Import health model file successful'
                else:
                    message = 'Import health model file failed'
                return (True, message, yaml_data, False) 
            elif button_id.endswith('cancel_button'):
                
                return (False, ' ', None, False) 
        return file_import_confirmed  
     
    # the callback for import tile sample yaml file
    def _file_import_received(self): 
        def file_import_received(contents, filename, last_modified):       
            uploaded = {'contents': contents, 'filename': filename, 'last_modified': last_modified}
            content_type, content_string = contents.split(',')
            decoded = base64.b64decode(content_string)
            yaml_data = yaml.load(io.BytesIO(decoded), Loader=yaml.Loader)
            is_valid, model = DETECT_DAO.validate_health_model_file_import(yaml_data)
            if not is_valid:
                message = 'One or more problems have been found in the tile sample spec yaml file.'
                return (True, 'Error in the uploaded file', model.to_dict('records'), message, {'display': 'none'}, yaml_data, None, None,)  
            else:
                return (True, 'Confirm to import this health index model specification', model.to_dict('records'), None, {'display': 'block'}, yaml_data, None, None,) 
        return file_import_received 