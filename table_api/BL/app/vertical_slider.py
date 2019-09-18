"""
Created on Wed Aug 23 12:36:27 2018

@author: Rana
"""

import cv2
from functools import reduce

try:
    from magnet import get_cv_lines
except:
    from app.magnet import get_cv_lines

try:
    from app.ace_logger import Logging
except:
    from ace_logger import Logging

logging = Logging()
def club(word1, word2):
    '''
        calculate average word space in the document
        - sum all the spaces
        - take the average

        Args:
            ocrData (list): list of words json of the page

        Returns:
            float: average spacce between words
    '''

    word  = {}
    left = min(word1['left'],word2['left'])
    top = min(word1['top'],word2['top'])
    right = max(word1['right'],word2['right'])
    bottom = max(word1['bottom'],word2['bottom'])
    word['left'] = left
    word['right'] = right
    word['top'] = top
    word['bottom'] = bottom
    word['word']=word1['word']+word2['word']
    return word


def ocrDataLocal(T, L, R, B, ocrData):
    '''
        Returns that part of ocrdata which is confined within given boundaries

        Args:
            T (float): top boundary of ocr data local
            L (float): left boundary of ocr data local
            R (float): right boundary of ocr data local
            B (float): bottom boundary of ocr data local
            ocrData (list): list of words json of the page

        Returns:
            list: ocr data local
    '''

    ocrDataLocal = []
    for data in ocrData:
        if L <= data['left'] and data['right'] <= R and data['top'] \
            >= T and data['bottom'] <= B:
            ocrDataLocal.append(data)
    return ocrDataLocal


def get_word_space(ocrData):
    '''
        calculate average word space in the document
        - sum all the spaces
        - take the average

        Args:
            ocrData (list): list of words json of the page

        Returns:
            float: average spacce between words
    '''

    spaces = []
    for i in range(len(ocrData)-1):
        space = ocrData[i+1]['left'] - ocrData[i]['right']
        if(space>0 and space<100):
            spaces.append(space)

    avg_space = reduce(lambda x,y : x+y , spaces)/len(spaces)
    return avg_space


def convert_word_to_line_C(word, ws, vers_bounds, i, ocrData):
    '''
        convert a word into a sentence by using word space
        - looping through all the word_space
        - take the words which are in close proximty of the word left and right
        - club the words together to make a big word with inclusive boundaries

        Args:
            word (json):

        Returns:
            json: combined word with left and right neighbors included
    '''


    '''left increment'''
    flag = 1
    while(flag):
        flag = 0
        for data_ in ocrData:
            if((word['top']>=data_['top'] and word['top'] <=data_['bottom']) or (data_['top']>=word['top'] and data_['top'] <=word['bottom'])):
                diff = word['left']-data_['right']
                if(diff>0 and diff>=ws[0] and diff<=ws[1] and data_['right'] < vers_bounds[i+1][1]  and data_['left']>vers_bounds[i-1][0]):
                    flag = 1
                    word = club(word, data_)
    flag = 1
    '''right increment'''
    while(flag):
        flag = 0
        for data_ in ocrData:
            if((word['top']>=data_['top'] and word['top'] <=data_['bottom']) or (data_['top']>=word['top'] and data_['top'] <=word['bottom'])):
                diff = data_['left']-word['right']
                if(diff>0 and diff>=ws[0] and diff<=ws[1] and data_['right'] < vers_bounds[i+1][1]  and data_['right']<vers_bounds[i+1][0]):
                    flag = 1
                    word = club(word, data_)
    return word


def validating_cv_lines(ocrData, cv_verticals, header_list, header_column_wise_data, algorithm_lines, headerBottom, footer):
    '''
        calculate average word space in the document
        - sum all the spaces
        - take the average

        Args:
            ocrData (list): list of words json of the page

        Returns:
            float: average space between words
    '''

    ''' validation 1 : if the line falls in between of some header'''

    if cv_verticals:
        for header in header_column_wise_data:
            l = header['coords'][1]
            r = header['coords'][2]
            cv_verticals = [ver for ver in cv_verticals if(ver not in range(l,r+1))]

    ''' validation 2: if line intersect with any word from header top to footer of table '''

    if cv_verticals:
        for ver in cv_verticals:
            for data in ocrData:
                if(data['top'] in range(headerBottom,footer)):
                    cv_verticals = [ver for ver in cv_verticals if(ver not in range(data['left'],data['right']))]

    ''' validation 3: if line is shorter than required '''
    # discussion required

    ''' validation 4: if no data between two cv lines '''
    if cv_verticals:
        cv_new = []
        for i in range(len(cv_verticals)-1):
            l = cv_verticals[i]
            r = cv_verticals[i+1]
            ocrDataColumn = ocrDataLocal(headerBottom, l, r, footer, ocrData)
            if(len(ocrDataColumn)):
                cv_new.append(cv_verticals[i])
        cv_new.append(cv_verticals[-1])
        cv_verticals = cv_new

    ''' validation 5: if some cv line is not there : use algo lines '''
    if cv_verticals:
        cv_vers = []
        for i in range(len(header_column_wise_data)-1):
            l = int((header_column_wise_data[i]['coords'][2] + header_column_wise_data[i]['coords'][1])/2)
            r = int((header_column_wise_data[i+1]['coords'][1] + header_column_wise_data[i+1]['coords'][2])/2)
            algo_line = int((l+r)/2)
            for line in algorithm_lines:
                if(line in range(l-5,r+5)):
                    algo_line = line
                    break
            cv_line = -1
            for line in cv_verticals:
                if line in range(l,r):
                    cv_line = line
                    break
            if(cv_line == -1):
                cv_vers.append(algo_line)
            else:
                cv_vers.append(cv_line)
        cv_verticals = cv_vers
    else:
        cv_verticals = algorithm_lines
    cv_verticals = sorted(cv_verticals)
    return cv_verticals


