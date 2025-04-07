# Copyright 2024 - Andrew Kwok Fai LUI, 
# Robotics and Autonomous Systems Group, REF, RI
# and the Queensland University of Technology

__author__ = 'Andrew Lui'
__copyright__ = 'Copyright 2024'
__license__ = 'GPL'
__version__ = '1.0'
__email__ = 'ak.lui@qut.edu.au'
__status__ = 'Development'

import os, csv
from detector.models.reconstruct import ImageReconstructModel, ImageReconstructModelHelper
from detector.models.locate_tile import LocateTileModel, LocateTileModelHelper
from detector.models.models_config import ModelsConfigNames
from detector.models.imaging_tools import ImageFileTools
from detector.models.detect import CoralObjectDetectModel, CoralObjectDetectModelHelper, CoralObjectListHelper, YoloObjectDetector

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
        ModelsConfigNames.FRAME_SIZE_IN_MM.value: [294, 294],
        ModelsConfigNames.TILE_SIZE_IN_MM.value: [280, 280],
        # not applicable in the machine learning classifier version 
        # ModelsConfigNames.LOCTILE_BLUE_RATIO_MIN.value: 0.40,
        # ModelsConfigNames.LOCTILE_RED_RATIO_MAX.value: 0.15,
        ModelsConfigNames.LOCTILE_WORKING_SCALE.value: 0.1,
        ModelsConfigNames.LOCTILE_TEMPLATE_SIZE.value: 20,
        ModelsConfigNames.LOCTILE_MATCHING_SCORE_MIN.value: 0.5,
        # NOTE: for testing
        'test_only_holder_width_in_px': 80,     # only relevant in testing
    } 
    return params

def sample_cod_params():
    params = {
        'logdata_folder': LOGDATA_FOLDER, 
        ModelsConfigNames.YOLO_MODEL_FILE.value: '/home/qcr/cgras_data/YoloModel/20240926_cgras_tiled_yolov8n_seg_640p.pt',
        'coral_classes': ['recruit_live_white', 'recruit_cluster_live_white', 'recruit_symbiotic', 
                          'recruit_cluster_symbiotic', 'recruit_partial', 'recruit_cluster_partial'],  # to be replaced by classes_map
        'classes_map': {'POLYP_KEYPART': ['alive'],
                        'POLYP_MULTI': ['mask_live'],
                        'DEAD_CORAL': ['dead', 'mask_dead'],
                        },
        ModelsConfigNames.COD_MODEL_FILENAME.value: 'coral_object_detect_model.yaml', 
        ModelsConfigNames.COD_DEBUG_BLOB_IMAGES.value: True,
        ModelsConfigNames.COD_BLOB_SIZE.value: (640, 640),
        ModelsConfigNames.COD_BLOB_OVERLAP_PIX.value: 32,
        ModelsConfigNames.COD_USE_CACHED_OBJECT_DETECTION.value: False,
        # ModelsConfigNames.COD_DUPLICATE_MAX_DISPLACEMENT_IMAGES.value: 32,
        # ModelsConfigNames.COD_DUPLICATE_MAX_DISPLACEMENT_BLOBS.value: 32,         
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

def test_load_loctile_model():
    # load params for building loctile model
    params = sample_loctile_params()
    # load the previously built loctile model
    loctile_model_filepath = os.path.join(params['logdata_folder'], params[ModelsConfigNames.LOCTILE_MODEL_FILENAME.value])     
    loctile_model:LocateTileModel = LocateTileModelHelper.from_yaml_file(loctile_model_filepath)
    return loctile_model

def test_index_permutations():
    # perm_list = CoralObjectListHelper.get_index_permutations(list(range(10)))
    # for perm in perm_list:
    #     print(perm)
    for perm in CoralObjectListHelper.index_permutations(list(range(4))):
        print(perm)

def test_build_coral_object_detect_model():
    reco_model:ImageReconstructModel = test_load_reco_model()
    loctile_model:LocateTileModel = test_load_loctile_model()
    # retrieve source images for analysis, which had been used to build the reco and the loctile models
    # load images_2d_list
    tile_sample_yaml_filepath = sample_tile_sample_filepath()
    images_2d_list = ImageFileTools.tile_sample_file_to_image_2d_list(tile_sample_yaml_filepath)
    # load params for building cod model
    params = sample_cod_params()
    print(f'test_coral_object_detect_model: started')
    logdata_folder = params['logdata_folder']
    # load a yolo model
    yolo_model_file = params[ModelsConfigNames.YOLO_MODEL_FILE.value]
    yolo_model:YoloObjectDetector = YoloObjectDetector(yolo_model_file=yolo_model_file, 
                                                       blob_size=params[ModelsConfigNames.COD_BLOB_SIZE.value],
                                                       classes_map=params['classes_map'])

    # build a CoralOjbectDetectModel for the images 
    # cod_model = CoralObjectDetectModel(image_map_as_list, reco_model, yolo_model, loctile_model, **params)
    cod_model = CoralObjectDetectModel(images_2d_list=images_2d_list, yolo_detect_model_list=[yolo_model], map_bbox_image_fn=reco_model.map_bbox, 
                                       map_normalize_bbox_tile_fn=loctile_model.map_and_normalize_bbox, 
                                       tile_size=loctile_model.get_tile_size_in_image_space(), **params)
    cod_model.build()

    cod_model_file = os.path.join(logdata_folder, params[ModelsConfigNames.COD_MODEL_FILENAME.value])
    CoralObjectDetectModelHelper.to_yaml_file(cod_model, cod_model_file)
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
    test_build_coral_object_detect_model()
    # test_load_coral_object_detect_model(params)
    # test_index_permutations()


