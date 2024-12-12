# Copyright 2024 - Andrew Kwok Fai LUI, 
# Robotics and Autonomous Systems Group, REF, RI
# and the Queensland University of Technology

__author__ = 'Andrew Lui'
__copyright__ = 'Copyright 2024'
__license__ = 'GPL'
__version__ = '1.0'
__email__ = 'ak.lui@qut.edu.au'
__status__ = 'Development'

import os, math, yaml, numbers, pickle


from detector.models.reconstruct_tools import ImageMap, test_get_cgras_sample_images_as_list
from detector.models.reconstruct import ImageReconstructModel, ImageReconstructModelHelper, test_load_reco_model

from detector.models import logger

class LocateTileModel():
    """ LocateTileModel uses computer vision means to detect the 4 corners of tile frames so to enable transformation from reconstructed image space to the tile space
    """
    def __init__(self, images_2d_list:list, reco_model:ImageReconstructModel, **kwargs):
        """ The constructor

        :param images_2d_list: The 2D grid of input source images as a list of lists  
        :type images_2d_list: list
        :param reco_model: The ImageReconstructModel computed for the 2D grid of input images
        :type reco_model: ImageReconstructModel
        """
        # ignore the constructor if the object is loaded from yaml file
        if images_2d_list is None:
            return
        self.images_2d_list = images_2d_list
        self.params = kwargs
        self.reco_model = reco_model
    
    def build(self):
        # model variables 
        self.tile_bbox = (0, 0, 21170, 8750)    # hardcode tile size frame bbox for testing  
        self.tile_bbox = (0, 0, 21740, 8764)    # hardcode tile size from the reconstructed image 
        # hard code
        whole_reco_image_size = self.reco_model.get_whole_reco_image_size()
        self.tile_bbox = (0, 0, whole_reco_image_size[0], whole_reco_image_size[1])
     
    def map_bbox(self, bbox:tuple):
        """ converts a bounding box in the reconstructed image space to the tile space according to a detection of the frame or holder of the tile

        :param bbox: The bounding box (x1, y1, x2, y2) specified as a 4-tuple or 4-list
        :type bbox: A 4-list or 4-tuple      
        """   
        points = [(bbox[0], bbox[1],), (bbox[2], bbox[3],)]
        results = self.map_locations(points)
        return [*results[0], *results[1]]
     
    def map_locations(self, points:list) -> list:
        """ converts one or more points in the reconstructed image space to the tile space according to a detection of the frame or holder of the tile

        :param points: The parameter can be a point (a tuple of two floats indicating the (x, y) position) or a list of points
        :type points: A list of tuples or a tuple
        """        
        single_point = False
        if type(points) in (tuple, list) and len(points) == 2 and isinstance(points[0], numbers.Number):
            single_point = True
            points = [points]
        # iterate through each point in an original image and compute their location in the whole reconstructed image
        results = []
        for point in points:
            mapped_point = (point[0] - self.tile_bbox[0], point[1] - self.tile_bbox[1],)
            if single_point:
                return mapped_point
            results.append(mapped_point)
        return results

    def normalize_bbox(self, bbox:tuple):
        """ normalize a bounding box in the tile space in the range [0, 1] 

        :param bbox: The bounding box (x1, y1, x2, y2) specified as a 4-tuple or 4-list
        :type bbox: A 4-list or 4-tuple      
        """   
        points = [(bbox[0], bbox[1],), (bbox[2], bbox[3],)]
        results = self.normalize_locations(points)
        return [*results[0], *results[1]]
    
    def normalize_locations(self, mapped_points:list) -> list:
        """ normalize one or more mapped points in the tile space in the range [0, 1] 

        :param mapped_points: The parameter can be a point (a tuple of two floats indicating the (x, y) position) or a list of points in the tile space
        :type mapped_points: A list of tuples or a tuple of normalized locations
        """        
        single_point = False
        if type(mapped_points) in (tuple, list) and len(mapped_points) == 2 and isinstance(mapped_points[0], numbers.Number):
            single_point = True
            mapped_points = [mapped_points]
        # iterate through each point in the tile space and normalize by dividing by the size of the tile
        results = []
        for point in mapped_points:
            mapped_point = (point[0] / self.tile_bbox[2], point[1] / self.tile_bbox[3],)
            if single_point:
                return mapped_point
            results.append(mapped_point)
        return results
    
    def get_tile_size(self) -> tuple:
        """ returns the size (xdim, ydim) of the tile as a rectangle

        :return: _description_
        :rtype: tuple
        """
        return (self.tile_bbox[2] - self.tile_bbox[0], self.tile_bbox[3] - self.tile_bbox[1],)
    
    def get_roi_points(self) -> list:
        """ returns the region of the tile frame specified by its corners from top-right clockwise 

        :return: a list of 4 tuples, each of which is a corner of the tile frame
        :rtype: list
        """
        roi_points = [
            self.tile_bbox[:2],
            (self.tile_bbox[2], self.tile_bbox[1]),
            self.tile_bbox[2:],
            (self.tile_bbox[0], self.tile_bbox[3]),
        ]
        return roi_points
    
    def print_info(self):
        """ prints the key parameters of the LocateTileModel object
        """
        logger.info(f'Tile Bounding Box: {self.tile_bbox}')
        

