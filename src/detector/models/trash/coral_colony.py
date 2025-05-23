# Copyright 2025 - Andrew Kwok Fai LUI, 
# Robotics and Autonomous Systems Group, REF, RI
# Queensland University of Technology, Australia

__author__ = 'Andrew Lui'
__copyright__ = 'Copyright 2025'
__license__ = 'GPL'
__version__ = '1.0'
__email__ = 'ak.lui@qut.edu.au'
__status__ = 'Development'

import os, shutil, yaml, copy, importlib
from pathlib import Path
import numpy as np
import cv2
from sklearn.svm import OneClassSVM
from sklearn.cluster import DBSCAN
# project modules
from detector.dao_detect import CoralObject, ClassHierarchyPresentation, ClassHierarchyCoral

            # coral_object = CoralObject(
            #     blob_row_index = blob_row_index,
            #     blob_col_index = blob_col_index,
            #     image_row_index = image_row_index,
            #     image_col_index = image_col_index,
            #     cls_id = yolo_result.cls_id,
            #     yolo_class = yolo_result.cls_name,      # class at the yolo layer
            #     coral_class = coral_class,              # class at the coral layer
            #     present_class = None,                   # class at the presentation layer
            #     bbox = bbox_in_reconstructed_image,
            #     centre = centre,
            #     size = yolo_result.size,
            #     bbox_in_blob = bbox_in_blob,
            #     bbox_in_image = bbox_in_image,
            #     bbox_in_tile = bbox_in_tile,
            #     bbox_normalized = bbox_in_tile_normalized,
            #     centre_normalized = centre_normalized,
            #     size_normalized = size_normalized,
            # )

