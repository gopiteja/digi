# import comtypes.client as cc
import cv2
import imutils
# import pythoncom
import traceback
import os
import json
from pdf2image import convert_from_path
import base64
from wand.image import Image
from wand.drawing import Drawing
from wand.color import Color
import numpy as np
from io import BytesIO
import io
# import extract
from app.electro_magnet import *
import matplotlib.pyplot as plt
import math
import re
import copy
from nltk import edit_distance
import requests
parent_dir = os.getcwd()
from py_zipkin.zipkin import zipkin_span,ZipkinAttrs, create_http_headers_for_new_span
from app.ace_logger import Logging
with open('/var/www/extraction_api/app/parameters.json') as f:
    parameters = json.loads(f.read())
logging = Logging()
# with open(parent_dir+'/configs/parameters.json') as f:
#     parameters = json.loads(f.read())

from flask import Flask, request, jsonify
from flask_cors import CORS

import requests




def checkbox_selector(file_name, checkbox_data, ocr_data, cordextract, output, output_):
    print('checkbox_data')
    print(checkbox_data)
    print('corddd',cordextract)
    ocr_length = len(ocr_data)
    pages = None
    if file_name.lower().endswith('.pdf'):
        print('Converting PDF to images... ')
        filename_with_path = '/var/www/table_api/app/invoice_files/' + file_name
        pages = convert_from_path(filename_with_path, dpi=500)
    # iterate each checkbox field
    for check_field, checkboxes in checkbox_data.items():
        # iterate each checkbox of a checkbox field
        checked_values = []
        for cbox in checkboxes:
            scope = cbox['scope']
            keyword = cbox['keyword']
            num_of_words = len(keyword.split())
            page_no = int(cbox['page'])
            validation = cbox['validation']
            print('validation is ', validation)

            # If keyword is there then get the nearest keyword to the trained
            # keyword and use relative position of that keyword to get the value
            if keyword:
                key_page = int(page_no)
                if (key_page > (ocr_length - 1)):  # if new invoice does not have the trained page number
                    for i in range(0, ocr_length):
                        val, valCords = keyword_selector_with_cords(ocr_data, keyword, scope, cbox, i, file_name,
                                                                    check_field, validation=validation, pages=pages)
                        if val:
                            break
                else:
                    # first check page in which field trained
                    val, valCords = keyword_selector_with_cords(ocr_data, keyword, scope, cbox, key_page, file_name, check_field, validation=validation, pages=pages)
                    if not val:  # if value not found in trained page, loop through other pages except trained page
                        for i in range(0, ocr_length):
                            if i != key_page:
                                val, valCords = keyword_selector_with_cords(ocr_data, keyword, scope, cbox, i, file_name, check_field, validation=validation, pages=pages)
                                if val:
                                    break
                if val:
                    print("VALUE FOUND:", val)
                else:
                    try:
                        print('OCR DATA IS {} LENGTH IS {} TYPE is {} PAGE NO is {}'.format(ocr_data,len(ocr_data), type(ocr_data), page_no))
                        val, valCords = closest_field_extract(ocr_data[page_no], keyword, scope, cbox, file_name, check_field, validation=validation, pages=pages)
                    except Exception as e:
                        print('In extract checkbox CLOSEST KEY {} not found in the OCR exception is {} type is {}'.format(keyword, e, type(page_no)))
            else:
                # No keyword
                field_value = []

                box_t = scope['y']
                box_r = scope['x'] + scope['width']
                box_b = scope['y'] + scope['height']
                box_l = scope['x']

                box = [box_l, box_r, box_b, box_t]

                sorted_data = (sorted(ocr_data[page_no], key=lambda i: (i['top'], i['left'])))
                for ocr_word in sorted_data:
                    word_t = ocr_word['top']
                    word_r = ocr_word['left'] + ocr_word['width']
                    word_b = ocr_word['bottom']
                    word_l = ocr_word['left']

                    word_box = [word_l, word_r, word_b, word_t]

                    if percentage_inside(box, word_box) > parameters['overlap_threshold']:
                        if ocr_word['confidence'] < parameters['ocr_confidence']:
                            field_value.append('suspicious' + ocr_word['word'])
                            # field_value.append(ocr_word['word'])
                        else:
                            field_value.append(ocr_word['word'])
                val = ' '.join(field_value)
            if val == 'Yes':
                checked_values.append(keyword)
                if check_field not in cordextract:
                    cordextract[check_field] = valCords
                else:
                    try:
                        cordextract[check_field].append(valCords[0])
                    except:
                        cordextract[check_field] = valCords
        val = ', '.join(checked_values)
        try:
            output[check_field] = val.strip()
        except:
            output[check_field] = val
        output_[check_field] = val
    logging.info(f'final output from checkbox: {output_}')    
    # return output, cordextract, output_
    return cordextract,output_


