import sys
from difflib import SequenceMatcher
from functools import reduce
import copy
import cv2


from ace_logger import Logging

logging = Logging()

def ocr_data_local(ocrData,T,L,R,B):
    '''
        Parameters : Boundaries of Scope
        Output     : Returns that part of ocrdata which is confined within given boundaries
    '''
    try:
        ocrDataLocal = []
        for data in ocrData:
            if  (data['left'] + int(0.25*data['width'])  >= L
                and data['right'] - int(0.25*data['width']) <= R
                and data['top'] + int(0.5*data['height']) >= T and data['bottom'] - int(0.5*data['height']) <= B ):
                ocrDataLocal.append(data)
        return ocrDataLocal
    except Exception as e:
        logging.exception('Error on line {}'.format(sys.exc_info()[-1].tb_lineno), type(e).__name__, e)
        return []


def get_word_space(ocrData):
    spaces = []
    for i in range(len(ocrData)-1):
        space = ocrData[i+1]['left'] - ocrData[i]['right']
        if(space>0 and space<100):
            spaces.append(space)
    avg_space = reduce(lambda x,y : x+y , spaces)/len(spaces)

    return avg_space


def return_lines(temp):
    '''
        Parameters : ocrData
        Output     : Returns ocrdata line-by-line
    '''
    #needs the ocr data to be deskewed
    data = copy.deepcopy(temp)
    data = sorted(data, key = lambda i: (i['top']))
    # print('data', data)
    for i in range(len(data)-1):
        if abs(data[i]['top'] - data[i+1]['top']) < 5:
            data[i+1]['top'] = data[i]['top']
    data = sorted(data, key = lambda i: (i['top'], i['left']))
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


def clean_word(string):
    string = ' '.join([''.join(e for e in word if e.isalnum() or e == '#' or e == '%') for word in string.split()])
    string = string.lower()
    return string


def get_field_list(field_json_data):
    '''
        function for getting field type

        Args:
            field_json_data(json): json data for fields trained in tables

        Returns:
            list: list of fields containing list of key and value for each
    '''

    field_list = []
    for k,v in field_json_data.items():
        if k.startswith('f'):
            field_list.append([k,v])
    return field_list


def get_field_type(field):
    '''
        function for getting field type

        Args:
            field(list): containing key and value for the field

        Returns:
            str: type of field
    '''

    k = field[0]
    v = field[1]
    return k[:k.rfind('_')+1]


def search_in_header():
    return data


def search_in_column():
    return data


def field_in_header_value_header(ocr_data, field, extracted_data_maintable, horizontal_lines, vertical_lines, header_bottom, main_table_bottom):
    '''
        function for searching and mapping the field which the table
        header contains
        algorithm:
            1. take header in the first row in extracted_data_maintable which
                is the header
            2. search the field in the header
            3. value must be one word forword or below
            4. if expected value not found in header then it must be in the
                column mostly it will be in column only except gst %s

        Args:
            ocr_data(list): list of ocr data of the page
            field(list): key and value of of the field in a list
            extracted_data_maintable(list): extracted table by table predict

        Returns:
            list: list of json of respective extracted values for the field
    '''

    data = []
    idx = field[1][['idx']]
    header = extracted_data_maintable[0][idx]
    if '%' in field[1]['keyword']:
        data = search_in_header(ocr_data, header, idx)
    else:
        data = search_in_column(ocr_data, header, idx)
    return data


# def keyword_value_search(ocr_data, key_word):
#
#     return []