class CoralColony():
    @staticmethod
    def predict_coral_colonies(image:np.ndarray, object_list:list, working_scale:float=0.2, **kwargs) -> list:
        # input parameters
        MIN_CORAL_SIZE_PX = kwargs.get('min_coral_size_px', 20)
        EXCLUDE_BORDER_PIXEL_RATIO = kwargs.get('exclude_border_pixel_ratio', 1.0)
        MAX_DIST_PX = kwargs.get('same_cluster_max_dist_px', 100)  # maximum distance between data points
        # image size
        image_size = image.shape[:2][::-1]
        # downscale the image
        image_scaled_size = (int(image_size[0] * working_scale), int(image_size[1] * working_scale))
        # downscale the image
        image_scaled = cv2.resize(image, image_scaled_size)  
        # declare data structure
        all_colony_bboxes = []
        contours_list = []
        image_filtered_list = []
        image_filtered_grey_list = []
        # generate bboxes
        bboxes = []
        obj:CoralObject
        for obj in object_list:
            bboxes.append({
                'xyxy': obj.bbox_in_blob,
            })
        # apply dbscan to identify clusters
        cluster_results = CoralColony._build_cluster_analysis_model(working_scale, bboxes)
        if cluster_results is not None and cluster_results['max_dbscan_id'] is not None:
            for cluster_id in range(cluster_results['max_dbscan_id'] + 1):
                # extract training samples
                bboxes_of_cluster_id = cluster_results['dbscan_id_members'][cluster_id]
                px_in_roi_coral = CoralColony._sample_train_data(image_scaled, working_scale, bboxes_of_cluster_id, sample_coverage=EXCLUDE_BORDER_PIXEL_RATIO)
                if px_in_roi_coral is None or len(px_in_roi_coral) < MIN_CORAL_SIZE_PX:    # if there are fewer than 5 samples, abort as not a valid cluster
                    continue
                # build one class classifier
                clf:OneClassSVM = CoralColony._build_one_classifier(px_in_roi_coral, **kwargs)
                # predict cluster bboxes
                colony_bboxes, contours, image_filtered, image_filtered_grey = CoralColony._predict_colony_bboxes(clf, 
                                                image_scaled, working_scale, bboxes_of_cluster_id, **kwargs)
                contours_list.extend(contours)
                # store the debug images
                image_filtered_list.append(image_filtered)
                image_filtered_grey_list.append(image_filtered_grey)
                all_colony_bboxes.extend(colony_bboxes)
        # draw all the contours on the scaled image for debug
        for cnt in contours_list:
            bbox = cv2.boundingRect(cnt) # x, y, w, h
            cv2.rectangle(image_scaled, (bbox[0], bbox[1]), (bbox[0] + bbox[2], bbox[1] + bbox[3]), (0, 255, 0), 1)          
        # prepare a dict of debug images
        debug_images = {
            # 'image_filtered': image_filtered,
            # 'image_filtered_grey': image_filtered_grey,
            'image_scaled': image_scaled,
        }
        for i, (image_filtered, image_filtered_grey) in enumerate(zip(image_filtered_list, image_filtered_grey_list)):
            debug_images[f'image_filtered_{i}'] = image_filtered
            debug_images[f'image_filtered_grey_{i}'] = image_filtered_grey
        # package debug images
        return all_colony_bboxes, debug_images

    @staticmethod
    def _build_cluster_analysis_model(scale_of_image:float, bboxes:list, **kwargs):
        # input parameters
        MAX_DIST_PX = kwargs.get('same_cluster_max_dist_px', 100)  # maximum distance between data points
        EPS = MAX_DIST_PX * scale_of_image
        # test if no bbox
        if not bboxes:
            return None
        # declare data structure 
        coral_pos_list = []
        # iterate through the bbox in the list of rois where the pixel values are considered training data
        for bbox_dict in bboxes:
            bbox_xyxy = bbox_dict['xyxy']
            pos_x, pos_y = int(bbox_xyxy[0] * scale_of_image), int(bbox_xyxy[1] * scale_of_image)
            coral_pos_list.append([pos_x, pos_y])
        X = np.array(coral_pos_list)        
        clustering = DBSCAN(eps=EPS, min_samples=1).fit(X)
        # organize the results for ease of handling
        max_cluster_id = None
        cluster_members = {}
        for bbox_dict, cluster_id in zip(bboxes, clustering.labels_):
            if cluster_id == -1:  # ignore the noisy data
                continue
            # annotate the bbox_dict
            bbox_dict['dbscan_id'] = str(cluster_id)
            # organize in cluster members
            if cluster_id in cluster_members:
                cluster_members[cluster_id].append(bbox_dict)
            else:
                cluster_members[cluster_id] = [bbox_dict]
            max_cluster_id = cluster_id if max_cluster_id is None else max(max_cluster_id, cluster_id)
        results_dict = {
            'max_dbscan_id': max_cluster_id,
            'dbscan_id_members': cluster_members,
            'labels_list': clustering.labels_
        }
        return results_dict

    @staticmethod
    def _build_one_classifier(px_in_roi_coral, **kwargs) -> OneClassSVM:
        one_class_svm_param_list = ['gamma', 'kernel']
        one_class_svm_params = {}
        for key in kwargs:
            if key in one_class_svm_param_list:
                one_class_svm_params[key] = kwargs[key]
        clf = OneClassSVM(**one_class_svm_params).fit(px_in_roi_coral)
        return clf

    def _predict_colony_bboxes(clf:OneClassSVM, image_scaled:np.ndarray, scale_of_image:float, bboxes:list,  **kwargs):
        # input parameters
        OPEN_ITERATIONS = kwargs.get('open_morph_iterations', 3)
        STEP_ITERATIONS = kwargs.get('step_morph_iterations', 2)
        MORPH_KERNEL_SIZE = kwargs.get('morph_kernel_size', 5)
        # size of image
        image_scaled_size = image_scaled.shape[:2][::-1]
        image_size = (int(image_scaled_size[0] / scale_of_image), int(image_scaled_size[1] / scale_of_image))
        # apply the classifier on the image
        X = np.stack((
                image_scaled[:, :, 0].flatten(),
                image_scaled[:, :, 1].flatten(),
                image_scaled[:, :, 2].flatten(),
            ), axis = 1)
        # classified each pixel
        y = clf.predict(X)
        # reshape the output which is of shape (height * width,) to (height, width)
        y = y.reshape((image_scaled.shape[0], image_scaled.shape[1]))
        y[y == 1] = 255
        y[y == -1] = 0
        image_filtered = y.astype(np.uint8)
        # apply morthological operations
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT,(MORPH_KERNEL_SIZE, MORPH_KERNEL_SIZE))
        kernel_small = cv2.getStructuringElement(cv2.MORPH_CROSS,(3, 3))
        image_filtered_grey = image_filtered
        # image_filtered = cv2.morphologyEx(image_filtered, cv2.MORPH_CLOSE, kernel=kernel, iterations=MORPH_ITERATIONS)
        
        for i in range(OPEN_ITERATIONS):
            image_filtered = cv2.morphologyEx(image_filtered, cv2.MORPH_DILATE, kernel, iterations=STEP_ITERATIONS)
            image_filtered = cv2.morphologyEx(image_filtered, cv2.MORPH_ERODE, kernel, iterations=STEP_ITERATIONS)

        contours, hierarchy = cv2.findContours(image_filtered, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        colony_bboxes = []
        for cnt in contours:
            rect = cv2.boundingRect(cnt) # x, y, w, h
            colony_bbox = {
                'x': int(rect[0] / scale_of_image),
                'y': int(rect[1] / scale_of_image),
                'width': int(rect[2] / scale_of_image),
                'height': int(rect[3] / scale_of_image),
                'size': int(rect[2] * rect[3] / (scale_of_image * scale_of_image)),
                '_coral_bboxes': [],
            }
            colony_bbox.update({
                'xyxy': [colony_bbox['x'], colony_bbox['y'], colony_bbox['x'] + colony_bbox['width'], colony_bbox['y'] + colony_bbox['height']],
                'normalized_bbox': [(colony_bbox['x'] + colony_bbox['width'] / 2) / image_size[0], 
                                    (colony_bbox['y'] + colony_bbox['height'] / 2) / image_size[1], 
                                    colony_bbox['width'] / image_size[0], colony_bbox['height'] / image_size[1],],
            })

            added_to_colony_bboxes = False 
            for bbox_dict in bboxes:
                bbox_xyxy = bbox_dict['xyxy']
                if CoralColony._point_in_bbox(colony_bbox['xyxy'], ((bbox_xyxy[0] + bbox_xyxy[2]) // 2, (bbox_xyxy[1] + bbox_xyxy[3]) // 2)):
                    if not added_to_colony_bboxes:
                        colony_bboxes.append(colony_bbox)
                        added_to_colony_bboxes = True
                # update the list of corals that a cluster bbox contains
                colony_bbox['_coral_bboxes'].append(bboxes)
                # update the list of cluster bbox that a coral is inside
                if '_candidate_colony_bbox' in bbox_dict:
                    bbox_dict['_candidate_colony_bboxes'].append(colony_bbox)
                else:
                    bbox_dict['_candidate_colony_bboxes'] = [colony_bbox]
                    
        # remove the operational note on the bboxes
        for bbox_dict in bboxes:
            if '_candidate_colony_bboxes' in bbox_dict:
                del bbox_dict['_candidate_colony_bboxes']
        for colony_bbox in colony_bboxes:
            del colony_bbox['_coral_bboxes']
        # return the results
        return colony_bboxes, contours, image_filtered, image_filtered_grey

    @staticmethod
    def _sample_train_data(image_scaled:np.ndarray, scale_of_image:float, bboxes:list, sample_coverage:float=0.8):
        # computer scale factor and scaled image size
        # image_size = image_scaled.shape[:2][::-1]
        px_in_roi_coral = None
        # iterate through the bbox in the list of rois where the pixel values are considered training data
        for bbox_dict in bboxes:
            bbox_xyxy = bbox_dict['xyxy']
            x, y = int(bbox_xyxy[0] * scale_of_image), int(bbox_xyxy[1] * scale_of_image)
            x2, y2 = int(bbox_xyxy[2] * scale_of_image), int(bbox_xyxy[3] * scale_of_image)
            px_in_roi = CoralColony._extract_px_in_roi(image_scaled, x, y, x2, y2, sample_coverage=sample_coverage)
            px_in_roi_coral = px_in_roi if px_in_roi_coral is None else np.vstack((px_in_roi_coral, px_in_roi))
        return px_in_roi_coral

    @staticmethod
    def _extract_px_in_roi(image:np.ndarray, x1, y1, x2, y2, sample_coverage:float=1.0):

        size_x, size_y = x2 - x1, y2 - y1
        # apply coverage
        offset_x = int(size_x * (1.0 - sample_coverage) // 2)
        offset_y = int(size_y * (1.0 - sample_coverage) // 2)
        x1 += offset_x
        x2 -= offset_x
        y1 += offset_y
        y2 -= offset_y
        # collect the pixel values
        B = image[y1:y2, x1:x2, 0].flatten()
        G = image[y1:y2, x1:x2, 1].flatten()
        R = image[y1:y2, x1:x2, 2].flatten()
        px_in_roi = np.stack((B, G, R), axis=1)        
        return px_in_roi

    
    def draw_colony_id(image:np.ndarray, bboxes:list, colour:tuple=(0, 63, 255), font_size:float=0.6) -> np.ndarray:
        # draw cluster_id
        for bbox in bboxes: 
            if 'dbscan_id' in bbox:
                cv2.putText(image, f'{bbox["dbscan_id"]}', (bbox['xyxy'][:2]), cv2.FONT_HERSHEY_SIMPLEX, font_size, colour, 1, cv2.LINE_AA)       
        return image        
    
    
    @staticmethod
    def _point_in_bbox(xyxy:tuple, point:tuple) -> bool:
        """ Test if the point (x, y) or (x, y, z) is in the bbox
        
        :param point: the (x, y) or (x, y, z) value of the point
        :type point: list of 2 or 3 numbers
        :param xyxy: the bounding square or bounding box
        :type xyxy: (x1, y1, x2, y2) or (x1, y1, z1, x2, y2, z2)
        :return: True if the point is within the bbox
        :rtype: bool
        """
        if xyxy is None or type(xyxy) not in (list, tuple) or point is None or type(point) not in (list, tuple):
            return False
        return (xyxy[0] <= point[0] <= xyxy[2]) and (xyxy[1] <= point[1] <= xyxy[3])
    

    
    @staticmethod
    def draw_bbox(image:np.ndarray, bboxes:list, colour:tuple=(0, 255, 0), class_label:int=None, draw_label:bool=True) -> np.ndarray:
        for bbox in bboxes:
            if class_label is not None and ('label' not in bbox or class_label == bbox['label']):
                cv2.rectangle(image, (bbox['xyxy'][:2]), bbox['xyxy'][2:], colour, 1) 
                if draw_label:
                    cv2.putText(image, f'{bbox["label"]}', (bbox['xyxy'][:2]), cv2.FONT_HERSHEY_SIMPLEX, 0.6, colour, 1, cv2.LINE_AA)        
        return image


    

    

    
