"""
Created on Wed Aug 23 12:36:27 2018

@author: abhishek and priyatham
"""

# -*- coding: utf-8 -*-
import pymysql
import re
import cv2
import itertools
import json
import ast
import math
import copy
import numpy as np
import os, time, sys
from functools import reduce
from difflib import SequenceMatcher
from PIL import Image as PI
# from wand.image import Image as WI
# from wand.image import Color
from pdf2image import convert_from_path

try:
    from app.ace_logger import Logging
    from app.find_intersections import find_intersections
    from app.complex_data_table_generator import complex_data_table_generator
    from app.subtable_helper import subtable_helper
    from app.exceptions import header_exceptions, footer_exceptions
    from app.magnet import get_cv_lines
    from app.vertical_slider import vertical_slider
    from app.vertical_slider import get_word_space
    from app.field_mapping import field_mapping
except:
    from ace_logger import Logging
    from find_intersections import find_intersections
    from complex_data_table_generator import complex_data_table_generator
    from subtable_helper import subtable_helper
    from exceptions import header_exceptions, footer_exceptions
    from magnet import get_cv_lines
    from vertical_slider import vertical_slider
    from vertical_slider import get_word_space
    from field_mapping import field_mapping

try:
    with open('app/parameters.json') as f:
        parameters = json.loads(f.read())
except:
    with open('parameters.json') as f:
        parameters = json.loads(f.read())

logging = Logging()

ANALYST_DATABASE = parameters['database_name']
# DEFAULT_IMGPATH = parameters['ui_folder'] + 'assets/images/invoices/'
# DEFAULT_IMGPATH = parameters['ui_folder'] + 'images/invoices/'
DEFAULT_IMGPATH = parameters['default_image_path']


def execute_query(sql, database=ANALYST_DATABASE):
    data = None
    conn = pymysql.connect(host='172.31.45.112', user='root', password='', db=database)
    try:
        a = conn.cursor()
        a.execute(sql)
        data = a.fetchall()
        conn.commit()
    except Exception as e:
        # #pass#print("exception")
        # #pass#print(e)
        # logger.error('Sql Error!!! \n check query\n {}'.format(sql))
        conn.rollback()
    conn.close()
    return data


def club(word1, word2):
    '''
    Parameters : two words to be clubbed
    Output     : Clubbed Word
    '''
    word = {}
    left = min(word1['left'], word2['left'])
    top = min(word1['top'], word2['top'])
    right = max(word1['right'], word2['right'])
    bottom = max(word1['bottom'], word2['bottom'])
    word['left'] = left
    word['right'] = right
    word['top'] = top
    word['bottom'] = bottom
    word['word'] = word1['word'] + word2['word']
    return word


def split_lines(L, R, T, B, ocrDataColumn):
    '''
        Parameters : L,R,T,B,Boundaries of ocrdata based on which horizontal lines are drawn
        Output     : Returns Horizontal Lines

    '''
    i = 0
    # make single line data separate
    while (i < len(ocrDataColumn) - 1):
        data = ocrDataColumn[i]
        data2 = ocrDataColumn[i + 1]
        if ((data['top'] >= data2['top'] and data['top'] <= data2['bottom']) or (
                data2['top'] >= data['top'] and data2['top'] <= data['bottom'])):
            word = club(data, data2)
            ocrDataColumn[i] = word
            ocrDataColumn.pop(i + 1)
            i = i - 1
        i = i + 1

    numberOfRows = len(ocrDataColumn)

    h_lines = []
    horizontal_lines = []
    if numberOfRows > 1:
        i = 1
        while i < len(ocrDataColumn):
            data = ocrDataColumn[i]
            h_lines.append(int(data['top'] - 2))
            i = i + 1

    for i in range(len(h_lines)):
        h = h_lines[i]
        horizontal_lines.append([[L, h], [R, h]])

    return horizontal_lines


def split_lines_alignment(L, R, T, B, ocrDataColumn, alignment):
    '''
        Parameters : L,R,T,B,Boundaries of ocrdata based on which horizontal lines are drawn
        Output     : Returns Horizontal Lines

    '''
    i = 0
    # make single line data separate
    # while(i<len(ocrDataColumn)-1):
    #     data = ocrDataColumn[i]
    #     data2 = ocrDataColumn[i+1]
    #     if((data['top']+2>=data2['top']+2 and data['top']+2 <=data2['bottom']-2) or (data2['top']+2>=data['top']+2 and data2['top']+2 <=data['bottom']-2)):
    #         word = club(data,data2)
    #         ocrDataColumn[i] = word
    #         ocrDataColumn.pop(i+1)
    #         i = i-1
    #     i=i+1
    lines_column = return_lines(ocrDataColumn)
    ocrDataColumn = [line[0] for line in lines_column]
    logging.debug(f'clubbed lines:{ocrDataColumn}')
    numberOfRows = len(ocrDataColumn)

    h_lines = []
    horizontal_lines = []
    if numberOfRows > 1:
        i = 1
        while i < len(ocrDataColumn):
            data = ocrDataColumn[i]
            if alignment == 'top':
                h_lines.append(int(data['top'] - 2))
            elif alignment == 'bottom':
                h_lines.append(int(data['bottom'] + 2))

            i = i + 1

    for i in range(len(h_lines)):
        h = h_lines[i]
        horizontal_lines.append([[L, h], [R, h]])

    return horizontal_lines


def ocrDataLocal(T, L, R, B, ocrData):
    '''
        Parameters : Boundaries of Scope
        Output     : Returns that part of ocrdata which is confined within given boundaries
    '''
    ocrDataLocal = []
    for data in ocrData:
        if (data['left'] + int(0.25 * data['width']) >= L
                and data['right'] - int(0.25 * data['width']) <= R
                and data['top'] + int(0.5 * data['height']) >= T and data['bottom'] - int(0.5 * data['height']) <= B):
            ocrDataLocal.append(data)
    return ocrDataLocal


def clean_word(string):
    string = ' '.join([''.join(e for e in word if e.isalnum() or e == '#' or e == '%') for word in string.split()])
    string = string.lower()
    return string


def get_header_data(v_lines, ocrData, headerTop, headerLeft, headerRight, headerBottom):
    '''
        Parameters : ocrdata ,vertical lines of header and header boundaries
        Output     : Return ocr data of header
    '''
    header_data = []
    for i in range(1, len(v_lines)):
        T = headerTop
        L = v_lines[i - 1][0][0]
        R = v_lines[i][0][0]
        B = headerBottom
        col_header_data = ocrDataLocal(T, L, R, B, ocrData)
        header_data.append(col_header_data)
    return header_data


def line_moving_method(L, R, i, header_data, vertical_lines, horizontal_lines, headerBottom):
    tempR = R
    tempL = L
    # logger.debug('i am header data {}'.format(header_data))
    header_right_bound = header_data[i + 1][0]['left']
    header_left_bound = header_data[i - 1][-1]['right']
    # right shift
    while (tempR < header_right_bound):
        T = headerBottom
        L = tempL
        R = tempR
        B = horizontal_lines[2][0][1]
        ocrDataBox = ocrDataLocal(T, L, R, B, ocrData)
        for word in ocrDataBox:
            if (word['left'] <= tempR and word['right'] >= tempR and word['right'] < header_right_bound):
                tempR = word['right']
        tempR += 1
    # left shift
    while (tempL > header_left_bound):
        T = headerBottom
        L = tempL
        R = tempR
        B = horizontal_lines[2][0][1]
        ocrDataBox = ocrDataLocal(T, L, R, B, ocrData)
        for word in ocrDataBox:
            if (word['right'] >= tempR and word['left'] <= tempL and word['left'] > header_left_bound):
                tempL = word['left']
        tempL -= 1
    return int(L), int(R)


def column_nature_validation(ocrData, json_data, vertical_lines, horizontal_lines, header_data, headerBottom, footer):
    label_type = []
    for k, v in json_data.items():
        if (k.startswith('v') and '.' not in k):
            label_type.append((v['label'], v['type']))

    for i, eachlabel in enumerate(label_type):
        label = eachlabel[0]
        type = eachlabel[1]
        T = int(headerBottom)
        L = int(vertical_lines[i][0][0])
        R = int(vertical_lines[i + 1][0][0])
        # find the next line that is greater than the header bottom
        B = footer
        for line in horizontal_lines:
            if (headerBottom < line[0][1]):
                B = int(line[0][1])
                break
        ocrDataColumn = ocrDataLocal(T, L, R, B, ocrData)
        cell_value = ""
        for data in ocrDataColumn:
            cell_value += data['word'].lower() + ' '
        if type == 'number':
            if (len(cell_value) == 0):
                try:
                    L, R = line_moving_method(L, R, i, header_data, vertical_lines, horizontal_lines, headerBottom)
                except:
                    pass  # print('cell value not detected')

                vertical_lines[i][0][0] = L
                vertical_lines[i][1][0] = L
                vertical_lines[i + 1][0][0] = R
                vertical_lines[i + 1][1][0] = R
    '''
    1.check what is the nature of column
    2.check that nature data is there or not
    3.if there no need to validate
    4.if not - function - lines moving method
    '''
    return horizontal_lines, vertical_lines


def suffix_validation(ocrData, json_data, vertical_lines, horizontal_lines, header_data, headerBottom):
    suffixes = []
    for k, v in json_data.items():
        if (k.startswith('v')):
            suffixes.append(v['suffix'])

    for i, each_suffix in enumerate(suffixes):
        if each_suffix:
            T = horizontal_lines[1][0][1]
            L = vertical_lines[i][0][0]
            R = vertical_lines[i + 1][0][0]
            B = horizontal_lines[2][0][1]
            try:
                ocrDataColumn = ocrDataLocal(T, L, R, B, ocrData)
                cell_value = ocrDataColumn[0]['word']
                if (cell_value.endswith(each_suffix) == False):
                    L, R = line_moving_method(L, R, i, header_data, vertical_lines, horizontal_lines, headerBottom)
            except Exception as e:
                pass  # print(i,e)
    return horizontal_lines, vertical_lines


def prefix_validation(ocrData, json_data, vertical_lines, horizontal_lines, header_data, headerBottom):
    prefixes = []
    for k, v in json_data.items():
        if (k.startswith('v')):
            prefixes.append(v['prefix'])

    for i, each_prefix in enumerate(prefixes):
        if each_prefix:
            T = headerBottom
            L = vertical_lines[i][0][0]
            R = vertical_lines[i + 1][0][0]
            B = horizontal_lines[2][0][1]
            try:
                ocrDataColumn = ocrDataLocal(T, L, R, B, ocrData)
                cell_value = ocrDataColumn[0]['word']
                if (bool(cell_value.startswith(each_prefix)) == False):
                    L, R = line_moving_method(L, R, i, header_data, vertical_lines, horizontal_lines, headerBottom)
            except Exception as e:
                pass  # print(i,e)
    return vertical_lines, horizontal_lines


def sort_ocr(data):
    data = sorted(data, key=lambda i: i['top'])
    for i in range(len(data) - 1):
        if abs(data[i]['top'] - data[i + 1]['top']) < 6:
            data[i + 1]['top'] = data[i]['top']
    data = sorted(data, key=lambda i: (i['top'], i['left']))
    return data


def return_lines(temp):
    '''
        Parameters : ocrData
        Output     : Returns ocrdata line-by-line
    '''
    # needs the ocr data to be deskewed
    data = copy.deepcopy(temp)
    data = sorted(data, key=lambda i: (i['top']))
    # print('data', data)
    for i in range(len(data) - 1):
        if abs(data[i]['top'] - data[i + 1]['top']) < 5:
            data[i + 1]['top'] = data[i]['top']
    data = sorted(data, key=lambda i: (i['top'], i['left']))
    # lines = []
    # line = []
    # print('data2',data)
    lines = {}
    for word in data:
        if word['top'] in lines.keys():
            lines[word['top']].append(word)
        else:
            lines[word['top']] = [word]
    final_lines = []
    for key, value in lines.items():
        final_lines.append(value)

    return final_lines


# def return_lines(temp):
#     '''
#         Parameters : ocrData
#         Output     : Returns ocrdata line-by-line
#     '''
#     #needs the ocr data to be deskewed
#     data = copy.deepcopy(temp)
#     data = sorted(data, key = lambda i: (i['top']))
#     for i in range(len(data)-1):
#         if abs(data[i]['top'] - data[i+1]['top']) <6 :
#             data[i+1]['top'] = data[i]['top']
#     data = sorted(data, key = lambda i: (i['top'], i['left']))
#     lines = []
#     line = []
#
#     if len(data) > 2:
#         for i in range(len(data)-1):
#             if(data[i+1]['top'] == data[i]['top']):
#                 line.append(data[i])
#             else:
#                 line.append(data[i])
#                 lines.append(line)
#                 line = []
#     else:
#         if data[0]['top'] == data[-1]['top']:
#             lines.append([data[0],data[-1]])
#         else:
#             lines.append([data[0]])
#             lines.append([data[-1]])
#
#     return lines

def match_list(needle, haystack):
    """
        Finding required string in whole invoice(ocrdata)
        Parameters : needle - String to be found
                     haystack - ocrdata
        Output     : Top, Bottom, Left and matched String in ocrdata
    """
    global parameters
    try:
        length = len(needle.split())
        matched_needles = []
        # pass#print('needle',needle)
        for i, hay in enumerate(haystack):
            match = ''
            match_ocr = []
            # hay['word'] = clean_word(hay['word'])
            # needle.split()[0] = clean_word(needle.split()[0])
            first_word_match_score = SequenceMatcher(None, clean_word(hay['word']),
                                                     clean_word(needle.split()[0])).ratio()
            match_threshold = 0.70
            # if hay['word'].lower() == needle.split()[0]:
            #     pass#print('hey word',hay['word'].lower())
            # #pass#print(hay['word'].lower(),needle.split()[0])
            if (first_word_match_score > match_threshold):

                match += hay['word'].lower()
                match_ocr.append(hay)
                # #pass#print('debug footer')
                # #pass#print(hay['word'],needle.split()[0],first_word_match_score)
                try:
                    for j in range(i + 1, i + length):
                        match += ' ' + haystack[j]['word'].lower()
                        match_ocr.append(haystack[j])
                except Exception as e:
                    logging.debug(e)
                    # logger.error(e)
                # pass#print('match:',match)
                # pass#print('needele',needle)
                score = SequenceMatcher(None, clean_word(needle), clean_word(match)).ratio()
                matched_needles.append([match_ocr, score])
        # print('matched needles',matched_needles)
        if length > 1:
            matched = sorted(matched_needles, key=lambda x: (x[1], -x[0][0]['top']))[-1]

        else:
            matched = matched_needles[0]
        # print('matched',matched)
        if matched[1] > parameters['match_list_threshold']:
            footer_string = ' '.join(word['word'] for word in matched[0])
            footer_top = min(matched[0], key=lambda x: x['top'])['top']
            footer_bottom = max(matched[0], key=lambda x: x['bottom'])['bottom']
            footer_left = min(matched[0], key=lambda x: x['left'])['left']
            footer_right = max(matched[0], key=lambda x: x['right'])['right']
        else:
            footer_top = footer_bottom = footer_left = footer_right = -1
            footer_string = ''
            logging.debug(f'cant find footer{e}')

    except Exception as e:
        footer_top = footer_bottom = footer_left = footer_right = -1
        footer_string = ''
        logging.debug(f'cant find footer{e}')
    return (footer_top, footer_bottom, footer_left, footer_right, footer_string)


