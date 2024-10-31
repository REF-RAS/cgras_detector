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
from dash import html, dcc, Input, Output, State, dash_table, ctx
import dash_bootstrap_components as dbc
from dash.dash_table.Format import Format, Padding
from dash.exceptions import PreventUpdate
from detector.model import DETECT_DAO
from tools.logging_tools import logger

class HealthModelTable():
    def __init__(self, app, prefix):
        self.app = app 
        self.prefix = prefix = prefix + 'hmet_'
        self.updated_success_trigger_id = prefix + 'updated_datatable_trigger'
        # model variable
        self.current_selected_row = None
        # define widgets 
        self._delete_confirm_dialog = dcc.ConfirmDialog(id=prefix+'delete_confirm_dialog',
            message='Are you sure to delete the model?',)  
        
        self._message_alert = dbc.Alert('', id=prefix+'message_alert', duration=3000, is_open=False, className='mx-auto mt-4 col-8', color='primary')
        
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
                    dbc.Button('View', id=prefix+'table_view_button', n_clicks=0, color='secondary', className='mb-1 me-1', size='sm'), 
                    dbc.Button('Delete', id=prefix+'table_delete_button', n_clicks=0, color='danger', className='mb-1', size='sm'),
                    self._datatable], className='p-2', style={'background-color': 'rgb(225, 225, 225)'})),
                self._message_alert,
                dcc.Store(id=prefix+'row_view_store'),
                dcc.Store(id=prefix+'row_delete_store'),
                dcc.Store(id=prefix+'update_datatable_trigger'),
                dcc.Store(id=self.updated_success_trigger_id),
                self._viewdata_modal,
                self._delete_confirm_dialog,            
                ], style={'margin-top':'24px'}) 

        self.app.callback([Output(prefix+'view_modal', 'is_open', allow_duplicate=True),
                           Output(prefix+'species_label', 'children'),
                           Output(prefix+'func_name_label', 'children'),
                           Output(prefix+'func_def_label', 'value'),
                           ],
                        [Input(prefix+'row_view_store', 'data')], prevent_initial_call=True)(self._view_row_received())   

        self.app.callback([Output(prefix+'datatable', 'data', allow_duplicate=True),
                           Output(prefix+'delete_confirm_dialog', 'submit_n_clicks'),
                            Output(prefix+'delete_confirm_dialog', 'cancel_n_clicks'),
                            Output(self.updated_success_trigger_id, 'data', allow_duplicate=True),
                           ],
                            [Input(prefix+'delete_confirm_dialog', 'submit_n_clicks'),
                             Input(prefix+'delete_confirm_dialog', 'cancel_n_clicks'),
                            State(prefix+'datatable', 'data_previous'),
                            State(prefix+'datatable', 'data'),
                            State(prefix+'row_delete_store', 'data'),], prevent_initial_call=True)(self._delete_row_confirmed())   
        
        self.app.callback([Output(self.prefix+'datatable', 'data'),
                           Output(self.prefix+'datatable', 'columns'),
                           Output(self.updated_success_trigger_id, 'data', allow_duplicate=True),],
                        [Input(self.prefix+'update_datatable_trigger', 'data')], prevent_initial_call=True, allow_duplicate=True)(self._update_datatable())
          
        
        self.app.callback([Output(prefix+'delete_confirm_dialog', 'displayed'),
                           Output(prefix+'row_view_store', 'data'),
                           Output(prefix+'row_delete_store', 'data'),
                           Output(prefix+'datatable', 'selected_rows', allow_duplicate=True)],
                        [Input(prefix+'table_view_button', 'n_clicks'),
                         Input(prefix+'table_delete_button', 'n_clicks'),
                        State(prefix+'datatable', 'selected_rows')], prevent_initial_call=True)(self._table_button_pressed())   

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
        def table_button_pressed(table_view_button, table_delete_button, selected_rows:list):
            if selected_rows is None or len(selected_rows) == 0:
                raise PreventUpdate
            row_index = selected_rows[0]
            name = self._model[row_index]['Species']
            data = DETECT_DAO.get_health_model(name)
            button_id = ctx.triggered_id if not None else 'No clicks yet'
            if button_id.endswith('table_view_button'):   
                return (False, data, None, [])    
            elif button_id.endswith('table_delete_button'):   
                return (True, None, row_index, [])    
            return (False, None, None, [])
        return table_button_pressed 
 
    def _view_row_received(self): 
        def view_row_received(row):
            if row is None:
                raise PreventUpdate
            return (True, row['species'], row['func_name'], row['func_def'])
        return view_row_received     

    def _delete_row_confirmed(self): 
        def delete_row_confirmed(submit_n_clicks, cancel_n_clicks, rows_previous, model_dict, row_index):
            if submit_n_clicks:
                DETECT_DAO.delete_health_model(model_dict[row_index]['Species'])
                del model_dict[row_index]
                return (model_dict, 0, 0, True)
            elif cancel_n_clicks:
                return (model_dict, 0, 0, False)
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