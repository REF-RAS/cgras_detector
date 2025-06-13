# CGRAS 2025: Coral Counting and Visualization System

The **Coral Counting and Visualization System (CCVS)** is one of the two systems of the CGRAS 2025 platform. It is designed to monitor the coral recruitment process in tanks with acquaculture tiles. It achieves the objective based on visual analytics on images captured of the tiles, which involves the application of deep-learning based object detection models, the post-processing of identified objects, and the presentation of the findings. CCVS provides a web interface for users to monitor and control the visual analytics process, to manage the image samples, and to visualize the trend and distribution of corals of a tile. 

At the upstream of the CGRAS 2025 finds the **Image Acquisition Coorindation System (IACS)**, which is designed to autonomously capture images of acquaculture tiles in a operation zone called the **CGRAS Arena**. 

## Basic Operation

The CCVS can operate in tendem with the IACS, from which the input images of tile samples are retrieved through the ROS middleware. It can also operate in a stand-alone manner, in which case the input images can be imported through the user interface or a RESTful API.

The input images are organized as tile samples. A tile sample is a set of images captured of a tile. Depending on the image capturing device, multiple images may be required to capture all areas of a tile at a required resolution. The images are expected to arrange in a grid-like manner. A tile sample is associated with a particular tile, identified by the __tile_id__, and the capture time, identified by the __batch_id__.

The operation of the CCVS is centred around management and processing of tile samples.  The following illustrates the generation and the associated data of a tile sample.

![Tile Sample](docs/images/TileSampleInfo.png)

### Job Monitor and Control with the Application Monitor

The following shows the first screen - the Application Monitor, which is structured into four areas.

![Dashboard Screen](docs/images/DashboardScreen.png)

The top-left corner is the __job control__ panel. CCVS has defined two job types: (1) coral detection of a tile sample and (2) retrieval of a tile sample from the IACS. In the __Automated Execution Mode__, the system autonomously polls the tile sample manager for samples pending for coral detection. It also autonomously polls the IACS for new tile samples. In the __Manual Execution Mode__, the buttons in the panel is enabled for users to execute the job one at a time. 

The remainder of the top panel includes tables showing the statistics of tile sample processing, the status of the two CGRAS systems and the computing resources of the host computer.

The job of coral detection of a tile sample involves several computation intensive steps:
- Logically stitch the images of a tile sample together into the original visual appearance of the tile.
- Reduce visual distortion and locate the tile region from other structural elements such as tile holders and spacers.
- Split the images up into smaller parts for coral detection by one or more object detector models.
- Refine the detected coral objects, which include duplication removal and classification resolution, and store away the findings.

The __job execution__ panel in the middle displays the progress when a coral detection job is being executed. It also displays the ID of the tile sample being analyzed, the time taken so far, and a button for cancelling the job. After a job is cancelled, the execution mode is set to manual.

![Job Execution Panel](docs/images/ProgressPanel.png)

The panels at the bottom are the recent executed job list on the left and the list of system issues and errors on the right.The recent job list shows whether the final status of the execution was successful or failed. If the failure requires the attention of the users, the system issue and error list will provide the details. Poor quality images, corrupted tile samples, and detection model misconfiguration are common examples of system issues. The system issue in the list can be clicked and dismissed.

### Interactive Visualization with the Result Browser

The following shows another main screen - the Result Browser, thought which the measurements of a particular acquaculture tile can be queried and visualized. 

![Browse Results Screen](docs/images/CoralDetectionResultBrowser.png)

Known tiles of the selected season are shown in the search table on the left side of the page.  Another spawning season may be selected using the dropdown menu at the top (as shown in the figure below). The table offers filters on each column for getting to the target tile quicker. Use the pagination controls at the bottom of the table to go through pages of tiles.  

![Browse Results Search Table](docs/images/ResultBrowserSearch.png)