def making_vers(header_column_wise_data, headerLeft, headerRight):
    '''
        making default vericals in the middle of the headers

        Args:
            header_column_wise_data (list): list of all the headers information
            headerLeft (float): left boundary of the headers
            headerRight (float): right boundary of the headers

        Returns:
            list, list
    '''

    vers = []
    vers_bounds = []
    for i in range(len(header_column_wise_data)-1):
        vers.append(int((header_column_wise_data[i]['coords'][2] + header_column_wise_data[i+1]['coords'][1])/2))
        vers_bounds.append([header_column_wise_data[i]['coords'][2],header_column_wise_data[i+1]['coords'][1]])
    return vers, vers_bounds


def correcting_verticals(ocrData, headerLeft, headerRight, headerBottom, headerTop, footer, header_list, header_column_wise_data, avg_space, img=None):
    '''
        correcting the default verticals made by making vers
        - loop though the lines
        - check if any one of them touches any word in ocr data
        - of it does calculate weather to move right or left and by how much
        - move the line to its correct place
        - check again untill all the words and gone through

        Args:
            ocrData (list): list of words json of the page
            headerLeft (float): left boundary of the headers
            headerRight (float): right boundary of the headers
            headerBottom (float): bottom boundary of the headers
            headerTop (float): top boundary of the headers
            footer (float): footer of table
            header_list (list): list of header data from database
            header_column_wise_data (list): list of all the headers information
            avg_space (float):
            img (numpy array)

        Returns:
            list: list of corrected verticals
    '''

    '''making vers'''

    vers, vers_bounds = making_vers(header_column_wise_data,
                        headerLeft,
                        headerRight)

    '''correctng vers'''

    ws = [0,avg_space]
    for i in range(len(vers)-1):
        ver = vers[i]
        avg = ver
        left_shift_array = []
        right_shift_array = []
        for data in ocrData:
            if(data['bottom']<footer and data['top']>=headerBottom):
                if((avg >= data['left'] and data['right'] >= avg)
                    or (abs(avg-data['left'])<=ws[1]/2)
                    or (abs(avg-data['right'])<=ws[1]/2)):
                    dataShift = convert_word_to_line_C(data,
                                ws,
                                vers_bounds,
                                i,
                                ocrData)

                    if(dataShift['left']<vers_bounds[i][0]
                        or (avg-dataShift['left'])>(dataShift['right']-avg)):
                        '''shift right'''
                        R = min(dataShift['right'],vers_bounds[i][1])
                        add = R-avg
                        if(R != dataShift['right']):
                            vers[i] = vers[i] + add + 2
                        else:
                            vers[i] = vers[i] + add + 2

                    elif(dataShift['right']>vers_bounds[i][1]
                        or (avg-dataShift['left'])<(dataShift['right']-avg)):
                        '''shift left'''
                        L = max(dataShift['left'],vers_bounds[i][0])
                        add = avg-L
                        if(L != dataShift['left']):
                            vers[i] = vers[i] - add + 2
                        else:
                            vers[i] = vers[i] - add -2
                    avg = int(vers[i])
    algorithm_lines = []
    for ver in vers:
        avg = int(ver)
        algorithm_lines.append(avg)
    return algorithm_lines


def vertical_slider(img,rf,header_column_wise_data,ocrData,headerLeft,headerRight,headerBottom,headerTop,footer,header_list,word_space, I = None):
    '''
        calculate average word space in the document
        - sum all the spaces
        - take the average

        Args:
            img (numpy array): image for cv lines detection
            rf (float): resize factor
            header_column_wise_data (list):
            ocrData (list): list of words json of the page
            headerLeft (float):
            headerRight (float):
            headerBottom (float):
            headerTop (float):
            footer (float):
            header_list (list):
            word_space (float):
            I (numpy array): image

        Returns:
            list: list of verticals lines
    '''

    algorithm_lines = correcting_verticals(ocrData,
                    headerLeft,
                    headerRight,
                    headerBottom,
                    headerTop,
                    footer,
                    header_list,
                    header_column_wise_data,
                    word_space)
    hors, cv_verticals = get_cv_lines(img,rf)
    vertical_lines = []

    '''validating open cv lines'''
    if(len(cv_verticals)>2):
        vertical_lines = validating_cv_lines(ocrData,
                        cv_verticals,
                        header_list,
                        header_column_wise_data,
                        algorithm_lines,
                        headerBottom,
                        footer)
    else:
        vertical_lines = algorithm_lines

    header_verticals = []
    for ver in vertical_lines:
        avg = int(ver)
        header_verticals.append([[int(avg),int(headerTop)],[int(avg),int(headerBottom)]])
    return header_verticals
