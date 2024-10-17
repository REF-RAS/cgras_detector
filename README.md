# CGRAS 2025: Coral Counting and Visualization System

The **Coral Counting and Visualization System (CCVS)** is part of the CGRAS 2025 platform. CCVS is designed for monitoring the well being of the growing coral babies on aquacultural tiles by analysing tile images and counting the number of corals and other objects. 

CCVS operates as an autonomous system that streamlines fetching of newly acquired tile images (from the other systems of CGRAS 2025), applying of deep learning object detection models on the images, analyzing and recording of data, and presenting of useful findings.  CCVS provides a web-based user interface for interactive visualization of trends of coral growth on tiles. It also offers control for the users to override the autonomous operations and to enhance the analysis with import of new models.  

![Dashboard Screen](docs/DashboardScreen.png)

![Chart Screen](docs/ChartScreen.png)

## Running the Node

After building the workspace, execute the following
```
rosrun cgras_detector run.py
```



## Developer

Dr Andrew Lui, Senior Research Engineer <br />
Robotics and Autonomous Systems, Research Engineering Facility <br />
Research Infrastructure <br />
Queensland University of Technology <br />

Latest update: Oct 2024