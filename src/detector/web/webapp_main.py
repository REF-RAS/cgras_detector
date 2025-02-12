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
import sys, os, signal, io, yaml, time, traceback
from flask import Flask, request
from flask_restx import Api, Resource

from detector.model import DETECT_DAO, logger

RESTX_API = Api()

@RESTX_API.route('/api/detected_objects/query/<string:tile_sample_id>')
class DetectedObjects(Resource):
    def get(self, tile_sample_id):
        results = DETECT_DAO.query_detected_objects(tile_sample_id).to_dict('records')
        results = [] if results is None else results
        return results

@RESTX_API.route('/api/tile_samples/list/<string:season_title>')
class TileSamples(Resource):
    def get(self, season_title):
        results = DETECT_DAO.list_tile_samples(season_title).to_dict('records')
        results = [] if results is None else results
        return results
    
@RESTX_API.route('/api/tile_samples/import')
class TileSamplesImport(Resource):
    def put(self):
        yaml_data = request.form['data']
        tile_sample_data = yaml.load(yaml_data, Loader=yaml.Loader)
        # logger.info(f'Received tile sample import restful call: {tile_sample_data}')     
        is_valid, model = DETECT_DAO.validate_tile_sample_import(tile_sample_data)
        if not is_valid:
            return {'error': model.to_dict('records')}, 201
        result = DETECT_DAO.import_tile_sample_yaml(tile_sample_data)
        if not result:
            return {'error': 'Failed to import tile sample (Unknown reason)'}, 201
        return []