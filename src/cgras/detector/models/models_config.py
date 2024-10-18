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

class ModelsConfigNames(Enum):
    """ Maps the config names as a sting to a constant
    """
    TASK_PARAMS_FILENAME = 'task_params_filename'
    RECO_MODEL_FILENAME = 'reco_model_filename'
    LOCTILE_MODEL_FILENAME = 'loctile_model_filename'
    RECO_DEGUG_IMAGE_ORIGINAL_SCALE = 'reco_debug_images_at_original_scale'
    RECO_DEBUG_FEATURE_MATCH_IMAGES = 'reco_debug_feature_matching_images'
    RECO_FEATURE_DETECTOR = 'reco_feature_detector'
    RECO_MATCHING_CONFIDENCE_THRESHOLD = 'reco_matching_confidence_threshold'
    COD_MODEL_FILENAME = 'cod_model_filename'
    COD_DEBUG_BLOB_IMAGES = 'cod_debug_blob_images'
    COD_BLOB_OVERLAP_PIX = 'cod_blob_overlap_pix'
    COD_USE_CACHED_OBJECT_DETECTION = 'cod_use_cached_object_detection'
    COD_DUPLICATE_MAX_DISPLACEMENT_IMAGES = 'cod_duplicate_max_displacement_images'
    COD_DUPLICATE_MAX_DISPLACEMENT_BLOBS = 'cod_duplicate_max_displacement_blobs'
    # the following are parameters generated dynamically during task execution
    LOGDATA_FOLDER = 'logdata_folder'
    COD_BLOB_SIZE = 'cod_blob_size'
    OBJECT_CLASSES_CORAL = 'coral_classes'
    OBJECT_CLASSES_DEAD_CORAL = 'dead_coral_classes'
    YOLO_MODEL_FILE = 'yolo_model_file'
    