def match_list_words(list1, list2, headerBottom, footer):
    first = 0
    last = 0
    if list1:
        for i in range(len(list2)):
            idx = 0
            f = True
            length = len(list1)
            while (f == True and idx < length):
                if list1[idx].lower() not in list2[i + idx]['word'].lower():
                    f = False
                idx += 1
            if (f == True and idx == length and list2[i + length - 1]['top'] >= headerBottom and list2[i + length - 1][
                'bottom'] <= footer):
                first = i
                last = i + length - 1
        matched_ocr = []
        for i in range(first, last + 1):
            matched_ocr.append(list2[i])
        return matched_ocr
    return


def check_similarity(header_list, line):
    count = 0
    # header_list = ' '.join(header_list).split()
    pseudo_header = []
    for word in header_list:
        for data in line:
            # match_score =
            if (word.lower() in data['word'].lower() and word.lower() not in pseudo_header):
                count += 1
                pseudo_header.append(word.lower())
    # score = 0
    # if(len(line)):
    #     score = count/len(line)
    return count


''' Header Functions'''


def get_header_list(json_data):
    header_list_dict, col_children_no = header_helper(json_data)
    header_list = [v for k, v in header_list_dict.items()]
    return header_list, col_children_no


def finding_baseline(header_list, ocrdata):
    header_list = ' '.join(header_list).split()
    lines = return_lines(ocrdata)

    # img = cv2.imread('/home/priyatham/Downloads/Deloitte/gold.jpg')
    # w,h,c = img.shape
    # rf = 670/int(h)
    # img = cv2.resize(img, (0,0), fx=rf, fy=rf)
    #
    # for hay in lines:
    #     for word in hay:
    #         cv2.rectangle(img,(word['left'],word['top']),(word['right'],word['bottom']),(0,0,255),2)
    #         cv2.imshow('line',img)
    # cv2.waitKey()
    # cv2.destroyAllWindows()
    line_scores = []
    for i, line in enumerate(lines):
        line_string = ' '.join([l['word'] for l in line])
        score = check_similarity(header_list, line)
        # score_2 = SequenceMatcher(None,header_list,line_string).ratio()
        # score = score_1*score_1 + score_2*score_2
        line_scores.append([score, line, i])
        # pass#print(line_string , score)
    line_scores = sorted(line_scores, key=lambda k: k[0])
    line2 = line_scores[-1][1]
    line_number = line_scores[-1][2]
    # pass#print('baseline is')
    # pass#print(' '.join([word['word'] for word in lines[line_number]]))
    return line2, line_number, lines


def check_line_score(line, header_list):
    global  parameters
    try:
        count = 0
        # line = [word for word in line if word['word'].isalnum()]
        # pass#print('line',line)
        header_list = ' '.join([header for header in header_list]).split()  #
        header_list = [''.join(e for e in header if e.isalnum() or e == '%' or e == '#') for header in header_list]
        # pass#print('header_list',header_list)
        for word in line:
            for data in header_list:
                word_ = ''.join(e for e in word['word'] if e.isalnum() or e == '%' or e == '#')
                if word_:
                    # #pass#print(word['word'])
                    # #pass#print('clleaning')
                    # #pass#print(word['word'])
                    # #pass#print(clean_word(word['word']))
                    # #pass#print(clean_word(data))
                    match_score = SequenceMatcher(None, clean_word(word_), clean_word(data)).ratio()
                    if match_score > parameters['match_score_threshold'] :
                        count += 1
                        break
        score = count / len(line)
    except:
        score = 0
    return score


def header_proximity_finder(header_list, line_number, lines, img=None):
    global parameters
    top_flag = True
    t_idx = line_number - 1
    while top_flag and t_idx >= 0:
        line = lines[t_idx]
        # pass#print('In top part')
        # pass#print('line: ', ' '.join([word['word'] for word in line]))
        # #pass#print('header list : ', ' '.join([word for word in header_list]))
        line_score = check_line_score(line, header_list)
        # line_score = SequenceMatcher(None,' '.join([word['word'] for word in line]),' '.join([header.replace('  ',' ') for header in header_list])).ratio()
        # pass#print('score', line_score)
        if line_score > :
            t_idx -= 1
            # if img is not None:
            #     #pass#print('imageeeeeeeeeeee')
            #     cv2.rectangle(img, (int(line[0]['left']),int(line[0]['top'])), (int(line[-1]['right']),int(line[-1]['bottom'])), (0,0,255),2)
            #     cv2.imshow('proximity above',img)
            #     cv2.waitKey(0)
        else:
            t_idx += 1
            break
    if (t_idx < 0):
        t_idx += 1
    bottom_flag = True
    b_idx = line_number + 1
    while (bottom_flag and b_idx < len(lines)):
        # pass#print('In bottom part')
        line = lines[b_idx]
        line_score = check_line_score(line, header_list)
        # line_score = SequenceMatcher(None,' '.join([word['word'] for word in line]),' '.join([header.replace('  ',' ') for header in header_list])).ratio()

        # pass#print('line: ', ' '.join([word['word'] for word in line]))
        # pass#print('score', line_score)

        if line_score > parameters['line_score_threshold']:
            b_idx += 1
            # if img is not None:
            #     cv2.rectangle(img, (int(line[0]['left']),int(line[0]['top'])), (int(line[-1]['right']),int(line[-1]['bottom'])), (0,0,255),2)
            #     cv2.imshow('proximity below',img)
            #     cv2.waitKey(0)
        else:
            b_idx -= 1
            break
    if b_idx == len(lines):
        b_idx -= 1

    exclusive_header = lines[t_idx:b_idx + 1]
    w = ' '.join([word['word'] for line in exclusive_header for word in line])
    # pass#print('exclusive header : ',w)
    line_words_data = [word for line in exclusive_header for word in line]

    return line_words_data


def init_mark_data(line_words_data):
    for word in line_words_data:
        word['taken'] = False
    return line_words_data


def mark_data(line_words_data, word):
    for i, data in enumerate(line_words_data):
        if (data['left'] == word['left'] and data['top'] == word['top']):
            data['taken'] = True
            break
    return line_words_data


def check_mark(line_words_data, word):
    for data in line_words_data:
        if (data['left'] == word['left'] and data['top'] == word['top']):
            return data['taken']


def make_word_rectangle(words_coord_list, last_boundary, header_base_point, line_words_data, img=None):
    word_rectangles = []
    rect_words = []
    # pass#print('words coord list ' ,words_coord_list)
    for words in words_coord_list:
        xo = last_boundary
        yo = header_base_point
        # if(img is not None):
        #     for word in words:
        #         cv2.rectangle(img,(int(word['left']),int(word['top'])),(int(word['right']),int(word['bottom'])),(0,0,100),2)
        #         cv2.line(img,(int(xo),int(yo)),(int((word['left']+word['right'])*0.5),int((word['top']+word['bottom'])*0.5)),(0,0,225),2)
        #         cv2.imshow('lines',img)
        #         cv2.waitKey(0)
        words = sorted(words, key=lambda x: math.sqrt(((x['top'] + x['bottom']) * 0.5 - yo) ** 2 + \
                                                      ((x['left'] + x['right']) * 0.5 - xo) ** 2))
        i = 0
        word = {}
        # pass#print('words', words)
        while (i < len(words)):
            if not check_mark(line_words_data, words[i]):
                word = words[i]
                break
            i += 1
        # word = words[0]
        # pass#print('word:',word['word'] )
        if (img is not None):
            cv2.rectangle(img, (int(word['left']), int(word['top'])), (int(word['right']), int(word['bottom'])),
                          (0, 0, 100), 2)
            cv2.imshow('lines', img)
            cv2.waitKey(0)
        if bool(word):
            rect_words.append(word)
        # pass#print('rect', rect_words)
        line_words_data = mark_data(line_words_data, word)
    # pass#print(rect_words)
    # pass#print('here1')
    # #pass#print('wordsdasda',rect_words[0]['word'])
    rectangle = {}
    left = int(min(rect_words, key=lambda x: x['left'])['left'])
    right = int(max(rect_words, key=lambda x: x['right'])['right'])
    top = int(min(rect_words, key=lambda x: x['top'])['top'])
    bottom = int(max(rect_words, key=lambda x: x['bottom'])['bottom'])
    rect_area = (right - left) * (bottom - top)
    coords = (top, left, right, bottom)
    rectangle['coords'] = coords
    rectangle['rect_area'] = rect_area
    rectangle['words'] = rect_words
    word_rectangles.append(rectangle)
    # pass#print('here2')
    return word_rectangles, line_words_data


# def make_pseudo_rectangle(pseudo_header_list,header_column_wise_data,invoice_left,invoice_right):
#
#     rectangle = {}
#     coords = []
#     rect_area = []
#     words = []
#     for i in range(len(pseudo_header_list)):
#         if pseudo_header_list[i][1] == False:
#             if i == 0:
#                 pseudo_left = invoice_left
#                 pseudo_right = invoice_left + 5
#                 # #pass#print( header_column_wise_data[i+1]['words'])
#                 # pseudo_right = int((header_column_wise_data[i+1]['coords'][1] + pseudo_left)*0.5)
#                 # #pass#print('pseudo_left',pseudo_left,'pseudo_right',pseudo_right)
#
#             elif i == len(pseudo_header_list)-1:
#                 pseudo_left = header_column_wise_data[i-1]['coords'][2]
#                 pseudo_right = pseudo_left + 5
#                 # pseudo_right = invoice_right
#
#             else:
#                 # while()
#                 pseudo_left = int(( header_column_wise_data[i-1]['coords'][1] + header_column_wise_data[i+1]['coords'][2])*0.5) -5
#                 pseudo_right = int(( header_column_wise_data[i-1]['coords'][1] + header_column_wise_data[i+1]['coords'][2])*0.5) +5
#                 # pseudo_right = header_column_wise_data[i+1]['coords'][2]
#
#
#             coords = (0,pseudo_left,pseudo_right,0)
#             rect_area = 1
#
#             rectangle['coords'] = coords
#             rectangle['rect_area'] = rect_area
#             rectangle['words'] = words
#
#             header_column_wise_data[i] =  rectangle
#
#     return header_column_wise_data
''' new '''


def make_pseudo_rectangle(pseudo_header_list, header_column_wise_data, invoice_left, invoice_right, pseudo_y_axis,
                          img_=None):
    coords = []
    rect_area = []
    words = []
    header_column_wise_data_new = []
    i = 0
    while (i < len(pseudo_header_list)):
        j = i
        count = 0
        while (j < len(pseudo_header_list) and pseudo_header_list[j][1] == False):
            j += 1
            count += 1
        left = -1
        right = -1
        add = -1
        start = -1

        if (i is not 0 and i is not len(pseudo_header_list) and count):
            left = header_column_wise_data[i - 1]['coords'][2]
            if (j < len(header_column_wise_data)):
                right = header_column_wise_data[j]['coords'][1]
            else:
                right = invoice_right
            add = int((right - left) / count)
            start = i
        flag = False
        while (i < j and count):
            if pseudo_header_list[i][1] == False:
                rectangle = {}
                flag = True
                if i == 0:
                    pseudo_left = int((invoice_left + header_column_wise_data[j]['coords'][1]) / 2) - 10
                    pseudo_right = pseudo_left + 5
                elif i == len(pseudo_header_list) - 1:
                    pseudo_right = invoice_right
                    pseudo_left = pseudo_right - 5
                else:
                    conti_pseudo_number = i + 1 - start
                    L = -1
                    R = -1
                    if (conti_pseudo_number == 1):
                        L = left
                        R = left + add
                    elif (conti_pseudo_number == count):
                        L = right - add
                        R = right
                    else:
                        L = left + add * (conti_pseudo_number - 1)
                        R = left + add * (conti_pseudo_number)
                    pseudo_left = int((L + R) / 2 - 10)
                    pseudo_right = int((L + R) / 2 + 10)
                coords = (pseudo_y_axis - 5, pseudo_left, pseudo_right, pseudo_y_axis + 5)
                rect_area = 1
                rectangle['coords'] = coords
                rectangle['rect_area'] = rect_area
                rectangle['words'] = words
            header_column_wise_data_new.append(rectangle)
            i += 1
        if (flag == False):
            header_column_wise_data_new.append(header_column_wise_data[i])
            i += 1
    return header_column_wise_data_new


def header_column_wise_data_function(header_list, line_words_data, inv_width, img_=None):
    # ln = ' '
    # for data in line_words_data:
    #     ln += data['word']
    # #pass#print('line words data', ln)
    global parameters

    line_words_data = init_mark_data(line_words_data)
    pseudo_header_list = [[header, True] for header in header_list]
    header_column_wise_data = []
    last_boundary = int(min(line_words_data, key=lambda x: x['left'])['left'])
    # right boundary
    # header_base_point = int((lines[line_number][0]['top'] + lines[line_number][0]['bottom'])/2)
    # pass#print(line_words_data)
    header_base_point = int((min(line_words_data, key=lambda x: x['top'])['top'] + \
                             max(line_words_data, key=lambda x: x['bottom'])['bottom']) / 2)
    for i, header in enumerate(header_list):
        # pass#print('ello5',i)
        # pass#print('new header',header)
        right_boundary = last_boundary + int(4 * (inv_width / len(header_list)))
        # #pass#print(right_boundary)
        # pass#print('header to match **************************************************', header)
        header_words = header.split()
        words_coord_list = []
        for word in header_words:
            # pass#print('word to match############################ ', word)
            one_word_coord_list = []
            for idx, data in enumerate(line_words_data):
                '''Replacing with SequenceMatcher to avoid break at spelling mistakes
                # if(word.lower() in (data['word'].lower())):
                #     one_word_coord_list.append(data)
                '''

                # pass#print('data here', data['word'])
                match_score = SequenceMatcher(None, clean_word(word), clean_word(data['word'])).ratio()
                # pass#print('match score', match_score)
                if (match_score > parameters['match_score_threshold'] and data['left'] >= last_boundary and data['right'] < right_boundary and data[
                    'taken'] == False):
                    one_word_coord_list.append(data)
            if one_word_coord_list:
                words_coord_list.append(one_word_coord_list)
        try:
            header_words_rectangles, line_words_data = make_word_rectangle(words_coord_list.copy(), last_boundary,
                                                                           header_base_point, line_words_data)
            # #pass#print()
            # pass#print('here3')
            header_words_rectangles = sorted(header_words_rectangles, key=lambda x: x['rect_area'])
            header_words_rectangle = header_words_rectangles[0]
            # pass#print('here4')
            # pass#print('crossed word Rectangles')
            coords = header_words_rectangle['coords']
            # if(img_ is not None):
            #     for word in header_words_rectangle['words'] :
            #         cv2.rectangle(img_,(int(word['left']),int(word['top'])),(int(word['right']),int(word['bottom'])),(0,0,100),2)
            #         cv2.line(img_, (last_boundary, 0), (last_boundary, 4000), (0,0,255), 2)
            #         cv2.namedWindow('nested header',cv2.WINDOW_NORMAL)
            #         cv2.resizeWindow('nested header', 1200,1200)
            #         cv2.imshow('nested header',img_)
            #         cv2.waitKey(0)
            #         cv2.destroyAllWindows()

            for rectangle in header_words_rectangles:
                if (abs(rectangle['coords'][1] - last_boundary) < abs(
                        header_words_rectangle['coords'][1] - last_boundary) and rectangle['coords'][
                    1] > last_boundary):
                    header_words_rectangle = rectangle
            last_boundary = header_words_rectangle['coords'][2]
            header_column_wise_data.append(header_words_rectangle)
        except Exception as e:
            logging.debug(f'in except{header}')
            header_column_wise_data.append({})
            pseudo_header_list[i][1] = False
            logging.debug(f'Exception in header-wise data : {e}')
            # pass#print('3')

    return header_column_wise_data, pseudo_header_list


