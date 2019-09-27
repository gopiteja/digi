import cv2
import json
from cluster_headers import cluster_headers_chooser
try:
    from magnet import get_cv_lines
except:
    from app.magnet import get_cv_lines
import copy
from table_predict import predict_maintable
from table_predict import *
# global footer_word
def ocr_data_local(ocrData, T, L, R, B):
    '''
        Parameters : Boundaries of Scope
        Output     : Returns that part of ocrdata which is confined within given boundaries
    '''
    ocrDataLocal = []
    for data in ocrData:
        # print('data', data)
        # print('tlrb' , T, L, R, B)
        if  (data['left'] + int(0.25*data['width'])  >= L
            and data['right'] - int(0.25*data['width']) <= R
            and data['top'] + int(0.5*data['height']) >= T and data['bottom'] - int(0.5*data['height']) <= B ):
            ocrDataLocal.append(data)
    return ocrDataLocal

def get_algo_horizontals(ocrData, header_vers, headerBottom, headerLeft, headerRight, main_table_bottom,ref_col,alignment = 'top'):
    '''Boundaries for horizontal_lines'''
    L = header_vers[ref_col-1][0][0]
    R = header_vers[ref_col][0][0]
    # L = header_vers[-2][0][0]
    # R = header_vers[-1][0][0]
    T = headerBottom
    B = main_table_bottom
    #pass#print('Last Column boundaries',L,R,T,B)
    horizontal_lines = []
    column_words = ocrDataLocal(T,L,R,B,ocrData)

    ln = ""
    for data in column_words:
        ln += data['word']+ ' '
    print('ln', ln)
    '''check for alignment '''

    ocr_data_table = ocrDataLocal(headerBottom,headerLeft,headerRight,main_table_bottom,ocrData)

    # if alignment != '':
    '''If alignment is center'''
    if alignment == 'center':
        horizontal_lines = line_space_hors(ocrData,header_vers,ref_col)
    else:
        line_splits = split_lines_alignment(L,R,T,B,column_words,alignment)
        logging.debug(f'Probable no. of horizontal_lines{len(line_splits)}')
        for splits in line_splits:
            for word in ocr_data_table:
                word_height = word['bottom'] - word['top']
                if (splits[0][1] >= word['top'] + int(word_height * 0.3) and splits[0][1] <= word['bottom'] - int(
                        word_height * 0.3)):
                    logging.debug(f"horiontal line striking {word['word']}../.extending the line above")
                    splits[0][1] = word['top']
                elif (splits[0][1] >= word['top'] + int(word_height * 0.7) and splits[0][1] <= word['bottom']):
                    logging.debug(f"horiontal line striking {word['word']}...extending the line below")
                    splits[0][1] = word['bottom']
            horizontal_lines.append(splits[0][1])
    #pass#print('algo horizontals ', horizontal_lines)
    return horizontal_lines

def validating_horizontal_cv_lines(ocrData,cv_hors,algo_hors,headerLeft,headerRight,headerBottom,main_table_bottom,header_vers,ref_col):
    ''' Validation 1 -
                If cv-line strikes any line items'''
    #pass#print('before val 1 hors', cv_hors)
    cv_hors_new = []
    for hor in cv_hors:
        for word in ocrData:
            if hor not in range(word['top'],word['bottom']) and hor not in cv_hors_new:
                cv_hors_new.append(hor)
            else:
                break
    # for i in range(len(cv_hors) -1):

    cv_hors = cv_hors_new
    cv_hors_new = []

    #pass#print('before val 2 hors', cv_hors)
    ''' Validation 2 -
            '''
    for i in range(len(cv_hors)-1):

        ocr_between_hors = ocrDataLocal(cv_hors[i],headerLeft,headerRight,cv_hors[i+1],ocrData)
        if len(ocr_between_hors):
            cv_hors_new.append(cv_hors[i])
    cv_hors_new.append(cv_hors[len(cv_hors)-1])
    cv_hors = cv_hors_new

    cv_hors_new = []
    ''' Validation 3 -
            if CV line not there, use algo lines
    '''
    logging.debug(f'before validation 3 hors {cv_hors}')
    L = header_vers[ref_col-1][0][0]
    R = header_vers[ref_col][0][0]
    T = headerBottom
    B = main_table_bottom
    column_words = ocrDataLocal(T,L-3,R+3,B,ocrData)
    column_words = ocr_to_lines(column_words)
    for i in range(len(column_words)-1):
        t = column_words[i]['bottom']
        b = column_words[i+1]['top']
        # logging.debug(f'{column_words[i]['word']},'t',{t,'\n','b',b,column_words[i]['word'])
        algo_line = int((t+b)/2)
        for line in algo_hors:
            if(line in range(t,b)):
                algo_line = line
                logging.debug(f'algo hor line found \n \n {algo_line}')
                break
        # cv_verticals = [cv_ver if cv_ver in range(l,r) else algo_line for i in range(len(cv_verticals))]
        cv_line = -1
        for line in cv_hors:
            if line in range(t,b):
                cv_line = line
                break
        if(cv_line == -1):
            logging.debug('Algo line made it through')
            cv_hors_new.append(algo_line)
        else:
            logging.debug('CV lines are the best !!!')
            cv_hors_new.append(cv_line)

    cv_hors = cv_hors_new

    return cv_hors

