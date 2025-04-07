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
from dash import html, dcc, Input, Output, State, dash_table, ctx, ALL
import dash_bootstrap_components as dbc
from dash.dash_table.Format import Format, Padding
from dash.exceptions import PreventUpdate
from detector.model import DETECT_DAO
from cgras_datatools.logging_tools import logger

class HealthModelTable():
    def __init__(self, app, prefix):
        self.app = app 
        self.prefix = prefix = prefix + 'hmet_'
        self.updated_success_trigger_id = prefix + 'updated_datatable_trigger'
        # model variable
        self.current_selected_row = None
        # define the modal for confirmation of user actions
        self._user_confirm_modal = dbc.Modal([
                    dbc.ModalHeader(dbc.ModalTitle(id=prefix+'confirm_modal_title')),
                    html.Div([html.P(id=prefix+'confirm_modal_message'),
                                dbc.Button('Confirm', id={'type': prefix+'action', 'index': 'confirm'},), 
                                dbc.Button('Cancel', id={'type': prefix+'action', 'index': 'cancel'}, color='secondary')
                            ]
                        , className='d-grid gap-2 col-8 mx-auto', style={'padding': '6px'})
                        ], id=prefix+'confirm_modal', is_open=False)
        
        # define a toast for feedback  
        self._toast = dbc.Toast(id=prefix+'toast', is_open=False, duration=5000, icon='primary', header='Message',
                                style={'position': 'fixed', 'top': '50%', 'left': '30%', 'width': 480, 'transform': 'translate(-50%, -50%)'})
        
        self._model, self._model_column = self.get_default_datatable_model()
        self._datatable = dash_table.DataTable(data=self._model, columns=self._model_column,
                                               id=prefix+'datatable', style_header={}, fill_width=True, 
                                               cell_selectable=False, row_selectable='multi')

        self._datatable_title = dbc.Row(html.Div([
                        html.Span('⬇️', className='col-6 text-center'),
                        html.H6([dbc.Badge('HEALTH MODELS', color='white', text_color='primary'), 
                        html.Span(id=prefix+'datatable_title')]),
                    ], className='mx-auto text-center')),

        species_label = dbc.Row([dbc.Label('Species:', width=2), dbc.Label(id=prefix+'species_label', width=10), ])
        func_name_label = dbc.Row([dbc.Label('Function Name:', width=2), dbc.Label(id=prefix+'func_name_label', width=10), ])     
        func_def_label =  dbc.Row([dcc.Textarea(id=prefix+'func_def_label', style={'width': '100%', 'height': 300, 'font-family': 'courier'}, )])       
              
        health_model_form = dbc.Form([species_label, func_name_label, func_def_label]) 
                
        self._viewdata_modal = dbc.Modal(id=prefix+'view_modal', children=[
                dbc.ModalHeader(dbc.ModalTitle(children='Health Model',)),
                dbc.ModalBody(children=[html.P(id=prefix+'edit_modal_textbox', className='text-danger'),
                                        html.P('Make the changes and Press Confirm', className='mb-3', style={}),
                                        health_model_form,
                                        ]),
            ], size='xl', is_open=False,)  

        self.the_panel = html.Div([
                dbc.Row(html.Div([
                    dbc.Button('View', id={'type': prefix+'table', 'index': 'view'}, n_clicks=0, color='secondary', className='mb-1 me-1', size='sm'), 
                    dbc.Button('Delete', id={'type': prefix+'table', 'index': 'delete'}, n_clicks=0, color='danger', className='mb-1', size='sm'),
                    self._datatable], className='p-2', style={'background-color': 'rgb(225, 225, 225)'})),
                dcc.Store(id=prefix+'row_view_store'),
                dcc.Store(id=prefix+'row_delete_store'),
                dcc.Store(id=prefix+'update_datatable_trigger'),
                dcc.Store(id=self.updated_success_trigger_id),
                self._toast,
                self._viewdata_modal,
                self._user_confirm_modal,         
                ], style={'margin-top':'24px'}) 

        self.app.callback([Output(prefix+'view_modal', 'is_open', allow_duplicate=True),
                           Output(prefix+'species_label', 'children'),
                           Output(prefix+'func_name_label', 'children'),
                           Output(prefix+'func_def_label', 'value'),
                           ],
                        [Input(prefix+'row_view_store', 'data')], prevent_initial_call=True)(self._view_row_received())   

        self.app.callback([Output(prefix+'confirm_modal', 'is_open', allow_duplicate=True),
                            Output(prefix+'datatable', 'data', allow_duplicate=True),
                            Output(self.updated_success_trigger_id, 'data', allow_duplicate=True),
                           ],
                            [State(prefix+'datatable', 'data_previous'),
                            State(prefix+'datatable', 'data'),
                            State(prefix+'row_delete_store', 'data'),
                            Input({'type': prefix+'action', 'index': ALL}, 'n_clicks')], prevent_initial_call=True)(self._delete_row_confirmed())   
        
        self.app.callback([Output(self.prefix+'datatable', 'data'),
                           Output(self.prefix+'datatable', 'columns'),
                           Output(self.updated_success_trigger_id, 'data', allow_duplicate=True),],
                        [Input(self.prefix+'update_datatable_trigger', 'data')], prevent_initial_call=True, allow_duplicate=True)(self._update_datatable())
          
        
        self.app.callback([Output(prefix+'confirm_modal', 'is_open', allow_duplicate=True),
                            Output(prefix+'confirm_modal_title', 'children'),
                            Output(prefix+'confirm_modal_message', 'children'),
                           Output(prefix+'row_view_store', 'data'),
                           Output(prefix+'row_delete_store', 'data'),
                           Output(prefix+'datatable', 'selected_rows', allow_duplicate=True)],
                        [State(prefix+'datatable', 'selected_rows'),
                         Input({'type': prefix+'table', 'index': ALL}, 'n_clicks')], prevent_initial_call=True)(self._table_button_pressed())   

        self.app.callback([Output(prefix+'datatable', 'style_data_conditional'),
                           Output(prefix+'datatable', 'selected_rows', allow_duplicate=True)],
                            [Input(prefix+'datatable', 'selected_rows'),
                             State(prefix+'datatable', 'data')], prevent_initial_call=True)(self._style_selected_rows())  

    def register_update_table_trigger(self, trigger_id:str):
        self.app.callback([Output(self.prefix+'update_datatable_trigger', 'data'),],
            [Input(trigger_id, 'data')], prevent_initial_call=False, allow_duplicate=True)(self._trigger_update_datatable())
        
    def get_updated_success_trigger_id(self):
        return self.updated_success_trigger_id
        
    def get_panel(self):
        return self.the_panel
    
    def get_default_datatable_model(self):
        model = DETECT_DAO.list_health_model()
        model = model[['species', 'func_name']]
        model.columns = ['Species', 'Function Name']
        columns = []
        for i in range(len(model.columns)):
            editable = False
            type = 'text'
            columns.append({
                'name': model.columns[i],
                'id': model.columns[i],
                'type': type,
                'editable': editable})
        return model.to_dict('records'), columns
        
    # the callback for updating the datatable
    def _update_datatable(self):
        def update_datatable(store):
            self._model, self._model_column = self.get_default_datatable_model()
            return (self._model, self._model_column, True)
        return update_datatable
    
    def _trigger_update_datatable(self):
        def trigger_update_datatable(store):
            return (store,)
        return trigger_update_datatable
            
    def _table_button_pressed(self): 
        def table_button_pressed(selected_rows:list, *args):
            if selected_rows is None or len(selected_rows) == 0:
                raise PreventUpdate
            row_index = selected_rows[0]
            name = self._model[row_index]['Species']
            data = DETECT_DAO.get_health_model(name)
            button_id = ctx.triggered_id if ctx.triggered_id is not None else {}
            button_index = button_id.get('index', None)
            if button_index.endswith('view'):   
                return (False, None, None, data, None, [])    
            elif button_index.endswith('delete'):  
                title = 'Delete the health index model'
                message = 'The selected health index model will be deleted. Are you sure?' 
                return (True, title, message, None, row_index, [])    
            return (False, None, None, [])
        return table_button_pressed 
 
    def _view_row_received(self): 
        def view_row_received(row):
            if row is None:
                raise PreventUpdate
            return (True, row['species'], row['func_name'], row['func_def'])
        return view_row_received     

    def _delete_row_confirmed(self): 
        def delete_row_confirmed(rows_previous, model_dict, row_index, *args):
            button_id = ctx.triggered_id if ctx.triggered_id is not None else {}
            button_index = button_id.get('index', None)
            if button_index == 'confirm':
                DETECT_DAO.delete_health_model(model_dict[row_index]['Species'])
                del model_dict[row_index]
                return (False, model_dict, True)
            else:
                return (False, model_dict, False)
        return delete_row_confirmed 

    def _style_selected_rows(self):
        def style_selected_rows(selected_rows, model):
            if selected_rows is None:
                return dash.no_update
            if len(selected_rows) >= 2:
                selected_rows.pop(0)   # assume that the new row is added to the end of the selected_row list

            style_data_conditional = [
                {"if": {"filter_query": "{{Species}} = '{}'".format(model[i]['Species'])}, "backgroundColor": "yellow",}
                for i in selected_rows
            ]
            return (style_data_conditional, selected_rows,)
        return style_selected_rows