Click on a row to inspect a tile's measurement results on the right side. The right pane is divided vertically into four sections (from top to bottom): 
- Key information of the tile and statistics of its samples.
- The number of corals at various sampling time presented as a trend chart and a table.
- The locations of detected corals and other key object classes of the latest sample presented as a scattered map. 
- The locations of detected corals or other key object classes of the latest sample presented as a heatmap. 

The last two sections offers users to interactively select samples to inspect and compare. 
- For the scattered map, click on the sampling time in the table on the left pane for comparison.  
- For the heatmap, click on the sampling time in the table on the left for comparison, or **Whole History** to display the heatmaps of all samples. Use the **Reverse** button to reverse the ordering of the heatmap. The top dropdown menu allows selection of the coral object class to view. The slider gives users the ability to hide labels of low count cells to reduce cluttering.  

### Data Handling with the Tile Sample Manager

The following shows the Tile Sample Manager, which supports manual handling of tile samples and monitoring the processing status.

![Tile Sample Manager](docs/images/TileSampleManager.png)

There are two panes at the top, which are the toggle switch for enabling/disabling automatic retrieval of tile samples from the Image Acquisition Coordinator System, and the drop area for manual import of tile sample specification yaml files. 
- Automatic retrieval of tile samples will happen only if the toggle switch is enabled and the Automated Execution Mode is eanbled.
- Tile samples can be imported manually through a specification yaml file, which contains the locations of the image files and other critical information.

The remainder of the page contains a table displaying the tile samples pending for processing and another table displaying the status of the processed tile samples. Use the buttons associated with the table to change the status of tile samples. Select one or more tile sample in the table and press the desired button.

The statuses of tile samples include:
- `QUEUED`: The tile sample pending processing is waiting in a queue.
- `DONE`: The tile sample has been processed successfully.
- `REJECTED`: The tile sample has been rejected by the system due to an inherent problem found in the processing. It may also be rejected according to external knowledge by the user.
- `FLAGGED`: The tile sample is tagged by the system due to a problem found in the processing but user inspection should resolve the problem. 

The functions of the buttons are explained below.
- `Prioritize`: Move the selected tile samples to the front of the queue.
- `Reject`: Reject the selected tile samples.
- `Delete`: Delete the tile sample permanantly from the CCVS (note: the IACS is not affected)
- `Redo`: Move the selected tile to the queue for re-processing, existing results can be selectively kept.

### The Detection Model Registry

A key feature of the CCVS is the ability to apply specialized coral detection models for tile samples of different species and development stages. The Detection Model Registry is the component that manages these specialized coral detection models. The Detection Model Registry provides an interface for the import of trained YOLO coral detection model into the system and for specifying the conditions in which the model is applied. The conditions include the coral species and the age of the tile sample. 

![Detection Model Registry](docs/images/DetectModelManager.png)

The top pane is the drop area for the import of a detection model specification yaml file.  In the middle the table displays the imported detection models and there are buttons for updating and deleting a model. The bottom pane shows a visualization of the coverage of each model in the species and in the coral age of the target tile samples.

## System Installation

The CCVS is written in Python and it is designed to run in a ROS1 (noetic) environment. It will run significantly more efficient with the support of CUDA/GPU but it can also run on a pure CPU host. 

#### Create a workspace for CGRAS packages

Assume that the path to the CGRAS packages is in the environment variable `CGRAS_WS` and it has the value `/home/qcr/cgras_ws`.  
```bash
CGRAS_WS=/home/qcr/cgras_ws
export CGRAS_WS
```
Create the workspace folders as follows.

```bash
mkdir -p ${CGRAS_WS}/src
```
In addition to this repository, the repositories of `cgras_datatools`, `cgras_messages`, and optionally `cgras_coordinator` are to be downloaded and saved to the `src` folder.

```bash
cd ${CGRAS_WS}/src
git clone git@github.com:REF-RAS/cgras_detector.git

git clone git@github.com:REF-RAS/cgras_datatools.git
git clone git@github.com:REF-RAS/cgras_messages.git
git clone git@github.com:REF-RAS/cgras_coordinator.git
```
The resulting folder structure under the CGRAS workspace is shown below.

