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

import yaml, os
from enum import Enum
from collections.abc import MutableMapping
# ros params
import rospy

class SystemConfigNames(Enum):
    """ Maps the config names as a sting to a constant
    """
    CGRAS_DATA_FOLDER = 'cgras_data_folder'
    CGRAS_CAPTURED_IMAGES_FOLDER = 'cgras_captured_images_folder'
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
    def __init__(self, config_file:str, *args, **kwargs):
        """the constructor
        :param scene_config_file: the path to the yaml configuration file
        :type scene_config_file: str, optional
        """
        # load data from the config yaml file
        if config_file is None:
            raise AssertionError(f'{__class__.__name__} parameter (config_file) is None')
        with open(config_file, 'r') as f:
            self.config = yaml.safe_load(f)
            if 'cgras_detector' not in self.config:
                raise AssertionError(f'{__class__.__name__} the config yaml file does not contain a branch named cgras_detector')
            self.config = self.config['cgras_detector'] 
        self.update(dict(*args, **kwargs))
        
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
    
    CONFIG:SystemConfig = SystemConfig(os.path.join(os.path.dirname(__file__), '../../config/system_config.yaml'))
    print(f'{type(SystemConfigNames.CGRAS_DATA_FOLDER)}')
    print(f'{isinstance(SystemConfigNames.CGRAS_DATA_FOLDER, Enum)}')
    print(f'{CONFIG[SystemConfigNames.CGRAS_DATA_FOLDER]}')
    print(f'{CONFIG.get(SystemConfigNames.CGRAS_DATA_FOLDER)}')
    print(f'{CONFIG.get("no_definition", "default")}')
    
    print(f'### The config dictionary')
    config_dict = CONFIG.to_params()
    print(f'{config_dict}')