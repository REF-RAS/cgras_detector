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
import sys, os, signal, time, threading, random, yaml, traceback
from datetime import datetime
from time import strftime, localtime
# ros modules
import rospy, message_filters, actionlib, rospkg
from std_msgs.msg import String, Header, Bool, Int8, Float32
# project module: ros
from cgras_messages.srv import QueryTileSamples, QueryTileSamplesRequest, QueryTileSamplesResponse
# project modules: web and generic
from cgras_datatools.logging_tools import logger
import cgras_datatools.hash_tools as hash_tools
from detector.web.dashapp_main import DashApplicationMain
from detector.model import APP_FILE_MANAGER, STATE, CONFIG, SystemStates, DETECT_DAO, AUTOMATED_TASK_EXECUTION, SystemConfigNames, TaskStatusNames, TaskTypes, SampleStatusNames, CALLBACK_MANAGER, CallbackTypes
from detector.model import COORDINATOR_STATE, CoordinatorStates
from detector.task_detection import DetectionTaskModel
from detector.models.detector_error import DetectorException, DetectorFailed, DetectorAborted, DetectorCancelled, DetectorExceptionCodes

# project modules: frame locator
# from detector.tile_reconstruct.model import CapturedImage, TileReconstructInfo
# from detector.tile_reconstruct.locate_tiles_main import TileBBoxLocator

