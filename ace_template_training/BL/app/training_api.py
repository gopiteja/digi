import argparse
import json
import math
import re
import requests
import traceback
import ast
import os
import numpy as np
import cv2

from difflib import SequenceMatcher
from pathlib import Path
from dateutil.parser import parse
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS
from nltk import edit_distance
from pdf2image import convert_from_path
from py_zipkin.util import generate_random_64bit_string
from py_zipkin import storage

from db_utils import DB
from producer import produce
from ace_logger import Logging

try:
    # from app.producer import produce
    from app.extracto_utils import *
    # from app.testing_extract import *
    from app.automatic_training import cluster_similar_words
    from app.smart_training.predict_keywords import predict_keywords
    from app.smart_training.key_value_method_key_prediction import kv_values_prediction
    from app.get_keywords import get_keywords, sort_ocr, get_coords, get_field_dict, get_keywords_for_value, \
        get_keywords_in_quadrant
    from app.get_keywords import caculate_dis, get_quadrant_dict, get_page_dimension, which_quadrant, \
        keywords_lying_in_exact_quadrant
    from app.get_keywords import get_keywords_max_length, keywords_lying_in_exact_quadrant_value
    from app.smart_training.string_matching import convert_ocrs_to_char_dict_only_al_num, merge_coord
    from app.smart_training.utils import get_rel_info as get_rel_info_smart
    from app.smart_training.utils import percentage_inside
except:
    from producer import produce
    from extracto_utils import *
    # from testing_extract import *
    from automatic_training import cluster_similar_words
    from smart_training.predict_keywords import predict_keywords
    from smart_training.key_value_method_key_prediction import kv_values_prediction
    from get_keywords import get_keywords, sort_ocr, get_coords, get_field_dict, get_keywords_for_value, \
        get_keywords_in_quadrant
    from get_keywords import caculate_dis, get_quadrant_dict, get_page_dimension, which_quadrant, \
        keywords_lying_in_exact_quadrant
    from get_keywords import get_keywords_max_length, keywords_lying_in_exact_quadrant_value
    from smart_training.string_matching import convert_ocrs_to_char_dict_only_al_num, merge_coord
    from smart_training.utils import get_rel_info as get_rel_info_smart
    from smart_training.utils import percentage_inside

try:
    with open('app/parameters.json') as f:
        parameters = json.loads(f.read())
except:
    with open('parameters.json') as f:
        parameters = json.loads(f.read())

logging = Logging()
from py_zipkin.zipkin import zipkin_span, ZipkinAttrs, create_http_headers_for_new_span

from app import app

# neighours to take for ring fencing
NEIGHBOURS = parameters['neighbours_use']


def http_transport(encoded_span):
    # The collector expects a thrift-encoded list of spans. Instead of
    # decoding and re-encoding the already thrift-encoded message, we can just
    # add header bytes that specify that what follows is a list of length 1.
    body = encoded_span
    requests.post(
        'http://servicebridge:80/zipkin',
        data=body,
        headers={'Content-Type': 'application/x-thrift'},
    )


@zipkin_span(service_name='ace_template_training', span_name='merge_highlights')
def merge_highlights(box_list, page_number=0):
    '''
    Merge 2 or more words and get combined coordinates
    '''
    max_height = -1
    min_left = 100000
    max_right = 0
    total_width = 0
    word = ''
    top = -1

    if box_list and type(box_list[0]) is dict:
        for box in box_list:
            try:
                max_height = max(box['height'], max_height)
                min_left = min(box['left'], min_left)
                max_right = max(box['right'], max_right)
                total_width += box['width']
                word += ' ' + box['word']
                top = box['top']
            except:
                continue

        return {'height': max_height, 'width': total_width, 'y': top, 'x': min_left, 'right': max_right,
                'word': word.strip(), 'page': page_number}
    else:
        return {}


@zipkin_span(service_name='ace_template_training', span_name='get_highlights')
def get_highlights(value, ocr_data, scope, page_no):
    try:
        value = [val.lower() for val in value.split()]
    except:
        value = ''
    ocr_data_box = ocrDataLocal(int(scope['y']), int(scope['x']), int(scope['x'] + scope['width']),
                                int(scope['y'] + scope['height']), ocr_data[page_no])
    value_ocr = []
    for word in ocr_data_box:
        if word['word'].lower() in value:
            value_ocr.append(word)
    return merge_highlights(value_ocr, page_no)


@zipkin_span(service_name='ace_template_training', span_name='get_area_intersection')
def get_area_intersection(box, word, area_of_word):
    box_l, box_r, box_b, box_t = box
    word_l, word_r, word_b, word_t = word

    mid_x = box_l + (box_r - box_l) / 2
    mid_y = box_t + (box_b - box_t) / 2

    width = box_r - box_l
    height = box_b - box_t

    margin_wid = (width * 5) / 100
    margin_hig = (height * 5) / 100

    # this means that word is can be too big for the box
    if (word_l >= box_l and word_l <= mid_x + margin_wid):
        dx = word_r - word_l
    else:
        dx = min(word_r, box_r) - max(word_l, box_l)

    if (word_t >= box_t and word_t <= mid_y + margin_hig):
        dy = word_b - word_t
    else:
        dy = min(word_b, box_b) - max(word_t, box_t)

    if (dx >= 0) and (dy >= 0):
        return dx * dy

    return 0


@zipkin_span(service_name='ace_template_training', span_name='percentage_inside')
def percentage_inside(box, word):
    '''
    Get how much part of the word is inside the box
    '''
    box_l, box_r, box_b, box_t = box
    word_l, word_r, word_b, word_t = word
    area_of_word = (word_r - word_l) * (word_b - word_t)
    area_of_intersection = get_area_intersection(box, word, area_of_word)
    try:
        return area_of_intersection / area_of_word
    except:
        return 0


@zipkin_span(service_name='ace_template_training', span_name='standardize_date')
def standardize_date(all_data, input_format=[r'%d-%m-%Y', r'%d.%m.%Y', r'%d/%m/%Y'], standard_format=r'%Y-%m-%d'):
    # Find date related fields and change the format of the value to a standard one
    logging.debug(f'Changing date formats in extracted fields...')
    # date_formats = [r'%d-%m-%Y', r'%d.%m.%Y', r'%d/%m/%Y']

    standard_format = r'%Y-%m-%d'
    for field_name, field_value in all_data.items():
        if 'date' in field_name.lower().split():
            if field_value is not None or field_value:
                new_field_value = field_value
                raw_field_value = field_value.replace('suspicious', '')
                try:
                    parsed_date = parse(raw_field_value, fuzzy=True, dayfirst=True)
                except ValueError:
                    logging.exception(f'Error occured while parsing date field `{field_name}`:`{field_value}`.')
                    parsed_date = None

                if parsed_date is not None:
                    if 'suspicious' in field_value:
                        new_field_value = 'suspicious' + parsed_date.strftime(standard_format)
                    else:
                        new_field_value = parsed_date.strftime(standard_format)
                all_data[field_name] = new_field_value
        if "invoice number" in field_name.lower():
            if field_value is not None or field_value:
                try:
                    all_data[field_name] = field_value.replace(' ', '')
                except:
                    all_data[field_name] = field_value + 'suspicious'
        if "gstin" in field_name.lower():
            if field_value is not None or field_value:
                pattern = r"\d{2}[a-zA-Z]{5}\d{4}[a-zA-Z]{1}\d{1}[a-zA-Z]{1}\w"
                try:
                    valid_gstin = re.findall(pattern, field_value.replace('suspicious', ''))[-1]
                    all_data[field_name] = valid_gstin
                except:
                    all_data[field_name] = field_value + 'suspicious'
        if "po number" in field_name.lower():
            if field_value is not None or field_value:
                try:
                    all_data[field_name] = field_value.replace('.', '').replace(':', '')[:10]
                except:
                    all_data[field_name] = field_value + 'suspicious'
        if field_name.lower() in ['invoice base amount', 'invoice total']:
            try:
                all_data[field_name] = float(''.join(re.findall(r'[0-9\.]', field_value.replace('suspicious', ''))))
            except:
                all_data[field_name] = field_value + 'suspicious'
    return all_data


@zipkin_span(service_name='ace_template_training', span_name='correct_keyword')
def correct_keyword(ocr_data, keyword_sentence, scope, value):
    # Correct the last word of the keyword sentence
    # If ocr has "Invoice No:.", and keyword was trained as "Invoice No", this will make sure ocr word is saved as keyword

    junk = ''
    val_to_check = ''
    if value:
        val_to_check = value.split()[0]

    kwList = keyword_sentence.split()
    box_t = scope['y']
    box_r = scope['x'] + scope['width']
    box_b = scope['y'] + scope['height']
    box_l = scope['x']

    if len(kwList) > 1:
        for val in ocr_data:
            if val['top'] >= box_t and val['bottom'] <= box_b and val['right'] <= box_r and val['left'] >= box_l:
                if kwList[-1] in val['word'] and val['word'] not in kwList:
                    if edit_distance(val['word'], kwList[-1]) <= 3:
                        kwList[-1] = val['word']
                    elif val_to_check:
                        if val_to_check in val['word']:
                            junk = kwList[-1]
                            kwList.pop(-1)
                    else:
                        kwList.pop(-1)

    return ' '.join(kwList), junk