def finding_header_boundaries(header_column_wise_data):
    header_data = header_column_wise_data.copy()
    header_data_flatten = [item for sublist in header_data for item in sublist['words']]
    headerTop = sorted(header_data_flatten, key=lambda x: x['top'])[0]['top']
    headerLeft = sorted(header_data_flatten, key=lambda x: x['left'])[0]['left']
    headerRight = sorted(header_data_flatten, key=lambda x: x['right'])[-1]['right']
    headerBottom = sorted(header_data_flatten, key=lambda x: x['bottom'])[-1]['bottom']
    return headerTop, headerLeft, headerRight, headerBottom


def header_lines(table_img, rf, header_column_wise_data, headerTop, headerLeft, headerRight, headerBottom, footer,
                 ocrData, header_list, header_data):
    # vertical_lines = making_and_correcting_verticals(header_column_wise_data,ocrData,headerLeft,headerRight,headerBottom,headerTop,footer,header_list)
    word_space = get_word_space(ocrData)
    vertical_lines = vertical_slider(table_img, rf, header_column_wise_data, ocrData, headerLeft, headerRight,
                                     headerBottom, headerTop, footer, header_list, word_space)
    invoice_left = min(ocrData, key=lambda x: x['left'])['left']
    vertical_lines.append([[invoice_left, headerTop], [invoice_left, headerBottom]])
    invoice_right = max(ocrData, key=lambda x: x['right'])['right']
    vertical_lines.append([[invoice_right, headerTop], [invoice_right, headerBottom]])
    vertical_lines = sorted(vertical_lines, key=lambda x: x[0][0])
    # pass#print('vertical splide lines',vertical_lines)
    horizontal_lines = []
    horizontal_lines.append([[int(headerLeft), int(headerTop)], [int(headerRight), int(headerTop)]])
    horizontal_lines.append([[int(headerLeft), int(headerBottom)], [int(headerRight), int(headerBottom)]])

    return horizontal_lines, vertical_lines


def convert_word_to_line(word, ws, ocrData):
    # left increment
    flag = 1
    while (flag):
        flag = 0
        for data_ in ocrData:
            if ((word['top'] >= data_['top'] and word['top'] <= data_['bottom']) or (
                    data_['top'] >= word['top'] and data_['top'] <= word['bottom'])):
                diff = word['left'] - data_['right']
                if (diff > 0 and diff >= ws[0] and diff <= ws[1]):
                    flag = 1
                    word = club(word, data_)
    flag = 1
    while (flag):
        flag = 0
        for data_ in ocrData:
            if ((word['top'] >= data_['top'] and word['top'] <= data_['bottom']) or (
                    data_['top'] >= word['top'] and data_['top'] <= word['bottom'])):
                diff = data_['left'] - word['right']
                if (diff > 0 and diff >= ws[0] and diff <= ws[1]):
                    flag = 1
                    word = club(word, data_)
                    # break

    return word


def get_word_space(ocrData):
    spaces = []
    for i in range(len(ocrData) - 1):
        space = ocrData[i + 1]['left'] - ocrData[i]['right']
        if (space > 0 and space < 100):
            spaces.append(space)
    avg_space = reduce(lambda x, y: x + y, spaces) / len(spaces)

    return avg_space


def side_corrections(ocrData, headerLeft, headerRight, headerBottom, headerTop, footer):
    avg_space = get_word_space(ocrData)
    ws = [0, avg_space]
    # left correction
    flag = 1
    L = headerLeft
    dataShift = {}
    for data in ocrData:
        if (data['bottom'] < (headerBottom + footer) / 2 + (footer - headerBottom) / 2 and data['top'] > headerTop):
            if (L > data['left'] and data['right'] > L):
                dataShift = convert_word_to_line(data, ws, ocrData)
                if (dataShift['left'] < L):
                    L -= (L - dataShift['left'])
    # right correction
    flag = 1
    R = headerRight
    for data in ocrData:
        if (data['bottom'] < (headerBottom + footer) / 2 + (footer - headerBottom) / 2 and data['top'] > headerTop):
            if (R > data['left'] and data['right'] > R):
                dataShift = convert_word_to_line(data, ws, ocrData)
                if (dataShift['right'] > R):
                    R += (dataShift['right'] - R)
    return L, R


def header_helper(json_data):
    result = []
    for k, v in json_data.items():
        if type(v) is dict:
            for key, value in v.items():
                if (key == 'label' and k.startswith('v')):
                    result.append((k, value))

    header_list_dict = {}
    split_cols = {}
    prev_key = result[0][0]
    for each in result:
        if (prev_key in each[0] and prev_key in header_list_dict):
            split_cols[prev_key].append(each[1])
            header_list_dict[prev_key] += ' ' + each[1]
        else:
            split_cols[each[0]] = [each[1]]
            header_list_dict[each[0]] = each[1]
            prev_key = each[0]
    col_children_no = {}
    for k, v in split_cols.items():
        col_children = {}
        if (len(v) > 1):
            for i in range(1, len(v)):
                if (v[0] in col_children):
                    col_children[v[0]].append(v[i])
                else:
                    col_children[v[0]] = [v[i]]
        if col_children:
            col_children_no[k] = col_children

    return header_list_dict, col_children_no


''' Subtable Functions'''


def predict_kv_subtable(ocrData, json_data):
    final_footer = int(max([word['bottom'] for word in ocrData]))
    top = ocrData[-1]['bottom']
    extracted_data_subtable_kv = []

    try:
        needles_for_kv = []
        for k, v in json_data.items():
            if (k.startswith('h') and v['type'] == 'subtable - kv'):
                for key, value in json_data.items():

                    if (key.startswith(k) and key != k and value['label'] != ''):
                        needles_for_kv.append(value['label'])

        if not needles_for_kv:
            pass
            # logger.info('Needle is empty')
        # logger.debug('needles {}'.format(needles_for_kv))
        haystack = ocrData
        for needle_for_kv in needles_for_kv:
            key_word_list = subtable_helper(haystack, needle_for_kv)

            key_word_list_words = ''
            for key in key_word_list:
                key_word_list_words += ' ' + key['word']
            # logger.debug('key_word_list of needle_for_kv :  {}'.format(key_word_list_words))

            key_value_break = 0
            for word in key_word_list:
                if (word['right'] > key_value_break):
                    key_value_break = int(word['right'])

            top = int(min([word['top'] for word in key_word_list]))
            bottom = int(max([word['bottom'] for word in key_word_list]))
            left = int(min([word['left'] for word in key_word_list]))
            left_boundary_subtable_kv = left
            bottom_boundary_subtable_kv = bottom

            final_footer = bottom
            # we have to find right boundary by right most ocr data in that range :

            # right_boundary_subtable_kv = 10000
            ocrDataSubtable = []
            for data in ocrData:
                if (data['top'] <= bottom and data['bottom'] >= top):
                    ocrDataSubtable.append(data)
            # right_boundary_subtable_kv = headerRight
            right_boundary_invoice = max(word['right'] for word in ocrData)
            if (left < 0.25 * right_boundary_invoice):
                right_boundary_subtable_kv = right_boundary_invoice / 2
            else:
                right_boundary_subtable_kv = max(word['right'] for word in ocrDataSubtable)
            # find with other tables

            # get split lines
            ocrData_split = ocrDataLocal(top, key_value_break, right_boundary_subtable_kv, bottom + 5, haystack)
            # #pass#print('\n'*4,ocrData_split)
            subtable_splits = split_lines(key_value_break, right_boundary_subtable_kv, top, bottom, ocrData_split)

            # making  subtable kv  splits
            horizontal_lines_subtable_kv = []
            vertical_lines_subtable_kv = []
            for splits in subtable_splits:
                horizontal_lines_subtable_kv.append([[left, splits[0][1]], [right_boundary_subtable_kv, splits[0][1]]])

            # making subtable kv
            horizontal_lines_subtable_kv.append([[left, final_footer], [right_boundary_subtable_kv, final_footer]])
            horizontal_lines_subtable_kv.append([[left, top], [right_boundary_subtable_kv, top]])
            vertical_lines_subtable_kv.append([[key_value_break, top], [key_value_break, final_footer]])

            vertical_lines_subtable_kv.append(
                [[left_boundary_subtable_kv, top], [left_boundary_subtable_kv, final_footer]])
            vertical_lines_subtable_kv.append(
                [[right_boundary_subtable_kv, top], [right_boundary_subtable_kv, final_footer]])

            intersection_points_subtable_kv = find_intersections(horizontal_lines_subtable_kv,
                                                                 vertical_lines_subtable_kv)
            extracted_data_subtable_kv = complex_data_table_generator(ocrData[i], intersection_points_subtable_kv)

            return extracted_data_subtable_kv
    except Exception as e:
        logging.debug(f'KV subtable not found : {e}')

    return []


def predict_hf_subtable(ocrData, json_data):
    key_word_list = []
    needle_for_hf = ''
    extracted_data_subtable_hf = []
    try:
        for k, v in json_data.items():
            if (k.startswith('h') and v['type'] == 'subtable - header'):
                # footer_row = k
                for key, value in json_data.items():

                    if (key.startswith(k) and key != k):
                        needle_for_hf += value['label']
        ocrDataSubtable_hf = []
        for data in ocrData:
            if (data['top'] <= final_footer and data['bottom'] >= top):
                ocrDataSubtable_hf.append(data)
        key_word_list_hf = match_list_words(needle_for_hf.split(), ocrDataSubtable_hf, top, final_footer)
        subtable_header_top = min([word['top'] for word in key_word_list_hf])
        subtable_header_bottom = max([word['bottom'] for word in key_word_list_hf])
        subtable_header_left = min([word['left'] for word in key_word_list_hf])
        subtable_header_right = max([word['right'] for word in key_word_list_hf])
        bottom = final_footer

        subtable_h_left, subtable_h_right = side_corrections(ocrData, subtable_header_left, subtable_header_right,
                                                             subtable_header_bottom, subtable_header_top, bottom)

        # making  subtable header hf
        horizontal_lines_subtable_hf = []
        vertical_lines_subtable_hf = []

        horizontal_lines_subtable_hf.append(
            [[subtable_h_left, subtable_header_top], [subtable_h_right, subtable_header_top]])
        horizontal_lines_subtable_hf.append(
            [[subtable_h_left, subtable_header_bottom], [subtable_h_right, subtable_header_bottom]])
        horizontal_lines_subtable_hf.append([[subtable_h_left, final_footer], [subtable_h_right, final_footer]])

        vertical_lines_subtable_hf.append([[subtable_h_left, subtable_header_top], [subtable_h_left, final_footer]])
        vertical_lines_subtable_hf.append([[subtable_h_right, subtable_header_top], [subtable_h_right, final_footer]])

        intersection_points_subtable_hf = find_intersections(horizontal_lines_subtable_hf, vertical_lines_subtable_hf)
        extracted_data_subtable_hf = complex_data_table_generator(ocrData, intersection_points_subtable_hf)
        return extracted_data_subtable_hf

    except Exception as e:
        pass
        # logger.error(' hf subtable not found :  {}'.format(e))

    return []


'''Footer Functions'''


def get_footers_dict(json_data):
    footer_list = {}
    for k, v in json_data.items():
        # #pass#print(k,v['type'])
        if (k.startswith('h') and type(v) is dict and v['type'] == 'Simple Single Key-value'):
            footer_row = k
            # footer_type = v['data']
            logging.debug(f'key{k}')
            footer_type = 'Simple Single Key-value'
            # #pass#print(footer_type)
            for key, value in json_data.items():
                if (key.startswith(k)):
                    pass  # print(value['label'],v['display'],footer_type)
                    if footer_type not in footer_list:
                        footer_list[footer_type] = [[value['label']]]
                    else:
                        footer_list[footer_type].append([value['label']])
        # elif(k.startswith('h') and (v['type'] == 'horizontal key - values' or v['type'] == 'vertical key - values' )):
        #     for key,value in json_data.items():
        #         if(key.startswith(k) and key != k):
        #             if v['type'] not in footer_list:
        #                 footer_list[v['type']] = [[value['label'],v['display']]]
        #             else:
        #                 footer_list[v['type']].append([value['label'],v['display']])

    logging.debug(f'footer list{footer_list}')
    return footer_list


def get_footers_dict_(json_data):
    footer_list = {}
    for k, v in json_data.items():
        # #pass#print(k,v['type'])
        if (k.startswith('h') and v['type'] == 'maintable - footer'):
            footer_row = k
            footer_type = v['data']
            # #pass#print(footer_type)
            for key, value in json_data.items():
                if (key.startswith(k) and key != k):
                    # pass#print(value['label'],v['display'],footer_type)
                    if footer_type not in footer_list:
                        footer_list[footer_type] = [[value['label'], v['display']]]
                    else:
                        footer_list[footer_type].append([value['label'], v['display']])
        elif (k.startswith('h') and (v['type'] == 'horizontal key - values' or v['type'] == 'vertical key - values')):
            for key, value in json_data.items():
                if (key.startswith(k) and key != k):
                    if v['type'] not in footer_list:
                        footer_list[v['type']] = [[value['label'], v['display']]]
                    else:
                        footer_list[v['type']].append([value['label'], v['display']])

    return footer_list


def get_next_line_ocr(ocrData, cur_line_bottom):
    next_line = []
    for i in range(len(ocrData) - 1):
        if ocrData[i]['top'] > cur_line_bottom:
            if ocrData[i]['top'] == ocrData[i + 1]['top']:
                next_line.append(ocrData[i])
                # #pass#print(ocrData[i])
            else:
                break

    return next_line


def move_ver(ocrData, v, T, B):
    L, R = int(min(ocrData, key=lambda x: x['left'])['left']), int(max(ocrData, key=lambda x: x['right'])['right'])
    ocr_data = ocrDataLocal(T, L, R, B, ocrData)
    for data in ocr_data:
        if v in range(data['left'], data['right']):
            if v - data['left'] > data['right'] - v:
                return int(data['right'])
            else:
                return int(data['left'])
        else:
            return v


def validate_verticals(ocrData, vers, T, B):
    for i in range(len(vers)):
        vers[i] = move_ver(ocrData, vers[i], T, B)
    return vers


