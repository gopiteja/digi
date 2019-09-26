import xml.etree.ElementTree as ET
import json
import pymysql
import copy
import sys
from difflib import SequenceMatcher

from nltk import edit_distance
from difflib import SequenceMatcher

try:
    from app.ace_logger import Logging
    from app.cluster_headers import cluster_headers_chooser
    from app.table_predict import complex_table_prediction
    with open('app/parameters.json') as f:
        parameters = json.loads(f.read())
except:
    from ace_logger import Logging
    from cluster_headers import cluster_headers_chooser
    from table_predict import complex_table_prediction
    with open('parameters.json') as f:
        parameters = json.loads(f.read())



ANALYST_DATABASE = parameters['database_name']
DEFAULT_IMGPATH = parameters['ui_folder'] + 'assets/images/invoices/'
# xml_folder_path = parameters['abbyy_xml']
xml_folder_path = './table_xml/ocr_xml_'

logging = Logging().getLogger('ace')

def execute_query(sql,database = ANALYST_DATABASE):
    data = None
    conn = pymysql.connect(host = '127.0.0.1', user = 'root', password = '', db = database)
    try:
        a = conn.cursor()
        a.execute(sql)
        data = a.fetchall()
        conn.commit()
    except Exception as e:
        logging.debug("exception")
        logging.exception(e)
        # logger.error('Sql Error!!! \n check query\n {}'.format(sql))
        conn.rollback()
    conn.close()
    return data


def ocr_data_local(T, L, R, B, ocrData):
    '''
        Args:
            Boundaries of Scope
        Returns:
            Returns that part of ocrdata which is confined within given boundaries
    '''

    ocrDataLocal = []
    for data in ocrData:
        if  (data['left'] + int(0.25*data['width'])  >= L
            and data['right'] - int(0.25*data['width']) <= R
            and data['top'] + int(0.5*data['height']) >= T and data['bottom'] - int(0.5*data['height']) <= B ):
            ocrDataLocal.append(data)
    return ocrDataLocal

def resize_ocr_data(ocr_data, rf):
    for data in ocr_data:
        data['left'] = int(data['left']*rf)
        data['right'] = int(data['right']*rf)
        data['bottom'] = int(data['bottom']*rf)
        data['top'] = int(data['top']*rf)
    return ocr_data


def header_helper(json_data):
    result = []
    for k,v in json_data.items():
        for key,value in v.items():
            if(key == 'label' and k.startswith('v')):
                result.append((k,value))

    header_list_dict = {}
    split_cols={}
    prev_key = result[0][0]
    for each in result:
        if(prev_key in each[0] and prev_key in header_list_dict):
            split_cols[prev_key].append(each[1])
            header_list_dict[prev_key] += ' '+each[1]
        else:
            split_cols[each[0]] = [each[1]]
            header_list_dict[each[0]] = each[1]
            prev_key = each[0]
    col_children_no = {}
    for k,v in split_cols.items():
        col_children = {}
        if(len(v)>1):
            for i in range(1,len(v)):
                if(v[0] in col_children):
                    col_children[v[0]].append(v[i])
                else:
                    col_children[v[0]] = [v[i]]
        if col_children:
            col_children_no[k] = col_children

    return header_list_dict,col_children_no


def get_header_list(json_data):
    header_list_dict,col_children_no = header_helper(json_data)
    header_list=[v for k,v in header_list_dict.items()]
    return header_list,col_children_no


