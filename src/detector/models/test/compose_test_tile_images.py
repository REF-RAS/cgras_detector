# Copyright 2024 - Andrew Kwok Fai LUI, 
# Robotics and Autonomous Systems Group, REF, RI
# and the Queensland University of Technology

__author__ = 'Andrew Lui'
__copyright__ = 'Copyright 2024'
__license__ = 'GPL'
__version__ = '1.0'
__email__ = 'ak.lui@qut.edu.au'
__status__ = 'Development'

import os, math, yaml, numbers, random, time, traceback
from enum import Enum
from collections import defaultdict
from datetime import datetime
import cv2
import numpy as np


PARAMS = {
    'id': 1,
    'compose_tile_spec_file': 'compose_image_tile_1.yaml',
    'rotation': 0.0, 
    'image_size': (25000, 25000,),
    'frame_bbox': (800, 800, 24200, 24200),  # frame size (23400, 23400)
    'landmark_steps': (1000, 1000),
    'captured_image_size': (8250, 5500,),
    'captured_grid_size': (6250, 4167),      # create a 4 x 6 grid
    'frame_holder_width_in_px': (80, 80,),
}

# PARAMS = {
#     'id': 2,
#     'compose_tile_spec_file': 'compose_image_tile_1.yaml',
#     'rotation': 2.0, 
#     'image_size': (25000, 25000,),
#     'frame_bbox': (800, 800, 24200, 24200),  # frame size (23400, 23400)
#     'landmark_steps': (1000, 1000),
#     'captured_image_size': (8250, 5500,),
#     'captured_grid_size': (6250, 4167),      # create a 4 x 6 grid
#     # 'captured_grid_size': (4167, 3126),    # create 6 x 8 grid
#     'frame_holder_width_in_px': (80, 80,),
# }

# PARAMS = {
#     'id': 5,
#     'compose_tile_spec_file': 'compose_image_tile_1.yaml',
#     'rotation': 0.0, 
#     'image_size': (25000, 25000,),
#     'frame_bbox': (800, 800, 24200, 24200),  # frame size (23400, 23400)
#     'landmark_steps': (1000, 1000),
#     'captured_image_size': (8250, 5500,),
#     'captured_grid_size': (6250, 4167),      # create a 4 x 6 grid
#     # 'captured_grid_size': (4167, 4167),    # create 6 x 6 grid
#     # 'captured_grid_size': (4167, 3126),    # create 6 x 8 grid
#     'frame_holder_width_in_px': (80, 80,),
# }

# the function compose a whole tile image according to the source images in the compose yaml file and the parameters
def compose_whole_tile_image(compose_yaml_file:str, params):
    IMAGE_SIZE = params.get('image_size', None)
    FRAME_BBOX = params.get('frame_bbox', None)
    ORIGIN_LOCATION = FRAME_BBOX[:2]  
    
    image_whole_with_frame = np.full(shape=(IMAGE_SIZE[1], IMAGE_SIZE[0], 3), fill_value=(195, 119, 47), dtype=np.uint8)
    
    # loading compose tile image
    with open(compose_yaml_file, 'r') as infile:
        compose_spec_dict = yaml.load(infile, Loader=yaml.Loader)
    assert 'images_set' in compose_spec_dict
    images_list = compose_spec_dict['images_set']
    # traverse the target image space row-major manner and copy the source images as a collage
    x, y = ORIGIN_LOCATION
    for row_images_list in images_list:
        bottom_y_list = []
        for image_spec in row_images_list:
            image_bgr = cv2.imread(image_spec['image_file'])
            bbox = image_spec['bbox']
            right_x = x + (bbox[2] - bbox[0])
            bottom_y = y + (bbox[3] - bbox[1])
            # ensure the source dimension matches the target dimension
            bbox[2] = min(bbox[2], max(FRAME_BBOX[2] - x, 0))
            bbox[3] = min(bbox[3], max(FRAME_BBOX[3] - y, 0))
            right_x = min(right_x, FRAME_BBOX[3])
            bottom_y = min(bottom_y, FRAME_BBOX[2])
            print(f'copy from {bbox[1], bbox[3], bbox[0], bbox[2]} to {x, right_x} {y, bottom_y} ')
            # copy the source image into the whole image
            image_whole_with_frame[y:bottom_y, x:right_x] = image_bgr[bbox[1]:bbox[3], bbox[0]:bbox[2]]
            # update the indices that traverse the whole image
            x = right_x
            # record the bottom_y so that the minimum will be used to traverse to the next row
            bottom_y_list.append(bottom_y)
        x = ORIGIN_LOCATION[0]
        y = min(bottom_y_list)    
    print(f'Image bbox: ({ORIGIN_LOCATION}) ({right_x, bottom_y})')
    return image_whole_with_frame

