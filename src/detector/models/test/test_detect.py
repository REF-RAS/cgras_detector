# Copyright 2024 - Andrew Kwok Fai LUI, 
# Robotics and Autonomous Systems Group, REF, RI
# and the Queensland University of Technology

__author__ = 'Andrew Lui'
__copyright__ = 'Copyright 2024'
__license__ = 'GPL'
__version__ = '1.0'
__email__ = 'ak.lui@qut.edu.au'
__status__ = 'Development'

import os
from detector.models.reconstruct import ImageReconstructModel, ImageReconstructModelHelper
from detector.models.locate_tile import LocateTileModel, LocateTileModelHelper
from detector.models.models_config import ModelsConfigNames
from detector.models.imaging_tools import ImageFileTools
from detector.models.detect import CoralObjectDetectModel, CoralObjectDetectModelHelper, CoralObjectListHelper, YoloObjectDetector

def sample_reconstruct_params():
    logdata_folder = '/home/qcr/cgras_data/test/detector'
    params = {
        'logdata_folder': logdata_folder, 
        ModelsConfigNames.RECO_MODEL_FILENAME.value: 'reco_model.yaml',
        ModelsConfigNames.RECO_DEGUG_IMAGE_ORIGINAL_SCALE.value: False,
        ModelsConfigNames.RECO_DEBUG_FEATURE_MATCH_IMAGES.value: True,
        ModelsConfigNames.RECO_FEATURE_DETECTOR.value: 'brisk',
        ModelsConfigNames.RECO_FEATURE_MATCHING_CONFIDENCE_THRESHOLD.value: 1.0,
        ModelsConfigNames.RECO_IMAGE_MATCHING_MIN_CONFIDENCE.value: 1.0,
        ModelsConfigNames.RECO_IMAGE2D_MATCHING_MIN_CONFIDENCE.value: 1.0,
        ModelsConfigNames.RECO_WORKING_SCALE.value: 0.1, 
    } 
    return params

def sample_loctile_params():
    logdata_folder = '/home/qcr/cgras_data/test/detector'
    params = {
        'logdata_folder': logdata_folder, 
        ModelsConfigNames.RECO_WORKING_SCALE.value: 0.1, 
        ModelsConfigNames.LOCTILE_MODEL_FILENAME.value: 'loctile_model.yaml',
        ModelsConfigNames.LOCTILE_DEBUG_IMAGES.value: True,
        ModelsConfigNames.WHOLE_TILE_IAMGE_SIZE.value: None, # [24280, 24460],
        ModelsConfigNames.TILE_HOLDER_WIDTH.value: 50,
        ModelsConfigNames.LOCTILE_BLUE_RATIO_MIN.value: 0.40,
        ModelsConfigNames.LOCTILE_RED_RATIO_MAX.value: 0.15,
        ModelsConfigNames.LOCTILE_WORKING_SCALE.value: 0.05,
        ModelsConfigNames.LOCTILE_TEMPLATE_SIZE.value: 20,
        ModelsConfigNames.LOCTILE_MATCHING_SCORE_MIN.value: 0.5,
    } 
    return params


def sample_tile_sample_filepath():
    filepath = os.path.join(os.path.dirname(__file__), '../../../../docs/detector_tile_sample_import_chris_mis5_t01_241119.yaml')
    return filepath

def test_load_reco_model():
    # load params for building reco_model
    params = sample_reconstruct_params()  
    # compute filepath
    reco_model_filepath = os.path.join(params['logdata_folder'], params[ModelsConfigNames.RECO_MODEL_FILENAME.value])     
    reco_model:ImageReconstructModel = ImageReconstructModelHelper.from_yaml_file(reco_model_filepath)
    reco_model.print_info()    
    return reco_model

def test_build_loctile_model():
    # load images_2d_list
    tile_sample_yaml_filepath = sample_tile_sample_filepath()
    images_2d_list = ImageFileTools.tile_sample_file_to_image_2d_list(tile_sample_yaml_filepath)
    image_grid_dimension = (len(images_2d_list[0]), len(images_2d_list), )
    print(f'images_2d_list dimension: {image_grid_dimension}')
    # load reco_model
    reco_model = test_load_reco_model()
    # load params for building loctile model
    params = sample_loctile_params() 
    # create LocateTileModel
    try:
        loctile_model = LocateTileModel(images_2d_list=images_2d_list, map_location_fn=reco_model.map_locations, **params)
        loctile_model.build()
    except Exception as e:
        raise AssertionError(f'Error in building LocateTileModel: {e}')
    # save LocateTileModel
    try:
        loctile_model_filepath = os.path.join(params['logdata_folder'], params.get(ModelsConfigNames.LOCTILE_MODEL_FILENAME.value, 'loctile_model.yaml'))
        LocateTileModelHelper.to_yaml(loctile_model, loctile_model_filepath)
    except Exception as e:
        raise AssertionError(f'Error in saving LocateTileModel: {e}')