def extract_table(path_xml):
    tree = ET.fromstring(path_xml)
    all_tables = []

    for ele in tree.iter():
        if ele.tag == '{http://www.abbyy.com/FineReader_xml/FineReader10-schema-v1.xml}block':
            if (ele.attrib['blockType'] == 'Table'):
                rows = []
                for el in ele:
                    if el.tag == '{http://www.abbyy.com/FineReader_xml/FineReader10-schema-v1.xml}row':
                         rows.append(el)

                all_row_words = []
                for row in rows:
                    row_words = []
                    for cell in row:
                        word = ""
                        for text in cell:
                            for par in text:
                                for line in par:
                                    for formatting in line:
                                        for charParams in formatting:
                                            word += charParams.text

                        rowSpan = int(cell.attrib['rowSpan']) if 'rowSpan' in cell.attrib else 1
                        colSpan = int(cell.attrib['colSpan']) if 'colSpan' in cell.attrib else 1
                        row_words.append((word, rowSpan, colSpan))
                    all_row_words.append(row_words)
                all_tables.append(all_row_words)
    return all_tables


def club_tables(table1, table2):
    for row in table2:
        table1.append(row)
    return table1


def remove_rows(table, del_rows):
    new_table = [row for i,row in enumerate(table) if i not in del_rows]
    return new_table


def required_cols(table, req_cols):
    new_table = []
    for row in table:
        new_row = []
        for i,data in enumerate(row):
            if(i in req_cols):
                new_row.append(data)
        new_table.append(new_row)
    return new_table


'''
Algorithm:
0. train and save the results in database normally
call table predicion abbyy instead of the normal complex table prediction
1. match the fist row for all the tables
if more than 90 percent of the words are in the header list
take that table

2. club the tables accordingly
3. remove headers while clubbing
4. output the results

'''


def merge_overflowing_tables(table1, table2):

    for i, row in enumerate(table1):
        table1[i].extend(table2[i])
    return table1


def club_all_tables(tables_to_club):
    table_results = tables_to_club[0]
    for i in range(1,len(tables_to_club)):
        tmp_table = tables_to_club[i]
        table_results = merge_overflowing_tables(table_results, tmp_table)
    return table_results


def match_text(text, header_list):
    text = text.strip()
    header_list = ' '.join(header_list)
    text = text.replace(' ','')
    header_list = header_list.replace(' ','')
    if text in header_list:
        return True
    else:
        return False

def val_equal(header_word, row_words_frequency):
    for key, val in row_words_frequency.items():
         if SequenceMatcher(None, key, header_word).ratio() > .4:
             return True, key
    return False, ''

def check_header(table_, header_words_list):
    header_words_frequency = {}
    for word in header_words_list:
        if word in header_words_frequency:
            header_words_frequency[word] += 1
        else:
            header_words_frequency[word] = 1
    try:
        for i, header_row in enumerate(table_):
            row_words = []
            for box in header_row:
                text = box[0]

                box_words = text.split()
                row_words.extend(box_words)

            row_words_frequency = {}
            for word in row_words:
                if word in row_words_frequency:
                    row_words_frequency[word] += 1
                else:
                    row_words_frequency[word] = 1
            # print("header_words_frequency", header_words_frequency)
            # print("row_words_frequency", row_words_frequency)
            # print(, "")
            x = 0
            y = 0
            for word, freq in header_words_frequency.items():
                y += freq
                # print(word)
                comp, row_word = val_equal(word, row_words_frequency)
                if comp:
                # if word in row_words_frequency:
                    x += min(row_words_frequency[row_word], freq)

            ratio = x/y
            # print("x", x)
            # print("y", y)
            # print(ratio)
            if(ratio >= 0.8):
                return True, i
    except Exception as e:
        # print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno), type(e).__name__, e)
        logging.exception(f'exception in check header{e}')
        return False, -1
    return False, -1



def check_header_predict(table_, header_list_):
    table = table_.copy()
    header_list = header_list_.copy()
    header_list = [(''.join(head.split())).lower() for head in header_list]

    # print('i : ',i)
    # print('header_list', header_list)
    # print('table row :', table[0])
    for idx, header_row in enumerate(table):
        count = 0
        for box in header_row:
            text = box[0]
            for head in header_list:
                if SequenceMatcher(None,(''.join(text.split())).lower(),head).ratio() > 0.7:
                    count += 1
        ratio = count/len(header_row)
        # print('ratio:',ratio)
        if(ratio >= 0.7):
            return True, idx

    return False, -1