def field_header_key_column_value(ocr_data, field_info, extracted_data_maintable, horizontal_lines_, vertical_lines, header_bottom, main_table_bottom, word_space, ocr_img_copy):
        try:
            data = []
            idx = field_info['idx']
            key_word = field_info['key_word']

            horizontal_lines = list(dict.fromkeys([hor[0][1] for hor in horizontal_lines_]))
            logging.debug(f'horizontal lines{horizontal_lines}')


            for i in range(len(horizontal_lines)-1):
                if(horizontal_lines[i] >= header_bottom):
                    T = horizontal_lines[i]
                    L = vertical_lines[idx-1][0][0]
                    R = vertical_lines[idx][0][0]
                    B = horizontal_lines[i+1]

                    Tem = copy.deepcopy(ocr_img_copy)
                    # cv2.line(Tem,(0,int(horizontal_lines[i])),(4000,int(horizontal_lines[i])),(50, 0, 255),1)
                    # cv2.line(Tem,(0,int(horizontal_lines[i+1])),(4000,int(horizontal_lines[i+1])),(50, 0, 255),1)
                    # cv2.namedWindow('main-table',cv2.WINDOW_NORMAL)
                    # cv2.resizeWindow('main-table', 1200,1200)
                    # cv2.imshow('main-table',T)
                    # cv2.waitKey(0)
                    # cv2.destroyAllWindows()

                    '''' nested columns or two values in one columns'''

                    ocr_data_ = ocr_data_local(ocr_data, T, L, R, B)
                    value = ''
                    for word in ocr_data_:
                        value += ' ' + word['word']
                    value = value.strip()
                    if 'sub_idx' in field_info:
                        if field_info['sub_idx'] == 1:
                            data.append(value.split()[0])
                        else:
                            data.append(value.split()[1])
                    else:
                        data.append(value)

            logging.debug(f'data{data}')
            return data
        except Exception as e:
            logging.debug(f'Error on line {sys.exc_info()[-1].tb_lineno}')
            return []


def keyword_value_search(needle,haystack, word_space):
    '''
        Finding required string in whole invoice(ocrdata)
        Parameters : needle - String to be found
                     haystack - ocrdata
        Output     : Top, Bottom, Left and matched String in ocrdata
    '''
    try:
        length = len(needle.split())
        matched_needles = []
        #pass#print('needle',needle)
        for i,hay in enumerate(haystack):
            match = ''
            match_ocr = []
            # hay['word'] = clean_word(hay['word'])
            # needle.split()[0] = clean_word(needle.split()[0])
            first_word_match_score = SequenceMatcher(None, clean_word(hay['word']), clean_word(needle.split()[0])).ratio()
            match_threshold = 0.70
            # if hay['word'].lower() == needle.split()[0]:
            #     pass#print('hey word',hay['word'].lower())
            # #pass#print(hay['word'].lower(),needle.split()[0])
            if(first_word_match_score>match_threshold):

                match += hay['word'].lower()
                match_ocr.append(hay)
                # #pass#print('debug footer')
                # #pass#print(hay['word'],needle.split()[0],first_word_match_score)
                try:
                    for j in range(i+1,i+length):
                        match += ' '+haystack[j]['word'].lower()
                        match_ocr.append(haystack[j])
                except Exception as e:
                    logging.exception(f'{e}')
                    # logger.error(e)
                #pass#print('match:',match)
                #pass#print('needele',needle)
                score = SequenceMatcher(None,clean_word(needle),clean_word(match)).ratio()
                matched_needles.append([match_ocr,score])
        # print('matched needles',matched_needles)
        if length > 1:
            matched = sorted(matched_needles,key = lambda x: (x[1],-x[0][0]['top']))[-1]

        else:
            matched = matched_needles[0]
        # print('matched',matched)
        if matched[1] > 0.6:
            footer_string = ' '.join(word['word'] for word in matched[0])
            footer_top = min(matched[0],key = lambda x : x['top'])['top']
            footer_bottom = max(matched[0],key = lambda x : x['bottom'])['bottom']
            footer_left = min(matched[0],key = lambda x : x['left'])['left']
            footer_right = max(matched[0],key = lambda x : x['right'])['right']
        else:
            footer_top = footer_bottom = footer_left = footer_right = -1
            footer_string = ''
            logging.debug(f'cant find footer{e}')

        invoice_right = max([hay['right'] for hay in haystack])

        # lines = return_lines(haystack)
        value_line = ocr_data_local(haystack, footer_top, footer_right, invoice_right, footer_bottom)

        value = ''
        logging.debug(f'value_line{value_line}')
        # word_space = get_word_space(haystack)
        logging.debug(f'word space {word_space}')

        if(len(value_line)):
            value = value_line[0]['word']
        i = 0
        while(i < len(value_line)-1 and (value_line[i+1]['left'] - value_line[i]['right']) < word_space):
            logging.debug(f"v{ value_line[i+1]['word']}")
            value += value_line[i+1]['word']
            i += 1
        value = value.strip()
        data = {'keyword':needle, 'value':value}
        logging.debug(data)
    except Exception as e:
        logging.exception(f'Error on line {sys.exc_info()[-1].tb_lineno}, {type(e).__name__},{e}')
        footer_top = footer_bottom = footer_left = footer_right = -1
        footer_string = ''
        logging.debug('cant find footer',e)
        data = []
    return data

