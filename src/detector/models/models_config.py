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
    RECO_FEATURE_MATCHING_CONFIDENCE_THRESHOLD = 'reco_feature_matching_confidence_threshold'
    RECO_IMAGE_MATCHING_MIN_CONFIDENCE = 'reco_image_matching_min_confidence'
    RECO_IMAGE2D_MATCHING_MIN_CONFIDENCE = 'reco_image2d_matching_min_confidence'
    RECO_WORKING_SCALE = 'reco_working_scale'
    RECO_ERROR_CORRECTION = 'reco_error_correction'
    
    # WHOLE_TILE_IAMGE_SIZE = 'whole_tile_image_size'     # the size of the tile (including tile holder) in pixels (for correction of rotated image and default value if the corner is not found)
    # TILE_HOLDER_WIDTH = 'tile_holder_width'             # the width of the tile holder in pixels
    
    TILE_SIZE_IN_MM = 'tile_size_in_mm'     # the size of the tile in mm (width, height)
    FRAME_SIZE_IN_MM = 'frame_size_in_mm'   # the size of the frame in mm (width, height)
    
    # LOCTILE_BLUE_RATIO_MIN = 'loctile_blue_ratio_min'     # NOTE: not used because the background classifier is a machine learning model
    # LOCTILE_RED_RATIO_MAX = 'loctile_red_ratio_max'       # NOTE: not used because the background classifier is a machine learning model
    
    LOCTILE_WORKING_SCALE = 'loctile_working_scale'
    LOCTILE_TEMPLATE_SIZE = 'loctile_template_size'
    LOCTILE_MATCHING_SCORE_MIN = 'loctile_matching_score_min'
    LOCTILE_DEBUG_IMAGES = 'loctile_debug_images'
    
    COD_MODEL_FILENAME = 'cod_model_filename'
    COD_DEBUG_BLOB_IMAGES = 'cod_debug_blob_images'
    COD_BLOB_OVERLAP_PIX = 'cod_blob_overlap_pix'
    COD_USE_CACHED_OBJECT_DETECTION = 'cod_use_cached_object_detection'
    COD_CORAL_CHILD_MIN_OVERLAP_RATIO = 'cod_coral_child_min_overlap_ratio'
    COD_MERGE_MULTI_MODELS = 'cod_merge_mutli_models'
    # COD_DUPLICATE_MAX_DISPLACEMENT_IMAGES = 'cod_duplicate_max_displacement_images'
    # COD_DUPLICATE_MAX_DISPLACEMENT_BLOBS = 'cod_duplicate_max_displacement_blobs'
    
    # the following are parameters generated dynamically during task execution
    LOGDATA_FOLDER = 'logdata_folder'
    COD_BLOB_SIZE = 'cod_blob_size'
    OBJECT_CLASSES_CORAL = 'coral_classes'
    OBJECT_CLASSES_DEAD_CORAL = 'dead_coral_classes'
    OBJECT_CLASSES_MAP = 'classes_map'
    YOLO_MODEL_FILE = 'yolo_model_file'
    