def get_footer_matrix(ocrData, key_words, header_column_wise_data, alias_names, img):
    vers = [int((header_column_wise_data[i]['coords'][2] + header_column_wise_data[i + 1]['coords'][1]) * 0.5) for i in
            range(len(header_column_wise_data) - 1)]

    FM_top, FM_bottom, FM_left, FM_key_right, footer_string = match_list(key_words, ocrData)
    # cv2.rectangle(img,(FM_left,FM_top),(FM_key_right,FM_bottom),(0,255,255),2)
    # pass#print(FM_top,FM_bottom)
    # pass#print('match list string',footer_string)
    footer_vers = []
    footer_vers.append(int(FM_left))
    FM_right = int(max(ocrData, key=lambda x: x['right'])['right'])
    footer_vers.append(FM_right)
    footer_vers.append(FM_key_right)
    footer_vers.extend([v for v in vers if v in range(FM_key_right, FM_right)])
    footer_vers = sorted(footer_vers)
    footer_vers = validate_verticals(ocrData, footer_vers, FM_top, FM_bottom)
    footer_vers = list(set(footer_vers))
    footer_vers = sorted(footer_vers)

    # pass#print(footer_vers)

    # make footer lines
    footer_hors = []
    footer_hors.append([[FM_left, FM_top], [FM_right, FM_top]])
    footer_hors.append([[FM_left, FM_bottom], [FM_right, FM_bottom]])

    ''' debug'''
    # for hor in footer_hors:
    #     cv2.line(img,(FM_left,FM_top),(FM_right,FM_top),(0,0,255),2)
    #     cv2.line(img,(FM_left,FM_bottom),(FM_right,FM_bottom),(0,0,255),2)
    # for ver in footer_vers:
    #     cv2.line(img,(ver,FM_top),(ver,FM_bottom),(0,0,255),2)
    #
    # cv2.namedWindow('matrix',cv2.WINDOW_NORMAL)
    # cv2.resizeWindow('matrix', 1200,1200)
    # cv2.imshow('matrix',img)
    # cv2.waitKey()
    # cv2.destroyAllWindows()
    footer_vers = sorted(footer_vers)
    footer_vers = [[[v, FM_top], [v, FM_bottom]] for v in footer_vers]
    intersection_points_footer = find_intersections(footer_hors, footer_vers)
    extracted_data_footer = complex_data_table_generator(ocrData, intersection_points_footer)
    # pass#print(' footer matrix', extracted_data_footer)
    FM_header = []
    FM_header.append(['', 1, 1])
    for i in range(1, len(footer_vers) - 1):
        l = footer_vers[i][0][0]
        r = footer_vers[i + 1][0][0]
        found = False
        for idx, header in enumerate(header_column_wise_data):
            # #pass#print(l,r)
            # #pass#print(header['coords'][1],header['coords'][2]+1)
            if (set(range(header['coords'][1], header['coords'][2] + 1)).intersection(set(range(l, r + 1)))):
                # #pass#print(i)
                # #pass#print(l,r)
                # #pass#print(alias_names[idx])
                if ocrDataLocal(FM_top, l, r, FM_bottom, ocrData):
                    FM_header.append([alias_names[idx], 1, 1])
                else:
                    FM_header.append(['', 1, 1])
                found = True
                break

        if (found == False):
            # pass#print('appending empty')
            FM_header.append(["", 1, 1])
    # #pass#print(FM_header)
    extracted_data_footer.insert(0, FM_header)
    # pass#print(extracted_data_footer)
    row1 = []
    row2 = []
    # pass#print(extracted_data_footer)
    for i in range(len(extracted_data_footer[0])):
        # #pass#print('matrixxxxxxxxxxxx',extracted_data_footer[0][i][0],extracted_data_footer[1][i][0])
        if extracted_data_footer[0][i][0] != '' or extracted_data_footer[1][i][0] != '':
            row1.append(extracted_data_footer[0][i])
            row2.append(extracted_data_footer[1][i])
    extracted_data_footer = [row1, row2]
    return extracted_data_footer, FM_top


def get_footer_matrix_top(ocrData, key_words):
    FM_top = max(ocrData, key=lambda x: x['bottom'])
    try:
        FM_top, FM_bottom, FM_left, FM_key_right, footer_string = match_list(key_words, ocrData)
    except:
        logging.debug('Footer matrix top not found')

    return FM_top


def get_footer_matrix_(ocrData, key_words, vers, header_column_wise_data, alias_names, img):
    extracted_data_footer = []
    FM_top = max(ocrData, key=lambda x: x['bottom'])
    try:

        FM_top, FM_bottom, FM_left, FM_key_right, footer_string = match_list(key_words, ocrData)
        # cv2.rectangle(img,(FM_left,FM_top),(FM_key_right,FM_bottom),(0,255,255),2)
        # pass#print('match list string',footer_string)
        footer_vers = []
        footer_vers.append(int(FM_left))
        FM_right = int(max(ocrData, key=lambda x: x['right'])['right'])
        footer_vers.append(FM_right)
        # footer_vers.append(FM_key_right)
        footer_vers.extend([v for v in vers if v in range(FM_key_right, FM_right)])
        footer_vers = sorted(footer_vers)
        footer_vers = validate_verticals(ocrData, footer_vers, FM_top, FM_bottom)
        footer_vers = list(set(footer_vers))
        footer_vers = sorted(footer_vers)
        # pass#print(FM_top,FM_bottom)
        # pass#print(footer_vers)

        # make footer lines
        footer_hors = []
        footer_hors.append([[FM_left, FM_top], [FM_right, FM_top]])
        footer_hors.append([[FM_left, FM_bottom], [FM_right, FM_bottom]])

        ''' debug'''
        # for hor in footer_hors:
        #     cv2.line(img,(FM_left,FM_top),(FM_right,FM_top),(0,0,255),1)
        #     cv2.line(img,(FM_left,FM_bottom),(FM_right,FM_bottom),(0,0,255),1)
        # for ver in footer_vers:
        #     cv2.line(img,(ver,FM_top),(ver,FM_bottom),(0,0,255),2)
        #
        #     cv2.namedWindow('matrix',cv2.WINDOW_NORMAL)
        #     cv2.resizeWindow('matrix', 1200,1200)
        #     cv2.imshow('matrix',img)
        #     cv2.waitKey()
        #     cv2.destroyAllWindows()
        footer_vers = sorted(footer_vers)
        footer_vers = [[[v, FM_top], [v, FM_bottom]] for v in footer_vers]
        intersection_points_footer = find_intersections(footer_hors, footer_vers)
        # #pass#print(ocrData)
        extracted_data_footer = complex_data_table_generator(ocrData, intersection_points_footer)
        # pass#print(' footer matrix', extracted_data_footer)
        FM_header = []
        FM_header.append(['', 1, 1])
        for i in range(1, len(footer_vers) - 1):
            l = footer_vers[i][0][0]
            r = footer_vers[i + 1][0][0]
            found = False
            for idx, header in enumerate(header_column_wise_data):
                # pass#print((l,r),(header['coords'][1],header['coords'][2]+1))
                if (set(range(header['coords'][1], header['coords'][2] + 1)).intersection(set(range(l, r + 1)))):
                    # pass#print(ocrDataLocal(FM_top,l,r,FM_bottom,ocrData))
                    if ocrDataLocal(FM_top, l, r, FM_bottom, ocrData):
                        FM_header.append([alias_names[idx], 1, 1])
                    else:
                        FM_header.append(['', 1, 1])
                    found = True
                    break

            if (found == False):
                # pass#print('appending empty')
                FM_header.append(["", 1, 1])
        # #pass#print(FM_header)
        extracted_data_footer.insert(0, FM_header)
        # pass#print(extracted_data_footer)
        row1 = []
        row2 = []
        # pass#print(extracted_data_footer)
        for i in range(len(extracted_data_footer[0])):
            # #pass#print('matrixxxxxxxxxxxx',extracted_data_footer[0][i][0],extracted_data_footer[1][i][0])
            if extracted_data_footer[0][i][0] != '' or extracted_data_footer[1][i][0] != '':
                row1.append(extracted_data_footer[0][i])
                row2.append(extracted_data_footer[1][i])
        extracted_data_footer = [row1, row2]
    except:
        logging.debug('Matrix footer not found')

    return extracted_data_footer, FM_top


def get_ver_kv_footer(verkv_list, ocrData):
    '''finding header of vertical kv footer'''
    inv_width = max(ocrData, key=lambda x: x['right'])['right']
    verkv_words_data, line_number, lines = finding_baseline(verkv_list, ocrData)
    line_words_data = header_proximity_finder(verkv_list, line_number, lines)
    keys = header_column_wise_data_function(verkv_list, line_words_data, inv_width)[0]
    verkv_top, verkv_left, verkv_right, verkv_bottom = finding_header_boundaries(keys)

    '''Finding footer of vertical kv footer'''

    ver_kv_footer_ocr = get_next_line_ocr(ocrData, verkv_bottom)

    ver_kv_footer_bottom = max([word['bottom'] for word in ver_kv_footer_ocr]) + 5
    ver_kv_footer_left = min(ver_kv_footer_ocr, key=lambda x: x['left'])['left']
    ver_kv_footer_right = max(ver_kv_footer_ocr, key=lambda x: x['right'])['right']

    '''Initialisation of verticals in middle of two header words'''

    keys_vers = [keys[0]['coords'][1]]
    for i in range(len(keys) - 1):
        key_left = keys[i]['coords'][2]
        next_key_right = keys[i + 1]['coords'][1]
        keys_vers.append(int((key_left + next_key_right) * 0.5))
        # cv2.line(img,(int(key_left),0),(int(key_left),4000),(0,255,0),2)
        # cv2.line(img,(int(next_key_right),0),(int(next_key_right),4000),(255,0,255),2)
        # cv2.namedWindow('da',cv2.WINDOW_NORMAL)
        # cv2.resizeWindow('da', 1200,1200)
        # cv2.imshow('da',img)
        # cv2.waitKey()
    keys_vers.append(keys[len(keys) - 1]['coords'][2])
    '''Correcting Verticals'''
    for i in range(len(keys_vers)):
        keys_vers[i] = move_ver(ocrData, keys_vers[i], verkv_bottom, ver_kv_footer_bottom)

    vers = []
    hors = []
    for ver in keys_vers:
        vers.append([[ver, verkv_top], [ver, ver_kv_footer_bottom]])
    hors.append([[keys_vers[0], verkv_top], [keys_vers[-1], verkv_top]])
    hors.append([[keys_vers[0], verkv_bottom], [keys_vers[-1], verkv_bottom]])
    hors.append([[keys_vers[0], ver_kv_footer_bottom], [keys_vers[-1], ver_kv_footer_bottom]])

    intersection_points_footer = find_intersections(horizontal_lines_footer, vertical_lines_footer)
    extracted_data_footer = complex_data_table_generator(ocrData, intersection_points_footer)

    return extracted_data_footer, verkv_top


def get_hor_kv_footer(needle_for_kv, haystack, img):  # Same as kv subtable

    extracted_data_subtable_kv = []
    top = max(haystack, key=lambda x: x['bottom'])

    try:
        key_word_list = subtable_helper(haystack, needle_for_kv, img)

        key_word_list_words = ''
        for key in key_word_list:
            key_word_list_words += ' ' + key['word']
        # logger.debug('key_word_list of needle_for_kv :  {}'.format(key_word_list_words))
        # pass#print('key words list for needle ',key_word_list_words)
        key_value_break = 0
        for word in key_word_list:
            if (word['right'] > key_value_break):
                key_value_break = int(word['right'])

        top = int(min([word['top'] for word in key_word_list]))
        bottom = int(max([word['bottom'] for word in key_word_list]))
        left = int(min([word['left'] for word in key_word_list]))
        left_boundary_subtable_kv = left
        bottom_boundary_subtable_kv = bottom

        final_footer = bottom

        ocrDataSubtable = []
        for data in haystack:
            if (data['top'] <= bottom and data['bottom'] >= top):
                ocrDataSubtable.append(data)
        # right_boundary_subtable_kv = headerRight
        values = []
        '''finding right boundary'''
        right_boundary_haystack = ocrDataLocal(top, key_value_break, max([word['right'] for word in haystack]), bottom,
                                               haystack)
        # pass#print('right_boundary_haystack',right_boundary_haystack)
        hays = return_lines(right_boundary_haystack)
        # pass#print('hays',hays)
        right_boundary_subtable_kv = max(hay[0]['right'] for hay in hays)
        # pass#print('right_boundary_subtable_kv',right_boundary_subtable_kv)
        # right_boundary_subtable_kv = max(word['right'] for word in haystack)

        # if(left < 0.25*right_boundary_invoice):
        #     right_boundary_subtable_kv = right_boundary_invoice/2
        # else:
        #     right_boundary_subtable_kv = max(word['right'] for word in haystack)

        # img = cv2.imread(imgpath)
        # w,h,c = img.shape
        # rf = 670/int(h)
        # img = cv2.resize(img, (0,0), fx=rf, fy=rf)
        # cv2.rectangle(img,(int(left_boundary_subtable_kv),int(top)),(int(right_boundary_subtable_kv),int(bottom_boundary_subtable_kv)),(0,0,255),2)

        # get split lines
        ocrData_split = ocrDataLocal(top, key_value_break, right_boundary_subtable_kv, bottom + 5, haystack)
        # #pass#print('\n'*4,ocrData_split)
        subtable_splits = split_lines(key_value_break, right_boundary_subtable_kv, top, bottom, ocrData_split)

        # making  subtable kv  splits
        horizontal_lines_subtable_kv = []
        vertical_lines_subtable_kv = []
        for splits in subtable_splits:
            horizontal_lines_subtable_kv.append([[left, splits[0][1]], [right_boundary_subtable_kv, splits[0][1]]])

        # making subtable kv
        horizontal_lines_subtable_kv.append([[left, final_footer], [right_boundary_subtable_kv, final_footer]])
        horizontal_lines_subtable_kv.append([[left, top], [right_boundary_subtable_kv, top]])
        vertical_lines_subtable_kv.append([[key_value_break, top], [key_value_break, final_footer]])

        vertical_lines_subtable_kv.append([[left_boundary_subtable_kv, top], [left_boundary_subtable_kv, final_footer]])
        vertical_lines_subtable_kv.append(
            [[right_boundary_subtable_kv, top], [right_boundary_subtable_kv, final_footer]])
        # #pass#print('hor kv hors',horizontal_lines_subtable_kv)
        # #pass#print('hor kv vers',vertical_lines_subtable_kv)
        # for hor in horizontal_lines_subtable_kv:
        #     # cv2.line(img,(int(hor[0][0]),int(hor[0][1])),(int(hor[1][0]),int(hor[1][1])),(255,0,255),2)
        # for ver in vertical_lines_subtable_kv:
        #     cv2.line(img,(int(ver[0][0]),int(ver[0][1])),(int(ver[1][0]),int(ver[1][1])),(255,0,255),2)

        # cv2.namedWindow('hor kv',cv2.WINDOW_NORMAL)
        # cv2.resizeWindow('hor kv', 1200,1200)
        # cv2.imshow('hor kv',img)
        # cv2.waitKey(0)

        intersection_points_subtable_kv = find_intersections(horizontal_lines_subtable_kv, vertical_lines_subtable_kv)
        extracted_data_subtable_kv = complex_data_table_generator(haystack, intersection_points_subtable_kv)
    except:
        logging.debug('Horizontal KV footer not found !!!')

    return extracted_data_subtable_kv, top


