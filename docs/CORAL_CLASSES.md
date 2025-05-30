# CGRAS 2025: Semantics of Coral Classes and the Hierchical Class Structure

The Coral Counting and Visualization System (CCVS) of CGRAS 2025 aims to offer understanding of spatial distributions and temporal changes of corals growing out on aquaculture tiles.  One of its key components is the coral object detector, which comprises of models for visually classify and locate corals from images of aquaculture tiles.  The understanding of vision-based coral modelling is still immature. 

In parallel to the development of CCVS, research effort has been put in to develop effective coral object detection models. Corals of different species and different ages can look very different.  A one-size-fits-all model for all coral species and for corals at different developmental stages is infeasible.  It is essential to design CCVS so that its abilities in detecting new coral species and differentiating coral development stages are extensible.

Therefore, the coral object detector of the CDVS has been designed with the following features: 
- Enables plugin of new YOLO models for coral object detection.  
- Selects YOLO models according to the coral species and developmental stage (represented by the number of days since settlement). 
- Supports, as a part of the plugin, a model-specific conversion of object classes of a YOLO model to the internal representation of CCVS.   

The following figure shows where the coral object detector (i.e., the component with a red outline) sits in the CCVS. 

![Tile Sample Processing](./images/TileSampleProcessing.png)

### A Hierarchical Framework of Coral Object Classification

The internal representation refers to hierarchical framework of coral object classification.  

![Hierarchical Class Framework](./images/HierarchicalClassFramework.png)

The middle



The internal representation refers to the set of three classes at the presentation semantic layer of CDVS, namely, coral objects, dead coral objects, and non-coral objects. The model-specific maps can specify how the new semantics of object classes in YOLO models are understood from the perspective of the internal representation. 

The outcomes of recent empirical studies by the project team indicate that the single-layer internal representation is limited at abstracting the semantic relation between a coral and its composition.  From a visual perspective, a coral has many forms, such as a singleton polyp, a cluster of polyps, a lump of settled coral larvae (which is likely a precursor of a cluster), etc.  Including these as classes of a more sophisticated internal representation will enhance the extensibility of CDVS and the usability of the detection results.  More powerful rules can be defined to map each of these forms into the 3 classes of internal representation for more accurate coral counts.  The enriched class hierarchy can support more downstream coral object analytics.  