import cv2
import numpy as np
from functools import reduce
import matplotlib.pyplot as plt
import statistics
try:
    from app.ace_logger import Logging
except:
    from ace_logger import Logging

logging = Logging()


def get_histogram(img,type):
    histogram = np.sum(img[:,:], axis=type)
    logging.debug(f'{img.shape}')
    return histogram


def normalise(histogram,thres):
    normalised = []
    k=0
    for i in range(len(histogram)-1):
        i = k
        idx = i+1
        normalised.append(histogram[i])
        try:
            while(int(abs(histogram[idx] - histogram[i])) < thres):
                normalised.append(histogram[i])
                idx += 1
            k = idx
        except Exception as e:
            logging.exception(f'{e}')
            break
    return normalised

def hist_to_lines(histogram):
    hist_lines = []
    lines = []
    start = 0
    for i in range(len(histogram)-1):
        if histogram[i] == 0 and histogram[i+1] != 0:
            hist_lines.append(i)
            start = i
        elif histogram[i] != 0 and histogram[i+1] == 0:
            hist_lines.append(int(sum([histogram[i] for i in range(start,i+1)])/(i+1-start)))
            hist_lines.append(i)
            lines.append(hist_lines)
            hist_lines = []

    average_line_height = int(sum([line[1] for line in lines])/len(lines))
    heights = [line[1] for line in lines]
    vers_cv = [int((line[0]+line[2])*0.5) for line in lines if line[1]>=0.25*average_line_height]

    return vers_cv

def get_cv_lines(src_img,rf=None,scale = 6.5):
    w,h = src_img.shape
    line_width = 5
    kernel = np.ones((2,2), np.uint8)
    src_img = cv2.erode(src_img, kernel, iterations=1)

    if len(src_img.shape) == 2:
        gray_img = src_img
    elif len(src_img.shape) ==3:
        gray_img = cv2.cvtColor(src_img, cv2.COLOR_BGR2GRAY)

    thresh_img = cv2.adaptiveThreshold(~gray_img,255,cv2.ADAPTIVE_THRESH_GAUSSIAN_C ,cv2.THRESH_BINARY,15,-2)
    h_img = thresh_img.copy()
    v_img = thresh_img.copy()

    h_scale = 10
    h_size = int(h_img.shape[1]/h_scale)
    h_structure = cv2.getStructuringElement(cv2.MORPH_RECT,(h_size,1))
    h_erode_img = cv2.erode(h_img,h_structure,1)
    h_dilate_img = cv2.dilate(h_erode_img,h_structure,1)

    v_size = int(v_img.shape[0] / scale)
    v_structure = cv2.getStructuringElement(cv2.MORPH_RECT, (1, v_size))
    v_erode_img = cv2.erode(v_img, v_structure, 1)
    v_dilate_img = cv2.dilate(v_erode_img, v_structure, 1)

    mask_img = v_dilate_img + h_dilate_img
    ver_histogram = get_histogram(v_dilate_img,0)
    hor_histogram = get_histogram(h_dilate_img,1)

    try:
        vers = hist_to_lines(ver_histogram)
    except:
        logging.debug('No verticals found')
        vers = []
    try:
        hors = hist_to_lines(hor_histogram)
    except:
        logging.debug('No horizontal lines')
        hors = []
    return hors,vers