class ApplicationCoordinator(object):
    NODE_NAME = 'cgras_detector'
    def __init__(self):
        logger.info(f'Starting the {ApplicationCoordinator.NODE_NAME} node (pid:{os.getpid()}) (python: {".".join(map(str, sys.version_info[:3]))})')
        # create lock for synchronization
        self.state_lock = threading.RLock()
        # create the stop signal handler
        signal.signal(signal.SIGINT, self.stop)
        rospy.on_shutdown(self.cb_shutdown)
        # model variables
        self.counter = 0
        # operation mode
        AUTOMATED_TASK_EXECUTION.set_value(bool(CONFIG.get(SystemConfigNames.TASK_AUTOMATION_MODE, False)))
        self.suspend_when_capturing_image = CONFIG.get(SystemConfigNames.SUSPEND_WHEN_CAPTURING_IMAGE, False)
        # ros topic names
        self.state_pub_name = CONFIG.get(SystemConfigNames.ROS_DETECTOR_STATE_TOPIC, '/cgras/detector/state')
        self.coordinator_state_sub_name = CONFIG.get(SystemConfigNames.ROS_COORDINATOR_STATE_TOPIC, '/cgras/coordinator/state')  
        # ros topic name for query tile samples
        self.query_tile_samples_srv_topic = CONFIG.get(SystemConfigNames.ROS_QUERY_TILE_SAMPLES_TOPIC)         
        # define the ros topic subscriptions and services
        self.ias_state_sub = rospy.Subscriber(self.coordinator_state_sub_name, Int8, self.cb_coordinator)
        self.state_pub = rospy.Publisher(self.state_pub_name, Int8, queue_size=1, latch=True)
        # register the callbacks (using the dash callback instead of the ros callback due to threading issue during GUI update)
        CALLBACK_MANAGER.set_listener(CallbackTypes.TIMER, self._timer_callback)
        CALLBACK_MANAGER.set_listener(CallbackTypes.TASK_EXECUTE_MODE_CHANGED, self._task_execute_mode_changed_callback)   
        CALLBACK_MANAGER.set_listener(CallbackTypes.PROCESS_TILE_CLICKED, self._manual_task_execute_callback)  
        CALLBACK_MANAGER.set_listener(CallbackTypes.IMPORT_SAMPLE_CLICKED, self._manual_task_execute_callback)  
        CALLBACK_MANAGER.set_listener(CallbackTypes.PROCESS_TILE_TO_CANCEL, self._console_callback) 
        # initialize the state
        STATE.update_state(SystemStates.READY)
        # create the work thread and the lock for execution of the detection task
        self.work_lock = threading.RLock()
        self.work_thread:threading.Thread = None

        # create the dash application
        try:
            self.dash_app_operator = DashApplicationMain()
            self.dash_app_operator.start()
        except (Exception, Warning) as e:
            logger.warning(f'{type(self).__name__} (__init__): {e}')
            traceback.print_exc()
        
    def stop(self, *args, **kwargs):
        logger.warning(f'The {ApplicationCoordinator.NODE_NAME} node (pid:{os.getpid()}) is being stopped')
        state = STATE.get_state()
        if state in [SystemStates.DETECT, SystemStates.WAIT_DETECT]:
            the_detection_task:DetectionTaskModel = STATE.get_var('the_detection_task')
            if the_detection_task:
                the_detection_task.cancel_task()
            if self.work_thread is not None and self.work_thread.is_alive():
                logger.warning(f'The {ApplicationCoordinator.NODE_NAME}  node (pid:{os.getpid()}) is waiting for the detect task thread to abort')
                self.work_thread.join()
        # time.sleep(2)
        sys.exit(0)
        
    def cb_shutdown(self):
        time.sleep(2)
        
    def cb_coordinator(self, msg:Int8): 
        received_coordinator_state_value = msg.data
        # assign coordinator state according to the state value
        if received_coordinator_state_value < 0:
            COORDINATOR_STATE.update(CoordinatorStates.ERROR)
        elif received_coordinator_state_value > 20:
            COORDINATOR_STATE.update(CoordinatorStates.WORKING)
        else:
            COORDINATOR_STATE.update(CoordinatorStates.IDLE)
        # do not attempt to suspend if the config parameter 'suspend_when_capturing_image' is not set
        if not self.suspend_when_capturing_image:
            return
        # test if the state of the coordinator is working, and change to SUSPENDED state and abort current detector task      
        if COORDINATOR_STATE.get_state() not in [CoordinatorStates.IDLE, CoordinatorStates.UNKNOWN, CoordinatorStates.ERROR]:
            try:
                state = STATE.get_state()
                if state in [SystemStates.DETECT, SystemStates.WAIT_DETECT]:
                    the_detection_task:DetectionTaskModel = STATE.get_var('the_detection_task')
                    if the_detection_task:
                        the_detection_task.cancel_task()
                with self.state_lock:
                    # switch the state to SUSPENDED to avoid task execution
                    STATE.update_state(SystemStates.SUSPENDED)
            except:
                logger.warning(f'Unexpected error in cb_coordinator (ignored)')
                # dump the exception to the error log file
                APP_FILE_MANAGER.dump_exc_to_error_log('Exception happens in _detect_work')
                
    def _pub_detector_state(self):
        # logger.info(f'pub {STATE.get_state()}')
        self.state_pub.publish(Int8(STATE.get_state().value))

    #  callback from the GUI console
    def _console_callback(self, event, *args):
        # no mutex lock is needed here
        state = STATE.get()
        if state in [SystemStates.DETECT, SystemStates.WAIT_DETECT]:
            if event == CallbackTypes.PROCESS_TILE_TO_CANCEL:
                logger.warning(f'_console_callback: received CANCEL callback')
                self.cancel_current_task()
                
    def cancel_current_task(self) -> bool:
        with self.state_lock:
            STATE.set_var('exception', DetectorCancelled(DetectorExceptionCodes.CANCELLED_BY_SYSTEM, 'Cancelled by the system'))  
            STATE.update_state(SystemStates.D_CANCELLED, info=STATE.get())
        
        the_detection_task:DetectionTaskModel = STATE.get_var('the_detection_task')
        if the_detection_task:   
            the_detection_task.cancel_task()     
            return True
        else:
            logger.warning(f'Cancel Current Task Received: The task has not started')
            return False
        
    def _manual_task_execute_callback(self, event, *args):
        with self.state_lock:
            state = STATE.get()
            if state in [SystemStates.CLICK_START]:
                if event == CallbackTypes.PROCESS_TILE_CLICKED:
                    STATE.update_state(SystemStates.POLL_DETECT)
                elif event == CallbackTypes.IMPORT_SAMPLE_CLICKED:
                    STATE.update_state(SystemStates.POLL_IMPORT_SAMPLE)
   
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
            # define the steps in the detect process
            detect_process = [
                (the_detection_task.execute_task_reco, 'DETECT: execute_task_reco'),
                (the_detection_task.execute_task_loctile, 'DETECT: execute_task_loctile'),
                (the_detection_task.execute_task_object_detection, 'DETECT: execute_task_object_detection'),
                (the_detection_task.execute_task_record, 'DETECT: execute_task_record'),
            ]
            # execute the steps one by one
            for process_step in detect_process:
                if STATE.is_state(SystemStates.D_CANCELLED):
                    return
                logger.warning(process_step[1])     # print the process description
                process_step[0]()                   # call the function of the process
            
            # update health index (disabled)
            # health_task_model = HealthEvaluateTaskModel()
            # health_task_model.detect_stat_to_cache_tile_health(tile_id_list=[tile_sample_id])                            
            with self.state_lock:
                STATE.update_state(SystemStates.D_SUCCESS)
            
        except DetectorFailed as e: 
            logger.warning(f'Detector FAILED (Reject): {e}')
            STATE.set_var('exception', e)
            with self.state_lock:
                STATE.update_state(SystemStates.D_FAILED)

        except DetectorAborted as e: 
            logger.warning(f'Detector ABORTED: {e}')
            STATE.set_var('exception', e) 
            with self.state_lock:
                STATE.update_state(SystemStates.D_FLAGGED)  

        except DetectorCancelled as e: 
            logger.warning(f'Detector CANCELLED: {e}')
            with self.state_lock:
                STATE.update_state(SystemStates.D_CANCELLED)   

        except:
            # an unexpected error has occurred
            traceback.print_exc(file=sys.stderr)  
            # dump the exception to the error log file
            APP_FILE_MANAGER.dump_exc_to_error_log('Exception happens in _detect_work')
            # switch to manual operation to prevent trapped in an error loop
            AUTOMATED_TASK_EXECUTION.set_value(False)            
            # set error flag to notify the user
            DETECT_DAO.set_error_flag(DetectorExceptionCodes.UNEXPECTED_ERROR.value, "System", '*** Unexpected Error Occurred ***: examine the error log file under the CGRAS Data Folder') 
            # cancel the current task, which will change to D_CANCELLED state
            self.cancel_current_task()
    
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
                    # logger.info(f'Initial Task Automation Mode: {AUTOMATED_TASK_EXECUTION.value}')
                    if AUTOMATED_TASK_EXECUTION.value:
                        STATE.update(SystemStates.AUTO_START)
                    else:
                        STATE.update(SystemStates.CLICK_START)
                
                elif state == SystemStates.AUTO_START:
                    if COORDINATOR_STATE.get_state() in [CoordinatorStates.IDLE, CoordinatorStates.UNKNOWN]:
                        if len(args) > 1:
                            if args[0] % 10 == 1:
                                STATE.update(SystemStates.POLL_IMPORT_SAMPLE)
                            elif args[0] % 2 == 0:
                                STATE.update(SystemStates.POLL_DETECT)
                        else:
                            if random.random() < 0.5:
                                STATE.update(SystemStates.POLL_DETECT)
                            elif random.random() > 0.8:
                                STATE.update(SystemStates.POLL_IMPORT_SAMPLE)
                        
                elif state == SystemStates.CLICK_START:
                    ...
                    # nothing to do inside the event loop, only GUI event will change the state
  
                elif state == SystemStates.POLL_IMPORT_SAMPLE:
                    # check if the ros service is present
                    try:
                        rospy.wait_for_service(self.query_tile_samples_srv_topic, 1.0)
                        query_tile_samples_service = rospy.ServiceProxy(self.query_tile_samples_srv_topic, QueryTileSamples)
                        tile_sample_yaml = query_tile_samples_service(the_query=QueryTileSamplesRequest.NEW_TILE_SAMPLE).data
                        if tile_sample_yaml:
                            tile_sample_data = yaml.load(tile_sample_yaml, Loader=yaml.Loader)
                            is_valid, model = DETECT_DAO.validate_tile_sample_import(tile_sample_data)
                            if is_valid:
                                DETECT_DAO.import_tile_sample_yaml(tile_sample_data)
                        STATE.update_state(SystemStates.READY)
                    except Exception as e:
                        STATE.update_state(SystemStates.READY)
                    
                # elif state == SystemStates.POLL_IMPORT_SAMPLE:
                #     # check if import tile sample is enabled
                #     enable_import_new_samples = PERSISTENT_STORE_DAO.get_config_value(PersistentStoreDAO.TILE_IMPORT_ENABLED, default=False)
                #     if not enable_import_new_samples:
                #         STATE.update_state(SystemStates.READY)
                #         return
                #     # query for new un-exported tile samples 
                #     exportable_tile_samples_list = IMPORT_SAMPLE_DAO.query_to_export_sample_as_list_tuples()
                #     if exportable_tile_samples_list is None or len(exportable_tile_samples_list) == 0:
                #         STATE.update_state(SystemStates.READY)
                #     else:
                #         STATE.set_var('exportable_tile_samples_list', exportable_tile_samples_list)
                #         STATE.update_state(SystemStates.IMPORT_SAMPLE)
                        
                # elif state == SystemStates.IMPORT_SAMPLE:
                #     exportable_tile_samples_list = STATE.get_var('exportable_tile_samples_list')
                #     self.process_exportable_tile_samples(exportable_tile_samples_list)
                #     STATE.update_state(SystemStates.READY)
                    
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
                    tile_sample_id = STATE.get_var('tile_sample_id')
                    the_detection_task:DetectionTaskModel = STATE.get_var('the_detection_task')
                    if the_detection_task:
                        DETECT_DAO.update_tile_sample_status(tile_sample_id, SampleStatusNames.DONE.value)
                        DETECT_DAO.add_task_record(TaskTypes.DETECT_CORALS.value, tile_sample_id, 
                            the_detection_task.get_start_time_iso8601(), int(the_detection_task.get_time_lapsed()), TaskStatusNames.SUCCESS.value, None)                      
                        
                    STATE.del_var('tile_sample_id')
                    STATE.del_var('the_detection_task')
                    STATE.update_state(SystemStates.READY)   

                elif state in [SystemStates.D_FAILED, SystemStates.D_FLAGGED]:
                    tile_sample_id = STATE.get_var('tile_sample_id')
                    the_detection_task = STATE.get_var('the_detection_task')
                    exception:DetectorException = STATE.get_var('exception')
                    if the_detection_task:
                        current_stage = the_detection_task.get_progress().get_current_stage()
                        start_time = the_detection_task.get_start_time_iso8601()
                        time_lapsed = int(the_detection_task.get_time_lapsed())
                    else:
                        current_stage = 'INIT'
                        start_time = strftime('%Y-%m-%d %H:%M:%S', localtime(time.time()))
                        time_lapsed = 0
                        
                    if state == SystemStates.D_FAILED:
                        DETECT_DAO.update_tile_sample_status(tile_sample_id, SampleStatusNames.REJECTED.value, exception.get_remarks())
                        DETECT_DAO.add_task_record(TaskTypes.DETECT_CORALS.value, tile_sample_id, 
                            start_time, time_lapsed, TaskStatusNames.FAIL.value, f'{DetectorExceptionCodes(exception.get_code()).name}')
                        error_remarks = f'Failed at {current_stage}: {exception.get_remarks()}'
                        DETECT_DAO.set_error_flag(exception.get_code().value, tile_sample_id, error_remarks)
                    else:
                        DETECT_DAO.update_tile_sample_status(tile_sample_id, SampleStatusNames.FLAGGED.value, exception.get_remarks())
                        DETECT_DAO.add_task_record(TaskTypes.DETECT_CORALS.value, tile_sample_id, 
                            start_time, time_lapsed, TaskStatusNames.RESOLVABLE_FAIL.value, f'{DetectorExceptionCodes(exception.get_code()).name}')
                        error_remarks = f'Stopped at {current_stage}: {exception.get_remarks()}'
                        DETECT_DAO.set_error_flag(exception.get_code().value, tile_sample_id, error_remarks)                        

                    STATE.del_var('tile_sample_id')
                    STATE.del_var('the_detection_task')
                    STATE.del_var('exception')
                    STATE.update_state(SystemStates.READY)       
                    
                elif state == SystemStates.D_CANCELLED:
                    STATE.del_var('tile_sample_id')
                    STATE.del_var('the_detection_task')
                    STATE.del_var('exception')
                    STATE.update_state(SystemStates.READY)                       
                    
                elif state == SystemStates.SUSPENDED:
                    if COORDINATOR_STATE.get_state() in [CoordinatorStates.IDLE, CoordinatorStates.UNKNOWN]:
                        STATE.update_state(SystemStates.READY)                                                     

                # check if connection to other component is lost
                if not COORDINATOR_STATE.is_state(CoordinatorStates.UNKNOWN) and COORDINATOR_STATE.time_lapsed_since_update() > CONFIG.get(SystemConfigNames.CONNECTION_TIMEOUT, 30):
                    COORDINATOR_STATE.update(CoordinatorStates.UNKNOWN)

            except DetectorFailed as e: 
                logger.warning(f'Detector FAILED (Reject): {e}')
                STATE.set_var('exception', e)
                STATE.update_state(SystemStates.D_FAILED)

            except DetectorAborted as e: 
                logger.warning(f'Detector ABORTED: {e}')
                STATE.set_var('exception', e) 
                STATE.update_state(SystemStates.D_FLAGGED)  
                
            except DetectorCancelled as e: 
                logger.warning(f'Detector ABORTED: {e}')
                STATE.set_var('exception', e) 
                STATE.update_state(SystemStates.D_CANCELLED)                

            except:
                # an unexpected error has occurred
                traceback.print_exc(file=sys.stderr)  
                # dump the exception to the error log file
                APP_FILE_MANAGER.dump_exc_to_error_log('Exception happened in _timer_callback')
                # switch to manual operation to prevent trapped in an error loop
                AUTOMATED_TASK_EXECUTION.set_value(False)            
                # set error flag to notify the user
                DETECT_DAO.set_error_flag(DetectorExceptionCodes.UNEXPECTED_ERROR.value, "System", '*** Unexpected Error Occurred ***: examine the error log file under the CGRAS Data Folder') 
                # switch to READY
                STATE.update_state(SystemStates.READY)
            
    # def process_exportable_tile_samples(self, exportable_tile_samples_list:list):
    #     for exportable_tile_sample in exportable_tile_samples_list:
    #         tile_id, batch_id = exportable_tile_sample
    #         tile_sample_data = IMPORT_SAMPLE_DAO.export_tile_sample_as_dict(tile_id=tile_id, batch_id=batch_id, auto_update_export_time=True)
    #         is_valid, model = DETECT_DAO.validate_tile_sample_import(tile_sample_data)
    #         if not is_valid:
    #             logger.warning(f'process_exportable_tile_samples: Invalid tile sample ({tile_id, batch_id}) and is skipped\n')
    #             continue
    #         if not DETECT_DAO.import_tile_sample_yaml(tile_sample_data):
    #             logger.warning(f'process_exportable_tile_samples: Unable to import tile sample ({tile_id, batch_id})')
        
# ---------------------------------------------------------
# The main program for running the detector
if __name__ == '__main__':
    rospy.init_node(ApplicationCoordinator.NODE_NAME, anonymous=False)
    the_agent = ApplicationCoordinator()
    DASH_HOST = CONFIG.get(SystemConfigNames.WEB_HOST)
    DASH_PORT = CONFIG.get(SystemConfigNames.WEB_PORT)
    # URL = f'http://{DASH_HOST}:{DASH_PORT}'
    # webbrowser.open(URL)

