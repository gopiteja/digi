import sys
import pdb
import re
import math
from ace_logger import Logging


try:
    from app.smart_training.key_value_method_key_prediction import get_split_info
    from app.smart_training.feud_key_prediction import feud_keywords_prediction
    from app.smart_training.context_maker import get_context
    from app.smart_training.utils import make_scope
    from app.smart_training.utils import percentage_inside
    from app.get_keywords import compute_all_key_list_coord
    from app.get_keywords import get_key_list_coord
except:
    from smart_training.key_value_method_key_prediction import get_split_info
    from smart_training.feud_key_prediction import feud_keywords_prediction
    from smart_training.context_maker import get_context
    from smart_training.utils import make_scope
    from smart_training.utils import percentage_inside
    from get_keywords import compute_all_key_list_coord
    from get_keywords import get_key_list_coord

logging = Logging()

def keyword_extract(pre_processed_char, keyword, scope):
    '''
    Get closest keyword to the trained keyword.
    '''

    char_index_list, haystack = pre_processed_char

    keyCords_list, keywords_list, counter = compute_all_key_list_coord([keyword], char_index_list, haystack)

    if(counter>0):
        keyList, keyCords = get_key_list_coord(keywords_list, keyCords_list, scope)

        keyList = ' '.join(keyList[0])


    if counter >0 and keyCords:
        key_top=keyCords[0]['top']
        key_bottom=keyCords[0]['bottom']
        key_left=keyCords[0]['left']
        key_right=keyCords[0]['right']

        return  {'height': key_bottom-key_top, 'width': key_right-key_left, 'y': key_top, 'x': key_left }

    else:
        logging.debug('keyword not found in OCR')
        return {}



def convert_into_trained_data(info, page_no):
    """
    """
    trained_info = {}
    trained_info['keyword'] = info['word']
    trained_info['scope'] = {
        'top' : info['top'],
        'left' : info['left'],
        'bottom' : info['bottom'],
        'right' : info['right']
    }

    trained_info['top'] = 0
    trained_info['bottom'] = 0
    trained_info['left'] = 0
    trained_info['right'] = 0

    trained_info['page'] = page_no

    return trained_info


def prepare_data(value):
    try:
        value['left'] = value['x']
        value['top'] = value['y']
        value['right'] = value['x'] + value['width']
        value['bottom'] = value['y'] + value['height']
    except:
        pass

    return value


def predict_keywords(keywords, values, kv_keywords, file_ocr, page_no, pre_processed_char):
    """
    Author : Akshat Goyal

    Args:
        Keywords : a list of all keyword in the ocr
        values : 
        kv_keywords : keyword associated with values
        file_ocr :

    Return :

    """
    logging.debug(kv_keywords)
    # print(values)
    key_val = []
    key_scope_actual = ''
    #if no keyword was cropped then we will predict the keyword
    if not kv_keywords:
        if keywords:
            kv_keywords, split_check = kv_keywords_prediction(values, keywords)
            if kv_keywords:
                kv_keywords = prepare_data(kv_keywords)
                key_scope_actual= make_scope([kv_keywords])
                key_scope = key_scope_actual
                key_val.append(kv_keywords)
                keyword = kv_keywords['word']
        else:
            kv_keywords = {}
    #if keyword cropped life is easy
    else:
        kv_keywords = prepare_data(kv_keywords)
        key_scope= make_scope([kv_keywords])
        key_val.append(kv_keywords)
        keyword = kv_keywords['word']
        key_scope_actual = keyword_extract(pre_processed_char[page_no], keyword, key_scope)
        if key_scope_actual:
            key_scope_actual = prepare_data(key_scope_actual)

    if not kv_keywords:
        key_scope = {}
        keyword = ''

    value_ocr = {}
    if keywords:
        feud = feud_keywords_prediction(values, keywords, kv_keywords, value_ocr)
    else:
        feud = {}

    boundary_data = {}
    if len(feud) > 1:
        for key, value in feud.items():
            boundary_data[key] = convert_into_trained_data(value, page_no)

    if values:
        values = prepare_data(values)
        value_scope = make_scope([values])
        key_val.append(values)
        value_scope_actual = keyword_extract(pre_processed_char[page_no], values['word'], value_scope)
        if value_scope_actual:
            value_scope_actual = prepare_data(value_scope_actual)

    else:
        value_scope = {}

    kv_scope = make_scope(key_val)

    

    context = get_context(file_ocr, kv_scope, page_no)
    if value_scope_actual and key_scope_actual:
        kv_scope_actual = make_scope([key_scope_actual, value_scope_actual])
        key_val_meta = get_split_info(kv_scope_actual, value_scope_actual, key_scope_actual)
    else:
        key_val_meta = {}


    relative = {
        'top' : '',
        'bottom' : '',
        'left' : '',
        'right' : ''
    }

    # calculating relative using this is incorrect as crop which ui sends is bigger than actual keyword,
    # so our relative will be skewed because we assume we are taking relativen from keyword actual coord not
    # the box drawn over it
    # import pdb
    # pdb.set_trace()
    if keyword and key_scope_actual:
        relative['top'] = key_scope['top'] - key_scope_actual['top']
        relative['bottom'] = kv_scope['bottom'] - key_scope_actual['bottom']
        relative['right'] = kv_scope['right'] - key_scope_actual['right']
        relative['left'] = key_scope['left'] - key_scope_actual['left']
    else:
        relative['top'] = kv_scope['top']
        relative['bottom'] = kv_scope['bottom']
        relative['right'] =  kv_scope['right']
        relative['left'] =  kv_scope['left']

    split_check = True
    return keyword, relative, key_scope_actual, split_check, context, boundary_data, key_val_meta

def main():
    values = [ 
                {
                    "width": 82,
                    "height": 8,
                    "top": 294,
                    "bottom": 303,
                    "right": 500,
                    "left": 418,
                    "word": "7242718100001548",
                    "confidence": 100,
                    "page" : 0
                }
             ]

    page_no = 0
    validation = ''

    key_list = ['Accounting:', 'Invoice Number:', 'Service Description:', 'Date of Issue:', 'Place of supply:', 'Contact details', 'GST:', 'TICKET DETAILS', 'Ticket Number:', 'Pax Name:', 'Date of issue:', 'Issuing Agent:', 'Business Trans. Type/Booking Class:']
    file = '/home/akshat/program/the_dream_project/2000459561.pdf'
    file_ocr = ocr(file, 670)
    keywords = get_keywords(file_ocr, key_list)

    keyword, relative, kv_scope, split_check, context_key_field_info, feud, key_val_meta = predict_keywords(keywords, values, file_ocr, page_no)


    training_info = {
        'keyword': keyword,
        'top': relative['top'],
        'right': relative['right'],
        'bottom': relative['bottom'],
        'left': relative['left'],
        'scope': kv_scope,
        'page': page_no,
        'junk' : '',
        'key_val_meta':key_val_meta,
        'validation':validation,
        'split_check' : split_check,
        'multi_key_field_info':'',
        'context_key_field_info':context_key_field_info,
        'boundary_data' : feud
    }

    logging.debug(training_info)


# main()




