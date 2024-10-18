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
from cgras.detector.dao_detect import StatusNames
from cgras.detector.task_detection import DetectionTaskHelper
from cgras.tools.logging_tools import logger

class TileSampleTable():
    def __init__(self, app, prefix, allow_priority=True, allow_reprocess=False, allow_view=False):
        self.app = app 
        self.prefix = prefix = prefix + 'tse_'
        self.allow_priority = allow_priority
        self.allow_reprocess = allow_reprocess
        self.update_table_store_id = prefix + 'update_table_store'
        # define widgets 
        self._delete_confirm_dialog = dcc.ConfirmDialog(id=prefix+'delete_confirm_dialog',
            message='The selected tile sample(s) will be deleted! (the source image files are kept) Are you sure?',)  
        
        self._reprocess_confirm_dialog = dcc.ConfirmDialog(id=prefix+'reprocess_confirm_dialog',
            message='The results of the selected tile sample(s) will be invaliated and the sample placed in the pending queue. Are you sure?',)          
        
        self._message_alert = dbc.Alert('', id=prefix+'message_alert', dismissable=True, duration=10000,
                                 is_open=False, className='mx-auto mt-4 col-8', color='secondary')

        self._columns = [{'name': 'Tile Sample ID', 'id': 'id', 'type': 'text', 'editable': False},
                         {'name': 'Batch Time', 'id': 'batch_time', 'type': 'datetime', 'editable': False},
                         {'name': 'Importer', 'id': 'importer_id', 'type': 'text', 'editable': False},
                         {'name': 'Operator', 'id': 'operator', 'type': 'text', 'editable': False},
                         {'name': 'Create Time', 'id': 'create_time', 'type': 'text', 'editable': False},  
                         {'name': 'Status', 'id': 'status', 'type': 'text', 'editable': False},                                                 
                         ]
        
        self._datatable = dash_table.DataTable(id=prefix+'datatable', columns=self._columns, style_header={}, fill_width=True, row_selectable='multi',
                                               cell_selectable=False, row_deletable=False)

        # self._viewdata_modal = dbc.Modal([
        #             dbc.ModalHeader(dbc.ModalTitle('View processing details of a sample')),
        #             html.Div([
        #                 html.B('', id=prefix+'viewdata_modal_message'),
        #                 html.P(''),
        #                 dbc.Button('Browse the Scanned Images', target='view_capture', external_link=True,
        #                         id='dataview_scan_link', color='success',),]
        #                 , className='d-grid gap-2 col-8 mx-auto', style={'padding': '6px'})
        #                 ], id=prefix+'viewdata_modal', is_open=False)
        
        # define confirm panel in a modal
        
        self._reprocess_mode_radio = dcc.RadioItems(id=prefix+'reprocess_mode', options={
                                                '_whole': '  Redo the whole analysis (reconstruction, tile location, object detection and analysis)',
                                                '_redo_detect': '  Redo from detection (object detection and analysis)',
                                                '_redo_analysis': '  Redo analysis (only analysis)'}, value='_redo_analysis')  # style={'display': 'flex'}
        
        self._confirm_reprocess_modal = dbc.Modal(id=prefix+'confirm_reprocess_modal', children=[
                dbc.ModalHeader(dbc.ModalTitle('Re-Process Tile Samples')),
                dbc.ModalBody(children=[html.P('Select the starting point of the re-process (i.e., involves removing different cache files)', className='text-secondary'),
                                        self._reprocess_mode_radio ,
                                            html.Div(id=prefix+'confirm_modal_button_panel', children=[
                                            dbc.Button('Confirm Re-Process', id=prefix+'confirm_reprocess_button', n_clicks=0, className='me-3'), 
                                            dbc.Button('Cancel', id=prefix+'cancel_reprocess_button', n_clicks=0, color='secondary'),], 
                                        className='text-center, mt-3', style={'display': 'block'}, ),
                                        ]),
            ], size='xl', is_open=False,)  
        
        self._deletedata_modal = dbc.Modal([
                    dbc.ModalHeader(dbc.ModalTitle('Deleted a Scan Session')),
                    html.Div( [
                        html.P(id=prefix+'deletedata_modal_message'),
                            ]
                        , className='d-grid gap-2 col-8 mx-auto', style={'padding': '6px'})
                        ], id=prefix+'deletedata_modal', is_open=False)

        self._div_panel_children = [
            dbc.Button('Select All', id=prefix+'table_selectall_button', color='light', className='mb-1 me-5', size='sm', style={'width': '100px'})
        ]
        if allow_reprocess:
            self._div_panel_children.append(
                dbc.Button('Re-Process ', id=prefix+'table_reprocess_button', color='primary', className='mb-1 me-1', size='sm', style={'width': '100px'}))
        if allow_priority:
            self._div_panel_children.append(
                dbc.Button('Prioritize', id=prefix+'table_priority_button', color='primary', className='mb-1 me-1', size='sm', style={'width': '100px'}))
        if allow_view:
            self._div_panel_children.append(
                dbc.Button('Processing Details', id=prefix+'table_view_button', color='primary', className='mb-1 me-1', size='sm', style={'width': '100px'}))    
        self._div_panel_children.extend([         
            dbc.Button('Delete', id=prefix+'table_delete_button', color='danger', className='mb-1 me-1', size='sm', style={'width': '100px'}),
            dcc.Dropdown(id=prefix+'season_list_dropdown', 
                                       searchable=False, clearable=False, className='ms-2', maxHeight=80, style={'width': '200px'}),
        ])
        self._datatable_panel_children = [html.Div(self._div_panel_children, style={'display':'flex'}), 
                                          self._datatable]

        self.the_panel = html.Div([
                dbc.Row(html.Div(self._datatable_panel_children, className='p-2', style={'background-color': 'rgb(225, 225, 225)'})),
                self._message_alert,
                dcc.Store(id=self.update_table_store_id),
                dcc.Store(id=prefix+'row_delete_store'),
                dcc.Store(id=prefix+'row_priority_store'),
                dcc.Store(id=prefix+'row_reprocess_store'),
                dcc.Store(id=prefix+'row_view_store'),
                self._confirm_reprocess_modal,
                self._deletedata_modal,    
                self._delete_confirm_dialog,            
                ], style={'margin-top':'24px'})
        
        # define callback for selecting a scan and open the modal window
        # self.app.callback([Output('dataview_scan_link', 'href'), 
        #         Output('dataview_scan_link', 'style'),
        #         Output('viewdata_modal_message', 'children'),
        #         Output('viewdata_modal', 'is_open'),],
        #     [Input('row_priority_store', 'data')], prevent_initial_call=True)(self._browse_scan())
        
        self.app.callback([Output(prefix+'delete_confirm_dialog', 'displayed')],
            [Input(prefix+'row_delete_store', 'data')], prevent_initial_call=True)(self._delete_row_requested())   

        self.app.callback([Output(prefix+'confirm_reprocess_modal', 'is_open', allow_duplicate=True)],
            [Input(prefix+'row_reprocess_store', 'data')], prevent_initial_call=True)(self._reprocess_row_requested())     

        self.app.callback([Output(prefix+'message_alert', 'is_open'),
                           Output(prefix+'message_alert', 'children'),
                           Output(prefix+'confirm_reprocess_modal', 'is_open'),
                           Output(self.update_table_store_id, 'data', allow_duplicate=True)],
                        [Input(prefix+'confirm_reprocess_button', 'n_clicks'),
                        Input(prefix+'cancel_reprocess_button', 'n_clicks'),
                        State(prefix+'reprocess_mode', 'value'),
                        State(prefix+'row_reprocess_store', 'data'),
                        State(self.update_table_store_id, 'data'),], prevent_initial_call=True)(self._reprocess_row_confirmed())           
        
        self.app.callback([Output(prefix+'message_alert', 'is_open', allow_duplicate=True),
                           Output(prefix+'message_alert', 'children', allow_duplicate=True),
                           Output(self.update_table_store_id, 'data', allow_duplicate=True)],
                            [Input(prefix+'delete_confirm_dialog', 'submit_n_clicks'),
                            State(prefix+'row_delete_store', 'data'),
                            State(self.update_table_store_id, 'data'),], prevent_initial_call=True)(self._delete_row_confirmed())    
        
        self.app.callback([Output(prefix+'message_alert', 'is_open', allow_duplicate=True),
                           Output(prefix+'message_alert', 'children', allow_duplicate=True)],
                            [Input(prefix+'row_priority_store', 'data'),], prevent_initial_call=True)(self._priority_row_confirmed())        
        
        input_list = [State(prefix+'datatable', 'selected_rows'), 
                      Input(prefix+'table_delete_button', 'n_clicks')]
        if allow_reprocess:
            input_list.append(Input(prefix+'table_reprocess_button', 'n_clicks'))
        if allow_priority:
            input_list.append(Input(prefix+'table_priority_button', 'n_clicks'))
        if allow_view:
            input_list.append(Input(prefix+'table_view_button', 'n_clicks'))

        self.app.callback([Output(prefix+'row_reprocess_store', 'data'),
                           Output(prefix+'row_priority_store', 'data'),
                            Output(prefix+'row_delete_store', 'data'),
                            Output(prefix+'row_view_store', 'data'),
                            Output(prefix+'datatable', 'selected_rows', allow_duplicate=True),
                           ], input_list, prevent_initial_call=True)(self._table_button_pressed())     

        self.app.callback(Output(prefix+'datatable', 'style_data_conditional'),
                            [Input(prefix+'datatable', 'derived_viewport_selected_rows'),
                             State(prefix+'datatable', 'data')])(self._style_selected_rows())
        
        self.app.callback([Output(self.prefix+'datatable', 'data')],
            [Input(self.update_table_store_id, 'data'),
             Input(self.prefix+'season_list_dropdown', 'value')], prevent_initial_call=True, allow_duplicate=True)(self._update_datatable())       
        
        self.app.callback([Output(self.prefix+'datatable', 'selected_rows')],
            [Input(self.prefix+'table_selectall_button', 'n_clicks'),
             State(self.prefix+'datatable', 'data'),
             State(self.prefix+'datatable', 'selected_rows')], prevent_initial_call=True, allow_duplicate=True)(self._selectall_button_pressed())               
    
    def register_trigger(self, trigger_id:str):
        # define callbacks for the datatable data
        self.app.callback([Output(self.update_table_store_id, 'data', allow_duplicate=True)],
            [Input(trigger_id, 'data')], prevent_initial_call=True, allow_duplicate=True)(self._update_panel())

        self.app.callback([Output(self.prefix+'season_list_dropdown', 'options', allow_duplicate=True),
                            Output(self.prefix+'season_list_dropdown', 'value', allow_duplicate=True)],
                         [Input(trigger_id, 'data'),], prevent_initial_call=True)(self._update_season_dropdown())  
        
    def get_panel(self):
        return self.the_panel
    
    def get_default_datatable_model(self, season_title):
        model = DETECT_DAO.list_tile_samples(season_title=season_title, status=StatusNames.PENDING.value)
        return model
    
    def refine_datatable_model(self, model, show_column_top=True, show_column_refresh=False):
        model['status'] = model['status'].apply(lambda x: StatusNames(x).name) 
        model = model[['id', 'batch_time', 'importer_id', 'operator', 'create_time', 'status']]
        return model
    
    # the callback for updating the datatable
    def _update_datatable(self):
        def update_datatable(store, season_title):
            # if the store contains a dict, a query triggers table refresh 
            if isinstance(store, list): 
                store.insert(0, season_title)
                self._model = DETECT_DAO.query_processed_tile_samples(*store)
            else:
                self._model = self.get_default_datatable_model(season_title)
            self._model = self.refine_datatable_model(self._model, self.allow_priority, self.allow_reprocess)
            return (self._model.to_dict('records'),)
        return update_datatable
    
    def _update_season_dropdown(self):
        def update_season_dropdown(tile_id):
            # get options for the dropdown
            options = DETECT_DAO.list_seasons_in_tile_sample()
            value = options[0] if options is not None and len(options) > 0 else None
            return (options, value,)
        return update_season_dropdown
    
    def _table_button_pressed(self): 
        def table_button_pressed(selected_rows:list, *args):
            if selected_rows is None or len(selected_rows) == 0:
                raise PreventUpdate
            row_index_list = list(selected_rows)
            button_id = ctx.triggered_id if not None else 'No clicks yet'
            # logger.warning(f'table button: {row_index_list} {button_id}')
            if button_id.endswith('table_reprocess_button'):
                return (row_index_list, None, None, None, [])
            elif button_id.endswith('table_priority_button'):
                return (None, row_index_list, None, None, [])
            elif button_id.endswith('table_delete_button'):
                return (None, None, row_index_list, None, [])     
            elif button_id.endswith('table_view_button'):
                return (None, None, None, row_index_list, [])        
            return (None, None, None, None, [])
        return table_button_pressed 

    def _delete_row_requested(self): 
        def delete_row_clicked(row_index_list):
            if row_index_list is None:
                raise PreventUpdate        
            return (True,)  
        return delete_row_clicked 

    def _delete_row_confirmed(self): 
        def delete_row_confirmed(submit_n_clicks, row_index_list, store):
            if submit_n_clicks:
                for row_index in row_index_list:
                    id = self._model.iloc[row_index]['id']
                    DETECT_DAO.delete_tile_sample(id)
                message = f'The tile sample(s) {row_index_list} deleted'
                return (True, message, store)
            return (False, '', store)
        return delete_row_confirmed 

    def _reprocess_row_requested(self): 
        def reprocess_row_requested(row_index_list):
            if row_index_list is None:
                raise PreventUpdate        
            return (True,)  
        return reprocess_row_requested 

    def _reprocess_row_confirmed(self): 
        def reprocess_row_confirmed(confirm_button, cancel_button, mode, row_index_list, store):
            button_id = ctx.triggered_id if not None else 'No clicks yet'
            if button_id.endswith('confirm_reprocess_button'):
                for row_index in row_index_list:
                    id = self._model.iloc[row_index]['id']
                    DETECT_DAO.update_tile_sample_status(id, StatusNames.PENDING.value)
                    # remove the cache files
                    if mode == '_whole':
                        DetectionTaskHelper.delete_cache_files(id, delete_reco=True, delete_object_detection=True)
                    elif mode == '_redo_detect':
                        DetectionTaskHelper.delete_cache_files(id, delete_reco=True, delete_object_detection=False)
                    elif mode == '_redo_analysis':
                        ...
                message = f'The tile sample(s) {row_index_list} moved to the pending queue'
                return (True, message, False, store)
            return (False, ' ', False, store) 
        return reprocess_row_confirmed 

    def _priority_row_confirmed(self): 
        def priority_row_confirmed(row_index_list):
            if row_index_list is None:
                raise PreventUpdate
            for row_index in row_index_list:
                id = self._model.iloc[row_index]['id']
                DETECT_DAO.set_top_priority(id)
            message = f'The tile sample(s) {row_index_list} moved to the top priority'
            return (True, message) 
        return priority_row_confirmed 
    
    def _style_selected_rows(self):
        def style_selected_rows(row_index_list, model):
            if row_index_list is None:
                return dash.no_update
            style_data_conditional = [
                {"if": {"filter_query": "{{id}} ={}".format(model[i]['id'])}, "backgroundColor": "yellow",}
                for i in row_index_list
            ]
            return style_data_conditional
        return style_selected_rows
    
    def _selectall_button_pressed(self): 
        def selectall_button_pressed(selectall_button, model, selected_rows):
            logger.warning(f'_selectall: {selectall_button, len(model), selected_rows}')
            if selectall_button is None:
                raise PreventUpdate
            if selected_rows is not None and len(selected_rows) == len(model):
                selected_rows = []
            else:
                selected_rows = [index for index in range(len(model))]
            return (selected_rows,)  
        return selectall_button_pressed     
    

    def _update_panel(self): 
        def update_panel(store):
            if store is None:
                raise PreventUpdate        
            return (store,)  
        return update_panel 