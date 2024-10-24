# Copyright 2024 - Andrew Kwok Fai LUI, 
# Robotics and Autonomous Systems Group, REF, RI
# and the Queensland University of Technology

__author__ = 'Andrew Lui'
__copyright__ = 'Copyright 2024'
__license__ = 'GPL'
__version__ = '1.0'
__email__ = 'ak.lui@qut.edu.au'
__status__ = 'Development'

import os, math, yaml, numbers, pickle, time
from enum import Enum
from collections import defaultdict
from datetime import datetime
import cv2
import numpy as np

from detector.models.reconstruct import ImageReconstructModel, ImageReconstructModelHelper
from detector.models.reconstruct_tools import test_get_cgras_sample_images_as_list 
from detector.models.locate_tile import LocateTileModel, LocateTileModelHelper
from detector.models.yolo_detector import YoloObjectDetector, YoloResult, ObjectType
from detector.models import logger, ModelsConfigNames
from detector.model import CoralObject, ObjectClassCategories

class CoralObjectDetectModel():
    """ CoralDetectorModel uses an object detector to extract a list of objects detected in a 2d grid of images that represent a full coral aquaculture tile. The images which may overlap with one another are
        arranged in a 2d grid that implies the location with reference to the tile. The class uses an ImageReconstructionModel to map locations on individual images to  
    """
    def __init__(self, images_2d_list:list, reco_model:ImageReconstructModel, yolo_model:YoloObjectDetector, locate_tile_model:LocateTileModel=None, progress_cb=None, **kwargs):
        """ the constructor

        :param images_2d_list: A list of lists of images, each of which can be image paths (str typed) or image pixels (np.ndarray), arranged in a 2D grid
        :type images_2d_list: list
        :param reco_model: The ImageReconstructModel computed for the 2d grid of images, which is used to map locations from image space to tile space
        :type reco_model: ImageReconstructModel
        :param yolo_model: The YoloObjectDetector model to be used, which should be suitable for the coral species found in the images
        :type yolo_model: YoloObjectDetector
        :param locate_tile_model: The LocateTileModel model computed for the 2d grid of images, which is used to map locations from reconstruction space to tile space, defaults to None
        :type locate_tile_model: LocateTileModel, optional
        """
        # ignore the constructor if the object is loaded from yaml file
        if images_2d_list is None:
            return
        # progress tracking
        self.progress_cb = progress_cb
        self.num_images = len(images_2d_list) * len(images_2d_list[0])
        self.count_images_completed = 0
        # input parameters
        self.tile_size = locate_tile_model.get_tile_size() if locate_tile_model is not None else None
        if self.tile_size is None:  # if the tile size is not known from LocateTileModel 
            whole_reco_image_size = reco_model.get_whole_reco_image_size()
            self.tile_size = whole_reco_image_size
        # other keyword parameters - operational
        self.blob_size = kwargs.get(ModelsConfigNames.COD_BLOB_SIZE.value, None)
        if self.blob_size is None:
            raise AssertionError(f'{type(self).__name__}: Parameter (mandatory) {ModelsConfigNames.COD_BLOB_SIZE.value} is missing')
        self.blob_overlap_pix = kwargs.get(ModelsConfigNames.COD_BLOB_OVERLAP_PIX.value, 0)
        self.duplicate_max_displacement = kwargs.get(ModelsConfigNames.COD_DUPLICATE_MAX_DISPLACEMENT_IMAGES.value, 10)
        # other keyword parameters - output cached data and debug information
        self.logdata_folder = kwargs.get(ModelsConfigNames.LOGDATA_FOLDER.value, None)
        self.cod_model_cache_filename = kwargs.get(ModelsConfigNames.COD_MODEL_FILENAME.value, f'coral_object_detect_model.yaml')
        # model parameters
        self.image_grid_size = reco_model.get_image_map_size()
        self.object_list_of_images = dict()
        self.object_class_names = None

        # model parameters: abort
        self.to_abort = False
        # step 1: iterate through each image in the 2d list of images
   
        for row_index, row_1d_image_list in enumerate(images_2d_list):
            for col_index, image in enumerate(row_1d_image_list):
                if hasattr(self, 'progress_cb') and self.progress_cb is not None:
                    self.progress_cb((self.count_images_completed, self.num_images))
                time.sleep(0.1)
                if self.to_abort:
                    return   
                cod_model = CoralObjectDetectImageModel(image, col_index, row_index, reco_model, yolo_model, locate_tile_model, **kwargs)
                index = (col_index, row_index)
                self.object_list_of_images[index] = cod_model.get_object_list(include_invalidated=False)
                if self.object_class_names is None:
                    self.object_class_names = cod_model.get_object_class_names() 
                self.count_images_completed += 1 

        # step 2: resolve duplicate objects in the overlapping regions between images
        logger.info(f'DUPLICATE REMOVAL between images in the tile') 
        self.num_invalidated_objects = self._invalidate_duplicate_objects(self.object_list_of_images, self.image_grid_size, self.duplicate_max_displacement)
        # step 3: extract the objects from individual lists of images into a single list
        self.object_list = self._merge_object_lists(include_invalidated=True)
        # step 4: save the object list and metadata to the cache file

    def _merge_object_lists(self, include_invalidated=False) -> list:
        """ internal function to return as a single list all the coral objects detected in the 2d grid of images, the duplicated objects due to overlapping regions between neighbouring images are flagged invalidated.
            The parameter include_invalidated controls whether to also return the invalidated object in the list
        """
        final_objects_list = []
        for index in self.object_list_of_images.keys():
            if include_invalidated:
                final_objects_list.extend(self.object_list_of_images[index])
            else:
                for coral_object in self.object_list_of_images[index]:
                    if not coral_object.invalidated:
                        final_objects_list.append(coral_object)
        return final_objects_list
    
    def abort(self):
        self.to_abort = True

    def get_progress(self) -> tuple:
        if hasattr(self, 'num_images') and hasattr(self, 'count_images_completed'):
            return (self.count_images_completed, self.num_images)

    def get_object_list(self) -> list:
        """ returns the list of CoralObject objects

        :return: the finalized list of CoralObject, which may include invalidated object
        :rtype: list
        """
        return self.object_list
    
    def get_num_objects(self) -> int:
        """ return the number of objects, which may include invalidated objects

        :return: the number of objects, which may include invalidated objects
        :rtype: int
        """
        return len(self.object_list)
    
    def get_num_invalidated_objects(self) -> int:
        """ returns the number of objects marked as invalidated, due to being a duplicate

        :return: the number of objects marked as invalidated, due to being a duplicate
        :rtype: int
        """
        return self.num_invalidated_objects
    
    def get_object_class_names(self) -> dict:
        """ returns a map of class_id, class_name for different classes of coral objects as specified by the object detection model

        :return: a map of class_id, class_name
        :rtype: dict
        """
        return self.object_class_names
    
    def get_tile_size(self) -> tuple:
        """ returns the size (xdim, ydim) of the tile in pixels

        :return: the size (xdim, ydim) of the tile in pixels
        :rtype: tuple
        """
        return self.tile_size

    def print_info(self) -> None:
        """ display the key parameters of the CoralObjectDetectModel
        """
        logger.info(f'Number of objects: {len(self.object_list)}')
        logger.info(f'Number of invalidated objects: {self.num_invalidated_objects}')
        logger.info(f'Number of unique objects: {len(self.object_list) - self.num_invalidated_objects}')
        logger.info(f'Tile size: {self.tile_size}')
        logger.info(f'Object Class Names: {self.object_class_names}')

    def _save_object_list_of_images(self, cache_file:str):
        """ Save the data associated with the detected coral objects to a yaml file

        :param cache_file: path to the target yaml file
        :type cache_file: str
        """
        data = {
            # 'object_list_of_images': self.object_list_of_images,
            'image_grid_size': self.image_grid_size,
            'resolved_object_list': self.object_list,
            'num_resolved_objects': len(self.object_list),
            'num_duplicate_objects': self.num_invalidated_objects,
            'object_class_names': self.object_class_names,
            'tile_size': self.tile_size,
        }
        with open(cache_file, 'w') as outfile:
            yaml.dump(data, outfile, Dumper=yaml.Dumper)
    
    def _load_object_list_of_images(self, cache_file:str) -> list:
        """ Load from a yaml file the data associated with the detected coral objects and restore them to the data structures of this object

        :param cache_file: path to the target yaml file
        :type cache_file: str
        """
        try:
            with open(cache_file, 'r') as infile:
                data = yaml.load(infile, Loader=yaml.Loader)
            # self.object_list_of_images = data['object_list_of_images']
            self.image_grid_size = data['image_grid_size']
            self.object_list = data['resolved_object_list']
            self.num_invalidated_objects = data['num_duplicate_objects']
            self.object_class_names = data['object_class_names']
            self.tile_size = data['tile_size']
        except (Warning, Exception) as e:
            # logger.warning(f'{type(self).__name__}: Failed to load object list cache file {cache_file}\n{e}')
            raise e
    
    @classmethod
    def from_yaml_file(cls, object_file:str):
        """ Create a CoralObjectDetectModel object from a yaml file

        :param object_file: the path to the yaml file
        :type object_file: str
        :return: the new CoralObjectDetectModel object
        :rtype: CoralObjectDetectModel
        """
        cod_model = cls(None, None, None)
        cod_model._load_object_list_of_images(object_file)
        return cod_model

    def _invalidate_duplicate_objects(self, object_list_of_images:dict, images_grid_size:tuple, max_displacement:float) -> int:
        """ a generic function for invalidating objects associated with every image in the 2d grid of images that are found to be duplicates.

        :param object_list_of_images: a 2d grid of object lists, each of which stores objects found from the corresponding image in the 2d grid of images
        :type object_list_of_images: dict
        :param images_grid_size: the dimension of the 2d grid of object list, which equals to the 2d grid of images
        :type images_grid_size: tuple
        :param max_displacement: the threshold distance beyond which two objects can be considered as duplicates
        :type max_displacement: float
        :return: the total number of objects marked as invalidated by this function
        :rtype: int
        """
        total_duplicates_removed = 0
        # iterate through each row and then each grid locations along a row
        for row_index in range(images_grid_size[1]):
            for col_index in range(images_grid_size[0] - 1):
                # abort the process
                if self.to_abort:
                    return
                # resolve diplicate between (col_index, row_index) and (col_index + 1, row_index)
                object_list_index_1, object_list_index_2 = (col_index, row_index), (col_index + 1, row_index)
                num_duplicates_removed = CoralObjectListHelper.invalidate_duplicate_objects_greedy(object_list_of_images[object_list_index_1], object_list_of_images[object_list_index_2], max_displacement)
                total_duplicates_removed += num_duplicates_removed
                logger.info(f'Number of duplicate removed between images {object_list_index_1} and {object_list_index_2}: {num_duplicates_removed}')
                if row_index >= images_grid_size[1] - 1:
                    continue
                # resolve diplicate between (col_index, row_index) and (col_index, row_index + 1)
                object_list_index_1, object_list_index_2 = (col_index, row_index), (col_index, row_index + 1)
                num_duplicates_removed = CoralObjectListHelper.invalidate_duplicate_objects_greedy(object_list_of_images[object_list_index_1], object_list_of_images[object_list_index_2], max_displacement)
                total_duplicates_removed += num_duplicates_removed
                logger.info(f'Number of duplicate removed between images {object_list_index_1} and {object_list_index_2}: {num_duplicates_removed}') 
                total_duplicates_removed += num_duplicates_removed  
                # resolve diplicate between (col_index, row_index) and (col_index + 1, row_index + 1)
                object_list_index_1, object_list_index_2 = (col_index, row_index), (col_index + 1, row_index + 1)
                num_duplicates_removed = CoralObjectListHelper.invalidate_duplicate_objects_greedy(object_list_of_images[object_list_index_1], object_list_of_images[object_list_index_2], max_displacement)
                total_duplicates_removed += num_duplicates_removed
                logger.info(f'Number of duplicate removed between images {object_list_index_1} and {object_list_index_2}: {num_duplicates_removed}')  
                total_duplicates_removed += num_duplicates_removed     
        logger.info(f'Total number of duplicates removed from overlapping regions between images: {total_duplicates_removed}')    
        return total_duplicates_removed     
       
