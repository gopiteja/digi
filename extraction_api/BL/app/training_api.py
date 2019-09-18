import argparse
import json
import math
import re

from dateutil.parser import parse
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS
from nltk import edit_distance

try:
    from app.db_utils import DB
    from app.producer import produce
    from app.extracto_utils import *
except:
    from db_utils import DB
    from producer import produce
    from extracto_utils import *

from app import app

def merge_highlights(box_list,page_number=0):
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

        return {'height': max_height, 'width': total_width, 'y': top, 'x': min_left, 'right':max_right, 'word': word.strip(), 'page':page_number}
    else:
        return {}

def get_word_highlight(val_word, ocr_data):
    return_word = {}
    for page_no, page in enumerate(ocr_data):
        for word in page:
            if word['word'] == val_word:
                return_word = word
                return_word['page'] = page_no
    return return_word

def get_highlights(value, ocr_data):
    word_highlights = []
    print(value)
    for val_word in value.split():
        word_highlights.append(get_word_highlight(val_word, ocr_data))
    return merge_highlights(word_highlights)

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


def standardize_date(all_data, input_format=[r'%d-%m-%Y', r'%d.%m.%Y', r'%d/%m/%Y'], standard_format=r'%Y-%m-%d'):
    # Find date related fields and change the format of the value to a standard one
    print(f'Changing date formats in extracted fields...')
    #date_formats = [r'%d-%m-%Y', r'%d.%m.%Y', r'%d/%m/%Y']

    standard_format = r'%Y-%m-%d'
    for field_name, field_value in all_data.items():
        if 'date' in field_name.lower().split():
            if field_value is not None or field_value:
                new_field_value = field_value
                raw_field_value = field_value.replace('suspicious', '')
                try:
                    parsed_date = parse(raw_field_value, fuzzy=True, dayfirst=True)
                except ValueError:
                    print(f'Error occured while parsing date field `{field_name}`:`{field_value}`.')
                    parsed_date = None

                if parsed_date is not None:
                    if 'suspicious' in field_value:
                        new_field_value = 'suspicious' + parsed_date.strftime(standard_format)
                    else:
                        new_field_value = parsed_date.strftime(standard_format)
                all_data[field_name] = new_field_value
        if "gstin" in field_name.lower():
            if field_value is not None or field_value:
                pattern = r"\d{2}[a-zA-Z]{5}\d{4}[a-zA-Z]{1}(?:\d{1}|[a-zA-Z]{1})[a-zA-Z]{1}\w"
                try:
                    valid_gstin = re.findall(pattern,field_value.replace('suspicious',''))[-1]
                    all_data[field_name] = valid_gstin
                except:
                    all_data[field_name] = field_value + 'suspicious'
        if field_name.lower() in ['invoice base amount', 'invoice total']:
            try:
                all_data[field_name] = float(''.join(re.findall(r'[0-9\.]', field_value.replace('suspicious',''))))
            except:
                all_data[field_name] = field_value + 'suspicious'
    return all_data
    
def correct_keyword(ocr_data, keyword_sentence, scope,value):
    # Correct the last word of the keyword sentence
    # If ocr has "Invoice No:.", and keyword was trained as "Invoice No", this will make sure ocr word is saved as keyword
    
    junk=''
    val_to_check=''
    if value:
        val_to_check=value.split()[0]

    kwList=keyword_sentence.split()
    box_t = scope['y']
    box_r = scope['x'] + scope['width']
    box_b = scope['y'] + scope['height']
    box_l = scope['x']
    
    if len(kwList)>1:
        for val in ocr_data:
            if val['top']>=box_t and val['bottom']<=box_b and val['right']<=box_r and val['left']>=box_l:
                if kwList[-1] in val['word'] and val['word'] not in kwList:
                    if edit_distance(val['word'],kwList[-1]) <=3:
                        kwList[-1]=val['word']
                    elif val_to_check:
                        if val_to_check in val['word']:
                            junk=kwList[-1]
                            kwList.pop(-1)
                    else:
                        kwList.pop(-1)

    return ' '.join(kwList),junk

