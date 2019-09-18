import math 

try:
    from app.smart_training.utils import centroid_hunt
    from app.smart_training.utils import find_closest_mate
    from app.smart_training.utils import calculate_limit
    from app.smart_training.utils import ocrDataLocal
    from app.smart_training.utils import make_scope
    from app.smart_training.utils import get_rel_info
except:
    from smart_training.utils import centroid_hunt
    from smart_training.utils import find_closest_mate
    from smart_training.utils import calculate_limit
    from smart_training.utils import ocrDataLocal
    from smart_training.utils import make_scope
    from smart_training.utils import get_rel_info



def ocrDataLocal_special(T,L,R,B,ocrData):
    '''
        Parameters : Boundaries of Scope
        Output     : Returns that part of ocrdata which is confined within given boundaries
    '''
    
    ocrDataLocal = []
    for data in ocrData:
        # print(data)
        
        if  (data['left'] + int(0.25*data['width'])  >= L
            and data['left'] <= R
            and data['top'] + int(0.5*data['height']) >= T
            and data['bottom'] - int(0.5*data['height'])  <= B ):
            ocrDataLocal.append(data)
    return ocrDataLocal

def kv_keywords_prediction(values, file_keywords):
    """
    Author : Akshat Goyal

    Args:
        values : the value for which the keyword has to be extracted
            [
                {
                    word,
                    coordinates             
                },

            ]

        file_keywords : all the potential keyword in the file
            [
                {
                    word,
                    coordinates
                }
            ]

    """
    local_ocr = []
    local_ocr.extend(values)
    local_ocr.extend(file_keywords)

    
    #todo add split check code
    split_check = False

    keywords = []

    values = centroid_hunt(values)

    value_scope = make_scope(values)

    file_keywords = centroid_hunt(file_keywords)

    #getting keywords left to value
    file_keywords_left = ocrDataLocal_special(value_scope['top'],value_scope['left']-100,value_scope['right'],value_scope['bottom'],file_keywords)

    #getting keyword top to value
    file_keywords_top = ocrDataLocal_special(value_scope['top']-20,value_scope['left'],value_scope['right'],value_scope['bottom'],file_keywords)

    #getting keyword aronud value
    file_keywords_key = ocrDataLocal_special(value_scope['top']-50,value_scope['left']-100,value_scope['right'],value_scope['bottom'],file_keywords)

    closest_keywords = []

    if values:
        #get the keyword closet in left
        closest_keywords = find_closest_mate(values[0], file_keywords_left, no_of_mate=1)

        #get the keyword closet in top
        if not closest_keywords:
            closest_keywords = find_closest_mate(values[0], file_keywords_top, no_of_mate=1)

        #get the keyword closet around
        if not closest_keywords:
            closest_keywords = find_closest_mate(values[0], file_keywords_key, no_of_mate=1)

    return closest_keywords, split_check

def remove_dangling_special_character(ocr_value):
    """
    Author : Akshat Goyal

    Removes singleton special character
    """
    purged_list = []

    for value in ocr_value:
        if len(value['word'].strip()) == 1 and not value['word'].strip().isalnum():
            pass
        else:
            purged_list.append(value)

    return purged_list



def get_local_ocr_for_orientation(ocr_data, key_orientation, keyword_scope):
    """
    """

    if key_orientation == 'left':
        values = ocrDataLocal_special(keyword_scope['top'], keyword_scope['right'], keyword_scope['right']+100,keyword_scope['bottom'],ocr_data)

    elif key_orientation == 'right':
        values = ocrDataLocal_special(keyword_scope['top'],keyword_scope['left']-100,keyword_scope['left'],keyword_scope['bottom'],ocr_data)

    elif key_orientation == 'top':
        values = ocrDataLocal_special(keyword_scope['bottom'],keyword_scope['left']-100,keyword_scope['right']+100,keyword_scope['bottom']+50,ocr_data)

    elif key_orientation == 'bottom':
        values = ocrDataLocal_special(keyword_scope['top']-50,keyword_scope['left']-100,keyword_scope['right']+100,keyword_scope['top'],ocr_data)

    else: 
        values = ocr_data

    values = remove_dangling_special_character(values)

    return values


def find_closest_value(file_keywords, keyword_scope, values, field_orientaion_dict, field_validation):
    """
    Author : Akshat Goyal

    """
    closest_values = []
    if file_keywords:
        field_orientaion_dict = sorted(field_orientaion_dict, key = lambda x:x[1], reverse = True)
        if field_orientaion_dict:
            for key_orientation in field_orientaion_dict:
                value_orientation = get_local_ocr_for_orientation(values, key_orientation[0], keyword_scope)
                closest_values = find_closest_mate(file_keywords[0], value_orientation, no_of_mate=1, field_validation=field_validation)

                if closest_values:
                    break       

        if not closest_values:
            #getting values right to key
            values_left = get_local_ocr_for_orientation(values, 'left', keyword_scope)

            #getting values top to key
            values_top = get_local_ocr_for_orientation(values, 'top', keyword_scope)

            #getting values aronud key
            values_key = ocrDataLocal_special(keyword_scope['bottom'],keyword_scope['right'],keyword_scope['right']+200,keyword_scope['bottom']+50,values)
            values_key = remove_dangling_special_character(values_key)


            #get the keyword closet in left
            closest_values = find_closest_mate(file_keywords[0], values_left, no_of_mate=1, field_validation=field_validation)

            #get the keyword closet in top
            if not closest_values:
                closest_values = find_closest_mate(file_keywords[0], values_top, no_of_mate=1, field_validation=field_validation)

            #get the keyword closet around
            if not closest_values:
                closest_values = find_closest_mate(file_keywords[0], values_key, no_of_mate=1, field_validation=field_validation)

    return closest_values



def kv_values_prediction(values, file_keywords, field_orientaion_dict = None, field_validation=None):
    """
    Author : Akshat Goyal

    Args:
        values : all the values in the ocr
            [
                {
                    word,
                    coordinates             
                },

            ]

        file_keywords : the keyword for which value has to be extracted
            [
                {
                    word,
                    coordinates
                }
            ]

        field_orientaion_dict :
            {
                'left' : count,
                'right' : count,
                ...
            }

    """
    local_ocr = []
    local_ocr.extend(values)
    # local_ocr.extend(file_keywords)

    
    #todo add split check code
    split_check = False

    keywords = []

    file_keywords = centroid_hunt(file_keywords)

    keyword_scope = make_scope(file_keywords)

    values = centroid_hunt(values)

    closest_values = find_closest_value(file_keywords, keyword_scope, values, field_orientaion_dict, field_validation)

    return closest_values



def get_split_info(field_box, value_meta, keyword_box):
    """
    """
    field_value_coords_left = {
        'top':field_box['top'],
        'bottom':field_box['bottom'],
        'left':value_meta['left'],
        'right':value_meta['right']+10
    }
    field_value_coords_bottom = {
        'top':value_meta['top'],
        'bottom':value_meta['bottom'],
        'left':field_box['left'],
        'right':field_box['right']
    }

    key_val_meta = {}
    field_value_coords = {}

    if keyword_box:
        print('direction', get_rel_info(keyword_box,value_meta,'direction'))
        if get_rel_info(keyword_box,value_meta,'direction') == 'left':
            field_value_coords = field_value_coords_left
        else:
            field_value_coords = field_value_coords_bottom

        print('keyword_box',keyword_box)
        print('field_value_coords',field_value_coords)
        key_val_meta = get_rel_info(keyword_box, field_value_coords)
    key_val_meta = {**field_value_coords, **key_val_meta}

    return key_val_meta