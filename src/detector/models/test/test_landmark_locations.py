# Copyright 2024 - Andrew Kwok Fai LUI, 
# Robotics and Autonomous Systems Group, REF, RI
# and the Queensland University of Technology

__author__ = 'Andrew Lui'
__copyright__ = 'Copyright 2024'
__license__ = 'GPL'
__version__ = '1.0'
__email__ = 'ak.lui@qut.edu.au'
__status__ = 'Development'

import os, yaml, math, csv
from detector.models.reconstruct import ImageReconstructModel, ImageReconstructModelHelper
from detector.models.locate_tile import LocateTileModel, LocateTileModelHelper

from detector.models.models_config import ModelsConfigNames
from detector.models.imaging_tools import ImageFileTools


LOGDATA_FOLDER = '/home/qcr/cgras_data/test/landmark'

def sample_reconstruct_params():
    
    params = {
        'logdata_folder': LOGDATA_FOLDER, 
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
    params = {
        'logdata_folder': LOGDATA_FOLDER, 
        ModelsConfigNames.RECO_WORKING_SCALE.value: 0.1, 
        ModelsConfigNames.LOCTILE_MODEL_FILENAME.value: 'loctile_model.yaml',
        ModelsConfigNames.LOCTILE_DEBUG_IMAGES.value: True,
        # ModelsConfigNames.WHOLE_TILE_IAMGE_SIZE.value: [25000, 25365], # [24280, 24460],
        # ModelsConfigNames.TILE_HOLDER_WIDTH.value: 50,
        ModelsConfigNames.FRAME_SIZE_IN_MM.value: [294, 294],
        ModelsConfigNames.TILE_SIZE_IN_MM.value: [280, 280],
        ModelsConfigNames.LOCTILE_BLUE_RATIO_MIN.value: 0.40,
        ModelsConfigNames.LOCTILE_RED_RATIO_MAX.value: 0.15,
        ModelsConfigNames.LOCTILE_WORKING_SCALE.value: 0.1,
        ModelsConfigNames.LOCTILE_TEMPLATE_SIZE.value: 20,
        ModelsConfigNames.LOCTILE_MATCHING_SCORE_MIN.value: 0.5,
        # NOTE: for testing
        'test_only_holder_width_in_px': 80,     # only relevant in testing
    } 
    return params

def sample_tile_sample_filepath():
    filepath = '/home/qcr/cgras_data/Source/LandmarkTestImages/Tile_Sample_1/landmark_simulated_tile_sample.yaml'
    return filepath

def sample_ground_truth_mapping_filepath():
    filepath = '/home/qcr/cgras_data/Source/LandmarkTestImages/Tile_Sample_1/landmark_location_mapping.yaml'
    return filepath

def test_build_reco_model():
    # load images_2d_list
    tile_sample_yaml_filepath = sample_tile_sample_filepath()
    images_2d_list = ImageFileTools.tile_sample_file_to_image_2d_list(tile_sample_yaml_filepath)
    image_grid_dimension = (len(images_2d_list[0]), len(images_2d_list), )
    print(f'images_2d_list dimension: {image_grid_dimension}')
    # load params for reco_model
    params = sample_reconstruct_params()

    reco_model = ImageReconstructModel(images_2d_list=images_2d_list, **params)
    reco_model.build()
        
    # save the reco_model to a file
    reco_model_filepath = os.path.join(params['logdata_folder'], params[ModelsConfigNames.RECO_MODEL_FILENAME.value])
    ImageReconstructModelHelper.to_yaml(reco_model, reco_model_filepath)
    
    
def test_load_reco_model():
    # load params for reco_model
    params = sample_reconstruct_params()  
    # compute filepath
    reco_model_filepath = os.path.join(params['logdata_folder'], params[ModelsConfigNames.RECO_MODEL_FILENAME.value])     
    reco_model:ImageReconstructModel = ImageReconstructModelHelper.from_yaml_file(reco_model_filepath)
    reco_model.print_info()    
    return reco_model

def interactive_reco_mapping_test():
    reco_model = test_load_reco_model()
    while True:
        col_index = int(input('Enter image column index: '))
        row_index = int(input('Enter image row index: '))    
        x = int(input('Enter x: '))
        y = int(input('Enter y: '))               
        result = reco_model.map_locations(col_index, row_index, (x, y))
        print(f'Point ({x, y}) is mapped to ({result})')

def ground_truth_file_reco_mapping_test():
    reco_model = test_load_reco_model()
    ground_truth_mapping_filepath = sample_ground_truth_mapping_filepath()
    # load the yaml file
    with open(ground_truth_mapping_filepath, 'r') as infile:
        landmark_mapping_list = yaml.load(infile, Loader=yaml.Loader)
    assert landmark_mapping_list is not None
    assert isinstance(landmark_mapping_list, list)
    results_list = []
    # iterate through the landmark mapping and test each one
    absolute_error_total, absolute_error_x, absolute_error_y = 0, 0, 0
    for landmark_mapping in landmark_mapping_list:
        in_captured_image = landmark_mapping['in_captured_image']
        in_whole_image = landmark_mapping['in_whole_image']
        pred_location =  reco_model.map_locations(in_captured_image[0], in_captured_image[1], (in_captured_image[2], in_captured_image[3]))
        absolute_error_components = (math.fabs(pred_location[0] - in_whole_image[0]), math.fabs(pred_location[1] - in_whole_image[1]))
        absolute_error = absolute_error_components[0] + absolute_error_components[1]
        absolute_error_x += absolute_error_components[0]
        absolute_error_y += absolute_error_components[1]
        absolute_error_total += absolute_error
        # convert mapped location to integers for ease of use
        pred_location[0], pred_location[1] = int(pred_location[0]), int(pred_location[1])
        results_list.append(
            (*in_captured_image, *in_whole_image, *pred_location, *absolute_error_components, absolute_error)
        )
    print(f'MAE-X: {absolute_error_x / len(landmark_mapping_list)}')
    print(f'MAE-Y: {absolute_error_y / len(landmark_mapping_list)}')
    print(f'MAE: {absolute_error_total / len(landmark_mapping_list)}')
    return results_list

def write_reco_test_result_csv(results_list:list, csv_filepath:str):
    with open(csv_filepath, 'w', newline='\n') as outfile:
        wr = csv.writer(outfile, quoting=csv.QUOTE_ALL)
        wr.writerow(('image_index_x', 'image_index_y', 'image_x', 'image_y', 'whole_image_x', 'whole_image_y', 'pred_x', 'pred_y', 'error_x', 'error_y', 'error'))
        for result in results_list:
            wr.writerow(result)

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

def test_load_loctile_model():
    # load params for building loctile model
    params = sample_loctile_params()
    # load the previously built loctile model
    loctile_model_filepath = os.path.join(params['logdata_folder'], params[ModelsConfigNames.LOCTILE_MODEL_FILENAME.value])     
    loctile_model:LocateTileModel = LocateTileModelHelper.from_yaml_file(loctile_model_filepath)
    return loctile_model

def ground_truth_file_loctile_mapping_test():
    reco_model = test_load_reco_model()
    loctile_model = test_load_loctile_model()
    
    ground_truth_mapping_filepath = sample_ground_truth_mapping_filepath()
    # load the yaml file
    with open(ground_truth_mapping_filepath, 'r') as infile:
        landmark_mapping_list = yaml.load(infile, Loader=yaml.Loader)
    assert landmark_mapping_list is not None
    assert isinstance(landmark_mapping_list, list)
    results_list = []
    # iterate through the landmark mapping and test each one
    # test loctile API function map_and_normalize_bbox and get_tile_size, which are used in the detector
    absolute_error_total, absolute_error_x, absolute_error_y = 0, 0, 0
    for landmark_mapping in landmark_mapping_list:
        in_captured_image = landmark_mapping['in_captured_image']
        in_whole_image = landmark_mapping['in_whole_image']
        in_tile = landmark_mapping['in_tile']
        
        reco_pred_in_image =  reco_model.map_locations(in_captured_image[0], in_captured_image[1], (in_captured_image[2], in_captured_image[3]))
        pred_bbox = (*reco_pred_in_image, *reco_pred_in_image)
        
        result_bbox, result_normalize_bbox = loctile_model.map_and_normalize_bbox(pred_bbox)      
        pred_tile_location = result_bbox[:2]
        pred_normalized_tile_location = result_normalize_bbox[:2]
        
        print(reco_pred_in_image)
        print(f'predicted: {pred_bbox}')
        print(result_bbox)
        
        absolute_error_components = (math.fabs(pred_tile_location[0] - in_tile[0]), math.fabs(pred_tile_location[1] - in_tile[1]))
        
        absolute_error = absolute_error_components[0] + absolute_error_components[1]
        absolute_error_x += absolute_error_components[0]
        absolute_error_y += absolute_error_components[1]
        absolute_error_total += absolute_error
        # convert mapped location to integers for ease of use
        pred_tile_location[0], pred_tile_location[1] = int(pred_tile_location[0]), int(pred_tile_location[1])
        results_list.append(
            (*in_captured_image, *in_whole_image, *in_tile, *reco_pred_in_image, *pred_tile_location, *pred_normalized_tile_location, *absolute_error_components, absolute_error)
        )
    print(f'MAE-X: {absolute_error_x / len(landmark_mapping_list)}')
    print(f'MAE-Y: {absolute_error_y / len(landmark_mapping_list)}')
    print(f'MAE: {absolute_error_total / len(landmark_mapping_list)}')
    return results_list

def write_loctile_test_result_csv(results_list:list, csv_filepath:str):
    with open(csv_filepath, 'w', newline='\n') as outfile:
        wr = csv.writer(outfile, quoting=csv.QUOTE_ALL)
        wr.writerow(('image_index_x', 'image_index_y', 'image_x', 'image_y', 'whole_image_x', 'whole_image_y', 'pred_image_x', 'pred_image_y', 
                     'pred_tile_x', 'pred_tile_y', 'pred_n_tile_x', 'pred_n_tile_y',
                     'error_x', 'error_y', 'error'))
        for result in results_list:
            wr.writerow(result)

if __name__ == '__main__':
    # reco model
    # test_build_reco_model()
    # test_load_reco_model()
    # interactive_reco_mapping_test()
    # results_list = ground_truth_file_reco_mapping_test()
    # write_reco_test_result_csv(results_list, os.path.join(LOGDATA_FOLDER, 'reco_ground_truth_test.csv'))
    
    # loctile model
    test_build_loctile_model()
    results_list = ground_truth_file_loctile_mapping_test()
    write_loctile_test_result_csv(results_list, os.path.join(LOGDATA_FOLDER, 'loctile_ground_truth_test.csv'))