@zipkin_span(service_name='ace_template_training', span_name='keyword_extract')
def keyword_extract(ocr_data, keyword, scope):
    '''
    Get closest keyword to the trained keyword.
    '''
    regex = re.compile(r'[@_!#$%^&*()<>?/\|}{~:;]')
    keyList = keyword.split()
    keyLength = len(keyList)
    keyCords = []
    counter = 0

    # Search OCR for the key pattern
    for i, data in enumerate(ocr_data):
        ocr_length = len(ocr_data)
        check = False
        data['word'] = data['word'].strip()
        if (data['word'] == keyList[0] or (regex.search(data['word']) != None and keyList[0] in data['word'])):
            if (keyLength > 1):
                for x in range(0, keyLength):
                    if (i + x) >= ocr_length:
                        check = False
                        break
                    else:
                        if (ocr_data[i + x]['word'] == keyList[x] or (
                                regex.search(ocr_data[i + x]['word']) != None and keyList[x] in ocr_data[i + x][
                            'word'])):
                            check = True
                        else:
                            check = False
                            break
            else:
                check = True

        tempCords = [{}] * 1
        if (check):
            counter = counter + 1
            top = 10000
            bottom = 0
            # Left is of the first word
            if (data['word'] == keyList[0] or (regex.search(data['word']) != None and keyList[0] in data['word'])):
                tempCords[0]['left'] = data['left']
                for x in range(0, keyLength):
                    # Right is of the last word
                    if (x == (keyLength - 1)):
                        tempCords[0]['right'] = ocr_data[i + x]['right']

                    # If multi word key
                    if (keyLength > 1):
                        if (ocr_data[i + x]['word'] == keyList[x]):
                            if (ocr_data[i + x]['top'] < top):
                                top = ocr_data[i + x]['top']
                            if (ocr_data[i + x]['bottom'] > bottom):
                                bottom = ocr_data[i + x]['bottom']
                    else:
                        top = data['top']
                        bottom = data['bottom']

                tempCords[0]['top'] = top
                tempCords[0]['bottom'] = bottom
                keyCords.append(tempCords[0])
    logging.debug(f'keyCords {keyCords}')
    if (counter > 0):
        keysDict = keyCords
        proceed = True
        # First try to find keyword inside the trained box
        pi = []
        for i, values in enumerate(keysDict):
            trained_box = [scope['x'], scope['x'] + scope['width'], scope['y'] + scope['height'], scope['y']]
            keysDict_box = [keysDict[i]['left'], keysDict[i]['right'], keysDict[i]['bottom'], keysDict[i]['top']]
            pi.append(percentage_inside(trained_box, keysDict_box))
        maxpi = max(pi)
        if maxpi > 0.9:
            minIndex = pi.index(maxpi)
            proceed = False

        if proceed:
            logging.debug("Finding nearest to trained..")
            # Find keyword nearest to trained box
            inpX = (scope['y'] + scope['y'] + scope['height']) / 2
            inpY = (scope['x'] + scope['x'] + scope['width']) / 2
            DistList = []
            pi = []
            for i, values in enumerate(keysDict):
                # Store all keywords,distances in a Dict
                # Get midpoint of the input
                midheight = ((keysDict[i]['top'] + keysDict[i]['bottom']) / 2)
                midwidth = ((keysDict[i]['left'] + keysDict[i]['right']) / 2)
                x = abs(midheight - inpX)
                y = abs(midwidth - inpY)
                dist = math.sqrt((x * x) + (y * y))
                DistList.append(round(dist, 2))
            closestKey = min(DistList)
            minIndex = DistList.index(closestKey)

        key_top = keyCords[minIndex]['top']
        key_bottom = keyCords[minIndex]['bottom']
        key_left = keyCords[minIndex]['left']
        key_right = keyCords[minIndex]['right']

        return {'height': key_bottom - key_top, 'width': key_right - key_left, 'y': key_top, 'x': key_left}

    else:
        logging.debug('keyword not found in OCR')
        return {}


@zipkin_span(service_name='ace_template_training', span_name='get_cell_data')
def get_cell_data(scope_, multi_way_field_info, resize_factor, ocr_data):
    scope = scope_.copy()
    cell_data = {}
    for each_additional_key in multi_way_field_info['coordinates']:
        value_box = {}

        '''Resizing keywords coordinates'''
        each_additional_key = resize_coordinates(each_additional_key, resize_factor)

        each_additional_key['top'] = each_additional_key['y']
        each_additional_key['left'] = each_additional_key['x']
        each_additional_key['right'] = each_additional_key['x'] + each_additional_key['width']
        each_additional_key['bottom'] = each_additional_key['y'] + each_additional_key['height']
        value_box['top'] = scope['y']
        value_box['left'] = scope['x']
        value_box['bottom'] = scope['y'] + scope['height']
        value_box['right'] = scope['x'] + scope['width']

        context_ocr_data = ocrDataLocal(each_additional_key['y'], each_additional_key['x'],
                                        each_additional_key['x'] + each_additional_key['width'],
                                        each_additional_key['y'] + each_additional_key['height'], ocr_data)
        context_text = ' '.join([word['word'] for word in context_ocr_data])
        each_additional_key['keyword'] = context_text
        direction = get_rel_info(each_additional_key, value_box, 'direction')
        try:
            cell_data[direction] = each_additional_key
        except Exception as e:
            logging.exception(f'Error in making cell-data for multi key fields')

    return cell_data


@zipkin_span(service_name='ace_template_training', span_name='resize_coordinates')
def resize_coordinates(box, resize_factor):
    box["width"] = int(box["width"] / resize_factor)
    box["height"] = int(box["height"] / resize_factor)
    box["y"] = int(box["y"] / resize_factor)
    box["x"] = int(box["x"] / resize_factor)

    try:
        box["left"] = int(box["left"] / resize_factor)
        box["right"] = int(box["right"] / resize_factor)
        box["top"] = int(box["top"] / resize_factor)
        box["bottom"] = int(box["bottom"] / resize_factor)
    except:
        pass

    return box


@zipkin_span(service_name='ace_template_training', span_name='get_requied_field_data')
def get_requied_field_data(field):
    additional_splits = field['additional_splits']
    fields = {'Left': '', 'Right': '', 'Top': '', 'Bottom': ''}
    # dream scenario
    '''
    fields = {'top' : {}, 'left': {}, 'right': {}, 'bottom': {}
    '''
    keyword_and_align = additional_splits['coordinates'][-1]
    coords = additional_splits['coordinates'][:3]

    training_data_field = {}
    coord_counter = 0
    for key, val in keyword_and_align.items():
        training_data_field[val] = {
            'field': val,
            'keyword': key,
            'value': '',
            'validation': {
                'pattern': 'NONE',
                'globalCheck': 'false'
            },
            'split': 'no',
            'coordinates': coords[coord_counter],
            'width': field['width'],
            'page': coords[coord_counter]['page']
        }
        coord_counter += 1

    for key in fields.keys():
        try:
            fields[key] = training_data_field[key]
        except:
            pass

    return fields


@zipkin_span(service_name='ace_template_training', span_name='get_checkbox')
def get_checkbox(field_type, field, checkboxes_all, validation):
    """
    """
    try:
        checkboxes = field['checkboxes']
    except:
        checkboxes = {}
    logging.debug(checkboxes)

    checkb = False
    if validation == 'Checkbox Body':
        checkb = True
        logging.debug('ssss')
    else:
        pass

    if checkb:
        logging.debug('enterred here')
        pattern = validation
        logging.debug(f'checkbox_keys {checkboxes.keys()}')

        for keyword_ch, ch_field_box in checkboxes.items():
            if keyword_ch == 'id':
                continue
            else:
                pass

            field_box = ch_field_box
            # logging.debug(field_box)
            logging.debug(f'keyyyy {keyword_ch}')

            # Resize field box
            field_box["width"] = int(field_box["width"] / resize_factor)
            field_box["height"] = int(field_box["height"] / resize_factor)
            field_box["y"] = int(field_box["y"] / resize_factor)
            field_box["x"] = int(field_box["x"] / resize_factor)

            # Scope is field box by default. Keyword box if keyword is there.
            # Its updated later when we check if keyword exists
            scope = {
                'x': field_box['x'],
                'y': field_box['y'],
                'width': field_box['width'],
                'height': field_box['height']
            }
            multi_key_field_info = {}
            context_key_field_info = {}

            try:
                additional_field_info = field['additional_splits']
                if additional_field_info['type'].lower() == '2d':
                    cell_data = get_cell_data(scope, additional_field_info, resize_factor, ocr_data[int(page_no)])
                    multi_key_field_info['cell_data'] = cell_data
                elif additional_field_info['type'].lower() == 'context':
                    context_coords = resize_coordinates(additional_field_info['coordinates'][0], resize_factor)
                    context_scope = {
                        'x': context_coords['x'],
                        'y': context_coords['y'],
                        'width': context_coords['width'],
                        'height': context_coords['height']
                    }
                    box = {}
                    box['width'] = context_coords['width']
                    box['height'] = context_coords['height']
                    relative = {
                        'left': scope['x'] - context_scope['x'],
                        'top': scope['y'] - context_scope['y']
                    }
                    # logging.debug('context_coords',context_coords)
                    # logging.debug('ocr_data type',type(ocr_data))
                    context_ocr_data = ocrDataLocal(context_coords['y'], context_coords['x'],
                                                    context_coords['x'] + context_coords['width'],
                                                    context_coords['y'] + context_coords['height'],
                                                    ocr_data[int(page_no)])
                    context_text = ' '.join([word['word'] for word in context_ocr_data])
                    context_key_field_info = {
                        'text': context_text,
                        'box': box,
                        'relative': relative
                    }
                # logging.debug('multi_key_field_info',multi_key_field_info)
                # logging.debug('context_key_field_info',context_key_field_info)
            except:
                pass
            '''
                Finding keyword using different method
                bcoz I don't trust old method.Hence keyword_box_new
            '''
            logging.debug(f'scope of checkbox {scope}')
            haystack = ocrDataLocal(scope['y'], scope['x'], scope['x'] + scope['width'], scope['y'] + scope['height'],
                                    ocr_data[int(page_no)])
            try:
                logging.debug(f'haystach {keyword_ch}')
                keyword_box_new = needle_in_a_haystack(keyword_ch, haystack)
                logging.debug(f'keybox new {keyword_box_new}')
            except Exception as e:
                keyword_box_new = {}
                logging.exception(f'Exception in finding keyword:')

            try:
                value_meta = needle_in_a_haystack(field_value, haystack)
            except Exception as e:
                value_meta = {}
                logging.exception('Exception in finding keyword')

            # Box's Top, Right, Bottom, Left
            box_t = field_box['y']
            box_r = field_box['x'] + field_box['width']
            box_b = field_box['y'] + field_box['height']
            box_l = field_box['x']

            # If keyword is there then save the
            # relative distance from keyword to box's edges
            # else save the box coordinates directly
            if keyword_ch:
                logging.debug(f'key_ch {keyword_ch}')
                regex = re.compile(r'[@_!#$%^&*()<>?/\|}{~:;]')
                alphareg = re.compile(r'[a-zA-Z]')
                keyList = keyword_ch.split()
                logging.debug(f'key ist {keyList}')
                if len(keyList) > 1:
                    logging.debug('Keyword greater than 1')
                    if regex.search(keyList[-1]) != None and alphareg.search(keyList[-1]) == None:
                        # if the last word of keyword sentence containes only special characters
                        junk = keyList[-1]
                        del keyList[-1]
                keyword_ch = ' '.join(keyList)
                # Get keyword's box coordinates
                keyword_box = keyword_extract(ocr_data[int(page_no)], keyword_ch, scope)

                logging.debug(f'keyword box {keyword_box}')
                if not keyword_box:
                    keyword_2, junk = correct_keyword(ocr_data[int(page_no)], keyword_ch, scope, field_value)
                    keyword_box = keyword_extract(ocr_data[int(page_no)], keyword_2, scope)
                    if keyword_box:
                        # field['keyword']=keyword_ch=keyword_2    ###### changed here
                        field['keyword'] = keyword_2
                if keyword_box:
                    logging.debug('in keyword loop')
                    # Keyword's Top, Right, Bottom, Left
                    keyword_t = keyword_box['y']
                    keyword_r = keyword_box['x'] + keyword_box['width']
                    keyword_b = keyword_box['y'] + keyword_box['height']
                    keyword_l = keyword_box['x']

                    # Scope is keyword is keyword exists
                    scope = {
                        'x': keyword_box['x'],
                        'y': keyword_box['y'],
                        'width': keyword_box['width'],
                        'height': keyword_box['height']
                    }

                    # Calculate distance to box edges wrt keyword
                    top = keyword_t - box_t
                    right = box_r - keyword_r
                    bottom = box_b - keyword_b
                    left = keyword_l - box_l
                else:
                    top = box_t
                    right = box_r
                    bottom = box_b
                    left = box_l
            else:
                top = box_t
                right = box_r
                bottom = box_b
                left = box_l

            logging.debug(f't {top} b {bottom} r {right} l {left}')
            try:
                logging.debug('in try loop')
                cbdict = {
                    'keyword': keyword_ch,
                    'top': top,
                    'right': right,
                    'bottom': bottom,
                    'left': left,
                    'validation': pattern if pattern else '',
                    'scope': scope,
                    'page': page_no
                }
                if field_type not in checkboxes_all:
                    checkboxes_all[field_type] = [cbdict]
                else:
                    checkboxes_all[field_type].append(cbdict)
                logging.debug(f'final checkbox {checkboxes_all}')
            except Exception as e:
                pass
    else:
        checkboxes_all[field_type] = {}

    return checkboxes_all


