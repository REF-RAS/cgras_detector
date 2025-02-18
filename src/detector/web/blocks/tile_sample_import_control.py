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
import dash_bootstrap_components as dbc
from dash.exceptions import PreventUpdate
from detector.model import DETECT_DAO, PERSISTENT_STORE_DAO, PersistentStoreDAO
from cgras_datatools.logging_tools import logger
 
class EnableTileSamplesImportBlock():

    def __init__(self, app, prefix):
        self.app = app 
        self.prefix = prefix = prefix + 'etsi'
        self.update_store_id = prefix + 'update_store'
        # model variables
        self.import_new_samples_options = [
                {'label': 'Enabled', 'value': True},
                {'label': 'Disabled', 'value': False},]
        # define widgets 
        self._toast = dbc.Toast(id=prefix+'toast', is_open=False, duration=5000, icon='danger', header='Message',
                                style={'position': 'fixed', 'top': '15%', 'left': '50%', 'width': 640, 'transform': 'translate(-50%, -50%)'})

        import_new_samples_select = dcc.Dropdown(self.import_new_samples_options, value=None, id=prefix+'mode_dropdown', 
                                                className='mx-auto col-8', searchable=False, clearable=False)
        # database reset panel
        self._panel = dbc.Col([
                html.H4(dbc.Badge('IMPORT TILE SAMPLES FROM IAS', className='ms-1 me-2', color='white', text_color='secondary')),
                html.P('', className='mt-3 text-danger'), 
                html.P('Import Tile Samples from the Image Acquisition System', className='mx-auto col-8 fw-bold'),
                html.Div([import_new_samples_select], className='mx-auto col-4'),
                # html.P('New tile sample', id=prefix+'new_tile_sample_status', className='mt-3'),               
                self._toast,
                dcc.Store(self.update_store_id),
            ], id=prefix+'main_panel', className='mx-auto text-center')

        self.app.callback([Output(self.update_store_id, 'data', allow_duplicate=True)],
                            [Input(prefix+'mode_dropdown', 'value')], prevent_initial_call=True)(self._enable_import_tile_samples_toggle())
        
        self.app.callback([Output(self.prefix+'mode_dropdown', 'value')],
            [Input(self.update_store_id, 'data')], prevent_initial_call=True, allow_duplicate=True)(self._update_dropdown())

        self.app.callback([Output(self.update_store_id, 'data', allow_duplicate=True)],
            [Input(prefix+'main_panel', 'children')], prevent_initial_call=True, allow_duplicate=True)(self._update_panel())
   
    def get_panel(self):
        return self._panel
    
    def register_trigger(self, trigger_id:str):
        # define callbacks for the datatable data
        self.app.callback([Output(self.update_store_id, 'data', allow_duplicate=True)],
            [Input(trigger_id, 'data')], prevent_initial_call=True, allow_duplicate=True)(self._update_dropdown())
    
    def _update_dropdown(self):
        def update_dropdown(data):
            enable_import_new_samples = PERSISTENT_STORE_DAO.get_config_value(PersistentStoreDAO.TILE_IMPORT_ENABLED, default=False)
            return (enable_import_new_samples,)
        return update_dropdown
    
    def _update_panel(self):
        def update_panel(children):
            message = ' '
            return (True,)
        return update_panel    
    
    def _enable_import_tile_samples_toggle(self):
        def enable_import_tile_samples_toggle(enabled):
            PERSISTENT_STORE_DAO.set_config_value(PersistentStoreDAO.TILE_IMPORT_ENABLED, enabled)
            raise PreventUpdate
        return enable_import_tile_samples_toggle