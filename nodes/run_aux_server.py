#!/usr/bin/env python3

# Copyright 2024 - Andrew Kwok Fai LUI, 
# Robotics and Autonomous Systems Group, REF, RI
# and the Queensland University of Technology

__author__ = 'Andrew Lui'
__copyright__ = 'Copyright 2024'
__license__ = 'GPL'
__version__ = '1.0'
__email__ = 'ak.lui@qut.edu.au'
__status__ = 'Development'

import sys, signal
import http.server
import socketserver

import rospy

from detector.model import CONFIG, SystemConfigNames

from cgras_datatools.logging_tools import logger

# callback function for shutdown
def cb_shutdown():
    logger.info('CGRAS ImageWebServer: the ros node is being shutdown')
    # sys.exit(0)

# callback function for the interrupt signal SIGINT
def cb_stop_server(*args, **kwargs):
    logger.info('CGRAS ImageWebServer: the ros node is being stopped')
    sys.exit(0)

# ----------------------------------------------------------------------
# The main program for running the detector as a web server and a daemon
if __name__ == '__main__':
    SERVER = CONFIG.get(SystemConfigNames.AUX_WEB_HOST, '0.0.0.0')
    PORT = CONFIG.get(SystemConfigNames.AUX_WEB_PORT, 8024)
    DIRECTORY = CONFIG.get(SystemConfigNames.AUX_WEB_DIRECTORY, '/home/qcr/cgras/images')

    # create the stop signal handler
    signal.signal(signal.SIGINT, cb_stop_server)
    rospy.on_shutdown(cb_shutdown)

    class Handler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=DIRECTORY, **kwargs)
        # stop the log print to console
        def log_message(self, format, *args):
            ...
            
    # Handler = http.server.SimpleHTTPRequestHandler
    with socketserver.TCPServer((SERVER, PORT), Handler) as httpd:
        logger.info(f'Starting the image server at http://{SERVER}:{PORT} from {DIRECTORY}')
        httpd.serve_forever()
