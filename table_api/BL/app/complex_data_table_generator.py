import cv2
import numpy as np
import pandas as pd

from operator import itemgetter
from PIL import Image
try:
    from app.ace_logger import Logging
except:
    from ace_logger import Logging

logging = Logging().getLogger('ace')

def pre_process_centroids(centroids):

    centroids_xSortT = sorted(centroids, key=itemgetter(0))
    centroids_ySortT = sorted(centroids, key=itemgetter(1))

    centroids_xSort = []
    for tup in centroids_xSortT:
        L = list(tup)
        centroids_xSort.append(L)
    for i in range(len(centroids_xSort)):
        last = centroids_xSort[i][0]
        while(i< len(centroids_xSort) and abs(centroids_xSort[i][0]-last)<= 3):
            centroids_xSort[i][0] = last
            i = i+1


    centroids_ySort = []
    for tup in centroids_ySortT:
        L = list(tup)
        centroids_ySort.append(L)
    for i in range(len(centroids_ySort)):
        last = centroids_ySort[i][1]
        while(i< len(centroids_ySort) and abs(centroids_ySort[i][1]-last)<= 3):
            centroids_ySort[i][1] = last
            i = i+1

    centroidsMatrix = []

    i = 0
    while(i < len(centroids_ySort)):
        tempList = []
        j = i
        while(j<len(centroids_ySort)-1 and (centroids_ySort[j][1]==centroids_ySort[j+1][1])):
            if((centroids_ySort[j][1]==centroids_ySort[j+1][1])):
                tempList.append(centroids_ySort[j])
                j=j+1
                i = j-1
            else:
                j=j+1

        i = i+1
        if(len(tempList)>0):
            tempList.append(centroids_ySort[j])
            centroidsMatrix.append(tempList)

    centroidsMatrixLevel = []
    i = 0
    while(i < len(centroids_ySort)):
        tempList = []
        j = i
        while(j<len(centroids_ySort)-1 and (centroids_ySort[j][0]==centroids_ySort[j+1][0])):
            if((centroids_ySort[j][0]==centroids_ySort[j+1][0])):
                tempList.append(centroids_ySort[j])
                j=j+1
                i = j-1
            else:
                j=j+1

        i = i+1
        if(len(tempList)>0):
            tempList.append(centroids_ySort[j])
            centroidsMatrixLevel.append(tempList)

    return centroidsMatrix,centroidsMatrixLevel


def sortMatrix(centroidsMatrix):
    i =0
    while(i<len(centroidsMatrix)):
        centroidsMatrix[i] = sorted(centroidsMatrix[i], key=itemgetter(0))
        i=i+1
    return centroidsMatrix


def check_points(centroidsMatrix, l, r, horizontal_lines=None, vertical_lines=None, img=None):
    horizontal_lines = sorted(horizontal_lines, key = lambda x : x[0][1])
    if(horizontal_lines):
        for h in horizontal_lines:
            lx = l[0]
            rx = r[0]
            hx1 = h[0][0]
            hx2 = h[1][0]
            if(set(range(lx,rx)).intersection(set(range(hx1,hx2))) == set(range(lx, rx)) and abs(l[1] - h[0][1]) < 2):
                return True
    return False


def findRect(centroidsMatrix, i, j, horizontal_lines=None, vertical_lines=None, img=None):
    rect = []
    row = i + 1
    flag = False
    while(row < len(centroidsMatrix)):
        col = 0
        while(col<len(centroidsMatrix[row])-1):
            col2 = col+1
            while(col2<len(centroidsMatrix[row])):
                if(abs(centroidsMatrix[row][col][0]-centroidsMatrix[i][j][0])<=2 and abs(centroidsMatrix[row][col2][0]-centroidsMatrix[i][j+1][0])<=2):
                    if(horizontal_lines is not None):
                        # if(check_points(centroidsMatrix, centroidsMatrix[row][col], centroidsMatrix[row][col2], horizontal_lines, vertical_lines, img)):
                        flag=True
                        rect = [centroidsMatrix[i][j][0],centroidsMatrix[i][j][1],centroidsMatrix[row][col2][0],centroidsMatrix[row][col2][1]]
                        break
                    else:
                        flag=True
                        rect = [centroidsMatrix[i][j][0],centroidsMatrix[i][j][1],centroidsMatrix[row][col2][0],centroidsMatrix[row][col2][1]]
                        break
                col2 = col2+1
            col = col+1
        if(flag==True):
            break
        row = row+1

    if(flag==True):
        return rect
    else:
        return None


