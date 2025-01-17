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
from cgras_datatools.logging_tools import logger

class DetectorExceptionCodes(Enum):
    UNDEFINED = 0
    INPUT_DATA_INVALID = 1
    RECO_MATCH_FAILED = 2
    RECO_FAILED = 3
    LOC_FAILED = 4
    LOC_FRAME_MISSING = 5 
    YOLO_MODEL_UNDEFINED = 6
    YOLO_MODEL_ERROR = 7
    YOLO_MODEL_FILE_ERROR = 8
    CANCELLED_BY_SYSTEM = 11
    FILE_IO_ERROR = 21
    DB_ERROR = 22
    OS_ERROR = 31
    DISK_SPACE_ERROR = 32

class DetectorException(Exception):
    def __init__(self, code:DetectorExceptionCodes, remarks:str=None, e=None, source=None):            
        # Call the base class constructor with the parameters it needs
        super().__init__(remarks)
        if isinstance(code, DetectorExceptionCodes):
            self.code = code
        else:
            logger.warning(f'DetectorError: Parameter code is not one of DetectorErrorCodes')
            self.code = DetectorExceptionCodes.UNDEFINED
        self.source = source
        self.remarks = remarks
        self.e = e
    
    def get_code(self) -> DetectorExceptionCodes:
        return self.code
    
    def get_source(self):
        return self.source
    
    def get_remarks(self):
        return self.remarks

class DetectorFailed(DetectorException):
    def __init__(self, code:DetectorExceptionCodes, remarks:str=None, e=None, source=None):            
        # Call the base class constructor with the parameters it needs
        super().__init__(code, remarks, e, source)

class DetectorAborted(DetectorException):
    def __init__(self, code:DetectorExceptionCodes, remarks:str=None, e=None, source=None):            
        # Call the base class constructor with the parameters it needs
        super().__init__(code, remarks, e, source) 
        
class DetectorCancelled(DetectorException):
    def __init__(self, code:DetectorExceptionCodes, remarks:str=None, e=None, source=None):            
        # Call the base class constructor with the parameters it needs
        super().__init__(code, remarks, e, source)    