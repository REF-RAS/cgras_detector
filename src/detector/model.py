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
from cgras_datatools.logging_tools import logger
import catkin_pkg.package

from detector.database_file import DBFile
from detector.dao_detect import DETECT_DDL, DetectorDAO, CoralObject, ClassHierarchyCoral, ClassHierarchyPresentation, TaskStatusNames, TaskTypes, SampleStatusNames
from detector.dao_persistent_storage import PERSISTENT_STORE_DDL, PersistentStoreDAO
from detector.file_manager import ApplicationFileManager

# --- System-wide definitions and variables 
# The callback types
class CallbackTypes(Enum):
    TIMER = 0
    TASK_EXECUTE_MODE_CHANGED = 1
    PROCESS_TILE_CLICKED = 3
    UPDATE_HEALTH_CLICKED = 4
    IMPORT_SAMPLE_CLICKED = 5
    PROCESS_TILE_TO_CANCEL = 11

# The states of the system for tracking the current task
class SystemStates(Enum):
    SUSPENDED = -1
    # WARNING = -2
    # ERROR = -3
    READY = 0
    AUTO_START = 1        
    CLICK_START = 2
    POLL_DETECT = 3
    DETECT = 10
    WAIT_DETECT = 11
    D_SUCCESS = 16
    D_CANCELLED = 17
    D_FAILED = 18
    D_FLAGGED = 19
    POLL_IMPORT_SAMPLE = 41
    IMPORT_SAMPLE = 42
    
# The states of the Image Acquisition system 
class CoordinatorStates(Enum):
    ERROR = -1
    UNKNOWN = 0
    IDLE = 1
    WORKING = 2
    
# General Class for synchronized set to a value 
class ValueHolder:
    value = None
    value_lock = threading.RLock()
    def set_value(self, value):
        with self.value_lock:
            self.value = value

# global variable for accessing the system configuration
CONFIG:SystemConfig = SystemConfig(os.path.join(os.path.dirname(__file__), '../../config/system_config.yaml'))
CGRAS_DATA_FOLDER = os.path.expanduser(CONFIG.get(SystemConfigNames.CGRAS_DATA_FOLDER, '/home/qcr/cgras_data'))
# global variables for import by other modules
STATE = model_base.StateManager(SystemStates.READY)                              # the state of the detection and visualization processor
CALLBACK_MANAGER:model_base.CallbackManager = model_base.CallbackManager()      # the callback manager for linking the GUI and the processor
# create the application file manager and populate the system asset folder that contains js libraries and images for web pages
APP_FILE_MANAGER:ApplicationFileManager = ApplicationFileManager(CGRAS_DATA_FOLDER)      # the object manages the data folders for the application
APP_FILE_MANAGER.populate_system_assets_folder()
# global variable for system configuration states
AUTOMATED_TASK_EXECUTION = ValueHolder()

# global variables for managing database tables
DETECT_DBFM = DBFile(APP_FILE_MANAGER.database_folder, 'detector.db', [DETECT_DDL, PERSISTENT_STORE_DDL])
DETECT_DAO:DetectorDAO = DetectorDAO(DETECT_DBFM.db_file)
PERSISTENT_STORE_DAO:PersistentStoreDAO = PersistentStoreDAO(DETECT_DBFM.db_file)
# the states of other components
COORDINATOR_STATE = model_base.StateManager(CoordinatorStates.UNKNOWN)