def makeRectanglesNew(centroidsMatrix, L, R, horizontal_lines=None, vertical_lines=None, img=None):
    rectangles = []
    i = 0


    if(centroidsMatrix):
        while(i<(len(centroidsMatrix)-1)):
        # while(i<1):
            j=0
            # centroidsMatrix[i] = sorted(centroidsMatrix[i], key=itemgetter(0))
            while(j<len(centroidsMatrix[i])-1):
                if(centroidsMatrix[i][j][0]<=R):
                    rect = findRect(centroidsMatrix, i, j, horizontal_lines, vertical_lines, img)
                    # print('rectangle is ',rect)
                    if(rect is not None):
                        rectangles.append(rect)
                        coords = rect
                        # if(img is not None):
                            # img_ = img
                            # w,h,c = img_.shape
                            # rf = 670/int(h)
                            # img_ = cv2.resize(img_, (0,0), fx=rf, fy=rf)
                            # cv2.rectangle(img_,(coords[0],coords[1]),(coords[2],coords[3]),(0, 0, 255),2)
                            # cv2.namedWindow('rects',cv2.WINDOW_NORMAL)
                            # cv2.resizeWindow('rects', 1200,1200)
                            # cv2.imshow('rects',img_)
                            # cv2.waitKey(0)
                        # print('rectangle is ',rect)
                        # cv2.rectangle(img, (rect[0], rect[1]), (rect[2], rect[3]), (255,0,0), 2)
                    j= j+1
            i= i+1
    return rectangles


def LR(centroids):
    R = 0
    L = 10000
    for cen in centroids:
        if(cen[0]>R):
            R = cen[0]
        if(cen[0]<L):
            L = cen[0]
    return L,R


def colspanArrayFunc(centroidsMatrix):
    array = []
    for i in range(len(centroidsMatrix)):
        for j in range(len(centroidsMatrix[i])):
            array.append(centroidsMatrix[i][j][0])
    array = list(set(array))
    return array


def rowspanArrayFunc(centroidsMatrix):
    rowspanArray = []
    for i in range(len(centroidsMatrix)):
        rowspanArray.append(centroidsMatrix[i][0][1])
    return rowspanArray


def count(l, r, t, b, rowspanArray, colspanArray):
    rowspan = 0
    for i in range(len(rowspanArray)):
        if(rowspanArray[i]>t and rowspanArray[i]<b):
            rowspan = rowspan + 1
    colspan = 0
    for j in range(len(colspanArray)):
        if(colspanArray[j]>l and colspanArray[j]<r):
            colspan = colspan + 1
    return rowspan+1, colspan+1


def colsRowSpanNewest(rectangles, centroidsMatrix, rowspanArray, colspanArray,ocr_page):
    h_thresh = 0
    v_thresh = 0
    cropsData = []
    idx = 0
    for rect in rectangles:
        temp = ""
        box_l = rect[0] - h_thresh
        box_r = rect[2] + h_thresh
        box_t = rect[1] - v_thresh
        box_b = rect[3] + v_thresh

        target_words_data = []
        for i in range(len(ocr_page)-1):
            word_l = ocr_page[i]['left']
            word_r = ocr_page[i]['left'] + ocr_page[i]['width']

            word_t = ocr_page[i]['top']
            word_b = ocr_page[i]['top'] + ocr_page[i]['height']

            '''abhishek's shit'''
            # if (box_l < word_r and word_l < box_r) and (box_t < word_b and word_t < box_b):
            #     temp += ' ' + (i['word'])
            '''priyatham's brilliant stuff'''
            if (word_l > box_l-0.5*(ocr_page[i]['width']) and word_r < box_r + 0.5*(ocr_page[i]['width'])
                and (box_t < word_b and word_t < box_b)):
                target_words_data.append(ocr_page[i])
                if int(ocr_page[i]['confidence']) < 100:
                    # temp += ' '+'suspicious'+ocr_page[i]['word']
                    temp += ' '+ocr_page[i]['word']
                else:
                    temp += ' '+ocr_page[i]['word']
        if len(target_words_data):
            bound_t =   min(target_words_data, key = lambda x : x['top'])['top']
            bound_l =   min(target_words_data, key = lambda x : x['left'])['left']
            bound_r =   max(target_words_data, key = lambda x : x['right'])['right']
            bound_b =   max(target_words_data, key = lambda x : x['bottom'])['bottom']
        else:
            bound_t, bound_l, bound_r, bound_b = -1, -1, -1, -1
        cropsData.append([temp,[bound_t, bound_l, bound_r , bound_b]])
        idx = idx+1
    idx = 0
    M = []
    row_bounds = []
    for i in range(len(centroidsMatrix)-1):
        row = []
        for j in range(len(centroidsMatrix[i])-1):
            if(idx<len(rectangles)):
                rect = rectangles[idx]
                rect[0] = rect[0]+3
                rect[1] = rect[1]+3
                rect[2] = rect[2]-3
                rect[3] = rect[3]-3
                rect = tuple(rect)

                l = rect[0]
                r = rect[2]
                t = rect[1]
                b = rect[3]
                rowspan,colspan = count(l, r, t, b, rowspanArray, colspanArray)
                result = cropsData[idx][0]
                word_bound = cropsData[idx][1]
                row.append([result,rowspan,colspan,rect, word_bound])
                idx=idx+1
        temp_bound = []
        max_dist = 0
        for i in range(len(row)):
            dist = abs(row[i][4][0] - row[i][4][3])
            if(dist > max_dist):
                max_dist = dist
                temp_bound = [row[i][4][0], row[i][4][3]]
        row_bounds.append([row[-1][4][0], row[-1][4][3]])
        M.append(row)
    return M, row_bounds