def rotate_image(image_whole_with_frame, params):
    ROTATION = params.get('rotation', 0)
    # compute the centre of the image
    (h, w) = image_whole_with_frame.shape[:2]
    (cX, cY) = (w // 2, h // 2)
    # apply rotation
    M = cv2.getRotationMatrix2D((cX, cY), ROTATION, 1.0)
    rotated_image_whole_tile = cv2.warpAffine(image_whole_with_frame, M, (w, h))
    return rotated_image_whole_tile

def annotate_landmarks(image_whole_with_frame, params):
    IMAGE_SIZE = params.get('image_size', None)
    FRAME_BBOX = params.get('frame_bbox', None) 
    LANDMARK_STEPS = params.get('landmark_steps', None)
    # gemerate the landmark list location
    landmark_list = [(x, y) for x in range(FRAME_BBOX[0], FRAME_BBOX[2], LANDMARK_STEPS[0]) for y in range(FRAME_BBOX[1], FRAME_BBOX[3], LANDMARK_STEPS[1])]
    # append the remaining 3 corners to the list
    landmark_list.append((FRAME_BBOX[2] - 1, FRAME_BBOX[0]))  # top right
    landmark_list.append((FRAME_BBOX[0], FRAME_BBOX[3] - 1))  # bottom left
    landmark_list.append((FRAME_BBOX[2] - 1, FRAME_BBOX[3] - 1))  # bottom right
    params['landmark_list'] = landmark_list
    # traverse the whole tile image and draw the landmarks
    for landmark in landmark_list:
        cv2.circle(image_whole_with_frame, landmark, 20, (0, 0, 255), 10, lineType=cv2.LINE_AA)
    return image_whole_with_frame

def point_in_bbox(bbox_as_list:tuple, point:tuple) -> bool:
    """ Test if the point (x, y) or (x, y, z) is in the bbox
    
    :param point: the (x, y) or (x, y, z) value of the point
    :type point: list of 2 or 3 numbers
    :param bbox_as_list: the bounding square or bounding box
    :type bbox_as_list: (x1, y1, x2, y2) or (x1, y1, z1, x2, y2, z2)
    :return: True if the point is within the bbox
    :rtype: bool
    """
    if bbox_as_list is None or type(bbox_as_list) not in (list, tuple) or point is None or type(point) not in (list, tuple):
        return False
    if len(bbox_as_list) == 4 and len(point) >= 2:
        return (bbox_as_list[0] <= point[0] <= bbox_as_list[2]) and (bbox_as_list[1] <= point[1] <= bbox_as_list[3])
    elif len(bbox_as_list) == 6 and len(point) >= 3:
        return (bbox_as_list[0] <= point[0] <= bbox_as_list[3]) and (bbox_as_list[1] <= point[1] <= bbox_as_list[4]) and \
            (bbox_as_list[2] <= point[2] <= bbox_as_list[5])
    raise AssertionError(f'CompareTools (point_in_bbox): the dimension of the parameters is not valid')

def _apply_affine_transform(affine_transform_matrix, point_in_tile_holder_space:tuple):
    if affine_transform_matrix is not None:
        transformed:np.ndarray = np.matmul(affine_transform_matrix, np.float32([point_in_tile_holder_space[0], point_in_tile_holder_space[1], 1]).T).astype(np.int32)
        # offset:np.ndarray = np.matmul(affine_transform_matrix, np.float32([0, 0, 1]).T).astype(np.int32)
        # result = tuple((transformed - offset).tolist())    
        return tuple(transformed.tolist())
    return point_in_tile_holder_space

def create_captured_images(image_whole_with_frame, image_output_folder:str, params):
    IMAGE_SIZE = params.get('image_size', None)
    FRAME_BBOX = params.get('frame_bbox', None) 
    CAPTURED_IMAEG_SIZE = params.get('captured_image_size', None)
    CAPTURED_GRID_SIZE = params.get('captured_grid_size', None)
    FRAME_HOLDER_WIDTH_IN_PX = params.get('frame_holder_width_in_px', None)
    ROTATION = params.get('rotation', 0)
    landmark_list = params.get('landmark_list', None) 
    
    # create the output folder if not exists
    if image_output_folder is not None:
        os.makedirs(image_output_folder, exist_ok=True)
    # data structure to note down the landmarks and their locations in the captured images for evaluation
    landmark_location_mapping_list = []
    # data structure to record the list of captured image files that are saved to the output folder
    capture_images_file_list = []
    # compute affine transform matrix
    affine_transform_matrix = cv2.getRotationMatrix2D((IMAGE_SIZE[0] // 2, IMAGE_SIZE[1] // 2,), ROTATION, 1.0)


    # generate capture_grid_origin_list
    capture_grid_origin_list = [(ix, iy, x, y) for iy, y in enumerate(range(0, IMAGE_SIZE[1], CAPTURED_GRID_SIZE[1])) for ix, x in enumerate(range(0, IMAGE_SIZE[0], CAPTURED_GRID_SIZE[0])) ]
    for index, capture_grid_origin in enumerate(capture_grid_origin_list):
        capture_index = (capture_grid_origin[0], capture_grid_origin[1],)
        captured_image_bbox = (capture_grid_origin[2], capture_grid_origin[3], capture_grid_origin[2] + CAPTURED_IMAEG_SIZE[0], capture_grid_origin[3] + CAPTURED_IMAEG_SIZE[1])
        captured_image = image_whole_with_frame[captured_image_bbox[1]:captured_image_bbox[3], captured_image_bbox[0]:captured_image_bbox[2]]
        output_file = f'Captured_{index:02}.jpg'
        cv2.imwrite(os.path.join(image_output_folder, output_file), captured_image)
        capture_images_file_list.append((*capture_index, output_file))
        # iterate through landmark list for the landmarks within this captured image
        for landmark in landmark_list:
            # landmark is the location in the original aligned tile
            # compute the landmark in rotated image
            landmark_in_rotated = _apply_affine_transform(affine_transform_matrix, landmark)
            
            if point_in_bbox(captured_image_bbox, landmark_in_rotated):
                # compute the landmark in the captured_image scope, which is rotated
                landmark_in_captured_image = (landmark_in_rotated[0] - captured_image_bbox[0], landmark_in_rotated[1] - captured_image_bbox[1])
                # the landmark in scope of the original aligned frame and the tile (ground truth)
                landmark_in_frame = [landmark[0] - FRAME_BBOX[0], landmark[1] - FRAME_BBOX[1],]
                landmark_in_tile = [landmark_in_frame[0] - FRAME_HOLDER_WIDTH_IN_PX[0], landmark_in_frame[1] - FRAME_HOLDER_WIDTH_IN_PX[1],]                
                # append the test data as a dictionary to a list
                landmark_in_captured_image_and_index = [*capture_index, *landmark_in_captured_image]
                landmark_location_mapping_list.append({'in_captured_image': landmark_in_captured_image_and_index, 
                                                        'in_whole_image': [*landmark],
                                                        'in_frame': landmark_in_frame,
                                                        'in_tile': landmark_in_tile,
                                                        })
        
    params['capture_images_file_list'] = capture_images_file_list
    params['capture_images_folder'] = image_output_folder
    params['landmark_location_mapping_list'] = landmark_location_mapping_list
    
def save_tile_sample_yaml_file(params):
    ID = params.get('id', None)
    capture_images_file_list = params.get('capture_images_file_list', None)
    capture_images_folder = params.get('capture_images_folder', None)
    # create 'images' list
    images_list = []
    for capture_image in capture_images_file_list:
        images_list.append({'x': capture_image[0], 'y': capture_image[1], 'file': capture_image[2]})
    # create the top level dict
    tile_sample_dict = {
        'images': images_list,
        'image_files_parent_folder': capture_images_folder,
        'tile_id': '2025Feb-SIM01',
        'species': 'Montipora aequituberculata',
        'settle_time': '2025-02-21',
        'spawning_time': '2025-02-18',
        'season': '2025Feb',
        'num_tabs': [20, 20],
        'tile_size': [280, 280],
        'frame_size': [294, 294],
        'batch_id': 'CG1-202502222300',
        'batch_time': '2024-11-19 23:00:00',
        'importer_id': 'YAML'
    }
    # save data to the yaml file
    with open(os.path.join(capture_images_folder, f'landmark_simulated_tile_sample.yaml'), 'w') as outfile:
        yaml.dump(tile_sample_dict, outfile, Dumper=yaml.Dumper)

def save_landmarks_location_mapping_yaml_file(params):
    ID = params.get('id', None)
    capture_images_folder = params.get('capture_images_folder', None)
    landmark_location_mapping_list = params.get('landmark_location_mapping_list', None)
    
    # save data to the yaml file
    with open(os.path.join(capture_images_folder, f'landmark_location_mapping.yaml'), 'w') as outfile:
        yaml.dump(landmark_location_mapping_list, outfile, Dumper=yaml.Dumper)    


if __name__ == '__main__':
    ID = PARAMS['id']
    COMPOSE_TILE_SPEC_FILE = PARAMS['compose_tile_spec_file']
    image_whole_with_frame = compose_whole_tile_image(os.path.join(os.path.dirname(__file__), COMPOSE_TILE_SPEC_FILE), PARAMS)
    image_whole_with_frame = annotate_landmarks(image_whole_with_frame, PARAMS)
    image_whole_with_frame = rotate_image(image_whole_with_frame, PARAMS)
    create_captured_images(image_whole_with_frame, f'/home/qcr/cgras_data/Source/LandmarkTestImages/Tile_Sample_{ID}', PARAMS)
    save_tile_sample_yaml_file(PARAMS)
    save_landmarks_location_mapping_yaml_file(PARAMS)
    # save the whole tile image
    cv2.imwrite('/home/qcr/cgras_data/Source/LandmarkTestImages/whole_reco_image.jpg', image_whole_with_frame)