def field_in_one_column(ocr_data, field_info, extracted_data_maintable, horizontal_lines, vertical_lines, header_bottom, main_table_bottom, word_space):
    '''
        function for searching and mapping specific fields which the table
        contains
        algorithm:
            same as field in header just the search would be in column instead
            of the header

        Args:
            ocr_data(list): list of ocr data of the page
            field(list): key and value of of the field in a list
            extracted_data_maintable(list): extracted table by table predict

        Returns:
            list: list of json of respective extracted values for the field
    '''
    try:
        data = []
        idx = field_info['idx']
        key_word = field_info['key_word']

        T = header_bottom
        L = vertical_lines[idx-1][0][0]
        R = vertical_lines[idx][0][0]
        B = main_table_bottom
        # print(T,L,R,B)
        # print(ocr_data)
        ocr_data_ = ocr_data_local(ocr_data, T, L, R, B)

        # print('ocr_data local ', ocr_data)
        data = keyword_value_search(key_word, ocr_data_, word_space)
        # print('data', data)
        return data
    except Exception as e:
        logging.exception(f'Error on line {sys.exc_info()[-1].tb_lineno}, {type(e).__name__}, {e}')
        return []

def keyword_value_search_mc(needle,haystack):
    '''
        Finding required string in whole invoice(ocrdata)
        Parameters : needle - String to be found
                     haystack - ocrdata
        Output     : Top, Bottom, Left and matched String in ocrdata
    '''
    try:
        length = len(needle.split())
        matched_needles = []
        #pass#print('needle',needle)
        for i,hay in enumerate(haystack):
            match = ''
            match_ocr = []
            # hay['word'] = clean_word(hay['word'])
            # needle.split()[0] = clean_word(needle.split()[0])
            first_word_match_score = SequenceMatcher(None, clean_word(hay['word']), clean_word(needle.split()[0])).ratio()
            match_threshold = 0.70
            # if hay['word'].lower() == needle.split()[0]:
            #     pass#print('hey word',hay['word'].lower())
            # #pass#print(hay['word'].lower(),needle.split()[0])
            if(first_word_match_score>match_threshold):

                match += hay['word'].lower()
                match_ocr.append(hay)
                # #pass#print('debug footer')
                # #pass#print(hay['word'],needle.split()[0],first_word_match_score)
                try:
                    for j in range(i+1,i+length):
                        match += ' '+haystack[j]['word'].lower()
                        match_ocr.append(haystack[j])
                except Exception as e:
                    logging.debug(f'{e}')
                    # logger.error(e)
                #pass#print('match:',match)
                #pass#print('needele',needle)
                score = SequenceMatcher(None,clean_word(needle),clean_word(match)).ratio()
                matched_needles.append([match_ocr,score])
        # print('matched needles',matched_needles)
        if length > 1:
            matched = sorted(matched_needles,key = lambda x: (x[1],-x[0][0]['top']))[-1]

        else:
            matched = matched_needles[0]
        # print('matched',matched)
        if matched[1] > 0.6:
            footer_string = ' '.join(word['word'] for word in matched[0])
            footer_top = min(matched[0],key = lambda x : x['top'])['top']
            footer_bottom = max(matched[0],key = lambda x : x['bottom'])['bottom']
            footer_left = min(matched[0],key = lambda x : x['left'])['left']
            footer_right = max(matched[0],key = lambda x : x['right'])['right']
        else:
            footer_top = footer_bottom = footer_left = footer_right = -1
            footer_string = ''
            logging.debug(f'cant find footer{e}')

        invoice_right = max([hay['right'] for hay in haystack])

        # lines = return_lines(haystack)
        value_line = ocr_data_local(haystack, footer_top, footer_right, invoice_right, footer_bottom)

        value = ''
        logging.debug(f'value_line{value_line}')

        if(len(value_line)):
            value = value_line[0]['word']
        i = 0
        while(i < len(value_line)-1):
            logging.debug(f"v{value_line[i+1]['word']}")
            value += '' + value_line[i+1]['word']
            i += 1
        value = value.strip()
        data = {'keyword':needle, 'value':value}
        logging.debug(f'{data}')
    except Exception as e:
        logging.exception(f'Error on line {sys.exc_info()[-1].tb_lineno}, {type(e).__name__}, {e}')
        footer_top = footer_bottom = footer_left = footer_right = -1
        footer_string = ''
        logging.debug(f'cant find footer{e}')
        data = []
    return data

