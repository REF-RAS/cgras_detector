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
from dash.exceptions import PreventUpdate
from cgras.detector.model import DETECT_DAO
from cgras.tools.logging_tools import logger

class YoloModelEditTable():
    def __init__(self, app, prefix, show_column_top=False, show_column_refresh=False):
        self.app = app 
        self.prefix = prefix = prefix + 'ymet_'
        self.show_column_top = show_column_top
        self.show_column_refresh = show_column_refresh
        # define widgets 
        self._delete_confirm_dialog = dcc.ConfirmDialog(id=prefix+'delete_confirm_dialog',
            message='Are you sure to delete the model?',)  
        
        self._message_alert = dbc.Alert('', id=prefix+'message_alert', dismissable=True, duration=10000,
                                 is_open=False, className='mx-auto mt-4 col-8', color='danger')
        
        
        self._model, self._model_column = self.get_default_datatable_model()
        self._datatable = dash_table.DataTable(data=self._model, columns=self._model_column,
                                               id=prefix+'datatable', style_header={}, fill_width=True, editable=True, row_deletable=True)

        self._viewdata_modal = dbc.Modal([
                    dbc.ModalHeader(dbc.ModalTitle('Selected a Scan')),
                    html.Div([
                        html.B('', id=prefix+'viewdata_modal_message'),
                        html.P('Choose one of the following options or click the cross to exit.'),
                        dbc.Button('Browse the Scanned Images', target='view_capture', external_link=True,
                                id='dataview_scan_link', color='success',),]
                        , className='d-grid gap-2 col-8 mx-auto', style={'padding': '6px'})
                        ], id=prefix+'viewdata_modal', is_open=False
                )
        
        self._deletedata_modal = dbc.Modal([
                    dbc.ModalHeader(dbc.ModalTitle('Deleted a Scan Session')),
                    html.Div( [
                        html.P(id=prefix+'deletedata_modal_message'),
                            ]
                        , className='d-grid gap-2 col-8 mx-auto', style={'padding': '6px'})
                        ], id=prefix+'deletedata_modal', is_open=False
                )

        self._datatable_title_message = html.Span(id=prefix+'datatable_title')

        self._datatable_title = dbc.Row(html.Div([
                        html.Span('⬇️', className='col-6 text-center'),
                        html.H6([dbc.Badge('YOLO MODELS', color='white', text_color='primary'), self._datatable_title_message]),
                    ], className='mx-auto text-center')),

        self.the_panel = html.Div([
                dbc.Row(html.Div(self._datatable)),
                self._message_alert,
                dcc.Store(id=prefix+'row_delete_store'),
                self._viewdata_modal,
                self._deletedata_modal,    
                self._delete_confirm_dialog,            
                ], style={'margin-top':'24px'})
                
        self.app.callback([Output(prefix+'delete_confirm_dialog', 'displayed')],
            [Input(prefix+'row_delete_store', 'data')], prevent_initial_call=True)(self._delete_row_clicked())        
        
        self.app.callback([Output(prefix+'datatable', 'data', allow_duplicate=True),
                           Output(prefix+'delete_confirm_dialog', 'submit_n_clicks'),
                            Output(prefix+'delete_confirm_dialog', 'cancel_n_clicks'),
                           ],
                            [Input(prefix+'delete_confirm_dialog', 'submit_n_clicks'),
                             Input(prefix+'delete_confirm_dialog', 'cancel_n_clicks'),
                            State(prefix+'datatable', 'data_previous'),
                            State(prefix+'datatable', 'data'),
                            State(prefix+'row_delete_store', 'data'),], prevent_initial_call=True)(self._delete_row_confirmed())
      
        # self.app.callback([Output(prefix+'row_top_store', 'data'),
        #                    Output(prefix+'row_delete_store', 'data'),
        #                     Output(prefix+'datatable', 'active_cell'),
        #                     Output(prefix+'datatable', 'selected_cells')],
        #     [Input(prefix+'datatable', 'active_cell')], prevent_initial_call=True)(self._row_selected())
        
        self.app.callback([Output(prefix+'row_delete_store', 'data'),
                           Output(prefix+'message_alert', 'is_open', allow_duplicate=True),
                           Output(prefix+'message_alert', 'children', allow_duplicate=True),],
                            [Input(prefix+'datatable', 'data_previous'),
                             State(prefix+'datatable', 'data'),
                             State(prefix+'datatable', 'active_cell')], prevent_initial_call=True)(self._table_edited())        

    def register_trigger(self, trigger_id:str):
        self.app.callback([Output(self.prefix+'datatable', 'data'),
                           Output(self.prefix+'datatable', 'columns'),],
            [Input(trigger_id, 'data')], prevent_initial_call=False, allow_duplicate=True)(self._update_datatable())
        
    def get_panel(self):
        return self.the_panel
    
    def get_default_datatable_model(self):
        model = DETECT_DAO.list_yolo_model()
        model = model[['id', 'name', 'species', 'start_day', 'end_day']]
        model.columns = ['ID', 'Model Name', 'Species', 'Start Day', 'End Day']
        columns = []
        for i in range(len(model.columns)):
            editable = model.columns[i] not in ['ID']
            columns.append({
                'name': model.columns[i],
                'id': model.columns[i],
                'editable': editable})
        return model.to_dict('records'), columns
        
    # the callback for updating the datatable
    def _update_datatable(self):
        def update_datatable(store):
            self._model, self._model_column = self.get_default_datatable_model()
            return (self._model, self._model_column)
        return update_datatable
    
    def _row_selected(self):
        def row_selected(active_cell):
            if active_cell:
                col = active_cell['column']
                row = active_cell['row']
                col_title = active_cell['column_id']
                if self._model.iloc[row, col] == '❌':  # delete 
                    return -1, row, None, []    
                else:
                    return -1, -1, active_cell, [active_cell]            
            return -1, -1, None, []
        return row_selected
    
    def _table_edited(self):
        def table_edited(rows_previous, rows, active_cell):
            if rows_previous is not None and len(rows_previous) != len(rows):
                # a row has been deleted
                row_deleted = [row for row in rows_previous if row not in rows]
                logger.info(f'row_deleted: {row_deleted}')
                return (row_deleted[0], False, None)
            logger.info(f'cell_edited: {rows} {active_cell}')
            return (None, False, None)
        return table_edited
    
    def _delete_row_clicked(self): 
        def delete_row_clicked(row):
            print(f'_delete_row_clicked: {row}')
            if row is None:
                raise PreventUpdate        
            return (True,)  
        return delete_row_clicked 

    def _delete_row_confirmed(self): 
        def delete_row_confirmed(submit_n_clicks, cancel_n_clicks, rows_previous, rows, the_row):
            print(f'submit: {submit_n_clicks}')
            if submit_n_clicks:
                DETECT_DAO.delete_yolo_model(the_row['Model Name'])
                return (rows, 0, 0)
            elif cancel_n_clicks:
                print(f'rows_previous: {rows_previous}')
                return (rows_previous, 0, 0)
        return delete_row_confirmed 
    
    def _top_row_confirmed(self): 
        def top_row_confirmed(row):
            if row >= 0:
                id = self._model.iloc[row]['Tile Sample ID']
                DETECT_DAO.set_top_priority(id)
                message = f'The tile sample {id} is moved to the top priority'
                return (True, message) 
            return (False, '')
        return top_row_confirmed 