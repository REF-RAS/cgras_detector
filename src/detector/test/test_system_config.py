#!/usr/bin/env python3

# Copyright 2024 - Andrew Kwok Fai LUI, 
# Robotics and Autonomous Systems Group, REF, RI
# and the Queensland University of Technology

__author__ = 'Andrew Lui'
__copyright__ = 'Copyright 2024'
__license__ = 'GPL'
__version__ = '1.0'
__email__ = 'ak.lui@qut.edu.au'
__status__ = 'Development'

import os, yaml
from enum import Enum
from json import dumps
import rospy

from detector.system_config import SystemConfig, SystemConfigNames

def sample_system_config_file():
    CURRENT_FOLDER = os.path.dirname(__file__)
    SYSTEM_CONFIG_FILE = os.path.join(CURRENT_FOLDER, '../../../config/system_config.yaml')
    return SYSTEM_CONFIG_FILE

def load_system_config_file() -> dict:
    with open(sample_system_config_file(), 'r') as infile:
        config_dict = yaml.load(infile, Loader=yaml.Loader)
    return config_dict

# test the basic operation of system config
def test_setup_config():
    CONFIG:SystemConfig = SystemConfig(sample_system_config_file())
    for config_name in SystemConfigNames:
        value = CONFIG.get(config_name.value, None)
        if value is None:
            print(f'The configuration parameter "{config_name}" has not been set in the system config file')
    # test a non-existent parameter
    value = CONFIG.get('no_definition', None)
    assert value is None
    # test conversion to a dictionary
    config_dict = CONFIG.to_params()
    for config_name in config_dict:
        assert config_dict[config_name] == CONFIG.get(config_name, None)

# test if SystemConfig returns the values currently defined in the system_config.yaml file
def test_config_value_consistent():
    # load config file directly
    config_dict = load_system_config_file()
    assert 'cgras_detector' in config_dict
    config_dict = config_dict['cgras_detector']
    # instantiate SystemConfig
    CONFIG:SystemConfig = SystemConfig(sample_system_config_file())
    # test if the two methods give consistent value for all config names
    for config_name in SystemConfigNames:
        try:
            value_from_dict = config_dict.get(config_name.value)
            value_from_system = CONFIG.get(config_name.value)
        except:
            print(f'The configuration parameter "{config_name}" has not been set in the system config file')  
            continue 
        assert value_from_dict == value_from_system 

def test_ros_override():
    try:
        # the rospy param will override the config file if a ros node is running
        rospy.init_node('config_manager')
    except:
        return
    CONFIG:SystemConfig = SystemConfig(sample_system_config_file())
    # assign test param name
    test_param_name = 'test_param'
    # reset the param name in rospy in case it has been assigned before
    if rospy.has_param(f'~{test_param_name}'):
        rospy.delete_param(f'~{test_param_name}')
    # add the config param to CONFIG
    CONFIG[test_param_name] = 'Apple'
    assert CONFIG.get(test_param_name, None) == 'Apple'
    # assign data_folder as ros param
    rospy.set_param(f'~{test_param_name}', 'Pear')
    assert rospy.get_param(f'~{test_param_name}', None) == 'Pear'
    # test if the override has happened
    assert CONFIG.get(test_param_name, None) == 'Pear'

if __name__ == '__main__':
    test_setup_config()
    test_config_value_consistent()
    test_ros_override()