def get_simple_kv_footer(needle, ocrData):
    footer_left = int(min([word['left'] for word in ocrData]))
    footer_right = int(max([word['right'] for word in ocrData]))
    footer_top = ocrData[-1]['bottom']
    footer_bottom = ocrData[-1]['bottom']
    extracted_data_footer = []
    try:
        footer_top, footer_bottom, footer_left, footer_middle, footer_string = match_list(needle, ocrData)

        logging.debug(f'{footer_top},{footer_bottom},{footer_left},{footer_middle}')
        ocr_s = ocrDataLocal(footer_top, footer_left, footer_right, footer_bottom, ocrData)
        # print('ocr_s', ocr_s)
        # print('footer string',footer_string)
        horizontal_lines_footer = []
        vertical_lines_footer = []

        horizontal_lines_footer.append([[footer_left, footer_top], [footer_right, footer_top]])
        horizontal_lines_footer.append([[footer_left, footer_bottom], [footer_right, footer_bottom]])
        vertical_lines_footer.append([[footer_left, footer_top], [footer_left, footer_bottom]])
        vertical_lines_footer.append([[footer_right, footer_top], [footer_right, footer_bottom]])
        vertical_lines_footer.append([[footer_middle, footer_top], [footer_middle, footer_bottom]])

        intersection_points_footer = find_intersections(horizontal_lines_footer, vertical_lines_footer)
        extracted_data_footer = complex_data_table_generator(ocrData, intersection_points_footer)
    except:
        logging.debug('cant find footer')

    return extracted_data_footer, footer_top


def get_maintable_footer(footer_tops):
    footer_tops = [top for top in footer_tops if top > 0]
    main_table_bottom = min(footer_tops)
    return main_table_bottom


def predict_maintable_footer(ocrData, json_data, idx, headerBottom, kv_subtable_top=None):
    '''Initialisation of footer default boundaries'''

    footer_list = []
    footer_left = int(min([word['left'] for word in ocrData]))
    footer_right = int(max([word['right'] for word in ocrData]))
    footer_top = ocrData[-1]['bottom']
    footer_bottom = ocrData[-1]['bottom']

    extracted_data_footer = []

    try:
        for k, v in json_data.items():
            if (k.startswith('h') and v['type'] == 'maintable - footer'):
                footer_row = k
                for key, value in json_data.items():
                    if (key.startswith(k) and key != k):
                        footer_list.append(value['label'])
        # #pass#print(footer_list)
        try:
            footer_word = footer_list[idx]
        except:
            footer_word = ''

        ''' Replace above snippet and get footer type dictionary and call corresponding functions'''

        # logger.debug('footer list {}'.format(footer_list))
        # #pass#print(footer_list)
        '''Defining scope for finding footer
               ----------------------------------------------
                |                    HEADER                  |
          T--------------------------------------------------------|
        L |                                                        | R
          |                   SCOPE FOR FOOTER                     |
          |--------------------------------------------------------|
                                    B

          '''

        T = headerBottom
        L = 0
        R = footer_right
        if kv_subtable_top:
            B = kv_subtable_top
        else:
            B = ocrData[-1]['bottom']
        # #pass#print(ocrData[-1]['word'],'Last word')
        ocr_data_footer_finder = ocrDataLocal(T, L, R, B, ocrData)
        # #pass#print(ocr_data_footer_finder)
        if footer_word:
            line_item_footer, footer_bottom, footer_left, footer_right, footer_string = match_list(footer_word,
                                                                                                   ocr_data_footer_finder)
            footer_top = line_item_footer
            # #pass#print(footer_string)
        # making footer table
        horizontal_lines_footer = []
        vertical_lines_footer = []
        horizontal_lines_footer.append([[footer_left, footer_top], [footer_right, footer_top]])
        horizontal_lines_footer.append([[footer_left, footer_bottom], [footer_right, footer_bottom]])
        vertical_lines_footer.append([[footer_left, footer_top], [footer_left, footer_bottom]])
        vertical_lines_footer.append([[footer_right, footer_top], [footer_right, footer_bottom]])
        ################################ CV Debugging for footer ##################################
        # imgpath_multi = '/home/lohith/ace_12/ACE-platform/documents/input/challan.jpg'
        #
        # img = cv2.imread(imgpath_multi)
        # w,h,c = img.shape
        # rf = 670/int(h)
        # img = cv2.resize(img, (0,0), fx=rf, fy=rf)
        # cv2.rectangle(img,(L,T),(R,B),(0,0,225),2)
        # for i,h in enumerate(horizontal_lines_footer):
        #     cv2.line(img,(int(h[0][0]),int(h[0][1])),(int(h[1][0]),int(h[1][1])),(0, 0, 255),2)
        # for i,v in enumerate(vertical_lines_footer):
        #     cv2.line(img,(int(v[0][0]),int(v[0][1])),(int(v[1][0]),int(v[1][1])),(0, 0, 255),2)
        #
        # cv2.namedWindow('Footer',cv2.WINDOW_NORMAL)
        # cv2.resizeWindow('Footer', 1200,1200)
        # cv2.imshow('Footer',img)
        # cv2.waitKey(0)
        # cv2.destroyAllwindows()
        ####################################################################################################
        intersection_points_footer = find_intersections(horizontal_lines_footer, vertical_lines_footer)
        extracted_data_footer = complex_data_table_generator(ocrData, intersection_points_footer)

        return [extracted_data_footer, footer_top]

    except Exception as e:
        logging.debug(e)
        # logger.error('footer not found :  {}'.format(e))

    return [extracted_data_footer, footer_top]


'''Drawing horizontal_lines
        ------------------------------------------------------------------
        |  H   E  |D   E   R   C  | O   L    U   M   N  S |  RIGHT COLUMN |
        --------------------------------------------------------------------T
        |                                                L |      ***       |R
        |                                                  |      ***       |
        -------------------------------------------------------------------- B
'''


# def predict_header(ocrData,horizontal_lines,vertical_lines,req_cols,alias_names):
#     extracted_data_maintable = []
#
#     try:
#         intersection_points_maintable = find_intersections(horizontal_lines, vertical_lines)
#         extracted_data_maintable = complex_data_table_generator(ocrData, intersection_points_maintable,req_cols, horizontal_lines, vertical_lines)
#         #pass#print('extracted_data_maintable',extracted_data_maintable)
#         for i,data in enumerate(extracted_data_maintable[0]):
#             #pass#print('data:',data[0])
#             #pass#print('alisa',alias_names[i])
#             data[0] = alias_names[i]
#
#     except Exception as e:
#         logger.error('main table not found  {}'.format(e))
#     return extracted_data_maintable

def predict_maintable(ocrData, ocr_data_old, horizontal_lines, vertical_lines, headerBottom, req_cols, alias_names,
                      subheader_data_arrays, img_=None):
    extracted_data_maintable = []
    # pass#print('alias_names',alias_names)
    try:
        intersection_points_maintable = find_intersections(horizontal_lines, vertical_lines)
        # pass#print('crossed find interections')
        extracted_data_maintable, row_bounds = complex_data_table_generator(ocrData, intersection_points_maintable,
                                                                            req_cols, horizontal_lines, vertical_lines,
                                                                            img_, 'subheader', True)
        row_bounds.append([horizontal_lines[-1][0][1], horizontal_lines[-1][0][1]])

        for i, data in enumerate(extracted_data_maintable[0]):
            # pass#print('data:',data[0])
            # pass#print('alisa',alias_names[i])
            data[0] = '<b>' + alias_names[i] + '</b>'

        extracted_data_maintable_new = []
        for row in extracted_data_maintable:
            if len(row):
                extracted_data_maintable_new.append(row)
        extracted_data_maintable = extracted_data_maintable_new
        '''Include Subheaders'''
        # #pass#print('sub headers:')
        # #pass#print(100*'#')
        # #pass#print(' data maintable before subtable', extracted_data_maintable)

        # if(img_ is not None):
        #     for row in row_bounds:
        #         cv2.line(img_, (0, row[0]), (4000, row[0]), (0,0,255), 2)
        #         cv2.line(img_, (0, row[1]), (4000, row[1]), (0,0,255), 2)
        #     cv2.namedWindow('main-table',cv2.WINDOW_NORMAL)
        #     cv2.resizeWindow('main-table', 1200,1200)
        #     cv2.imshow('main-table',img_)
        #     cv2.waitKey(0)
        #     cv2.destroyAllWindows()

        for subheader_data_array in subheader_data_arrays:
            for subheader in subheader_data_array:
                # find the row after which to include
                i = 0
                while (i < len(row_bounds) - 1):
                    # line1 = horizontal_lines[i][0][1]
                    # line2 = horizontal_lines[i+1][0][1]
                    line1 = int((row_bounds[i][0] + row_bounds[i][1]) / 2)
                    line2 = int((row_bounds[i + 1][0] + row_bounds[i + 1][0]) / 2)
                    # pass#print(line1,line2)
                    # pass#print(subheader[0])
                    if int((subheader[0] + subheader[3]) / 2) in range(line1, line2):
                        # pass#print('index of line is ', i)
                        subheader_row = return_subheader_row(subheader, ocr_data_old)
                        # pass#print('sub header row ',subheader_row)
                        subheader_row_rect = [subheader_row, 1, len(vertical_lines) - 1]
                        # pass#print(line1, headerBottom)
                        if line1 == headerBottom:
                            # pass#print(' in here yesssssssssssssssssssssssssssssssss')
                            extracted_data_maintable.insert(i, [subheader_row_rect])
                            row_bounds.insert(i, [subheader[0], subheader[3]])
                            i += 1
                            break
                        else:
                            extracted_data_maintable.insert(i + 1, [subheader_row_rect])
                            row_bounds.insert(i + 1, [subheader[0], subheader[3]])
                            i += 1
                            break
                    i += 1
    except Exception as e:
        logging.debug(f'main table not found  {e}')
        # print('extracted data maintable', extracted_data_maintable)
    return extracted_data_maintable


# def get_alignment(json_data,lines):
#     alignment = 'top'
#
#     '''check for subheader '''
#
#     sub_header_alignment = 'bottom'
#     for k,v in json_data.items():
#         if k.startswith('h') and v['type'] == 'maintable - sub - header':
#             v['data'] = json.loads(v['data'])
#             sub_header_alignment = v['data']['position']
#
#     if sub_header_alignment == 'top':
#         #pass#print(lines['hors'])

def ocr_to_lines(ocrDataColumn):
    '''
        Parameters : ocrData
        Output     : Returns ocrdata line-by-line
    '''
    # needs the ocr data to be deskewed
    i = 0
    # make single line data separate
    while (i < len(ocrDataColumn) - 1):
        data = ocrDataColumn[i]
        data2 = ocrDataColumn[i + 1]
        if ((data['top'] >= data2['top'] and data['top'] <= data2['bottom']) or (
                data2['top'] >= data['top'] and data2['top'] <= data['bottom'])):
            word = club(data, data2)
            ocrDataColumn[i] = word
            ocrDataColumn.pop(i + 1)
            i = i - 1
        i = i + 1
    return ocrDataColumn


def line_space_hors(ocr_data, vers, ref_col):
    # vers = [54,352,413,481,516,585,660]
    ocrdata_col = ocrDataLocal(0, vers[-2], vers[-1], w, ocr_data)
    lines = ocr_to_lines(ocrdata_col)

    no_of_rows = len(lines)
    hors = []
    tops = [[] for i in range(no_of_rows - 1)]
    bottoms = [[] for i in range(no_of_rows - 1)]
    for i in range(len(vers) - 1):
        ocrdata_col = ocrDataLocal(0, vers[i], vers[i + 1], w, ocr_data)
        lines = ocr_to_lines(ocrdata_col)
        spaces_list = []
        spaces = {}
        space = lines[0]['bottom']
        for idx in range(1, len(lines)):
            top = lines[idx]['top']
            bottom = lines[idx]['bottom']
            # spaces.append(top-space)
            spaces['top'] = space
            spaces['bottom'] = top
            spaces['space'] = top - space
            spaces_list.append(spaces)
            spaces = {}
            space = bottom
        spaces_list = sorted(spaces_list, key=lambda x: x['space'], reverse=True)
        spaces_list = spaces_list[:no_of_rows - 1]
        for iter, space in enumerate(spaces_list):
            tops[iter].append(space['top'])
            bottoms[iter].append(space['bottom'])
            hor = int(space['top']) + int((space['bottom'] - space['top']) * 0.5)

    for i in range(no_of_rows - 1):
        max_top = max(tops[i])
        min_bottom = min(bottoms[i])
        hors.append(int((max_top + min_bottom) * 0.5))
    return hors


def get_ref_col(json_data):
    logging.debug(f'in ref col{json_data}')
    try:
        for k, v in json_data.items():
            if k.startswith('v') and (v['ref'] == 'true' or v['ref'] == True):
                # #pass#print(k[1:])
                return int(k[1:])
    except:
        logging.debug(' no ref col')
        return 0


# def get_ref_col(json_data,header_column_wise_data):
#     #pass#print('Fetching ref column')
#     try:
#         ref_col_name = ''
#         for k,v in json_data.items():
#             if k.startswith('v') and v['ref'] == 'true':
#                 ref_col_name = v['label'].replace('  ',' ')
#         for i,head in enumerate(header_column_wise_data):
#             head['words'] = sorted(head['words'],key = lambda x : (x['top'],x['left']))
#             header_name = ' '.join([word['word'] for word in head['words']])
#             #pass#print(header_name,ref_col_name)
#             if SequenceMatcher(None,clean_word(ref_col_name),clean_word(header_name)).ratio() > 0.75:
#                 #pass#print(i+1)
#                 return int(i+1)
#     except:
#         print(' no ref col')
#         pass

# def get_lines(json_data):
#
# def alignment(ocrData,json_data):
#
#     # for
# 	ocrDataRow = ocrDataLocal( T, L, R, B,ocrData)
# 	ocrDataColumn = ocrDataLocal( T, L, R, B,ocrData)
# 	lines = ocr_to_lines(ocrDataRow)
# 	column_word = ocr_to_lines(ocrDataColumn)[0]
# 	alignment = ''
#
# 	# check alignment
# 	x = range(data['top'],data['bottom'])
# 	xs = set(x)
# 	if(len(line) > 1):
# 		y_top = range(line[0]['top'],line[0]['bottom'])
# 		y_bottom = range(line[-1]['top'],line[-1]['bottom'])
# 		if(len(xs.intersection(y_top)))
# 			alignment = 'top'
# 		elif(len(xs.intersection(y_bottom)))
# 			alignment = 'bottom'
# 		else:
# 			alignment = 'center'
# 	else:
# 		alignment = 'top'
# 	return alignment

def get_algo_horizontals(ocrData, header_vers, headerBottom, headerLeft, headerRight, main_table_bottom, ref_col,
                         alignment='top'):
    '''Boundaries for horizontal_lines'''
    L = header_vers[ref_col - 1][0][0]
    R = header_vers[ref_col][0][0]
    # L = header_vers[-2][0][0]
    # R = header_vers[-1][0][0]
    T = headerBottom
    B = main_table_bottom
    # pass#print('Last Column boundaries',L,R,T,B)
    horizontal_lines = []
    column_words = ocrDataLocal(T, L, R, B, ocrData)

    ln = ""
    for data in column_words:
        ln += data['word'] + ' '
    '''check for alignment '''

    ocr_data_table = ocrDataLocal(headerBottom, headerLeft, headerRight, main_table_bottom, ocrData)

    # if alignment != '':
    '''If alignment is center'''
    if alignment == 'center':
        horizontal_lines = line_space_hors(ocrData, header_vers, ref_col)
    else:
        line_splits = split_lines_alignment(L, R, T, B, column_words, alignment)
        logging.debug(f'Probable no. of horizontal_lines{len(line_splits)}')
        for splits in line_splits:
            for word in ocr_data_table:
                word_ = word['word']
                word_height = word['bottom'] - word['top']
                if (word['top'] + int(word_height * 0.3) <= splits[0][1] <= word['bottom'] - int(
                        word_height * 0.3)):
                    logging.debug(f'horiontal line striking {word_}../.extending the line above')
                    splits[0][1] = word['top']
                elif word['top'] + int(word_height * 0.7) <= splits[0][1] <= word['bottom']:
                    logging.debug(f'horiontal line striking {word_}...extending the line below')
                    splits[0][1] = word['bottom']
            horizontal_lines.append(splits[0][1])
    # pass#print('algo horizontals ', horizontal_lines)
    return horizontal_lines