def keyword_selector_with_cords(ocr_data, keyword, inp, field_data, page, filename, field_name, validation=None, pages=None):
    print('field name is ', field_name)
    print('field data is ', field_data)
    rel_top = field_data['top']
    rel_bottom = field_data['bottom']
    rel_left = field_data['left']
    rel_right = field_data['right']

    keyList = keyword.split()
    print('Keyword list is', keyList)
    # print("\nKeyList:\n%s" % keyList)
    keyLength = len(keyList)
    page_no = page
    
    keyCords = []
    counter = 0
    if (keyLength > 0):
        # Search OCR for the key pattern
        for i, data in enumerate(ocr_data[page_no]):
            ocr_length = len(ocr_data[page_no])
            regex = re.compile('[@_!#$%^&*()<>?/\|}{~:]')
            check = False
            if (data['word'] == keyList[0] or (regex.search(data['word']) != None and keyList[0] in data['word'])):
                print('WORD FOUND IS ',data['word'])
                if (keyLength > 1):
                    for x in range(0, keyLength):
                        if i + x >= ocr_length:
                            check = False
                            break
                        else:
                            if (ocr_data[page_no][i + x]['word'] == keyList[x] or (
                                    regex.search(ocr_data[page_no][i + x]['word']) != None and keyList[x] in
                                    ocr_data[page_no][i + x]['word'])):
                                check = True
                            else:
                                check = False
                                break
                else:
                    check = True

            tempCords = [{}] * 1
            if (check):
                # print("-----")
                # print(data['word'])
                counter = counter + 1
                top = 1000
                bottom = 0
                # Left is of the first word
                if (data['word'] == keyList[0] or (regex.search(data['word']) != None and keyList[0] in data['word'])):
                    print('WORD 2 FOUND IS ',data['word'])
                    tempCords[0]['left'] = data['left']
                    for x in range(0, keyLength):
                        # Right is of the last word
                        if (x == (keyLength - 1)):
                            tempCords[0]['right'] = ocr_data[page_no][i + x]['right']

                        # If multi word key
                        if (keyLength > 1):
                            if (ocr_data[page_no][i + x]['word'] == keyList[x]):
                                # print("%s" % keyList[x])
                                if (ocr_data[page_no][i + x]['top'] < top):
                                    top = ocr_data[page_no][i + x]['top']
                                if (ocr_data[page_no][i + x]['bottom'] > bottom):
                                    bottom = ocr_data[page_no][i + x]['bottom']
                        else:
                            top = data['top']
                            bottom = data['bottom']

                    tempCords[0]['top'] = top
                    tempCords[0]['bottom'] = bottom
                    # print(tempCords)
                    print('tempCords for {} is {}'.format(data['word'], tempCords[0]))
                    keyCords.append(tempCords[0])

        # print("\nNo of occurences of %s:\n%s" %(keyword,counter))
    if (counter > 0):
        keysDict = keyCords
        inpX = (inp['y'] + inp['y'] + inp['height']) / 2
        inpY = (inp['x'] + inp['x'] + inp['width']) / 2
        DistList = []
        for i, values in enumerate(keysDict):
            # Store all keywords,distances in a Dict
            # Get midpoint of the input
            midheight = ((keysDict[i]['top'] + keysDict[i]['bottom']) / 2)
            midwidth = ((keysDict[i]['left'] + keysDict[i]['right']) / 2)
            x = abs(midheight - inpX)
            y = abs(midwidth - inpY)
            dist = math.sqrt((x * x) + (y * y))
            DistList.append(round(dist, 2))
        # print("\nKey distance dictionary:\n%s" % DistList)
        closestKey = min(DistList)
        minIndex = DistList.index(closestKey)

        # determine the box and search for the value
        box_top = keyCords[minIndex]['top'] - rel_top
        box_bottom = keyCords[minIndex]['bottom'] + rel_bottom
        box_left = keyCords[minIndex]['left'] - rel_left
        box_right = keyCords[minIndex]['right'] + rel_right
        box = [box_left, box_right, box_bottom, box_top]
        print('box is ', box)
        print('keycords is ', keyCords)
        word = []
        valueCords = []
        print('filename is ', filename)
        if validation:
            print('entered in checkbox')
            if 'checkbox body' in validation.lower() or 'checkbox body' in validation.lower():
                state, cboxCords = extract_checkbox_cords(filename, box, keyCords[minIndex], page_no, field_name, keyword, pdf_pages=pages)
                if cboxCords:
                    valueCords.append({'word': keyword, 'left': cboxCords[0], 'right': cboxCords[2],
                                       'width': cboxCords[2] - cboxCords[0], 'height': cboxCords[3] - cboxCords[1],
                                       'top': cboxCords[1], 'page': page_no, 'x': cboxCords[0], 'y': cboxCords[1]})
                    return state, valueCords
                else:
                    return state, valueCords.append({})

        for data in ocr_data[page_no]:
            word_box = [data['left'], data['right'], data['bottom'], data['top']]
            if (percentage_inside(box, word_box) > parameters['overlap_threshold']
                    and data['word'] not in keyList):
                if data['confidence'] < parameters['ocr_confidence']:
                    word.append('suspicious' + data['word'])
                    # word.append(data['word'])
                    valueCords.append({'word': data['word'], 'left': word_box[0], 'right': word_box[1], 'width': word_box[1] - word_box[0],
                                       'height': word_box[2] - word_box[3], 'top': word_box[3], 'page': page_no})
                else:
                    word.append(data['word'])
                    valueCords.append({'word': data['word'], 'left': word_box[0], 'right': word_box[1], 'width': word_box[1] - word_box[0],
                                       'height': word_box[2] - word_box[3], 'top': word_box[3], 'page': page_no})
        return ' '.join(word), valueCords

    else:
        print('Exact Keyword not found in OCR')
        return None, []