def get_pre_processed_char(ocr_data):
    """
    """
    pre_processed_char = []
    for page in ocr_data:
        page = sort_ocr(page)
        char_index_list, haystack = convert_ocrs_to_char_dict_only_al_num(page)
        pre_processed_char.append([char_index_list, haystack])

    return pre_processed_char


@zipkin_span(service_name='ace_template_training', span_name='get_trained_info')
def get_trained_info(ocr_data, fields, resize_factor, keywords=[], ocr_field_keyword={}, pre_processed_char=[]):
    logging.debug(f'fields {fields}')
    field_data = {}
    extracted_data = {}

    checkboxes_all = {}
    junk = ''

    if not pre_processed_char:
        pre_processed_char = get_pre_processed_char(ocr_data)

    for _, field in fields.items():

        if not field['value']:
            continue
            field_data[field_type] = {
                'value': '',
                'not trained': True,
                'keyword': ''
            }
        else:
            field_type = field['field']
            page_no = int(field['page'])
            field['coordinates'][0] = resize_coordinates(field['coordinates'][0], resize_factor)
            values = field['coordinates'][0]
            values['word'] = field['value']
            validation = fields['validation'] if 'validation' in fields else ''
            try:
                field['coordinates'][1] = resize_coordinates(field['coordinates'][1], resize_factor)
                kv_keywords = field['coordinates'][1]
                kv_keywords['word'] = field['keyword']
            except:
                kv_keywords = {}

            # logging.debug(f'values - {values}')
            keyword, relative, kv_scope, split_check, context_key_field_info, feud, key_val_meta = predict_keywords(
                keywords, values, kv_keywords, ocr_data, page_no, pre_processed_char)

            checkboxes_all = get_checkbox(field_type, field, checkboxes_all, validation)

            field_data[field_type] = {
                'keyword': keyword,
                'value': field['value'],
                'top': relative['top'],
                'right': relative['right'],
                'bottom': relative['bottom'],
                'left': relative['left'],
                'scope': kv_scope,
                'scope_value': field['coordinates'][0],
                'scope_key': field['coordinates'][1] if len(field['coordinates']) > 1 else {},
                'page': page_no,
                'junk': '',
                'key_val_meta': key_val_meta,
                'validation': validation,
                'split_check': split_check,
                'multi_key_field_info': '',
                'context_key_field_info': context_key_field_info,
                'boundary_data': feud
            }

    ocr_text = ' '.join([word['word'] for page in ocr_data for word in page])

    # for saving to ner
    # train_params = {    "ocr_text":ocr_text,
    #                             "field_data":field_data
    #                         }
    # host = '192.168.0.108'
    # port = 7002
    # route = 'train'
    # response = requests.post(f'http://{host}:{port}/{route}', json=train_params)

    # training the ner keyword prediction model
    # try:
    #     ner_model_path = './app/model/'
    #     keyword_trainer = KeywordTrainer(ner_model_path)

    #     keyword_trainer.train(ocr_text, field_data)
    #     logging.debug("training ner model complete")
    # except:
    #     logging.error('path wrong maybe')
    #     traceback.logging.debug_exc()

    # storing fued positional descriptors information
    return field_data, checkboxes_all


@zipkin_span(service_name='ace_template_training', span_name='update_queue_trace')
def update_queue_trace(queue_db, case_id, latest):
    queue_trace_q = "SELECT * FROM `trace_info` WHERE `case_id`=%s"
    queue_trace_df = queue_db.execute(queue_trace_q, params=[case_id])

    if queue_trace_df.empty:
        message = f' - No such case ID `{case_id}` in `trace_info`.'
        logging.error(f'ERROR: {message}')
        return {'flag': False, 'message': message}
    # Updating Queue Name trace
    try:
        queue_trace = list(queue_trace_df.queue_trace)[0]
    except:
        queue_trace = ''
    if queue_trace:
        queue_trace += ',' + latest
    else:
        queue_trace = latest

    # Updating last_updated_time&date

    try:
        last_updated_dates = list(queue_trace_df.last_updated_dates)[0]
    except:
        last_updated_dates = ''
    if last_updated_dates:
        last_updated_dates += ',' + datetime.now().strftime(r'%d/%m/%Y %H:%M:%S')
    else:
        last_updated_dates = datetime.now().strftime(r'%d/%m/%Y %H:%M:%S')

    update = {'queue_trace': queue_trace}
    where = {'case_id': case_id}
    update_q = "UPDATE `trace_info` SET `queue_trace`=%s, `last_updated_dates`=%s WHERE `case_id`=%s"
    queue_db.execute(update_q, params=[queue_trace, last_updated_dates, case_id])

    return {'flag': True, 'message': 'Updated Queue Trace'}


@zipkin_span(service_name='ace_template_training', span_name='convert_coord_for_ui')
def convert_coord_for_ui(value, page_no=0):
    ui_coord = {}

    ui_coord['x'] = value['left']
    ui_coord['y'] = value['top']
    ui_coord['width'] = value['right'] - value['left']
    ui_coord['height'] = value['bottom'] - value['top']
    ui_coord['page'] = page_no

    return ui_coord


@zipkin_span(service_name='ace_template_training', span_name='prepare_predicted_data')
def prepare_predicted_data(values, field_name, keyword, page_no):
    field = {}
    field['field'] = field_name
    if keyword and 'word' in keyword:
        field['keyword'] = keyword['word']
    else:
        field['keyword'] = ''

    field['value'] = [value['word'] for value in values]
    if field['value']:
        field['value'] = ' '.join(field['value'])

    valueCords = {'top': 10000, 'bottom': 0, 'right': 0, 'left': 10000}
    for value in values:
        valueCords = merge_coord(valueCords, value)

    field['coordinates'] = []
    if values:
        field['coordinates'].append(convert_coord_for_ui(valueCords, page_no))
        if field['keyword']:
            field['coordinates'].append(convert_coord_for_ui(keyword, page_no))
    field['validation'] = ''
    field['keycheck'] = True

    return field


@zipkin_span(service_name='ace_template_training', span_name='get_max_marks_fields')
def get_max_marks_fields(fields):
    """
    Author : Akshat Goyal

    Args: [[keyword,weight]]
            keyword - dict
            weight - int
    """
    sorted_field = sorted(fields, key=lambda x: x[1], reverse=True)

    max_weight = sorted_field[0][1]

    max_fields = []

    for field in sorted_field:
        if field[1] == max_weight:
            max_fields.append(field[0])

    return max_fields


@zipkin_span(service_name='ace_template_training', span_name='get_neighbourhood_dict')
def get_neighbourhood_dict(tenant_id=None):
    """
    Author : Akshat Goyal

    Returns the neighbourhood dict for the field

    """
    db_config = {
        'host': os.environ['HOST_IP'],
        'port': os.environ['LOCAL_DB_PORT'],
        'user': os.environ['LOCAL_DB_USER'],
        'password': os.environ['LOCAL_DB_PASSWORD'],
        'tenant_id': tenant_id
    }
    db = DB('template_db', **db_config)
    db_data = db.get_all('field_neighbourhood_dict')
    query_result = json.loads(db_data.to_json(orient='records'))

    fields = {}
    field_orientation = {}
    for row in query_result:
        field_type = row['field']
        try:
            neighbourhood_dict = ast.literal_eval(row['neighbourhood_dict'])
        except:
            neighbourhood_dict = {}

        try:
            orientation_variation = ast.literal_eval(row['orientation_variation'])
        except:
            orientation_variation = []

        fields[field_type] = neighbourhood_dict
        field_orientation[field_type] = orientation_variation

    return fields, field_orientation


@zipkin_span(service_name='ace_template_training', span_name='get_distance')
def get_distance(field, sorted_neighbourhood, ocr_data, pre_processed_char):
    """
    Author : Akshat Goyal

    gives the distance between the field and best four neighbour found

    """

    # so that we can use field as scope
    field_scope = convert_coord_for_ui(field, field['page'])

    dis = []

    for neighbour in sorted_neighbourhood:
        coord = get_coords(ocr_data, neighbour[0], field_scope, pre_processed_char)
        if coord:
            # taking the neighbour location with heighest wieght and taking the coord
            coord = sorted(coord, key=lambda x: x[1])[0][0]

            # neighbour having close connection are closer than they appear
            if neighbour[1] != 0:
                distance = caculate_dis(coord, field) / neighbour[1]
            else:
                distance = caculate_dis(coord, field)

            dis.append(distance)

            if len(dis) > NEIGHBOURS:
                break

    return sum(dis)


