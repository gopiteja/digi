from flask import Flask, request, jsonify
from flask_cors import CORS
import argparse
import json
import re
import math
from pprint import pprint
import traceback

try:
    from app.extracto_utils import *
    from app.context_field_utils import get_context_box
    with open('app/parameters.json') as f:
        parameters = json.loads(f.read())
except:
    from extracto_utils import *
    from context_field_utils import get_context_box
    with open('parameters.json') as f:
        parameters = json.loads(f.read())

def extraction_with_keyword(ocr_data,keyword,scope,fte,fte_data,key_page,ocr_length,context = None):
    val = ''
    word_highlights = {}
    if(key_page> (ocr_length-1)):        #if new invoice does not have the trained page number
        print('Looping through all pages')
        for i in range (0,ocr_length):
            if context:
                val,word_highlights=keyword_selector(ocr_data,keyword,scope,fte_data,i,context)
            else:
                val,word_highlights=keyword_selector(ocr_data,keyword,scope,fte_data,i)
            if val:
                break
    else:
        #first check page in which field trained
        if context:
            val,word_highlights=keyword_selector(ocr_data,keyword,scope,fte_data,key_page,context)
        else:
            # print('Checking in page no ',key_page)
            val,word_highlights=keyword_selector(ocr_data,keyword,scope,fte_data,key_page)
       
        if not val: #if value not found in trained page, loop through other pages except trained page
            for i in range (0,ocr_length):
                if i!=key_page:
                    if context:
                        val,word_highlights=keyword_selector(ocr_data,keyword,scope,fte_data,i,context)
                    else:
                        val,word_highlights=keyword_selector(ocr_data,keyword,scope,fte_data,i)
                    if val:
                        break
    if val:
        print('value found for',keyword,'value:',val)
        pass
    else:
        try:
            if context:
                val,word_highlights=keyword_selector(ocr_data,keyword,scope,fte_data,key_page,context)
            else:
                val,word_highlights=keyword_selector(ocr_data,keyword,scope,fte_data,key_page)
        except:
            "Closest not found"
            pass

    if val:
        # print('keyword_selector',val)
        for word in keyword.split():
            if word in val.split()[0]:
                val = val.replace(word, '')
    return val,word_highlights


