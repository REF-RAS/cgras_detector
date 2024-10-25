# Copyright 2024 - Andrew Kwok Fai LUI, 
# Robotics and Autonomous Systems Group, REF, RI
# and the Queensland University of Technology

__author__ = 'Andrew Lui'
__copyright__ = 'Copyright 2024'
__license__ = 'GPL'
__version__ = '1.0'
__email__ = 'ak.lui@qut.edu.au'
__status__ = 'Development'

import os, math, yaml, contextlib, glob, time, shutil
from enum import Enum
from collections import defaultdict, OrderedDict
import datetime
from time import strftime, localtime
import numpy as np
import pandas as pd

from tools.lock_tools import synchronized
from detector.models import logger, ModelsConfigNames
from detector.models.detect import ImageReconstructModel, ImageReconstructModelHelper, CoralObjectDetectModel, CoralObjectDetectModelHelper, YoloObjectDetector, CoralObject, ObjectClassCategories
from detector.models.locate_tile import LocateTileModel, LocateTileModelHelper
from detector.model import AIMSTILE_DAO, DETECT_DAO, APP_FILE_MANAGER, CONFIG, SystemConfigNames     


class ProgressStages(Enum):
    UNKNOWN = -1
    INIT = 0
    RECO = 1
    LOCTILE = 2
    OBJECT_DETECT = 3
    COLLECT_STAT = 4
    COMPLETED = 5

class ProgressModel():
    def __init__(self):
        self.progress = OrderedDict()
        self.start_time = OrderedDict()
        self.end_time = OrderedDict()
        for stage in ProgressStages:
            self.progress[stage] = [0, 0]  # (currnet step, num_steps)
            self.start_time[stage] = None
            self.end_time[stage]  = None
        self.current_stage = ProgressStages.UNKNOWN

    @synchronized
    def start_stage(self, stage:ProgressStages):
        self.current_stage = stage
        self.progress[stage][1] = 1
        self.start_time[stage] = time.time()

    @synchronized
    def update_stage_progress(self, stage:ProgressStages, current_step:int, num_steps:int):
        self.progress[stage][0] = current_step
        self.progress[stage][1] = num_steps

    @synchronized
    def end_stage(self, stage:ProgressStages):
        self.current_stage = stage        
        self.progress[stage][0] = self.progress[stage][1]
        self.end_time[stage] = time.time()

    @synchronized
    def get_total_time(self):
        total_time = 0
        for stage in ProgressStages:
            if self.start_time[stage] is not None and self.end_time[stage] is not None:
                total_time += self.end_time[stage] - self.start_time[stage]
        return total_time
    
    def get_progress_at_stage(self, stage):
        return self.progress[stage]