@zipkin_span(service_name='ace_template_training', span_name='get_ring_fenced_field')
def get_ring_fenced_field(fields, neighbourhood, ocr_data, pre_processed_char):
    """
    Author : Akshat Goyal

    Args:

    """
    # this can be tweaked so that we can check multiple keywords
    # if validation fails for value
    min_dis = 100000

    most_prob_field = {}

    sorted_neighbourhood = sorted(neighbourhood, key=lambda x: x[1], reverse=True)

    for field in fields:
        dis = get_distance(field, sorted_neighbourhood, ocr_data, pre_processed_char)

        if dis < min_dis:
            most_prob_field = field
            min_dis = dis

    return most_prob_field


# @zipkin_span(service_name='ace_template_training', span_name='pdf_to_image')
# def pdf_to_image(file_name):
#     source_folder = '/home/akshat/extract/Srini1300'
#     file_path = Path(source_folder) / file_name
#
#     if not os.path.isfile(file_path):
#         source_folder = '/var/www/training_api/app/invoice_files'
#         file_path = Path(source_folder) / file_name
#
#     images = convert_from_path(file_path)
#
#     return images
#
#
# @zipkin_span(service_name='ace_template_training', span_name='make_cv_box_list')
# def make_cv_box_list(word_list, file_name, field_name):
#     if file_name:
#         images = pdf_to_image(file_name)
#
#     for word in word_list:
#         make_cv_box(word, file_name, images, field_name)
#
#     cv2.destroyAllWindows()
#
#
# @zipkin_span(service_name='ace_template_training', span_name='make_cv_box')
# def make_cv_box(word_temp, file_path, images=None, field_name=''):
#     global parameters
#     if images is None:
#         images = pdf_to_image(file_name)
#
#     logging.debug(word_temp)
#     # if the word also have weightage
#     if type(word_temp) is list:
#         word = word_temp[0]
#     else:
#         word = word_temp
#
#     # converting to opencv image
#     img = np.array(images[word['page']])
#     img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
#
#     w, h, c = img.shape
#     rf = parameters['default_img_width'] / int(h)
#     img = cv2.resize(img, (0, 0), fx=rf, fy=rf)
#     logging.debug(word)
#     if type(word) == list:
#         word = word[0]
#
#     cv2.rectangle(img, (int(word['left']), int(word['top'])), (int(word['right']), int(word['bottom'])), (0, 0, 255), 2)
#
#     img = cv2.resize(img, (0, 0), fx=1, fy=.75)
#
#     cv2.imshow(field_name, img)
#     while (1):
#         if cv2.waitKey() == 13:
#             break


@zipkin_span(service_name='ace_template_training', span_name='get_predicted_fields')
def get_predicted_fields(
        mandatory_fields,
        all_values,
        fields_keywords,
        ocr_data,
        pre_processed_char,
        field_validations,
        quadrant_dict,
        case_id='',
        tenant_id=None
):
    """
    Author : Akshat Goyal

    """

    predicted_fields = []

    field_neighbourhood_dict, field_orientation_dict = get_neighbourhood_dict(tenant_id)

    logging.debug(f'field_neighbourhood_dict - {field_neighbourhood_dict}')
    logging.debug(f'fields_keyword - {fields_keywords}')

    for field, neighbours in field_neighbourhood_dict.items():
        neighbour_list = [[neighbour, count] for neighbour, count in neighbours.items()]
        field_neighbourhood_dict[field] = neighbour_list

    for field_name in mandatory_fields:
        logging.debug(f'\nfield - {field_name}')
        field = {}

        if field_name in fields_keywords:
            # make_cv_box_list(fields_keywords[field_name], file_name, field_name)
            if not fields_keywords[field_name]:
                continue
            max_fields = get_max_marks_fields(fields_keywords[field_name])

            logging.debug(f'max field - {max_fields}')

            # if field_name == 'Invoice Total':
            # make_cv_box_list(max_fields, file_name, field_name)

            if field_name in field_neighbourhood_dict:
                ring_fenced_field = get_ring_fenced_field(max_fields, field_neighbourhood_dict[field_name], ocr_data,
                                                          pre_processed_char)
            else:
                ring_fenced_field = max_fields[0]

            logging.debug(f'ring_fenced_field - {ring_fenced_field}')

            page_no = int(ring_fenced_field['page'])
            # logging.debug(f'all_values - {all_values[page_no]}')
            value = ''

            if field_name in field_orientation_dict:
                values = kv_values_prediction(all_values[page_no], [ring_fenced_field],
                                              field_orientation_dict[field_name],
                                              field_validations.get('field_name', None))
            else:
                values = kv_values_prediction(all_values[page_no], [ring_fenced_field], {},
                                              field_validations.get('field_name', None))

            logging.debug(f'value - {values}')
            if values:
                field = prepare_predicted_data(values, field_name, ring_fenced_field, page_no)

        # if no keyword is found
        else:
            logging.debug('no keyword is found')
            if case_id:
                page_dimensions = get_page_dimension(case_id, tenant_id=tenant_id)
            else:
                page_dimensions = {}
            # on which page will we find the value
            if field_name in quadrant_dict and page_dimensions:
                values = []
                for page in all_values:
                    value_temp = keywords_lying_in_exact_quadrant_value(page, quadrant_dict[field_name],
                                                                        page_dimensions)
                    values.extend(value_temp)

                if values:
                    field = prepare_predicted_data(values, field_name, None, values[0]['page'])

        if not field:
            field = {}
            field['field'] = field_name
            field['keyword'] = ''
            field['value'] = ''
            field['coordinates'] = []
            field['validation'] = ''
            field['keycheck'] = True

        predicted_fields.append(field)

    return predicted_fields


@zipkin_span(service_name='ace_template_training', span_name='get_trained_data_format')
def get_trained_data_format(field):
    """
    Author : Akshat Goyal
    """
    if field['value']:
        field_data = {
            'keyword': field['keyword'],
            'value': field['value'],
            'scope': field['coordinates'][1] if len(field['coordinates']) > 1 else {},
            'scope_value': field['coordinates'][0],
            'page': field['coordinates'][0]['page'],
            'junk': '',
        }
    else:
        field_data = {}

    return field_data


@zipkin_span(service_name='ace_template_training', span_name='get_nearest_neighbour')
def get_nearest_neighbour(trained_info, field_neighbourhood, no_of_neighbour=NEIGHBOURS):
    """
    Author : Akshat Goyal
    """
    neighbour_dict = {}

    logging.debug(f'trained_info - {trained_info}')

    for field, field_data in trained_info.items():
        if 'scope' not in field_data or not field_data['scope']:
            continue
        dis = set()
        logging.debug(f'field - {field}')
        logging.debug(f'neighbours - {field_neighbourhood[field]}')
        for keyword in field_neighbourhood[field]:
            s = field_data['scope']
            logging.debug(f'field_data - {s}')
            if keyword['right'] - keyword['left'] > 0 \
                    and field_data['scope']['right'] - field_data['scope']['left'] > 0:

                distance = caculate_dis(field_data['scope'], keyword)
                if keyword['word']:
                    dis.add((keyword['word'], distance))
        if dis:
            dis = list(dis)
            dis = sorted(dis, key=lambda x: x[1])
            neighbour_dict[field] = dis[:no_of_neighbour]

    return neighbour_dict


@zipkin_span(service_name='ace_template_training', span_name='update_field_dict')
def update_field_dict(config, tenant_id):
    """
    Author : Akshat Goyal
    """

    db_config = {
        'host': os.environ['HOST_IP'],
        'port': os.environ['LOCAL_DB_PORT'],
        'user': os.environ['LOCAL_DB_USER'],
        'password': os.environ['LOCAL_DB_PASSWORD'],
        'tenant_id': tenant_id
    }
    db = DB('template_db', **db_config)

    old_field_dict = get_field_dict(for_update=True, tenant_id=tenant_id)
    table_name = 'field_dict'

    new_fields = {}

    for field_type, value in config.items():
        if field_type in old_field_dict:
            new_fields[field_type] = {}
            new_fields[field_type].update(old_field_dict[field_type])
            if value not in old_field_dict[field_type]:
                new_fields[field_type][value] = 1
            else:
                new_fields[field_type][value] = old_field_dict[field_type][value] + 1


        elif field_type not in old_field_dict:
            new_fields[field_type] = {value: 1}

    for field_type, value in new_fields.items():
        var = json.dumps(value)
        check_query = "SELECT * FROM {} WHERE `field_type` = '{}'".format(table_name, field_type)

        check = db.execute(check_query)

        if type(check) != bool:
            check = not check.empty

        if check:
            try:
                if value != old_field_dict[field_type]:
                    update = "UPDATE {} SET `variation` = '{}' WHERE `field_type` = '{}'".format(table_name, var,
                                                                                                 field_type)
                    db.execute(update)
            except:
                insert = "INSERT INTO {} (`field_type`, `variation`) VALUES ('{}', '{}')".format(table_name, field_type,
                                                                                                 var)
                db.execute(insert)
        else:
            insert = "INSERT INTO {} (`field_type`, `variation`) VALUES ('{}', '{}')".format(table_name, field_type,
                                                                                             var)
            db.execute(insert)

    return "Updated Field Dict"


@zipkin_span(service_name='ace_template_training', span_name='merge_neightbour_dict_value')
def merge_neightbour_dict_value(old_neighbours, maybe_new_neighbours, multi=False):
    """
    Author : Akshat Goyal
    """
    new_neighbours_list = {}

    logging.debug(maybe_new_neighbours)
    if not multi:
        new_neighbours = [maybe_new_neighbours[0]]
    else:
        new_neighbours = [neighbour[0] for neighbour in maybe_new_neighbours]

    # for finding same word in old neighours
    for neighbour, count in old_neighbours.items():
        new_neighbours_list[neighbour] = count
        for new_neighbour in new_neighbours:
            if SequenceMatcher(None, neighbour, new_neighbour).ratio() > 0.9:
                new_neighbours_list[neighbour] += 1
                new_neighbours.remove(new_neighbour)
                break

    if new_neighbours:
        for new_neighbour in new_neighbours:
            if new_neighbour in new_neighbours_list:
                new_neighbours_list[new_neighbour] += 1
            else:
                new_neighbours_list[new_neighbour] = 1

    return new_neighbours_list


@zipkin_span(service_name='ace_template_training', span_name='merge_key_orientation')
def merge_key_orientation(old_orientation_list, orientation):
    """
    Author : Akshat Goyal
    """

    new_orientation_list = []

    orientation_consumed = False

    for neighbour, count in old_orientation_list:
        if neighbour == orientation:
            orientation_consumed = True
            new_orientation_list.append([neighbour, count + 1])
        else:
            new_orientation_list.append([neighbour, count])

    if not orientation_consumed:
        new_orientation_list.append([orientation, 1])

    return new_orientation_list


