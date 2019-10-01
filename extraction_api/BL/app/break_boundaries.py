import json
import pdb
from ace_logger import Logging

#threshold in percentage
threshold_to_expand = 60 

orientations_dict = {
    'left' : 0,
    'right' : 1,
    'top' : 3,
    'bottom' : 2
}

orientation_sign = {
    'left' : -1,
    'right' : 1,
    'top' : -1,
    'bottom' : 1
}

logging = Logging()

try:
    from app.finding_field_without_keyword import return_lines
    with open('app/parameters.json') as f:
        parameters = json.loads(f.read())
except:
    from finding_field_without_keyword import return_lines
    with open('parameters.json') as f:
       parameters = json.loads(f.read())

def sort_ocr(data):
    data = sorted(data, key = lambda i: (i['top']))
    for i in range(len(data)-1):
        if abs(data[i]['top'] - data[i+1]['top']) <6 :
            data[i+1]['top'] = data[i]['top']
    data = sorted(data, key = lambda i: (i['top'], i['left']))

    return data

def expand_along_orientation(box, orientations):
    global orientations_dict
    global orientation_sign
    logging(box)

    width = box[1] - box[0]
    height = box[2] - box[3]

    for temp_orientation in orientations:
        orientation = orientations_dict[temp_orientation]
        sign = orientation_sign[temp_orientation]
        #left or right
        if orientation in [0,1]:
            box[orientation] += (int(width*(threshold_to_expand/100)))*sign

        else:
            box[orientation] += (int(height*(threshold_to_expand/100)))*sign


    return box



def get_keyword_box(keyword_box):
    return {'left': keyword_box['x'],'right':keyword_box['x'] + keyword_box['width'], 'top': keyword_box['y'], 'bottom': keyword_box['y'] + keyword_box['height']}

def get_mid(first, second):
    return first + int((second - first)/2)

def get_crop_box(field_data):
    crop_box = {}

    try:
        crop_box['left'] = field_data['scope']['x'] - field_data['left']
        crop_box['top'] = field_data['scope']['y'] - field_data['top']
        crop_box['right'] = field_data['scope']['x'] + field_data['scope']['width'] + field_data['right']
        crop_box['bottom'] = field_data['scope']['y']  + field_data['scope']['height'] + field_data['bottom']
    except Exception as e:
        logging.exception(e)
        crop_box = {}

    return crop_box


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



def actual_get_orientations(crop_box, keyword_box):
    crop_box_mid_x = get_mid(crop_box['left'], crop_box['right'])
    crop_box_mid_y = get_mid(crop_box['top'], crop_box['bottom'])


    keyword_box_mid_x = get_mid(keyword_box['left'], keyword_box['right'])
    keyword_box_mid_y = get_mid(keyword_box['top'], keyword_box['bottom'])
    logging.debug("crop_box_mid ", [crop_box_mid_x, crop_box_mid_y])
    logging.debug("keyword ", keyword_box)
    orientation = []

    x_dis = crop_box_mid_x - keyword_box_mid_x
    y_dis = crop_box_mid_y - keyword_box_mid_y

    mod_x_dis = abs(x_dis)
    mod_y_dis = abs(y_dis)

    consider_x = False
    consider_y = False

    if mod_x_dis > (crop_box['right'] - crop_box['left'])*10/100:
        consider_x = True

    if mod_y_dis > (crop_box['bottom'] - crop_box['top'])*10/100:
        consider_y = True


    if consider_x and x_dis < 0:
        orientation.append('left')
    elif consider_x and x_dis  >0:
        orientation.append('right')
    if consider_y and y_dis < 0:
        orientation.append('top')
    elif consider_y and y_dis > 0:
        orientation.append('bottom')

    return orientation


def get_orientations(field_data):
    """
    Author : Akshat Goyal
    
    find the orientation of the value respect to keyword

    Args:
        field_data(dict) : field_data

    Returns:
        orientation(list) : [left, right, top, bottom] (example)

    """
    #if orientation field is there
    if 'orientation' in field_data:
        #if orientation field is not empty
        if field_data['orientation']:
            return field_data['orientation']

    #if orientation not there then use appromation to judge the orientaiton
    crop_box = get_crop_box(field_data)
    if not crop_box:
        return ''

    keyword_box = get_keyword_box(field_data['scope'])
    
    orientations = actual_get_orientations(crop_box, keyword_box)

    return orientations, crop_box


def break_boundaries(ocr_data, field_data, box, field_conf_threshold):
    """
    Author : Akshat Goyal
    
    breaks the boundaries enforced by the elders and consumes more than prescribed.

    basically just extends in the direction of value if value is not found by my ancestors.

    Args:
        ocr_data():
        field_data():
        box():

    returns:
        value
        highlight

    """

    orientations, crop_box = get_orientations(field_data)

    logging.debug("orientations - ", orientations)
    logging.debug("box before - ", box)
    box = expand_along_orientation(box, orientations)

    # box = [box['left'],box['right'],box['bottom'],box['top']]
    keyword = field_data['keyword']
    keyList=keyword.split()
    keyList = [i.strip() for i in keyList]

    logging.debug("box = ", box)
    word = []
    temp_highlight = []
    for data in ocr_data:
        word_box = [data['left'], data['right'], data['bottom'], data['top']]
        if(percentage_inside(box, word_box) > parameters['overlap_threshold']
            and data['word'] not in keyList):
            if 'junk' in field_data:
                data['word']=data['word'].replace(field_data['junk'],'')
            if data['confidence'] < field_conf_threshold:
                word.append('suspicious' + data['word'])
            else:
                word.append(data['word'])
            temp_highlight.append(data)

    return word, temp_highlight
