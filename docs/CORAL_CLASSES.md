# CGRAS 2025: Semantics of Coral Classes and the Hierchical Class Structure

The visual appearance of corals of different species and development stages can look significantly different. No one-size-fit-all YOLO-based detection model is likely to offer reasonable detection performance. To enable the CCVS improved capacity to handle increasing number of coral species and to enhance the detection performance, CCVS is designed with the following features.
- Enable import of new YOLO coral object detection models.
- Select and apply the YOLO models specialized for the coral species and the developmental stage that are present in the file sample.
- Accept arbitrary object class names and conversion rules for mapping them to the cononical classes associated for coral counting and visualization.

The understanding of vision-based coral detection is still inadequate. A coral object 


A reliable coral object detection model must be able to identify the whole coral 



In the CCVS, specialized coral detection models can be selectivelty applied on tile samples of different species and development stages. 
Part of the Coral Object Detector is the Coral Detection Model Registry that provides an interface for the import and management of specialized coral detection models. The ability to incorporate new models is important to the extensibility of the CCVS.  


The Detection Model Registry is the component that manages these specialized coral detection models.  It supports the Coral Object Detector 


One of the key features of the Coral Counting and Visualization System (CCVS) is  object detection model


The Coral Counting and Visualization System (CCVS) of CGRAS 2025 aims to offer understanding of spatial distributions and temporal changes of corals growing out on aquaculture tiles.  One of its key components is the coral object detector, which comprises of models for visually classify and locate corals from images of aquaculture tiles.   

In parallel to the development of CCVS, research effort has been put in to develop effective coral object detection models. Corals of different species and different ages can look very different.  A one-size-fits-all model for all coral species and for corals at different developmental stages is infeasible.  It is essential to design CCVS so that its abilities in detecting new coral species and differentiating coral development stages are extensible.

Therefore, the  

The following figure shows where the coral object detector (i.e., the component with a red outline) sits in the CCVS. 

![Tile Sample Processing](./images/TileSampleProcessing.png)

### A Hierarchical Framework of Coral Object Classification

The internal representation refers to hierarchical framework of coral object classification.  

![Hierarchical Class Framework](./images/HierarchicalClassFramework.png)

The middle



The internal representation refers to the set of three classes at the presentation semantic layer of CDVS, namely, coral objects, dead coral objects, and non-coral objects. The model-specific maps can specify how the new semantics of object classes in YOLO models are understood from the perspective of the internal representation. 

The outcomes of recent empirical studies by the project team indicate that the single-layer internal representation is limited at abstracting the semantic relation between a coral and its composition.  From a visual perspective, a coral has many forms, such as a singleton polyp, a cluster of polyps, a lump of settled coral larvae (which is likely a precursor of a cluster), etc.  Including these as classes of a more sophisticated internal representation will enhance the extensibility of CDVS and the usability of the detection results.  More powerful rules can be defined to map each of these forms into the 3 classes of internal representation for more accurate coral counts.  The enriched class hierarchy can support more downstream coral object analytics.  