def test_load_and_use_loctile_model():
    # load params for building loctile model
    params = sample_loctile_params()
    # load the previously built loctile model
    loctile_model_filepath = os.path.join(params['logdata_folder'], params[ModelsConfigNames.LOCTILE_MODEL_FILENAME.value])     
    loctile_model:LocateTileModel = LocateTileModelHelper.from_yaml_file(loctile_model_filepath)
    # run tests: mapping locations
    print('test mapping locations')
    original_points = [(945, 425), (25237, 807), (594, 24887), (24928, 25365)]
    truth_values = [(0, 0), (24295, 16), (17, 24464), (24355, 24576)]
    for point, truth in zip(original_points, truth_values):
        result = loctile_model.map_locations(point)
        print(point, result, truth)
        assert result == truth
    # run tests: mapping locations and normalize
    print('test mapping locations and normalize')
    original_bbox = [(945, 425, 25237, 807), (594, 24887, 24928, 25365)]
    truth_values = [(0, 0, 24295, 16), (17, 24464, 24355, 24576)]
    for bbox, truth in zip(original_bbox, truth_values):
        result = loctile_model.map_and_normalize_bbox(bbox)
        print(point, result, truth)

# ----------------------------------------------------------------------------------
# Test functions

def test_index_permutations():
    # perm_list = CoralObjectListHelper.get_index_permutations(list(range(10)))
    # for perm in perm_list:
    #     print(perm)
    for perm in CoralObjectListHelper.index_permutations(list(range(4))):
        print(perm)

def test_coral_object_detect_model(params, print=False):
    """ Test loading a reco model, a loctile model and a YOLO model from the file system, and use them to construct the CoralObjectDetectModel from scratch
    """
    print(f'test_coral_object_detect_model: started')
    logdata_folder = params['logdata_folder']
    # load a reco model
    reco_model_file = os.path.join(logdata_folder, params['reco_model_filename'])
    reco_model:ImageReconstructModel = ImageReconstructModelHelper.from_yaml_file(reco_model_file)
    # load a loctile model
    loctile_model_file = os.path.join(logdata_folder, params['loctile_model_filename'])
    loctile_model:LocateTileModel = LocateTileModelHelper.from_yaml_file(loctile_model_file)
    # load a yolo model
    yolo_model_file = params['yolo_model_file']
    yolo_model:YoloObjectDetector = YoloObjectDetector(yolo_model_file=yolo_model_file)
    # retrieve source images for analysis, which had been used to build the reco and the loctile models
    # load images_2d_list
    tile_sample_yaml_filepath = sample_tile_sample_filepath()    
    image_map_as_list = ImageFileTools.tile_sample_file_to_image_2d_list(tile_sample_yaml_filepath)
    # build a CoralOjbectDetectModel for the images 
    cod_model = CoralObjectDetectModel(image_map_as_list, reco_model, yolo_model, loctile_model, **params)
    cod_model_file = os.path.join(logdata_folder, params['cod_model_filename'])
    CoralObjectDetectModelHelper.to_yaml_file(cod_model, cod_model_file)
    if print:
        cod_model.print_info()
    return cod_model

def test_load_coral_object_detect_model(params, print=False):
    """ Test loading a CoralObjectDetectModel from a yaml file
    """
    logdata_folder = params['logdata_folder']
    cod_model_file = os.path.join(logdata_folder, params['cod_model_filename'])
    cod_model = CoralObjectDetectModelHelper.from_yaml_file(cod_model_file)
    if print:
        cod_model.print_info()
    return cod_model

if __name__ == '__main__':
    logdata_folder = '/home/qcr/cgras_data/detector/data/2023Dec/2023Dec-P00003-CG1-202311201200/'
    params = {
        'logdata_folder': logdata_folder, 
        'reco_model_filename': 'reco_model.yaml',
        'loctile_model_filename': 'loctile_model.yaml',
        'yolo_model_file': '/home/qcr/cgras_data/YoloModel/20240923_tiledimages_yolov8xseg_naive.pt',
        'coral_classes': ['recruit_live_white', 'recruit_cluster_live_white', 'recruit_symbiotic', 
                          'recruit_cluster_symbiotic', 'recruit_partial', 'recruit_cluster_partial'],
        'cod_model_filename': 'coral_object_detect_model.yaml', 
        'cod_debug_blob_images': True,
        'cod_blob_size': (640, 640),
        'cod_blob_overlap_pix': 32,
        'cod_use_cached_object_detection': False,
        'cod_duplicate_max_displacement_images': 16,
        'cod_duplicate_max_displacement_blobs': 32,        
    }   
    test_coral_object_detect_model(params)
    # test_load_coral_object_detect_model(params)
    # test_index_permutations()


if __name__ == '__main__':
    test_build_loctile_model()
    test_load_and_use_loctile_model()