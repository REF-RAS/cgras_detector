# Copyright 2024 - Andrew Kwok Fai LUI, 
# Robotics and Autonomous Systems Group, REF, RI
# and the Queensland University of Technology

__author__ = 'Andrew Lui'
__copyright__ = 'Copyright 2024'
__license__ = 'GPL'
__version__ = '1.0'
__email__ = 'ak.lui@qut.edu.au'
__status__ = 'Development'

import os, math, yaml, numbers, glob
import numpy as np

from detector.models import logger
from detector.models.heatmap_tools import HeatmapHelper
from detector.model import AIMSTILE_DAO, DETECT_DAO, APP_FILE_MANAGER, CONFIG

class CoralObjectMapModelHelper():
    """ a collection of tools for the CoralObjectMapModel class
    """
    # constant class names for the two default classes - "all classes" and "coral classes"
    VISCLASS_ALL = {'label': 'all', 'value': '_all'}
    VISCLASS_CORAL = {'label': 'coral classes', 'value': '_coral'}
    CLASS_OPTIONS = None
    
    @staticmethod
    def form_cache_file_path(tile_sample_id:str, map_size:tuple) -> tuple:
        """ generate the filename and folder of the coral object map cache file for tile_sample_id

        :param tile_sample_id: the tile_sample_id assoicated with the maps
        :param map_size: the dimension of the map as a tuple of (ncols, nrows)
        :return: a tuple of (filename, path)
        """
        tile_sample_dict = DETECT_DAO.get_tile_sample(tile_sample_id)
        logdata_folder = APP_FILE_MANAGER.get_detector_subfolder(APP_FILE_MANAGER.DATA_FOLDER, tile_sample_dict['season'], tile_sample_id)
        cache_filename = f'countmap_{tile_sample_id}_{map_size[0]}_{map_size[1]}.yaml' 
        cache_file = os.path.join(logdata_folder, cache_filename)         
        return cache_file, logdata_folder
    
    @staticmethod
    def delete_cache_files(tile_sample_id:str):
        """ delete the cache files associated with a tile_sample_id

        :param tile_sample_id: the tile_sample_id of which the cache files are to be deleted
        """
        _, logdata_folder = CoralObjectMapModelHelper.form_cache_file_path(tile_sample_id, (0, 0))
        for file in glob.glob(os.path.join(logdata_folder, 'countmap_*.yaml')):
             os.remove(file) 

    @classmethod
    def get_class_options_list(cls) -> list:
        """ return the option list containing the currently known coral object classes and the two default classes

        :return: a list of dict objects each of which contains the keys 'label' and 'value'
        """
        if cls.CLASS_OPTIONS is None:
            cls.CLASS_OPTIONS = [cls.VISCLASS_CORAL, cls.VISCLASS_ALL,]
            classname_list = DETECT_DAO.list_detected_classes()
            for classname in classname_list:
                cls.CLASS_OPTIONS.append({'label': classname, 'value': classname})
        return cls.CLASS_OPTIONS
    
    @staticmethod
    def from_yaml_file(cache_file) -> dict:
        """ load the generated maps associated with the class filter from a cache file

        :param cache_file: the path to the cache file 
        :return: the dict object containing keys of object classes and the value a numpy array representing the maps for heatmap generation
        """
        try:
            with open(cache_file, 'r') as infile:
                data = yaml.load(infile, Loader=yaml.Loader)
                return data
        except (Warning, Exception) as e:
            raise 
    
    @classmethod            
    def to_yaml_file(cls, count_map_cache:dict, cache_file:str) -> str:
        """ Save an object of CoralObjectDetectModelHelper to a yaml file

        :param count_map_cache: A cache of count_map indexed by the filter_class
        :type count_map_cache: dict
        :param cache_file: The target file path of the yaml file, defaults to None, which returns the yaml as a string
        :type cache_file: str, optional
        :return: The yaml file as a string
        :rtype: str
        """
        logger.info(f'{type(cls).__name__}: Save cached ObjectCountMap to {cache_file}')
        with open(cache_file, 'w') as outfile:
            yaml.dump(count_map_cache, outfile, Dumper=yaml.Dumper)

