import ast
# from modules import extract
from difflib import SequenceMatcher
import re
from math import sqrt
import copy
import json

from functools import reduce

try:
    from app.ace_logger import Logging
except:
    from ace_logger import Logging

thres = 0.7
word_space_mul = 1.5
logging = Logging()

exclude = {'left':'right', 'right':'left', 'top':'bottom', 'bottom':'top'}


def get_word_space(ocrData):
    spaces = []
    for i in range(len(ocrData)-1):
        space = ocrData[i+1]['left'] - ocrData[i]['right']
        if(space>0 and space<100):
            spaces.append(space)
    avg_space = reduce(lambda x,y : x+y , spaces)/len(spaces)

    return avg_space

def find_in_ocr(ocr_data, value):
    """

    :param ocr_data:
    :param value:
    :return:
    """

    to_return = []
    try:
        if value["regex"] == 'true':
            regex = re.compile(value['keyword'])
            for ind, page_data in enumerate(ocr_data):
                for data in page_data:
                    if regex.search(data['word']) != None:
                        to_return.append([ind, data])
    except:
        for ind, page_data in enumerate(ocr_data):
            for data in page_data:
                for val in value['keyword'].split(' '):
                    ratio = SequenceMatcher(None, val, data['word']).ratio()
                    if ratio > thres:
                        to_return.append([ind, data])

    return to_return

def get_word_space_all_pages(ocr_data):
    for data in ocr_data:
        return get_word_space(data)

def get_distance(value1, value2):
    v1_x = value1['left'] + (value1['right']-value1['left'])/2
    v1_y = value1['top'] + (value1['bottom']-value1['top'])/2

    v2_x = value2['x'] + (value2['width'])/2
    v2_y = value2['y'] + (value2['height'])/2

    return sqrt((v1_x - v2_x)*(v1_x - v2_x)+(v1_y - v2_y)*(v1_y - v2_y))

def option_selector(options, value):

    min_m = 8888888
    page = 0

    for data in options:
        ind ,option = data
        temp_m = get_distance(option, value['scope'])
        if temp_m < min_m:
            nearest_option = option
            min_m = temp_m
            page = ind

    return nearest_option, page

def get_boundry_data(training_data):
    """

    :param training_data:
    :return:
    """
    boundry_data = {'left': '', 'right': '', 'top': '', 'bottom': ''}

    for key in boundry_data.keys():
        try:
            boundry_data[key] = training_data[key]
        except:
            pass

    return boundry_data

def give_default_value(scope, key):
    to_return = 0

    if key == 'left':
        to_return = scope['x']
    elif key == 'right':
        to_return = scope['x'] + scope['width']
    elif key == 'top':
        to_return = scope['y']
    elif key == 'bottom':
        to_return = scope['y'] + scope['height']

    return to_return

def get_ref_bound(train_value, actual_value):
    """

    :param train_value:
    :param actual_value:
    :return:
    """
    boundry_data = {'left': '', 'right': '', 'top': '', 'bottom': ''}
    for key in boundry_data.keys():
        boundry_data[key] = actual_value[key] - give_default_value(train_value['scope'], key)

    return boundry_data

def get_boundries_data(boundry_data, ocr_data, training_data, field):
    # gives the box from which we have to extract info
    box = {}
    # keeps tracks which boundary parameter is accurate
    box_accurate = {}
    # boundary of the reference field to that inaccurate field could be measure to some accuracy
    ref_boundry = {}

    page = 0

    no_options = False
    for key, value in boundry_data.items():
        no_options = False
        if value:
            options = find_in_ocr(ocr_data, value)
            logging.debug(f"Options: - {options} ")
            if not options:
                no_options = True
                # return box, box_accurate, ref_boundry, page
            else:
                #todo make the option to find whole word
                right_option, page = option_selector(options, value)

                try:
                    if True:
                        box[key] = right_option[exclude[key]]
                    else:
                        box[key] = right_option[key]
                except:
                    box[key] = right_option[key]
                finally:
                    box_accurate[key] = True
                try:
                    if value['reference'] == 'true':
                        ref_boundry = get_ref_bound(value, right_option)
                except:
                    pass

        if not value or no_options:
            box[key] = give_default_value(training_data[field]['scope'], key)
            # box[key] = training_data[field]['scope'][key]
            box_accurate[key] = False

    return box, box_accurate, ref_boundry, page

def adjust_boundary(actual_boundary, data):
    if data['left'] < actual_boundary['left']:
        actual_boundary['left'] = data['left']

    if data['right'] > actual_boundary['right']:
        actual_boundary['right'] = data['right']

    if data['top'] < actual_boundary['top']:
        actual_boundary['top'] = data['top']

    if data['bottom'] > actual_boundary['bottom']:
        actual_boundary['bottom'] = data['bottom']

    return actual_boundary