```bash
${CGRAS_WS}                 # the root of the CGRAS workspace
├── src                  
├──├── cgras_detector           # the package of CCVS
├──├── cgras_coordinator        # the package of IACS (optional)
├──├── cgras_messages           # the package containing common ROS messaging definitions
├──├── cgras_datatools          # the package containing common programming utilities
├── devel                       # system generated (by catkin_make)
├── build                       # system generated (by catkin_make)
```

#### The folder structure of this repository

The repository contains various kinds of files that are relevant to the setup of the system. This section shows the locations of these critical files.

```bash
src
├── cgras_detector                   
├──├── config
├──├──├── system_config.yaml    # defines system configuration        
├──├── docker                   # contains files relevant to deployment of this system based on docker
├──├──├── assets                # a folder containing misc files used for building docker images
├──├──├── docker-compose.yaml   # a folder containing misc files used for building docker images
├──├──├── services              # a folder containing files for running the system as a systemd service and files for loading the system in a browser
├──├── docs                     # contains files relevant to deployment of this system based on docker
├──├──├── images                # a folder containing the images used in this README.md file 
├──├──├── tile_samples          # a folder containing template yaml files for specifying a tile sample manually
├──├──├── tile_samples_autogen  # a folder containing tile sample specification files generated by the system tools
├──├──├── tiles_info_csv        # a folder containing sample csv files holding information of tiles (only needed for the IACS)
├──├──├── yolo_model_samples    # a folder containing sample yaml files for specifying a yolo-based coral detection model 
├──├── launch                   # contains ros launch files
├──├── nodes                    # contains files to start the CCVS and the auxiliary image server
├──├── scripts                  # contains system tools
├──├── src                      # contains the source code
├──├──├── detector              
├──├──├──├── models                # program components for the various stages of tile image analysis
├──├──├──├──├── reco_error         # the component for the correction of location error in the reconstruction (not used by the system)
├──├──├──├──├── test               # contains unit tests for validating the components in the models subfolder
├──├──├──├──├── tile_filter        # contains program tool and sample training data for modelling the corners 
├──├──├──├── html                  # contains html snippets for image display functions of the system
├──├──├──├── test                  # contains unit tests for the rest of the system
├──├──├──├── web                   # program components for the web interface
├── READNE.md                   # this README.md file
├── requirements.txt            # python module dependencies 
```

#### Set up the file space

The two CGRAS systems, the CCVS and the IACS, shared a folder for file data storage. The default location is `cgras_data` under the home folder of the user.  The location may be updated as the value of the parameter `cgras_data_folder` in the `system_config.yaml` file.

Create the folder as follows.

```bash
mkdir -p ~/cgras_data
```

#### Set up the execution environment

The CCVS is a complex software built on many third-party modules and middleware. Some of them are listed below.
- ROS Noetic (ROS 1).
- Python 3.8 (Python 3.9 if pytorch 2.0 or above)
- Dash 3.0 or above
- Plotly 6.0 or above
- Numpy 1.24, Pandas 2.0, OpenCV 4.8.1, SkLearn
- Stitching 0.5.3
- Pytorch (CPU or GPU)
- CUDA/GPU Driver (optional)

It is recommended that the execution environment is to be set up by one of the following approaches: docker and virtual environment.  Docker is highly recommended for ease of setup. These two approaches are explained in the next sections.

