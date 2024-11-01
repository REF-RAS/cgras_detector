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
import pandas as pd
# dash modules
import dash
from dash import html, dcc, Input, Output, State, dash_table, ctx
import dash_bootstrap_components as dbc
from dash.exceptions import PreventUpdate
from detector.model import DETECT_DAO, PERSISTENT_STORE_DAO, AIMSTILE_DAO
from tools.logging_tools import logger

class CountTileSelectTable():
    def __init__(self, app, prefix, page_size=25):
        self.app = app 
        self.prefix = prefix = prefix + 'ctst_'
        self.row_selected_trigger_id = self.prefix + 'row_selected_store'
        # define model variables
        self._model = None
        self._model_last_updated = None
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
                         {'name': 'Settled On', 'id': 'settle_time', 'type': 'datetime', 'editable': False},
                         ]
        self._datatable = dash_table.DataTable(id=prefix+'datatable', columns=self._columns, style_header={}, fill_width=True, 
                                                page_current=0, page_size=page_size, page_action='custom',
                                                filter_action='custom', filter_query='', row_selectable='multi',
                                                cell_selectable=False, row_deletable=False, style_cell={'fontSize': 14})

        self.the_panel = html.Div([
                html.H4([dbc.Badge('TILES IN THE SELECTED SEASON', color='white', text_color='secondary'), ]),
                dcc.Dropdown(id=prefix+'season_list_dropdown', 
                                       searchable=False, clearable=False, className='ms-2 small mb-2', maxHeight=80, style={'width': '200px'}),
                dbc.Row(html.Div(self._datatable)),
                dcc.Store(id=self.row_selected_trigger_id),     
            ], id=prefix+'main_panel', style={'margin-top':'24px'})     
        
        self.app.callback([Output(self.row_selected_trigger_id, 'data'),
                            Output(prefix+'datatable', 'style_data_conditional'),
                            Output(prefix+'datatable', 'selected_rows')],
            [Input(prefix+'datatable', 'selected_rows'),
             State(self.prefix+'datatable', 'data'),
             State(self.prefix+'datatable', 'page_current'),
             State(self.prefix+'datatable', 'page_size'),
             ], prevent_initial_call=True)(self._row_selected())
    
        self.app.callback([Output(self.prefix+'datatable', 'data'),],
            [Input(self.prefix+'datatable', 'page_current'),
             Input(self.prefix+'datatable', 'page_size'),
             Input(self.prefix+'datatable', 'sort_by'),
             Input(self.prefix+'datatable', 'filter_query'),
             Input(self.prefix+'season_list_dropdown', 'value'),
             ], prevent_initial_call=False)(self._update_datatable())
        
        # define callback for the season
        self.app.callback([Output(self.prefix+'season_list_dropdown', 'options', allow_duplicate=False),
                            Output(self.prefix+'season_list_dropdown', 'value', allow_duplicate=False)],
                         [Input(self.prefix+'main_panel', 'children'),], prevent_initial_call=False)(self._update_season_dropdown())       
            
    def get_panel(self):
        return self.the_panel
    
    def get_row_selected_trigger_id(self) -> str:
        return self.row_selected_trigger_id
    
    def _get_default_datatable_model(self, season_title):
        # model = DETECT_DAO.list_tiles_in_cache_tile_health(season_title)
        model = DETECT_DAO.list_tile_samples(season_title=season_title, status=None)
        return model
    
    def refine_datatable_model(self, model):
        model = model[['tile_id', 'species', 'settle_time']]
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
            # options = DETECT_DAO.list_seasons_in_tile_sample()
            options = AIMSTILE_DAO.get_season_titles_list()
            value = PERSISTENT_STORE_DAO.get_config_value(PERSISTENT_STORE_DAO.CONFIG_SELECTED_SEASON, None)
            value = options[0] if value is None and options else None
            options = [{'label': f'{x} Season', 'value': x} for x in options]           
            return (options, value,)
        return update_season_dropdown

    def _update_datatable(self):
        def update_datatable(page_current, page_size, sort_by, filter, season_title):
            # current_time = time.time()
            # if self._model is None or self._model_last_updated is None or current_time - self._model_last_updated > 10:  # update once every minute at most
            #     self._model = self._get_default_datatable_model(season_title)
            #     self._model = self.refine_datatable_model(self._model)
            #     self._model_last_updated = current_time
            
            self._model = self._get_default_datatable_model(season_title)
            self._model = self.refine_datatable_model(self._model)            
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
            # update the selected season in the persistent storage
            PERSISTENT_STORE_DAO.set_config_value(PERSISTENT_STORE_DAO.CONFIG_SELECTED_SEASON, season_title)
            return (model.iloc[page_current * page_size:(page_current + 1) * page_size].to_dict('records'),)
            # return (self._model.to_dict('records'),)
        return update_datatable 
    
    def _row_selected(self):
        def row_selected(selected_rows, model, page_current, page_size):
            if selected_rows is None:
                return dash.no_update
            if len(selected_rows) >= 2:
                selected_rows.pop(0)   # assume that the new row is added to the end of the selected_row list
            if len(selected_rows) == 1:
                row = selected_rows[0]
                tile_id = model[row]['tile_id']
            else:
                tile_id = None
            style_data_conditional = [
                {"if": {"filter_query": "{{tile_id}} = '{}'".format(model[i]['tile_id'])}, "backgroundColor": "yellow",}
                for i in selected_rows
            ]
            return (tile_id, style_data_conditional, selected_rows,)
        return row_selected