@zipkin_span(service_name='ace_template_training', span_name='get_orientation_dict')
def get_orientation_dict(trained_info):
    """
    Author : Akshat Goyal
    """
    orientation_dict = {}

    for field, field_data in trained_info.items():
        orientation_dict[field] = get_rel_info_smart(field_data['scope'], field_data['scope_value'], direction=True)

    return orientation_dict


@zipkin_span(service_name='ace_template_training', span_name='update_field_neighbour_dict')
def update_field_neighbour_dict(neighbour_dict, trained_info, tenant_id=None):
    """
    Author : Akshat Goyal
    """
    db_config = {
        'host': os.environ['HOST_IP'],
        'port': os.environ['LOCAL_DB_PORT'],
        'user': os.environ['LOCAL_DB_USER'],
        'password': os.environ['LOCAL_DB_PASSWORD'],
        'tenant_id': tenant_id
    }
    db = DB('template_db', **db_config)

    old_neighbour_dict, old_orientation_dict = get_neighbourhood_dict(tenant_id)
    new_fields = {}
    new_orientation_dict = {}
    table_name = 'field_neighbourhood_dict'

    orientation_dict = get_orientation_dict(trained_info)

    logging.debug(f'old_neighbour_dict - {old_neighbour_dict}')
    logging.debug(f'neighbour_dict - {neighbour_dict}')

    for field_type, neighbours in neighbour_dict.items():
        if field_type not in old_neighbour_dict:
            new_fields[field_type] = merge_neightbour_dict_value({}, neighbours, multi=True)
            new_orientation_dict[field_type] = merge_key_orientation([], orientation_dict[field_type])
        else:
            new_values = merge_neightbour_dict_value(old_neighbour_dict[field_type], neighbours, multi=True)
            new_fields[field_type] = new_values
            new_orientation_dict[field_type] = merge_key_orientation(old_orientation_dict[field_type],
                                                                     orientation_dict[field_type])

    for field_type, value in new_fields.items():
        var = json.dumps(value)
        check_query = "SELECT * FROM {} WHERE `field` = '{}'".format(table_name, field_type)

        check = db.execute(check_query)

        if type(check) != bool:
            check = not check.empty

        if check:
            try:
                if value != old_neighbour_dict[field_type]:
                    update = "UPDATE {} SET `neighbourhood_dict` = '{}', `orientation_variation` = '{}' WHERE `field` " \
                             "= '{}'".format(
                        table_name, var, json.dumps(new_orientation_dict[field_type]), field_type)
                    db.execute(update)
            except:
                insert = "INSERT INTO {} (`field`, `neighbourhood_dict`, `orientation_variation`) VALUES ('{}', '{}', " \
                         "'{}')".format(
                    table_name, field_type, var, json.dumps(new_orientation_dict[field_type]))
                db.execute(insert)
        else:
            insert = "INSERT INTO {} (`field`, `neighbourhood_dict`, `orientation_variation`) VALUES ('{}', '{}', '{}')".format(
                table_name, field_type, var, json.dumps(new_orientation_dict[field_type]))
            db.execute(insert)

    return "Updated Field neighbourhood dict"


@zipkin_span(service_name='ace_template_training', span_name='get_field_dict_from_info')
def get_field_dict_from_info(trained_info):
    """
    """
    dictionary = {}
    for field, f_data in trained_info.items():
        if field != 'Vendor Name':
            try:
                keyword = f_data['keyword']
                if keyword:
                    dictionary[field] = keyword
            except:
                pass
    return dictionary


@zipkin_span(service_name='ace_template_training', span_name='prepare_neighbours')
def prepare_neighbours(ocr_field_keyword, trained_info):
    field_neighbourhood = {}

    for ocr_field, keywords in ocr_field_keyword.items():
        for field, _ in trained_info.items():
            if ocr_field != field:

                # logging.debug(f'keywords - {keywords}')
                if field in field_neighbourhood:
                    field_neighbourhood[field].extend([keyword[0] for keyword in keywords])
                else:
                    field_neighbourhood[field] = [keyword[0] for keyword in keywords]
                # logging.debug(f'field_neighbourhood - {field_neighbourhood[field]}')

    return field_neighbourhood


@zipkin_span(service_name='ace_template_training', span_name='extract_quadrant_information')
def extract_quadrant_information(trained_info, case_id, tenant_id=None):
    """
    Author : Akshat Goyal
    """
    quadrant_info = {}

    page_dimensions = get_page_dimension(case_id, tenant_id=tenant_id)

    if not page_dimensions:
        return quadrant_info

    for field, field_data in trained_info.items():
        field_page = field_data['page']
        quadrant = which_quadrant(field_data['scope'], page_dimensions[field_page])

        quadrant_info[field] = quadrant

    return quadrant_info


@zipkin_span(service_name='ace_template_training', span_name='update_quadrant_dict')
def update_quadrant_dict(quadrant_dict, tenant_id):
    """
    Author : Akshat Goyal
    """
    db_config = {
        'host': os.environ['HOST_IP'],
        'port': os.environ['LOCAL_DB_PORT'],
        'user': os.environ['LOCAL_DB_USER'],
        'password': os.environ['LOCAL_DB_PASSWORD'],
        'tenant_id': tenant_id
    }
    db = DB('template_db', **db_config)

    old_quadrant_dict = get_quadrant_dict(for_update=True, tenant_id=tenant_id)

    new_quadrant_dict = {}

    for field, quad in quadrant_dict.items():
        quad = str(quad)
        if field in old_quadrant_dict:
            new_quadrant_dict[field] = {}
            new_quadrant_dict[field].update(old_quadrant_dict[field])
            if quad not in old_quadrant_dict[field]:
                new_quadrant_dict[field][quad] = 1
            else:
                new_quadrant_dict[field][quad] = old_quadrant_dict[field][quad] + 1
        else:
            new_quadrant_dict[field] = {quad: 1}

        # adding to db
        table_name = 'field_quadrant_dict'

        var = json.dumps(new_quadrant_dict[field])
        check_query = "SELECT * FROM {} WHERE `field` = '{}'".format(table_name, field)

        check = db.execute(check_query)

        if type(check) != bool:
            check = not check.empty

        if check:
            try:
                update = "UPDATE {} SET `quadrant` = '{}' WHERE `field` = '{}'".format(table_name, var, field)
                db.execute(update)
            except:
                insert = "INSERT INTO {} (`field`, `quadrant`) VALUES ('{}', '{}')".format(table_name, field, var)
                db.execute(insert)
        else:
            insert = "INSERT INTO {} (`field`, `quadrant`) VALUES ('{}', '{}')".format(table_name, field, var)
            db.execute(insert)

    return "Updated quadrant dict"


@zipkin_span(service_name='ace_template_training', span_name='update_field_dict_with_neighbour')
def update_field_dict_with_neighbour(trained_info, ocr_data, pre_processed_char, case_id, tenant_id=None):
    """
    Author : Akshat Goyal
    """
    dictionary = get_field_dict_from_info(trained_info)

    update_field_dict(dictionary, tenant_id=tenant_id)

    field_with_variation = get_field_dict(tenant_id=tenant_id)

    _, ocr_field_keyword = get_keywords(ocr_data, field_with_variation, pre_processed_char, field_with_variation=field_with_variation , tenant_id=tenant_id)

    field_neighbourhood = prepare_neighbours(ocr_field_keyword, trained_info)
    # ocr_keywords = covert_keyword_to_trianed_info(ocr_keywords)

    neighbour_dict = get_nearest_neighbour(trained_info, field_neighbourhood)

    logging.debug(f'neighbour_dict - {neighbour_dict}')

    update_field_neighbour_dict(neighbour_dict, trained_info, tenant_id)

    quadrant_dict = extract_quadrant_information(trained_info, case_id, tenant_id=tenant_id)

    update_quadrant_dict(quadrant_dict, tenant_id=tenant_id)

    return True


@zipkin_span(service_name='ace_template_training', span_name='remove_keys')
def remove_keys(ocr_data, ocr_keywords):
    """
    Author : Akshat Goyal
    """
    all_values = []

    for page_no, data in enumerate(ocr_data):
        page_values = []
        for word in data:
            word['page'] = page_no
            word_match = False
            for key in ocr_keywords:
                logging.debug(f"key - {key}")

                if percentage_inside([word['left'], word['right'], word['bottom'], word['top']], \
                                     [key['left'], key['right'], key['bottom'],
                                      key['top']]) > parameters['remove_key_match_threshold']:
                    word_match = True
            if not word_match:
                page_values.append(word)

        all_values.append(page_values)

    return all_values


@zipkin_span(service_name='ace_template_training', span_name='get_field_validations')
def get_field_validations(tenant_id=None):
    # * Get the OCR tab ID
    db_config = {
        'host': os.environ['HOST_IP'],
        'user': os.environ['LOCAL_DB_USER'],
        'password': os.environ['LOCAL_DB_PASSWORD'],
        'port': os.environ['LOCAL_DB_PORT'],
        'tenant_id': tenant_id
    }
    queue_db = DB('queues', **db_config)

    tab_df = queue_db.get_all('tab_definition')
    ocr_tab = tab_df.loc[tab_df['source'] == 'ocr']
    tab_id = 1

    # * Get the OCR fields
    query = 'SELECT * FROM `field_definition` WHERE `tab_id`=%s'
    ocr_fields = queue_db.execute(query, params=[tab_id])
    ocr_fields_list = ocr_fields.to_dict('records')
    ocr_fields_dict = {}

    for ocr_field_data in ocr_fields_list:
        ocr_fields_dict[ocr_field_data['display_name']] = ocr_field_data

    return ocr_fields_dict


'''Utility functions table info '''


@zipkin_span(service_name='ace_template_training', span_name='header_helper')
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


@zipkin_span(service_name='ace_template_training', span_name='get_header_list')
def get_header_list(json_data):
    header_list_dict, col_children_no = header_helper(json_data)
    header_list = [v for k, v in header_list_dict.items()]
    return header_list, col_children_no


