# Copyright 2024 - Andrew Kwok Fai LUI, 
# Robotics and Autonomous Systems Group, REF, RI
# and the Queensland University of Technology

__author__ = 'Andrew Lui'
__copyright__ = 'Copyright 2024'
__license__ = 'GPL'
__version__ = '1.0'
__email__ = 'ak.lui@qut.edu.au'
__status__ = 'Development'

# import libraries
import sys, os, signal, io, time, traceback
from urllib.parse import urlparse, parse_qs
import dash
import dash_bootstrap_components as dbc
from dash import html, dcc
from dash.exceptions import PreventUpdate
from dash_auth import BasicAuth
from dash.dependencies import Input, Output, State
from flask import Flask
# ros modules
import rospy, message_filters
# project modules
from cgras_datatools.logging_tools import logger
import cgras_datatools.hash_tools as hash_tools
import detector.model as model
from detector.model import CONFIG, SystemConfigNames, APP_FILE_MANAGER, CALLBACK_MANAGER, CallbackTypes
from detector.web.dash import themes
# from dash_bootstrap_components import themes

SERVER = Flask(__name__)
APP = dash.Dash(__name__, 
                external_stylesheets=themes.BOOTSTRAP, 
                external_scripts=themes.BOOTSTRAP_JS, 
                server=SERVER,
                meta_tags=[{"name": "viewport", "content": "width=device-width"}],
                suppress_callback_exceptions=True,
                include_assets_files=False,
                # assets_ignore='foundation-renamed.min.css|jquery.nanogallery2.min.js|nanogallery2.min.css',
                # assets_ignore='foundation-renamed.min.css|foundation-renamed.min.js',
                # assets_ignore='foundation-renamed.min.css|foundation-renamed.min.js|bootstrap.min.css',  # this combination stops the annoying refreshing of the UI when online
                assets_ignore='*.css|*.js|*.jpg|*.html|*.yaml',
                assets_folder=APP_FILE_MANAGER.get_detector_subfolder(APP_FILE_MANAGER.SYSTEM_SUBFOLDER)
                )

APP.config['suppress_callback_exceptions'] = True

# -- load the pages for the dash application which should appear after the above APP creation
from . import page_count_display, page_dashboard, page_db_browse, page_models, page_sample_manager, page_coral_health, page_system_setup, popup_count_display

