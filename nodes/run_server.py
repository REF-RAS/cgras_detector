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

# ros modules
import rospy
# project modules: web and generic

from tools.logging_tools import logger
from detector.model import CONFIG, SystemConfigNames
from detector.run import ApplicationCoordinator

# ----------------------------------------------------------------------
# The main program for running the detector as a web server and a daemon
if __name__ == '__main__':
    rospy.init_node(ApplicationCoordinator.NODE_NAME, anonymous=False)
    the_agent = ApplicationCoordinator()
    DASH_HOST = CONFIG.get(SystemConfigNames.WEB_HOST)
    DASH_PORT = CONFIG.get(SystemConfigNames.WEB_PORT)


