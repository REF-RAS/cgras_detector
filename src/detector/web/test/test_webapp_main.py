# Copyright 2024 - Andrew Kwok Fai LUI, 
# Robotics and Autonomous Systems Group, REF, RI
# and the Queensland University of Technology

__author__ = 'Andrew Lui'
__copyright__ = 'Copyright 2024'
__license__ = 'GPL'
__version__ = '1.0'
__email__ = 'ak.lui@qut.edu.au'
__status__ = 'Development'

# import libraries
import sys, os, signal, io, yaml, json, time, traceback
from flask import Flask
from flask_restx import Api, Resource
from requests import put, get


def call_detected_objects_query():
    # http://0.0.0.0:8023/api/detected_objects/query/2024Oct-MIS5T01_CG1-202411192300
    URL = 'http://0.0.0.0:8023/api/detected_objects/query/2024Oct-MIS5T01_CG1-202411192300'
    result = get(URL)
    if result.status_code == 200:
        print(result.json())
    else:
        print(f'Status Code: {result.status_code}')

def call_tile_samples_list():
    # http://0.0.0.0:8023/api/tile_samples/list/2024Oct
    URL = 'http://0.0.0.0:8023/api/tile_samples/list/2024Oct'
    result = get(URL)
    if result.status_code == 200:
        print(result.json())
    else:
        print(f'Status Code: {result.status_code}')
        
def call_import_tile_sample():
    # http://0.0.0.0:8023/api/tile_samples/import
    URL = 'http://0.0.0.0:8023/api/tile_samples/import'
    YAML_FILE = '/home/qcr/cgras_ws/src/cgras_detector/docs/detector_tile_sample_import_chris_mis5_t05_241031.yaml'
    with open(YAML_FILE, 'r') as infile:
        yaml_data = infile.read()
        result = put(URL, data={'data': yaml_data})
        
        if result.status_code == 200:
            print(result.json())
        else:
            print(f'Status Code: {result.status_code}\n{result.json()}')
    
# call_detected_objects_query()

# call_tile_samples_list()

call_import_tile_sample()