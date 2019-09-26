import cv2
import sys
from functools import reduce
import numpy as np
import statistics

try:
    from app.ace_logger import Logging
except:
    from ace_logger import Logging

logging = Logging().getLogger('ace')

def get_histogram(img,type):
    histogram = np.sum(img[:,:], axis=type)
    logging.debug(img.shape)
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


def get_cv_lines(src_img, rf, scale = 5):
    try:
        w,h,c = src_img.shape
        # rf = 670/int(h)
        line_width = 5
        kernel = np.ones((2,2), np.uint8)
        src_img = cv2.erode(src_img, kernel, iterations=1)

        if len(src_img.shape) == 2:
            gray_img = src_img
        elif len(src_img.shape) ==3:
            gray_img = cv2.cvtColor(src_img, cv2.COLOR_BGR2GRAY)

        # thresh_img = gray_img
        thresh_img = cv2.adaptiveThreshold(~gray_img,255,cv2.ADAPTIVE_THRESH_GAUSSIAN_C ,cv2.THRESH_BINARY,15,-2)
        h_img = thresh_img.copy()
        v_img = thresh_img.copy()

        # scale = 5

        h_size = int(h_img.shape[1]/scale)
        h_structure = cv2.getStructuringElement(cv2.MORPH_RECT,(h_size,1))
        h_erode_img = cv2.erode(h_img,h_structure,1)
        h_dilate_img = cv2.dilate(h_erode_img,h_structure,1)

        v_size = int(v_img.shape[0] / scale)
        v_structure = cv2.getStructuringElement(cv2.MORPH_RECT, (1, v_size))
        v_erode_img = cv2.erode(v_img, v_structure, 1)
        v_dilate_img = cv2.dilate(v_erode_img, v_structure, 1)

        mask_img = v_dilate_img + h_dilate_img
        # cv2.namedWindow('Mask',cv2.WINDOW_NORMAL)
        # cv2.resizeWindow('Mask', 2000,700)
        # cv2.imshow('Mask',mask_img)
        # cv2.waitKey(0)
        # cv2.destroyAllWindows()

        ver_histogram = get_histogram(v_dilate_img, 0)
        hor_histogram = get_histogram(h_dilate_img, 1)

        try:
            vers = hist_to_lines(ver_histogram)
        except:
            logging.debug('No verticals found')
            logging.exception('')
            vers = []
        try:
            hors = hist_to_lines(hor_histogram)
        except:
            logging.debug('No horizontal lines')
            logging.exception('')
            hors = []

        logging.debug(f'{hors},{vers}')

        for ver in vers:
            cv2.line(src_img,(ver,0),(ver,4000),(0,0,255),2)
            # print('Drawwing vertical_lines')
        for hor in hors:
            cv2.line(src_img,(0,hor),(4000,hor),(213,0,255),2)

        # cv2.namedWindow('cv_lines',cv2.WINDOW_NORMAL)
        # cv2.resizeWindow('cv_lines', 1000,700)
        # cv2.imshow('cv_lines',src_img)
        # cv2.waitKey(0)
        # cv2.destroyAllWindows()
        # plt.plot(ver_histogram)
        # plt.plot(hor_histogram)
        # plt.show()
        vers = [int(ver*rf) for ver in vers]
        hors = [int(hor*rf) for hor in hors]
        # print('vers',vers)
        return hors,vers
    except Exception as e:
        logging.exception(f'Error on line {sys.exc_info()[-1].tb_lineno},{type(e).__name__} , {e}')
        return [],[]