Note that this instruction does not cover the installation of GPU driver (for Nvidia) and CUDA and the NVidia container toolkit.  Follow this page for a [easy-to-follow instruction](https://dev.to/thenjdevopsguy/using-nvidia-gpus-with-docker-in-5-minutes-386g) to enable GPU computation for CCVS.

### Docker Installation

Running from docker containers is the quickest way to set up the system if the [docker engine](https://docs.docker.com/engine/install/) is already installed.  Templates of docker images and docker compose services are provided in the repository under the `docker` folder.

The following docker compose services are defined in file `docker/docker-compose.yaml` file that carry out the setup the environment and the execution of the CCVS system through a single command.

| Docker Compose Services | Remarks                                | Execution Scripts | 
| :----------------       | :------:                               | :------:          |
| `cgras`                     | Start a container suitable for the running of the system with CUDA 10.1 enabled | `docker compose up cgras` |
| `cgras-cpu`                 | Start a container suitable for the running of the system with CPU only | `docker compose up cgras-cpu` |
| `cgras-system`             | Execute the CCVS system in the `cgras` container | `docker compose up cgras-system` |
| `cgras-system-cpu`         | Execute the CCVS system in the `cgras-cpu` container  | `docker compose up cgras-system-cpu` |


1. Change directory to the `docker` folder of this respository
```bash
cd ${CGRAS_WS}/cgras_detector/docker
```
2. The CGRAS docker containers will share the network with the host computer, including being the ROS Master if the host computer is already running `roscore`. The environment variable `ROS_MASTER` may be passed to the containers to determine if the `roscore` should be started by the container. The variable may be updated in the `environment` section of the services in `docker-compose.yaml`.

If the host computer is already running as the ROS Master, ensure that `ROS_MASTER` is set to `False`.
```yaml
        environment:
            - DISPLAY
            - QT_X11_NO_MITSHM=1
            - ROS_MASTER=false
            ...
```
If the container should be the ROS Master, set `ROS_MASTER` to `True` and `ROS_MASTER_URI` to the IP of the container. The default `localhost:11311` should work unless the network configuration requires something different.
```yaml
        environment:
            - DISPLAY
            - QT_X11_NO_MITSHM=1
            - ROS_MASTER=true
            - ROS_MASTER_URI=http://localhost:11311
            # - ROS_MASTER_URI=http://192.168.1.50:11311
```

3. Execute below to allow applications in the container to display a GUI on the host.
```
xhost +
```

4. To start the CCVS, execute one of the following in the `docker` folder (depending on whether CUDA/GPU is available). At the first time of execution, the image does not exist and so it has to be built from scratch and the building may take a while.  If the image is already available, the command starts a container based on the `cgras` (or `cgras-cpu`) image and launch the CCVS ros node. 

If CUDA/GPU is available, use this script.
```bash
docker compose up cgras-system
```
If CUDA/GPU is not available, use this script.
```bash
docker compose up cgras-system-cpu
```
If the image building is successful and the node is launched, the command line window will last print lines similar to the following.
```bash
[INFO] [1748390642.515012]: Starting the cgras_detector node (pid:950) (python: 3.8.10)
[INFO] [1748390642.555908]: DashApplicationMain: starting the web application at http://0.0.0.0:8023
```

5. To access the web interface, point a browser to the URL `http://localhost:8023`.  The host ip and port may be specified in the system configuration file.  The Application Monitor page will be loaded.

6. The docker service can be terminated by CTRL-C in the command line window running the docker compose command.


### Virtual Environment Installation

Non-docker system installation is more challenging for novices. Its success can depend on the host computer current settings.

1. A host computer with Ubuntu 20.04 is available. 

2. Ensure that, if GPU computation is desired, the Nvidia drivers and CUDA are already installed.  Use `nvidia-smi` to find out the status.    

3. Ensure that ROS Noetic is already installed. Follow [the instruction on this page](https://wiki.ros.org/Installation/Ubuntu) to install ROS Noetic on the host computer. 

4. If the computer has no virtual environment manager such as conda, install one such as miniconda as follows. 
```bash
wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh 
bash ~/Miniconda3-latest-Linux-x86_64.sh 
``` 

5. Create a new environment (replace the name `cgras` with your preference). 
```bash
conda create -n "cgras" python=3.8 ipython ipykernel 
conda activate cgras 
```

6. Install Python 3.8 and various Python tools.
```bash
sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt-get update && sudo apt-get upgrade python3.8
sudo apt-get update 
sudo apt-get install python3-pip python3-rospkg python3-rosdep python3-setuptools
pip install -U pip
```

7. Install third-party Python modules.
```bash
cd ${CGRAS_WS}/cgras_detector
pip install -r requirements.txt
```

8. Install pytorch and ultralytics.
```bash
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu101
pip install networkx==3.1 ultralytics>=8.3
```

9. Build the CGRAS package.
```bash
rosdep update
cd ${CGRAS_WS}
catkin_make -DPYTHON_EXECUTABLE=/usr/bin/python3
source devel/setup.bash
```
10. Launch the CCVS node.
```bash
roslaunch cgras_detector default.launch
```

### System Properties

The system will load properties from the yaml file `system_config.yaml` under the folder `config`. The properties can be divided into several cateogories: web interface, CGRAS system integration, CCVS system operation, and models/algorithms parameters.

#### Properties: Web Interface

```yaml
cgras_detector:
  # WEB INTERFACE
  # main web server
  web_host: 0.0.0.0
  web_port: 8023
  web_debug_mode: False             # for developers' use and not to be adjusted
  web_debug_hot_reload: False       # for developers' use and not to be adjusted

  # auxillary web server
  aux_web_host: 0.0.0.0
  aux_web_port: 8024
  aux_web_directory: ~/cgras_data/detector/data    # for developers' use and not to be adjusted

  # timers for driving the system and refresh the GUI
  system_timer: 0.5  # seconds
  dashboard_refresh_cycles: 2  # refresh rate of dashboard, the unit is system timer cycles
  ...
```
The following table describes the purpose of the key properties.

| Config variables     | Remarks                                                          | Default value (type) | 
| :----------------    | :------:                                                         | :------:      |
| `web_host`             | The ip of the web interface                                    | 0.0.0.0 (str)     |
| `web_port`             | The port number of the web interface                           | 8023          |
| `aux_web_host`             | The ip of the auxilliary web host that serves image        | 0.0.0.0 (str)     |
| `aux_web_port`             | The port number of the auxilliary web host                 | 8024          |
| `system_timer`             | The clock that triggers signals in the web interface       | 0.5 (seconds)     |
| `dashboard_refresh_cycles` | Number of system timer cycles to refresh the web interface | 2          |


#### Properties: CGRAS Integration

These properties are about connections to other components in the CGRAS platform.

```yaml
cgras_detector:
  # CGRAS INTEGRATION
  # default ros topics for the states of the coordinator and detector
  ros_coordinator_state_topic: '/cgras/coordinator/state' 
  ros_detector_state_topic: '/cgras/detector/state' 

  # default ros topic for the service for querying tile sample
  ros_query_tile_samples_topic: '/cgras/coordinator/query_tile_samples'

  # suspend operation when executing a capture image program
  suspend_when_capturing_image: False

  # connection timeout
  connection_timeout: 120   # seconds
  ...
```
| Config variables     | Remarks                                                          | Default value (type) | 
| :----------------    | :------:                                                         | :------:      |
| `ros_coordinator_state_topic` | The ROS topic where the IACS's state is published       | `/cgras/coordinator/state`  (str)     |
| `ros_detector_state_topic` | The ROS topic where this CCVS's state is published         | `/cgras/detector/state`  (str)       |
| `ros_query_tile_samples_topic` | The ROS service name for querying new tile samples at the IACS | `/cgras/coordinator/query_tile_samples` (str)     |
| `suspend_when_capturing_image` | Whether the CCVS is suspended when the IACS is executing an image capture program  | False (bool)          |
| `connection_timeout`           | The connection to the IACS is considered lost      | 120 (seconds)     |

#### Properties: System Operations

```yaml
cgras_detector:
  # OPERATION
  # the data folder
  cgras_data_folder: ~/cgras_data

  # automation mode (whether the task execution is automated at system startup)
  task_automation: False  

  # yolo model range
  max_coral_age: 120  # days

  # heatmap properties
  heatmap_colour_scale: viridis
  heatmap_show_label_slider_max: 30
  ...
```
| Config variables     | Remarks                                                          | Default value (type) | 
| :----------------    | :------:                                                         | :------:      |
| `cgras_data_folder` | The location of the CGRAS data folder       | `~/cgras_data`  (str)     |
| `task_automation` | The system starts with the automation mode turned on        | False (bool)      |
| `max_coral_age` | The maximum age of corals assumed by the system | 120 (days)     |
| `heatmap_colour_scale` | The colormap name used for coral count heatmaps| `viridis` (str)  |
| `heatmap_show_label_slider_max` | The maximum value of the slider controlling label showing threshold in the heatmaps | 30 (integers) |

For choices of colormaps, refer to [this tutorial](https://seaborn.pydata.org/tutorial/color_palettes.html).

#### Properties: Models and Algorithms

These system properties related to internal models and algorithms for computer vision based coral detection. They are further divided into reconstruction related (`reco`), tile locator related (`loctile`), and coral object detection related (`cod`).

```yaml
cgras_detector:
  # MODELS AND ALGORITHMS
  # general
  task_params_filename: params.yaml             # for developers' use and not to be adjusted
  reco_model_filename: reco_model.yaml          # for developers' use and not to be adjusted
  loctile_model_filename: loctile_model.yaml    # for developers' use and not to be adjusted
  cod_model_filename: coral_object_detect_model.yaml   # for developers' use and not to be adjusted
  # detection task parameters: reconstruction
  reco_working_scale: 0.1
  reco_debug_images_at_original_scale: False
  reco_debug_feature_matching_images: True
  reco_feature_detectors: ['brisk', 'sift']     # sift, orb, brisk, akaze 
  reco_feature_matching_confidence_threshold: 1.2
  reco_image_matching_min_confidence: 1.0   # between rows matching confidence
  reco_image2d_matching_min_confidence: 1.0 # row matching confidence
  # reco_error_correction: False            # for developers' use and not to be adjusted
  reco_aspect_ratio_roi_error_rel: 0.1           # the maximum relative error of aspect ratio of rois from that of the original image
  reco_misplaced_roi_erro_rel: 0.1               # the maximum relative error of roi corner placement with respect to the roi sizes

  # model of the tile holder and frame
  tile_size_in_mm: [294, 294]  # default value, only if not defined in the metadata of the tile_sample 
  frame_size_in_mm: [280, 280] # default value, only if not defined in the metadata of the tile_sample 

  # detection task parameters: locate tile
  loctile_rotate_angle_max: 3.0   # degrees
  loctile_aspect_ratio_diff_max_rel: 0.05   # 0.05 relative difference
  loctile_aspect_ratio_diff_max_abs: 0.05   # 0.05 absolute difference

  # detection task parameters: object detection  
  cod_debug_blob_images: True
  cod_blob_overlap_pix: 128
  cod_use_cached_object_detection: True
  cod_coral_child_min_overlap_ratio: 0.25         # the pverlap ratio of a polyp_single or polyp_keypart that is considered a child of a polyp_multi
  cod_merge_mutli_models: True                # merge the detection result with duplication removal
  
  # detection task parameters: object detection classification
  cod_mask_polyp_keypart: False
  ...
```

##### Geometry related
| Config variables     | Remarks                                                          | Default value (type) | 
| :----------------    | :------:                                                         | :------:      |
| `tile_size_in_mm` | The width and the height of the tiles (the default values) | [294, 294] (a list of two lenghts in mm)    |
| `frame_size_in_mm` | The width and the height of the frames (the default values) | [280, 280] (a list of two lenghts in mm)    |

##### Reconstruction related
| Config variables     | Remarks                                                          | Default value (type) | 
| :----------------    | :------:                                                         | :------:      |
| `reco_working_scale` | The image scale at which the reconstruction algorithm is operating | 0.1 (float)    |
| `reco_debug_images_at_original_scale` | Save debug images of tile reconstruction at original scale      | False (bool)      |
| `reco_debug_feature_matching_images` | Save debug feature matching images | True (bool)     |
| `reco_feature_detectors` | A list of feature detectors to be tried in tile image reconstruction | [`brisk`, `sift`] (list)  |
| `reco_feature_matching_confidence_threshold` | The minimum confidence value to consider feature matching acceptable | 1.2 (float) |
| `reco_image_matching_min_confidence` | More specific minumum confidence value for reconstruction along a row of images | 1.0 (float) |
| `reco_image2d_matching_min_confidence` | More specific minumum confidence value for reconstruction between rows of images | 1.0 (float) |
| `reco_aspect_ratio_roi_error_rel` | The maximum relative error of aspect ratio of rois from that of the original image | 0.1 (ratio) |
| `reco_misplaced_roi_erro_rel` | The maximum relative error of roi corner placement with respect to the roi sizes | 0.1 (ratio) |

##### Tile Locator related
| Config variables     | Remarks                                                          | Default value (type) | 
| :----------------    | :------:                                                         | :------:      |
| `loctile_rotate_angle_max` | The maximum angle of rotation acceptable | 3.0 (degrees)   |
| `loctile_aspect_ratio_diff_max_rel` | The maximum relative error between the aspect ratio of the reconstructed tile and that of `tile_size_in_mm`  | 0.05 (ratio)    |
| `loctile_aspect_ratio_diff_max_abs` | The maximum absolute error between the aspect ratio of the reconstructed tile and that of `tile_size_in_mm`  | 0.05 (aspect ratio)    |

##### Coral Object Detection related
| Config variables     | Remarks                                                          | Default value (type) | 
| :----------------    | :------:                                                         | :------:      |
| `cod_debug_blob_images` | The maximum angle of rotation acceptable | True (bool)  |
| `cod_blob_overlap_pix` | The size of the overlappign region between neighbouring blobs  | 128 (pixels)    |
| `cod_use_cached_object_detection` | Use the cached object detection if available  | True (bool)   |
| `cod_coral_child_min_overlap_ratio` | The minimum ratio to consider an overlapping object a child-parent pair  | 0.25 (ratio)    |
| `cod_merge_mutli_models` | Use multiple applicable coral detection models | True (bool)   |
| `cod_mask_polyp_keypart` | Mask the class polyp_keypart class when determining the presentation class | False (bool)   |

## System Setup

The operation of CCVS requires a coral detection model based on YOLO and a source of tile samples to be processed. 

### Import of a Coral Detection Model

The following shows a template of a coral detection model specification yaml file, which contains critical information such as the file location of a trained YOLO model, the class names of the detection results, and other metadata.

```yaml
name: Maeq 20250320
file: /home/qcr/cgras_data/YoloModel/cgras_20250320_yolov8nseg_640p_first30.pt
species: montipora aequituberculata 
input_image_width: 640
input_image_height: 640
valid_start_day: 0
valid_end_day: null
classes_map: 
  POLYP_SINGLE: []
  POLYP_MULTI: ['mask_live']
  POLYP_KEYPART: ['alive']
  DEAD_CORAL: ['dead', 'mask_dead']
remarks: 
yolo_predict_params:
  conf:               # default 0.25
  iou:                # default 0.7
  agnostic_nms:       # default False
```
| Parameter     | Remarks         |  |
| :----------------    | :------: | :------: | 
| `name` | The name of the coral detection model | Mandatory |
| `file` | The full path to the trained YOLOv8 model file (.pt) | Mandatory |
| `species` | The species that this model is applicable |  Mandatory |
| `input_image_width` | The image width expected by the YOLOv8 model | Mandatory |
| `input_image_height` | The image height expected by the YOLOv8 model |  Mandatory |
| `valid_start_day` | The start of the age range that this model is applicable | Optional |
| `valid_end_day` | The end of the age range that this model is applicable  | Optional | 
| `classes_map` | The node that maps the output classes of YOLOv8 model to the internal classes | Mandatory | 
| `remarks` | Additional description | Optional | 
| `yolo_predict_params` | The node that defines yolo prediction parameters | Mandatory | 

The significance of `classes_map` is to map the classes of the YOLOv8 model, which depends on the modelling of coral objects and the choice of class names, to the internal coral classes of the CCVS, which comprises of the following.

| CCVS Coral Classes     | Remarks         |  
| :----------------    | :------: | 
| `POLYP_SINGLE` | Represents a singleton coral polyp (not in a cluster/colony)  | 
| `POLYP_MULTI` | Represents a cluster or colony of coral polyps | 
| `POLYP_KEYPART` | Represents a keypart that distinguishes a cluster or colony |
| `DEAD_CORAL` | Represents a dead coral whether it is a part or as a whole |

The `yolo_predict_params` contains parameters that are passed to the YOLO predict function call. (Ref: https://docs.ultralytics.com/modes/predict/#inference-arguments)

| YOLO Predict Params     | Remarks         |  
| :----------------    | :------: | 
| `conf` | Sets the minimum confidence threshold for detections | 
| `iou` | Intersection Over Union (IoU) threshold for Non-Maximum Suppression (NMS) | 
| `agnostic_nms` | Enables class-agnostic Non-Maximum Suppression (NMS), which merges overlapping boxes of different classes |

### Import of a Tile Sample Specification

The following shows a template of a tile sample specification yaml file, which specifies the locations and the indices of the images that all together capture the visual appearance of a tile, additionally, other metadata of the tile such as the species and the age and the sampling time.

```yaml
tile_id: 2024Oct-MIS5T14
species: Acropora
settle_time: 2024-10-30
spawning_time: 2024-10-15
season: 2024Oct
num_tabs: [20, 20]
tile_size: [280, 280]
frame_size: [294, 294]
batch_id: CG1-202410312300
batch_time: 2024-10-31 23:00:00
importer_id: YAML
operator: luia2
image_files_parent_folder: /home/qcr/cgras_data/Source/2024/MIS5_T14_241031
images:
  - x: 0
    y: 0
    file: CGRAS_Amag_241031_T14_00.jpg
  ...
```
| Parameter     | Remarks         |  |
| :----------------    | :------: | :------: | 
| `tile_id` | The ID of the tile, which is made up of the season and the PIT tag ID (connected by a hyphen) | Mandatory |
| `species` | The species of the coral that is growing on the tile | Mandatory |
| `settle_time` | The date that the coral larvae was allowed to settle on the tile | Mandatory |
| `spawning_time` | The date that the coral spores spawned | Mandatory |
| `season` | The spawning season | Mandatory |
| `num_tabs` | The number of tabs of the tile| Mandatory |
| `tile_size` | The width and the height of this tile (in mm)  | Option |
| `frame_size` | The width and the height of the frame of this tile (in mm)  | Option |
| `batch_id` | The batch ID, which comprises of the CGRAS station ID and the sampling time (connected by a hyphen) | Mandatory |
| `batch_time` | The date and time of the sample  | Mandatory |
| `importer_id` | Denotes how the tile sample is imported | Optional |
| `operator` | Denotes the operator of the import action | Optional |
| `image_files_parent_folder` | The path if all the images are in the same folder | Optional |
| `images` | A list of records each of which describes the location of the image file and the index in the capture grid | Mandatory |

Each record under the `images` node has the following fields.

| Image Parameters     | Remarks         |  
| :----------------    | :------: | 
| `x` | The column index of the image in the capture grid  |
| `y` | The row index of the image in the capture grid  |
| `file` | The path to the image if the string starts with `/` or image filename if otherwise  |

### Experimental Feature: RESTful API

The system provides several endpoints as a part of an experimental RESTful API. 

| Endpoints     | Remarks         |  Return Values | 
| :----------------    | :------: | :------:  |
| `/api/tile_samples/list/<string:season_title>` | Query for all the tile samples of a season | A list of tile samples (json) |
| `/api/detected_objects/query/<string:tile_sample_id>` | Query for the detected objects of a tile sample | A list of detected objects (json) |
| `/api/tile_samples/import` | Import a new tile sample in yaml format | N/A |




## Developer

Dr Andrew Lui, Senior Research Engineer <br />
Robotics and Autonomous Systems, Research Engineering Facility <br />
Research Infrastructure <br />
Queensland University of Technology <br />

Latest update: May 2025