def field_in_multiple_columns(ocr_data, field_info, extracted_data_maintable, horizontal_lines, vertical_lines, header_bottom, main_table_bottom):
    '''
        function for searching and mapping specific fields which the table
        contains
        algorithm:
            same as field in one column just the search would be all the table
            body and value would be all the horiontal row covering it
            and it will be mappend according to headers

        Args:
            ocr_data(list): list of ocr data of the page
            field(list): key and value of of the field in a list
            extracted_data_maintable(list): extracted table by table predict

        Returns:
            list: list of json of respective extracted values for the field
    '''
    try:
        data = []
        key_word = field_info['key_word']
        T = header_bottom
        L = vertical_lines[0][0][0]
        R = vertical_lines[-1][0][0]
        B = main_table_bottom
        ocr_data = ocr_data_local(ocr_data, T, L, R, B)

        data = keyword_value_search_mc(key_word, ocr_data)
        return data
    except Exception as e:
        logging.exception(f'Error on line {sys.exc_info()[-1].tb_lineno}, {type(e).__name__}, {e}')



def multiple_fields_in_multiple_columns(ocr_data, field_info, extracted_data_maintable, horizontal_lines, vertical_lines, header_bottom, main_table_bottom, word_space):
    '''
        function for searching and mapping specific fields which the table
        contains
        algorithm:
            same as field in header but multiple values will be there
            mostly one value in each line item

        Args:
            ocr_data(list): list of ocr data of the page
            field(list): key and value of of the field in a list
            extracted_data_maintable(list): extracted table by table predict

        Returns:
            list: list of json of respective extracted values for the field
    '''
    # data = []
    # idx = field[1]['idx']
    # data = multi_value_search(extracted_data_maintable, idx)
    # return data
    try:
        data = []
        idx = field_info['idx']
        key_word = field_info['key_word']
        logging.debug(f'len of hori lines {len(horizontal_lines)}')
        for i in range(len(horizontal_lines)-1):
            logging.debug(f'hori{horizontal_lines[i][0][1]}')
            logging.debug(f'header bottom{header_bottom}')
            if(horizontal_lines[i][0][1] >= header_bottom):
                T = horizontal_lines[i][0][1]
                L = vertical_lines[idx-1][0][0]
                R = vertical_lines[idx][0][0]
                B = horizontal_lines[i+1][0][1]
                ocr_data_ = ocr_data_local(ocr_data, T, L, R, B)
                # print('ocr_data local ', ocr_data)
                data.append(keyword_value_search(key_word, ocr_data_, word_space))
        logging.debug(f'data{data}')
        return data
    except Exception as e:
        logging.exception(f'Error on line {sys.exc_info()[-1].tb_lineno}, {type(e).__name__}, {e}')