def check_header_new_predict(table_, header_list_):
    # print('header listssss', header_list_)
    # print('table', table_)
    table = table_.copy()
    header_list = header_list_.copy()
    header_list = [(''.join(head.split())).lower() for head in header_list]
    count = 0
    # print('i : ',i)
    # print('header_list', header_list)
    # print('table row :', table[0])
    for i, header_row in enumerate(table):
        for box in header_row:
            text = box[0]
            for head in header_list:
                if SequenceMatcher(None,(''.join(text.split())).lower(),head).ratio() > 0.7:
                    count += 1
        ratio = count/len(header_row)
        # print('ratio:',ratio)
        if(ratio >= 0.7):
            return True

    return False

def check_found_list(header_found_list):
    for val in header_found_list:
        if not val:
            return True
    return False


def new_header_list(header_list, header_found_list):
    return  [ header for i, header in enumerate(header_list) if not header_found_list[i]]


def mark(header_marker_index, table, header_found_list):
    for i in range(header_marker_index, min(len(table[0]), len(header_found_list)) ):
        header_found_list[i] = True
    return header_found_list


def remove_cols(table, del_cols):
    new_table = []
    for row in table:
        new_row = []
        for i, box in enumerate(row):
            if(i not in del_cols):
                new_row.append(box)
        new_table.append(new_row)
    return new_table


''' clubbing of similar header tables with removal of headers (work in progress)'''

def highest_header_spans(tables):

    return header_spans


def correct_RC_span(tables):
    header_span = highest_header_spans(tables)

    for table_id, table in enumerate(tables):
        for row in table:
            for i, span in enumerate(header_span):
                if(table_id is not header_span[1]):
                    table
                else:
                    new_row.append()
    return tables


def flatten_tables(tables, header_idx_list):
    new_tables = []
    # tables = correct_RC_span(tables)
    new_tables.append(tables[0])
    for i in range(1,len(tables)):
        table = tables[i]
        new_tables[0].extend(table[header_idx_list[i]:])
    return new_tables


def remove_headers(tables, header_idx_list):
    new_tables = []
    new_tables.append(tables[0])
    for i in range(1, len(tables)):
        new_tables.append(tables[i][header_idx_list[i]:])
    return new_tables


def tuples_to_list(tables):
    for i in range(len(tables)):
        for j in range(len(tables[i])):
            for k in range(len(tables[i][j])):
                # print(tables[i][j][k])
                tables[i][j][k] = list(tables[i][j][k])
    return tables


def hard_code_span(tables):
    for row in tables[0]:
        row[2][2] = 2
    return tables


def remove_unwanted_rows(tables):
    new_tables = []
    tables = tables[0]
    for row in tables:
        if(len(row)>2):
            new_tables.append(row)
    return [new_tables]


def remove_unwanted_rows_f2(tables):
    new_tables = []

    for table in tables:
        new_table = []
        for row in table:
            if(len(row)>2):
                new_table.append(row)
        new_tables.append(new_table)

    return new_tables

# def cluster_headers(header_words, header_top, header_left, header_right, header_bottom):
#     '''
#         The function process the headers data and try to cluster headers to
#             predict header lines
#         algorithm:
#         1. calculate avg word space
#         2. equalize the tops
#         3. crop the image of headers and get open cv header_lines
#         4. add top and bottom to horizontal lines
#         5. add cv horizontals to horizontal lines, there will be maximum one so
#             validation should be easy but still left and right will be hard
#         6. final algo verticals :
#             - take cluster algo lines( assumption: trusting word space )
#                 checking for false positives()
#             - validate with cv lines
#             - if cv line is there also - (there means between those exact same words)
#                 that means its a yes for that line
#             -
#
#         Args:
#             result (json): data from UI
#         Returns:
#             list: list of header split lines to be shown to the user
#     '''
#
#     # word_space_sum =
#     # avg_space = word_space_sum / len(headers_list)
#     hors = []
#     vers = []
#
#     hors.append([[header_left,header_top],[header_right,header_top]])
#     hors.append([[header_left,header_bottom],[header_right,header_bottom]])
#     # header_lines = {
#     #     'hors' : hors,
#     #     'vers' : vers
#     # }
#     return hors, vers