def closest_field_extract(ocr_og, keyword_sentence, scope, field_data, filename, field_name, validation=None, pages=None):
    print('FIELD DATA In CLOSEST is ', field_data)
    size_increment = 100#Constant value of expanding of scope field box
    sort=True
    right_offset=0
    page_data = copy.deepcopy(ocr_og)

    original_field_tokens = keyword_sentence.lower().split()#All original keywords with special chars
    field_tokens=[]
    for index,val in enumerate(original_field_tokens):
        if not re.match(r'^[_\W]+$', val):
            field_tokens.append(val)# add only non special characters to field kw list
            right_offset+=7 #because special character removed, keyword's right should not reduce
    length = len(field_tokens)
    # print("\nNo. of keywords to be found: ",length)

    # print("\nFinal field tokens: ",field_tokens)
    # print("\nOriginal field tokens :",original_field_tokens)
    scope_page_data = []

    if scope:
        box_t = scope['y'] - size_increment
        box_r = (scope['x'] + scope['width']) + size_increment
        box_b = (scope['y'] + scope['height']) + size_increment
        box_l = scope['x'] - size_increment

        box = [box_l, box_r, box_b, box_t]
        print("\nExpanded scope box",box)
        for data in page_data:
            word_t = data['top']
            word_r = data['left'] + data['width']
            word_b = data['bottom']
            word_l = data['left']

            word_box = [word_l, word_r, word_b, word_t]
            if percentage_inside(box, word_box) > parameters['overlap_threshold']:
                scope_page_data.append(data)


    if sort:
        data = sorted(scope_page_data, key = lambda i: (i['top']))
        # print("\nData:",data)

    for i in range(len(data)-1):
        if abs(data[i]['top'] - data[i+1]['top']) < 5:
            data[i+1]['top'] = data[i]['top']

    if sort:
        sorted_data = (sorted(data, key = lambda i: (i['top'], i['left'])))
    else:
        sorted_data = data


    with_special=copy.deepcopy(scope_page_data)#store original ocr words in scope box

    for i in scope_page_data:
        if not re.match(r'^[_\W]+$', i["word"]):
            i["word"]=re.sub('[^ a-zA-Z0-9]', '', i["word"])#remove special character from scope box
    # print("\nSorted data:",sorted_data)
    # print("\nWith_special",with_special)


    og_words=[]#to store all closest keywords found,in original format,with special characters
    for line_no, line in enumerate(sorted_data):
        flag = True
        index = 0
        while(flag == True and index < length):

            kw=field_tokens[index].lower()
            ocr_word=sorted_data[line_no + index]['word'].lower()
            ed=edit_distance(kw,ocr_word)
            print('ocr word is {} and kw is{} and ed is{}'.format(ocr_word,kw, ed))
            if not ( ( ed<=1 and 1<len(ocr_word)<=4)  or ( ed <=2 and 10>=len(ocr_word)>4 )  or ( ed <=3 and len(ocr_word)>10  )  )   :
                flag = False
                print("---")
            else:
                og_words.append(with_special[line_no + index]['word'].lower())
            index += 1
        if flag == True and index == length:
            print(og_words,"++++")
            # keyCords = [with_special[line_no + index]['left'], with_special[line_no + index]['lef']]
            # print("\nKeywords coords to merge:\n",sorted_data[line_no: line_no + length])
            result=merge_fields(sorted_data[line_no: line_no + length])#get combined coordinates
            print("\nMerged kw box\n",result)
            result = result[0]
            result["left"]=result["x"]
            result["top"]=result["y"]
            result["bottom"]=result["y"]+result["height"]

            rel_top = field_data['top']
            rel_bottom = field_data['bottom']
            rel_left = field_data['left']
            rel_right = field_data['right']

            box_top=result['top']-rel_top
            box_bottom=result['bottom']+rel_bottom
            box_left=result['left']-rel_left
            box_right=result['right']+rel_right+right_offset #offset is imp

            box = [box_left, box_right, box_bottom, box_top]
            # print("\nBOX TO EXTRACT",box)
            word=[]
            valueCords = []
            page_no = int(field_data['page'])
            if 'checkbox' in validation.lower() or 'check box' in validation.lower():
                print('Heere in checkbox box is ', box)
                state, cboxCords = extract_checkbox_cords(filename, box, result, page_no, field_name, keyword_sentence, pdf_pages=pages)
                valueCords.append({'word': keyword_sentence, 'left': cboxCords[0], 'right': cboxCords[2],
                                   'width': cboxCords[2] - cboxCords[0], 'height': cboxCords[3] - cboxCords[1],
                                   'top': cboxCords[1], 'page': page_no, 'x': cboxCords[0], 'y': cboxCords[1]})
                return state, valueCords