class LocateTileModelHelper():
    """ LocateTileModelHelper provides helper functions for saving and loading an object of LocateFileModel to the file system

    """
    @staticmethod            
    def to_yaml(loctile_model:LocateTileModel, object_file:str = None) -> str:
        """ Save the model parameters of a LocateTileModel object as a yaml file to the path specified by the given object_file

        :param loctile_model: The object of LocateTileModel to be saved to a yaml file
        :type loctile_model: LocateTileModel
        :param object_file: The path where the yaml file is saved to, defaults to None
        :type object_file: str, optional
        :return: The string content of the yaml file
        :rtype: str
        """
        object_dict = {
            'tile_bbox': loctile_model.tile_bbox,
                       }
        if object_file is None:
            return yaml.dump(object_dict)
        else:
            with open(object_file, 'w') as outfile:
                yamlstr = yaml.dump(object_dict, outfile, Dumper=yaml.Dumper)
            return yamlstr
        
    @staticmethod
    def from_yaml_file(object_file:str) -> LocateTileModel:
        """ Create an LocateTileModel object from a yaml file

        :param object_file: the path to the yaml file 
        :type object_file: str
        :return: An ImageReconstructModel object created from the yaml file
        :rtype: ImageReconstructModel
        """
        with open(object_file, 'r') as infile:
            data = yaml.load(infile, Loader=yaml.Loader)
        return LocateTileModelHelper._create_model(data)
    
    @staticmethod
    def from_yaml(yaml_str:str) -> LocateTileModel:
        """ Create an LocateTileModel object from a yaml string

        :param yaml_str: the yaml string
        :type yaml_str: str
        :return: An ImageReconstructModel object created from the yaml string
        :rtype: ImageReconstructModel
        """        
        data = yaml.load(yaml_str, Loader=yaml.Loader)
        return LocateTileModelHelper._create_model(data)
    
    @staticmethod
    def _create_model(data:dict) -> LocateTileModel:
        """ internal function for creating a LocateTileModel 

        :param data: The parameters of a LocateTileModel as a dict, which comes from a yaml file or string
        :type data: dict
        :return: An ImageReconstructModel object
        :rtype: LocateTileModel
        """
        loctile_model = LocateTileModel(None, None)
        loctile_model.tile_bbox = data['tile_bbox']
        return loctile_model
    
# ----------------------------------------------------------------------------------
# Test functions

def test_build_model(params, reco_model:ImageReconstructModel):
    image_map_as_list = test_get_cgras_sample_images_as_list()    
    logdata_folder = params['logdata_folder']
    loctile_model_file = os.path.join(logdata_folder, params['loctile_model_filename'])
    os.makedirs(logdata_folder, exist_ok=True)
    loctile_model = LocateTileModel(image_map_as_list, reco_model=reco_model, **params) 
    logger.info('Saving LocateTileModel model to file')
    LocateTileModelHelper.to_yaml(loctile_model, loctile_model_file)
    return loctile_model

def test_load_model(params):
    logger.info('Loading LocateTileModel model from file')
    logdata_folder = params['logdata_folder']
    loctile_model_file = os.path.join(logdata_folder, params['loctile_model_filename'])
    loctile_model:LocateTileModel = LocateTileModelHelper.from_yaml_file(loctile_model_file)
    loctile_model.print_info()    
    return loctile_model

if __name__ == '__main__':
    logdata_folder = '/home/qcr/cgras_data/detector/data/2024-Nov/2024-Nov-P00001-CG1-202411151200/'
    params = {
        'logdata_folder': logdata_folder, 
        'reco_model_filename': 'reco_model.yaml',
        'loctile_model_filename': 'loctile_model.yaml',
    }
    reco_model_file = '/home/qcr/cgras_data/detector/reconstruct/reco_model.yaml'
    reco_model = test_load_reco_model(params)
    loctile_model_file = '/home/qcr/cgras_data/detector/reconstruct/loctile_model.yaml'
    loctile_model = test_build_model(params, reco_model)
    loctile_model = test_load_model(params)
