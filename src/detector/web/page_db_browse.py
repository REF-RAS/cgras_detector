# Copyright 2024 - Andrew Kwok Fai LUI, 
# Robotics and Autonomous Systems Group, REF, RI
# and the Queensland University of Technology

__author__ = 'Andrew Lui'
__copyright__ = 'Copyright 2024'
__license__ = 'GPL'
__version__ = '1.0'
__email__ = 'ak.lui@qut.edu.au'
__status__ = 'Development'


import pandas as pd
import dash
from dash import html, dcc, callback, Input, Output, State, dash_table, ctx
import dash_bootstrap_components as dbc
from dash.exceptions import PreventUpdate 
# project modules
from tools import db_tools, type_tools
from detector.model import DETECT_DAO, AIMSTILE_DAO

dash.register_page(__name__)

class DBTableBrowsePage():
    def __init__(self, app):
        # model variables
        self.dao_map = {'Detector DB': DETECT_DAO, 'Tile DB': AIMSTILE_DAO}
        self.dao_selected = 'Detector DB'
        self.sql_list = []
        self._error_placeholder = None
        # setup the page
        self.app = app  
        self._define_page()


    def get_tablenames(self, db_name=None):
        selected_dao = self.dao_map[db_name]
        return db_tools.list_table_names(selected_dao.db_file)    

    def layout(self):
        return self._layout

    def _define_page(self):
        self.tablenames = self.get_tablenames(self.dao_selected)
        if 'accounts' in self.tablenames:
            self.tablenames.remove('accounts') 
        self._datatable = dash_table.DataTable(id='db_display_table', page_current=0, page_size=100, page_action='custom', cell_selectable=False, row_selectable=False,
                                                style_cell={
                                                    'overflow': 'hidden',
                                                    'textOverflow': 'ellipsis',
                                                    # 'maxWidth': 0
                                                })
        # the placeholders
        self._error_placeholder = html.Div(id='error_div', className='col-12')
        self._dropdown_placeholder = html.Div(className='col-12')
        self._sql_dropdown = dcc.Dropdown(self.sql_list, id='sql_list_dropdown', searchable=False, clearable=False)
        self._dropdown_placeholder.children = self._sql_dropdown
        # the left panel
        browse_db_panel = dbc.Col([
            dbc.Row(html.H4(children = 'Browse DB Tables', className='mt-3 mb-3')),
            
            dbc.Row([dbc.Col(dcc.Dropdown(list(self.dao_map.keys()), self.dao_selected, id='db_display_dblist_dropdown', 
                                          clearable=False, className='col-12 d-inline-block')
                             , className='col-12')]),
            
            dbc.Row([dbc.Col(dcc.Dropdown(self.tablenames, '', id='db_display_tablelist_dropdown', clearable=False, className='col-12 d-inline-block')
                             , className='col-12'),
                    dbc.Col(dbc.Button('Refresh', id='db_display_table_refresh', n_clicks=0))]),
        ], className='col-3')
        # the right panel
        query_db_panel = dbc.Col([
            dbc.Row(html.H4(children = 'Query DB Tables', className='mt-3 mb-3')),
            dbc.Row(self._dropdown_placeholder, className='mb-2'),
            dbc.Row([dbc.Col(dcc.Input(id='db_query_textbox_input', type='text', placeholder='SQL', className='col-12 d-inline-block'), 
                             className='col-10'),
                    dbc.Col([dbc.Button('Query', id='db_query_button', n_clicks=0, className='me-3'), dbc.Button('Update', id='db_update_button', n_clicks=0)])]),
        ], className='col-9')

        rows = html.Div(children = [
            dbc.Row(html.H3(children = 'Danger Zone (REF Research Engineers Only)', className='text-center mt-5 mb-3 text-danger')),
            dbc.Row([browse_db_panel, query_db_panel]),
            dbc.Row(self._error_placeholder),
            dbc.Row([html.Div(html.H6(dbc.Badge('TABLE CONTENT', color='white', text_color='primary'))),
                html.Div(self._datatable)
            ], id='db_display_table_div', style={'display': 'none'})
        ])
        self._layout = dbc.Container(rows, fluid=True) 
        # define callback for the table select dropdown
        self.app.callback(Output('db_display_table', 'data', allow_duplicate=True),
                          Output('db_display_table_div', 'style', allow_duplicate=True),
                            [
                            Input('db_display_table_refresh', 'n_clicks'),
                            Input('db_display_tablelist_dropdown', 'value'),
                            State('db_display_dblist_dropdown', 'value'),
                            Input('db_display_table', "page_current"),
                            Input('db_display_table', "page_size")
                            ], prevent_initial_call=True)(self._update_table_browse())
        # define callback for the db file select dropdown
        self.app.callback(Output('db_display_tablelist_dropdown', 'options'),
                            [
                            Input('db_display_dblist_dropdown', 'value'),
                            ], prevent_initial_call=True)(self._update_dblist())

        # define callback for query and update buttons
        self.app.callback([Output('db_display_table', 'data', allow_duplicate=True),
                           Output('db_display_table_div', 'style', allow_duplicate=True),
                           Output('sql_list_dropdown', 'options'),
                           Output('error_div', 'children'),],
                            [
                            Input('db_query_button', 'n_clicks'),
                            Input('db_update_button', 'n_clicks'),
                            State('db_query_textbox_input', 'value'),
                            State('db_display_dblist_dropdown', 'value'),
                            Input('db_display_table', 'page_current'),
                            Input('db_display_table', 'page_size')
                            ], prevent_initial_call=True)(self._update_table_query())   
        
        # define callback for the sql list dropdown
        self.app.callback(Output('db_query_textbox_input', 'value'),
                          Input('sql_list_dropdown', 'value'), prevent_initial_call=True)(self._update_sql_textbox()) 
    
    time_columns = ['timestamp', 'create_time', 'start_time', 'end_time']
        
    def _update_table_browse(self):
        def update_table(n_clicks, tablename, dbname, page_current, page_size):
            if not tablename or not dbname:
                raise PreventUpdate
            df = db_tools.dump_table_df(self.dao_map[dbname].db_file, tablename, page_size, page_current * page_size)
            # for time_column in DBTableBrowsePage.time_columns:
            #     if time_column in df.columns:
            #         df[time_column] = df[time_column].apply(type_tools.timestamp_to_datestr)
            # truncate the cell with long strings
            return (df.to_dict('records'), {'display': 'block'},)
        return update_table

    def _update_dblist(self):
        def update_dblist(dbname):
            if not dbname:
                raise PreventUpdate
            table_names = self.get_tablenames(dbname)
            return table_names
        return update_dblist
    
    def _update_table_query(self):
        def update_table_query(query_button, update_button, sql, dbname, page_current, page_size):
            self._error_placeholder.children = None
            if not sql or len(sql.strip()) == 0:
                raise PreventUpdate
            if not dbname:
                raise PreventUpdate            
            try:
                button_id = ctx.triggered_id if not None else 'No clicks yet'
                if button_id == 'db_query_button':
                    df = db_tools.query_paged(self.dao_map[dbname].db_file, sql, page_size, page_current * page_size)
                    if 'start_time' in df.columns:
                        df['start_time'] = df['start_time'].apply(type_tools.timestamp_to_datestr)
                    if 'commit_time' in df.columns:
                        df['commit_time'] = df['commit_time'].apply(type_tools.timestamp_to_datestr)
                    if 'timestamp' in df.columns:
                        df['timestamp'] = df['timestamp'].apply(type_tools.timestamp_to_datestr)
                elif button_id == 'db_update_button':
                    rowcount = db_tools.update(self.dao_map[dbname].db_file, sql)
                    df = pd.DataFrame(['Results', rowcount])
                else:
                    raise AssertionError(f'Invalid button id: {button_id}')

                if sql not in self.sql_list:
                    self.sql_list.append({'label': sql, 'value': sql})
                    self.sql_list = self.sql_list[-10:]
                    self._sql_dropdown.__setattr__('options', self.sql_list)
                return (df.to_dict('records'), {'display': 'block'}, self.sql_list, html.P(), )
            except Exception as e:
                error_alert = dbc.Alert(f'Error: {e}', dismissable=True, is_open=True, color='danger')
                return (pd.DataFrame().to_dict('records'), {'display': 'none'}, self.sql_list, error_alert,  )
        return update_table_query

    def _update_sql_textbox(self):
        def update_sql_textbox(value):
            return value
        return update_sql_textbox