def get_field_list(field_json_data):
    field_list = []
    for k,v in field_json_data.items():
        if k.startswith('v') and v['field']:
            temp_json = {
                'key_word': v['label'],
                'type': v['field_type'],
                'idx' : int(k[1:])
            }
            field_list.append(temp_json)
    return field_list

def field_mapping(ocr_data, extracted_data_maintable, field_json_data, horizontal_lines, vertical_lines, header_bottom, main_table_bottom, ocr_img_copy):
    '''
        function for searching and mapping specific fields which the table
        contains

        Args:
            ocr_data(list): list of ocr data of the page
            extracted_data_maintable(list): extracted table by table predict
            field_json_data(json): json data for fields trained in tables

        Returns:
            list: list of json of respective extracted values for each field
    '''
    try:
        # field_list = field_json_data['field_list']
        field_list = get_field_list(field_json_data)
        # field_list = [{'key_word':'HSN/SAC',
        #                 'type':'f_kh_vc',
        #                 'idx':2,
        #                 },
        #                 {'key_word':'Description',
        #                 'type':'f_kh_vc',
        #                 'idx':3,
        #                 'sub_idx': 1
        #                 },
        #                 {'key_word':'Qty.',
        #                 'type':'f_kh_vc',
        #                 'idx':5
        #                 },
        #                 {'key_word':'Rate',
        #                 'type':'f_kh_vc',
        #                 'idx':6
        #                 },
        #                 {'key_word':'Rate',
        #                 'type':'f_kh_vc',
        #                 'idx':7
        #                 }
        #             ]

        logging.debug(f'field list{field_list}')
        field_extracted_list = {}


        word_space = get_word_space(ocr_data)
        for field_info in field_list:

            field_type = field_info['type']

            if field_type == "kh_vh":
                logging.debug('f_kh_vh')
                # field_extracted_list.append(field_in_header_value_header(ocr_data,
                                                        # field,
                                                        # extracted_data_maintable)
                                                        # )
            elif field_type == "kh_vc":
                logging.debug('in f kh vc')
                key = extracted_data_maintable[0][field_info['idx']-1][0][9:-4]
                logging.debug(f'key{key}')
                value = field_header_key_column_value(ocr_data,
                                                        field_info,
                                                        extracted_data_maintable,
                                                        horizontal_lines,
                                                        vertical_lines,
                                                        header_bottom,
                                                        main_table_bottom,
                                                        word_space,
                                                        ocr_img_copy)
                logging.debug(f'value{value}')
                field_extracted_list[key] = value[0]
            elif field_type == "koc_vc":
                logging.debug('in f_oc')
                # field_extracted_list.append(field_in_one_column(ocr_data,
                #                                         field_info,
                #                                         extracted_data_maintable,
                #                                         horizontal_lines,
                #                                         vertical_lines,
                #                                         header_bottom,
                #                                         main_table_bottom,
                #                                         word_space))
            elif field_type == "kmc_vc":
                logging.debug('in f_mc')
                # field_extracted_list.append(field_in_multiple_columns(ocr_data,
                #                                         field_info,
                #                                         extracted_data_maintable,
                #                                         horizontal_lines,
                #                                         vertical_lines,
                #                                         header_bottom,
                #                                         main_table_bottom))
            elif field_type == "f_omr_mv":
                logging.debug('in fm mc')
                # field_extracted_list.append(multiple_fields_in_multiple_columns(ocr_data,
                #                                         field_info,
                #                                         extracted_data_maintable,
                #                                         horizontal_lines,
                #                                         vertical_lines,
                #                                         header_bottom,
                #                                         main_table_bottom,
                #                                         word_space))
    except Exception as e:
        logging.exception(f'Error on line {sys.exc_info()[-1].tb_lineno}, {type(e).__name__}, {e}')
    logging.debug(f'field_extracted_list{field_extracted_list}')
    return field_extracted_list