def crop(coordinates, original_image):
    i = 0
    img_array = []
    original_image = Image.fromarray(original_image)
    for val in coordinates:
        left = val[0]
        top = val[1]
        right = left+val[2]
        bottom = top+val[3]

        crop_rectangle = (left, top, right, bottom)
        cropped_im = original_image.crop(crop_rectangle)
        img_array.append(cropped_im)
        i=i+1
    return img_array


def required_columns(data, rectangles, req_cols, centroidsMatrix):
    req_data = []
    req_ranges = []
    header_rects = data[0]

    for col in req_cols:

        try:
            req_ranges.append([header_rects[col-1][3][0]-5,header_rects[col-1][3][2]+5])
        except Exception as e:
            logging.exception(f'Exception in Required Columns: {e}')

    for i in range(len(data)):
        temp_row = []
        for j in range(len(data[i])):
            rect = data[i][j]
            for Range in req_ranges:
                if(rect[3][0]>=Range[0] and rect[3][2]<=Range[1]):
                    temp_row.append(rect[:3])
                    break
        req_data.append(temp_row)
    return req_data


def complex_data_table_generator(ocr_page, intersection_points,req_cols=None, horizontal_lines=None, vertical_lines=None, img=None,subheader=None, nested=None):
    centroids = []
    for i in range(len(intersection_points)):
        centroids.append(intersection_points[i])

    centroidsMatrix, centroidsMatrixLevel = pre_process_centroids(centroids)
    centroidsMatrix = sortMatrix(centroidsMatrix)
    L,R = LR(centroids)
    for i in range(len(centroidsMatrix)):
        k = 0
        for j in range(1,len(centroidsMatrix[i])):
            j = j+k
            if(abs(centroidsMatrix[i][j-1][0]-centroidsMatrix[i][j][0])<2):
                centroidsMatrix[i].pop(j)
                k = k-1

    try:
        if(nested is not None):
            first = centroidsMatrix[1][0][1]
            for p in range(1,len(centroidsMatrix[1])):
                centroidsMatrix[1][p][1] = first
    except:
        pass

    rectangles = makeRectanglesNew(centroidsMatrix, L, R, horizontal_lines, vertical_lines, img)
    l = centroidsMatrix[0][0][0]
    t = centroidsMatrix[0][0][1]
    b = centroidsMatrix[len(centroidsMatrix)-1][0][1]
    r = centroidsMatrix[len(centroidsMatrix)-1][len(centroidsMatrix[len(centroidsMatrix)-1])-1][0]
    rowspanArray = rowspanArrayFunc(centroidsMatrix)
    colspanArray = colspanArrayFunc(centroidsMatrix)
    data, row_bounds = colsRowSpanNewest(rectangles, centroidsMatrix, rowspanArray, colspanArray, ocr_page)

    if req_cols:
        data = required_columns(data, rectangles, req_cols, centroidsMatrix)
    else:
        data_new = []
        for row in data:
            R = []
            for box in row:
                R.append(box[:3])
            data_new.append(R)
        data = data_new

    if subheader:
        return data, row_bounds
    return data
