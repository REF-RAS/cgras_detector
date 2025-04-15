# Copyright 2024 - Andrew Kwok Fai LUI, 
# Robotics and Autonomous Systems Group, REF, RI
# and the Queensland University of Technology

__author__ = 'Andrew Lui'
__copyright__ = 'Copyright 2024'
__license__ = 'GPL'
__version__ = '1.0'
__email__ = 'ak.lui@qut.edu.au'
__status__ = 'Development'

import os, math, yaml, numbers, pickle
from enum import Enum
import numpy as np
import cv2

import matplotlib.pyplot as plt


class RecoErrorCorrection():
    TRAINING_DATA_FILE = os.path.join(os.path.dirname(__file__), 'reco_error/error_correct_training.txt')
    def __init__(self):
        model_X_x = []
        model_X_y = []
        model_Y_x = []
        model_Y_y = []
        with open(RecoErrorCorrection.TRAINING_DATA_FILE, 'r') as infile:
            for line in infile:
                if line:
                    value_list = line.split('\t')
                    model_X_x.append(int(value_list[0]))
                    model_X_y.append(int(value_list[2]))
                    model_Y_x.append(int(value_list[1]))
                    model_Y_y.append(int(value_list[3]))
        model_X_z = np.polyfit(np.array(model_X_x), np.array(model_X_y), 2)
        model_Y_z = np.polyfit(np.array(model_Y_x), np.array(model_Y_y), 2)
        self.model_X = np.poly1d(model_X_z)
        self.model_Y = np.poly1d(model_Y_z)

    def predict_error_X(self, value:float):
        return self.model_X(value)

    def predict_error_Y(self, value:float):
        return self.model_Y(value) 

    def predict_error_point(self, point:tuple):
        if point is None or type(point) not in (tuple, list) or len(point) != 2:
            raise AssertionError(f'RecoErrorCorrection: Parameter (point) is not a 2-tuple')
        return (self.model_X(point[0]), self.model_Y(point[1]))
    
    def plot(self):
        xp = np.linspace(0, 26000, 100)
        _ = plt.plot(xp, self.model_X(xp), '-')
        plt.ylim(0,300)
        plt.show()

if __name__ == '__main__':
    rec = RecoErrorCorrection()
    for x in range(800, 20000, 1000):
        print(x, rec.predict_error_X(x))
    rec.plot()