def get_horizontal_lines(table_img,rf,ocrData,header_hors,header_vers,headerLeft,headerRight,headerBottom,main_table_bottom,ref_col,alignment = 'top'):
    line_item_lines = []
    horizontal_lines  = []

    # cv_hors = get_cv_lines(table_img,rf,10)[0]
    # # print('cv hors',cv_hors)
    # cv_hors = [cv_hor+headerBottom for cv_hor in cv_hors if cv_hor]
    # logging.debug(f'cv hors{cv_hors}')

    for h in header_hors:
        horizontal_lines.append([[headerLeft,h[0][1]],[headerRight,h[0][1]]])
        horizontal_lines.append([[headerLeft,main_table_bottom],[headerRight,main_table_bottom]])
    horizontal_lines.append([[headerLeft,main_table_bottom],[headerRight,main_table_bottom]])

    try:
        algo_hors = get_algo_horizontals(ocrData, header_vers, headerBottom,headerLeft,headerRight,main_table_bottom,ref_col)
        print('algo hors',algo_hors)

        '''
            Validation of horizontal lines
        '''
        # if(len(cv_hors)):
        #     hors = validating_horizontal_cv_lines(ocrData,cv_hors,algo_hors,headerLeft,headerRight,headerBottom,main_table_bottom,header_vers,ref_col)
        # else:
        #     hors = algo_hors
        hors = algo_hors
        #pass#print(' hors after validation',hors)
        for hor in hors:
            horizontal_lines.append([[headerLeft,hor],[headerRight,hor]])
        line_item_lines = horizontal_lines.copy()

        '''Drawing top and bottom horizontal lines of maintable'''

        horizontal_lines = sorted(horizontal_lines, key = lambda x: x[0][1])

        line_item_lines.append([[headerLeft,main_table_bottom],[headerRight,main_table_bottom]])
        line_item_lines.insert(0,[[headerLeft,headerBottom],[headerRight,headerBottom]])

    except Exception as e:
        # logger.error(' No horizontal lines found in table :  {}'.format(e))
        # logging.debug(f'{horizontal_lines},{e}')
        print('error in horizontal')
    return horizontal_lines,line_item_lines

def check_spliting_of_headers(ocr_data, l, r, header_top, header_bottom, cv_verticals):
    cv_ver = -1
    ver_present = False
    ver_needed = False
    # find the cv line that is in between l and r
    print('cv vers', cv_verticals)
    for line in cv_verticals:
        v = line
        if v < r and v > l:
            cv_ver = v
            ver_present = True
            break
    # if there is none return
    if ver_present == False:
        return ver_needed, cv_ver
    else:
        header_1 = ocr_data_local(ocr_data, header_top, l, cv_ver, header_bottom)
        header_2 = ocr_data_local(ocr_data, header_top, cv_ver, r, header_bottom)
        print('header 1 ', header_1)
        print('header2', header_2)
        if len(header_1) and len(header_2):
            ver_needed = True
    return ver_needed, cv_ver