def value_extract(field_data, ocr_data):

    # case_id = result['case_id']
    # is_field_exception = False
    # pprint(field_data)
    remove_keys = ['header_ocr', 'footer_ocr', 'address_ocr']
    
    # data = request.json
    # field_data = data['field_data']
    [field_data.pop(key, None) for key in remove_keys]
    # ocr_data = data['ocr_data']

    ocr_length = len(ocr_data)
    word_highlights={}
    output = {}
    output_ = {}


    for fte, fte_data in field_data.items():
        if 'value' in fte_data:
            output[fte] = fte_data['value']
        
        if fte == 'Invoice Category':
            output_[fte] = fte_data['keyword']
            output[fte] = fte_data['keyword']

        else:
            scope = fte_data['scope']
            keyword = fte_data['keyword']
            page_no = int(fte_data['page'])
            split_check = fte_data.pop('split_check','')
            validation = fte_data.pop('validation','')
            multi_key_field_info = fte_data.pop('multi_key_field_info',{})
            context_key_field_info = fte_data.pop('context_key_field_info',{})
            # print('multi_key_field_info',multi_key_field_info)
            if fte not in ['header_ocr', 'footer_ocr', 'address_ocr']:
                # If keyword is there then get the nearest keyword to the trained
                # keyword and use relative position of that keyword to get the value
                if keyword:
                    key_page=int(page_no)
                    if context_key_field_info:
                        try:
                            val,word_highlights[fte] = extraction_with_keyword(ocr_data,keyword,scope,fte,fte_data,key_page,ocr_length,context_key_field_info)
                        except Exception as e:
                            val = ''
                            print(traceback.print_exc())
                            print('Error in extracting for field:{} keyword:{} due to {}'.format(fte,keyword,e))
                    elif split_check == 'yes':
                        key_val_meta = fte_data['key_val_meta']
                        try:
                            keyword_meta = needle_in_a_haystack(keyword,ocr_data[page_no],scope)
                            # print('keyword_meta',keyword_meta)

                            '''debugging keyword meta'''
                            # cv2.rectangle(img,(keyword_meta['left'],keyword_meta['top']),(keyword_meta['right'],keyword_meta['bottom']),(0,0,255),2)
                            key_midpoint =  keyword_meta['midpoint']
                            value_midpoint = point_pos(key_midpoint[0],key_midpoint[1],key_val_meta['dist'],key_val_meta['angle'])
                            value_box_padding = 0
                            value_box = {
                                            'top':value_midpoint[1]-int((key_val_meta['bottom']-key_val_meta['top'])/2)-value_box_padding,
                                            'bottom':value_midpoint[1]+int((key_val_meta['bottom']-key_val_meta['top'])/2)+value_box_padding,
                                            'left':value_midpoint[0]-int((key_val_meta['right']-key_val_meta['left'])/2)-value_box_padding,
                                            'right':value_midpoint[0]+int((key_val_meta['right']-key_val_meta['left'])/2)+value_box_padding
                                        }
                            value_ocr = ocrDataLocal(value_box['top'],value_box['left'],value_box['right'],value_box['bottom'],ocr_data[page_no])
                            # print('value_ocr',value_ocr)
                            # print('value_text',' '.join([word['word'] for word in value_ocr]))
                            val = ' '.join([word['word'] for word in value_ocr])
                            word_highlights[fte] = {'word': val, 'x': value_box['left'], 'right': value_box['right'],
                                        'width': value_box['right'] - value_box['left'],
                                        'height': value_box['bottom'] - value_box['top'], 'y': value_box['top'], 'page': page_no}
                        except Exception as e:
                            val = ''
                            print('Error in remove junk',e)
                    else:
                        print('normal Keyword extraction',keyword)
                        val,word_highlights[fte] = extraction_with_keyword(ocr_data,keyword,scope,fte,fte_data,key_page,ocr_length)
                elif not keyword and multi_key_field_info:
                    try:
                        predicted_val = field_extract_with_cell_method(ocr_data[page_no],multi_key_field_info['cell_data'],fte_data)
                        print('multi key predicted val',predicted_val)
                        val = ' '.join([word['word'] for word in predicted_val])
                        word_highlights[fte] = merge_fields(predicted_val, page_no)
                    except Exception as e:
                        print('Failed to predict using multikey method',e)
                        val = ''

                else:
                    # No keyword
                    field_value = []
                    temp_highlight=[]

                    box_t = scope['y']
                    box_r = scope['x'] + scope['width']
                    box_b = scope['y'] + scope['height']
                    box_l = scope['x']

                    box = [box_l, box_r, box_b, box_t]

                    sorted_data = (sorted(ocr_data[page_no], key = lambda i: (i['top'], i['left'])))
                    for ocr_word in sorted_data:
                        word_t = ocr_word['top']
                        word_r = ocr_word['left'] + ocr_word['width']
                        word_b = ocr_word['bottom']
                        word_l = ocr_word['left']

                        word_box = [word_l, word_r, word_b, word_t]

                        if percentage_inside(box, word_box) > parameters['overlap_threshold']:
                            if ocr_word['confidence'] < parameters['ocr_confidence']:
                                field_value.append('suspicious' + ocr_word['word'])
                            else:
                                field_value.append(ocr_word['word'])
                            temp_highlight.append(ocr_word)
                    val = ' '.join(field_value)
                    word_highlights[fte]=merge_fields(temp_highlight, page_number=page_no)

                try:
                    output[fte] = val.strip()
                    if fte == 'Invoice Number' and val:
                        output[fte] = output[fte].replace(" ","")
                except:
                    output[fte] = val
                    if fte == 'Invoice Number' and val:
                        output[fte] = output[fte].replace(" ","")
                output_[fte] = val

    
    
    return_data = {
            'output': output_   
    }
    return return_data

def field_extract(page_data, query,sort=True):
    for page_number,data in enumerate(page_data):
        if sort:
            data = sorted(data, key = lambda i: (i['top']))
        for i in range(len(data)-1):
            if abs(data[i]['top'] - data[i+1]['top']) < 5:
                data[i+1]['top'] = data[i]['top']

        if sort:
            sorted_data = (sorted(data, key = lambda i: (i['top'], i['left'])))
        else:
            sorted_data=data
        field_tokens = query.lower().split()
        length = len(field_tokens)

        for line_no, _ in enumerate(sorted_data[:-length]):
            flag = True
            index = 0
            while(flag == True and index < length):
                if field_tokens[index].lower() not in sorted_data[line_no + index]['word'].lower():
                    flag = False
                index += 1

            if flag == True and index == length:
                return merge_fields(sorted_data[line_no: line_no + length],page_number)

