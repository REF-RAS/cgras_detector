## Summary of Processing Errors and System Issues


### Procssing Errors

Processing errors are issues that causes the execution to fail and the tile sample rejected.

#### Import Failures

| Error Code | Message     | Remarks |
| ---------- | ------     | ------- |
| INPUT_DATA_INVALID  | Tile sample does not contain tile size or frame size  | (For manual import) Ensure the tile/frame size exists in the tile sample spec file |
| INPUT_DATA_INVALID  | Invalid date/time format in batch time or settle time | (For manual import) Ensure the format is correct in the tile sample spec file |
| INPUT_DATA_INVALID  | Missing image in the capture grid | (For manual import) Ensure that the indices of the image are not missing in the tile sample spec file |
| INPUT_DATA_INVALID  | Image file in the capture grid not found / image file not found | (For manual import) Ensure the image file exists (names and path are correct) |
| INPUT_DATA_INVALID  | Unable to read image file / Not a valid image file | (For manual import) Ensure the file is of a valid image format |
| INPUT_DATA_INVALID  | Row Length Mismatch: two rows in the image grid are of different lengths | (For manual import) Ensure the indices of images form a rectangular grid |

If any of the above error occurred is associated with a tile sample that is imported automatically, check if the images have been deleted or moved to other locations, or the image file is locked (such as locked by an image editor).

#### Resolvable Failures

| Error Code | Message     | Remarks |
| ---------- | ------     | ------- |
| RECO_FAILED  | Unable to obtain camera transforms for every image in the row #  | Possibly due to poor image quality or the original tile is devoid of visual features |
| RECO_FAILED  | Cannot find warp rois for all images in the row | Possibly due to poor image quality or the original tile is devoid of visual features |
| RECO_FAILED  | The aspect ratio of one or more rois is different from the original image | A result of reconstructon validation that is possibly due to a problem in image capture |
| RECO_FAILED  | Roi corners not regularly placed | A result of reconstructon validation that is possibly due to a problem in image capture |
| RECO_FAILED  | Cannot combine image as a grid: possibly wayward homography matrices| As above |
| RECO_MATCH_FAILED  | Cannot merge adjacent images: possibly error in image capturing | Possibly due to misplaced image in the capture grid (for manaul import) or generally poor image quality or the original tile is devoid of visual features |
| RECO_MATCH_FAILED  | Cannot obtain camera transform for every rows: lack sufficient features or feature detector not suitable | Ditto |
| RECO_MATCH_FAILED  | Cannot obtain camera transforms between rows: lack sufficient between row features or feature detector not suitable | Ditto |

The above errors are mostly coming from error in the upstream image capture application or manual image capture.  No remedial action can be recommended.

| Error Code | Message     | Remarks |
| ---------- | ------     | ------- |
| LOC_FRAME_MISSING | Not all four corners are found | Possibly due to capture error or the visual aspects of the tile frame are not as required (i.e. blue corners) |
| LOC_FAILED | Angle of rotation outside of the valid range | Possibly due to too much mis-alignment when capturing the images |
| LOC_FAILED | The aspect ratio of the detected frame does not match the given frame size in mm | Ensure that the frame size in the tile sample specification is correct, or it may be due to reconstruction error |

The above errors (except the last) are mostly coming from error in the upstream image capture application or manual image capture.  No remedial action can be recommended.

#### Resolvable Failures

| Error Code | Message     | Remarks |
| ---------- | ------     | ------- |
| YOLO_MODEL_FILE_ERROR | Failed to load the yolo model file  |Ensure that the file path in the COD model specification is correct and the file exists |
| YOLO_MODEL_UNDEFINED | Multiple yolo models: blob sizes are not consistent | The image sizes (`image_sz`) of two or more COD models are not the same |
| YOLO_MODEL_ERROR | Error happened when the YoloModel is applied on an image blob | Test the YOLOv8 model file offline for errors |
| YOLO_MODEL_UNDEFINED | No suitable yolo model: species and days_since_settlement | Import a COD model applicable to the tile sample |

The tile sample associated with the above errors can be moved back to the processing queue after the issue about the COD models is resolved.

#### IO and File Errors

| Error Code | Message     | Remarks |
| ---------- | ------     | ------- |
| OS_ERROR | Failed to save detect model parameter to the logdata folder | |
|          | Failed to write cod model to yaml file | |
|          | Failed to write detection results to the database | |
|          | Unable to write html files | |
|          | Failed to write feature matching output to  | |
|          | Failed to write whole reco image with tile bounds output to | |
|          | Failed to write rotated whole reco image with tile bounds output to| |
|          | Failed to write ImageReconstructModel to | |
|          | Failed to create folder for log and cache files | |
|          | Failed to write feature matching output to | |
|          | Failed to write row reconstructed image to | |
|          | Failed to write feature matching results between row reconstructed images to| |
|          | Failed to write whole reconstructed image to | |
|          | Failed to write rotated reconstructed image to | |
|          | Failed to write whole reconstructed image at original scale to  | |
|          | Failed to write row reconstructed image at scale to| |
                   
Possibly causes of the above errors include insufficient disk space, the file in question already exists and locked by another application, the host computer or file space is faulty.

## System Issues

| Error Code | Message     | Remarks |
| ---------- | ------     | ------- |
| DISK_SPACE_ERROR | Current free disk space is too low. The processing is ceased until more space becomes available | Ensure enough free disk space is available |