def validating_cv_lines(ocrData, cv_verticals, algorithm_lines, header_top, header_bottom, footer):
    '''
        calculate average word space in the document
        - sum all the spaces
        - take the average

        Args:
            ocrData (list): list of words json of the page

        Returns:
            float: average space between words
    '''


    ''' validation 1: if line intersect with any word from header top to footer of table '''

    # if cv_verticals:
    #     for ver in cv_verticals:
    #         for data in ocrData:
    #             if(data['top'] in range(header_top,footer)):
    #                 cv_verticals = [ver for ver in cv_verticals if(ver not in range(data['left'],data['right']))]

    ''' validation 2: if line is shorter than required '''
    # discussion required

    ''' validation 3: if no data between two cv lines -> remove '''
    # if cv_verticals:
    #     cv_new = []
    #     for i in range(len(cv_verticals)-1):
    #         l = cv_verticals[i]
    #         r = cv_verticals[i+1]
    #         ocrDataColumn = ocr_data_local(ocrData, header_top, l, r, footer)
    #         if(len(ocrDataColumn)):
    #             cv_new.append(cv_verticals[i])
    #     cv_new.append(cv_verticals[-1])
    #     cv_verticals = cv_new



    '''validation 4: if cv line comes in between two algo lines and its dividing the header data between them then consider that otherwise not'''
    new_algo_vers = []
    algorithm_lines.insert(0, [[0,0],[0,2]])
    algorithm_lines.append([[4000,0],[4000,2]])
    for i in range(len(algorithm_lines)-1):
        l = algorithm_lines[i][0][0]
        r = algorithm_lines[i+1][0][0]
        flag, cv_ver = check_spliting_of_headers(ocrData, l, r, header_top, header_bottom, cv_verticals)
        if (flag):
            new_algo_vers.append([[cv_ver, header_top], [cv_ver, footer]])

    algorithm_lines.extend(new_algo_vers)
    algorithm_lines.pop(0)
    algorithm_lines = sorted(algorithm_lines, key=lambda x: x[0][0])
    algorithm_lines.pop(-1)

    return algorithm_lines

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

def sort_ocr(data):
    data = sorted(data, key = lambda i: i['top'])
    for i in range(len(data)-1):
        if abs(data[i]['top'] - data[i+1]['top']) <6 :
            data[i+1]['top'] = data[i]['top']
    data = sorted(data, key = lambda i: (i['top'], i['left']))
    return data

def return_headerend(temp, key, table_outline):

    '''returns the header end given the table outline'''
    header_end_line = 0.0
    data = copy.deepcopy(temp)
    data_key = copy.deepcopy(key)
    data_table = copy.deepcopy(table_outline)

    table_keywords =[]
    T = data_table[0]['y']
    B = data_table[0]['y'] + data_table[0]['height']
    L = data_table[0]['x']
    R = data_table[0]['x'] + data_table[0]['width']
    table_ocrData = ocr_data_local(data_key, T,L,R,B)
    print("local ocr                              -")
    print(table_ocrData)
    for items in table_ocrData:
        table_keywords.append(items['word'])



    sorted_ocr = sort_ocr(data)         #sorting the ocr according to lines
    lines = return_lines(sorted_ocr)



    count = 0  #count for consecutive lines with threshold less than cut off

    No_lines = 0
    for line in lines:


        if count == 2:
            break
        else:

            if line[0]['top'] >= data_table[0]['y']:      #comparing lines and table from same page
                if No_lines == 0:
                    firstline_height = line[0]['bottom'] + 1
                No_lines += 1
                total_words = 0
                matched_words = 0
                for words in line:
                    total_words += 1
                    x = words['word']

                    if x in table_keywords:
                        matched_words += 1
                threshold = matched_words/total_words


                if threshold >= 0.7:
                    count = 0
                    header_end_line = line[0]['bottom'] + 1

                else:
                    count += 1

    if header_end_line == 0.0:
        header_end_line += firstline_height
    return header_end_line

def predict_alias(extracted_data_maintable):
    from difflib import SequenceMatcher
    std_header_list = ['Base Amount', 'Total Amount', 'Product Description','Quantity', 'Rate', 'CGST %', 'SGST %','CGST Amount','IGST %','IGST Amount', 'HSN Code', 'SGST Amount', 'PO Number']

    header_list = [header[0] for header in extracted_data_maintable[0]]

    # for i in range(len(extracted_data_maintable[0])):

    alias_list = []
    for header in header_list:
        scores_with_std_header = []
        for std_header in std_header_list:
            score = SequenceMatcher(None, header.lower(), std_header.lower()).ratio()
            scores_with_std_header.append([score, std_header])
        scores_with_std_header = sorted(scores_with_std_header, key = lambda x: x[0])
        alias_list.append(scores_with_std_header[-1][1])
    print('alias list', alias_list)
    return alias_list

