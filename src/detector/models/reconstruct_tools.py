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
import numpy as np
import cv2
from collections import defaultdict
from .detector_error import DetectorRejectError, DetectorErrorCodes

class ImageMap():
    """ Model a 2D list of images as an ImageMap object that facilitates downscaling for reducing the processing time 
    """
    def __init__(self, image_map, working_scale:float=0.1, **kwargs):
        """ the constructor

        :param image_map: a list of lists of numpy images representing a 2D grid of images
        :param working_scale: the scale at which the images are downscampled, defaults to 0.1
        """
        
        # input parameters
        self.working_scale = working_scale
        # model parameters
        self.image_size_full = None
        self.map_image_scaled = defaultdict(lambda: None)
        # validate the image_map parameter
        if type(image_map) not in (list, tuple):
            raise AssertionError(f'Parameter image_map is not a list/tuple')
        self.nrows, self.ncols = len(image_map), None
        # iterate through the 2d list of lists image_map
        for row_index, image_row in enumerate(image_map):
            if type(image_row) not in (list, tuple):
                raise AssertionError(f'Parameter image_map is not a 2d list: A list element is not a list/tuple')  
            # set the number of columns
            if self.ncols is None:
                self.ncols = len(image_row)
            elif self.ncols != len(image_row):
                raise DetectorRejectError(DetectorErrorCodes.INPUT_DATA_INVALID, f'Row Length Mismatch: two rows in the image grid are of different lengths')
            for col_index, image_obj in enumerate(image_row):
                # if image_obj is a file path, read in the image
                if type(image_obj) == str:
                    if not os.path.isfile(image_obj):
                        raise DetectorRejectError(DetectorErrorCodes.INPUT_DATA_INVALID, f'Image File Not Found: {image_obj}')
                    try:
                        image_obj = cv2.imread(image_obj)
                    except Warning as e:
                        raise DetectorRejectError(DetectorErrorCodes.INPUT_DATA_INVALID, f'Not An Valid Image File: {image_obj}', e)
                    except Exception as e:
                        raise DetectorRejectError(DetectorErrorCodes.INPUT_DATA_INVALID, f'Not An Valid Image File: {image_obj}', e)
                # test if image_obj is a numpy image
                if type(image_obj) is not np.ndarray:
                    raise DetectorRejectError(DetectorErrorCodes.INPUT_DATA_INVALID, f'Not An Valid Image File: {image_obj}')
                # test if the image size is consistent with the first image
                if self.image_size_full is None:
                    self.image_size_full = image_obj.shape[:2][::-1]
                else:
                    if self.image_size_full[0] != image_obj.shape[1] or self.image_size_full[1] != image_obj.shape[0]:
                        raise DetectorRejectError(DetectorErrorCodes.INPUT_DATA_INVALID, f'Dimension of Images Different: Image at grid index (row {row_index} col {col_index}) has a different resolution ')
                # resize the image to the work_scale
                self.image_size_scale = (int(self.image_size_full[0] * self.working_scale), int(self.image_size_full[1] * self.working_scale))
                image_scaled = cv2.resize(image_obj, self.image_size_scale)
                self.map_image_scaled[col_index, row_index] = image_scaled
    
    def get_working_scale(self) -> float:
        """ return the working scale

        :return: the working scale of this ImageMap
        """
        return self.working_scale
    
    def get_scaled_image(self, x:int, y:int) -> np.ndarray:
        """ return the image at grid cell (x, y)

        :param x: the x index of the grid cell
        :param y: the y index of the grid cell
        :return: the numpy image at the index (x, y) of the image grid
        """
        return self.map_image_scaled[x, y]
    
    def get_nrows(self) -> int:
        """ return the number of rows

        :return: the number of rows as an int
        """
        return self.nrows   
    
    def get_ncols(self) -> int:
        """ return the number of columns

        :return: the number of columns as an int
        """
        return self.ncols
    
    def get_image_map_size(self) -> tuple:
        """ return the 2d grid dimension of the image map

        :return: the dimension (ncols, nrows) as a tuple
        """
        return (self.ncols, self.nrows)
    
    def get_row_images_at_working_scale(self, y:int) -> list:
        """ return a row of images at row y as a list

        :param y: the row index
        :return: a list of numpy images ordered by their x index on the row 
        """
        assert y is not None and y >= 0 and y < self.nrows, 'Parameter y should be a valid row index'
        return [self.map_image_scaled[x, y] for x in range(self.ncols)]
    
    def get_col_images_at_working_scale(self, x:int) -> list:
        """ return a column of images at row x as a list

        :param x: the column index
        :return: a list of numpy images ordered by their y index on the column 
        """        
        assert y is not None and x >= 0 and x < self.ncols, 'Parameter x should be a valid column index'
        return [self.map_image_scaled[x, y] for y in range(self.nrows)]    
    
    def get_scaled_images_as_dict(self) -> dict:
        """ return the downscaled images as a 2D map indexed by (x, y) in the 2D grid

        :return: a map of numpy images as dict type which is indexed by (x, y) location in the 2D grid
        """
        return self.map_image_scaled

    def get_image_size(self) -> tuple:
        """ return the size of images at the original scale (width, height) and all images have the same size

        :return: a tuple representing the (width, height) of the images
        """
        return self.image_size_full
    
    def get_scaled_image_size(self) -> tuple:
        """ return the size of images at downscale (width, height)

        :return: a tuple representing the (width, height) of the downscaled images
        """        
        return self.get_scaled_image_size