@app.route('/force_template', methods=['POST', 'GET'])
def force_template():
    ui_data = request.json
    if 'tenant_id' in ui_data:
        tenant_id = ui_data['tenant_id']
    else:
        message = f'tenant_id not present'
        return {'flag': False, "message": message}

    attr = ZipkinAttrs(
        trace_id=generate_random_64bit_string(),
        span_id=generate_random_64bit_string(),
        parent_span_id=None,
        flags=None,
        is_sampled=False,
        tenant_id=tenant_id
    )

    with zipkin_span(
            service_name='ace_template_training',
            zipkin_attrs=attr,
            span_name='train',
            transport_handler=http_transport,
            sample_rate=0.5
    ) as zipkin_context:

        case_id = ui_data['case_id']
        template_name = ui_data['template_name']

        # Database configuration
        db_config = {
            'host': os.environ['HOST_IP'],
            'user': os.environ['LOCAL_DB_USER'],
            'password': os.environ['LOCAL_DB_PASSWORD'],
            'port': os.environ['LOCAL_DB_PORT'],
            'tenant_id': tenant_id
        }
        queue_db = DB('queues', **db_config)

        # Database configuration
        extraction_db_config = {
            'host': os.environ['HOST_IP'],
            'user': os.environ['LOCAL_DB_USER'],
            'password': os.environ['LOCAL_DB_PASSWORD'],
            'port': os.environ['LOCAL_DB_PORT'],
            'tenant_id': tenant_id
        }

        extraction_db = DB('extraction', **extraction_db_config)

        stats_db_config = {
            'host': os.environ['HOST_IP'],
            'user': os.environ['LOCAL_DB_USER'],
            'password': os.environ['LOCAL_DB_PASSWORD'],
            'port': os.environ['LOCAL_DB_PORT'],
            'tenant_id': tenant_id
        }

        kafka_db = DB('kafka', **db_config)

        message_flow = kafka_db.get_all('message_flow')
        listen_to_topic_df = message_flow.loc[message_flow['listen_to_topic'] == 'train']
        send_to_topic = list(listen_to_topic_df.send_to_topic)[0]

        stats_db = DB('stats', **stats_db_config)

        fields = {'template_name': template_name, 'cluster': None, 'queue': 'Processing'}

        # Insert a new record for each file of the cluster with template name set and cluster removed
        logging.debug(f'Extracting for case ID `{case_id}`')

        if retrain == 'yes':
            queue_db.update('process_queue', update=fields, where={'case_id': case_id})
            extraction_db.execute('DELETE from `ocr` where `case_id` = %s', params=[case_id])
            extraction_db.execute('DELETE from `business_rule` where `case_id` = %s', params=[case_id])
            audit_data = {
                "type": "update", "last_modified_by": "Force Template", "table_name": "process_queue",
                "reference_column": "case_id",
                "reference_value": case_id, "changed_data": json.dumps(fields)
            }
            stats_db.insert_dict(audit_data, 'audit')

            # Send case ID to extraction topic
            produce(send_to_topic, {'case_id': case_id, 'tenant_id': tenant_id})

            return jsonify({'flag': True, 'message': 'Successfully extracting with new template. Please wait!'})

        cluster_query = "SELECT `id`,`cluster` from `process_queue` where `case_id` = %s"
        cluster = list(queue_db.execute(cluster_query, params=[case_id]).cluster)[0]

        logging.debug(cluster)

        queue_db.update('process_queue', update=fields, where={'case_id': case_id})
        audit_data = {
            "type": "update", "last_modified_by": "Force Template", "table_name": "process_queue",
            "reference_column": "case_id",
            "reference_value": case_id, "changed_data": json.dumps(fields)
        }
        stats_db.insert_dict(audit_data, 'audit')

        # Send case ID to extraction topic
        produce(send_to_topic, {'case_id': case_id, 'tenant_id': tenant_id})

        if cluster is not None:
            cluster_ids_query = "SELECT * from `process_queue` where `cluster` = %s"
            cluster_files_df = queue_db.execute(cluster_ids_query, params=[str(int(cluster))])

            cluster_case_data = cluster_files_df.to_dict(orient='records')
        else:
            return jsonify({'flag': True, 'message': 'Successfully extracted!'})

        logging.debug(cluster_case_data)
        for case_data in cluster_case_data:
            if case_data['case_id'] == case_id:
                logging.debug(f'Already extracted for case ID `{case_id}`')
                continue

            cluster_case_id = case_data['case_id']

            # Update the record for each file of the cluster with template name set and cluster removed
            logging.debug(f'Extracting for case ID - Force `{cluster_case_id}`')

            fields['template_name'] = template_name
            fields['cluster'] = None

            queue_db.update('process_queue', update=fields, where={'case_id': cluster_case_id})
            audit_data = {
                "type": "update", "last_modified_by": "Force Template Cluster", "table_name": "process_queue",
                "reference_column": "case_id",
                "reference_value": case_id, "changed_data": json.dumps(fields)
            }
            stats_db.insert_dict(audit_data, 'audit')

            # Send case ID to extraction topic
            produce(send_to_topic, {'case_id': cluster_case_id, 'tenant_id': tenant_id})

        return jsonify({'flag': True, 'message': 'Successfully extracted!'})


@app.route('/retrain', methods=['POST', 'GET'])
def retrain():
    ui_data = request.json
    if 'tenant_id' in ui_data:
        tenant_id = ui_data['tenant_id']
    else:
        message = f'tenant_id not present'
        return {'flag': False, "message": message}

    attr = ZipkinAttrs(
        trace_id=generate_random_64bit_string(),
        span_id=generate_random_64bit_string(),
        parent_span_id=None,
        flags=None,
        is_sampled=False,
        tenant_id=tenant_id
    )

    with zipkin_span(
            service_name='ace_template_training',
            zipkin_attrs=attr,
            span_name='train',
            transport_handler=http_transport,
            sample_rate=0.5
    ) as zipkin_context:

        # ! Requires `template_name`, `extracted_data`, `case_id`, `trained_data`, `resize_factor`
        # ! `header_ocr`, `footer_ocr`, `address_ocr`
        # Database configuration
        db_config = {
            'host': os.environ['HOST_IP'],
            'user': os.environ['LOCAL_DB_USER'],
            'password': os.environ['LOCAL_DB_PASSWORD'],
            'port': os.environ['LOCAL_DB_PORT'],
            'tenant_id': tenant_id
        }
        queue_db = DB('queues', **db_config)
        # queue_db = DB('queues')

        trained_db_config = {
            'host': os.environ['HOST_IP'],
            'user': os.environ['LOCAL_DB_USER'],
            'password': os.environ['LOCAL_DB_PASSWORD'],
            'port': os.environ['LOCAL_DB_PORT'],
            'tenant_id': tenant_id
        }
        trained_db = DB('template_db', **trained_db_config)
        # trained_db = DB('template_db')

        table_db_config = {
            'host': os.environ['HOST_IP'],
            'user': os.environ['LOCAL_DB_USER'],
            'password': os.environ['LOCAL_DB_PASSWORD'],
            'port': os.environ['LOCAL_DB_PORT'],
            'tenant_id': tenant_id
        }
        table_db = DB('table_db', **table_db_config)
        # trained_db = DB('template_db')

        extarction_db_config = {
            'host': os.environ['HOST_IP'],
            'user': os.environ['LOCAL_DB_USER'],
            'password': os.environ['LOCAL_DB_PASSWORD'],
            'port': os.environ['LOCAL_DB_PORT'],
            'tenant_id': tenant_id
        }
        extraction_db = DB('extraction', **extarction_db_config)
        # extraction_db = DB('extraction')

        stats_db_config = {
            'host': os.environ['HOST_IP'],
            'user': os.environ['LOCAL_DB_USER'],
            'password': os.environ['LOCAL_DB_PASSWORD'],
            'port': os.environ['LOCAL_DB_PORT'],
            'tenant_id': tenant_id
        }

        stats_db = DB('stats', **stats_db_config)

        template_name = ui_data['template_name']
        fields = ui_data['fields']
        case_id = ui_data['case_id']
        table_check = False

        new_vendor = ui_data['temp_type']

        if new_vendor == 'new':
            trained_db.insert_dict({"vendor_name": template_name}, 'vendor_list')

        if json.loads(ui_data['trained_table']):
            try:
                trained_table = json.dumps([[json.loads(ui_data['trained_table'])['0']]])
            except:
                try:
                    trained_table = json.dumps([[json.loads(ui_data['trained_table'])['undefined']]])
                except:
                    trained_table = '[]'

            table_check = True

        resize_factor = ui_data['resize_factor']

        try:
            table_trained_info = ui_data['table'][0]['table_data']['trained_data']
            table_method = ui_data['table'][0]['method']

            table_data_column_values = {
                'template_name': template_name,
                'method': table_method,
                'table_data': json.dumps(table_trained_info)
                # bytes(table_trained_info, 'utf-8').decode('utf-8', 'ignore')
            }
            table_db.insert_dict(table_data_column_values, 'table_info')
        except:
            table_trained_info = {}

        # process_queue_df = queue_db.get_all('process_queue')
        query = "SELECT * from process_queue where case_id = %s"
        latest_case = queue_db.execute(query, params=[case_id])

        # * Calculate relative positions and stuff
        query = 'SELECT * FROM `ocr_info` WHERE `case_id`=%s'
        params = [case_id]
        ocr_info = queue_db.execute(query, params=params)
        try:
            ocr_data = json.loads(json.loads(list(ocr_info.ocr_data)[0]))
        except:
            ocr_data = json.loads(list(ocr_info.ocr_data)[0])
        trained_data = get_trained_info(ocr_data, fields, resize_factor)

        # * Add trained information & template name into `trained_info` table
        trained_data_column_values = {
            'template_name': template_name,
            'field_data': json.dumps(trained_data),
        }
        # trained_db.insert_dict(trained_data_column_values, 'trained_info')
        trained_db.update('trained_info', update=trained_data_column_values, where={'template_name': template_name})
        # TODO: Add table data into a table training microservice database

        # * Save extracted data to ocr table
        # Create a dictionary with field names as key and extracted value as value of the key
        extracted_column_values = {'case_id': case_id}
        columns_in_ocr = extraction_db.get_column_names('ocr')
        extracted_column_values['highlight'] = {}
        for _, field in fields.items():
            column_name = field['field']
            value = field['value']
            value_scope = field['coordinates']
            try:
                page_no = int(field['page'])
            except:
                page_no = 0
            # Check if column name is there in OCR table
            if column_name not in columns_in_ocr:
                logging.debug(f' - `{column_name}` does not exist in `ocr` table. Skipping field.')
                continue

            # Add highlight to the dict
            # extracted_column_values['highlight'] = highlight
            highlight = get_highlights(value, ocr_data, value_scope[0], page_no)
            extracted_column_values['highlight'][column_name] = highlight

            extracted_column_values[column_name] = value

        # highlight = {}
        standardized_data = standardize_date(extracted_column_values)
        standardized_data['highlight'] = json.dumps(extracted_column_values['highlight'])
        if table_check:
            standardized_data['Table'] = trained_table
        extraction_db.update('ocr', standardized_data, {'case_id': case_id})
        audit_data = {
            "type": "update", "last_modified_by": "Train", "table_name": "ocr", "reference_column": "case_id",
            "reference_value": case_id, "changed_data": json.dumps(standardized_data)
        }
        stats_db.insert_dict(audit_data, 'audit')

        return jsonify({'flag': True, 'message': 'Retraining completed!'})