def validating_horizontal_cv_lines(ocrData, cv_hors, algo_hors, headerLeft, headerRight, headerBottom,
                                   main_table_bottom, header_vers, ref_col):
    ''' Validation 1 -
                If cv-line strikes any line items'''
    # pass#print('before val 1 hors', cv_hors)
    cv_hors_new = []
    for hor in cv_hors:
        for word in ocrData:
            if hor not in range(word['top'], word['bottom']) and hor not in cv_hors_new:
                cv_hors_new.append(hor)
            else:
                break
    # for i in range(len(cv_hors) -1):

    cv_hors = cv_hors_new
    cv_hors_new = []

    # pass#print('before val 2 hors', cv_hors)
    ''' Validation 2 -
            '''
    for i in range(len(cv_hors) - 1):

        ocr_between_hors = ocrDataLocal(cv_hors[i], headerLeft, headerRight, cv_hors[i + 1], ocrData)
        if len(ocr_between_hors):
            cv_hors_new.append(cv_hors[i])
    cv_hors_new.append(cv_hors[len(cv_hors) - 1])
    cv_hors = cv_hors_new

    cv_hors_new = []
    ''' Validation 3 -
            if CV line not there, use algo lines
    '''
    logging.debug(f'before validation 3 hors {cv_hors}')
    L = header_vers[ref_col - 1][0][0]
    R = header_vers[ref_col][0][0]
    T = headerBottom
    B = main_table_bottom
    column_words = ocrDataLocal(T, L - 3, R + 3, B, ocrData)
    column_words = ocr_to_lines(column_words)
    for i in range(len(column_words) - 1):
        t = column_words[i]['bottom']
        b = column_words[i + 1]['top']
        # logging.debug(f'{column_words[i]['word']},'t',{t,'\n','b',b,column_words[i]['word'])
        algo_line = int((t + b) / 2)
        for line in algo_hors:
            if (line in range(t, b)):
                algo_line = line
                logging.debug(f'algo hor line found \n \n {algo_line}')
                break
        # cv_verticals = [cv_ver if cv_ver in range(l,r) else algo_line for i in range(len(cv_verticals))]
        cv_line = -1
        for line in cv_hors:
            if line in range(t, b):
                cv_line = line
                break
        if (cv_line == -1):
            logging.debug('Algo line made it through')
            cv_hors_new.append(algo_line)
        else:
            logging.debug('CV lines are the best !!!')
            cv_hors_new.append(cv_line)

    cv_hors = cv_hors_new

    return cv_hors


def get_horizontal_lines(table_img, rf, ocrData, header_hors, header_vers, headerLeft, headerRight, headerBottom,
                         main_table_bottom, ref_col, alignment='top'):
    line_item_lines = []
    horizontal_lines = []

    cv_hors = get_cv_lines(table_img, rf, 10)[0]
    # print('cv hors',cv_hors)
    cv_hors = [cv_hor + headerBottom for cv_hor in cv_hors if cv_hor]
    logging.debug(f'cv hors{cv_hors}')

    for h in header_hors:
        horizontal_lines.append([[headerLeft, h[0][1]], [headerRight, h[0][1]]])
        horizontal_lines.append([[headerLeft, main_table_bottom], [headerRight, main_table_bottom]])
    horizontal_lines.append([[headerLeft, main_table_bottom], [headerRight, main_table_bottom]])

    try:
        algo_hors = get_algo_horizontals(ocrData, header_vers, headerBottom, headerLeft, headerRight, main_table_bottom,
                                         ref_col)
        logging.debug('algo hors', algo_hors)

        '''
            Validation of horizontal lines
        '''
        if (len(cv_hors)):
            hors = validating_horizontal_cv_lines(ocrData, cv_hors, algo_hors, headerLeft, headerRight, headerBottom,
                                                  main_table_bottom, header_vers, ref_col)
        else:
            hors = algo_hors
        # pass#print(' hors after validation',hors)
        for hor in hors:
            horizontal_lines.append([[headerLeft, hor], [headerRight, hor]])
        line_item_lines = horizontal_lines.copy()

        '''Drawing top and bottom horizontal lines of maintable'''

        horizontal_lines = sorted(horizontal_lines, key=lambda x: x[0][1])

        line_item_lines.append([[headerLeft, main_table_bottom], [headerRight, main_table_bottom]])
        line_item_lines.insert(0, [[headerLeft, headerBottom], [headerRight, headerBottom]])

    except Exception as e:
        # logger.error(' No horizontal lines found in table :  {}'.format(e))
        logging.debug(f'{horizontal_lines},{e}')
    return horizontal_lines, line_item_lines


def row_splits(ocrData, json_data, horizontal_lines, vertical_lines, line_item_lines):
    try:
        split_cols = []
        for k, v in json_data.items():

            if (v['split_lines'] != 'true' and v['split_lines'] != 'false' and v['split_lines'] != '' and v[
                'split_lines'] != [] and k != 'h0'):
                split_cols.append(v['split_lines'])
        split_column_nos = []

        for each_col in split_cols:
            for each_val in each_col:
                split_column_nos.append(each_val[2:])

        if split_column_nos:
            for col_no in split_column_nos:
                col_no = int(col_no)
                split_range = [vertical_lines[col_no][0][0], vertical_lines[col_no + 1][0][0]]
                for i in range(1, len(line_item_lines)):
                    L = int(split_range[0])
                    R = int(split_range[1])
                    T = int(line_item_lines[i - 1][0][1])
                    B = int(line_item_lines[i][0][1])
                    column_words = ocrDataLocal(T, L, R, B, ocrData[i])
                    lines = split_lines(L, R, T, B, column_words)
                    horizontal_lines.extend(lines)
    except Exception as e:
        logging.debug(f'{e}')
        # logger.error(' row splits not found :  {}'.format(e))

    return horizontal_lines


def nested_columns(ocrData, table_img, col_children_no, header_column_wise_data, horizontal_lines, vertical_lines,
                   headerLeft, headerRight, main_table_bottom, img_=None, rf=None):
    nested_flag = False
    # img_ = cv2.imread(imgpath)
    # img_ = img
    # w,h,c = img_.shape
    # rf = 670/int(h)
    # img_ = cv2.resize(img_, (0,0), fx=rf, fy=rf)
    try:
        inv_width = max(ocrData, key=lambda x: x['right'])['right']
        word_space = get_word_space(ocrData)
        # #pass#print('length of header data ', len(header_column_wise_data))
        for key, value in col_children_no.items():
            split_vers = []
            idx = key[1:]
            # #pass#print('\n'*50,idx)
            idx = int(idx)
            header_data = header_column_wise_data[idx - 1]['words']
            # #pass#print(header_data)
            col_left = int(headerLeft)
            col_right = int(headerRight)
            try:
                header_left = header_column_wise_data[idx - 1]['coords'][1]
                header_right = header_column_wise_data[idx - 1]['coords'][2]
                header_top = header_column_wise_data[idx - 1]['coords'][0]
                header_bottom = header_column_wise_data[idx - 1]['coords'][3]
                for k, v in value.items():
                    if v:
                        nested_flag = True

                    main_heading = k
                    sub_heading_words = v
                    split_top = 0
                    # #pass#print(v)
                    for ver in vertical_lines:
                        if (ver[0][0] > header_right):
                            col_right = ver[0][0]
                            break
                    # if v == ['PF', 'ESI', 'Prof  essio  nal  Tax', 'Labo  ur  We  If  are  fund', 'Adva  nee/  Other  Dedu  ction  s', 'Fines']:
                    # #pass#print(len(vertical_lines))
                    # col_left = max(vertical_lines , key= lambda x : x[0][0] - header_left)[0][0]
                    temp = 100000
                    for i in range(len(vertical_lines) - 1, -1, -1):
                        ver = vertical_lines[i]
                        if abs(ver[0][0] - header_left) < temp:
                            temp = abs(ver[0][0] - header_left)
                            col_left = ver[0][0]

                    # for i in range(len(vertical_lines)-1,-1,-1):
                    #     #pass#print(i)
                    #     ver = vertical_lines[i]
                    #     cv2.line(img_,(ver[0][0] ,0),(ver[0][0],4000),(0,i*55,255),2)
                    #     cv2.imshow('col left',img_)
                    #     cv2.waitKey()
                    #     if(ver[0][0]<header_left):
                    #         col_left = ver[0][0]
                    #         break
                    # finding split top
                    main_heading_words = [main_heading]
                    main_ocr_data = ocrDataLocal(header_top, header_left, header_right, header_bottom, ocrData)
                    header_words_data, line_number, lines = finding_baseline(main_heading_words, main_ocr_data)

                    line_number = 0
                    # if(img_ is not None):
                    #     cv2.rectangle(img_,(header_left,header_top),(header_right,header_bottom),(0, 0, 255),2)
                    #     # cv2.line(img_,(col_left,0),(col_left,4000),(255,0,255),2)
                    #     cv2.namedWindow('region',cv2.WINDOW_NORMAL)
                    #     cv2.resizeWindow('region', 1200,1200)
                    #     cv2.imshow('region',img_)
                    #
                    #     cv2.waitKey(0)
                    main_words_data = header_proximity_finder(main_heading_words, line_number, lines)
                    main_header_rect = header_column_wise_data_function(main_heading_words, main_words_data, inv_width)[
                        0]
                    # #pass#print('in nested header')
                    # #pass#print('main header rect', main_header_rect)
                    split_top = main_header_rect[0]['coords'][3]
                    horizontal_lines.append([[col_left, split_top], [col_right, split_top]])

                    coords = main_header_rect[0]['coords']
                    # cv2.rectangle(img_,(coords[1],coords[0]),(coords[2],coords[3]),(0, 0, 255),2)

                    # finding nested columns

                    line_words_data = ocrDataLocal(split_top, header_left, header_right, header_bottom, ocrData)
                    # #pass#print('before nested subheader')
                    sub_header_rects = header_column_wise_data_function(sub_heading_words, line_words_data, inv_width)[
                        0]
                    # #pass#print('in nested subheader')
                    # nested_columns_data.append(sub_header_rects)
                    # img_ = cv2.imread(imgpath)
                    # w,h,c = img_.shape
                    # rf = 670/int(h)
                    # img_ = cv2.resize(img_, (0,0), fx=rf, fy=rf)
                    # for head in sub_header_rects:
                    #     coords = head['coords']
                    #     cv2.rectangle(img_,(coords[1],coords[0]),(coords[2],coords[3]),(0, 0, 255),2)
                    #     cv2.namedWindow('nested header',cv2.WINDOW_NORMAL)
                    #     cv2.resizeWindow('nested header', 1200,1200)
                    #     cv2.imshow('nested header',img_)
                    #     cv2.waitKey(0)

                    # for rect in sub_header_rects:
                    #     # right = int(max(rects, key = lambda x : x['right'])['right'])
                    #     right = rect['coords'][2]
                    #     split_vers.append([[right , int(split_top)], [right, int(main_table_bottom)]])
                    # split_vers = sorted(split_vers, key = lambda x : x[0][0])
                    # split_vers = split_vers[:-1]

                    ocr_data_subheader = ocrDataLocal(header_top, col_left, col_right, main_table_bottom, ocrData)
                    img = np.zeros((800, 800, 3), np.uint8)
                    img[:] = (0, 0, 255)
                    # to include : handle local area of image
                    # #pass#print('ocr_data_subheader',ocr_data_subheader)
                    split_vers = vertical_slider(table_img, rf, sub_header_rects, ocr_data_subheader, col_left,
                                                 col_right, header_bottom, header_top, main_table_bottom,
                                                 sub_heading_words, word_space, img_)
                    # img_ = cv2.imread(imgpath)
                    # img_ = img.copy()
                    # w,h,c = img_.shape
                    # rf = 670/int(h)
                    # img_ = cv2.resize(img_, (0,0), fx=rf, fy=rf)
                    # for v in split_vers:
                    #     # coords = head['coords']
                    #     cv2.line(img_,(v[0][0],v[0][1]),(v[1][0],v[1][1]),(0, 0, 255),2)
                    # cv2.namedWindow('Header',cv2.WINDOW_NORMAL)
                    # cv2.resizeWindow('Header', 1200,1200)
                    # cv2.imshow('Header',img_)
                    # cv2.waitKey(0)
            except Exception as e:
                logging.debug(f'vertical col split exception : {e}')
    except Exception as e:
        # ('vertical split exceptions :  {}'.format(e))
        # split_vers_new = []
        # for v in split_vers:
        #     split_vers_new.append([[int(v[0][0]), split_top], [int(v[0][0]), int(main_table_bottom)]])
        # if(len(split_vers_new)):
        #     vertical_lines.extend(split_vers_new)
        pass

    return horizontal_lines, vertical_lines, nested_flag


'''Utils '''


def get_alias_names(json_data):
    alias_names = []
    for k, v in json_data.items():
        if k.startswith('v'):
            if k[-2] != '.':
                if v['alias']:
                    alias_names.append(v['alias'])
                else:
                    alias_names.append(re.sub(' +', ' ', v['label']))

    for k, v in json_data.items():
        if k.startswith('v'):
            if k[-2] == '.':
                if v['alias']:
                    alias_names.append(v['alias'])
                else:
                    alias_names.append(re.sub(' +', ' ', v['label']))

    return alias_names


def get_req_cols(json_data):
    req_cols = []
    for k, v in json_data.items():
        if k.startswith('v') and v['del'] == 'no':
            if k[-2] != '.':
                req_cols.append(int(k[1:]))

    return req_cols


def open_pdf(file_path, batch=10):
    try:
        i = 0
        pages = [1]
        final_pages = []
        while len(pages):
            pages = convert_from_path(file_path, 300, first_page=i, last_page=i + batch, thread_count=1)
            i += batch + 1
            final_pages.extend(pages)
        return final_pages
    except Exception as e:
        logging.debug(f'open-pdf{e}')


def to_image(img, file_path, extension, file_no=None):
    file_name = ''
    for idx, page in enumerate(img):
        if idx == file_no:
            file_name = file_path.rsplit(extension, 1)[0] + '_' + str(idx) + '.jpg'
            page.save(file_name, 'JPEG')
            logging.debug(f'saving as{file_name}')
    return file_name


# def to_image_wand(img,file_path,extension,file_no = None):
#
#     print('Converting {} to images'.format(file_path))
#     for idx, page_wand_image in enumerate(img):
#         if idx == file_no:
#             print(idx)
#             page_wand_image.background_color = Color("white")
#             page_wand_image.alpha_channel = 'remove'
#             file_name = file_path.split('.pdf')[0] + '_' + str(idx) + '.jpg'
#             if not os.path.isfile(file_name):
#                 page_wand_image.save(filename=file_name)
#                 print('saving')
#     return file_name