def return_lines(ocrdata):
    '''
        Parameters : ocrData
        Output     : Returns ocrdata line-by-line
    '''
    #needs the ocr data to be deskewed
    data = copy.deepcopy(ocrdata)
    data = sorted(data, key = lambda i: (i['top']))
    for i in range(len(data)-1):
        if abs(data[i]['top'] - data[i+1]['top']) <6 :
            data[i+1]['top'] = data[i]['top']
    data = sorted(data, key = lambda i: (i['top'], i['left']))
    lines = []
    line = []
    single_line = True
    if len(data) > 2:
        for i in range(len(data)-1):
            if(data[i+1]['top'] == data[i]['top']):
                line.append(data[i])
            else:
                single_line = False
                line.append(data[i])
                lines.append(line)
                line = []
        if single_line:
            line.append(data[len(data)-1])
            lines.append(line)
    else:
        if data[0]['top'] == data[-1]['top']:
            lines.append([data[0],data[-1]])
        else:
            lines.append([data[0]])
            lines.append([data[-1]])

    return lines

def percentage_inside(box, word):
    '''
    Get how much part of the word is inside the box
    '''
    box_l,box_r,box_b,box_t = box
    word_l,word_r,word_b,word_t = word
    area_of_word = (word_r - word_l) * (word_b - word_t)
    area_of_intersection = get_area_intersection(box, word, area_of_word)
    try:
        return area_of_intersection/area_of_word
    except:
        return 0

def get_area_intersection(box, word, area_of_word):
    box_l,box_r,box_b,box_t = box
    word_l,word_r,word_b,word_t = word

    mid_x = box_l+(box_r - box_l)/2
    mid_y = box_t+(box_b - box_t)/2

    width = box_r - box_l
    height = box_b - box_t

    margin_wid = (width*5)/100
    margin_hig = (height*5)/100

    #this means that word is can be too big for the box
    if (word_l >= box_l and word_l <= mid_x + margin_wid):
        dx = word_r - word_l
    else:
        dx = min(word_r, box_r) - max(word_l, box_l)

    if(word_t >= box_t and word_t <= mid_y + margin_hig):
        dy = word_b - word_t
    else:
        dy = min(word_b, box_b) - max(word_t, box_t)

    if (dx>=0) and (dy>=0):
        return dx*dy

    return 0

def compare_func(data, T,L,R,B):
    left_match = data['left'] + int(0.25 * data['width']) >= L
    right_match = data['right'] - int(0.25 * data['width']) <= R
    top_match = data['top'] + int(0.5 * data['height']) >= T
    bottom_match = data['bottom'] - int(0.5 * data['height']) <= B
    if (left_match and right_match and top_match and bottom_match):
        return left_match, right_match, top_match, bottom_match, True
    else:
        if percentage_inside((L,R,B,T),(data['left'], data['right'],data['bottom'],data['top'])) > thres:
            return left_match, right_match, top_match, bottom_match, True
        return left_match, right_match, top_match, bottom_match, False

def compare_func_t_B(data, T,B):
    top_match = data['top'] + int(0.5 * data['height']) >= T
    bottom_match = data['bottom'] - int(0.5 * data['height']) <= B
    if (top_match and bottom_match):
        return True
    else:
        return False

def left_expand(ind, ocr_data, T,L,R,B,  ocrDataLocal, actual_boundary, word_space):
    prev = ocr_data[ind]
    for i in range(ind-1, -1, -1):
        match = compare_func_t_B(ocr_data[i], T,B)
        if match:
            space = abs(ocr_data[i]['right'] - prev['left'])
            if space < word_space_mul*word_space:
                ocrDataLocal.append(ocr_data[i])
                actual_boundary = adjust_boundary(actual_boundary, ocr_data[i])
                prev = ocr_data[i]
            else:
                break
        else:
            break

    return ocrDataLocal, actual_boundary

def right_expand(ind, ocr_data, T,L,R,B, ocrDataLocal, actual_boundary, word_space):
    if ind>0:
        prev = ocr_data[ind-1]
    else:
        prev = ocr_data[ind]
        ind = ind+1

    # to check if the prev exist in the extracted data
    if prev not in ocrDataLocal:
        return ocrDataLocal, actual_boundary

    for i in range(ind, len(ocr_data), 1):
        match = compare_func_t_B(ocr_data[i], T,B)
        if match:
            space = ocr_data[i]['left'] - prev['right']
            if space < word_space_mul*word_space:
                ocrDataLocal.append(ocr_data[i])
                actual_boundary = adjust_boundary(actual_boundary, ocr_data[i])
                prev = ocr_data[i]
            else:
                break
        else:
            break
    return ocrDataLocal, actual_boundary

def get_actual_boundary(ocrDataLocal):
    box = {'left':1000, 'right':0, 'top' : 2000, 'bottom':0}

    for data in ocrDataLocal:
        for key in box:
            if 'left' in key or 'top' in key:
                if data[key] < box[key]:
                    box[key] = data[key]
            else:
                if data[key] > box[key]:
                    box[key] = data[key]
    return box

