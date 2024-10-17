# Copyright 2023 - Andrew Kwok Fai LUI, Centre for Robotics
# and the Queensland University of Technology
#
__author__ = 'Andrew Lui'
__copyright__ = 'Copyright 2023, The CGRAS Project'
__license__ = 'GPL'
__version__ = '0.0.1'
__email__ = 'ak.lui@qut.edu.au'
__status__ = 'Development'

# dash modules
import dash
from dash import html, dcc, Input, Output, State, dash_table, ctx
import dash_bootstrap_components as dbc
from dash.exceptions import PreventUpdate
# project modules
import detector.model as model

#### PANEL for interacting with the scanning task
class TaskGenMinipage():
    def __init__(self, app, prefix=''):
        self.app = app
        try:
            self.splash_url = f'https://cms.qut.edu.au/__data/assets/image/0011/1324955/be-ready-campaign-2023-forest.jpg'
        except:
            print(f'splash minipage: unable to load splash image')
        self._panel = None
        self._define_panel()        
        
    def panel(self, validate):
        if validate:
            pass
        return self._panel

    def _define_panel(self): 
        self._splash_card = dbc.Card([dbc.CardBody([
            html.H3('Welcome to CGRAS TASKGEN Minipage'),                  
            dbc.Button('Start', id='taskgen_change_state_button', color='primary', className='w-50', size='lg')]),
            dbc.CardImg(src=self.splash_url, bottom=True),
        ], className='text-center mt-5')

        self._placeholder = dbc.Row(self._splash_card, className='mx-auto col-8')
                            
        self._panel = html.Div([
            self._placeholder,
        ])
        
        # - define callbacks         
        self.app.callback([Output('idle_change_state_button', 'n_click')],
                            [Input('idle_change_state_button', 'n_clicks_timestamp')], 
                            prevent_initial_call=True)(self._button_pressed())
        
    # - the callback function for the buttons
    def _button_pressed(self):
        def button_pressed(start_button):
            button_id = ctx.triggered_id if not None else 'No clicks yet'
            if button_id == 'idle_change_state_button':
                model.STATE.update_state(model.SystemStates.DETECT)
            raise PreventUpdate
        return button_pressed