def table_training(ocr_data_list, keywords_list, table_crop, file_path, img_width):

    '''variables needed'''
    ocr_data = ocr_data_list[0]

    # resize table crop
    Rf = int(img_width)/670
    for i in range(len(table_crop)):
        table_crop[i]['x'] /= Rf
        table_crop[i]['y'] /= Rf
        table_crop[i]['height'] /= Rf
        table_crop[i]['width'] /= Rf


    # resize ocr data
    # for data in ocr_data:
    #     data['top'] /= Rf
    #     data['bottom'] /= Rf
    #     data['left'] /= Rf
    #     data['right'] /= Rf
    #     data['height'] /= Rf
    #     data['width'] /= Rf



    # footer_area_top = 445
    footer_area_top = table_crop[0]['y'] + table_crop[0]['height']
    header_top = table_crop[0]['y']


    # print('ocr data', ocr_data)
    header_bottom = return_headerend(ocr_data, keywords_list, table_crop)
    print('header bottom', header_bottom)
    header_right = max(ocr_data, key=lambda x: x['right'])['right']
    header_left = min(ocr_data, key=lambda x: x['left'])['left']

    # print('header top', header_top)
    # print('header left', header_left)
    # print('header_right', header_right)
    # print('footer area top', footer_area_top)

    '''Image from pdf'''
    # print('hereeee')
    # imgpath = 'app/2000438276.jpg'
    # try:
    #     img = cv2.imread(imgpath)
    #     h,w = img.shape[:2]
    # except Exception as e:
    #     print('img path failed')
    #     img = np.zeros((1000,1000,3),np.uint8)
    #     # logging.debug('loading default blank image')
    #     h,w = img.shape[:2]
    # print('eer')
    # rf = 670/int(w)
    # print('rf table',rf)
    # # img_ = cv2.resize(img, (0,0), fx=rf, fy=rf)
    # img_ = img
    # print('ere')
    # ocr_img = img_.copy()
    # print('ereggg')
    # ocr_img_hors = img_.copy()
    # print('sdkasbjadk')


    print('here-1')
    ''' Finding Footer Function '''
    # ocr lines 2
    footer_lines = return_lines(ocr_data)
    base_line_idx = -1
    bottom_line_idx = -1
    top_line_idx = -1
    for i, line in enumerate(footer_lines):
        if line[0]['bottom'] > footer_area_top:
            base_line_idx = i
            break

    try:
        bottom_line_idx = base_line_idx + 3
        prob_footer_bottom = footer_lines[bottom_line_idx][0]['bottom']
    except:
        prob_footer_bottom = max(ocr_data, key=lambda x: x['bottom'])['bottom']
    try:
        top_line_idx = base_line_idx -2
        prob_footer_top = footer_lines[top_line_idx][0]['bottom']
    except:
        prob_footer_top = header_bottom


    print('keywords list', keywords_list)
    keywords_list_footer_b = ocr_data_local(keywords_list, footer_area_top, 0, 4000, prob_footer_bottom)
    if len(keywords_list_footer_b):
        minimal_footer = keywords_list_footer_b[0]
    else:

        keywords_list_footer_t = ocr_data_local(keywords_list, prob_footer_top, 0, 4000, footer_area_top)
        if len(keywords_list_footer_t):
            minimal_footer = keywords_list_footer_t[-1]
        else:
            keywords_list_footer_f = ocr_data_local(keywords_list, prob_footer_top, 0, 4000, footer_area_top)
            if len(keywords_list_footer_f):
                minimal_footer = keywords_list_footer_b[0]
            else:
                minimal_footer = {}
    # now some improvements in footer and footer data to be saved
    # add footer lines in horizontal_lines

    if minimal_footer == {}:
        ocr_data_footer = ocr_data_local(ocr_data, footer_area_top, 0, 4000, 4000)
        minimal_footer = ocr_data_footer[0]
    print('minimal footer', minimal_footer)
    footer_word = minimal_footer
    footer_lines = []
    try:
        footer_lines.append([[header_left,minimal_footer['top']-3],[header_right,minimal_footer['top']-3]])
        footer_lines.append([[header_left,minimal_footer['bottom']+3],[header_right,minimal_footer['bottom']+3]])
    except Exception as e:
        print(e)
        print('no footer found')

    print('here0')

    '''clustering headers function  and making vers'''
    algorithm_lines = []
    vers_ = cluster_headers_chooser(ocr_data, int(header_top), int(header_left), int(header_right), int(footer_area_top))
    for ver in vers_:
        algorithm_lines.append([[ver,header_top],[ver,footer_area_top]])

    vertical_lines = algorithm_lines

    vertical_lines.append([[header_left, header_top], [header_left, footer_area_top]])
    vertical_lines.append([[header_right, header_top], [header_right, footer_area_top]])


    '''making cv lines and validating  with algo lines'''
    # try:
    #     table_img_hors = img_[int(header_bottom):int(footer_area_top),:]
    # except Exception as e:
    #     print(e)
    #     print('error in 478')
    # hors, cv_verticals = get_cv_lines(table_img_hors, rf)
    # cv_verticals = [int(ver/rf) for ver in cv_verticals]
    # print('here1')
    # # for i,v in enumerate(cv_verticals):
    # #     cv2.line(ocr_img,(int(v),int(header_top)),(int(v),int(footer_area_top)),(50, 0, 255),1)
    # # cv2.namedWindow('table',cv2.WINDOW_NORMAL)
    # # cv2.resizeWindow('table', 1200,1200)
    # # cv2.imshow('table',ocr_img)
    # # cv2.waitKey(0)
    # # cv2.destroyAllWindows()

    # if(len(cv_verticals)>2):
    #     vertical_lines = validating_cv_lines(ocr_data,
    #                     cv_verticals,
    #                     algorithm_lines,
    #                     header_top,
    #                     header_bottom,
    #                     footer_area_top)
    # else:
    #     vertical_lines = algorithm_lines

    print('here2')

    '''making hors'''
    # ref_col = get_ref_col(json_data)
    # table_img_hors = ocr_img_hors[int(header_bottom/rf):int(footer_area_top/rf),:]
    header_hors = []
    header_hors.append([[header_left,header_top],[header_right,header_top]])
    header_hors.append([[header_left,header_bottom],[header_right,header_bottom]])

    header_vers = []
    for v in vertical_lines:
        header_vers.append([[v[0][1], header_top],[v[0][1], footer_area_top]])

    ref_col = -1
    # table_img_hors = img[int(header_bottom/rf):int(footer_area_top/rf),:]
    table_img_hors = 0
    print('here3')
    rf = 0
    horizontal_lines,line_item_lines = get_horizontal_lines(table_img_hors,rf,ocr_data,header_hors,header_vers,header_left,header_right,header_bottom,footer_area_top,ref_col)
    print('here4')

    # horizontal_lines = []
    # horizontal_lines.append([[header_left,header_top],[header_right,header_top]])
    # horizontal_lines.append([[header_left,header_bottom],[header_right,header_bottom]])
    # horizontal_lines.append([[header_left,footer_area_top],[header_right,footer_area_top]])


    #sorting
    horizontal_lines = sorted(horizontal_lines, key = lambda x: x[0][1])

    # remove repeating lines
    horizontal_lines_unique = []
    horizontal_lines_unique.append(horizontal_lines[0])
    for i in range(1, len(horizontal_lines)):
        h = horizontal_lines[i]
        if h[0][1] != horizontal_lines[i-1][0][1]:
            horizontal_lines_unique.append(h)
    horizontal_lines  = horizontal_lines_unique



    '''tables extraction '''
    ocr_data_old = ocr_data
    subheader_data_arrays = None
    # import pdb; pdb.set_trace()
    req_cols = None
    alias_names = []
    print('here5')
    tables = predict_maintable(ocr_data, ocr_data_old, horizontal_lines,vertical_lines, header_bottom, req_cols, alias_names,subheader_data_arrays)

    print('here6')
    '''show lines (will be replaced by return lines in future)'''

    #
    # for i,h in enumerate(horizontal_lines):
    #     cv2.line(ocr_img_copy,(int(h[0][0]),int(h[0][1])),(int(h[1][0]),int(h[1][1])),(50, 0, 255),1)
    # for i,v in enumerate(vertical_lines):
    #     cv2.line(ocr_img_copy,(int(v[1][0]),int(v[0][1])),(int(v[1][0]),int(v[1][1])),(50, 0, 255),1)
    # cv2.namedWindow('table',cv2.WINDOW_NORMAL)
    # cv2.resizeWindow('table', 1200,1200)
    # cv2.imshow('table',ocr_img_copy)
    # cv2.waitKey(0)
    # cv2.destroyAllWindows()

    '''final formatting'''
    # {width: 100, height: 100, x:10, y:1, page:1, color:red}
    hors = []

    for h in horizontal_lines:
        width = h[1][0] - h[0][0]
        hors.append({'width': width*Rf, 'height': 10*Rf, 'x':h[0][0]*Rf, 'y':h[0][1]*Rf, 'page':0, 'color':'red'})
    hors[0]['color'] = 'blue'
    hors[1]['color'] = 'blue'
    # hors[-1]['color'] = 'blue'
    # hors[-2]['color'] = 'blue'
    print('footer lines', footer_lines)
    for h in footer_lines:
        width = h[1][0] - h[0][0]
        hors.append({'width': width*Rf, 'height': 10*Rf, 'x':h[0][0]*Rf, 'y':h[0][1]*Rf, 'page':0, 'color':'blue'})
    vers = []
    for v in vertical_lines:
        height = v[1][1] - v[0][1]
        vers.append({'width': 10*Rf, 'height': height*Rf, 'x':v[0][0]*Rf, 'y':v[0][1]*Rf, 'page':0, 'color':'red'})


    '''Alias'''
    no_of_alias = len(vertical_lines) - 1
    # alias = ['' for i in range(no_of_alias)]
    alias = predict_alias(tables)

    table_final_data = [[tables, {'lines': { 'hors':hors, 'vers':vers}, 'alias': alias, 'footer': footer_word}]]
    return {"table": table_final_data}

