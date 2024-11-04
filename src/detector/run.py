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
import sys, os, signal, time, threading, webbrowser, subprocess, traceback
from datetime import datetime
# ros modules
import rospy, message_filters, actionlib, rospkg
from std_msgs.msg import String, Header, Bool, Int8, Float32
# project modules: web and generic
from tools.logging_tools import logger
import tools.hash_tools as hash_tools
from detector.web.dashapp_main import DashApplicationMain
from detector.model import APP_FILE_MANAGER, STATE, CONFIG, SystemStates, DETECT_DAO, PERSISTENT_STORE_DAO, SystemConfigNames, StatusNames, TaskTypes, CALLBACK_MANAGER, CallbackTypes
from detector.model import CAPTURER_STATE, CapturerStates
from detector.task_detection import DetectionTaskModel
from detector.task_health import HealthEvaluateTaskModel
from detector.models.detector_error import DetectorError, DetectorErrorCodes

# project modules: frame locator
# from detector.tile_reconstruct.model import CapturedImage, TileReconstructInfo
# from detector.tile_reconstruct.locate_tiles_main import TileBBoxLocator

class ApplicationCoordinator(object):
    NODE_NAME = 'cgras_detect_viewer'
    def __init__(self):
        logger.info(f'The {ApplicationCoordinator.NODE_NAME} application (pid:{os.getpid()})')
        # create lock for synchronization
        self.state_lock = threading.RLock()
        # create the stop signal handler
        signal.signal(signal.SIGINT, self.stop)
        rospy.on_shutdown(self.cb_shutdown)
        # model variables
        self.counter = 0
        # ros topic names
        self.state_pub_name = '/cgras/detector/state'
        
        self.ias_state_sub_name = '/cgras/capturer/state'   
        # define the ros topic subscriptions and services
        self.robot_state_sub = rospy.Subscriber(self.ias_state_sub_name, Int8, self.cb_capturer)
        self.state_pub = rospy.Publisher(self.state_pub_name, Int8, queue_size=1, latch=True)
        # register the callbacks (using the dash callback instead of the ros callback due to threading issue during GUI update)
        CALLBACK_MANAGER.set_listener(CallbackTypes.TIMER, self._timer_callback)
        CALLBACK_MANAGER.set_listener(CallbackTypes.TASK_EXECUTE_MODE_CHANGED, self._task_execute_mode_changed_callback)   
        CALLBACK_MANAGER.set_listener(CallbackTypes.PROCESS_TILE_CLICKED, self._manual_task_execute_callback)  
        CALLBACK_MANAGER.set_listener(CallbackTypes.PROCESS_TILE_TO_ABORT, self._console_callback) 
        # initialize the state
        STATE.update_state(SystemStates.READY)
        # create the work thread and the lock
        self.work_to_stop = False
        self.work_lock = threading.RLock()
        self.work_thread = threading.Thread(target=self._work_thread_loop)
        # start the work thread
        self.work_thread.start()

        # create the dash application
        try:
            logger.info(f'Starting Dash Server')
            self.dash_app_operator = DashApplicationMain()
            self.dash_app_operator.start()
        except (Exception, Warning) as e:
            logger.warning(f'{type(self).__name__} (__init__): {e}')
            traceback.print_exc()
        
    def stop(self, *args, **kwargs):
        logger.info(f'The application (pid:{os.getpid()}) is being stopped')
        self.work_to_stop = True
        time.sleep(2)
        sys.exit(0)

    def cb_shutdown(self):
        self.work_to_stop = True
        time.sleep(2)
        
    def cb_capturer(self, msg:Int8):
        CAPTURER_STATE.update(CapturerStates(msg.data))
        
    def pub_detector_state(self):
        logger.info(f'pub {STATE.get_state()}')
        self.state_pub.publish(Int8(STATE.get_state()))

    #  callback from the GUI console
    def _console_callback(self, event, *args):
        with self.state_lock:
            state = STATE.get()
            if state in [SystemStates.D_INIT, SystemStates.D_RECO, SystemStates.D_LOCTILE, SystemStates.D_OBJECT, SystemStates.D_COLLECT_STAT]:
                if event == CallbackTypes.PROCESS_TILE_TO_ABORT:
                    the_detection_task:DetectionTaskModel = STATE.get_var('the_detection_task')
                    logger.warning(f'ABORT CALLBACK: {the_detection_task}')
                    if the_detection_task:
                        STATE.update_state(SystemStates.D_ABORTED)
                        the_detection_task.abort_task()
                return
                        

    def _timer_callback(self, event, *args):
        with self.state_lock:
            state = STATE.get()
            # if STATE.time_lapsed_since_update() < 3.0:  # demo state change with an arbitrary 3 second period
            #     return
            # the state transition machine 
            if state == SystemStates.READY:
                ...

    def _manual_task_execute_callback(self, event, *args):
        with self.state_lock:
            state = STATE.get()
            if state in [SystemStates.CLICK_START]:
                if event == CallbackTypes.PROCESS_TILE_CLICKED:
                    STATE.update_state(SystemStates.POLL_DETECT)
   
    def _task_execute_mode_changed_callback(self, event, *args):
        logger.warning(f'_task_execute_mode_changed_callback: {event}')
        with self.state_lock:
            state = STATE.get()
            # if STATE.time_lapsed_since_update() < 3.0:  # demo state change with an arbitrary 3 second period
            #     return
            # the state transition machine 
            if state in [SystemStates.AUTO_START, SystemStates.CLICK_START]:
                STATE.update_state(SystemStates.READY)
            
                    
    def _work_thread_loop(self):
        while not self.work_to_stop:
            self.pub_detector_state()
            time.sleep(0.1)
            with self.state_lock:
                try:
                    state = STATE.get()
                    # check lost connection to the capturer
                    if CAPTURER_STATE.time_lapsed_since_update() > CONFIG.get(SystemConfigNames.CONNECTION_TIMEOUT, 60):
                        CAPTURER_STATE.update(CapturerStates.UNKNOWN)
                    
                    if state == SystemStates.READY:
                        STATE.del_var('tile_sample_id')
                        STATE.del_var('the_detection_task')
                        
                        task_execute_mode = PERSISTENT_STORE_DAO.get_task_execute_mode(PERSISTENT_STORE_DAO.AUTO_EXECUTE_OFF)
                        if task_execute_mode == PERSISTENT_STORE_DAO.AUTO_EXECUTE_ON:
                            STATE.update(SystemStates.AUTO_START)
                        else:
                            STATE.update(SystemStates.CLICK_START)
                    
                    elif state == SystemStates.AUTO_START:
                        time.sleep(1.0)
                        if CAPTURER_STATE.get_state() in [CapturerStates.IDLE, CapturerStates.UNKNOWN]:
                            STATE.update(SystemStates.POLL_DETECT)
                            
                    elif state == SystemStates.CLICK_START:
                        time.sleep(1.0)
                        # nothing to do inside the event loop, only GUI event will change the state
                        
                    elif state == SystemStates.POLL_DETECT:
                        time.sleep(1.0)
                        # query for a tile sample pending processig 
                        # if the request is DETECT, query the next pending tile sample
                        self.next_tile_sample = DETECT_DAO.query_next_pending_tile_sample()
                        # make sure the image acquisition system is idle or not alive
                        if self.next_tile_sample is not None and \
                                CAPTURER_STATE.get_state() in [CapturerStates.IDLE, CapturerStates.UNKNOWN]:
                            try:
                                STATE.set_var('tile_sample_id', self.next_tile_sample['id'])
                                STATE.update_state(SystemStates.D_INIT)
                            except Exception as e:
                                logger.error(e)
                                DETECT_DAO.update_tile_sample_status(tile_sample_id, StatusNames.FAILED.value)
                                STATE.update_state(SystemStates.READY)
                        else:
                            STATE.update_state(SystemStates.READY)

                    elif state == SystemStates.D_INIT:             
                        time.sleep(1.0)
                        try:
                            tile_sample_id = STATE.get_var('tile_sample_id')
                            the_detection_task = DetectionTaskModel(tile_sample_id)
                            STATE.set_var('the_detection_task', the_detection_task)
                            STATE.update_state(SystemStates.D_RECO)
                        except DetectorError as e:
                            STATE.set_var('exception', e)
                            STATE.update_state(SystemStates.D_FAILED) 
                      
                    elif state == SystemStates.D_RECO:             
                        time.sleep(1.0)
                        try:
                            the_detection_task = STATE.get_var('the_detection_task')
                            the_detection_task.execute_task_reco()
                            if STATE.is_state(SystemStates.D_ABORTED):
                                continue
                            STATE.update_state(SystemStates.D_LOCTILE)
                        except DetectorError as e:
                            STATE.set_var('exception', e)
                            STATE.update_state(SystemStates.D_FAILED) 

                    elif state == SystemStates.D_LOCTILE:             
                        time.sleep(1.0)
                        try:
                            the_detection_task = STATE.get_var('the_detection_task')
                            the_detection_task.execute_task_loctile()
                            if STATE.is_state(SystemStates.D_ABORTED):
                                continue
                            STATE.update_state(SystemStates.D_OBJECT)
                        except DetectorError as e:
                            STATE.set_var('exception', e)
                            STATE.update_state(SystemStates.D_FAILED) 
                            
                    elif state == SystemStates.D_OBJECT:             
                        time.sleep(1.0)
                        try:
                            the_detection_task = STATE.get_var('the_detection_task')
                            the_detection_task.execute_task_object_detection()
                            if STATE.is_state(SystemStates.D_ABORTED):
                                continue
                            STATE.update_state(SystemStates.D_COLLECT_STAT)
                        except DetectorError as e:
                            STATE.set_var('exception', e)
                            STATE.update_state(SystemStates.D_FAILED) 

                    elif state == SystemStates.D_COLLECT_STAT:             
                        time.sleep(1.0)
                        try:
                            the_detection_task = STATE.get_var('the_detection_task')
                            the_detection_task.execute_task_record()
                            if STATE.is_state(SystemStates.D_ABORTED):
                                continue
                            STATE.update_state(SystemStates.D_UPDATE_HEALTH_INDEX)
                        except DetectorError as e:
                            STATE.set_var('exception', e)
                            STATE.update_state(SystemStates.D_FAILED) 
                                                                
                    elif state == SystemStates.D_UPDATE_HEALTH_INDEX:             
                        time.sleep(1.0)
                        tile_sample_id = STATE.get_var('tile_sample_id')
                        try:
                            health_task_model = HealthEvaluateTaskModel()
                            health_task_model.detect_stat_to_cache_tile_health(tile_id_list=[tile_sample_id])
                            STATE.update_state(SystemStates.D_SUCCESS)  
                        except Exception as e:
                            STATE.update_state(SystemStates.D_FAILED) 
                        
                    elif state == SystemStates.D_SUCCESS:
                        the_detection_task:DetectionTaskModel = STATE.get_var('the_detection_task')
                        if the_detection_task:
                            DETECT_DAO.update_tile_sample_status(tile_sample_id, StatusNames.SUCCESS.value)
                            DETECT_DAO.add_task_record(TaskTypes.DETECT_CORALS.value, the_detection_task.get_tile_sample_id(), 
                                the_detection_task.get_start_time_iso8601(), int(the_detection_task.get_time_lapsed()), StatusNames.SUCCESS.value, None)
                        STATE.update_state(SystemStates.READY)   

                    elif state == SystemStates.D_FAILED:
                        traceback.print_exc()
                        the_detection_task = STATE.get_var('the_detection_task')
                        exception:DetectorError = STATE.get_var('exception')
                        if the_detection_task and exception:
                            previous_state = STATE.get_previous_state()
                            DETECT_DAO.update_tile_sample_status(tile_sample_id, StatusNames.FAILED.value, exception.get_remarks())
                            DETECT_DAO.add_task_record(TaskTypes.DETECT_CORALS.value, the_detection_task.get_tile_sample_id(), 
                                the_detection_task.get_start_time_iso8601(), int(the_detection_task.get_time_lapsed()), StatusNames.FAILED.value, f'Failed at {previous_state.name}')
                            DETECT_DAO.set_error_flag(exception.get_id(), exception.get_remarks())
                        STATE.update_state(SystemStates.READY)    
                          
                    elif state == SystemStates.D_ABORTED:
                        time.sleep(2.0)
                        the_detection_task = STATE.get_var('the_detection_task')
                        if the_detection_task:
                            previous_state = STATE.get_previous_state()
                            DETECT_DAO.update_tile_sample_status(tile_sample_id, StatusNames.ABORTED.value)
                            DETECT_DAO.add_task_record(TaskTypes.DETECT_CORALS.value, the_detection_task.get_tile_sample_id(), 
                                the_detection_task.get_start_time_iso8601(), int(the_detection_task.get_time_lapsed()), StatusNames.ABORTED.value, f'Aborted at {previous_state.name}')     
                                                   
                        STATE.update_state(SystemStates.READY)                                                           
                        
                except Exception as e:
                    traceback.print_exc()
                    logger.error(e)
                
                


# ---------------------------------------------------------
# The main program for running the detector
if __name__ == '__main__':
    rospy.init_node(ApplicationCoordinator.NODE_NAME, anonymous=False)
    the_agent = ApplicationCoordinator()
    DASH_HOST = CONFIG.get(SystemConfigNames.WEB_HOST)
    DASH_PORT = CONFIG.get(SystemConfigNames.WEB_PORT)
    # URL = f'http://{DASH_HOST}:{DASH_PORT}'
    # webbrowser.open(URL)