def percentage_inside(box, word):
    '''
    Get how much part of the word is inside the box
    '''
    box_l,box_r,box_b,box_t = box
    word_l,word_r,word_b,word_t = word
    area_of_word = (word_r - word_l) * (word_b - word_t)
    area_of_intersection = get_area_intersection(box, word)
    try:
        return area_of_intersection/area_of_word
    except:
        return 0

def get_area_intersection(box, word):
    box_l, box_r, box_b, box_t = box
    word_l, word_r, word_b, word_t = word

    dx = min(word_r, box_r) - max(word_l, box_l)
    dy = min(word_b, box_b) - max(word_t, box_t)

    if (dx >= 0) and (dy >= 0):
        return dx*dy
    return 0


def merge_fields(box_list, page_number=0):
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
            max_height = max(box['height'], max_height)
            min_left = min(box['left'], min_left)
            max_right = max(box['right'], max_right)
            total_width += box['width']
            word += ' ' + box['word']
            top = box['top']

        return [{'height': max_height, 'width': total_width, 'y': top, 'x': min_left, 'right':max_right, 'word': word.strip(), 'page':page_number}]
    else:
        return [{}]

def copy_file(blob,filename,url="http://192.168.0.138:5087/copy_file"):
    files_data = {'file':(filename,blob, 'application/octet-stream')}
    requests.post(url, files=files_data) 
    return 'Sucessfully Copied'
    
