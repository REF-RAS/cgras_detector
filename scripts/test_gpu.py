#!/usr/bin/env python3

# Copyright 2025 - Andrew Kwok Fai LUI, 
# Robotics and Autonomous Systems Group, REF, RI
# and the Queensland University of Technology

__author__ = 'Andrew Lui'
__copyright__ = 'Copyright 2025'
__license__ = 'GPL'
__version__ = '1.0'
__email__ = 'ak.lui@qut.edu.au'
__status__ = 'Development'

import torch

if torch.cuda.is_available():
    print('CUDA is available')
    device_count = torch.cuda.device_count()
    print(f'device_count: {device_count}')
    print(f'current_device: {torch.cuda.current_device()}')
    for index in range(device_count):
        print(f'device: {torch.cuda.device(index)}')
        print(f'get_device_name: {torch.cuda.get_device_name(index)}')

else:
    print('CUDA is not available')