import numpy as np
import cv2
import glob
import yaml
import pathlib

# termination criteria
criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001)
# prepare object points, like (0,0,0), (1,0,0), (2,0,0) ....,(6,5,0)
objp = np.zeros((7*7,3), np.float32)
objp[:,:2] = np.mgrid[0:7,0:7].T.reshape(-1,2)
# print(f'objp: {objp}')
# Arrays to store object points and image points from all the images.
objpoints = [] # 3d point in real world space
imgpoints = [] # 2d points in image plane.

images = glob.glob(r'/home/qcr/cgras_data/CameraCalibrate/*.JPG')
# images = images[:4]

path = '/home/qcr/cgras_data/CameraCalibrateOutput'
pathlib.Path(path).mkdir(parents=True, exist_ok=True) 

found = 0
for fname in images:  # Here, 10 can be changed to whatever number you like to choose
    print(fname)
    
    img = cv2.imread(fname) # Capture frame-by-frame
    #print(images[im_i])
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # cv2.imwrite('out.jpg', gray)
    # lwr = np.array([0, 0, 143])
    # upr = np.array([179, 61, 252])
    # hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    # msk = cv2.inRange(hsv, lwr, upr)
    # # Extract chess-board
    # krn = cv2.getStructuringElement(cv2.MORPH_RECT, (50, 30))
    # dlt = cv2.dilate(msk, krn, iterations=5)
    # res = 255 - cv2.bitwise_and(dlt, msk)
    # Find the chess board corners
    # ret, corners = cv2.findChessboardCornersSB(gray, (7,7), None)
    ret, corners = cv2.findChessboardCorners(gray, (7, 7),
                                         flags=cv2.CALIB_CB_ADAPTIVE_THRESH +
                                               cv2.CALIB_CB_FAST_CHECK +
                                               cv2.CALIB_CB_NORMALIZE_IMAGE)
    # If found, add object points, image points (after refining them)
    if ret == True:
        print('found chess board corners')
        objpoints.append(objp)   # Certainly, every loop objp is the same, in 3D.
        corners2 = cv2.cornerSubPix(gray,corners,(11,11),(-1,-1),criteria)
        imgpoints.append(corners2)
        # Draw and display the corners
        img = cv2.drawChessboardCorners(gray, (7,7), corners2, ret)
        found += 1
        #cv2.imshow('img', img)
        #cv2.waitKey(500)
        # if you want to save images with detected corners 
        # uncomment following 2 lines and lines 5, 18 and 19
        image_name = path + f'/{fname[-12:-4]}' + '.png'
        cv2.imwrite(image_name, img)

print("Number of images used for calibration: ", found)

# When everything done, release the capture
# cap.release()
cv2.destroyAllWindows()

# calibration
ret, mtx, dist, rvecs, tvecs = cv2.calibrateCamera(objpoints, imgpoints, img.shape[::-1], None, None)

# transform the matrix and distortion coefficients to writable lists
data = {'camera_matrix': np.asarray(mtx).tolist(),
        'dist_coeff': np.asarray(dist).tolist()}

# and save it to a file
with open("calibration_matrix.yaml", "w") as f:
    yaml.dump(data, f)
