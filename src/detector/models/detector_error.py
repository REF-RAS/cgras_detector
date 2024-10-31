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
import os, sys, threading, collections, time, shutil, traceback
from enum import Enum
from datetime import datetime
# project modules
from tools.logging_tools import logger

class DetectorErrorCodes(Enum):
    IMAGE_FILE_NOT_FOUND = 1
    FILE_NOT_IMAGE = 2
    IMAGE_FILES_NOT_SAME_SIZE = 3


class DetectorError(Exception):
    def __init__(self, id:int, remarks:str, e=None):            
        # Call the base class constructor with the parameters it needs
        super().__init__(remarks)
        if isinstance(id, Enum):
            id = id.value
        self.remarks = remarks
        self.id = id
        self.e = e
    
    def get_id(self):
        return self.id
    
    def get_remarks(self):
        return self.remarks