def keyword_extract(ocr_data, keyword, scope):
    '''
    Get closest keyword to the trained keyword.
    '''
    regex = re.compile(r'[@_!#$%^&*()<>?/\|}{~:;]')
    keyList=keyword.split()
    keyLength=len(keyList)
    keyCords=[]
    counter=0

    # Search OCR for the key pattern
    for i, data in enumerate(ocr_data):
        ocr_length=len(ocr_data)
        check=False

        if(data['word']==keyList[0] or (regex.search(data['word'])!=None and keyList[0] in data['word'] )):
            if(keyLength>1):
                for x in range(0,keyLength):
                    if (i+x) >= ocr_length:
                        check=False
                        break
                    else:
                        if(ocr_data[i+x]['word']==keyList[x] or (regex.search(ocr_data[i+x]['word'])!=None and  keyList[x] in ocr_data[i+x]['word'])):
                            check=True
                        else:
                            check=False
                            break
            else:
                check=True

        tempCords=[{}]*1
        if(check):
            counter=counter+1
            top=10000
            bottom=0
            # Left is of the first word
            if(data['word']==keyList[0] or (regex.search(data['word'])!=None and keyList[0] in  data['word'] )):
                tempCords[0]['left']=data['left']
                for x in range(0,keyLength):
                    # Right is of the last word
                    if(x==(keyLength-1)):
                        tempCords[0]['right']=ocr_data[i+x]['right']

                    # If multi word key
                    if(keyLength>1):
                        if(ocr_data[i+x]['word']==keyList[x]):
                            if(ocr_data[i+x]['top']<top):
                                top=ocr_data[i+x]['top']
                            if(ocr_data[i+x]['bottom']>bottom):
                                bottom=ocr_data[i+x]['bottom']
                    else:
                        top=data['top']
                        bottom=data['bottom']

                tempCords[0]['top']=top
                tempCords[0]['bottom']=bottom
                keyCords.append(tempCords[0])

    if(counter>0):
        keysDict=keyCords
        proceed=True
        #First try to find keyword inside the trained box
        pi=[]
        for i,values in enumerate(keysDict):
            trained_box=[scope['x'],scope['x']+scope['width'],scope['y']+scope['height'],scope['y']]
            keysDict_box=[keysDict[i]['left'],keysDict[i]['right'],keysDict[i]['bottom'],keysDict[i]['top']]
            pi.append(percentage_inside(trained_box,keysDict_box))
        maxpi=max(pi)
        if maxpi > 0.9:
            minIndex=pi.index(maxpi)
            proceed=False

        if proceed:
            print("Finding nearest to trained..")
            #Find keyword nearest to trained box
            inpX=(scope['y']+scope['y']+scope['height'])/2
            inpY=(scope['x']+scope['x']+scope['width'])/2
            DistList=[]
            pi=[]
            for i,values in enumerate(keysDict):
                    # Store all keywords,distances in a Dict
                    # Get midpoint of the input
                    midheight=((keysDict[i]['top']+keysDict[i]['bottom'])/2)
                    midwidth=((keysDict[i]['left']+keysDict[i]['right'])/2)
                    x=abs(midheight-inpX)
                    y=abs(midwidth-inpY)
                    dist=math.sqrt((x*x)+(y*y))
                    DistList.append(round(dist, 2))
            closestKey=min(DistList)
            minIndex=DistList.index(closestKey)

        key_top=keyCords[minIndex]['top']
        key_bottom=keyCords[minIndex]['bottom']
        key_left=keyCords[minIndex]['left']
        key_right=keyCords[minIndex]['right']

        return  {'height': key_bottom-key_top, 'width': key_right-key_left, 'y': key_top, 'x': key_left }

    else:
        print('keyword not found in OCR')
        return {}

