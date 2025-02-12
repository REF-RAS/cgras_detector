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
from detector.models.models_config import ModelsConfigNames
from detector.models.imaging_tools import ImageFileTools

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

def sample_tile_sample_filepath():
    filepath = os.path.join(os.path.dirname(__file__), '../../../../docs/detector_tile_sample_import_chris_mis5_t01_241119.yaml')
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
    
    # test image grid size
    assert reco_model.get_image_map_size() == image_grid_dimension
    # test reconstructed image size
    reco_model.get_whole_reco_image_size() == (2549, 2514,)
    
    # save the reco_model to a file
    reco_model_filepath = os.path.join(params['logdata_folder'], params[ModelsConfigNames.RECO_MODEL_FILENAME.value])
    ImageReconstructModelHelper.to_yaml(reco_model, reco_model_filepath)
    
    assert os.path.isfile(reco_model_filepath)
    
def test_load_reco_model():
    # load params for reco_model
    params = sample_reconstruct_params()  
    # compute filepath
    reco_model_filepath = os.path.join(params['logdata_folder'], params[ModelsConfigNames.RECO_MODEL_FILENAME.value])     
    reco_model:ImageReconstructModel = ImageReconstructModelHelper.from_yaml_file(reco_model_filepath)
    reco_model.print_info()    
    return reco_model

def interactive_test():
    reco_model = test_load_reco_model()
    while True:
        col_index = int(input('Enter image column index: '))
        row_index = int(input('Enter image row index: '))    
        x = int(input('Enter x: '))
        y = int(input('Enter y: '))               
        result = reco_model.map_locations(col_index, row_index, (x, y))
        print(f'Point ({x, y}) is mapped to ({result})')

if __name__ == '__main__':
    test_build_reco_model()
    # test_load_reco_model()