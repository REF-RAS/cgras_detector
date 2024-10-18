# Copyright 2024 - Andrew Kwok Fai LUI, 
# Robotics and Autonomous Systems Group, REF, RI
# and the Queensland University of Technology

__author__ = 'Andrew Lui'
__copyright__ = 'Copyright 2024'
__license__ = 'GPL'
__version__ = '1.0'
__email__ = 'ak.lui@qut.edu.au'
__status__ = 'Development'

# general modules
import os, sys, threading, collections, time
from enum import Enum
from datetime import datetime
# project modules
from cgras.tools.logging_tools import logger

class ApplicationFileManager():
    def __init__(self, cgras_data_folder):
        self.log_lock = threading.Lock()
        self.user_home = os.path.expanduser('~') 
        self.cgras_data_folder = cgras_data_folder
        # crate subfolders
        self.images_folder = os.path.join(self.cgras_data_folder, 'images')
        os.makedirs(self.images_folder, exist_ok=True)
        self.database_folder = os.path.join(self.cgras_data_folder, 'database')
        os.makedirs(self.database_folder, exist_ok=True)        
        self.coordinator_folder = os.path.join(self.cgras_data_folder, 'coordinator')
        os.makedirs(self.coordinator_folder, exist_ok=True)
        self.detector_folder = os.path.join(self.cgras_data_folder, 'detector')
        os.makedirs(self.detector_folder, exist_ok=True)
        # create the subfolders under the two platforms
        self._create_platform_folders(self.coordinator_folder)
        self._create_platform_folders(self.detector_folder)
    
    @staticmethod
    def _create_platform_folders(platform_home):
        system_folder = os.path.join(platform_home, 'system')
        os.makedirs(system_folder, exist_ok=True)
        data_folder = os.path.join(platform_home, 'data')
        os.makedirs(data_folder, exist_ok=True)       
        temp_folder = os.path.join(platform_home, 'temp')
        os.makedirs(temp_folder, exist_ok=True)                   
    
    def get_cgras_home(self) -> str:
        return self.cgras_data_folder    
    
    def get_images_folder(self) -> str:
        return self.images_folder

    def get_database_folder(self) -> str:
        return self.database_folder
    
    def get_capturer_folder(self, *args) -> str:
        return self.get_subfolder(self.coordinator_folder, *args)
    
    def get_detector_folder(self, *args) -> str:
        return self.get_subfolder(self.detector_folder, *args)
    
    def get_detector_data_folder(self, *args) -> str:
        return self.get_subfolder(self.detector_folder, 'data', *args)   
    
    @staticmethod
    def get_subfolder(parent_folder:str, *args) -> str:
        """ return the path string of a subfolder of a parent_folder, and create the folder if not exists, with the partial paths specified as
            positional raguments

        :param parent_folder: the parent folder path 
        :type parent_folder: str
        :return: the full path to the subfolder, which has been created if not exists
        :rtype: str
        """
        if args is not None and len(args) > 0:
            parent_folder = os.path.join(parent_folder, *args)
            os.makedirs(parent_folder, exist_ok=True)
        return parent_folder
    
    def record_event(self, message):
        ...