def get_trained_info(ocr_data, fields, resize_factor):
    # Database configuration
    db_config = {
        'host': 'extraction_db',
        'user': 'root',
        'password': 'root',
        'port': '3306'
    }
    db = DB('extraction', **db_config)
    # db = DB('extraction') # Development purpose
    
    # ! Getting OCR data from train route
    # get ocr from db
    # ocr_query = "SELECT ocr_data FROM process_queue WHERE file_name= %s "
    # params=[file_name]
    # res= execute_query(ocr_query, ANALYST_DATABASE,params)
    # ocr_data = json.loads(res[0][0])


    # ! Checking if template exists in train route
    # q=("SELECT count(template_name) from trained_info where template_name =%s ")
    # params = [template_name]
    # res=db.execute_query(q,params = params)[0][0]
    # if res>0:
    #     print("Template name is duplicate")
    #     return jsonify({'flag': 'error', 'result': 'Template name already exists in database'})

    field_data = {}
    extracted_data = {}
    junk = ''
    for _, field in fields.items():
        field_type = field['field']
        keyword = field['keyword']
        field_value = field['value']
        field_box = field['coordinates']
        page_no = field_box['page']
        extracted_data[field_type] = field_value
        try:
            validation = field_box['page']
        except Exception as e:
            print('Validation error',e)
            validation = ''
        
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

        # Box's Top, Right, Bottom, Left
        box_t = field_box['y']
        box_r = field_box['x'] + field_box['width']
        box_b = field_box['y'] + field_box['height']
        box_l = field_box['x']

        # If keyword is there then save the
        # relative distance from keyword to box's edges
        # else save the box coordinates directly
        if keyword:
            regex = re.compile(r'[@_!#$%^&*()<>?/\|}{~:;]')
            alphareg = re.compile(r'[a-zA-Z]')
            keyList=keyword.split()
            if len(keyList)>1:
                if regex.search(keyList[-1])!=None and alphareg.search(keyList[-1])==None:
                    #if the last word of keyword sentence containes only special characters
                    junk=keyList[-1]
                    del keyList[-1]
            keyword=' '.join(keyList)     
            # Get keyword's box coordinates
            keyword_box = keyword_extract(ocr_data[int(page_no)], keyword, scope)
            if not keyword_box:
                keyword_2, junk = correct_keyword(ocr_data[int(page_no)], keyword, scope ,field_value)
                keyword_box = keyword_extract(ocr_data[int(page_no)], keyword_2, scope)
                if keyword_box:
                    field['keyword']=keyword=keyword_2
            if keyword_box:
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

        ''' Storing additional information of value wrt keyword'''
        value_meta = needle_in_a_haystack(field_value,ocrDataLocal(field_box['y'],field_box['x'],field_box['x']+field_box['width'],field_box['y']+field_box['height'],ocr_data[int(page_no)]))

        field_value_coords = {
                                'top':field_box['y'],
                                'bottom':field_box['y']+field_box['height'],
                                'left':value_meta['left'],
                                'right':field_box['x']+field_box['width']
                            }

        key_val_meta = {}

        if keyword_box_new:
            keyword_box_new = {
                            'top':keyword_box_new['top'],
                            'left':keyword_box_new['left'],
                            'right':keyword_box_new['right'],
                            'bottom':keyword_box_new['bottom']
                        }

            key_val_meta = get_rel_info(field_value_coords,keyword_box_new)
        key_val_meta = {**field_value_coords, **key_val_meta}

        # Add to final data
        field_data[field_type] = {
            'keyword': keyword,
            'top': top,
            'right': right,
            'bottom': bottom,
            'left': left,
            'scope': scope,
            'page': page_no,
            'junk' : junk,
            'key_val_meta':key_val_meta,
            'validation':validation
        }

    return field_data

@app.route('/force_template', methods=['POST', 'GET'])
def force_template():
    ui_data = request.json

    case_id = ui_data['case_id']
    template_name = ui_data['template_name']
  
    # Database configuration
    db_config = {
        'host': 'queue_db',
        'user': 'root',
        'password': 'root',
        'port': '3306'
    }
    queue_db = DB('queues', **db_config)

    # Insert a new record for each file of the cluster with template name set and cluster removed
    print(f'Extracting for case ID `{case_id}`')

    fields = {}
    fields['template_name'] = template_name
    fields['cluster'] = None

    queue_db.update('process_queue', update=fields, where={'case_id': case_id})

    # Send case ID to extraction topic
    produce('extract', {'case_id': case_id})

    return jsonify({'flag': True, 'message': 'Successfully extracted!'})