class CameraTransformTools():
    """ A collection of tools for handling the cv2.detail.CameraParams objects
    """
    @staticmethod
    def print_camera_transform(camera_transform:cv2.detail.CameraParams):
        print(dir(camera_transform))
        print(type(camera_transform.K()))
        print(type(camera_transform.R))
        print(type(camera_transform.t))
        print(type(camera_transform.aspect))
        print(type(camera_transform.focal))
        print(type(camera_transform.ppx))
        print(type(camera_transform.ppy))
        print(camera_transform.K().shape) 
        print(camera_transform.t.shape) 
        print(camera_transform.R.shape) 

    @staticmethod
    def camera_to_dict(camera_transform:cv2.detail.CameraParams) -> dict:
        """ extract information from cv2.detail.CameraParams into a dict

        :param camera_transform: a cv2.detail.CameraParams object 
        :return: a dict object containing keys K, R, t, aspect, focal, ppx, and ppy
        """

        data = {
            'K': camera_transform.K().tolist(),
            'R': camera_transform.R.tolist(),
            't': camera_transform.t.tolist(),
            'aspect': camera_transform.aspect,
            'focal': camera_transform.focal,
            'ppx': camera_transform.ppx,
            'ppy': camera_transform.ppy,
        }
        return data
    
    @staticmethod
    def dict_to_camera(data: dict) -> cv2.detail.CameraParams:
        """ convert a dict object containing keys K, R, t, aspect, focal, ppx, and ppy into a cv2.detail.CameraParams

        :param data: the dict object
        :return: a cv2.detail.CameraParams object populated with the parameters 
        """
        camera_transform = cv2.detail.CameraParams()
        camera_transform.R = np.asarray(data['R'], dtype=np.float32)
        camera_transform.t = np.asarray(data['t'], dtype=np.float32)
        camera_transform.aspect = data['aspect']
        camera_transform.focal = data['focal']
        camera_transform.ppx = data['ppx']
        camera_transform.ppy = data['ppy']
        return camera_transform
    
    @staticmethod
    def rescale_camera_transform(camera_transform: cv2.detail.CameraParams, scaling_factor:float) -> cv2.detail.CameraParams:
        """ apply a scaling factor to a cv2.detail.CameraParams object

        :param camera_transform: a cv2.detail.CameraParams object 
        :param scaling_factor: the scaling factor 
        :return: the same cv2.detail.CameraParams object but the parameters adjusted by the scaling factor
        """
        camera_transform.focal = camera_transform.focal * scaling_factor
        camera_transform.ppx = camera_transform.ppx * scaling_factor
        camera_transform.ppy = camera_transform.ppy * scaling_factor
        return camera_transform    


# ----------------------------------------------------------------------------------
# Test functions

# a helper function for testing the ImageMap class by loading an folder containing 
# CGRAS 2023 images of filenames embedded with index (col, row)
def test_get_cgras_sample_images_as_list():
    source_folder = '/home/qcr/cgras_data/Source/AnnotatedTile_1_1'
    images_as_2d_list = []
    for row in range(0, 3):
        image_row = []
        for col in range(0, 6):
            image_file = f'Tile_1_1_{col}_{row}.jpg'
            image_row.append(os.path.join(source_folder, image_file))
        images_as_2d_list.append(image_row)
    return images_as_2d_list

# test the ImageMap class
def test_image_map():
    images_as_2d_list = test_get_cgras_sample_images_as_list()
    for row_index in range(len(images_as_2d_list)):
        print(images_as_2d_list[row_index])
    image_map = ImageMap(images_as_2d_list, work_scale=0.05)

def test_dict_to_camera():
    data = {
        'K': [1, 1, 1, 1, 1, 1, 1, 1, 1], # to be ignored
        'R': [1, 2, 3, 4, 5],
        't': [1, 2, 3],
        'aspect': 1.0,
        'focal': 50.0,
        'ppx': 100,
        'ppy': 200
    }
    print(f'original dict: {data}')
    camera_transform = CameraTransformTools.dict_to_camera(data)
    CameraTransformTools.print_camera_transform(camera_transform)
    data = CameraTransformTools.camera_to_dict(camera_transform)
    print(f'final dict: {data}')


if __name__ == '__main__':
    # image_map = test_get_cgras_sample_images_as_list()
    # test_image_map()
    test_dict_to_camera()
    
    
    