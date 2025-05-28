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

### The Detection Model Manager

The Detection Model Manager provides an interface for the import of trained YOLO coral detection model into the system and for specifying the conditions in which the model is applied. The conditions include the coral species and the age of the tile sample. 

![Detection Model Manager](docs/images/DetectModelManager.png)

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

1. Assume that if GPU computation is desired, the Nvidia drivers and CUDA are already installed.  Use `nvidia-smi` to find out the status.

2. If the computer has no virtual environment manager such as conda, install one such as miniconda as follows. 
```bash
wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh 
bash ~/Miniconda3-latest-Linux-x86_64.sh 
``` 

3. Create a new environment (replace the name `cgras` with your preference). 
```bash
conda create -n "cgras" python=3.8 ipython ipykernel 
conda activate cgras 









## Running the Node

After building the workspace, execute the following
```
rosrun cgras_detector run.py
```

## Installation (Docker)

The [Dockerfile](docker/Dockerfile) for building the environment is in the `docker` directory of this repository. The file [docker-compose.yaml](docker/docker-compose.yaml) enables the management of containers as services. It has been tested with Docker 25.0.3 and Ubuntu 20.04. First change directory to where the file is located, and then build the image using the command below.
```
cd docker
docker compose build cgras_image
```
The image building may take some time. When the build is completed, execute the following to check if the image `cgras_image` is there.
```
docker image ls
```
Execute below to allow applications in the container to display a GUI on the host.
```
xhost +
```
Create a workspace for CGRAS in your local computer.
```
cd ~
mkdir -p ~/cgras_ws/src
```
Clone the `cgras_detector` and `cgras_datatools` repositories to the workspace
```
cd ~/cgras_ws/src
git clone git@github.com:REF-RAS/cgras_detector.git
git clone git@github.com:REF-RAS/cgras_datatools.git
```
Create a folder for system data at `cgras_data`.
```
mkdir -p ~/cgras_data
```
Start a container based on the image. Note that the two packages above and the data folder will become read/write volumes mapped to the container. 
```
docker compose up cgras_image
```
To obtain an interactive shell of the container
```
docker compose exec cgras_image bash
```
In the interactive shell, build the system and launch the node.
```
cd ~/cgras_ws
catkin_make
source devel/setup.bash
roslaunch cgras_detector default.launch
```


## Developer

Dr Andrew Lui, Senior Research Engineer <br />
Robotics and Autonomous Systems, Research Engineering Facility <br />
Research Infrastructure <br />
Queensland University of Technology <br />

Latest update: Apr 2025