def extract_checkbox_cords(filename, selected_box, keycords, page_no, field_name, keyword, pdf_pages=None):
    try:
        print('keycords are ',keycords)
        print('box is ',selected_box)
        # filename = parameters['ui_folder']+'assets/images/invoices/'+filename
        try:
            host = '172.31.45.112'
            port = 5002
            route = 'get_blob_data'
            print(f'Hitting URL: http://{host}:{port}/{route}')
            print(f'Sending Data: "case_id":{filename}')
            response = requests.post(f'http://{host}:{port}/{route}', json= {'case_id':filename})
            print("step 1")
            blob_resp = response.json()
            print("step 2")
            blob = blob_resp['data'].replace('data:application/pdf;base64,','').strip()

            try:
                print('In try loop')
                pdf_blob = base64.b64decode(blob)
                all_pages = Image(blob=pdf_blob)   # PDF will have several pages.
                single_image = all_pages.sequence[int(page_no)] 
                image = Image(single_image)
                image.format = 'png'
                image.alpha_channel = False
                width = image.width
                rf = width/670
                h = image.height
                res_h = int(h/rf)
                image.resize(670,res_h,filter = 'gaussian')

                print('Obtained Image')
            except Exception as e:
                print("Error reading Image", e)


        except Exception as e:
            print(e)
        # print(pdf_pages)
        # new_filename = '/app/invoices/{}'.format(fname)
        # copy_file(fname,url = "http://192.168.0.138:5087/copy_file")


        # try:
        #     image = cv2.imdecode(img_buffer, cv2.IMREAD_UNCHANGED)       
        # except Exception as e:
        #     print('Not able to read image', e)
            
        # dimensions of image for resize factor
        # h, width, channels = image.shape
        # calculate resize factor
        print('h ',h,'width ',width)
        rf = 1        # Need to define
        # resize cropped box and keyword co-ordinates
        keycords = {key: int(value*rf) for key, value in keycords.items() if not type(value) == str}  # keycords = {'left', 'right', 'top', 'bottom'}
        print('key cords are ', keycords)
        # take the cropped region
        print('box is',selected_box[0],selected_box[3],keycords['left'], selected_box[2])

        image.crop(selected_box[0],selected_box[3],keycords['left'], selected_box[2])  # left,top,right,bottom
        
        new_image = image.clone()
        print(new_image.height)
        print(new_image.width)
        img_buffer=np.asarray(bytearray(new_image.make_blob()), dtype=np.uint8)
        image = cv2.imdecode(img_buffer, cv2.IMREAD_GRAYSCALE)
        scaleX = 0.6
        scaleY = 0.6
        print('before resize',image.shape)
        scaleUp = cv2.resize(image, None, fx= scaleX*10, fy= scaleY*10, interpolation= cv2.INTER_LINEAR)
        print('scale up ',scaleUp.shape)
        final_copy = scaleUp.copy()
        kernel = np.array([[-1,-1,-1], [-1,9,-1], [-1,-1,-1]])
        im = cv2.filter2D(scaleUp, -1, kernel)
        print('shape is ',im.shape)
        
        
        thresh = cv2.adaptiveThreshold(im, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY, 31, 2)
        kernel = np.ones((3,3),np.uint8)
        img_erosion = cv2.erode(thresh, kernel, iterations=1) 
        img_dilation = cv2.dilate(img_erosion, kernel, iterations=1) 
        cnts,hierarchy = cv2.findContours(img_dilation.copy(), cv2.RETR_TREE,cv2.CHAIN_APPROX_SIMPLE)

        new_copy = img_dilation.copy()
        backtorgb = cv2.cvtColor(scaleUp,cv2.COLOR_GRAY2RGB)
        print(len(cnts))
        cont_ares = []
        for c in cnts:
            # approximate the contour
            accuracy = 0.03*cv2.arcLength(c, True)
            approx = cv2.approxPolyDP(c, accuracy, True)
            print(len(approx))
            print(cv2.contourArea(approx))
            if cv2.contourArea(approx) < 6000 and cv2.contourArea(approx) > 2000:
                cont_ares.append((len(approx),cv2.contourArea(approx),approx))
        cont_ares.sort(key = lambda x:x[1],reverse = True)
        cont_ares_max = cont_ares[0]
        max_rect_cord = cont_ares_max[-1]
        print(max_rect_cord)
        max_rec = max_rect_cord.tolist()

        x,y,w,h = cv2.boundingRect(max_rect_cord)
        print(x,y,w,h)
        # print('new shape ',new_image.shape)
        print(y+10,y+h-10,x+10,x+w-10)
        crop_img = final_copy[y+13:y+h-10,x+13:x+w-10]
        print('crop shape',crop_img.shape)

        if crop_img.shape[0] > crop_img.shape[1]:
            final_crop = crop_img.shape[1]
        else:
            final_crop = crop_img.shape[0] 


        buf = io.BytesIO()
        plt.imsave(buf, crop_img, format='png')
        image_data = buf.getvalue()
        
        
        # cropped_image = image.make_blob()
        print("Cropped file successfully")
        # cropped_image = image[crop_box[3]:crop_box[2], crop_box[0]:crop_box[1]]
        # keyword_image = image[keycords['top']:keycords['bottom'], keycords['left']: keycords['right']]

        # highlight_box = [crop_box[3]:crop_box[2], keycords['left']-5: crop_box[1]]
       
        # cbox = [crop_box[0]+15,keycords['left']-5,keycords['bottom'],keycords['top']-10]
        # Java API Call

        copy_file(image_data,filename=filename,url = "http://7e72bbd1.ngrok.io/copy_file")
        print('copied file successfully')
        value_extract_params = {'filename':filename+'.png','left':str(0),'right':str(final_crop),'top':str(1),'bottom':str(final_crop),'checkmark_type':'SQUARE'}
        value_extract_params = json.dumps(value_extract_params)
        host = '192.168.0.142'   # ip address
        port = 8081
        route = 'get_checkmark'
        print(f'Hitting URL: http://{host}:{port}/{route}')
        print(f'Sending Data: {value_extract_params}')
        headers = {'Content-type': 'application/json; charset=utf-8', 'Accept': 'text/json'}
        response = requests.post(f"http://2f91d92e.ngrok.io/get_checkmark?checkbox_param={value_extract_params}", headers=headers)
        # response = requests.post(f'http://{host}:{port}/{route}', data={'checkbox_params':json.dumps(value_extract_params)}, headers=headers)
        # print('response',response.content)
        print(response.text)
        print('response',json.loads(response.text))
        res = json.loads(response.text)
        checkmark_state = res['cmarkstate']
        # import pdb
        # pdb.set_trace()
        # print('response',json.loads(response.text))
        "left top right bottom"
        cbox = [selected_box[0],selected_box[3],selected_box[1],selected_box[2]]   
        if checkmark_state == 'CMCS_NotChecked':
            return 'No', cbox
        if checkmark_state == 'CMCS_Checked':
            return 'Yes', cbox
        if checkmark_state == 'CMCS_Corrected':
            return 'Corrected', cbox
        if checkmark_state == 'CMCS_NotRecognized':
            return 'Not Recognized', cbox
        else:
            return 'None', cbox
    except Exception as e:
        traceback.print_exc()
        return 'not able to process'