# def open_pdf_wand(file_path):
#     page_wand_image_seq = []
#     with WI(filename=file_path, resolution=300) as img:
#         for image_seq in img.sequence:
#             page_wand_image_seq.append(WI(image_seq))
#         return page_wand_image_seq

def del_temp_images(file_path):
    if os.path.exists(file_path):
        # pass#print('Removing temp images: ',file_path)
        os.remove(file_path)
    else:
        # pass#print("The file does not exist")
        pass


def get_imgpath(file_name, extension, i):
    imgpath = DEFAULT_IMGPATH + file_name
    imgpath = imgpath.split('.' + extension)[0] + '_' + str(i) + '.jpg'
    return imgpath


def check_multipage(json_data):
    multi_page_table = False
    for k, v in json_data.items():
        # if(k == 'h0' and v['repeatable'] == 'true'):
        if k == 'headerCheck' and v == True:
            multi_page_table = True
    return multi_page_table


def get_ocr_data(ocr_data_list, json_data, header_list):
    try:
        scored_ocr_list = []
        for pg_no, ocr_data in enumerate(ocr_data_list):
            ocr_data_string = json.dumps(ocr_data)
            score = 0
            for each_header in header_list:
                if (each_header in ocr_data_string):
                    score += 1
            scored_ocr_list.append([score, ocr_data, pg_no])

        multi_page_table = check_multipage(json_data)
        page_no = get_pageno(json_data)
        if multi_page_table:
            ocrData = ocr_data_list
        else:
            ocrData = [ocr_data_list[page_no]]
    except Exception as e:
        logging.debug(f'Error on line {sys.exc_info()[-1].tb_lineno}', type(e).__name__, e)
    return ocrData, multi_page_table, page_no


def get_pageno(json_data):
    page_no = 0
    try:
        for k, v in json_data.items():
            if k.startswith('h'):
                page_no = int(v['page'])
                break
    except:
        logging.debug('page no not found')
        page_no = 0

    return page_no


''' SUB header functions'''


def find_subheaders(ocrData, subheader_words, header_bottom, invoice_left, invoice_right, main_table_bottom, img=None):
    subheader_data_array = []
    run = True
    T = header_bottom
    L = invoice_left
    R = invoice_right
    B = main_table_bottom
    # #pass#print('ocr data ')
    # ln = ''
    # for data in ocrData:
    #     ln += data['word'] + ' '
    # #pass#print(ln)
    # img2 = img.copy()
    while (run):
        haystack = ocrDataLocal(T, L, R, B, ocrData)
        # pass#print('haystack')
        ln = ''
        # img3 = img2.copy()
        for data in haystack:
            ln += data['word'] + ' '
            # cv2.rectangle(img3, (data['left'], data['top']), (data['right'], data['bottom']), (0,0,255), 2)
        # cv2.imshow('ocr data', img3)
        # cv2.waitKey()
        # pass#print(ln)
        # words = subtable_helper(haystack, subheader_words)
        _top, _bottom, _left, _right, words = match_list(subheader_words, haystack)
        # pass#print('wordsasasaad', words)
        # pass#print(_top, _left, _right, _bottom)

        if img is not None:
            cv2.rectangle(img, (_left, _top), (_right, _bottom), (0, 0, 255), 2)
            cv2.namedWindow('igg', cv2.WINDOW_NORMAL)
            cv2.resizeWindow('igg', 1200, 1200)
            cv2.imshow('igg', img)
            cv2.waitKey()

        if (_top == -1):
            run = False
        else:
            # T = int(max(words, key = lambda x : x['bottom'])['bottom'])
            # B = _top - 5
            T = _bottom + 2
            subheader_data_array.append([_top, _left, _right, _bottom])
    # pass#print('sub header data array ', subheader_data_array)
    return subheader_data_array


def return_subheader_row(subheader, ocrData, img=None):
    invoice_left = int(min(ocrData, key=lambda x: x['left'])['left'])
    invoice_right = int(max(ocrData, key=lambda x: x['right'])['right'])
    # cv2.rectangle(I, (invoice_left, subheader[0]-5), (invoice_right, subheader[3]+5), (0,0,255), 2)
    # cv2.namedWindow('igg',cv2.WINDOW_NORMAL)
    # cv2.resizeWindow('igg', 1200,1200)
    # cv2.imshow('igg',I)
    # cv2.waitKey()
    # #pass#print('ocrdata  for subheader',ocrData)
    subheader_row = ocrDataLocal(subheader[0] - 5, invoice_left, invoice_right, subheader[3] + 5, ocrData)
    str = '<b>'
    for data in subheader_row:
        str += data['word'] + ' '
    str += '</b>'
    # pass#print('sub header ocr : ', str)
    return str


def remove_subheader_ocr(ocrData, subheader_data_array):
    ocr_data_new = []
    # ln = ' '
    # for data in ocr_data_new:
    #     ln += data['word'] + ' '
    # #pass#print(' ocr dataa new : ', ln)

    for coords in subheader_data_array:
        ocr_data_new = []
        for data in ocrData:
            # #pass#print(data['word'])
            if (data['top'] >= coords[0] - 5 and data['bottom'] <= coords[3] + 5):
                pass
            else:
                ocr_data_new.append(data)
        ocrData = ocr_data_new

    ln = ' '
    for data in ocr_data_new:
        ln += data['word'] + ' '
    # pass#print(' ocr dataa new : ', ln)
    return ocr_data_new


def get_subheader_words(json_data):
    needles = []
    for k, v in json_data.items():
        if k.startswith('h') and type(v) is dict and v['type'] == 'maintable - sub - header':
            for key, value in json_data.items():
                if (key.startswith(k) and key != k):
                    str = value['label']
                    str = str.replace('  ', ' ')
                    needles.append(str)
    return needles


def gst_preprocessing(extracted_data_maintable):
    extracted_data_maintable_new = []
    for i, row in enumerate(extracted_data_maintable):
        row_string = ' '.join(row[i][0] for i in range(len(row)))
        row_string = row_string.replace('  ', ' ')
        row_string = clean_word(row_string)
        if i == 0:
            extracted_data_maintable_new.append(row)
        else:
            if 'gst' in row_string:
                # pass#print('removing', row_string)
                pass
            else:
                extracted_data_maintable_new.append(row)

    return extracted_data_maintable_new


def add_default_columns(extracted_data_maintable, column_list, nested_flag, req_alias_names):
    ''' input : list of default col header words to be added'''
    # pass#print('add_default_columns')
    for i, row in enumerate(extracted_data_maintable):
        for col in column_list:
            add_dummy_flag = True
            col_str = col[3:-4]
            if any(col_str in s for s in req_alias_names):
                add_dummy_flag = False
            if (add_dummy_flag):
                if (i == 0):
                    if (nested_flag):
                        row.insert(len(row) - 1, [col, 2, 1])
                    else:
                        row.insert(len(row) - 1, [col, 1, 1])
                    # #pass#print(col,row)
                elif (nested_flag and i == 1):
                    pass
                else:
                    # pass#print('col',col_str)
                    if (col_str == "Quantity"):
                        row.insert(len(row) - 1, ['1', 1, 1])
                    else:
                        row.insert(len(row) - 1, ['', 1, 1])
                # #pass#print(col,row)
        # #pass#print(row)
    return extracted_data_maintable


def find_pos(st_header, header_data_row):
    for i, h in enumerate(header_data_row):
        # pass#print('h0',h[0])
        h_copy = h[0][3:-4]
        if (st_header == h_copy):
            return i
    return -1


def shuffle(extracted_data_maintable):
    extracted_data_maintable_new = [[] for row in extracted_data_maintable]
    static_header_list = ['Item Description', 'Quantity', 'HSN/SAC', 'Tax', 'Project Code', 'Line Amount']
    for st_header in static_header_list:
        # pass#print('static header', st_header)
        pos = find_pos(st_header, extracted_data_maintable[0])
        # pass#print('found at position', pos)
        if (pos is not -1):
            for i, row in enumerate(extracted_data_maintable):
                extracted_data_maintable_new[i].append(extracted_data_maintable[i][pos])
        else:
            for i, row in enumerate(extracted_data_maintable):
                extracted_data_maintable_new[i].append(['', 1, 1])
            extracted_data_maintable_new[0][-1] = [st_header, 1, 1]
    # pass#print('extracted_data_maintable_new: ',extracted_data_maintable_new)
    return extracted_data_maintable_new


def get_add_columns_list(cols_num):
    if cols_num > 2:
        columns = ['<b>HSN/SAC</b>', '<b>GST</b>', '<b>Project Code</b>']
    else:
        columns = ['<b>Quantity</b>', '<b>HSN/SAC</b>', '<b>Tax</b>', '<b>Project Code</b>']
    return columns


