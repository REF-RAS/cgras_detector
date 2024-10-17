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

# import libraries
import  webbrowser
# ros modules
import rospy
# project modules: web and generic

from cgras.tools.logging_tools import logger
from cgras.detector.model import CONFIG, SystemConfigNames
from cgras.detector.run import ApplicationCoordinator

# ----------------------------------------------------------------------
# The main program for running the detector as a web server and a daemon
if __name__ == '__main__':
    rospy.init_node(ApplicationCoordinator.NODE_NAME, anonymous=False)
    the_agent = ApplicationCoordinator()
    DASH_HOST = CONFIG.get(SystemConfigNames.CGRAS_DETECTOR_WEB_HOST)
    DASH_PORT = CONFIG.get(SystemConfigNames.CGRAS_DETECTOR_WEB_PORT)
    if CONFIG.get(SystemConfigNames.CGRAS_DETECTOR_WEB_LAUNCH_BROWSER, False):
        URL = f'http://{DASH_HOST}:{DASH_PORT}'
        webbrowser.open(URL)

