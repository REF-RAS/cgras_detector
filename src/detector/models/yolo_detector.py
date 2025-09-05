# Copyright 2024 - Andrew Kwok Fai LUI, 
# Robotics and Autonomous Systems Group, REF, RI
# and the Queensland University of Technology

__author__ = 'Andrew Lui'
__copyright__ = 'Copyright 2024'
__license__ = 'GPL'
__version__ = '1.0'
__email__ = 'ak.lui@qut.edu.au'
__status__ = 'Development'

from collections import namedtuple
import numpy as np
import cv2
from ultralytics import YOLO
import numpy as np
import seaborn as sns

from detector.models import logger

# a data structure representing a coral object detected by the YOLO model
ObjectType = namedtuple('ObjectType', ['cls_id', 'cls_name', 'bbox', 'topleft', 'size', 'centre', 'points', 'conf'])

class YoloResult():
    """ Model the object detection results returned by YOLO and provide functions for getting the results easier
    """
    def __init__(self, yolo_predict_results:list):
        """ the constructor

        :param yolo_predict_results: the object returned from the call to YOLO.predict
        """
        if len(yolo_predict_results) != 1:
            raise AssertionError(f'{type(self).__name__}: Input parameter yolo_predict_results does not contain the expected one result')
        self.yolo_predict_results = yolo_predict_results

    def get_processes_speed_as_dict(self, total_speed_dict:dict=None) -> dict:
        """ return the time taken for individual stages in the predict processing

        :return: a dict containing key-value pairs representing the time taken for every stage
        """
        speed_dict = dict(self.yolo_predict_results[0].speed)
        if total_speed_dict is None:
            total_speed_dict = speed_dict
        else:
            for key in total_speed_dict:
                total_speed_dict[key] += speed_dict.get(key, 0)
        # iterate through the values in the speed attribute of the result object from YOLO to update the total time
        total_time = 0
        for value in total_speed_dict.values():
            total_time += value
        # populate the total time taken
        total_speed_dict['total_time'] = total_time
        return total_speed_dict

    def get_class_names(self):
        """ return the names of the object classes as a list

        :return: the list
        """
        return self.yolo_predict_results[0].names 
    
    def num_objects(self) -> int:
        """ return the number of objects found in the image

        :return: the number of objects as an int
        """
        return len(self.yolo_predict_results[0].boxes)
    
    def get_object(self, index:int) -> ObjectType:
        """ return an object of ObjectType that contains information of the detected object at index

        :param index: the index 
        :return: the detected object at the index as ObjectType
        """
        if index < 0 or index >= self.num_objects():
            raise AssertionError(f'{type(self).__name__} (get_object_class_bbox): Input parameter index is invalid')
        # obtain the bounding box, class_id, size, and the centre of the object
        box = self.yolo_predict_results[0].boxes[index]
        cls_id = int(box.cls[0])
        bbox = [int(a) for a in box.xyxy.tolist()[0]]
        size = (bbox[2] - bbox[0], bbox[3] - bbox[1],)
        centre = (bbox[0] + size[0] // 2, bbox[1] + size[1] // 2,)
        # handle the mask
        points = []
        mask = None
        if isinstance(self.yolo_predict_results[0].masks, list):
            mask = self.yolo_predict_results[0].masks[index]
        if mask is not None:
            for point in mask.xy[0]:
                points.append(point.tolist())
        # create and return the object as an ObjectType
        return ObjectType(cls_id, self.yolo_predict_results[0].names[cls_id], bbox, bbox[:2], size, centre, points, box.conf.tolist()[0])
    
    def get_all_objects(self) -> list:
        """ return a list of all detected objects

        :return: a list of ObjectType
        """
        object_list = []
        for index in range(self.num_objects()):
            object_info = self.get_object(index)
            object_list.append(object_info)
        return object_list
    
    @classmethod
    def _get_palette(cls):
        """ return a color palette which is used by the function drawing detected objects on an image 

        :return: the color palette as an array of 3-tuple of RGB values in the range (0, 255)
        """
        if not hasattr(cls, 'palette'):
            palette = sns.color_palette(palette='tab20', n_colors=24)  # previously 'hls'
            cls.palette = []
            # convert the palette from sns which is normalized (0, 1) to the range (0, 255) suitable for opencv drawing
            for color in palette:
                cls.palette.append((int(color[0] * 255), int(color[1] * 255), int(color[2] * 255)))
        return cls.palette

    def draw_detection(self, image:np.ndarray, print_name=False) -> np.ndarray:
        """ draw the detected objects on the given numpy image

        :param image: the numpy image on which the detected objects are drawn
        :param print_name: whether to print the class name of the object, defaults to False
        :return: the same numpy image annotated with detected objects' bounding box and name
        """
        palette = YoloResult._get_palette()
        for result in self.yolo_predict_results:
            for box in result.boxes:
                color = palette[int(box.cls[0])]
                cv2.rectangle(image, (int(box.xyxy[0][0]), int(box.xyxy[0][1])),
                            (int(box.xyxy[0][2]), int(box.xyxy[0][3])), color, 3)
                if print_name:
                    text_to_draw = f'{result.names[int(box.cls[0])]} ({box.conf.tolist()[0]:.1f})'
                    cv2.putText(image, text_to_draw,
                            (int(box.xyxy[0][0]), int(box.xyxy[0][1]) - 10),
                            cv2.FONT_HERSHEY_PLAIN, 1.2, (0, 0, 0), 1)
        return image

class YoloObjectDetector():
    """ A wrapper class for YOLO so that the results of object detection are presented as an object of YoloResult class providing
        convenient functions
    """
    def __init__(self, yolo_model_file:str, blob_size:tuple, classes_map:dict, predict_params:dict, keep_object_filter:dict):
        """ the constructor

        :param yolo_model_file: the path to the .pt yolo model file 
        :param blob_size: a tuple of two integer indicating the input image size for the yolo model
        :param classes_map: a dict that contains mapping between yolo model classes and internal coral classes
        :param predict_params: a dict that contains parameters of inference using yolo model
        :param keep_object_filter: a dict that contains conditions that filter and keep objects      
        """
        assert yolo_model_file is not None, 'Parameter (yolo_model_file) is None'
        self.model:YOLO = YOLO(yolo_model_file)
        # assign other input parameters
        self.blob_size = blob_size
        self.classes_map = classes_map
        self.predict_params = predict_params
        self.keep_object_filter = keep_object_filter
    
    def detect(self, image_cv:np.ndarray) -> YoloResult:
        """ apply the Yolo model on the given numpy image and return the results as a YoloResult object

        :param image_cv: the numpy image 
        :return: a YoloResult object containing the detected objects in the numpy image
        """
        # logger.warning(f'YoloObjectDetector detect: apply parameters {self.predict_params}')
        yolo_result = self.model.predict(image_cv, **self.predict_params)
        return YoloResult(yolo_result)
    
    def get_classes_list(self) -> list:
        """ return the classes defined in the Yolo model

        :return: the class names in a list
        """
        return self.model.names
    
    def get_keep_object_filter(self) -> list:
        """ return the dict containing conditions for keep object filter

        :return: the dict containing the conditions
        """
        return self.keep_object_filter
    
    def get_blob_size(self) -> tuple:
        """ return tuple of two integer indicating the input image size for the yolo model

        :return: a tuple of two integer indicating the input image size for the yolo model
        """
        return self.blob_size
    
    def get_classes_map(self) -> list:
        """ return a dict that contains mapping between yolo model classes and internal coral classes

        :return: a dict that contains mapping between yolo model classes and internal coral classes
        """
        return self.classes_map

    # a test function
    def _test(self):
        # info_list = self.model.info(detailed=True, verbose=False)
        # test with a blank image
        image_cv = np.zeros((16, 16, 3), dtype=np.uint8)  
        yolo_result:YoloResult = self.detect(image_cv)

if __name__ == '__main__':
    # yolo_model_file = ' /home/qcr/cgras_data/YoloModel/20240926_cgras_tiled_yolov8n_seg_640p.pt'
    yolo_model_file = ' /home/qcr/cgras_data/YoloModel/20240923_tiledimages_yolov8xseg_naive.pt'
    classes_map = {'POLYP_KEYPART': ['alive'],
                        'POLYP_MULTI': ['mask_live'],
                        'DEAD_CORAL': ['dead', 'mask_dead'],
                        }
    yolo_detector = YoloObjectDetector(yolo_model_file, blob_size=(640, 640), classes_map=classes_map, predict_params={}, keep_object_filter={})
    print(yolo_detector.info())