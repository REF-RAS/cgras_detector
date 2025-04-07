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
from dash import html, dcc, Input, Output, State, dash_table, ctx, ALL
import dash_bootstrap_components as dbc
from dash.exceptions import PreventUpdate
from detector.model import DETECT_DBFM

 
class ResetDBBlock():
    def __init__(self, app, prefix):
        self.app = app 
        self.prefix = prefix = prefix + 'rdb_'
        self.reset_success_trigger_id = prefix+'reset_success'
        self.counter_store_id = prefix+'counter_store'
        # define the toast for feedback 
        self._toast = dbc.Toast('The database is reset and rebuilt', id=prefix+'toast', is_open=False, duration=5000, icon='danger', header='Message',
                                style={'position': 'fixed', 'top': '15%', 'left': '50%', 'width': 640, 'transform': 'translate(-50%, -50%)'})
        # define the modal for confirmation of user actions
        self._user_confirm_modal = dbc.Modal([
                    dbc.ModalHeader(dbc.ModalTitle('Clear Database', id=prefix+'confirm_modal_title')),
                    html.Div([html.P('All data in the database will be cleared! Are you sure you want to continue?', id=prefix+'confirm_modal_message'),
                                dbc.Button('Confirm', id={'type': prefix+'action', 'index': 'confirm'},), 
                                dbc.Button('Cancel', id={'type': prefix+'action', 'index': 'cancel'}, color='secondary')
                            ]
                        , className='d-grid gap-2 col-8 mx-auto', style={'padding': '6px'})
                        ], id=prefix+'confirm_modal', is_open=False)
        # database reset panel
        self.reset_db_panel = html.Div([
            dcc.Store(id=self.reset_success_trigger_id),
            dcc.Store(id=self.counter_store_id),
            html.H4(dbc.Badge('RESET DB TABLES', className='ms-1 me-2', color='white', text_color='secondary')),
            html.P('Press the button to reset the database', className='mt-3'),
            dbc.Button('Drop and Create Tables', id=prefix+'reset_button', color='danger', className=''), 
            html.P('Warning! All the DB tables will be deleted and then created', className='mt-3 text-danger'),
            html.P('(You will be required to confirm thrice)', className='mt-3 text-danger'),
            self._toast,
            self._user_confirm_modal,
            ], className='text-center')

        # define the callbacks
        self.app.callback([Output(prefix+'confirm_modal', 'is_open', allow_duplicate=True),
                           Output(self.counter_store_id, 'data', allow_duplicate=True)],
                            [Input(prefix+'reset_button', 'n_clicks')], prevent_initial_call=True)(self._cb_reset_button_pressed())
        
        # self.app.callback([Output(prefix+'confirm_modal', 'is_open', allow_duplicate=True),
        #                    Output(prefix+'toast', 'is_open', allow_duplicate=True),
        #                    Output(prefix+'toast', 'children', allow_duplicate=True),
        #                    Output(self.counter_store_id, 'data', allow_duplicate=True),
        #                    Output(self.reset_success_trigger_id, 'data',)],
        #                    [State(self.counter_store_id, 'data'),
        #                     Input({'type': prefix+'action', 'index': ALL}, 'n_clicks')], prevent_initial_call=True)(self._cb_confirm_modal_pressed())

        self.app.callback([Output('page_content', 'children', allow_duplicate=True),
                           Output(prefix+'confirm_modal', 'is_open', allow_duplicate=True),
                           Output(self.counter_store_id, 'data', allow_duplicate=True),
                           Output(self.reset_success_trigger_id, 'data',)],
                           [State(self.counter_store_id, 'data'),
                            State('page_content', 'children'),
                            Input({'type': prefix+'action', 'index': ALL}, 'n_clicks')], prevent_initial_call=True)(self._cb_confirm_modal_pressed()) 

    # return the panel to the state page           
    def get_panel(self):
        return self.reset_db_panel
    
    # return the store id that is triggered when the reset successful   
    def get_success_trigger_id(self):
        return self.reset_success_trigger_id
        
    # callback when the reset button is pressed, and the confirm dialog is set open
    def _cb_reset_button_pressed(self):
        def cb_reset_button_pressed(reset_button):
            return (True, 0,)
        return cb_reset_button_pressed
    
    # callback when the confirm button is pressed, which then clear the database of coordinator, and open the toast for feedback
    # def _cb_confirm_modal_pressed(self):
    #     def cb_confirm_modal_pressed(counter, *args):
    #         button_id = ctx.triggered_id if ctx.triggered_id is not None else {}
    #         button_index = button_id.get('index', None)
    #         # if the confirm buttons is pressed
    #         if button_index == 'confirm':
    #             # count thrice pressing the confirm button to really confirm the reset
    #             if counter <= 1:
    #                 return (True, False, None, counter + 1, False)
    #             else:
    #                 # drop all the tables first and create them again
    #                 DETECT_DBFM.drop_tables()
    #                 error_str = DETECT_DBFM.create_tables()   
    #                 if error_str is None:
    #                     return (False, True, f'Successfully reset the database tables to a blank state', 0, True)
    #                 else:
    #                     return (False, True, f'The database tables are deleted but then error occurred when creating tables: {error_str}', 0, False)                    
    #         else:
    #             return (False, False, None, 0, False)
            
    #     return cb_confirm_modal_pressed 
    
    # callback when the confirm button is pressed, which then clear the database of coordinator, and open the toast for feedback
    # a new version that refresh the page after successful reset db
    def _cb_confirm_modal_pressed(self):
        def cb_confirm_modal_pressed(counter, page_content, args):
            button_id = ctx.triggered_id if ctx.triggered_id is not None else {}
            button_index = button_id.get('index', None)
            # if the confirm buttons is pressed
            if button_index == 'confirm' and args[0] is not None:  # the second condition checks if it is a page loading event
                # count thrice pressing the confirm button to really confirm the reset
                if counter is None:
                    counter = 0
                if counter <= 1:
                    return (page_content, True, counter + 1, False)
                else:
                    # drop all the tables first and create them again
                    DETECT_DBFM.drop_tables()
                    error_str = DETECT_DBFM.create_tables()  
                    if error_str is None:
                        return (page_content, False, 0, True)
                    else:
                        return (page_content, False, 0, False)                    
            else:
                return (page_content, False, 0, False)
        return cb_confirm_modal_pressed       