class CoralObjectDetectImageModel():
    """ CoralObjectDetectImageModel is a delegated class of CoralObjectDetectModel to handle one image. The class returns a list of objects detected within the image.
        The class divides the image into a 2D grid of blobs. There may be overlapped regions between neighouring blobs, specified by the parameter cod_blob_overlap_pix. 
        The class removes any duplicate resulting from the overlappng regions before resolving the final list of objects. 
    """
    def __init__(self, image:np.ndarray, image_col_index:int, image_row_index:int, reco_model:ImageReconstructModel, yolo_model:YoloObjectDetector, locate_tile_model:LocateTileModel=None, **kwargs): 
        """ the constructor
        
        :param image: the source numpy image
        :type image: np.ndarray
        :param image_col_index:the column (x) index of the image, used for reference with the ImageReconstructModel and for data logging
        :type image_col_index: int
        :param image_row_index: the row index (y) of the image, used for reference with the ImageReconstructModel and for data 
        :type image_row_index: int
        :param reco_model: The ImageReconstructModel computed for the 2d grid of images, which is used to map locations from image space to tile space
        :type reco_model: ImageReconstructModel
        :param yolo_model: The YoloObjectDetector model to be used, which should be suitable for the coral species found in the images
        :type yolo_model: YoloObjectDetector        
        :param locate_tile_model: The LocateTileModel model computed for the 2d grid of images, which is used to map locations from reconstruction space to tile space, defaults to None
        :type locate_tile_model: LocateTileModel, optional
        """       
        # other keyword parameters - operational
        self.blob_size = kwargs.get(ModelsConfigNames.COD_BLOB_SIZE.value, None)
        if self.blob_size is None:
            raise AssertionError(f'{type(self).__name__}: Parameter (mandatory) {ModelsConfigNames.COD_BLOB_SIZE.value} is missing')
        # the object categories as defined by the yolo model
        self.coral_classes = kwargs.get(ModelsConfigNames.OBJECT_CLASSES_CORAL.value, [])
        self.dead_coral_classes = kwargs.get(ModelsConfigNames.OBJECT_CLASSES_DEAD_CORAL.value, [])
        # parameters for blob creation and duplicate removal
        self.blob_overlap_pix = kwargs.get(ModelsConfigNames.COD_BLOB_OVERLAP_PIX.value, 0)
        self.duplicate_max_displacement = kwargs.get(ModelsConfigNames.COD_DUPLICATE_MAX_DISPLACEMENT_BLOBS.value, 10)
        # other keyword parameters - output cache and debug information
        self.logdata_folder = kwargs.get(ModelsConfigNames.LOGDATA_FOLDER.value, None)
        # other keyword parameters - use cached detection object list instead of actual detection using the yolo_model
        self.use_cached_object_detection = kwargs.get(ModelsConfigNames.COD_USE_CACHED_OBJECT_DETECTION.value, False)
        self.debug_blob_images = kwargs.get(ModelsConfigNames.COD_DEBUG_BLOB_IMAGES.value, True)
        # model variables
        self.object_class_names:dict = None                   # list of class names of the detection model
        self.metadata_of_blobs = dict()                # metadata of the blobs including detection 
        self.raw_object_list_of_blobs = dict()         # data structure for the duplicate removal process
        self.resolved_object_list = None                  # final object list after duplicate removal
        # attempt to load from cache if the flag is true
        if self.use_cached_object_detection and self.logdata_folder is not None:
            cached_file = os.path.join(self.logdata_folder, f'object_list_{image_col_index}_{image_row_index}.yaml')
            self._load_raw_object_list_of_blobs(cached_file)
        # step 1: load the image if not already loaded
        if type(image) == str:
            try:
                image = cv2.imread(image)
            except (Warning, Exception):
                raise IOError(f'Unable to read image file {image}')
        if type(image) is not np.ndarray:
            raise TypeError(f'Parameter image is neither an image file nor a numpy image') 
        # step 2: traverse through the image coordinates to build a list of logical image blobs 
        image_size = image.shape[:2][::-1]
        step_x, step_y = self.blob_size[0] - self.blob_overlap_pix, self.blob_size[1] - self.blob_overlap_pix
        self.image_blob_grid_size = math.ceil(image_size[0] / step_x), math.ceil(image_size[1] / step_y)
        self.blobs_count = 0
        self.to_update_cache = False
        # start_x and start_y are the top left corner of an image blob
        for start_x in range(0, image_size[0], step_x):
            for start_y in range(0, image_size[1], step_y):
                # compute the blob index, the top left and the bottom right corner of an image blob
                blob_col_index, blob_row_index = start_x // step_x, start_y // step_y 
                corner = (start_x, start_y,)
                end_x, end_y = start_x + self.blob_size[0], start_y + self.blob_size[1]
                end_x, end_y = min(end_x, image_size[0]), min(end_y, image_size[1]) 
                # extract the image blob from the numpy image
                image_blob = image[start_y:end_y, start_x:end_x]
                image_blob_size = image_blob.shape[:2][::-1]
                # compute the cache index
                cache_index = (image_col_index, image_row_index, blob_col_index, blob_row_index,)
                if cache_index not in self.raw_object_list_of_blobs:
                    self.to_update_cache = True
                    # if the object list of the cache index does not exist (not using the cache file), invoke the yolo object detector and extract objects as a list
                    # detect objects in the image_blob using the yolo_model
                    logger.info(f'OBJECT DETECTION in image ({image_col_index, image_row_index}) blob ({blob_col_index, blob_row_index}): {start_x, start_y} {end_x, end_y} {image_blob_size}') 
                    yolo_result:YoloResult = yolo_model.detect(image_blob)
                    if self.object_class_names is None:
                        self.object_class_names = yolo_result.get_class_names()
                    # extract the processing speed information
                    speed_as_dict = yolo_result.get_processes_speed_as_dict() 
                    blob_metdata = {
                        'cod_blob_size': image_blob_size,
                        'cod_blob_bbox': [start_x, start_y, end_x, end_y] 
                    }
                    blob_metdata.update(speed_as_dict)
                    self.metadata_of_blobs[cache_index] = blob_metdata   # the data structure is for logdata
                    object_list = self._extract_objects_from_result(yolo_result, image_col_index, image_row_index, corner, blob_col_index, blob_row_index, reco_model, locate_tile_model)  
                    self.raw_object_list_of_blobs[cache_index] = object_list
                    # if the self.debug_blob_images is True, then generate the annotated image for this image blob and save to the logdata folder
                    if self.debug_blob_images and self.logdata_folder is not None:
                        annotated_image = yolo_result.draw_detection(image_blob, True)
                        cv2.imwrite(os.path.join(self.logdata_folder, f'annotated_blob_{image_col_index}_{image_row_index}_{blob_col_index}_{blob_row_index}.jpg'), annotated_image)
                else:
                    # if the object_list for the cache_index exists, just get it from the data structure
                    object_list = self.raw_object_list_of_blobs[cache_index]
                for coral_object in object_list:
                    logger.info(coral_object)
                self.blobs_count += 1
 
        # save the raw_object_list_of_blobs to cache file
        if self.to_update_cache or (not self.use_cached_object_detection and self.logdata_folder is not None):
            cache_data_file = os.path.join(self.logdata_folder, f'object_list_{image_col_index}_{image_row_index}.yaml')        # save the object list and metadata to the cache file
            logger.info(f'{type(self).__name__}: Save object list and metadata for {self.blobs_count} image blobs to {cache_data_file}')
            self._save_raw_object_list_of_blobs(cache_data_file)
        
        # step 3: iterate through each pair of neighbour blobs
        logger.info(f'DUPLICATE REMOVAL between image blobs in the image ({image_col_index, image_row_index})') 
        self._invalidate_duplicate_objects(self.raw_object_list_of_blobs, image_col_index, image_row_index, self.image_blob_grid_size, self.duplicate_max_displacement)
    
        # step 4: merge object lists of every blob into final object list
        self.resolved_object_list = self._merge_into_image_object_list()
        
        # step 5: generate and save the image annotated with the resolved list of objects if the self.debug_blob_images is True
        if self.debug_blob_images and self.logdata_folder is not None:
            # generate the annotated image for the whole image and save to the logdata folder
            annotated_image = CoralObjectListHelper.annotate_image_with_objects(self.resolved_object_list, image, print_name=True, include_invalidated=False)
            cv2.imwrite(os.path.join(self.logdata_folder, f'annotated_image_{image_col_index}_{image_row_index}.jpg'), annotated_image)            
    
    def _merge_into_image_object_list(self) -> list:
        """ internal function to merge the object lists from the blobs into the overall list

        :return: a list contains the coral objects detected in the image, probably including invalidated objects
        :rtype: list
        """
        all_object_list = []
        for index in self.raw_object_list_of_blobs.keys():
            all_object_list.extend(self.raw_object_list_of_blobs[index])    
        return all_object_list    
    
    def get_object_list(self, include_invalidated=False) -> list:
        """ returns the coral objects of the image as a list

        :param include_invalidated: the list includes the invalidated objects, defaults to False
        :type include_invalidated: bool, optional
        :return: the coral objects of the image as a list
        :rtype: list
        """
        if include_invalidated:
            return self.resolved_object_list
        validate_objects_list = []
        for coral_object in self.resolved_object_list:
            if not coral_object.invalidated:
                validate_objects_list.append(coral_object)
        return validate_objects_list
    
    def get_object_class_names(self) -> dict:
        """ returns a map of class_id, class_name for different classes of coral objects as specified by the object detection model

        :return: a map of class_id, class_name
        :rtype: dict
        """
        return self.object_class_names

    def _save_raw_object_list_of_blobs(self, cache_file:str):
        """ Save the data associated with the detected coral objects to a yaml file

        :param cache_file: path to the target yaml file
        :type cache_file: str
        """
        data = {
            'raw_object_list_of_blobs': self.raw_object_list_of_blobs,
            'metadata_of_blobs': self.metadata_of_blobs,
            'image_blob_grid_size': self.image_blob_grid_size,
            'blobs_count': self.blobs_count,
        }
        with open(cache_file, 'w') as outfile:
            yaml.dump(data, outfile, Dumper=yaml.Dumper)
    
    def _load_raw_object_list_of_blobs(self, cache_file:str):
        """ Load from a yaml file the data associated with the detected coral objects and restore them to the data structures of this object

        :param cache_file: path to the target yaml file
        :type cache_file: str
        """
        try:
            with open(cache_file, 'r') as infile:
                data = yaml.load(infile, Loader=yaml.Loader)
            self.raw_object_list_of_blobs = data['raw_object_list_of_blobs']
            self.metadata_of_blobs = data['metadata_of_blobs']
            return True
        except (Warning, Exception) as e:
            # logger.warning(f'{type(self).__name__}: Failed to load object list of blobs cache file {cache_file}\n{e}')
            ...
        return False

    def _extract_objects_from_result(self, yolo_result:YoloResult, image_col_index:int, image_row_index:int, corner:tuple, blob_col_index:int, blob_row_index:int, 
                                     reco_model:ImageReconstructModel, locate_tile_model:LocateTileModel=None) -> list:
        """ build a list of coral objects (CoralObject class) from the result of yolo model

        :param yolo_result: The result object received from prediction using a yolo model
        :type yolo_result: YoloResult
        :param image_col_index: The column (x) index of the image in the 2d grid of images
        :type image_col_index: int
        :param image_row_index: The row (y) index of the image in the 2d grid of images
        :type image_row_index: int
        :param corner: The topleft corner of the image blob location in the original image
        :type corner: tuple
        :param blob_col_index: The column (x) index of the blob in the 2d grid of blobs resulting from dividing an image 
        :type blob_col_index: int
        :param blob_row_index: The row (y) index of the blob in the 2d grid of blobs resulting from dividing an image 
        :type blob_row_index: int
        :param reco_model: The image reconstruction model for the 2d grid of images of the tile, which is used for mapping locations from image space to the reconstructed image space
        :type reco_model: ImageReconstructModel
        :param locate_tile_model: The locate tile model for mapping a location in reconstructed image space to the tile space, considering the frame of the tile
        :type locate_tile_model: LocateTileModel      
        :param coral_classes: The list of classes from the yolo model that are considered as coral
        :type coral_classes: list               
        :return: A list of CoralObject objects
        :rtype: list
        """
        object_list = []
        yolo_result_list = yolo_result.get_all_objects()
        yolo_result:ObjectType
        for yolo_result in yolo_result_list:
            # extract findings from one result
            bbox_in_blob = yolo_result.bbox
            bbox_in_image = (bbox_in_blob[0] + corner[0], bbox_in_blob[1] + corner[1], bbox_in_blob[2] + corner[0], bbox_in_blob[3] + corner[1])
            bbox_in_reconstructed_image = reco_model.map_bbox(image_col_index, image_row_index, bbox_in_image)
            centre = (bbox_in_reconstructed_image[0] + yolo_result.size[0] // 2, bbox_in_reconstructed_image[1] + yolo_result.size[1] // 2,)
            bbox_in_tile = bbox_in_tile_normalized = None
            # if the locatetile model is available, convert locations in the reconstructed image space into tile space, by considering the location of the frames
            if locate_tile_model is not None:
                bbox_in_tile = locate_tile_model.map_bbox(bbox_in_reconstructed_image)
                bbox_in_tile_normalized = locate_tile_model.normalize_bbox(bbox_in_tile)
                centre_normalized = ((bbox_in_tile_normalized[0] + bbox_in_tile_normalized[2]) / 2, (bbox_in_tile_normalized[1] + bbox_in_tile_normalized[3]) / 2,)
                size_normalized = bbox_in_tile_normalized[2] - bbox_in_tile_normalized[0], bbox_in_tile_normalized[3] - bbox_in_tile_normalized[1] 
            # compute the object class category fron cls_name
            class_category = ObjectClassCategories.NOT_CORAL.value
            if yolo_result.cls_name in self.coral_classes:
                class_category = ObjectClassCategories.CORAL.value
            elif yolo_result.cls_name in self.dead_coral_classes:
                class_category = ObjectClassCategories.DEAD_CORAL.value
            # create the object from the extracted data
            coral_object = CoralObject(
                blob_row_index = blob_row_index,
                blob_col_index = blob_col_index,
                image_row_index = image_row_index,
                image_col_index = image_col_index,
                cls_id = yolo_result.cls_id,
                cls_name = yolo_result.cls_name,
                class_category = class_category,
                bbox = bbox_in_reconstructed_image,
                centre = centre,
                size = yolo_result.size,
                bbox_in_blob = bbox_in_blob,
                bbox_in_tile = bbox_in_tile,
                bbox_normalized = bbox_in_tile_normalized,
                centre_normalized = centre_normalized,
                size_normalized = size_normalized,
            )
            object_list.append(coral_object)
        return object_list

    @staticmethod
    def _invalidate_duplicate_objects(raw_object_list_of_blobs:dict, image_col_index:int, image_row_index:int, image_blob_grid_size:tuple, max_displacement:float):
        """ a generic function for invalidating objects associated with every blobs in an image that are found to be duplicates.

        :param raw_object_list_of_blobs: a 2d grid of object lists, each of which stores objects found from the corresponding blob in the 2d grid of image blobs of an image
        :type raw_object_list_of_blobs: dict
        :param image_col_index:the column (x) index of the image, used for data logging
        :type image_col_index: int
        :param image_row_index: the row index (y) of the image, used for data logger
        :type image_row_index: int        
        :param image_blob_grid_size: the dimension of the 2d grid of object list, which equals to the 2d grid of image blobs
        :type image_blob_grid_size: tuple
        :param max_displacement: the threshold distance beyond which two objects can be considered as duplicates
        :type max_displacement: float
        :return: the total number of objects marked as invalidated by this function
        :rtype: int
        """
        total_duplicates_removed = 0
        # iterate through each row and then each grid locations along a row
        for blob_row_index in range(image_blob_grid_size[1]):
            for blob_col_index in range(image_blob_grid_size[0] - 1):
                # resolve diplicate between (blob_col_index, blob_row_index) and (blob_col_index + 1, blob_row_index)
                object_list_index_1 = (image_col_index, image_row_index, blob_col_index, blob_row_index)
                object_list_index_2 = (image_col_index, image_row_index, blob_col_index + 1, blob_row_index)
                num_duplicates_removed = CoralObjectListHelper.invalidate_duplicate_objects_greedy(raw_object_list_of_blobs[object_list_index_1], raw_object_list_of_blobs[object_list_index_2], max_displacement)
                total_duplicates_removed += num_duplicates_removed
                logger.info(f'Number of duplicate removed between blobs {object_list_index_1} and {object_list_index_2}: {num_duplicates_removed}')
                if blob_row_index >= image_blob_grid_size[1] - 1:
                    continue
                # resolve diplications between (blob_col_index, blob_row_index) and (blob_col_index, blob_row_index + 1)
                object_list_index_1 = (image_col_index, image_row_index, blob_col_index, blob_row_index)
                object_list_index_2 = (image_col_index, image_row_index, blob_col_index, blob_row_index + 1)
                num_duplicates_removed = CoralObjectListHelper.invalidate_duplicate_objects_greedy(raw_object_list_of_blobs[object_list_index_1], raw_object_list_of_blobs[object_list_index_2], max_displacement)
                logger.info(f'Number of duplicate removed between blobs {object_list_index_1} and {object_list_index_2}: {num_duplicates_removed}')
                total_duplicates_removed += num_duplicates_removed
                # resolve diplicate between (blob_col_index, blob_row_index) and (blob_col_index + 1, blob_row_index + 1)
                object_list_index_1 = (image_col_index, image_row_index, blob_col_index, blob_row_index)
                object_list_index_2 = (image_col_index, image_row_index, blob_col_index + 1, blob_row_index + 1)
                num_duplicates_removed = CoralObjectListHelper.invalidate_duplicate_objects_greedy(raw_object_list_of_blobs[object_list_index_1], raw_object_list_of_blobs[object_list_index_2], max_displacement)
                logger.info(f'Number of duplicate removed between blobs {object_list_index_1} and {object_list_index_2}: {num_duplicates_removed}')
                total_duplicates_removed += num_duplicates_removed     
        logger.info(f'Total number of duplicates removed from overlapped regions between blobs: {total_duplicates_removed}')    
        return total_duplicates_removed     
    

class CoralObjectListHelper():
    """ CoralObjectListHelper provides generic functions for processing lists of coral objects

    """
    @staticmethod            
    def invalidate_duplicate_objects_greedy(object_list_1:list, object_list_2:list, max_displacement:float, verbose=False) -> int:
        """ a generic function for invalidating objects from two lists if they are found to co-locate in the tile space, subject to a maximum distance, using the greedy algorithm

        :param object_list_1: a list of CoralObject objects
        :type object_list_1: list
        :param object_list_2: another list of CoralObject objects
        :type object_list_2: list
        :param max_displacement: the threshold distance beyond which two objects can be considered as duplicates
        :type max_displacement: float
        :return: the number of object invalidated in this function
        :rtype: int
        """
        object_1:CoralObject
        object_2:CoralObject
        nearest_match_list = [None] * len(object_list_1)
        # for every object in object_list_1
        for index_1, object_1 in enumerate(object_list_1):
            if object_1.invalidated:
                continue
            # find the object in object_list_2 which is the nearest to object_1
            nearest_index, nearest_dist = None, None
            for index_2, object_2 in enumerate(object_list_2): 
                if index_2 in nearest_match_list:
                    continue
                if object_2.invalidated:
                    continue
                dist = math.pow(object_1.centre[0] - object_2.centre[0], 2) + math.pow(object_1.centre[1] - object_2.centre[1], 2)
                # if the distance between them is beyond the max displacement
                if dist > max_displacement:
                    continue
                if nearest_dist is None or dist < nearest_dist:
                    nearest_index, nearest_dist = index_2, dist
            if nearest_index is not None:
                nearest_match_list[index_1] = nearest_index
        # invalidate one of the matching pairs
        num_duplicates = 0
        for index_1, index_2 in enumerate(nearest_match_list):
            if index_2 is not None:
                object_list_2[index_2].invalidate = True
                if verbose:
                    logger.info(f'Duplicate: {object_list_1[index_1]}\n{object_list_2[index_2]}')
                num_duplicates += 1
        return num_duplicates 
    
    @staticmethod 
    def annotate_image_with_objects(object_list:list, output_image:np.ndarray, print_name=True, include_invalidated=False) -> np.ndarray:
        """ draw objects from a list at their locations on the given numpy image

        :param object_list: a list that contains CoralObject objects to be drawn
        :type object_list: list
        :param output_image: The numpy image as the canvas for drawing
        :type output_image: np.ndarray
        :param print_name: to include classname in the drawing, defaults to True
        :type print_name: bool, optional
        :param include_invalidated: include the invalidated objects, defaults to False
        :type include_invalidated: bool, optional
        :return: the numpy image annotated with locations of the objects
        :rtype: np.ndarray
        """
        palette = YoloResult._get_palette()
        coral_object:CoralObject
        for coral_object in object_list:
            if not include_invalidated and coral_object.invalidated:
                continue
            color = palette[int(coral_object.cls_id)]
            cv2.rectangle(output_image, (int(coral_object.bbox[0]), int(coral_object.bbox[1])),
                        (int(coral_object.bbox[2]), int(coral_object.bbox[3])), color, 3)            
            if print_name:
                cv2.putText(output_image, f'{coral_object.cls_name}',
                        (int(coral_object.bbox[0]), int(coral_object.bbox[1]) - 10),
                        cv2.FONT_HERSHEY_PLAIN, 1.2, (0, 0, 0), 1)
        return output_image        

    @staticmethod
    def get_index_permutations(sequence:list) -> list:
        """ generate a list of all permutations from the given sequence of objects

        :param sequence: a sequence of objects for the generation of permutations
        :type sequence: list
        :return: a list all permutations from the given sequence of objects
        :rtype: list
        """
        # returns if the sequence is empty and there are no permutations
        if len(sequence) == 0:
            return []
        elif len(sequence) == 1:
            return [sequence]
        output_list = [] # empty list that will store current permutation
        # iterate the input sequence and calculate the permutation
        for i in range(len(sequence)):
            m = sequence[i]
            remLst = sequence[:i] + sequence[i+1:]
            for p in CoralObjectListHelper.get_index_permutations(remLst):
                output_list.append([m] + p)
        return output_list
    
    @staticmethod
    def index_permutations(sequence:list):
        """ a generator that yield permutations from the given sequence of objects

        :param sequence: a sequence of objects for the generation of permutations
        :type sequence: list
        :return: one permutation
        :rtype: Generator[Any, Any, Any]
        """
        if len(sequence) <= 1:
            yield sequence
            return
        for perm in CoralObjectListHelper.index_permutations(sequence[1:]):
            for i in range(len(sequence)):
                yield perm[:i] + sequence[0:1] + perm[i:]

class CoralObjectDetectModelHelper():
    """ CoralObjectDetectModelHelper provides helper functions for caching CoralObjectDetectModel to the file system and retrieve the object

    """
    @classmethod            
    def to_yaml_file(cls, cod_model:CoralObjectDetectModel, object_file:str) -> None:
        """ Save an object of CoralObjectDetectModelHelper to a yaml file

        :param cod_model: The CoralObjectDetectModel object
        :type cod_model: CoralObjectDetectModel
        :param object_file: The target file path of the yaml file, defaults to None, which returns the yaml as a string
        :type object_file: str, optional
        """
        logger.info(f'{type(cls).__name__}: Save CoralObjectDetectModel to {object_file}')
        cod_model._save_object_list_of_images(object_file)
        
    @staticmethod
    def from_yaml_file(object_file:str) -> CoralObjectDetectModel:
        """ Load an object of CoralObjectDetectModelHelper from a yaml file

        :param object_file: The source file path of the yaml file
        :type object_file: str
        :return: An object of CoralObjectDetectModel loaded from the yaml file 
        :rtype: CoralObjectDetectModel
        """
        return CoralObjectDetectModel.from_yaml_file(object_file)

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
    logger.info(f'test_coral_object_detect_model: started')
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
    image_map_as_list = test_get_cgras_sample_images_as_list()   
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
