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
from detector.model import DETECT_DAO, CONFIG, SystemConfigNames
from tools.logging_tools import logger

class YoloModelTable():
    def __init__(self, app, prefix):
        self.app = app 
        self.prefix = prefix = prefix + 'ymet_'
        self.default_max_end_day = CONFIG.get(SystemConfigNames.MAX_CORAL_AGE)
        self.updated_success_trigger_id = prefix + 'updated_datatable_trigger'
        # model variable
        # define widgets 
        self._delete_confirm_dialog = dcc.ConfirmDialog(id=prefix+'delete_confirm_dialog',
            message='Are you sure to delete the model?',)  
        
        self._message_alert = dbc.Alert('', id=prefix+'message_alert', duration=3000, is_open=False, className='mx-auto mt-4 col-8', color='primary')
        
        self._model, self._model_column = self.get_default_datatable_model()
        self._datatable = dash_table.DataTable(data=self._model, columns=self._model_column,
                                               id=prefix+'datatable', style_header={}, fill_width=True, 
                                               cell_selectable=False, row_selectable='multi')
        
        model_name_label = dbc.Row([dbc.Label('Model Name:', width=2), dbc.Label(id=prefix+'name_label', width=10), ])
        model_file_label = dbc.Row([dbc.Label('Model File:', width=2), dbc.Label(id=prefix+'file_label', width=10), ])
        model_coral_class_label = dbc.Row([dbc.Label('Coral Classes:', width=2), dbc.Label(id=prefix+'coral_classes_label', width=10), ])
        model_dead_coral_class_label = dbc.Row([dbc.Label('Dead Coral Classes:', width=2), dbc.Label(id=prefix+'dead_coral_classes_label', width=10), ])
        
        species_input = dbc.Row([
            dbc.Label('Species', html_for=prefix+'species_input', width=2),
            dbc.Col(dbc.Input(type='text', id=prefix+'species_input', placeholder='Enter coral species name'), width=10),
        ], className='mb-3',)
        
        range_input = dbc.Row([
            dbc.Label('Applicable Period', html_for=prefix+'range_input', width=2),
            dbc.Col(dcc.RangeSlider(0, self.default_max_end_day, value=[0, self.default_max_end_day], id=prefix+'range_input', marks={
                        0: {'label': 'Start', 'style': {'color': '#77b0b1'}},
                        21: {'label': '21'},
                        42: {'label': '42'},
                        63: {'label': '63'},
                        self.default_max_end_day: {'label': 'End', 'style': {'color': '#f50'}}
                    }, tooltip={"placement": "bottom", "always_visible": True}))
        ])
        
        define_yolo_model_form = dbc.Form([model_name_label, model_file_label, model_coral_class_label, model_dead_coral_class_label, species_input, range_input]) 
                
        self._editdata_modal = dbc.Modal(id=prefix+'edit_modal', children=[
                dbc.ModalHeader(dbc.ModalTitle(children='Edit Model Attributes',)),
                dbc.ModalBody(children=[html.P(id=prefix+'edit_modal_textbox', className='text-danger'),
                                        html.P('Make the changes and Press Confirm', className='mb-3', style={}),
                                        define_yolo_model_form,
                                        html.Div(children=[
                                            dbc.Button('Confirm', id=prefix+'edit_confirm_button', n_clicks=0, className='me-3'), 
                                            dbc.Button('Cancel', id=prefix+'edit_cancel_button', n_clicks=0, color='secondary'),], 
                                        className='text-center, mt-3', style={'display': 'block'}),
                                        ]),
            ], size='xl', is_open=False,)  

        self._datatable_title = dbc.Row(html.Div([
                        html.Span('⬇️', className='col-6 text-center'),
                        html.H6([dbc.Badge('YOLO MODELS', color='white', text_color='primary'), 
                        html.Span(id=prefix+'datatable_title')]),
                    ], className='mx-auto text-center')),

        self.the_panel = html.Div([
                dbc.Row(html.Div([
                    dbc.Button('Modify', id=prefix+'table_edit_button', n_clicks=0, color='secondary', className='mb-1 me-1', size='sm'), 
                    dbc.Button('Delete', id=prefix+'table_delete_button', n_clicks=0, color='danger', className='mb-1', size='sm'),
                    self._datatable], className='p-2', style={'background-color': 'rgb(225, 225, 225)'})),
                self._message_alert,
                dcc.Store(id=prefix+'row_edit_store'),
                dcc.Store(id=prefix+'row_delete_store'),
                dcc.Store(id=prefix+'update_datatable_trigger'),
                dcc.Store(id=self.updated_success_trigger_id),
                self._editdata_modal,    
                self._delete_confirm_dialog,            
                ], style={'margin-top':'24px'})
                
        # self.app.callback([Output(prefix+'delete_confirm_dialog', 'displayed'),
        #                    Output(prefix+'row_edit_store', 'data'),],
        #     [Input(prefix+'datatable', 'active_cell')], prevent_initial_call=True)(self._cell_clicked())    
    
        self.app.callback([Output(prefix+'edit_modal', 'is_open', allow_duplicate=True),
                           Output(prefix+'name_label', 'children'),
                           Output(prefix+'file_label', 'children'),
                           Output(prefix+'coral_classes_label', 'children'),
                           Output(prefix+'dead_coral_classes_label', 'children'),
                           Output(prefix+'species_input', 'value'),
                           Output(prefix+'range_input', 'value'),],
            [Input(prefix+'row_edit_store', 'data')], prevent_initial_call=True)(self._edit_row_received())    

        self.app.callback([Output(prefix+'message_alert', 'is_open'),
                           Output(prefix+'message_alert', 'children'),
                           Output(prefix+'edit_modal', 'is_open', allow_duplicate=True),
                           Output(self.prefix+'update_datatable_trigger', 'data', allow_duplicate=True),
                           Output(self.updated_success_trigger_id, 'data', allow_duplicate=True),],
                        [Input(prefix+'edit_confirm_button', 'n_clicks'),
                        Input(prefix+'edit_cancel_button', 'n_clicks'),
                        State(prefix+'species_input', 'value'),
                        State(prefix+'range_input', 'value'),
                        State(prefix+'row_edit_store', 'data')], prevent_initial_call=True)(self._edit_row_confirmed()) 
        
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
                           Output(prefix+'row_edit_store', 'data'),
                           Output(prefix+'row_delete_store', 'data'),
                            Output(prefix+'datatable', 'selected_rows', allow_duplicate=True),
                           ],
                        [Input(prefix+'table_edit_button', 'n_clicks'),
                        Input(prefix+'table_delete_button', 'n_clicks'),
                        State(prefix+'datatable', 'data'),
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
        model = DETECT_DAO.list_yolo_model()
        model['Period'] = model.apply(lambda row: DETECT_DAO.get_period_str(row['start_day'], row['end_day']), axis=1)
        model['Input Image Size'] = model.apply(lambda row: f'{row["input_image_width"]} x {row["input_image_height"]}', axis=1)
        model = model[['id', 'name', 'species', 'Period', 'Input Image Size']]
        model.columns = ['ID', 'Model Name', 'Species', 'Period', 'Input Image Size']
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
        def table_button_pressed(table_edit_button, table_delete_button, model, selected_rows:list):
            if selected_rows is None or len(selected_rows) == 0:
                raise PreventUpdate
            row_index = selected_rows[0]
            name = model[row_index]['Model Name']
            data = DETECT_DAO.get_yolo_model(name)
            button_id = ctx.triggered_id if not None else 'No clicks yet'
            if button_id.endswith('table_edit_button'):
                return (False, data, None, [])  
            elif button_id.endswith('table_delete_button'):   
                return (True, None, row_index, [])        
            return (False, None, None, [])
        return table_button_pressed 
    
    def _edit_row_received(self): 
        def edit_row_received(row):
            if row is None:
                raise PreventUpdate
            start_day, end_day = row['start_day'], row['end_day']
            if end_day is None or end_day < 0:
                end_day = self.default_max_end_day
            return (True, row['name'], row['model_file_path'], ' '.join(row['coral_classes']), ' '.join(row['dead_coral_classes']), row['species'], (start_day, end_day,),)
        return edit_row_received     

    def _edit_row_confirmed(self): 
        def edit_row_confirmed(confirm_button, cancel_button, species, range, row):
            button_id = ctx.triggered_id if not None else 'No clicks yet'
            if button_id.endswith('confirm_button'):
                start_day, end_day = range
                end_day = -1 if end_day >= self.default_max_end_day else end_day
                result = DETECT_DAO.update_yolo_model(row['name'], species, start_day, end_day)
                if result:
                    message = 'Update yolo model successful'
                    return (True, message, False, True, True) 
                else:
                    message = 'Update yolo model failed'
                    return (True, message, False, True, False) 
            elif button_id.endswith('cancel_button'):
                return (False, ' ', False, True, False) 
        return edit_row_confirmed  

    def _delete_row_confirmed(self): 
        def delete_row_confirmed(submit_n_clicks, cancel_n_clicks, rows_previous, model_dict, row_index):
            if submit_n_clicks:
                DETECT_DAO.delete_yolo_model(model_dict[row_index]['Model Name'])
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
                {"if": {"filter_query": "{{ID}} = '{}'".format(model[i]['ID'])}, "backgroundColor": "yellow",}
                for i in selected_rows
            ]
            return (style_data_conditional, selected_rows,)
        return style_selected_rows