@app.route('/testFields', methods=['POST', 'GET'])
def test_fields():
    data = request.json
    if 'tenant_id' in data:
        tenant_id = data['tenant_id']
    else:
        message = f'tenant_id not present'
        return {'flag': False, "message": message}

    attr = ZipkinAttrs(
        trace_id=generate_random_64bit_string(),
        span_id=generate_random_64bit_string(),
        parent_span_id=None,
        flags=None,
        is_sampled=False,
        tenant_id=tenant_id
    )

    with zipkin_span(
            service_name='ace_template_training',
            zipkin_attrs=attr,
            span_name='train',
            transport_handler=http_transport,
            sample_rate=0.5
    ) as zipkin_context:
        case_id = data['case_id']
        global  parameters

        case_id = data['case_id']
        force_check = data['force_check']
        query = "SELECT `id`, `ocr_data` from `ocr_info` WHERE `case_id`=%s"

        db_config = {
            'host': os.environ['HOST_IP'],
            'user': os.environ['LOCAL_DB_USER'],
            'password': os.environ['LOCAL_DB_PASSWORD'],
            'port': os.environ['LOCAL_DB_PORT'],
            'tenant_id': tenant_id
        }
        queue_db = DB('queues', **db_config)

        template_db_config = {
            'host': os.environ['HOST_IP'],
            'user': os.environ['LOCAL_DB_USER'],
            'password': os.environ['LOCAL_DB_PASSWORD'],
            'port': os.environ['LOCAL_DB_PORT'],
            'tenant_id': tenant_id
        }
        templates_db = DB('template_db', **template_db_config)

        ocr_data_df = queue_db.execute(query, params=[case_id])

        try:
            ocr_data = json.loads(json.loads(ocr_data_df['ocr_data'].iloc[0]))
        except:
            ocr_data = json.loads(ocr_data_df['ocr_data'].iloc[0])


        checkboxes_all = {}
        if force_check == 'yes':
            template_name = data['template_name']
            trained_info_data = templates_db.get_all('trained_info')
            template_info_df = trained_info_data.loc[trained_info_data['template_name'] == template_name]

            # * Get fields to extract (fte) from the trained info
            trained_info = json.loads(template_info_df.field_data.values[0])
            remove_keys = ['header_ocr', 'footer_ocr', 'address_ocr']
            [trained_info.pop(key, None) for key in remove_keys]
        else:
            field_data = data['field_data']
            updated_fields = {}
            for key, field in field_data.items():
                if not field.get('not_in_invoice', False):
                    updated_fields[key] = field

            resize_factor = data['width'] / parameters['default_img_width']
            trained_info, checkboxes_all = get_trained_info(ocr_data, updated_fields, resize_factor)
            logging.info(f'trained_info `{trained_info}`')
            logging.info(f'checkbox_info `{checkboxes_all}`')

        value_extract_params = {
                                "case_id": case_id,
                                "field_data": trained_info,
                                "checkbox_data": checkboxes_all,
                                "tenant_id": tenant_id
                                }
        if os.environ['MODE'] == "Test":
            return value_extract_params

        host = 'extractionapi'
        port = 80
        route = 'predict_field'
        logging.debug(f'Hitting URL: http://{host}:{port}/{route}')
        logging.debug(f'Sending Data: {value_extract_params}')
        headers = {'Content-type': 'application/json; charset=utf-8', 'Accept': 'text/json'}
        response = requests.post(f'http://{host}:{port}/{route}', json=value_extract_params, headers=headers)
        logging.debug(f'response {response.content}')
        return jsonify({'flag': 'true', 'data': response.json()})


@app.route('/train', methods=['POST', 'GET'])
def train():
    ui_data = request.json

    if 'tenant_id' in ui_data:
        tenant_id = ui_data['tenant_id']
    else:
        message = f'tenant_id not present'
        return {'flag': False, "message": message}

    attr = ZipkinAttrs(
        trace_id=generate_random_64bit_string(),
        span_id=generate_random_64bit_string(),
        parent_span_id=None,
        flags=None,
        is_sampled=False,
        tenant_id=tenant_id
    )

    with zipkin_span(
            service_name='ace_template_training',
            zipkin_attrs=attr,
            span_name='train',
            transport_handler=http_transport,
            sample_rate=0.5
    ) as zipkin_context:
        # ! Requires `template_name`, `extracted_data`, `case_id`, `trained_data`, `resize_factor`
        # ! `header_ocr`, `footer_ocr`, `address_ocr`
        logging.debug(f'ui_data {ui_data}')
        # Database configuration
        db_config = {
            'host': os.environ['HOST_IP'],
            'user': os.environ['LOCAL_DB_USER'],
            'password': os.environ['LOCAL_DB_PASSWORD'],
            'port': os.environ['LOCAL_DB_PORT'],
            'tenant_id': tenant_id
        }
        queue_db = DB('queues', **db_config)
        trained_db = DB('template_db', **db_config)
        table_db = DB('table_db', **db_config)
        extraction_db = DB('extraction', **db_config)
        kafka_db = DB('kafka', **db_config)
        stats_db = DB('stats', **db_config)

        template_name = ui_data['template_name']
        new_vendor = ui_data['temp_type']
        fields = ui_data['fields']
        updated_fields = {}
        for key, field in fields.items():
            if not field.get('not_in_invoice', False):
                updated_fields[key] = field
        fields = updated_fields
        case_id = ui_data['case_id']

        if new_vendor == 'new':
            trained_db.insert_dict({"vendor_name": template_name}, 'vendor_list')

        try:
            trained_table = json.dumps([[json.loads(ui_data['trained_table'])['0']]])
        except:
            try:
                trained_table = json.dumps([[json.loads(ui_data['trained_table'])['undefined']]])
            except:
                trained_table = '[]'
        resize_factor = ui_data['resize_factor']
        header_ocr = ui_data['template']['header_ocr']['value']
        footer_ocr = ui_data['template']['footer_ocr']['value']
        address_ocr = [ui_data['template']['address_ocr']['value']]  # A list because ... idk ask Ashish
        try:
            unique_fields = ui_data['template']['uniqueFields']['fields']
            condition = ui_data['template']['uniqueFields']['condition']
        except:
            unique_fields = None
            condition = None
        # * Check if template name already exists
        trained_info = trained_db.get_all('trained_info')
        trained_template_names = list(trained_info.template_name)
        if template_name.lower() in [t.lower() for t in trained_template_names]:
            message = f'Template name `{template_name}` already exist.'
            logging.debug(message)
            return jsonify({'flag': False, 'message': message})
        try:
            table_trained_info = ui_data['table'][0]['table_data']['trained_data']
            try:
                table_method = ui_data['table'][0]['method']
            except:
                table_method = ''

            table_data_column_values = {
                'template_name': template_name,
                'method': table_method,
                'table_data': json.dumps(table_trained_info)
                # bytes(table_trained_info, 'utf-8').decode('utf-8', 'ignore')
            }
            table_db.insert_dict(table_data_column_values, 'table_info')

            # saving table headers dictionary
            try:
                json_data = table_trained_info
                header_list, col_children_no = get_header_list(json_data)
                table_header_list_dict = {}
                table_keywords_dict = {}
                for header in header_list:
                    table_header_list_dict[header] = ''
                    [table_keywords_dict.update({word: ''}) for word in header.split()]
                table_keywords = {
                    'table_header_list': table_header_list_dict,
                    'table_keywords': table_keywords_dict
                }
                table_keywords_info = table_db.get_all('table_keywords')

                table_header_list_old = table_keywords_info.loc[0].table_header_list
                table_header_list_old = json.loads(table_header_list_old)
                table_header_list_old.update(table_header_list_dict)

                table_keywords_old = table_keywords_info.loc[0].table_keywords
                table_keywords_old = json.loads(table_keywords_old)
                table_keywords_old.update(table_keywords_dict)

                table_keywords = {
                    'table_header_list': json.dumps(table_header_list_old),
                    'table_keywords': json.dumps(table_keywords_old)
                }
                where = {'id': 0}
                table_db.update('table_keywords', update=table_keywords, where=where)
            except Exception as e:
                logging.exception('error in saving table keywords')
        except Exception as e:
            logging.exception('table info not saved')
            table_trained_info = {}

        query = "SELECT * from process_queue where queue = 'Template Exceptions'"
        process_queue_df = queue_db.execute(query)
        # latest_process_queue = queue_db.get_latest(process_queue_df, 'case_id', 'created_date')
        query = "SELECT * from process_queue where case_id = %s"
        latest_case = queue_db.execute(query, params=[case_id])

        # * Calculate relative positions and stuff
        query = 'SELECT * FROM `ocr_info` WHERE `case_id`=%s'
        params = [case_id]
        ocr_info = queue_db.execute(query, params=params)
        try:
            ocr_data = json.loads(json.loads(list(ocr_info.ocr_data)[0]))
        except:
            ocr_data = json.loads(list(ocr_info.ocr_data)[0])


        trained_data, checkboxes_all = get_trained_info(ocr_data, fields, resize_factor)

        pre_processed_char = []
        for page in ocr_data:
            page = sort_ocr(page)
            char_index_list, haystack = convert_ocrs_to_char_dict_only_al_num(page)
            pre_processed_char.append([char_index_list, haystack])

        update_field_dict_with_neighbour(trained_data, ocr_data, pre_processed_char, case_id, tenant_id=tenant_id)

        # * Add trained information & template name into `trained_info` table
        trained_data_column_values = {
            'template_name': template_name,
            'field_data': json.dumps(trained_data),
            'header_ocr': header_ocr,
            'footer_ocr': footer_ocr,
            'address_ocr': json.dumps(address_ocr),
            'checkbox_data': json.dumps(checkboxes_all),
            'unique_fields': unique_fields,
            'operator': condition
        }
        trained_db.insert_dict(trained_data_column_values, 'trained_info')

        ui_train_data = {
            'case_id': case_id,
            'template_name': template_name,
            'ui_train_info': json.dumps(ui_data)
        }

        trained_db.insert_dict(ui_train_data, 'ui_train_data')

        # TODO: Add table data into a table training microservice database

        # * Save extracted data to ocr table
        # Create a dictionary with field names as key and extracted value as value of the key
        extracted_column_values = {'case_id': case_id}
        columns_in_ocr = extraction_db.get_column_names('ocr')
        extracted_column_values['highlight'] = {}
        logging.debug(fields)
        for _, field in fields.items():
            column_name = field['field']
            value = field['value']
            value_scope = field['coordinates']
            try:
                page_no = int(field['page'])
            except:
                page_no = 0
            # Check if column name is there in OCR table
            if column_name not in columns_in_ocr:
                logging.debug(f' - `{column_name}` does not exist in `ocr` table. Skipping field.')
                continue

            # Add highlight to the dict
            # extracted_column_values['highlight'] = highlight
            highlight = get_highlights(value, ocr_data, value_scope[0], page_no)
            extracted_column_values['highlight'][column_name] = highlight

            extracted_column_values[column_name] = value

        # highlight = {}
        standardized_data = standardize_date(extracted_column_values)
        standardized_data['highlight'] = json.dumps(extracted_column_values['highlight'])
        standardized_data['Table'] = trained_table

        extraction_db.insert_dict(standardized_data, 'ocr')
        audit_data = {
            "type": "insert", "last_modified_by": "Train", "table_name": "ocr", "reference_column": "case_id",
            "reference_value": case_id, "changed_data": json.dumps(standardized_data)
        }
        stats_db.insert_dict(audit_data, 'audit')

        # get the queue name
        current_queue_df = queue_db.get_all('process_queue', condition={'case_id': case_id})

        logging.info(current_queue_df)

        current_queue = list(current_queue_df['queue'])[0]

        # * Update the queue name and template name in the process_queue
        query = 'SELECT * FROM `workflow_definition`, `queue_definition` WHERE ' \
                '`workflow_definition`.`queue_id`=`queue_definition`.`id` '
        template_exc_wf = queue_db.execute(query)
        move_to_queue_id = list(template_exc_wf.loc[template_exc_wf['unique_name'] == current_queue]['move_to'])[0]
        query = 'SELECT * FROM `queue_definition` WHERE `id`=%s'
        move_to_queue_df = queue_db.execute(query, params=[move_to_queue_id])
        move_to_queue = list(move_to_queue_df['unique_name'])[0]
        update = {'queue': move_to_queue, 'template_name': template_name}
        where = {'case_id': case_id}
        queue_db.update('process_queue', update=update, where=where)
        audit_data = {
            "type": "update", "last_modified_by": "Train", "table_name": "process_queue", "reference_column": "case_id",
            "reference_value": case_id, "changed_data": json.dumps(update)
        }
        stats_db.insert_dict(audit_data, 'audit')

        # updating queue trace information
        update_queue_trace(queue_db, case_id, move_to_queue)

        # # To Enable only training
        # return jsonify({'flag': True, 'message': 'Training completed!'})

        # * Run extraction on the same cluster
        cluster = list(latest_case.cluster)[0]
        cluster_files_df = process_queue_df.loc[process_queue_df['cluster'] == cluster]
        cluster_case_data = cluster_files_df.to_dict(orient='records')
        for case_data in cluster_case_data:
            if case_data['case_id'] == case_id:
                logging.debug(f'Already extracted for case ID `{case_id}`')
                continue

            cluster_case_id = case_data['case_id']

            # Update the record for each file of the cluster with template name set and cluster removed
            logging.debug(f'Extracting for case ID - cluster `{cluster_case_id}`')

            fields['template_name'] = template_name
            fields['cluster'] = None

            queue_db.update('process_queue', update=fields, where={'case_id': cluster_case_id})
            audit_data = {
                "type": "update", "last_modified_by": "Train", "table_name": "process_queue",
                "reference_column": "case_id",
                "reference_value": case_id, "changed_data": json.dumps(fields)
            }
            stats_db.insert_dict(audit_data, 'audit')


            message_flow = kafka_db.get_all('message_flow')
            listen_to_topic_df = message_flow.loc[message_flow['listen_to_topic'] == 'train']
            send_to_topic = list(listen_to_topic_df.send_to_topic)[0]
            # Send case ID to extraction topic
            produce(send_to_topic, {'case_id': cluster_case_id, 'tenant_id': tenant_id})

        return jsonify({'flag': True, 'message': 'Training completed!'})


