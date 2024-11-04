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
from dash import html
import dash_bootstrap_components as dbc
# project modules
from dash.exceptions import PreventUpdate
from tools.logging_tools import logger
from detector.web.blocks import ResetDBBlock, DiskspaceBlock, FileSpaceSaver, ResetStatDBTableBlock

dash.register_page(__name__)

class AdminSetupPage():
    def __init__(self, app):
        self.app = app 
        prefix = 'admin_setup_'
        self.reset_db_block = ResetDBBlock(app, prefix)
        self.reset_statistics_block = ResetStatDBTableBlock(app, prefix)
        self.diskspace_block = DiskspaceBlock(app, prefix)
        self.filespace_saver_block = FileSpaceSaver(app, prefix)

        self._define_page()
    
    def layout(self):
        return self._layout
    
    # define the GUI components of this page
    def _define_page(self):        
        self.diskspace_block.register_trigger('dashapp_interval_store')
        # self.tile_stat_block.register_trigger(self.tile_info_import_block.get_success_trigger_id())      

        # putting the GUI components together 
        rows = html.Div(id='scan-body',children = [
            dbc.Row(html.H3(children = 'System Setup', className='mt-3 mb-3')),
            # dbc.Row(html.H4(children = 'Spawning Season', className='text-center mt-3 mb-3')),
            # dbc.Row([dbc.Col(self.spwaning_season_block.get_panel(), className='col-12 border')], 
            #         className='mx-auto'),            
            # dbc.Row(html.H4(children = 'AIMS Tile Identification', className='text-center mt-5 mb-3')),
            # dbc.Row([dbc.Col(self.tile_info_import_block.get_panel(), className='col-6'), 
            #          dbc.Col(self.tile_stat_block.get_panel(), className='col-6')], 
            #         className='mx-auto border'),
            dbc.Row(html.H4(children = 'Danger Zone', className='text-center mt-5 mb-3 text-danger')),
            dbc.Row([dbc.Col(self.reset_db_block.get_panel(), className='col-6 border'),
                     dbc.Col(self.reset_statistics_block.get_panel(), className='col-4 border'),
                     dbc.Col(self.diskspace_block.get_panel(), className='col-2 border'),
                     ], 
                    className='mx-auto mb-5'),
        ], className='mx-auto col-10')
        self._layout = dbc.Container(rows, fluid=True)
        


