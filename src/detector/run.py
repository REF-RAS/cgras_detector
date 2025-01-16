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
from cgras_datatools.logging_tools import logger
import cgras_datatools.hash_tools as hash_tools
from detector.web.dashapp_main import DashApplicationMain
from detector.model import APP_FILE_MANAGER, STATE, CONFIG, SystemStates, DETECT_DAO, AUTOMATED_TASK_EXECUTION, SystemConfigNames, TaskStatusNames, TaskTypes, SampleStatusNames, CALLBACK_MANAGER, CallbackTypes
from detector.model import COORDINATOR_STATE, CoordinatorStates
from detector.task_detection import DetectionTaskModel
from detector.models.detector_error import DetectorError, DetectorRejectError, DetectorAbortError, DetectorErrorCodes

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
        # operation mode
        AUTOMATED_TASK_EXECUTION.set_value(bool(CONFIG.get(SystemConfigNames.TASK_AUTOMATION_MODE, False)))

        # ros topic names
        self.state_pub_name = CONFIG.get(SystemConfigNames.ROS_DETECTOR_STATE_TOPIC, '/cgras/detector/state')
        self.coordinator_state_sub_name = CONFIG.get(SystemConfigNames.ROS_COORDINATOR_STATE_TOPIC, '/cgras/coordinator/state')  
        # define the ros topic subscriptions and services
        self.ias_state_sub = rospy.Subscriber(self.coordinator_state_sub_name, Int8, self.cb_coordinator)
        self.state_pub = rospy.Publisher(self.state_pub_name, Int8, queue_size=1, latch=True)
        # register the callbacks (using the dash callback instead of the ros callback due to threading issue during GUI update)
        CALLBACK_MANAGER.set_listener(CallbackTypes.TIMER, self._timer_callback)
        CALLBACK_MANAGER.set_listener(CallbackTypes.TASK_EXECUTE_MODE_CHANGED, self._task_execute_mode_changed_callback)   
        CALLBACK_MANAGER.set_listener(CallbackTypes.PROCESS_TILE_CLICKED, self._manual_task_execute_callback)  
        CALLBACK_MANAGER.set_listener(CallbackTypes.PROCESS_TILE_TO_ABORT, self._console_callback) 
        # initialize the state
        STATE.update_state(SystemStates.READY)
        # create the work thread and the lock
        self.work_lock = threading.RLock()
        self.work_thread:threading.Thread = None
        # self.work_thread = threading.Thread(target=self._work_thread_loop)
        # start the work thread
        # self.work_thread.start()

        # create the dash application
        try:
            logger.info(f'Starting Dash Server')
            self.dash_app_operator = DashApplicationMain()
            self.dash_app_operator.start()
        except (Exception, Warning) as e:
            logger.warning(f'{type(self).__name__} (__init__): {e}')
            traceback.print_exc()
        
    def stop(self, *args, **kwargs):
        logger.warning(f'The application (pid:{os.getpid()}) is being stopped')
        state = STATE.get_state()
        if state in [SystemStates.DETECT, SystemStates.WAIT_DETECT]:
            the_detection_task:DetectionTaskModel = STATE.get_var('the_detection_task')
            if the_detection_task:
                the_detection_task.abort_task()
            if self.work_thread is not None and self.work_thread.is_alive():
                logger.warning(f'The application (pid:{os.getpid()}) is waiting for the detect task thread to abort')
                self.work_thread.join()
        # time.sleep(2)
        sys.exit(0)
        
    def cb_shutdown(self):
        time.sleep(2)
        
    def cb_coordinator(self, msg:Int8): 
        received_coordinator_state_value = msg.data
        if received_coordinator_state_value < 0:
            COORDINATOR_STATE.update(CoordinatorStates.ERROR)
        elif received_coordinator_state_value > 20:
            COORDINATOR_STATE.update(CoordinatorStates.UNSAFE)
        else:
            COORDINATOR_STATE.update(CoordinatorStates.SAFE)
                
        with self.state_lock:
            if COORDINATOR_STATE.get_state() not in [CoordinatorStates.SAFE, CoordinatorStates.UNKNOWN]:
                state = STATE.get_state()
                if state in [SystemStates.DETECT, SystemStates.WAIT_DETECT]:
                    the_detection_task:DetectionTaskModel = STATE.get_var('the_detection_task')
                    if the_detection_task:
                        the_detection_task.abort_task()
                # switch the state to SUSPENDED to avoid task execution
                STATE.update_state(SystemStates.SUSPENDED)
                

    def _pub_detector_state(self):
        # logger.info(f'pub {STATE.get_state()}')
        self.state_pub.publish(Int8(STATE.get_state().value))

    #  callback from the GUI console
    def _console_callback(self, event, *args):
        # no mutex lock is needed here
        state = STATE.get()
        if state in [SystemStates.DETECT, SystemStates.WAIT_DETECT]:
            if event == CallbackTypes.PROCESS_TILE_TO_ABORT:
                logger.warning(f'_console_callback: received ABORT callback')
                self.abort_current_task(sample_state=SampleStatusNames.ABORTED)
                
    def abort_current_task(self, sample_state=SampleStatusNames.ABORTED) -> bool:
        STATE.set_var('exception', DetectorAbortError(DetectorErrorCodes.ABORTED_BY_SYSTEM, 'Received the abort command'))          
        STATE.update_state(SystemStates.D_ABORTED, info=sample_state)
        the_detection_task:DetectionTaskModel = STATE.get_var('the_detection_task')
        if the_detection_task:   
            the_detection_task.abort_task()        
            return True
        else:
            logger.warning(f'Abort Current Task Received: No current task')
            return False
        
    def _manual_task_execute_callback(self, event, *args):
        with self.state_lock:
            state = STATE.get()
            if state in [SystemStates.CLICK_START]:
                if event == CallbackTypes.PROCESS_TILE_CLICKED:
                    STATE.update_state(SystemStates.POLL_DETECT)
   
    def _task_execute_mode_changed_callback(self, event, *args):
        AUTOMATED_TASK_EXECUTION.set_value(bool(args[0]))
        with self.state_lock:
            state = STATE.get()
            # if STATE.time_lapsed_since_update() < 3.0:  # demo state change with an arbitrary 3 second period
            #     return
            # the state transition machine 
            if state in [SystemStates.AUTO_START, SystemStates.POLL_DETECT, SystemStates.CLICK_START]:
                STATE.update_state(SystemStates.READY)
    
    def _detect_work(self, the_detection_task:DetectionTaskModel):
        try:
            # initialization
            if STATE.is_state(SystemStates.D_ABORTED):
                return
            # reconstruction                           
            logger.warning(f'DETECT: execute_task_reco')
            the_detection_task.execute_task_reco()
            if STATE.is_state(SystemStates.D_ABORTED):
                return
            # locate tile frames
            logger.warning(f'DETECT: execute_task_loctile')
            the_detection_task.execute_task_loctile()
            if STATE.is_state(SystemStates.D_ABORTED):
                return
            # detect objects
            logger.warning(f'DETECT: execute_task_object_detection')
            the_detection_task.execute_task_object_detection()
            if STATE.is_state(SystemStates.D_ABORTED):
                return
            # collect and record statistics
            the_detection_task.execute_task_record()
            if STATE.is_state(SystemStates.D_ABORTED):
                return
            # update health index (disabled)
            # health_task_model = HealthEvaluateTaskModel()
            # health_task_model.detect_stat_to_cache_tile_health(tile_id_list=[tile_sample_id])                            
            with self.state_lock:
                STATE.update_state(SystemStates.D_SUCCESS)
            
        except DetectorRejectError as e: 
            logger.warning(f'Detector FAILED (Reject): {e}')
            STATE.set_var('exception', e)
            with self.state_lock:
                STATE.update_state(SystemStates.D_FAILED)

        except DetectorAbortError as e: 
            logger.warning(f'Detector ABORTED: {e}')
            STATE.set_var('exception', e) 
            with self.state_lock:
                STATE.update_state(SystemStates.D_ABORTED)  
            
        except OSError as e:
            logger.warning(f'OS Error: {e}')
            STATE.set_var('exception', e) 
            with self.state_lock:
                STATE.update_state(SystemStates.D_ABORTED)       
    
    def _timer_callback(self, event, *args):
        self._pub_detector_state()
        with self.state_lock:
            try:
                state = STATE.get()
                # check lost connection to the capturer
                if COORDINATOR_STATE.time_lapsed_since_update() > CONFIG.get(SystemConfigNames.CONNECTION_TIMEOUT, 60):
                    COORDINATOR_STATE.update(CoordinatorStates.UNKNOWN)
                
                if state == SystemStates.READY:
                    STATE.del_var('tile_sample_id')
                    STATE.del_var('the_detection_task')
                    
                    logger.info(f'Initial Task Automation Mode: {AUTOMATED_TASK_EXECUTION.value}')
                    if AUTOMATED_TASK_EXECUTION.value:
                        STATE.update(SystemStates.AUTO_START)
                    else:
                        STATE.update(SystemStates.CLICK_START)
                
                elif state == SystemStates.AUTO_START:

                    if COORDINATOR_STATE.get_state() in [CoordinatorStates.SAFE, CoordinatorStates.UNKNOWN]:
                        STATE.update(SystemStates.POLL_DETECT)
                        
                elif state == SystemStates.CLICK_START:
                    ...
                    # nothing to do inside the event loop, only GUI event will change the state
                    
                elif state == SystemStates.POLL_DETECT:

                    # query for a tile sample pending processig 
                    # if the request is DETECT, query the next pending tile sample
                    self.next_tile_sample = DETECT_DAO.query_next_pending_tile_sample()
                    if self.next_tile_sample is not None:
                        STATE.set_var('tile_sample_id', self.next_tile_sample['id'])
                        STATE.update_state(SystemStates.DETECT)
                    else:
                        STATE.update_state(SystemStates.READY)

                elif state == SystemStates.DETECT:          
                    tile_sample_id = STATE.get_var('tile_sample_id')
                    the_detection_task = DetectionTaskModel(tile_sample_id)
                    STATE.set_var('the_detection_task', the_detection_task)         
                    self.work_thread = threading.Thread(target=self._detect_work, args=[the_detection_task])
                    self.work_thread.start()
                    STATE.update_state(SystemStates.WAIT_DETECT)
                        
                elif state == SystemStates.WAIT_DETECT:
                    ...
                    
                elif state == SystemStates.D_SUCCESS:
                    the_detection_task:DetectionTaskModel = STATE.get_var('the_detection_task')
                    if the_detection_task:
                        tile_sample_id = the_detection_task.get_tile_sample_id()
                        DETECT_DAO.update_tile_sample_status(tile_sample_id, SampleStatusNames.DONE.value)
                        DETECT_DAO.add_task_record(TaskTypes.DETECT_CORALS.value, the_detection_task.get_tile_sample_id(), 
                            the_detection_task.get_start_time_iso8601(), int(the_detection_task.get_time_lapsed()), TaskStatusNames.SUCCESS.value, None)
                    STATE.del_var('tile_sample_id')
                    STATE.del_var('the_detection_task')
                    STATE.update_state(SystemStates.READY)   

                elif state == SystemStates.D_FAILED:
                    traceback.print_exc()
                    the_detection_task = STATE.get_var('the_detection_task')
                    exception:DetectorError = STATE.get_var('exception')
                    if the_detection_task and exception:
                        tile_sample_id = the_detection_task.get_tile_sample_id()
                        sub_progress_model = the_detection_task.get_progress()
                        current_stage = sub_progress_model.get_current_stage()
                        
                        DETECT_DAO.update_tile_sample_status(tile_sample_id, SampleStatusNames.REJECTED.value, exception.get_remarks())
                        DETECT_DAO.add_task_record(TaskTypes.DETECT_CORALS.value, tile_sample_id, 
                            the_detection_task.get_start_time_iso8601(), int(the_detection_task.get_time_lapsed()), TaskStatusNames.FAILED.value, f'{DetectorErrorCodes(exception.get_code()).name}')
                        error_remarks = f'{tile_sample_id} Failed at {current_stage} ({DetectorErrorCodes(exception.get_code()).name}): {exception.get_remarks()}'
                        DETECT_DAO.set_error_flag(exception.get_code().value, error_remarks)
                    STATE.del_var('tile_sample_id')
                    STATE.del_var('the_detection_task')
                    STATE.del_var('exception')
                    STATE.update_state(SystemStates.READY)    
                        
                elif state == SystemStates.D_ABORTED:
                    the_detection_task = STATE.get_var('the_detection_task')
                    exception:DetectorError = STATE.get_var('exception')
                    if the_detection_task:
                        tile_sample_id = the_detection_task.get_tile_sample_id()
                        sub_progress_model = the_detection_task.get_progress()
                        current_stage = sub_progress_model.get_current_stage()
                        if exception is None:
                            error_remarks = f'{tile_sample_id} Aborted at {current_stage} ({DetectorErrorCodes(exception.get_code()).name}): Received the abort command'
                            task_remarks = DetectorErrorCodes.ABORTED_BY_SYSTEM.name
                        elif type(exception) == OSError:
                            error_remarks = f'{tile_sample_id} Aborted at {current_stage} ({DetectorErrorCodes.FILE_IO_ERROR.name}): {exception}'
                            task_remarks = DetectorErrorCodes.FILE_IO_ERROR.name
                        else:
                            error_remarks = f'{tile_sample_id} Aborted at {current_stage} ({DetectorErrorCodes(exception.get_code()).name}): {exception.get_remarks()}'
                            task_remarks = DetectorErrorCodes.ABORTED_BY_SYSTEM.name
                            DETECT_DAO.set_error_flag(exception.get_code().value, error_remarks) 
                            
                        DETECT_DAO.update_tile_sample_status(tile_sample_id, SampleStatusNames.ABORTED.value)
                        DETECT_DAO.add_task_record(TaskTypes.DETECT_CORALS.value, tile_sample_id, 
                            the_detection_task.get_start_time_iso8601(), int(the_detection_task.get_time_lapsed()), TaskStatusNames.ABORTED.value, task_remarks)                              
                    
                    STATE.del_var('tile_sample_id')
                    STATE.del_var('the_detection_task')
                    STATE.del_var('exception')
                    STATE.update_state(SystemStates.READY)    
                
                elif state == SystemStates.SUSPENDED:
                    time.sleep(1.0)
                    if COORDINATOR_STATE.get_state() in [CoordinatorStates.SAFE, CoordinatorStates.UNKNOWN]:
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