class DetectionTaskModel():
    def __init__(self, tile_sample_id:str, params:dict=None, **kwargs):
        # progress tracking
        self.progress_model = ProgressModel()
        self.progress_model.start_stage(ProgressStages.INIT)
        # model variables
        self.image_map_as_list:list = None
        self.image_grid_dim:tuple = None
        self.reco_model:ImageReconstructModel = None
        self.loctile_model:LocateTileModel = None
        self.cod_model:CoralObjectDetectModel = None
        self.detection_stat = {} 
        self.to_abort = False
        self.start_time = time.time()
        # extract information about this tile sample
        self.tile_sample_id = tile_sample_id
        self.tile_sample_dict = DETECT_DAO.get_tile_sample(self.tile_sample_id)
        if self.tile_sample_dict is None:
            logger.warning(f'{type(self).__name__}: The tile_sample_id ({self.tile_sample_id}) not found')
            raise AssertionError(f'Invalid parameter (tile_sample_id)')        
        self.tile_id, self.batch_id, self.batch_time = self.tile_sample_dict['tile_id'], self.tile_sample_dict['batch_id'], self.tile_sample_dict['batch_time']
        # extract information about the tile
        self.tile_dict = AIMSTILE_DAO.get_tile(self.tile_id)
        if self.tile_dict is None:
            logger.warning(f'{type(self).__name__}: The tile_id ({self.tile_id}) recorded in the tile sample ({self.tile_sample_id}) not found')
            raise AssertionError(f'Invalid parameter (tile_id)') 
        self.species, self.settle_time, self.season = self.tile_dict['species'], self.tile_dict['settle_time'], self.tile_dict['season']
        # evaluate the number of days since settlement
        self.settle_date_dt, self.capture_date_dt = pd.to_datetime(self.settle_time, utc=True), pd.to_datetime(self.batch_time, utc=True)
        self.days_since_settle = (self.capture_date_dt - self.settle_date_dt).days
        # resolve the suitable yolo model for this tile
        self.yolo_model_list = DETECT_DAO.query_yolo_model(self.species, self.days_since_settle)
        if self.yolo_model_list is None or len(self.yolo_model_list) == 0:
            logger.warning(f'{type(self).__name__}: No suitable yolo model for species ({self.species}) and days_since_settlement ({self.days_since_settle}) is found')
            raise AssertionError(f'No suitable yolo model for tile_sample_id ({self.tile_sample_id})') 
        # just pick the first one if more than one yolo model is suitable
        self.yolo_model_dict = self.yolo_model_list[0]
        # build parameters for the detection process
        if params is not None:
            self.params = params
        else:
            self.params = CONFIG.to_params([SystemConfigNames, ModelsConfigNames])
        self.logdata_folder = self.params[ModelsConfigNames.LOGDATA_FOLDER.value] = APP_FILE_MANAGER.get_detector_subfolder(APP_FILE_MANAGER.DATA_FOLDER, self.season, self.tile_sample_id)
        self.params[ModelsConfigNames.YOLO_MODEL_FILE.value] = self.yolo_model_dict['model_file_path']
        self.params[ModelsConfigNames.COD_BLOB_SIZE.value] = (self.yolo_model_dict['input_image_width'], self.yolo_model_dict['input_image_height'], )
        self.params[ModelsConfigNames.OBJECT_CLASSES_CORAL.value] = self.yolo_model_dict['coral_classes']
        self.params[ModelsConfigNames.OBJECT_CLASSES_DEAD_CORAL.value] = self.yolo_model_dict['dead_coral_classes']
        # add other tile info to the params for metadata yaml file output
        self.params['tile_sample_id'] = self.tile_sample_id
        self.params['tile_id'] = self.tile_id
        self.params['batch_id'] = self.batch_id
        self.params['batch_time'] = self.batch_time
        self.params['season'] = self.season
        self.params['settle_date'] = self.settle_time
        self.params['species'] = self.species
        self.params['coral_age_in_days'] = self.days_since_settle
        # write the params to the log folder
        task_params_metadata_filename = self.params.get(ModelsConfigNames.TASK_PARAMS_FILENAME.value, '_params.yaml')
        try:
            param_yaml_file = os.path.join(self.logdata_folder, task_params_metadata_filename)
            with open(param_yaml_file, 'w') as outfile:
                yaml.dump(self.params, outfile, Dumper=yaml.Dumper)
        except Exception as e:
            logger.warning(f'{type(self).__name__}: unable to save detect model parameter to the logdata folder {param_yaml_file}')
        # signal the end of the INIT stage
        self.progress_model.end_stage(ProgressStages.INIT)

    def get_tile_sample_id(self) -> str:
        return self.tile_sample_id
    
    def get_start_time(self) -> float:
        return self.start_time
    
    def get_time_lapsed(self) -> float:
        return time.time() - self.start_time    
    
    def get_start_time_iso8601(self) -> str:
        # return str(datetime.datetime.fromtimestamp(self.start_time))
        return strftime('%Y-%m-%d %H:%M:%S', localtime(self.start_time))
    
    def get_params(self) -> dict:
        return self.params

    @staticmethod
    def _build_image_map_as_list(tile_sample_id:str) -> list:
        captured_image_list = DETECT_DAO.query_source_images_of_tile_sample(tile_sample_id)
        capture_image_grid = defaultdict(lambda: None)
        # collect the image file path into a 2d grid first, before building a 2d list
        grid_size_x, grid_size_y = 0, 0
        for captured_image in captured_image_list:
            capture_image_grid[(captured_image['capture_x'], captured_image['capture_y'])] = captured_image['file_path']
            grid_size_x = max(grid_size_x, captured_image['capture_x'])
            grid_size_y = max(grid_size_y, captured_image['capture_y'])
        # build the 2d list
        image_map_as_list = []
        for y in range(grid_size_y + 1):
            row_images = []
            for x in range(grid_size_x + 1):
                if (x, y) not in capture_image_grid:
                    logger.warning(f'DetectionTaskModel._build_image_map_as_list: One or more images are missing in the 2d grid of images')
                    raise AssertionError('Unable to build image_map_as_list')
                row_images.append(capture_image_grid[(x, y)])
            image_map_as_list.append(row_images)
        return image_map_as_list, (grid_size_x, grid_size_y,)
    
    def execute_task_reco(self):
        self.progress_model.start_stage(ProgressStages.INIT)
        # build image_map_as_list from the captured images
        self.image_map_as_list, self.image_grid_dim = self._build_image_map_as_list(self.tile_sample_id)
        # load the cached ImageReconstructModel if exists, or build a new model from captured images
        reco_model_file = os.path.join(self.logdata_folder, self.params.get('reco_model_filename', 'reco_model.yaml'))
        try:
            logger.info(f'{type(self).__name__}: Attempting to load cached ImageReconstructModel')
            self.reco_model:ImageReconstructModel = ImageReconstructModelHelper.from_yaml_file(reco_model_file)
        except:
            logger.info(f'{type(self).__name__}: No cached file. Building the ImageReconstructModel from capture images')
            self.reco_model = ImageReconstructModel(self.image_map_as_list, working_scale=0.1, **self.params) 
            ImageReconstructModelHelper.to_yaml(self.reco_model, reco_model_file)
        self.progress_model.end_stage(ProgressStages.RECO)
        
    def execute_task_loctile(self):
        self.progress_model.start_stage(ProgressStages.LOCTILE)
        # load the cached LocateTileModel if exists, or build a new model from captured images and the ImageReconstructModel
        loctile_model_file = os.path.join(self.logdata_folder, self.params.get('loctile_model_filename', 'loctile_model.yaml'))
        try:
            logger.info(f'{type(self).__name__}: Attempting to load cached LocateTileModelHelper')
            self.loctile_model:LocateTileModel = LocateTileModelHelper.from_yaml_file(loctile_model_file)
        except:
            logger.info(f'{type(self).__name__}: No cached file. Building the loctile_model_file from capture images')
            self.loctile_model = LocateTileModel(self.image_map_as_list, reco_model=self.reco_model, **self.params)
            LocateTileModelHelper.to_yaml(self.loctile_model, loctile_model_file)
        self.progress_model.end_stage(ProgressStages.LOCTILE)
                
    def execute_task_object_detection(self):
        self.progress_model.start_stage(ProgressStages.OBJECT_DETECT)
        self.progress_model.update_stage_progress(ProgressStages.OBJECT_DETECT, 0, self.image_grid_dim[0] * self.image_grid_dim[1])
        # load the cached CoralObjectDetectionModel if exists, or build a new model from captured images, the ImageReconstructModel, and the yolo model
        cod_model_file = os.path.join(self.logdata_folder, self.params.get('cod_model_filename', 'coral_object_detect_model.yaml'))
        try:
            logger.info(f'{type(self).__name__}: Attempting to load cached CoralObjectDetectModel')
            self.cod_model = CoralObjectDetectModelHelper.from_yaml_file(cod_model_file)
            ### NOTE: fix the coral object strucutres
            # for co in self.cod_model.object_list:
            #     if co.is_coral:
            #         co.class_category = ObjectClassCategories.CORAL.value
            #     else:
            #         co.class_category = ObjectClassCategories.NOT_CORAL.value
            # CoralObjectDetectModelHelper.to_yaml_file(self.cod_model, cod_model_file) 
        except:
            logger.info(f'{type(self).__name__}: No cached file. Building the CoralObjectDetectModel from capture images, reco model, loctile model, and yolo model')
            # load the yolo_model first
            yolo_model_file=self.params.get(ModelsConfigNames.YOLO_MODEL_FILE.value)
            if self.to_abort:
                self.progress_model.end_stage(ProgressStages.OBJECT_DETECT)  
                return
            try:
                logger.info(f'{type(self).__name__}: Attempting to load the yolo_model_file at {yolo_model_file}')
                yolo_model:YoloObjectDetector = YoloObjectDetector(yolo_model_file)
            except Exception as e:
                logger.info(f'{type(self).__name__}: Failed to load the yolo model file: {e}')
                raise AssertionError(f'The yolo model file is invalid or not present')
            # build the cod model
            if self.to_abort:
                self.progress_model.end_stage(ProgressStages.OBJECT_DETECT)  
                return
            self.cod_model = CoralObjectDetectModel(self.image_map_as_list, self.reco_model, yolo_model, self.loctile_model, self._execute_task_object_detection_cb, **self.params)
            CoralObjectDetectModelHelper.to_yaml_file(self.cod_model, cod_model_file)  
        self.progress_model.end_stage(ProgressStages.OBJECT_DETECT)        

    def _execute_task_object_detection_cb(self, progress_tuple:tuple):
        if progress_tuple is not None:
            self.progress_model.update_stage_progress(ProgressStages.OBJECT_DETECT, *progress_tuple)
            
    def execute_task_collect_stat(self):
        self.progress_model.start_stage(ProgressStages.COLLECT_STAT)        
        # extract statistics of the tile 
        self.detection_stat['tile_pixel_x'], self.detection_stat['tile_pixel_y'] = self.reco_model.get_whole_reco_image_size()
        # detection of coral objects is completed, save the results to the database
        logger.info(f'{type(self).__name__}: Saving {self.cod_model.get_num_objects()} coral objects to database')
        DETECT_DAO.delete_detected_objects_of_tile_sample(self.tile_sample_id)
        if self.to_abort:
            self.progress_model.end_stage(ProgressStages.COLLECT_STAT) 
            return
        stat = self._process_detected_objects(self.cod_model)
        self.detection_stat.update(stat)
        # save the statistics to the database
        self._update_detection_stat(self.detection_stat)
        self.progress_model.end_stage(ProgressStages.COLLECT_STAT) 
        self.progress_model.end_stage(ProgressStages.COMPLETED)

    def execute_task(self):
        self.execute_task_reco()
        self.execute_task_loctile()
        self.execute_task_object_detection()
        self.execute_task_collect_stat()

    def abort_task(self):
        self.to_abort = True
        if self.cod_model is not None:
            self.cod_model.abort()

    def get_time_since_start(self):
        return time.time() - self.start_time

    def get_progress(self) -> ProgressModel:
        return self.progress_model

    def _update_detection_stat(self, detection_stat:dict):
        yaml_data = yaml.dump(detection_stat)
        DETECT_DAO.update_tile_sample_detect_stat(self.tile_sample_id, detection_stat['tile_pixel_x'], detection_stat['tile_pixel_y'], 
                            detection_stat['coral_object_count'], detection_stat['dead_coral_object_count'], detection_stat['other_object_count'], 
                            detection_stat['duplicates_removed'], yaml_data)
         
    def _process_detected_objects(self, cod_model:CoralObjectDetectModel) -> dict:
        dead_coral_classes = self.params['dead_coral_classes']
        stat = {
            'coral_object_count': 0,
            'dead_coral_object_count': 0,
            'other_object_count': 0,
            'duplicates_removed': cod_model.get_num_invalidated_objects(),
            'total_object_count': cod_model.get_num_objects(),
        }
        coral_object_list:list = cod_model.get_object_list()
        coral_object:CoralObject
        for coral_object in coral_object_list:
            if coral_object.invalidated:
                continue
            centre_x, centre_y = coral_object.centre_normalized[0], coral_object.centre_normalized[1]
            corner_x1, corner_y1 = coral_object.bbox_normalized[0], coral_object.bbox_normalized[1]
            size_x, size_y = coral_object.bbox_normalized[2] - corner_x1, coral_object.bbox_normalized[3] - corner_y1
            if coral_object.class_category == ObjectClassCategories.CORAL.value:
                stat['coral_object_count'] += 1
            else:
                if coral_object.cls_name in dead_coral_classes:
                    stat['dead_coral_object_count'] += 1
                else:
                    stat['other_object_count'] += 1
            DETECT_DAO.add_detected_object_from_coral_object(self.tile_sample_id, coral_object)
        return stat

    @staticmethod
    def delete_cache_files(tile_sample_id:str, delete_reco=False, delete_object_detection=False):
        tile_sample_dict = DETECT_DAO.get_tile_sample(tile_sample_id)
        logdata_folder = APP_FILE_MANAGER.get_detector_subfolder(APP_FILE_MANAGER.DATA_FOLDER, tile_sample_dict['season'], tile_sample_id)
        with contextlib.suppress(FileNotFoundError, Exception):
            if delete_reco:
                os.remove(os.path.join(logdata_folder, CONFIG.get(ModelsConfigNames.RECO_MODEL_FILENAME.value, 'reco_model.yaml')))
                os.remove(os.path.join(logdata_folder, CONFIG.get(ModelsConfigNames.LOCTILE_MODEL_FILENAME.value, 'loctile_model.yaml')))
            
            if delete_object_detection:            
                os.remove(os.path.join(logdata_folder, CONFIG.get(ModelsConfigNames.COD_MODEL_FILENAME.value, 'coral_object_detect_model.yaml')))
                for file in glob.glob(os.path.join(logdata_folder, 'object_list_*.yaml')):
                    os.remove(file) 
                    
    @staticmethod
    def delete_cache_folder(tile_sample_id:str):
        tile_sample_dict = DETECT_DAO.get_tile_sample(tile_sample_id)
        logdata_folder = APP_FILE_MANAGER.get_detector_subfolder(APP_FILE_MANAGER.DATA_FOLDER, tile_sample_dict['season'], tile_sample_id)
        with contextlib.suppress(FileNotFoundError, Exception):
            shutil.rmtree(logdata_folder, ignore_errors=True)        