def closest_field_extract(ocr_og, keyword_sentence, scope, field_data):
    highlight={}
    temp_highlight=[]
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
        # print("\nExpanded scope box",box)
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
    else:
        data=scope_page_data

    for i in range(len(data)-1):
        if abs(data[i]['top'] - data[i+1]['top']) < 5:
            data[i+1]['top'] = data[i]['top']

    if sort:
        sorted_data = (sorted(data, key = lambda i: (i['top'], i['left'])))
    else:
        sorted_data = data


    with_special=copy.deepcopy(sorted_data)#store original ocr words in scope box

    for i in scope_page_data:
        if not re.match(r'^[_\W]+$', i["word"]):
            i["word"]=re.sub('[^ a-zA-Z0-9]', '', i["word"])#remove special character from scope box
    # print("\nSorted data:",sorted_data)
    # print("\nWith_special",with_special)


    og_words=[]#to store all closest keywords found,in original format,with special characters
    for line_no, _ in enumerate(sorted_data):
        flag = True
        index = 0
        while(flag == True and index < length):

            kw=field_tokens[index].lower()
            ocr_word=sorted_data[line_no + index]['word'].lower()
            ed=edit_distance(kw,ocr_word)
            if not ( ( ed<=1 and 1<len(ocr_word)<=4)  or ( ed <=2 and 10>=len(ocr_word)>4 )  or ( ed <=3 and len(ocr_word)>10  )  )   :
                flag = False
            else:
                og_words.append(with_special[line_no + index]['word'].lower())
            index += 1
        if flag == True and index == length:
            # print("\nKeywords coords to merge:\n",sorted_data[line_no: line_no + length])
            result=merge_fields(sorted_data[line_no: line_no + length])#get combined coordinates
            print("\nMerged kw box\n",result)
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

            for w in ocr_og:
                word_box = [w['left'], w['right'], w['bottom'], w['top']]
                # print("WORD_BOX",word_box,"IS for",w['word'])
                if(percentage_inside(box, word_box) > parameters['overlap_threshold']
                    and w['word'].lower() not in og_words+original_field_tokens ):
                    if w['confidence'] < parameters['ocr_confidence']:
                        word.append('suspicious' + w['word'])
                        #word.append(data['word'])
                    else:
                        word.append(w['word'])
                    temp_highlight.append(w)
            highlight=merge_fields(temp_highlight)
            # print("\nOriginal ocr keywords",og_words)
            return [' '.join(word),highlight]

def merge_fields(box_list,page_number=0):
    '''
    Merge 2 or more words and get combined coordinates
    '''
    if box_list and type(box_list[0]) is dict:
        min_left = min([word['left'] for word in box_list])
        min_top = min([word['top'] for word in box_list])
        max_right = max([word['right'] for word in box_list])
        max_bottom = max([word['bottom'] for word in box_list])
       
        max_height = max_bottom-min_top
        total_width = max_right-min_left
        word = ' '.join([word['word'] for word in box_list])


        return {'height': max_height, 'width': total_width, 'y': min_top, 'x': min_left, 'right':max_right, 'word': word.strip(), 'page':page_number}
    else:
        return {}

def add_field_value(field_value, box, word, rel_coord, ocr_word, parameters, offset_percentage=90):
    if (percentage_inside(word,box) > offset_percentage):
        if 'validation' not in rel_coord and ocr_word['confidence'] < parameters['ocr_confidence']:
            field_value.append('suspicious'+ocr_word['word'])
            #field_value.append(ocr_word['word'])
        else:
            field_value.append(ocr_word['word'])
    return field_value

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