# -- Create a dash application object
class DashApplicationMain():
    def __init__(self):
        global APP
        self.DASH_HOST = CONFIG.get(SystemConfigNames.WEB_HOST)
        self.DASH_PORT = CONFIG.get(SystemConfigNames.WEB_PORT)
        self.SYSTEM_TIMER = CONFIG.get(SystemConfigNames.SYSTEM_TIMER, 1) * 1000  # in milliseconds

        self.app = APP
        self.flask_server = self.app.server
        self.dash_thread = None
        # define the pages
        self._dashboard_page = page_dashboard.DashboardPage(self.app, CONFIG.get(SystemConfigNames.DASHBOARD_TIMER, 1))
        self._setup_page = page_system_setup.AdminSetupPage(self.app)
        self._db_browse_page = page_db_browse.DBTableBrowsePage(self.app)   
        self._sample_manager_page = page_sample_manager.SampleManagerPage(self.app)     
        self._yolo_model_file_page = page_models.ModelsPage(self.app)     
        self._count_display_page = page_count_display.CountDisplayPage(self.app)   
        self._page_coral_health = page_coral_health.CoralHealthPage(self.app)
        # define the popup
        self._popup_count_display = popup_count_display.CountDisplayPopup(self.app) 
        # initialize the application
        self._define_app()

    def _define_app(self):
        # brand_div = html.Div([html.H3('CGRAS Coral Counting and Visualization'), html.H6('Robotics and Autonomous Systems Group, REF, RI, Queensland University of Technology')])    
        brand_div = dbc.Row([
            html.Img(src='/assets/images/QUTLogo.png', height='60', className='col-2'),
            html.Div([html.H3('CGRAS Coral Counting and Visualization'), 
                      html.H6('Robotics and Autonomous Systems Group, REF')
                      ], className='col-10')
        ])
        self._navbar_with_menu = dbc.NavbarSimple(
                    children=[
                        dbc.NavItem(dbc.NavLink('Monitor', href='/page_monitor')),
                        dbc.NavItem(dbc.NavLink('Sample', href='/page_sample_manager')), 
                        dbc.NavItem(dbc.NavLink('Count', href='/page_count_display')), 
                        # dbc.NavItem(dbc.NavLink('Health', href='/page_coral_health')), 
                        dbc.NavItem(dbc.NavLink('Model', href='/page_yolo_model')), 
                        dbc.NavItem(dbc.NavLink('System', href='/page_setup')),                                                 
                    ],
                    brand=brand_div,
                    brand_href='/page_monitor', color='#ffcc99', className='fs-3 text')

        # self._navbar_simple = dbc.NavbarSimple(
        #             brand=html.H3('CGRAS Coral Counting and Visualization'), color='#cccc99', className='fs-4 text')      

        self._nav_placeholder = html.Div(id='nav_placeholder')
        
        self.app.layout = html.Div([ 
            # for the dash system timer
            dcc.Store(id='dashapp_interval_store'),
            dcc.Interval(id='system_interval', interval=self.SYSTEM_TIMER, n_intervals=0),
            dcc.Location(id='url', refresh=False),
            self._nav_placeholder, 
            html.Div(id='page_content', children=[]), 
        ])
        # ----- the dash callbacks
        self.app.callback([Output('page_content', 'children'),
                           Output('nav_placeholder', 'children')],
              [Input('url', 'pathname'),
                State('url', 'href')])(self._display_page())
        
        self.app.callback([Output('dashapp_interval_store', 'data')],
              [Input('system_interval', 'n_intervals')],
              [State('url', 'pathname')])(self._dash_system_timer())
               
    def start(self):
        rospy.loginfo(f'{type(self).__name__}: starting the dash flask server')
        # switch off the hot reload
        self.app.enable_dev_tools(dev_tools_hot_reload=CONFIG.get(SystemConfigNames.WEB_DEBUG_HOT_RELOAD, True))
        # start the server
        self.app.run_server(host=self.DASH_HOST, port=self.DASH_PORT, debug=CONFIG.get(SystemConfigNames.WEB_DEBUG_MODE, True))

    def stop(self, *args, **kwargs):
        rospy.loginfo(f'{type(self).__name__}: the dash flask server is being shutdown')
        time.sleep(2)
        sys.exit(0)

    # -- flask dash callback for url handling
    def _display_page(self):
        def display_page(pathname, href):
            page_content = ''
            nav_content = self._navbar_with_menu
            parsed_url = urlparse(href)
            params = parse_qs(parsed_url.query)
            try: 
                if pathname == '/page_monitor':
                    page_content = self._dashboard_page.layout()
                elif pathname == '/page_sample_manager':
                    page_content = self._sample_manager_page.layout()    
                elif pathname == '/page_yolo_model':
                    page_content = self._yolo_model_file_page.layout() 
                elif pathname == '/page_count_display':
                    page_content = self._count_display_page.layout() 
                elif pathname == '/popup_count_display':
                    tile_id = params.get('tile_id', None)
                    if tile_id is None:
                        raise PreventUpdate
                    return (self._popup_count_display.layout(tile_id[0]), None,)               
                elif pathname == '/page_coral_health':
                    page_content = self._page_coral_health.layout()   
                elif pathname == '/page_setup':
                    page_content = self._setup_page.layout()              
                elif pathname == '/db':
                    page_content = self._db_browse_page.layout()                                        
                elif pathname == '/': 
                    page_content = self._dashboard_page.layout()
                else: # if redirected to unknown link
                    page_content = '404 Page Error! Please choose a link'
            except Exception as e:
                logger.error(e)
                traceback.print_exc()
            return (page_content, nav_content,)
        return display_page
    
    # -- dash callback for system interval timer
    def _dash_system_timer(self):
        def dash_system_timer(n, pathname):
            model.CALLBACK_MANAGER.fire_event(model.CallbackTypes.TIMER)
            return (n,)
        return dash_system_timer 
    
    @SERVER.route("/<path>")
    def update_title(path):
        APP.title = 'CGRAS Coral Counting and Visualization'
        return APP.index()
        
    