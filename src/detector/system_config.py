#!/usr/bin/env python3
# 
# # Copyright 2024 - Andrew Kwok Fai LUI, 
# Robotics and Autonomous Systems Group, REF, RI
# and the Queensland University of Technology

__author__ = 'Andrew Lui'
__copyright__ = 'Copyright 2024'
__license__ = 'GPL'
__version__ = '1.0'
__email__ = 'ak.lui@qut.edu.au'
__status__ = 'Development'

import yaml, os, logging, shutil
from enum import Enum
from collections.abc import MutableMapping
# ros params
import rospy

class SystemConfigNames(Enum):
    """ Maps the config names as a sting to a constant
    """
    CGRAS_DATA_FOLDER = 'cgras_data_folder'
    DISK_SPACE_MIN = 'disk_space_min'                                # GBytes
    # CGRAS_CAPTURED_IMAGES_FOLDER = 'cgras_captured_images_folder'  # obsolete as the query is changed to ros service call
    WEB_HOST = 'web_host'
    WEB_PORT = 'web_port'
    WEB_DEBUG_MODE = 'web_debug_mode'
    WEB_DEBUG_HOT_RELOAD = 'web_debug_hot_reload'
    # aux web server
    AUX_WEB_HOST = 'aux_web_host'
    AUX_WEB_PORT = 'aux_web_port'
    AUX_WEB_DIRECTORY = 'aux_web_directory'
    # automation mode (whether the task execution is automated)
    TASK_AUTOMATION_MODE = 'task_automation' 
    SUSPEND_WHEN_CAPTURING_IMAGE = 'suspend_when_capturing_image'
    # default ros topics
    ROS_COORDINATOR_STATE_TOPIC = 'ros_coordinator_state_topic' 
    ROS_DETECTOR_STATE_TOPIC = 'ros_detector_state_topic' 
    # ros topic: query tile sample service server
    ROS_QUERY_TILE_SAMPLES_TOPIC = 'ros_query_tile_samples_topic'  
    # timer for refresh the system and GUI
    SYSTEM_TIMER = 'system_timer'                                # the timer driving the state transition machine through the timer callback
    DASHBOARD_REFRESH_CYCLES = 'dashboard_refresh_cycles'        # the refresh rate of 'auto-refresh pages' in the dashboard the number of cycles of system timer
    # yolo model range
    MAX_CORAL_AGE = 'max_coral_age'
    # heatmap
    HEATMAP_COLOUR_SCALE = 'heatmap_colour_scale'
    HEATMAP_SHOW_LABEL_SLIDER_MAX = 'heatmap_show_label_slider_max'
    # connection timeout
    CONNECTION_TIMEOUT = 'connection_timeout'

class SystemConfig(MutableMapping):
    """ The class providing easy query of the hierarcy of configurations in yaml
    """
    CONFIG_FILENAME = 'system_config.yaml'
    DEFAULT_CONFIG_FOLDER = os.path.join(os.path.dirname(__file__), '../../config')
    logger = logging.getLogger('global')
    """ The class providing easy query of the hierarcy of configurations in yaml
    """
    def __init__(self, namespace:str='cgras_detector', default_config_folder:str=None, use_default=False, *args, **kwargs):
        """the constructor
        :param default_config_folder: the path to the folder where the yaml configuration file resides
        :type default_config_folder: str, optional
        """
        # input parameters
        self.namespace = namespace
        # model variables
        self.config = None
        
        if not use_default:
            # create config folder
            self.config_folder = os.path.join(os.path.expanduser(f'~/.config/{self.namespace}'))
            os.makedirs(self.config_folder, exist_ok=True)
            # attempt to load config yaml file from the .config folder under the user home folder
            self.config_file = os.path.join(self.config_folder, self.CONFIG_FILENAME)
            self.config = self._load_config_file(self.config_file)
        # load data from the config yaml file
        if default_config_folder is None:
            default_config_folder = self.DEFAULT_CONFIG_FOLDER
        # if no config file is found under the .config folder, use the default one from the source code
        if self.config is None:
            if not use_default:
                # copy the default config file to the .config folder
                shutil.copy(os.path.join(default_config_folder, self.CONFIG_FILENAME), self.config_folder)   
                self.logger.info(f'SystemConfig: using the configuration file at {self.config_file} after copied from the default folder {default_config_folder}')
            else:
                self.logger.info(f'SystemConfig: using the configuration file at {default_config_folder}/{self.CONFIG_FILENAME}')
                self.config_file = os.path.join(default_config_folder, self.CONFIG_FILENAME)
            self.config = self._load_config_file(self.config_file) 
        else:
            self.logger.info(f'SystemConfig: using the configuration file at {self.config_file}')
        # use the remaining input parameters to the config to add or update
        self.update(dict(*args, **kwargs))

    def _load_config_file(self, config_file) -> dict:
        if not os.path.isfile(config_file):
            return None
        try:
            with open(config_file, 'r') as f:
                config_dict = yaml.safe_load(f)
                if self.namespace not in config_dict:
                    raise AssertionError(f'{__class__.__name__} the config yaml file at ({config_file}) does not contain a branch named {self.namespace}')
                config_dict = config_dict[self.namespace] 
                return config_dict
        except AssertionError: 
            raise
        except Exception as e:
            raise        
        
    def get_namespace(self) -> str:
        return self.namespace
        
    def __getitem__(self, key):
        name = f'~{self._keytransform(key)}'
        value = rospy.get_param(name, self.config[self._keytransform(key)])
        return value

    def __setitem__(self, key, value):
        self.config[self._keytransform(key)] = value

    def __delitem__(self, key):
        del self.config[self._keytransform(key)]

    def __iter__(self):
        return iter(self.config)
    
    def __len__(self):
        return len(self.config)

    def _keytransform(self, key):
        if isinstance(key, SystemConfigNames):
            key = key.value
        return key
    # -------------------------------------------
    # model functions

    # return a dict object for the system configs
    def to_params(self, param_enum_cls:list=None):
        if param_enum_cls is None:
            param_enum_cls = [SystemConfigNames]
        output = {}
        for param_enum in param_enum_cls:
            for param in param_enum:
                if param.value in self.config:
                    output[param.value] = self.get(param.value)
        return output

# ------------------------
# test program
if __name__ == '__main__':
    # the rospy param will override the config file if a ros node is running
    rospy.init_node('config_manager')
    print(f'ros_param: {rospy.get_param("~data_folder")}')
    
    CONFIG:SystemConfig = SystemConfig(namespace='cgras_detector', default_config_folder=os.path.join(os.path.dirname(__file__), '../../config'))
    print(f'{type(SystemConfigNames.CGRAS_DATA_FOLDER)}')
    print(f'{isinstance(SystemConfigNames.CGRAS_DATA_FOLDER, Enum)}')
    print(f'{CONFIG[SystemConfigNames.CGRAS_DATA_FOLDER]}')
    print(f'{CONFIG.get(SystemConfigNames.CGRAS_DATA_FOLDER)}')
    print(f'{CONFIG.get("no_definition", "default")}')
    
    print(f'### The config dictionary')
    config_dict = CONFIG.to_params()
    print(f'{config_dict}')