def get_extracted_data(ocrDataLocal):
    return_data = []

    for data in ocrDataLocal:
        return_data.append(data['word'])

    return return_data

def extract_data_in_line(ind, ocr_data, data, T, L, R, B, ocrDataLocal, actual_boundary, word_space, switch):
    #todo implement that if left and right is given then left and right expand does not go beyond it
    left_match, right_match, top_match, bottom_match, match = compare_func(data, T, L, R, B)
    try:
        if match:
            if not switch:
                ocrDataLocal, actual_boundary = left_expand(ind, ocr_data, T, L, R, B, ocrDataLocal, actual_boundary,
                                                            word_space)
            ocrDataLocal.append(data)
            actual_boundary = adjust_boundary(actual_boundary, data)
            switch = True
        else:
            if switch:
                ocrDataLocal, actual_boundary = right_expand(ind, ocr_data, T, L, R, B, ocrDataLocal, actual_boundary,
                                                             word_space)
            switch = False
    except Exception as e:
        logging.error(f'Something went wrong in extract_data_in_line. Passing. [{e}]')
        pass

    return ocrDataLocal, actual_boundary, switch

def extract_data(box, box_accurate, word_space, ocrData, pages):
    '''
        Parameters : Boundaries of Scope
        Output     : Returns that part of ocrdata which is confined within given boundaries
    '''

    T,L,R,B = box['top'], box['left'], box['right'], box['bottom']
    ocrDataLocal = []
    actual_boundary = copy.deepcopy(box)
    prev_match = []
    switch = False
    for page in pages:
        ocr_data_line_by_line = return_lines(ocrData[page])
        for ocr_data in ocr_data_line_by_line:
            for ind, data in enumerate(ocr_data):
                ocrDataLocal, actual_boundary, switch = extract_data_in_line(ind, ocr_data, data, T, L, R, B, ocrDataLocal, actual_boundary, word_space, switch)

    if actual_boundary != box:
        ocrDataLocal, actual_boundary = extract_data(actual_boundary, box_accurate, word_space, ocrData, pages)

    try:
        actual_boundary = get_actual_boundary(ocrDataLocal)
    except:
        pass

    return ocrDataLocal, actual_boundary

def make_highlight(highlight_actual, page, value):
    to_return = {}
    to_return['x'] = highlight_actual['left']
    to_return['y'] = highlight_actual['top']
    to_return['width'] = highlight_actual['right'] - highlight_actual['left']
    to_return['height'] = highlight_actual['bottom'] - highlight_actual['top']
    to_return['page'] = page
    to_return['word'] = value

    return to_return

def get_trained_boundary_data(training_data, field):
    try:
        return training_data[field]['boundary_data']
    except:
        return training_data

def find_field(field, field_data, template_name, ocr_data, highlight={}):
    """
    Author : Akshat Goyal

    :param record:
    :param columns:
    :return:
    """
    # print(record)
    # template_index = columns.index('template_name')
    # template_name = record[template_index]

    training_data = field_data
    return_value = ''
    # training_data = ast.literal_eval(db.get_trained_info_template(template_name))
    # trained_boundary_data = field_data['boundary_data']

    trained_boundary_data = get_trained_boundary_data(training_data, field)

    boundry_data = get_boundry_data(trained_boundary_data)

    # ocr_data_index = columns.index('ocr_data')
    # ocr_data = ast.literal_eval(record[ocr_data_index])
    # print("training_data : ", training_data)
    if not field in training_data:
        return return_value, highlight

    # print(boundry_data)
    box, box_accurate, ref_boundry, page = get_boundries_data(boundry_data, ocr_data, training_data, field)

    if not box:
        return return_value, highlight

    for pos, val in box_accurate.items():
        if not val:
            try:
                box[pos] = box[pos] + ref_boundry[pos]
            except:
                box[pos] = box[pos]

    word_space = get_word_space_all_pages(ocr_data)
    logging.debug(f'{box}, {box_accurate}, {word_space}, {[page]}')
    try:
        value, highlight_actual = extract_data(box, box_accurate, word_space, ocr_data, [page])
        logging.debug(f"Value : - {value}")
    except Exception as e:
        logging.exception('Something went wrong in find_fields. Check trace. Continuing.')

    value = get_extracted_data(value)
    return_value = (' '.join(value)).replace('/u00ad', '-')
    # print(value)
    # record[update_index] = (' '.join(value)).replace('/u00ad','-')

    # highlight_index = columns.index('highlight')
    # highlight = json.loads(record[highlight_index])

    try:
        highlight = make_highlight(highlight_actual, page, value)
        # highlight[field] = make_highlight(highlight_actual, page, value)
        # record[highlight_index] = json.dumps(highlight)
    except:
        pass
        # highlight = make_highlight(highlight_actual, page, value)

    return return_value, highlight
