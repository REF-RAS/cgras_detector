# CGRAS 2025: Coral Counting and Visualization System

The **Coral Counting and Visualization System (CCVS)** is part of the CGRAS 2025 platform. It is designed to monitor the coral recruitment process in tanks with acquaculture tiles. It achieves the objective based on visual analytics on images captured of the tiles, which involves the application of deep-learning based object detection models, the post-processing of identified objects, and the presentation of the findings. CCVS provides a web interface for users to monitor and control the visual analytics process, to manage the image samples, and to visualize the trend and distribution of corals of a tile. 

## Basic Operation

The CCVS can operate in tendem with the **Image Acquisition Coorindation System (IACS)**, from which the input images of tile samples are retrieved through the ROS middleware. It can operate also in a stand-alone manner, in which case the input images can be imported through the user interface or a RESTful API.

The input images are organized as tile samples. A tile sample is a set of images captured of a tile. Depending on the image capturing device, multiple images may be required to capture all areas of a tile at a required resolution. The images are expected to arrange in a grid-like manner. A tile sample is associated with a particular tile, identified by the __tile_id__, and the capture time, identified by the __batch_id__.

The operation of the CCVS is centred around management and processing of tile samples.  The following illustrates the generation and the associated data of a tile sample.

![Tile Sample](docs/images/TileSampleInfo.png)

### The Web Interface

The following shows the main screen - the Monitor, which is structured into four areas.

![Dashboard Screen](docs/images/DashboardScreen.png)

The top-left corner is the __job control__ panel. CCVS has defined two job types: (1) coral detection of a tile sample and (2) retrieval of a tile sample from the IACS. 



It is designed for monitoring the well being of the growing coral babies on aquacultural tiles by analysing tile images and counting the number of corals and other objects. 

CCVS operates as an autonomous system that streamlines fetching of newly acquired tile images (from the other systems of CGRAS 2025), applying of deep learning object detection models on the images, analyzing and recording of data, and presenting of useful findings.  CCVS provides a web-based user interface for interactive visualization of trends of coral growth on tiles. It also offers control for the users to override the autonomous operations and to enhance the analysis with import of new models.  



![Chart Screen](docs/ChartScreen.png)

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