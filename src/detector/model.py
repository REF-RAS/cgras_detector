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
# project modules
import detector.model_base as model_base
from detector.system_config import SystemConfig, SystemConfigNames
from tools.logging_tools import global_logger
import catkin_pkg.package

from detector.database_manager import DBFileManager
from detector.dao_detect import DETECT_DDL, DetectorDAO, CoralObject, ObjectClassCategories, StatusNames, TaskTypes
from detector.dao_persistent_storage import PersistentStoreDAO
from detector.dao_aims import AIMSTILE_DDL, AIMSTileDAO
from detector.file_manager import ApplicationFileManager

# --- System-wide definitions and variables 
# The callback types
class CallbackTypes(Enum):
    TIMER = 0
    TASK_EXECUTE_MODE_CHANGED = 1
    PROCESS_TILE_CLICKED = 3
    UPDATE_HEALTH_CLICKED = 4
    IMPORT_TILES_CLICKED = 5
    PROCESS_TILE_TO_ABORT = 11

# The states of the system for tracking the current task
class SystemStates(Enum):
    D_ABORTED = 19
    WARNING = -2
    ERROR = -3
    READY = 0
    AUTO_START = 1        
    CLICK_START = 2
    POLL_DETECT = 3
    D_INIT = 11
    D_RECO = 12   
    D_LOCTILE = 13
    D_OBJECT = 14
    D_COLLECT_STAT = 15
    D_UPDATE_HEALTH_INDEX = 16
    D_SUCCESS = 17
    D_FAILED = 18
    POLL_UPDATE_HEALTH_INDEX = 31
    H_UPDATE_INDEX_ALL = 32
    POLL_SAMPLE = 41
    S_NEW_SAMPLE = 42
    
# The states of the Image Acquisition system 
# the global variable for the light state
class CapturerStates(Enum):
    UNKNOWN = -1
    IDLE = 0
    ACTIVE = 1

# global variable for accessing the system configuration
CONFIG:SystemConfig = SystemConfig(os.path.join(os.path.dirname(__file__), '../../config/system_config.yaml'))
CGRAS_DATA_FOLDER = CONFIG.get(SystemConfigNames.CGRAS_DATA_FOLDER, '/home/qcr/cgras_data')
# global variables for import by other modules
STATE = model_base.StateManager(SystemStates.READY)                              # the state of the detection and visualization processor
CALLBACK_MANAGER:model_base.CallbackManager = model_base.CallbackManager()      # the callback manager for linking the GUI and the processor
# create the application file manager and populate the system asset folder that contains js libraries and images for web pages
APP_FILE_MANAGER:ApplicationFileManager = ApplicationFileManager(CGRAS_DATA_FOLDER)      # the object manages the data folders for the application
APP_FILE_MANAGER.populate_system_assets_folder()

# global variables for managing database tables
AIMSTILE_DBFM = DBFileManager(APP_FILE_MANAGER.database_folder, 'tile.db', AIMSTILE_DDL)
AIMSTILE_DAO:AIMSTileDAO = AIMSTileDAO(AIMSTILE_DBFM.db_file)
DETECT_DBFM = DBFileManager(APP_FILE_MANAGER.database_folder, 'detector.db', DETECT_DDL)
DETECT_DAO:DetectorDAO = DetectorDAO(DETECT_DBFM.db_file)
PERSISTENT_STORE_DAO:PersistentStoreDAO = PersistentStoreDAO(DETECT_DBFM.db_file)

# the states of other components
CAPTURER_STATE = model_base.StateManager(CapturerStates.UNKNOWN)
