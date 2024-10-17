# Copyright 2024 - Andrew Kwok Fai LUI, 
# Robotics and Autonomous Systems Group, REF, RI
# and the Queensland University of Technology

__author__ = 'Andrew Lui'
__copyright__ = 'Copyright 2024'
__license__ = 'GPL'
__version__ = '1.0'
__email__ = 'ak.lui@qut.edu.au'
__status__ = 'Development'


# dash modules
import dash
from dash import html, dcc, Input, Output, State, dash_table, ctx
import dash_daq as daq
import dash_bootstrap_components as dbc
from dash.exceptions import PreventUpdate
from cgras.detector.model import DETECT_DAO, PERSISTENT_STORE_DAO

 
class EnableTileSamplesImportBlock():
    def __init__(self, app, prefix):
        self.app = app 
        self.prefix = prefix = prefix + 'etsi'
        # model variables
        self.enable_import_new_samples_config = 'enable_import_new_samples'
        self.enable_import_new_samples:bool = PERSISTENT_STORE_DAO.get_tiles_import_enabled(default=False)
        self.import_new_samples_options = [
                {'label': 'Enabled', 'value': True},
                {'label': 'Disabled', 'value': False},]
        # define widgets 
        message_alert = dbc.Alert('', id=prefix+'message_alert', dismissable=True, is_open=False, className='col-12')

        import_new_samples_select = dcc.Dropdown(self.import_new_samples_options, value=self.enable_import_new_samples, id=prefix+'mode_dropdown', 
                                                className='mx-auto col-8', searchable=False, clearable=False)
        # database reset panel
        self._panel = dbc.Col([
                html.H4(dbc.Badge('IMPORT TILE SAMPLES FROM IAS', className='ms-1 me-2', color='white', text_color='secondary')),
                html.P('', className='mt-3 text-danger'), 
                html.P('Import Tile Samples from the Image Acquisition System', className='mx-auto col-8 fw-bold'),
                html.Div([import_new_samples_select], className='mx-auto col-4'),
                html.P('New tile sample', id=prefix+'new_tile_sample_status', className='mt-3'),               
                message_alert,
            ], className='mx-auto text-center')

        self.app.callback([Output(prefix+'dummy', 'data')],
                            [Input(prefix+'mode_dropdown', 'value')], 
            prevent_initial_call=True)(self._enable_import_tile_samples_toggle())
   
    def get_panel(self):
        return self._panel
    
    def register_trigger(self, trigger_id:str):
        # define callbacks for the datatable data
        self.app.callback([Output(self.prefix+'new_tile_sample_status', 'children')],
            [Input(trigger_id, 'data')], prevent_initial_call=True, allow_duplicate=True)(self._update_panel())
    
    def _update_panel(self):
        def update_panel(data):
            message = 'No new tile sample is found in the image acquisition system'
            return (message,)
        return update_panel
    
    def _enable_import_tile_samples_toggle(self):
        def enable_import_tile_samples_toggle(enabled):
            PERSISTENT_STORE_DAO.update_tiles_import_enabled(enabled)
            return (None,)
        return enable_import_tile_samples_toggle