def extract_table_from_lines(ocr_data_list, table_lines, img_width):
    print('hereeeeee')
    ocr_data = ocr_data_list[0]
    Rf = int(img_width)/670


    hors = table_lines['hors']
    vers = table_lines['vers']

    horizontal_lines = []
    vertical_lines = []

    for v in vers:
        x1 = v['x']/Rf
        y1 = v['y']/Rf
        x2 = v['x']/Rf
        y2 = (v['y'] + v['height'])/Rf
        vertical_lines.append([[x1, y1], [x2, y2]])
    vertical_lines = sorted(vertical_lines, key=lambda x: x[0][0])

    for h in hors:
        x1 = h['x']/Rf
        y1 = h['y']/Rf
        x2 = (h['x'] + h['width'])/Rf
        y2 = h['y']/Rf
        horizontal_lines.append([[x1, y1], [x2, y2]])
    horizontal_lines = sorted(horizontal_lines, key=lambda x: x[0][1])

    headerBottom = horizontal_lines[-2][0][1]
    header_hors = horizontal_lines[:-1].copy()
    header_vers = [ [[ver[0][0], ver[0][1]], [ver[0][0], headerBottom]] for ver in vertical_lines]
    table_img = None
    rf = Rf
    ocrData = ocr_data
    headerLeft = horizontal_lines[0][0][0]
    headerRight = horizontal_lines[0][1][0]
    
    main_table_bottom = horizontal_lines[-1][0][1]
    ref_col = -1
    horizontal_lines = sorted(horizontal_lines, key=lambda x: x[0][1])
    print('len', len(horizontal_lines))
    horizontal_lines, _ = get_horizontal_lines(table_img,rf,ocrData,header_hors,header_vers,headerLeft,headerRight,headerBottom,main_table_bottom,ref_col,alignment = 'top')
    horizontal_lines = sorted(horizontal_lines, key=lambda x: x[0][1])

    ocr_data_old = ocr_data
    subheader_data_arrays = None
    # import pdb; pdb.set_trace()
    req_cols = None
    alias_names = []
    header_bottom = horizontal_lines[1][0][1]

    print('hors', horizontal_lines)
    print('vers', vertical_lines)
    tables = predict_maintable(ocr_data, ocr_data_old, horizontal_lines,vertical_lines, header_bottom, req_cols, alias_names,subheader_data_arrays)

    '''footer word'''
    ocr_data_footer = ocr_data_local(ocr_data, horizontal_lines[-1][0][1], 0, 4000, 4000)
    try:
        minimal_footer = ocr_data_footer[0]
    except:
        minimal_footer = {}
    print('minimal footer', minimal_footer)
    footer_word = minimal_footer

    table_final_data = [[tables, {'lines': { 'hors':hors, 'vers':vers}, 'footer': footer_word}]]
    return {"table": table_final_data}