@app.route('/get_ocr_data_training', methods=['POST', 'GET'])
def get_ocr_data():
    data = request.json

    if 'tenant_id' in data:
        tenant_id = data['tenant_id']
    else:
        message = f'tenant_id not present'
        return {'flag': False, "message": message}

    attr = ZipkinAttrs(
        trace_id=generate_random_64bit_string(),
        span_id=generate_random_64bit_string(),
        parent_span_id=None,
        flags=None,
        is_sampled=False,
        tenant_id=tenant_id
    )

    with zipkin_span(
            service_name='ace_template_training',
            zipkin_attrs=attr,
            span_name='train',
            transport_handler=http_transport,
            sample_rate=0.5
    ) as zipkin_context:
        case_id = data['case_id']


        logging.debug(f'case_id - {case_id}')

        db_config = {
            'host': os.environ['HOST_IP'],
            'port': 3306,
            'user': os.environ['LOCAL_DB_USER'],
            'password': os.environ['LOCAL_DB_PASSWORD'],
            'tenant_id': tenant_id
        }
        db = DB('queues', **db_config)

        trained_db = DB('template_db', **db_config)

        try:
            io_db = DB('io_configuration', **db_config)
            query = "SELECT * FROM `output_configuration`"
            file_parent = list(io_db.execute(query).access_1)[0] + '/'
        except:
            file_parent = ''
            logging.info('No output folder defined')

        # Get all OCR mandatory fields
        try:
            tab_df = db.get_all('tab_definition')
            ocr_tab_id = tab_df.loc[tab_df['source'] == 'ocr'].index.values.tolist()

            tab_list = ', '.join([str(i) for i in ocr_tab_id])
            logging.debug(f'Tab List: {tab_list}')
            query = f'SELECT * FROM `field_definition` WHERE `tab_id`in ({tab_list})'

            ocr_fields_df = db.execute(query)
            mandatory_fields = list(ocr_fields_df.loc[ocr_fields_df['mandatory'] == 1]['display_name'])
            logging.debug(f'OCR Fields DF: {ocr_fields_df}')
            fields = list(ocr_fields_df['display_name'])

        except Exception as e:
            logging.exception(f'Error getting mandatory fields: {e}')
            mandatory_fields = []
            fields = []

        # Get data related to the case from invoice table
        invoice_files_df = db.get_all('process_queue')

        case_files = invoice_files_df.loc[invoice_files_df['case_id'] == case_id]
        if case_files.empty:
            message = f'No such case ID {case_id}.'
            logging.debug(f'ERROR: {message}')
            return jsonify({'flag': False, 'message': message})

        query = 'SELECT * FROM `ocr_info` WHERE `case_id`=%s'
        params = [case_id]
        ocr_info = db.execute(query, params=params)

        try:
            ocr_data = json.loads(json.loads(list(ocr_info.ocr_data)[0]))
        except:
            ocr_data = json.loads(list(ocr_info.ocr_data)[0])

        pre_processed_char = []
        for index, page in enumerate(ocr_data):
            page = sort_ocr(page)

            char_index_list, haystack = convert_ocrs_to_char_dict_only_al_num(page)
            pre_processed_char.append([char_index_list, haystack])

        pdf_type = list(case_files.document_type)[0]

        file_name = list(case_files['file_name'])[0]

        try:
            file_name = file_parent + file_name
        except:
            file_name = file_parent + case_id + '.pdf'

        quadrant_dict = get_quadrant_dict(tenant_id=tenant_id)

        _, ocr_field_keyword = get_keywords(ocr_data, mandatory_fields, pre_processed_char, case_id=case_id,
                                            tenant_id=tenant_id)

        ocr_field_keyword = get_keywords_max_length(mandatory_fields, ocr_field_keyword)

        ocr_field_keyword = get_keywords_in_quadrant(mandatory_fields, ocr_field_keyword, case_id, standard_width=parameters['default_img_width'], tenant_id=tenant_id)

        logging.debug(f'ocr_field_keyword- {ocr_field_keyword}')
        # ocr_keywords = json.loads(list(ocr_info.keywords)[0])

        # ocr_field_keyword = json.loads(list(ocr_info.fields_keywords)[0])

        # ocr_data = [sort_ocr(data) for data in ocr_data]

        vendor_list = list(trained_db.get_all('vendor_list').vendor_name)
        template_list = list(trained_db.get_all('trained_info').template_name)

        ocr_keywords, _ = get_keywords_for_value(ocr_data, mandatory_fields, pre_processed_char, tenant_id=tenant_id)
        all_values = remove_keys(ocr_data, ocr_keywords)

        field_validations = get_field_validations(tenant_id)

        predicted_fields = get_predicted_fields(
            mandatory_fields,
            all_values,
            ocr_field_keyword,
            ocr_data,
            pre_processed_char,
            field_validations,
            quadrant_dict,
            case_id=case_id,
            tenant_id=tenant_id
        )

        if predicted_fields:
            trained_data = {}
            for field in predicted_fields:
                trained_data[field['field']] = get_trained_data_format(field)

            query = f'SELECT id, case_id from trained_info_predicted where case_id = "{case_id}"'
            logging.debug(query)

            check = trained_db.execute(query)

            logging.debug(check)
            if type(check) != bool:
                check = not check.empty

            if check:
                to_update = {'field_data': json.dumps(trained_data)}
                where = {'case_id': case_id}

                trained_db.update('trained_info_predicted', update=to_update, where=where)

            else:
                # * Add trained information & template name into `trained_info` table
                trained_data_column_values = {
                    'case_id': case_id,
                    'field_data': json.dumps(trained_data),
                    'ocr_data': json.dumps(ocr_data)
                }
                trained_db.insert_dict(trained_data_column_values, 'trained_info_predicted')

        return jsonify(
            {'flag': True, 'data': ocr_data, 'vendor_list': sorted(vendor_list), 'template_list': sorted(template_list),
             'mandatory_fields': mandatory_fields, 'predicted_fields': predicted_fields, 'fields': fields, 'type': pdf_type, 'file_name': file_name})


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-p', '--port', type=int, help='Port Number', default=5019)
    parser.add_argument('--host', type=str, help='Host', default='0.0.0.0')

    args = parser.parse_args()

    host = args.host
    port = args.port

    app.run(host=host, port=port, debug=False)
