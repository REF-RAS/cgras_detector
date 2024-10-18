# Copyright 2024 - Andrew Kwok Fai LUI, 
# Robotics and Autonomous Systems Group, REF, RI
# and the Queensland University of Technology

__author__ = 'Andrew Lui'
__copyright__ = 'Copyright 2024'
__license__ = 'GPL'
__version__ = '1.0'
__email__ = 'ak.lui@qut.edu.au'
__status__ = 'Development'

import os, math, random, re
from datetime import datetime
from enum import Enum
from cgras.tools.logging_tools import init_logger
from .models_config import ModelsConfigNames

class Constants(Enum):
    SCALE_ORIGINAL = 0
    SCALE_WORKING = 1

logger = init_logger()
