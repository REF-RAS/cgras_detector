# Copyright 2024 - Andrew Kwok Fai LUI, 
# Robotics and Autonomous Systems Group, REF, RI
# and the Queensland University of Technology

__author__ = 'Andrew Lui'
__copyright__ = 'Copyright 2024'
__license__ = 'GPL'
__version__ = '1.0'
__email__ = 'ak.lui@qut.edu.au'
__status__ = 'Development'

import time, numbers
from datetime import timedelta, date
import pandas as pd
# dash modules
from dash import html, dcc, Input, Output, State, dash_table, ctx
from dash.dash_table.Format import Format, Group, Scheme
import dash_bootstrap_components as dbc
from dash.exceptions import PreventUpdate
from detector.model import DETECT_DAO
from tools.logging_tools import global_logger

class HealthViewTable():
    def __init__(self, app, prefix, page_size=50, refresh_cycle=10):
        self.app = app 
        self.prefix = prefix = prefix + 'atb_'
        self.update_store_id = self.prefix + 'update_store'
        self.row_selected_trigger_id = self.prefix + 'row_selected_store'
        # define model variables
        self._model = None
        self._model_last_updated = None
        self.to_refresh = False
        self.refresh_cycle = refresh_cycle
        # define widgets 
        self._operators = [['ge ', '>='],
                    ['le ', '<='],
                    ['lt ', '<'],
                    ['gt ', '>'],
                    ['ne ', '!='],
                    ['eq ', '='],
                    ['contains '],
                    ['datestartswith ']]
        self._columns = [{'name': 'Tile ID', 'id': 'tile_id', 'type': 'text', 'editable': False},
                         {'name': 'Species', 'id': 'species', 'type': 'text', 'editable': False},
                         {'name': 'Spwaned on', 'id': 'settle_time', 'type': 'datetime', 'editable': False},
                         {'name': '# Samples', 'id': 'num_samples', 'type': 'numeric', 'editable': False},
                         {'name': '# Corals Latest', 'id': 'coral_count_latest', 'type': 'numeric', 'editable': False},  
                         {'name': 'Age Latest', 'id': 'age_latest', 'type': 'numeric', 'editable': False},
                         {'name': 'LRW', 'id': 'loss_rate_whole', 'type': 'numeric', 'editable': False, 'format': Format(precision=3, scheme=Scheme.fixed),},
                         {'name': 'LRR', 'id': 'loss_rate_recent', 'type': 'numeric', 'editable': False, 'format': Format(precision=3, scheme=Scheme.fixed),},
                         {'name': 'Health Index', 'id': 'health_index', 'type': 'numeric', 'editable': False},                                                  
                         ]
        self._style_data_conditional = [
                {'if': {
                    'filter_query': '{health_index} >= 0.1 && {health_index} < 0.5',
                    'column_id': 'health_index'
                }, 'backgroundColor': '#e5ffcc', 'color': 'black'},
                {'if': {
                    'filter_query': '{health_index} >= 0.5',
                    'column_id': 'health_index'
                }, 'backgroundColor': '#66cc00', 'color': 'black'},
                {'if': {
                    'filter_query': '{health_index} <= -0.2',
                    'column_id': 'health_index'
                }, 'backgroundColor': '#ffcccc', 'color': 'black'}, 
                {'if': {
                    'filter_query': '{num_samples} = 0',
                    'column_id': 'health_index'
                }, 'backgroundColor': '#cccccc', 'color': 'black'},                                                
                ]

        self._datatable = dash_table.DataTable(id=prefix+'datatable', columns=self._columns, style_header={}, fill_width=True, 
                                                style_data_conditional = self._style_data_conditional,
                                                page_current=0, page_size=page_size, page_action='custom',
                                                filter_action='custom', filter_query='',
                                                cell_selectable=False, row_selectable='multi')

        # define modal for showing the table legend
        self._legend_modal = dbc.Modal(id=prefix+'view_modal', children=[
                dbc.ModalHeader(dbc.ModalTitle(children='Legend',)),
                dbc.ModalBody(children=[html.P('The filter accepts operators <, >, <=, >=, !=, <>', className='mb-3', style={}),
                                        dbc.ListGroupItem('Spawned on: the date when the coral babies were born'),
                                        dbc.ListGroupItem('# Samples: the number of samples captured from this tile'),
                                        dbc.ListGroupItem('# Corals Latest: the number of corals on the tile found in the latest capture'),
                                        dbc.ListGroupItem('Age Latest: the age of the corals at the latest captured'),
                                        dbc.ListGroupItem('LRW: Overall loss rate from the start to the latest capture'),
                                        dbc.ListGroupItem('LRR: Recent loss rate at the latest capture'),
                                        dbc.ListGroupItem('Health Index: the health index (-ve: unhealthy)'),
                                        ]),
            ], size='xl', is_open=False,) 

        self._menu_panel = dbc.Row([
            dbc.Col([dbc.Button('View Coral Count', id=prefix+'table_view_button', n_clicks=0, color='primary', className='mb-1 me-3', size='sm', 
                               disabled=True, external_link=True, target='count_view', style={'width': '180px'}),
                    dcc.Dropdown(id=prefix+'season_list_dropdown', 
                                       searchable=False, clearable=False, className='ms-2 small', maxHeight=80, style={'width': '200px'}),
            ], className='col-8', style={'display': 'flex'}),
            dbc.Col([dbc.Button('Table Legend', id=prefix+'table_legend_button', n_clicks=0, color='secondary', className='mb-1', size='sm'),],
                className='col-4 text-end'),
        ])

        self._datatable_panel = dbc.Row(html.Div([
                    self._menu_panel,
                    self._datatable], className='p-2', style={'background-color': 'rgb(225, 225, 225)'}))

        self.the_panel = html.Div([
                html.H4([dbc.Badge('TILES IN THE SELECTED SEASON', color='white', text_color='secondary'), ]),
                # html.P('Click to view results', className='ms-4'),
                self._datatable_panel,
                dcc.Store(id=self.update_store_id),
                dcc.Store(id=self.row_selected_trigger_id),
                self._legend_modal,     
                ], style={'margin-top': '24px'})     

        # self.app.callback([Output(self.row_selected_trigger_id, 'data'),
        #                     Output(prefix+'datatable', 'active_cell'),
        #                     Output(prefix+'datatable', 'selected_cells')],
        #     [Input(prefix+'datatable', 'active_cell'),
        #      State(self.prefix+'datatable', 'page_current'),
        #      State(self.prefix+'datatable', 'page_size'),
        #      ], prevent_initial_call=True)(self._row_selected())
    
        self.app.callback([Output(self.prefix+'datatable', 'data')],
            [Input(self.prefix+'datatable', 'page_current'),
             Input(self.prefix+'datatable', 'page_size'),
             Input(self.prefix+'datatable', 'sort_by'),
             Input(self.prefix+'datatable', 'filter_query'),
             Input(self.prefix+'season_list_dropdown', 'value'),
             ], prevent_initial_call=False)(self._update_datatable())
        
        self.app.callback([Output(prefix+'view_modal', 'is_open', allow_duplicate=True)],
                    [Input(prefix+'table_legend_button', 'n_clicks')], prevent_initial_call=True)(self._table_legend_button_pressed())  
        
        self.app.callback([Output(prefix+'table_view_button', 'href', allow_duplicate=True),
                           Output(prefix+'table_view_button', 'disabled', allow_duplicate=True),
                           Output(prefix+'datatable', 'style_data_conditional'),
                           Output(prefix+'datatable', 'selected_rows'),],
                    [Input(prefix+'datatable', 'selected_rows'),
                     State(self.prefix+'datatable', 'page_current'),
                     State(self.prefix+'datatable', 'page_size'),
                     State(prefix+'datatable', 'data')], prevent_initial_call=True)(self._row_selected())      
        
        # define callback for the season
        self.app.callback([Output(self.prefix+'season_list_dropdown', 'options', allow_duplicate=True),
                            Output(self.prefix+'season_list_dropdown', 'value', allow_duplicate=True)],
                         [Input(self.update_store_id, 'data'),], prevent_initial_call=True)(self._update_season_dropdown())              
        
        # self.app.callback(Output(prefix+'datatable', 'style_data_conditional'),
        #                     [Input(prefix+'datatable', 'derived_viewport_selected_rows'),
        #                      State(prefix+'datatable', 'data')])(self._style_selected_rows())  
        
    def get_panel(self):
        return self.the_panel
    
    def refresh(self):
        self.to_refresh = True
    
    def register_trigger(self, trigger_id:str):
        # define callback for the datatable data
        self.app.callback([Output(self.update_store_id, 'data')],
            [Input(trigger_id, 'data')], prevent_initial_call=True, allow_duplicate=True)(self._update_panel())

    
    def get_row_selected_trigger_id(self) -> str:
        return self.row_selected_trigger_id
    
    def _get_default_datatable_model(self, season):
        model = DETECT_DAO.list_all_cache_tile_health(season)
        return model
    
    def refine_datatable_model(self, model):
        # model['spawned'] =  model['batch_time_latest'] - pd.to_timedelta(model['age_latest'], unit='d')
        model = model[['tile_id', 'species', 'settle_time', 'num_samples', 'coral_count_latest', 'age_latest', 'loss_rate_whole', 'loss_rate_recent', 'health_index']]
        to_drop = []
        model = model.drop(to_drop, axis=1)
        return model
    
    def split_filter_part(self, filter_part):
        for operator_type in self._operators:
            for operator in operator_type:
                if operator in filter_part:
                    name_part, value_part = filter_part.split(operator, 1)
                    name = name_part[name_part.find('{') + 1: name_part.rfind('}')]
                    value_part = value_part.strip()
                    v0 = value_part[0]
                    if (v0 == value_part[-1] and v0 in ("'", '"', '`')):
                        value = value_part[1: -1].replace('\\' + v0, v0)
                    else:
                        try:
                            value = int(value_part)
                        except ValueError:
                            value = value_part
                    # word operators need spaces after them in the filter string, but we don't want these later
                    return name, operator_type[0].strip(), value
        return [None] * 3

    def _update_season_dropdown(self):
        def update_season_dropdown(timer):
            # get options for the dropdown
            options = DETECT_DAO.list_seasons_in_tile_sample()
            value = options[0] if options is not None and len(options) > 0 else None
            options = [{'label': f'{x} Season', 'value': x} for x in options]           
            return (options, value,)
        return update_season_dropdown

    def _update_datatable(self):
        def update_datatable(page_current, page_size, sort_by, filter, season_title):
            if not self.to_refresh:
                raise PreventUpdate
            current_time = time.time()
            if self._model is None or self._model_last_updated is None or current_time - self._model_last_updated > 60:  # update once every minute at most
                self._model = self._get_default_datatable_model(season_title)
                self._model = self.refine_datatable_model(self._model)
                self._model_last_updated = current_time
            model = self._model
            filtering_expressions = filter.split(' && ')            
            for filter_part in filtering_expressions:
                col_name, operator, filter_value = self.split_filter_part(filter_part)
                if operator in ('eq', 'ne', 'lt', 'le', 'gt', 'ge'):
                    # these operators match pandas series operator method names
                    model = model.loc[getattr(model[col_name], operator)(filter_value)]
                elif operator == 'contains':
                    if isinstance(filter_value, numbers.Number):
                        filter_value = str(filter_value)
                    model = model.loc[model[col_name].str.contains(filter_value)]
                elif operator == 'datestartswith':
                    # this is a simplification of the front-end filtering logic,
                    # only works with complete fields in standard format
                    model = model.loc[model[col_name].str.startswith(filter_value)]

            return (model.iloc[page_current * page_size:(page_current + 1) * page_size].to_dict('records'),)
            # return (self._model.to_dict('records'),)
        return update_datatable 
    
    def _update_panel(self):
        def update_panel(timer):
            if (timer-1) % self.refresh_cycle != 0:
                raise PreventUpdate
            return (timer,)
        return update_panel
    
    def _table_legend_button_pressed(self):
        def table_legend_button_pressed(n_clicks):
            if not n_clicks:
                raise PreventUpdate
            return (True,)
        return table_legend_button_pressed

    def _row_selected(self):
        def row_selected(selected_rows:list, page_current, page_size, model):
            # ensure only one row is selected
            if selected_rows is None:
                return dash.no_update
            if len(selected_rows) >= 2:
                selected_rows.pop(0)   # assume that the new row is added to the end of the selected_row list
            # if no row is selected
            if not selected_rows or len(selected_rows) == 0:
                return (None, True, self._style_data_conditional, selected_rows)
            # update the href field of the button before enable it
            tile_id = model[selected_rows[0]]['tile_id']
            href = f'/popup_count_display?tile_id={tile_id}'
            # highlight the selected row
            style_data_conditional = self._style_data_conditional + [
                {"if": {"filter_query": "{{tile_id}} = '{}'".format(model[i]['tile_id']), "column_id": "tile_id"}, "backgroundColor": "yellow",}
                for i in selected_rows
            ]

            return (href, False, style_data_conditional, selected_rows)
        return row_selected  