def complex_table_prediction(ocr_data_list, file_name, json_data=None):
    '''Convert or pdf to jpg'''
    global parameters

    file_path = DEFAULT_IMGPATH + file_name

    logging.debug(f'file name{file_name}')
    try:
        start_pdf = time.time()
        wand_pdf = open_pdf(DEFAULT_IMGPATH + file_name)
        end_pdf = time.time()
        logging.debug(f'opened pdf in {end_pdf - start_pdf}s')

    except Exception as e:
        logging.debug(f'wand-pdf failed{e}')
        wand_pdf = ''

    # if json_data:
    json_data_list = [json_data]
    # else:
    #     get_json_data = "SELECT table_data from table_db where template_name = '{}'".format(template_name)
    #     json_data_list = execute_query(get_json_data)
    #     json_data_list = [json.loads(data[0]) for data in json_data_list]

    table_final_data = []

    for table_num in range(len(json_data_list)):

        # pass#print('#'*50,'Predicting {} Table'.format(table_num),'#'*50)

        try:
            # pass#print('getting json data')
            json_data = json_data_list[table_num]
            try:
                json_data = json_data[0]
                # lines = json_data[1]
            except:
                pass

            '''
                --------------------------------Get req_cols and alias_names from database ------------------------
            '''

            logging.debug(f'json data{json_data}')
            req_cols = get_req_cols(json_data)
            alias_names = get_alias_names(json_data)

            req_alias_names = [alias_names[i - 1] for i in req_cols]

            header_list, col_children_no = get_header_list(json_data)
            # findinf header in ocrdata
            # pass#print('#'*50,'Got Header List','#'*50)

            ocrData, multi_page_table, page_no = get_ocr_data(ocr_data_list, json_data, header_list)
            # pass#print('#'*50,'Got OCR Data','#'*50)
            # pass#print('length of ocr list',len(ocrData))
            # logger.info("Finding Header Data")

            '''
                --------------------------------Init the default final output -----------------------------------------

            '''
            horizontal_lines_ui = []
            vertical_lines_ui = []

            final_tables = []
            multi_maintables = []
            multi_footers = []
            ''' ------------------------------------------------------------------------------------------------------'''

            '''
                ---------------------------------   Main stuff starts here ---------------------------------------------

            '''
            for i in range(len(ocrData)):
                ''' Create temp images of tiff and pdf'''
                try:
                    img_type = 'jpg'
                    imgpath = DEFAULT_IMGPATH + file_name
                    try:
                        if not file_name.endswith('.jpg'):
                            extension = file_name.rsplit('.', 1)[-1]
                            # if sys.platform == 'linux':
                            imgpath = to_image(wand_pdf, imgpath, extension, page_no)
                            logging.debug('Using pdf2image')
                            # elif sys.platform == 'win32':
                            #     imgpath = to_image_wand(wand_pdf,imgpath,extension,page_no)
                            #     print('Using Wand')
                            # imgpath = to_image(wand_pdf ,imgpath,extension,i)
                    except Exception as e:
                        logging.debug(f'{e}')
                        pass

                    try:
                        logging.debug(f'image path{imgpath}')

                        '''sort the ocr '''
                        ocrData[i] = sort_ocr(ocrData[i])
                        # #pass#print(i,'\n'*50)
                        # pass#print('imgpath',imgpath)
                        try:
                            img = cv2.imread(imgpath)
                            w, h = img.shape[:2]

                        except Exception as e:
                            img = np.zeros((1000, 1000, 3), np.uint8)
                            logging.debug('loading default blank image')
                            w, h = img.shape[:2]
                        rf = parameters['default_img_width'] / int(h)
                        # print('rf table',rf)
                        img_ = cv2.resize(img, (0, 0), fx=rf, fy=rf)
                        ocr_img = img_.copy()
                        ocr_img_copy = img_.copy()
                        # table_img = img_.copy()
                        # cv2.imshow('img',img)
                        # cv2.waitKey()
                        # cv2.destroyAllWindows()
                        # z = i

                        ''' ----------------------------------  Debug ocr data ------------------------------------------'''

                        # for word in ocrData[i]:
                        #     cv2.rectangle(ocr_img,(word['left'],word['top']),(word['right'],word['bottom']),(0,0,255),2)
                        # cv2.imshow('ocred words',ocr_img)
                        # cv2.waitKey()
                        # cv2.destroyAllWindows()

                        '''
                            ---------------------------------------------------------------------------------------------------------
                        '''
                        # pass#print('#'*50,'Header Stuff starts','#'*50)

                        header_words_data, line_number, lines = finding_baseline(header_list, ocrData[i])
                        # logger.debug('Header words from ocr {}'.format(header_words_data))

                        line_words_data = header_proximity_finder(header_list, line_number, lines, img)

                        invoice_left = min(ocrData[i], key=lambda x: x['left'])['left']
                        invoice_right = max(ocrData[i], key=lambda x: x['right'])['right']
                        invoice_top = min(ocrData[i], key=lambda x: x['top'])['top']
                        invoice_bottom = max(ocrData[i], key=lambda x: x['bottom'])['bottom']
                        header_column_wise_data, pseudo_header_list = header_column_wise_data_function(header_list,
                                                                                                       line_words_data,
                                                                                                       invoice_right,
                                                                                                       img_)

                        try:
                            pseudo_y_axis = int(lines[line_number][0]['top'])
                            # pass#print('pseuod y axis: ', pseudo_y_axis)
                            header_column_wise_data = make_pseudo_rectangle(pseudo_header_list, header_column_wise_data,
                                                                            invoice_left, invoice_right, pseudo_y_axis,
                                                                            img_)
                        except Exception as e:
                            logging.debug(f'Pseudo Rectangle Failed:{e}')

                        headerTop, headerLeft, headerRight, headerBottom = finding_header_boundaries(
                            header_column_wise_data)

                        #########################         Header Rectangles Debugging            ############################################
                        # #pass#print(' i am header_column_wise_data ', header_column_wise_data )
                        # imgpath_multi = '/home/lohith/ACE-platform-master/file_path0.jpg'
                        # img_ = cv2.imread(imgpath_)
                        # w,h,c = img.shape
                        # rf = 670/int(h)
                        # img = cv2.resize(img, (0,0), fx=rf, fy=rf)
                        # for head in header_column_wise_data:
                        #     coords = head['coords']
                        #     cv2.rectangle(img_,(coords[1],coords[0]),(coords[2],coords[3]),(0, 0, 255),2)
                        #     cv2.namedWindow('Header',cv2.WINDOW_NORMAL)
                        #     cv2.resizeWindow('Header', 1200,1200)
                        #     cv2.imshow('Header',img_)
                        #     cv2.waitKey(0)

                        extracted_data_subtable_kv = predict_kv_subtable(ocrData[i], json_data)
                        extracted_data_subtable_hf = predict_hf_subtable(ocrData[i], json_data)

                        '''Finding footer '''
                        # pass#print('#'*50,'Footer Stuff starts','#'*50)

                        foot_path = ocrDataLocal(headerBottom, invoice_left, invoice_right, invoice_bottom, ocrData[i])
                        # #pass#print('foot_path',foot_path)
                        footers_dict = get_footers_dict(json_data)
                        # pass#print(footers_dict)
                        footer_tops = []
                        extracted_data_footer = []

                        if not footers_dict:
                            main_table_bottom = invoice_bottom
                        else:
                            for footer_type, info in footers_dict.items():
                                for no in range(len(info)):
                                    label = info[no][0]
                                    # display = info[no][1]
                                    display = 'false'
                                    if footer_type == 'horizontal key - values':
                                        extracted_data_hkv_footer, hkv_top = get_hor_kv_footer(label, ocrData[i], img_)
                                        footer_tops.append(hkv_top)
                                        if display == 'true':
                                            extracted_data_footer.append(extracted_data_hkv_footer)
                                    elif footer_type == 'vertical key - values':
                                        extracted_data_vkv_footer, vkv_top = get_ver_kv_footer(label, foot_path)
                                        footer_tops.append(vkv_top)
                                        if display == 'true':
                                            extracted_data_footer.append(extracted_data_vkv_footer)

                                    elif footer_type == 'Simple Single Key-value':
                                        # pass#print('finding footer for :',i)
                                        logging.debug('in simple footer')
                                        extracted_data_skv_footer, skv_top = get_simple_kv_footer(label, foot_path)
                                        # print('extracted_data_skv_footer',extracted_data_skv_footer)
                                        footer_tops.append(skv_top)
                                        if display == 'true':
                                            extracted_data_footer.append(extracted_data_skv_footer)

                                    # elif footer_type == 'Main Table Matrix':
                                    #     extracted_data_fm_footer,fm_top = get_footer_matrix(foot_path,label,header_column_wise_data,alias_names,img_)
                                    #     footer_tops.append(fm_top)
                                    #     if display == 'true':
                                    #         extracted_data_footer.append(extracted_data_fm_footer)
                                    elif footer_type == 'Main Table Matrix':
                                        fm_top = get_footer_matrix_top(foot_path, label)
                                        footer_tops.append(fm_top)
                                        # if display == 'true':
                                        #     extracted_data_footer.append(extracted_data_fm_footer)

                            # extracted_data_footer = predict_maintable_footer(ocrData[i],json_data,i,headerBottom)[0]
                            # main_table_bottom = predict_maintable_footer(ocrData[i],json_data,i,headerBottom)[1]
                            # extracted_data_footer = extracted_data_hkv_footer
                            ''' Main table bottom | max of tops of all footers'''
                            # footer_tops = [hkv_top,vkv_top,skv_top,fm_top]
                            # pass#print('footers',extracted_data_footer)
                            try:
                                main_table_bottom = get_maintable_footer(footer_tops)
                            except:
                                logging.debug('taking default as invoice bottom')
                                main_table_bottom = invoice_bottom
                            # pass#print('main_table_bottom',main_table_bottom)
                        # main_table_bottom = 636

                        ''' #################################### MainTable SUBHEADER ALGO #################################################'''
                        # subheader_words = '''from database'''
                        subheader_words_list = get_subheader_words(json_data)
                        subheader_data_arrays = []
                        for subheader_words in subheader_words_list:
                            subheader_data_arrays.append(
                                find_subheaders(ocrData[i], subheader_words, headerBottom, invoice_left, invoice_right,
                                                main_table_bottom))
                        ocr_data_old = ocrData[i]
                        for subheader_data_array in subheader_data_arrays:
                            if len(subheader_data_array):
                                ocrData[i] = remove_subheader_ocr(ocrData[i], subheader_data_array)

                        # pass#print('#'*70,i,'#'*70)
                        # for word in ocrData[i]:
                        #     cv2.rectangle(img_,(word['left'],word['top']),(word['right'],word['bottom']),(0,0,255),2)
                        # cv2.imshow('ocr data',img_)
                        # cv2.waitKey()

                        '''Correction of Vertical Lines'''
                        # pass#print('#'*50,'Vertical lines Stuff starts','#'*50)

                        table_img = img[int(headerTop / rf):int(headerBottom / rf), :]
                        # table_img = img_
                        # cv2.imshow('table image ',table_img)
                        # cv2.waitKey()
                        # cv2.destroyAllWindows()
                        header_hors, header_vers = header_lines(table_img, rf, header_column_wise_data, headerTop,
                                                                headerLeft, headerRight, headerBottom,
                                                                main_table_bottom, ocrData[i], header_list,
                                                                header_words_data)
                        headerLeft = header_vers[0][0][0]
                        headerRight = header_vers[-1][0][0]

                        # pass#print('header_vers',header_vers)

                        # vertical lines main_table_footer
                        '''Limiting Vertical Lines to top-of-footer i.e main_table_bottom'''

                        vertical_lines = []
                        for v_line in header_vers:
                            tem = v_line.copy()
                            tem[1][1] = main_table_bottom
                            vertical_lines.append(tem)

                        # logger.debug('Vertical Lines after Correction {}'.format(vertical_lines))

                        vers_x = [ver[0][0] for ver in vertical_lines]
                        # pass#print(vers_x)
                        '''Matrix type footer flow changed '''

                        for footer_type, info in footers_dict.items():
                            for no in range(len(info)):
                                label = info[no][0]
                                # display = info[no][1]
                                display = 'false'
                                if footer_type == 'Main Table Matrix':
                                    # pass#print('matrix detected')
                                    extracted_data_fm_footer, _ = get_footer_matrix_(foot_path, label, vers_x,
                                                                                     header_column_wise_data,
                                                                                     alias_names, img_)
                                    if display == 'true':
                                        extracted_data_footer.append(extracted_data_fm_footer)

                        # pass#print('#'*50,'Horiontal lines Stuff starts','#'*50)

                        table_img_hors = img[int(headerBottom / rf):int(main_table_bottom / rf), :]
                        # cv2.imshow('table_img_hors',table_img_hors)
                        # cv2.waitKey()
                        # ref_col = get_ref_col(json_data,header_column_wise_data)
                        ref_col = get_ref_col(json_data)
                        horizontal_lines, line_item_lines = get_horizontal_lines(table_img_hors, rf, ocrData[i],
                                                                                 header_hors, header_vers, headerLeft,
                                                                                 headerRight, headerBottom,
                                                                                 main_table_bottom, ref_col)

                        horizontal_lines = row_splits(ocrData[i], json_data, horizontal_lines, vertical_lines,
                                                      line_item_lines)

                        horizontal_lines = sorted(horizontal_lines, key=lambda x: x[0][1])

                        vertical_lines = sorted(vertical_lines, key=lambda x: x[0][0])

                        ''' Column splits nested columns'''

                        horizontal_lines, vertical_lines, nested_flag = nested_columns(ocrData[i], table_img,
                                                                                       col_children_no,
                                                                                       header_column_wise_data,
                                                                                       horizontal_lines, vertical_lines,
                                                                                       headerLeft, headerRight,
                                                                                       main_table_bottom, img_, rf)
                        horizontal_lines = sorted(horizontal_lines, key=lambda x: x[0][1])
                        vertical_lines = sorted(vertical_lines, key=lambda x: x[0][0])

                        '''Validations'''

                        header_data = get_header_data(header_vers, ocrData[i], headerTop, headerLeft, headerRight,
                                                      headerBottom)

                        '''Column-nature validation'''
                        try:
                            horizontal_lines, vertical_lines = column_nature_validation(ocrData[i], json_data,
                                                                                        header_data, vertical_lines,
                                                                                        horizontal_lines, header_data,
                                                                                        headerBottom, footer)
                        except Exception as e:
                            pass
                            # logger.error('column nature validation Failed :  {}'.format(e))
                        '''Suffix Validation'''
                        try:
                            horizontal_lines, vertical_lines = suffix_validation(ocrData[i], json_data, vertical_lines,
                                                                                 horizontal_lines, header_data,
                                                                                 headerBottom)
                            # # logger.info('Suffix validation successfull')
                        except Exception as e:
                            pass
                            # # logger.error('suffix validation broke : {}'.format(e))
                        '''Prefix Validation'''
                        try:
                            vertical_lines, horizontal_lines = prefix_validation(ocrData[i], json_data, vertical_lines,
                                                                                 horizontal_lines, header_data,
                                                                                 headerBottom)
                            # logger.info('Prefix validation successfull')
                        except Exception as e:
                            pass
                            # logger.error('prefix validation broke :  {}'.format(e))

                        extracted_data_maintable = []

                        # #pass#print(req_cols)
                        #
                        # w,h,c = img.shape
                        # rf = 670/int(h)
                        # img = cv2.resize(img, (0,0), fx=rf, fy=rf)
                        # hors_cv,vers_cv = get_cv_lines(img)
                        # for hor in hors_cv:
                        #     cv2.line(img,(0,hor),(4000,hor),(225,0,225),1)
                        # for hor in vers_cv:
                        #     cv2.line(img,(0,hor),(4000,hor),(225,0,225),1)
                        # for i,h in enumerate(horizontal_lines):
                        #     cv2.line(ocr_img_copy,(int(h[0][0]),int(h[0][1])),(int(h[1][0]),int(h[1][1])),(50, 0, 255),1)
                        # for i,v in enumerate(vertical_lines):
                        #     cv2.line(ocr_img_copy,(int(v[1][0]),int(v[0][1])),(int(v[1][0]),int(v[1][1])),(50, 0, 255),1)
                        # cv2.namedWindow('table',cv2.WINDOW_NORMAL)
                        # cv2.resizeWindow('table', 1200,1200)
                        # cv2.imshow('table',ocr_img_copy)
                        # cv2.waitKey(0)
                        # cv2.destroyAllWindows()
                        # #pass#print('#'*70,i,'#'*70)
                        # for word in ocrData[i]:
                        #     cv2.rectangle(ocr_img_copy,(word['left'],word['top']),(word['right'],word['bottom']),(0,0,255),2)
                        # cv2.imshow('ocr data removed',ocr_img_copy)
                        # cv2.waitKey()
                        # for coords in subheader_data_array:
                        #     cv2.rectangle(img_, (coords[1], coords[0]), (coords[2], coords[3]), (0,0,255), 2)
                        # cv2.imshow('sub header coords', img_)
                        # cv2.waitKey()
                        # #pass#print('\n'*50,ocrData[i],'\n'*50)

                        extracted_data_maintable = predict_maintable(ocrData[i], ocr_data_old, horizontal_lines,
                                                                     vertical_lines, headerBottom, req_cols,
                                                                     req_alias_names, subheader_data_arrays)
                        logging.debug(f'original shuffle{extracted_data_maintable}')
                        # column_list = get_add_columns_list(len(req_cols))
                        # extracted_data_maintable = add_default_columns(extracted_data_maintable, column_list, nested_flag, req_alias_names)
                        # print('befor shuffle',extracted_data_maintable)
                        # extracted_data_maintable = shuffle(extracted_data_maintable)
                        # print('after shuffle',extracted_data_maintable)
                        horizontal_lines = sorted(horizontal_lines, key=lambda x: x[0][1])
                        vertical_lines = sorted(vertical_lines, key=lambda x: x[0][0])
                        horizontal_lines_ui = copy.deepcopy(horizontal_lines)
                        vertical_lines_ui = copy.deepcopy(vertical_lines)

                        '''field mapping  '''
                        field_json_data = json_data
                        header_bottom = max([header['coords'][3] for header in header_column_wise_data])
                        field_extracted_list = field_mapping(ocrData[i], extracted_data_maintable, field_json_data,
                                                             horizontal_lines, vertical_lines, header_bottom,
                                                             main_table_bottom, ocr_img_copy)
                        # print(field_extracted_list)


                    except Exception as e:
                        logging.debug(f'Error on line {sys.exc_info()[-1].tb_lineno}', type(e).__name__, e)
                        logging.debug(f'Table not found in this page ,{i},{e}')
                        extracted_data_maintable = []

                    table_data = [extracted_data_maintable]

                    try:
                        for footer in extracted_data_footer:
                            table_data.append(footer)
                            multi_footers.extend(footer)
                        # #pass#print(extracted_data_maintable)
                    except:
                        logging.debug('Footer not found')
                        extracted_data_footer = []

                    '''Delete Tiff and pdf Images'''
                    if img_type != 'jpg':
                        del_temp_images(imgpath)

                    if i == 0:
                        multi_maintables.extend(extracted_data_maintable)
                        # pass#print('#'*100,'\n Multi page table - {} \n'.format(i),extracted_data_maintable,'#'*100)
                    elif nested_flag:
                        multi_maintables.extend(extracted_data_maintable[2:])
                    else:
                        multi_maintables.extend(extracted_data_maintable[1:])
                        # pass#print('#'*100,'\n Multi page table - {} \n'.format(i),extracted_data_maintable,'#'*100)

                    # multi_footers.extend(extracted_data_footer)

                    final_tables.append(table_data)

                    ########################### main-table debugging ##############################
                    # #pass#print('i',z)
                    # img = cv2.imread(imgpath)
                    # w,h,c = img.shape
                    # rf = 670/int(h)
                    # img = cv2.resize(img, (0,0), fx=rf, fy=rf)
                    #
                    # hors_cv,vers_cv = get_cv_lines(img)
                    # for hor in hors_cv:
                    #     cv2.line(img,(0,hor),(4000,hor),(225,0,225),1)
                    # for hor in vers_cv:
                    #     cv2.line(img,(0,hor),(4000,hor),(225,0,225),1)
                    # for h in horizontal_lines:
                    #     cv2.line(ocr_img_copy,(int(h[0][0]),int(h[0][1])),(int(h[1][0]),int(h[1][1])),(50, 0, 255),1)
                    # for v in vertical_lines:
                    #     cv2.line(ocr_img_copy,(int(v[1][0]),int(v[0][1])),(int(v[1][0]),int(v[1][1])),(50, 0, 255),1)
                    # cv2.namedWindow('main-table',cv2.WINDOW_NORMAL)
                    # cv2.resizeWindow('main-table', 1200,1200)
                    # cv2.imshow('main-table',ocr_img_copy)
                    # cv2.waitKey(0)
                    # cv2.destroyAllWindows()
                except Exception as e:
                    logging.debug(f'Exception is{e}')
                    final_tables = []

            if multi_page_table:
                table_data = [[multi_maintables, multi_footers], {"fields_extracted_list": field_extracted_list}]
                # pass#print('\n Final Multipage table \n ',table_data[0])
            else:
                final_tables = final_tables[0]
                table_data = [final_tables, {"fields_extracted_list": field_extracted_list}]
            # pass#print('#'*20,'Final Table Data','#'*20)
            # pass#print('table_data',table_data)

        except Exception as e:
            logging.debug(f'Error on line {sys.exc_info()[-1].tb_lineno}', type(e).__name__, e)
            logging.debug(f'Failed to predict table {table_num}')
            table_data = []
        table_final_data.append(table_data)
    # pass#print('Final Output of Table',table_final_data)
    logging.debug(f'table data final{table_final_data}')

    return {"table": table_final_data}
