# Copyright 2024 - Andrew Kwok Fai LUI, 
# Robotics and Autonomous Systems Group, REF, RI
# and the Queensland University of Technology

__author__ = 'Andrew Lui'
__copyright__ = 'Copyright 2024'
__license__ = 'GPL'
__version__ = '1.0'
__email__ = 'ak.lui@qut.edu.au'
__status__ = 'Development'

import sys, random
from detector.model import DETECT_DAO
from detector.dao_detect import StatusNames, ClassHierarchyPresentation, ClassHierarchyCoral

def change_tile_sample_status(tile_sample_id:str, status:int):
    DETECT_DAO.update_tile_sample_status(tile_sample_id, status)


def add_new_tile_sample():   
    # add new tile_sample
    new = {
        # 'id': '2024-Nov-P00001-CG1-202411151200',
        'tile_id': '2023Dec-P00001',
        'batch_id': 'CG1-202311211200',
        'batch_time': '2023-11-21T12:00:00',
        'age': 9,
        'species': 'acropora palmata',
        'season': '2023Dec',
        'settle_time': '2023-11-12 12:00:00',
        'importer_id': 'YAML',
        'operator': 'luia2',
        'create_time': '2024-10-02 04:11:00',
        'status': StatusNames.SUCCESS.value,
        'priority': '2024-10-02 04:11:00'
    }
    try:
        DETECT_DAO.add_tile_sample(new['tile_id'], new['batch_id'], new['batch_time'], new['age'], new['species'], new['season'], new['settle_time'], new['importer_id'], 
                               new['operator'], new['status'])
        print(f'Add success: {new["tile_id"], new["batch_id"]}')
    except Exception as e:
        print(f'Add failed: {e}')
        
    new = {
        # 'id': '2024-Nov-P00001-CG1-202411151200',
        'tile_id': '2023Dec-P00001',
        'batch_id': 'CG1-202311251200',
        'batch_time': '2023-11-25T12:00:00',
        'age': 13,
        'species': 'acropora palmata',
        'season': '2023Dec',
        'settle_time': '2023-11-12 12:00:00',
        'importer_id': 'YAML',
        'operator': 'luia2',
        'create_time': '2024-10-02 04:11:00',
        'status': StatusNames.SUCCESS.value,
        'priority': '2024-10-02 04:11:00'
    }
    try:
        DETECT_DAO.add_tile_sample(new['tile_id'], new['batch_id'], new['batch_time'], new['age'], new['species'], new['season'], new['settle_time'], new['importer_id'], 
                               new['operator'], new['status'])
        print(f'Add success: {new["tile_id"], new["batch_id"]}')
    except Exception as e:
        print(f'Add failed: {e}')
    
def add_fake_detected_objects():
    def generate_detected_objects(new_tile_sample_id, tile_sample_detect_stat_dict, reduction = 0.85):
        for index, row in detected_objects_df.iterrows():
            if random.random() <= reduction:
                DETECT_DAO.add_detected_object(new_tile_sample_id, row['yolo_class'], row['coral_class'], row['present_class'], row['centre_x'], row['centre_y'], 
                                row['corner_x1'], row['corner_y1'], row['size_x'], row['size_y'])
            else:
                DETECT_DAO.add_detected_object(new_tile_sample_id, 'dead', ClassHierarchyCoral.DEAD_CORAL.value, ClassHierarchyPresentation.DEAD_CORAL.value, row['centre_x'], row['centre_y'], 
                                row['corner_x1'], row['corner_y1'], row['size_x'], row['size_y'])
        # add the detection stat for the new tile_sample_id
        new = tile_sample_detect_stat_dict
        coral_count = int(new['coral_alive_count'] * reduction)
        other_count = int(new['other_count'] * random.normalvariate(1.0, 0.15) )
        coral_dead_count = int(new['coral_dead_count'] + new['coral_dead_count'] * (1 - reduction))
        DETECT_DAO.update_tile_sample_detect_stat(new_tile_sample_id, new['tile_pixel_x'], new['tile_pixel_y'], coral_count, coral_dead_count, other_count, 
                                                new['duplicates_removed'], new['yaml_data'])
    
    # retrieve detected objects for the source tile_sample_id
    tile_sample_id = '2023Dec-P00001-CG1-202311151200'
    detected_objects_df = DETECT_DAO.query_detected_objects(tile_sample_id)
    # retrieve detection stat of the source tile_sample_id
    tile_sample_detect_stat_dict = DETECT_DAO.get_tile_sample_detect_stat(tile_sample_id)
    print(f'tile_sample: {tile_sample_detect_stat_dict} {tile_sample_id}')
    # generate object list for the new tile_sample_id based on randomized setting the class to recruit_dead
    new_tile_sample_id = '2023Dec-P00001-CG1-202311211200'
    DETECT_DAO.delete_detected_objects_of_tile_sample(new_tile_sample_id)
    generate_detected_objects(new_tile_sample_id, tile_sample_detect_stat_dict, reduction = 0.85)
    # generate object list for the new tile_sample_id based on randomized setting the class to recruit_dead
    new_tile_sample_id_2 = '2023Dec-P00001-CG1-202311251200'
    tile_sample_detect_stat_dict = DETECT_DAO.get_tile_sample_detect_stat(new_tile_sample_id)
    DETECT_DAO.delete_detected_objects_of_tile_sample(new_tile_sample_id_2)
    generate_detected_objects(new_tile_sample_id_2, tile_sample_detect_stat_dict, reduction = 0.75)    
    


def generate_test_data():
    tile_sample_id = '2023Dec-P00001-CG1-202311151200'
    change_tile_sample_status(tile_sample_id, StatusNames.SUCCESS.value) 
    add_new_tile_sample()
    add_fake_detected_objects()

if __name__ == '__main__':
    generate_test_data()