@app.route('/train', methods=['POST', 'GET'])
def train():
    ui_data = request.json
    print('uidata',ui_data)
    # ! Requires `template_name`, `extracted_data`, `case_id`, `trained_data`, `resize_factor`
    # ! `header_ocr`, `footer_ocr`, `address_ocr`

    # Database configuration
    db_config = {
        'host': 'queue_db',
        'user': 'root',
        'password': 'root',
        'port': '3306'
    }
    queue_db = DB('queues', **db_config)
    # queue_db = DB('queues')

    trained_db_config = {
        'host': 'template_db',
        'user': 'root',
        'password': 'root',
        'port': '3306'
    }
    trained_db = DB('template_db', **trained_db_config)
    # trained_db = DB('template_db')

    table_db_config = {
        'host': 'table_db',
        'user': 'root',
        'password': 'root',
        'port': '3306'
    }
    table_db = DB('table_db', **table_db_config)
    # trained_db = DB('template_db')

    extarction_db_config = {
        'host': 'extraction_db',
        'user': 'root',
        'password': 'root',
        'port': '3306'
    }
    extraction_db = DB('extraction', **extarction_db_config)
    # extraction_db = DB('extraction')

    template_name = ui_data['template_name']
    fields = ui_data['fields']
    case_id = ui_data['case_id']
    try:
        validation = ui_data['validation']
    except Exception as e:
        print('Exception in Validation. Probably UI is not sending validation')
        validation = ''
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
    address_ocr = [ui_data['template']['address_ocr']['value']] # A list because ... idk ask Ashish
    # * Check if template name already exists
    trained_info = trained_db.get_all('trained_info')
    trained_template_names = list(trained_info.template_name)
    if template_name.lower() in [t.lower() for t in trained_template_names]:
        message = f'Template name `{template_name}` already exist.'
        print(message)
        return jsonify({'flag': False, 'message': message})
    try:
        table_trained_info = ui_data['table'][0]['table_data']['trained_data']
        table_method = ui_data['table'][0]['method']
        
        table_data_column_values = {
            'template_name': template_name,
            'method': table_method,
            'table_data': json.dumps(table_trained_info) #bytes(table_trained_info, 'utf-8').decode('utf-8', 'ignore')
        }
        table_db.insert_dict(table_data_column_values, 'table_info')
    except:
        table_trained_info = {}  
    
    process_queue_df = queue_db.get_all('process_queue')
    latest_process_queue = queue_db.get_latest(process_queue_df, 'case_id', 'created_date')
    latest_case = latest_process_queue.loc[latest_process_queue['case_id'] == case_id]


    # * Calculate relative positions and stuff
    ocr_data = json.loads(list(latest_case.ocr_data)[0])
    trained_data = get_trained_info(ocr_data, fields, resize_factor)

    # * Add trained information & template name into `trained_info` table
    trained_data_column_values = {
        'template_name': template_name,
        'field_data': json.dumps(trained_data),
        'header_ocr': header_ocr,
        'footer_ocr': footer_ocr,
        'address_ocr': json.dumps(address_ocr)
    }
    trained_db.insert_dict(trained_data_column_values, 'trained_info')

    # TODO: Add table data into a table training microservice database

    # * Save extracted data to ocr table
    # Create a dictionary with field names as key and extracted value as value of the key
    extracted_column_values = {'case_id': case_id}
    columns_in_ocr = extraction_db.get_column_names('ocr')
    extracted_column_values['highlight'] = {}
    for _, field in fields.items():
        column_name = field['field']
        value = field['value']

        # Check if column name is there in OCR table
        if column_name not in columns_in_ocr:
            print(f' - `{column_name}` does not exist in `ocr` table. Skipping field.')
            continue

        #Add highlight to the dict
        #extracted_column_values['highlight'] = highlight
        highlight = get_highlights(value, ocr_data)
        extracted_column_values['highlight'][column_name] = highlight

        extracted_column_values[column_name] = value

    # highlight = {}
    standardized_data = standardize_date(extracted_column_values)
    standardized_data['highlight'] = json.dumps(extracted_column_values['highlight'])
    standardized_data['Table'] = trained_table
    extraction_db.insert_dict(standardized_data, 'ocr')


    # * Insert new record process queue with template name
    latest_case_dict = latest_case.to_dict(orient='records')[0]
    latest_case_dict['template_name'] = template_name
    cluster = latest_case_dict['cluster']
    latest_case_dict['cluster'] = None
    latest_case_dict['queue'] = 'Verify'
    latest_case_dict.pop('created_date', None)
    latest_case_dict.pop('last_updated', None)

    queue_db.insert_dict(latest_case_dict, 'process_queue')
    ocr_data = json.loads(list(latest_case.ocr_data)[0])

    # Send case ID to extraction topic
    produce('business_rules', {'stage': 'One', 'case_id': case_id, 'send_to_topic': 'sap'})
    
    # # To Enable only training
    # return jsonify({'flag': True, 'message': 'Training completed!'})


    # * Run extraction on the same cluster
    cluster_files_df = latest_process_queue.loc[latest_process_queue['cluster'] == cluster]
    cluster_case_data = cluster_files_df.to_dict(orient='records')
    for case_data in cluster_case_data:
        if case_data['case_id'] == case_id:
            print(f'Already extracted for case ID `{case_id}`')
            continue
        
        cluster_case_id = case_data['case_id']

        # Update the record for each file of the cluster with template name set and cluster removed
        print(f'Extracting for case ID `{cluster_case_id}`')

        fields['template_name'] = template_name
        fields['cluster'] = None

        queue_db.update('process_queue', update=fields, where={'case_id': cluster_case_id})

        # Send case ID to extraction topic
        produce('extract', {'case_id': cluster_case_id})

    return jsonify({'flag': True, 'message': 'Training completed!'})

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-p', '--port', type=int, help='Port Number', default=5019)
    parser.add_argument('--host', type=str, help='Host', default='0.0.0.0')

    args = parser.parse_args()

    host = args.host
    port = args.port

    app.run(host=host, port=port, debug=False)