class CoralObjectMapModel():
    """ Models a storage of generated nunpy map of various class filters of a tile sample (given the id)
    """
    def __init__(self, tile_sample_id:str, **kwargs):
        """ the constructor

        :param tile_sample_id: the id of the tile_sample
        """
        # save the input parameters
        self.tile_sample_id = tile_sample_id
        self.params = kwargs
        # gather information about the tile_sample_id from the database
        self.tile_sample_dict = DETECT_DAO.get_tile_sample(tile_sample_id)
        self.season_dict = AIMSTILE_DAO.get_season(self.tile_sample_dict['season']) 
        # obtain the dimension of the heatmap from the attributes tab_ncols and tab_nrows in the season definition
        if self.season_dict is None:
            self.map_size_default = self.params.get('vis_map_size_default', (30, 10))
        else:
            self.map_size_default = (self.season_dict['tab_ncols'], self.season_dict['tab_nrows'],) 
        # first check if a cache file exists: compute the location of the cache file
        self.cache_file, _ = CoralObjectMapModelHelper.form_cache_file_path(tile_sample_id, self.map_size_default)      
        # first check if a cache file exists: attempt to load the cache file
        try:
            logger.info(f'{type(self).__name__}: Attempting to load cached ObjectCountMap from ({self.cache_file})')
            self.count_map_cache = CoralObjectMapModelHelper.from_yaml_file(self.cache_file)
        except:
            self.count_map_cache = {}
            
    def compute_object_count_map(self, class_filter:str=None) -> np.ndarray:
        """ return the object count map of a class detected objects on a tile_sample 

        :param tile_sample_id: The tile sample id
        :type tile_sample_id: str
        :param class_filter: one of the yolo model classes, or VisualizeTaskHelper.VISCLASS_ALL or VisualizeTaskHelper.VISCLASS_CORAL, defaults to None
        :type class_filter: str, optional
        :return: an object count map of size given in the parameter
        :rtype: np.ndarray
        """
        class_filter = CoralObjectMapModelHelper.VISCLASS_ALL['value'] if class_filter is None else class_filter
        if class_filter not in self.count_map_cache:
            # load the detected object list from db and convert them into a list of CoralObject
            coral_object_list = self._load_coral_object_list(self.tile_sample_id, class_filter)
            count_map = HeatmapHelper.compute_object_count_map(coral_object_list, self.map_size_default, None)
            self.count_map_cache[class_filter] = count_map
            # save the generated map indexed by the class_filter to the yaml file for this tile_sample_id
            CoralObjectMapModelHelper.to_yaml_file(self.count_map_cache, self.cache_file)
        else:
            count_map = self.count_map_cache[class_filter]
        return count_map
    
    def get_tile_sample_info(self) -> dict:
        """ return the information of the tile sample associated with this object

        :return: a dict containing keys of names same as that in the database table tile_sample
        """
        return self.tile_sample_dict
    
    # a helper function for loading the list of coral objects according to the class filter
    def _load_coral_object_list(self, tile_sample_id:str, class_filter=None):
        if class_filter == None:
            class_filter = CoralObjectMapModelHelper.VISCLASS_ALL['value']
        if class_filter == CoralObjectMapModelHelper.VISCLASS_ALL['value']:
            object_list = DETECT_DAO.query_detected_objects_as_coral_objects(tile_sample_id, object_classes=None)
        elif class_filter == CoralObjectMapModelHelper.VISCLASS_CORAL['value']:
            object_list = DETECT_DAO.query_detected_objects_as_coral_objects(tile_sample_id, class_category=1)
        else:
            object_list = DETECT_DAO.query_detected_objects_as_coral_objects(tile_sample_id, object_classes=class_filter)
        return object_list

# ----------------------------------------------------------------------------------
# Test functions

# test the generation of a heatmap for a tile_sample_id which has been analyzed and the coral objects detected are
# stored in teh database
def test_generate_heatmap(tile_sample_id:str):
    vt_model = CoralObjectMapModel(tile_sample_id)
    count_map = vt_model.compute_object_count_map()
    HeatmapHelper.generate_plotly_heatmap(count_map, (1500, 500), output_file='heatmap_test_sample.jpg')

if __name__ == '__main__':
    tile_sample_id = '2024-Nov-P00001-CG1-202411151200'  # tile_sample_id and the associated source images are assumed in the database
    test_generate_heatmap(tile_sample_id)