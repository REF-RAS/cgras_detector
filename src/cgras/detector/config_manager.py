# Copyright 2024 - Andrew Kwok Fai LUI, 
# Robotics and Autonomous Systems Group, REF, RI
# and the Queensland University of Technology

__author__ = 'Andrew Lui'
__copyright__ = 'Copyright 2024'
__license__ = 'GPL'
__version__ = '1.0'
__email__ = 'ak.lui@qut.edu.au'
__status__ = 'Development'

import yaml
from collections.abc import MutableMapping

class SystemConfigNames():
    """ Maps the config names as a sting to a constant
    """
    CGRAS_DATA_FOLDER = 'cgras.data.folder'
    CGRAS_DETECTOR_SUBFOLDER = 'cgras.detector.subfolder'
    CGRAS_DETECTOR_WEB_HOST = 'cgras.detector.web.host'
    CGRAS_DETECTOR_WEB_PORT = 'cgras.detector.web.port'
    CGRAS_DETECTOR_WEB_DEBUG_MODE = 'cgras.detector.web.debug.mode'
    CGRAS_DETECTOR_WEB_LAUNCH_BROWSER = 'cgras.detector.web.launch_browser'

    CGRAS_DETECTOR_SYSTEM_TIMER = 'cgras.detector.system.timer'
    CGRAS_DETECTOR_DASHBOARD_REFRESH = 'cgras.detector.dashboard.refresh'

    CGRAS_DETECTOR_MAX_CORAL_DAYS = 'cgras.detector.max_coral_days'
    CGRAS_CONNECTION_TIMEOUT = 'cgras.connection.timeout'


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
        self.update(dict(*args, **kwargs))
        
    def __getitem__(self, key):
        return self.config[self._keytransform(key)]

    def __setitem__(self, key, value):
        self.config[self._keytransform(key)] = value

    def __delitem__(self, key):
        del self.config[self._keytransform(key)]

    def __iter__(self):
        return iter(self.config)
    
    def __len__(self):
        return len(self.config)

    def _keytransform(self, key):
        return key
    # -------------------------------------------
    # model functions

    # returns the value of a named config given as a dot-separated path 
    def query(self, key_path:str, default=None):
        """ returns the value of any named config given as a dot-separated path
        :param key_path: the dot-separated path
        :type key_path: str
        :param default: the default value if nothing is found in the path, defaults to None
        :type default: any
        :return: the value of the config key
        :rtype: any
        """
        if key_path is None:
            return default
        name_as_list = key_path.split('.')
        pointer = self.config
        # iterate the parts of the config name
        for item in name_as_list:
            if item.isnumeric():
                item = int(item)
                if item < 0 or item >= len(pointer):
                    print(f'query_config: part of the name contains an invalid index {item}')
                    # raise AssertionError(f'query_config: Non-existent config name "{name}", which contains an invalid index {item}')
                    return default
                pointer = pointer[item]
            else:
                if item not in pointer:
                    print(f'query_config: part of the name contains an invalid key {item}')
                    # raise AssertionError(f'query_config: Non-existent the config name "{name}", which contains an invalid key {item}')
                    return default
                pointer = pointer[item]
        return pointer
    