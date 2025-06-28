# CGRAS 2025: Modelling Coral Object Detection in CCVS

This document explains the semantics of coral counting and coral object classes in CCVS.

## Counting Coral Objects

CCVS is designed to count three types of objects: alive corals, dead corals, and other objects. The _other objects_ refer to those that are not corals, alive or dead, but of interest to the users.  CCVS uses a combination of bespoke object detection models and heuristics to infer these classes of objects based on their visual appearance. 

The visual appearance of corals of different species can change drastically. There are over 600 species in the Great Barrier Reef alone. Even for corals of the same species, the shape, color, and structure of corals can change significantly within weeks. The following figure illustrates the different appearance of the Amag species between week 1 to week 6 since settlement on the tile.

![Coral Amag Development Visual Change](./images/CoralAmagDevelop.png)

Counting alive coral objects depends on accurate identification of individual corals through distinctive visual features. As seen above, an individual coral is sometimes better identified as a whole and other times identified through its parts. More specifically, the corals in the first week lack an internal structure and they are better identified as a pinkish blob. The more matured corals, on the other hand, contain multiple visually distinctive polyps as their internal structure. Modelling an individual coral as the whole and modelling through its parts are both suitable approaches for counting alive corals.

CCVS has adopted a hierarchical framework of coral classes in order to support the two modelling approaches.

## Hierarchical Framework of Coral Classes

The hierarchical framework of the CCVS is described in the following figure.

![Hierarchical Class Framework](./images/HierarchicalClassFramework.png)

The framework stipulates that every object is progressively assigned with three annotations from low to high semantic levels. The process starts from the bottom, the __YOLO model layer__, which represents the initial detection of candidate objects based on visual appearance. The possible classes of a __model label__ are dependent on how the applicable YOLOv8 model and are therefore custom and modeller-defined. 

The next layer up is the __coral feature layer__ which defines several cononical classes for interpreting the custom classes of the __model layer__. This layer allows the custom classes to be mapped into coral feature classes that are understood by the CCVS. The following table summarizes the four coral feature classes.

| Coral Feature Classes | Visual Features | Significance |
| ------- | ------- | ------- |
| POLYP_SINGLE | A coral with a single polyp | Contributes to one count of `alive_coral` |
| POLYP_MULTI | A coral with multiple polyps | Contributes to one count of `alive_coral`|
| POLYP_KEYPART | A key part of a coral | Indirectly or partially contributes to one count of `alive_coral` |
| DEAD_CORAL | A part or a whole dead coral | Indirectly or partially contributes to one count of `dead_coral`|
| OTHER | A part or a whole other object | Contribute to one count of `other`|

> [!NOTE]
> The `OTHER` coral feature class is currently not fully implemented in CCVS.

The top layer is the __presentation layer__ which contributes to counting of alive corals, dead corals, and other objects. The following table summarizes the three presentation classes.

| Presentation Classes | Description | Significance to Counting |
| ------- | ------- | ------- |
| `alive_coral`  | An alive coral biologically | Contributes to one count of `alive_coral` |
| `dead_coral` | A biological coral that is now dead | Contributes to one count of `dead_coral`|
| `other` | A non-coral object of interest  | Contributes to one count of `other` |

### Map Function between YOLO Model Labels and Coral Feature Labels

The map function between the bottom layer and the middle layer is part of the Coral Object Detection model and it is specified by the coral modeller. The actual function is included in the COD model yaml file. Each cononical class of the coral feature layer is mapped to zero or more classes of the YOLO model layer. 

The following is an example of such a map function.
 
```yaml
classes_map: 
  POLYP_SINGLE: []
  POLYP_MULTI: ['mask_live']
  POLYP_KEYPART: ['alive']
  DEAD_CORAL: ['dead', 'mask_dead']
```

### Map Function between Coral Feature Labels and Presentation Labels






## Developer of the System

Dr Andrew Lui, Senior Research Engineer <br />
Robotics and Autonomous Systems, Research Engineering Facility <br />
Research Infrastructure <br />
Queensland University of Technology <br />

## Author

This document is written by Dr Andrew Lui <br />
Latest update: June 2025