def check_multipage(json_data):

    multi_page_table = False
    for k,v in json_data.items():
        if(k == 'h0' and v['repeatable'] == 'true'):
            multi_page_table = True
    return multi_page_table


def get_pageno(json_data):
    page_no = 0
    try:
        for k,v in json_data.items():
            if k.startswith('h'):
                page_no = int(v['page'])
                break
    except:
        logging.exception('page no not found')
        page_no = 0

    return page_no


def get_ocr_data(ocr_data_list,json_data,header_list):
    try:
        scored_ocr_list = []
        for pg_no,ocr_data in enumerate(ocr_data_list):
            ocr_data_string = json.dumps(ocr_data)
            score = 0
            for each_header in header_list:
                if(each_header in ocr_data_string):
                    score += 1
            scored_ocr_list.append([score,ocr_data,pg_no])

        multi_page_table = check_multipage(json_data)
        page_no = get_pageno(json_data)
        if multi_page_table:
            ocrData = ocr_data_list
        else:
            ocrData = [ocr_data_list[page_no]]
    except Exception as e:
        # logging.exception(f'Error on line {}'.format(sys.exc_info()[-1].tb_lineno), type(e).__name__, e)
        logging.exception('error')
    return ocrData,multi_page_table,page_no


def table_training_abbyy(ocr_data_list, img_width, trained_data, xml_string, file_name=None, template_name = None, json_data = None):
    '''
        The function returns the predicted table using abby xml

        Args:
            ocr_data_list (list): ocr data from for each page
            file_name (str): name of the file
            template_name (str): name of the template
            json_data (json): json data saved in database for the table
        Returns:
            json: object returning the table results
    '''

    # table_final_data = []
    # return {"table": table_final_data}
    # if json_data:
    #     json_data_list = [json_data[0]]
    # else:
    #     get_json_data = "SELECT table_data from table_db \
    #                     where template_name ='{}'".format(template_name)
    #     json_data_list = execute_query(get_json_data)
    #     json_data_list = [json.loads(data[0]) for data in json_data_list]

    logging.debug(f'len osf ocr data{len(ocr_data_list)}')
    try:
        logging.debug(f'json data{json_data}')
        if json_data is None:
            json_data = trained_data
        # print('json data', json_data)
        json_data_list = [json_data]
        table_final_data = []

        for table_num in range(len(json_data_list)):
            json_data = json_data_list[table_num]

            # try:
            #     json_data = json_data[0]
            # except:
            #     pass
            rf = img_width/670


            # ocr_data,multi_page_table,page_no = get_ocr_data(ocr_data_list,json_data,header_list)

            ocr_data = ocr_data_list[table_num]
            ocr_data_copy = copy.deepcopy(ocr_data)
            ocr_data = resize_ocr_data(ocr_data_copy, rf)

            # file_name = file_name.replace(' ','')
            # path_xml = xml_folder_path +file_name+'.xml'
            # header_list,col_children_no = get_header_list(json_data)
            coordinates_header = json_data['coordinates'][0]
            # pdb.set_trace()
            T_h = int(coordinates_header['y'])
            L_h = int(coordinates_header['x'])
            R_h = int((coordinates_header['x'] + coordinates_header['width']))
            B_h = int((coordinates_header['y'] + coordinates_header['height']))

            # print("l ,r , t, b", L_h, R_h, T_h, B_h)
            # print("ocr_data", ocr_data)
            header_ocr = ocr_data_local(T_h, L_h, R_h, B_h, ocr_data)
            header_words_list = []
            # print("header_ocr",header_ocr)
            for data in header_ocr:
                header_words_list.append(data['word'])


            coordinates_footer = json_data['coordinates'][1]
            T = int(coordinates_footer['y'])
            # tables = remove_unwanted_rows_f2(tables)

            L = int(coordinates_footer['x'])
            R = int((coordinates_footer['x'] + coordinates_footer['width']))
            B = int((coordinates_footer['y'] + coordinates_footer['height']))
            footer_ocr = ocr_data_local(T, L, R, B, ocr_data)
            footer_words_list = []
            for data in footer_ocr:
                footer_words_list.append(data['word'])

            hors = []
            hors.append([[L_h,T_h],[R_h,T_h]])
            hors.append([[L_h,B_h],[R_h,B_h]])
            hors.append([[L,T],[R,T]])
            hors.append([[L,B],[R,B]])

            vers = []
            # print('ocr_data 2', ocr_data)
            #
            # print('ocr_data 3', ocr_data)
            # print(T_h, L_h, R_h, T)
            vers_ = cluster_headers_chooser(ocr_data, T_h, L_h, R_h, T )
            for ver in vers_:
                vers.append([[ver,T_h],[ver,B_h]])

            table_results = []

            header_idx_list = []
            footer_idx_list = []
            all_tables = extract_table(xml_string)
            logging.debug(f'all tables{all_tables}')
            # print("all tables",all_tables)
            # print("header_word_list", header_words_list)
            for i, table in enumerate(all_tables):
                verify_flag, header_idx = check_header(table, header_words_list)
                # print("verify", verify_flag)
                if(verify_flag):
                    verify_flag, footer_idx = check_header(table, footer_words_list)
                    table_results.append(table[header_idx:footer_idx])
                    header_idx_list.append(header_idx+2)
                    footer_idx_list.append(footer_idx+2)

            tables = table_results
            # tables = [all_tables[0]]

            '''method 1 .. merging all tables '''
            # # tables = remove_headers(tables)
            # tables = tuples_to_list(tables)
            # tables = hard_code_span(tables)
            # tables = flatten_tables(tables, header_idx_list)
            # tables = remove_unwanted_rows(tables)

            '''method 2 showing tables differently '''
            # tables = tuples_to_list(tables)
            # tables = remove_headers(tables, header_idx_list)
            # tables = remove_unwanted_rows_f2(tables)


            # header_list = ['hshs', 'sdakda', 'asdsa', 'asdad', 'aknfnf']
            # print('tables',tables)
            header_list = []
            if len(tables):
                header_list = [ box[0] for box in tables[0][0]]

            # print('header list ', header_list)


            '''checking if fields data present and collecting fields '''
            fields_extracted_list = []
            # print('trained_data', trained_data)
            if trained_data is not None:
                ocr_data_list = [ocr_data]
                template_name = ''
                file_name = file_name
                json_data = trained_data,
                table_no = '1'
                table_predict_output = complex_table_prediction(ocr_data_list, file_name, json_data)
                # print('table_predict_output', table_predict_output)
                fields_extracted_list = table_predict_output['table'][0][1]['fields_extracted_list']

        table_final_data = [[tables,header_list, { 'hors':hors, 'vers':vers, 'fields_extracted_list': fields_extracted_list}]]
        table_final_data = json.loads(json.dumps(table_final_data).replace("'",''))

        # print('table final data', table_final_data)
        return {"table": table_final_data}
    except Exception as e:
        # print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno), type(e).__name__, e)
        # hors = []
        # vers = []
        hors = []
        try:
            hors.append([[L_h,T_h],[R_h,T_h]])
            hors.append([[L_h,B_h],[R_h,B_h]])
            hors.append([[L,T],[R,T]])
            hors.append([[L,B],[R,B]])
        except:
            pass

        vers = []
        try:
            vers_ = cluster_headers_chooser(ocr_data, T_h, L_h, R_h, B_h )
            for ver in vers_:
                vers.append([[ver,T_h],[ver,B_h]])
        except:
            pass

        fields_extracted_list = []
        tables = [[[]]]
        header_list = ['','']
        table_final_data = [[tables,header_list, { 'hors':hors, 'vers':vers, 'fields_extracted_list': fields_extracted_list}]]
        table_final_data = json.loads(json.dumps(table_final_data).replace("'",''))

        # print('table final data', table_final_data)
        return {"table": table_final_data}