# ---------------------------------------
# test functions

def get_basic_detection_params() -> dict:
    params = {
        'reco_model_filename': 'reco_model.yaml',
        'loctile_model_filename': 'loctile_model.yaml',
        'reco_debug_images_at_original_scale': False,
        'reco_debug_feature_matching_images': True,
        'reco_feature_detector': 'sift',
        'reco_matching_confidence_threshold': 0.4,
        'reco_working_scale': 0.1,
        'cod_model_filename': 'coral_object_detect_model.yaml', 
        'cod_debug_blob_images': True,
        'cod_blob_overlap_pix': 32,
        'cod_use_cached_object_detection': True,
        'cod_duplicate_max_displacement_images': 16,
        'cod_duplicate_max_displacement_blobs': 32, 
        # to be updated in the DetectionTaskModel using the database
        'logdata_folder': None, 
        'yolo_model_file': None,  
        'cod_blob_size': None,     
        'coral_classes': None,                                                             
    }  
    return params


if __name__ == '__main__':
    # tile_sample_id = '2023Dec-P00003-CG1-202311201200'
    tile_sample_id = '2023Dec-P10001-CG1-202402161404'
    dt_model = DetectionTaskModel(tile_sample_id, get_basic_detection_params())
    dt_model.execute_task()
    
    # DetectionTaskModel.delete_cache_files(tile_sample_id, True, True)
