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

def sample_reconstruct_params():
    logdata_folder = '/home/qcr/cgras_data/test/detector'
    params = {
        'logdata_folder': logdata_folder, 
        ModelsConfigNames.RECO_MODEL_FILENAME.value: 'reco_model.yaml',
        ModelsConfigNames.RECO_DEGUG_IMAGE_ORIGINAL_SCALE.value: False,
        ModelsConfigNames.RECO_DEBUG_FEATURE_MATCH_IMAGES.value: True,
        ModelsConfigNames.RECO_FEATURE_DETECTORS.value: 'brisk',
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
        # ModelsConfigNames.WHOLE_TILE_IAMGE_SIZE.value: [25000, 25365], # [24280, 24460],
        # ModelsConfigNames.TILE_HOLDER_WIDTH.value: 50,
        ModelsConfigNames.FRAME_SIZE_IN_MM.value: [294, 294],
        ModelsConfigNames.TILE_SIZE_IN_MM.value: [280, 280],
        # not applicable in the machine learning classifier version 
        # ModelsConfigNames.LOCTILE_BLUE_RATIO_MIN.value: 0.40,
        # ModelsConfigNames.LOCTILE_RED_RATIO_MAX.value: 0.15,
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
        loctile_model = LocateTileModel(images_2d_list=images_2d_list, map_location_fn=reco_model.map_locations, image_size_in_px=reco_model.get_whole_reco_image_size(), **params)
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
    original_points = [(977, 416), (977 + 24335, 416 + 24564)]
    truth_values = [(0, 0), (24335, 24564)]
    for point, truth in zip(original_points, truth_values):
        result = loctile_model.map_locations(point)
        print(point, result, truth)
    # run tests: mapping locations and normalize
    print('test mapping locations and normalize')
    original_bbox = [(1680, 1050, 24260, 24740,)]
    for bbox in original_bbox:
        result_bbox, result_normalize_bbox = loctile_model.map_and_normalize_bbox(bbox)
        print(bbox, result_bbox, result_normalize_bbox)
        assert result_normalize_bbox[0] >= 0 and result_normalize_bbox[1] >= 0 and result_normalize_bbox[2] <= 1 and result_normalize_bbox[3] <= 1

if __name__ == '__main__':
    test_build_loctile_model()
    test_load_and_use_loctile_model()