def table_prediction_abbyy(ocr_data_list, img_width, trained_data, file_name=None, template_name=None, json_data=None, xml_string=None):
    '''
        The function returns the predicted table using abby xml

        Args:
            ocr_data_list (list): ocr data from for each page
            file_name (str): name of the file
            template_name (str): name of the template
            json_data (json): json data saved in database for the table
        Returns:
            json: object returning the table results
    '''

    # print('len osf ocr data',len(ocr_data_list))
    try:
        # print('json data', json_data)
        # if json_data is None:
        #     json_data = trained_data
        json_data_list = [json_data]
        # print('json data', json_data)
        table_final_data = []

        for table_num in range(len(json_data_list)):
            json_data = json_data_list[table_num]
            # print('json datasss',json_data)
            rf = img_width/670
            # ocr_data,multi_page_table,page_no = get_ocr_data(ocr_data_list,json_data,header_list)

            ocr_data = ocr_data_list[table_num]
            ocr_data_copy = copy.deepcopy(ocr_data)
            ocr_data = resize_ocr_data(ocr_data_copy, rf)


            all_tables = extract_table(xml_string)
            # print('all tables',all_tables)

            '''PREDICTION  '''
            header_list,col_children_no = get_header_list(json_data)
            table_results = []

            header_idx_list = []
            for i, table in enumerate(all_tables):
                if(check_header_new_predict(table, header_list) ):
                    verify_flag, header_idx = check_header_predict(table, header_list)
                    table_results.append(table)
                    # print('header idx', header_idx)
                    header_idx_list.append(header_idx+2)

            # print('length of table results', len(table_results))
            # print(table_results)
            tables = table_results


            hors = []
            vers = []
            # print('tables',tables)
            header_list = []
            if len(tables):
                header_list = [ box[0] for box in tables[0][0]]


            '''checking if fields data present and collecting fields '''
            fields_extracted_list = []
            # print('trained_data', trained_data)
            if trained_data is not None:
                ocr_data_list = [ocr_data]
                template_name = ''
                file_name = file_name
                table_no = '1'
                table_predict_output = complex_table_prediction(ocr_data_list, file_name, trained_data)
                # print('table_predict_output', table_predict_output)
                fields_extracted_list = table_predict_output['table'][0][1]['fields_extracted_list']

        table_final_data = [[tables,header_list, { 'hors':hors, 'vers':vers, 'fields_extracted_list': fields_extracted_list}]]
        table_final_data = json.loads(json.dumps(table_final_data).replace("'",''))

        # print('table final data', table_final_data)
        return {"table": table_final_data}
    except Exception as e:
        # print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno), type(e).__name__, e)
        # hors = []
        # vers = []
        hors = []
        hors.append([[L_h,T_h],[R_h,T_h]])
        hors.append([[L_h,B_h],[R_h,B_h]])
        hors.append([[L,T],[R,T]])
        hors.append([[L,B],[R,B]])

        vers = []
        try:
            vers_ = cluster_headers_chooser(ocr_data, T_h, L_h, R_h, B_h )
            for ver in vers_:
                vers.append([[ver,T_h],[ver,B_h]])
        except:
            pass

        fields_extracted_list = []
        tables = [[[]]]
        header_list = ['','']
        table_final_data = [[tables,header_list, { 'hors':hors, 'vers':vers, 'fields_extracted_list': fields_extracted_list}]]
        table_final_data = json.loads(json.dumps(table_final_data).replace("'",''))

        # print('table final data', table_final_data)
        return {"table": table_final_data}