def keyword_selector(ocr_data, keyword, inp, field_data, page, context=None):
    '''
    Get closest keyword to the trained keyword.
    '''
    # print(field_data)
    # Find_box value
    highlight={}
    temp_highlight=[]
    
    rel_top = field_data['top']
    rel_bottom = field_data['bottom']
    rel_left = field_data['left']
    rel_right = field_data['right']

    keyList=keyword.split()
    # print("\nKeyList:\n%s" % keyList)
    keyLength=len(keyList)
    page_no = page

    keyCords=[]
    counter=0
    if(keyLength>0):
        # Search OCR for the key pattern
        for i, data in enumerate(ocr_data[page_no]):
            data['word'] = data['word'].strip()
            ocr_length = len(ocr_data[page_no])
            regex = re.compile(r'[@_!#$%^&*()<>?/\|}{~:]')
            check=False
            if(data['word']==keyList[0] or (regex.search(data['word'])!=None and re.search('[a-zA-Z]', data['word'].replace(keyList[0],''))==None and keyList[0] in data['word'] )):
                if(keyLength>1):
                    # if keyword == 'PO Number':
                    #     print('keyList',data['word'])
                    for x in range(0,keyLength):
                        if i+x >= ocr_length:
                            check = False
                            break
                        else:
                            # print('Next words',ocr_data[page_no][i+x]['word'])
                            if(ocr_data[page_no][i+x]['word']==keyList[x] or (regex.search(ocr_data[page_no][i+x]['word'])!=None and re.search('[a-zA-Z]', data['word'].replace(keyList[x],''))==None and  keyList[x] in ocr_data[page_no][i+x]['word'])):
                                check=True
                            else:
                                check=False
                                break
                else:
                    check=True

            tempCords=[{}]*1
            if(check):
                # print("-----")
                # print(data['word'])
                counter=counter+1
                top=1000
                bottom=0
                # Left is of the first word
                if(data['word']==keyList[0] or (regex.search(data['word'])!=None and re.search('[a-zA-Z]', data['word'].replace(keyword,''))==None and keyList[0] in  data['word'] )):
                    tempCords[0]['left']=data['left']
                    for x in range(0,keyLength):
                        # Right is of the last word
                        if(x==(keyLength-1)):
                            tempCords[0]['right']=ocr_data[page_no][i+x]['right']

                        # If multi word key
                        if(keyLength>1):
                            if(ocr_data[page_no][i+x]['word']==keyList[x]):
                                # print("%s" % keyList[x])
                                if(ocr_data[page_no][i+x]['top']<top):
                                    top=ocr_data[page_no][i+x]['top']
                                if(ocr_data[page_no][i+x]['bottom']>bottom):
                                    bottom=ocr_data[page_no][i+x]['bottom']
                        else:
                            top=data['top']
                            bottom=data['bottom']

                    tempCords[0]['top']=top
                    tempCords[0]['bottom']=bottom
                    # print(tempCords)
                    keyCords.append(tempCords[0])

    # print("\nNo of occurences of %s:\n%s" %(keyword,counter),keyCords)
    if context is not None:
        print('Context available. Finding context box.')
        # Find context box and get new scope box
        context_box = get_context_box(ocr_data[page_no], keyCords, context)
        if context_box:
            inp = context_box

    if(counter>0):
        keysDict=keyCords
        inpX=(inp['y']+inp['y']+inp['height'])/2
        inpY=(inp['x']+inp['x']+inp['width'])/2
        DistList=[]
        for i,values in enumerate(keysDict):
            # Store all keywords,distances in a Dict
            # Get midpoint of the input
            midheight=((keysDict[i]['top']+keysDict[i]['bottom'])/2)
            midwidth=((keysDict[i]['left']+keysDict[i]['right'])/2)
            x=abs(midheight-inpX)
            y=abs(midwidth-inpY)
            dist=math.sqrt((x*x)+(y*y))
            DistList.append(round(dist, 2))
        # print("\nKey distance dictionary:\n%s" % DistList)
        closestKey=min(DistList)
        minIndex=DistList.index(closestKey)

        box_top=keyCords[minIndex]['top']-rel_top
        box_bottom=keyCords[minIndex]['bottom']+rel_bottom
        box_left=keyCords[minIndex]['left']-rel_left
        box_right=keyCords[minIndex]['right']+rel_right

        box = [box_left, box_right, box_bottom, box_top]

        word=[]
        # print('Box',box)
        # print('Checking in keyword seelctor in page ',page_no)
        for data in ocr_data[page_no]:
            word_box = [data['left'], data['right'], data['bottom'], data['top']]
            if(percentage_inside(box, word_box) > parameters['overlap_threshold']
                and data['word'] not in keyList):
                # print('Keyword',keyword,"word" ,data['word'])
                if 'junk' in field_data:
                    data['word']=data['word'].replace(field_data['junk'],'')
                if data['confidence'] < parameters['ocr_confidence']:
                    word.append('suspicious' + data['word'])
                else:
                    word.append(data['word'])
                temp_highlight.append(data)
        highlight=merge_fields(temp_highlight, page_no)
        return [' '.join(word).strip(),highlight]


    else:
        # print('Exact Keyword not found in OCR')
        return ['',highlight]



