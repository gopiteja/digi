import json
import ast
import math
import os
import io

from PyPDF2 import PdfFileReader
from pathlib import Path
from PIL import Image
from db_utils import DB
from ace_logger import Logging


try:
    from app.smart_training.string_matching import convert_ocrs_to_char_dict_only_al_num
    from app.smart_training.string_matching import remove_all_except_al_num
    from app.smart_training.string_matching import string_match_python
    from app.smart_training.string_matching import merge_coord
    from app.smart_training.string_matching import make_keyword_string
except:
    from db_utils import DB
    from smart_training.string_matching import convert_ocrs_to_char_dict_only_al_num
    from smart_training.string_matching import remove_all_except_al_num
    from smart_training.string_matching import string_match_python
    from smart_training.string_matching import merge_coord
    from smart_training.string_matching import make_keyword_string

logging = Logging()

try:
    with open('app/parameters.json') as f:
        parameters = json.loads(f.read())
except:
    with open('parameters.json') as f:
        parameters = json.loads(f.read())

# the multiplier for the distance between the keyword threshold
DISTANCE_THRESHOLD = parameters['distance_multiplier']

# same line deviation percentage height
SAME_LINE_THRESHOLD = parameters['SAME_LINE_THRESHOLD']


def caculate_dis(box1, box2):
    if box1['right'] - box1['left'] < 0 or box2['right'] - box2['left'] < 0:
        return 100000000

    mid1 = (
        box1['left'] + int(abs(box1['left'] - box1['right']) / 2),
        box1['top'] + int(abs(box1['top'] - box1['bottom']) / 2)
    )
    mid2 = (
        box2['left'] + int(abs(box2['left'] - box2['right']) / 2),
        box2['top'] + int(abs(box2['top'] - box2['bottom']) / 2)
    )

    dist = math.hypot(mid2[0] - mid1[0], mid2[1] - mid1[1])

    return dist


def calculate_threhold(width, height):
    return math.hypot(width, height) * DISTANCE_THRESHOLD


def sort_ocr(data):
    data = sorted(data, key=lambda i: i['top'])
    for i in range(len(data) - 1):
        data[i]['word'] = data[i]['word'].strip()
        data[i]['word'] = data[i]['word'].encode('utf-8').decode()
        data[i + 1]['word'] = data[i + 1]['word'].strip()
        if abs(data[i]['top'] - data[i + 1]['top']) < 6:
            data[i + 1]['top'] = data[i]['top']
    data = sorted(data, key=lambda i: (i['top'], i['left']))
    return data


def in_same_line(point_1, point_2):
    """
    Author : Akshat Goyal
    """
    mid_y_1 = point_1['top'] + int(abs(point_1['top'] - point_1['bottom']) / 2)
    mid_y_2 = point_2['top'] + int(abs(point_2['top'] - point_2['bottom']) / 2)

    height_1 = abs(point_1['top'] - point_1['bottom'])
    height_2 = abs(point_2['top'] - point_2['bottom'])

    deviation_threshold = height_1 if height_1 > height_2 else height_2

    if abs(mid_y_2 - mid_y_1) < (deviation_threshold * SAME_LINE_THRESHOLD / 100):
        return True
    else:
        return False


def return_same_line_point(anchor_points, floating_points):
    """
    Author : Akshat Goyal
    """
    for index, point in enumerate(floating_points):
        point_in_same_line = True
        for anchor in anchor_points:
            if not in_same_line(point, anchor):
                point_in_same_line = False
                break
        if point_in_same_line:
            return index
    return -1


def calculate_point_distance_from_other_points(remaining_coords, cluster_coord):
    """
    Author : Akshat Goyal
    """
    all_dist = []
    for remaining_coord in remaining_coords:
        tot_dis = 0
        for point in cluster_coord:
            tot_dis += caculate_dis(point, remaining_coord)

        all_dist.append(tot_dis)

    return all_dist


def actual_clustering(keywords_list, keyCords_list):
    """
    Author : Akshat Goyal
    """
    smallest_list_coord = keyCords_list[0]

    coord_clusters = []
    word_clusters = []

    for idx, coord in enumerate(smallest_list_coord):
        cluster_coord = [coord]
        word_cluster = [keywords_list[0][idx]]

        for rem_idx, remaining_coords in enumerate(keyCords_list[1:]):
            all_dist = []

            max_width = sum([point['right'] - point['left'] for point in cluster_coord])
            max_height = sum([point['bottom'] - point['top'] for point in cluster_coord])

            threshold = calculate_threhold(max_width, max_height)

            same_line_point_index = return_same_line_point(cluster_coord, remaining_coords)

            if same_line_point_index != -1:
                all_dist = calculate_point_distance_from_other_points([remaining_coords[same_line_point_index]],
                                                                      cluster_coord)

                min_dis = min(all_dist)

                if min_dis < threshold:
                    cluster_coord.append(remaining_coords[same_line_point_index])
                    word_cluster.append(keywords_list[1 + rem_idx][same_line_point_index])

            if all_dist and min_dis > threshold:
                all_dist = calculate_point_distance_from_other_points(remaining_coords, cluster_coord)

                min_dis = min(all_dist)

                logging.debug(f'idx - {idx}')
                logging.debug(f'coord - {coord}')
                logging.debug(f'threshold - {threshold}')
                logging.debug(f'all_dist - {all_dist}')
                logging.debug(f'min_dis - {min_dis}')
                logging.debug(f'key_list - {keywords_list[1 + rem_idx]}')
                logging.debug(f'coord_list - {remaining_coords}')
                logging.debug(f'index - {all_dist.index(min_dis)}')

                if min_dis < threshold:
                    min_index = all_dist.index(min_dis)

                    cluster_coord.append(remaining_coords[min_index])
                    word_cluster.append(keywords_list[1 + rem_idx][min_index])

        coord_clusters.append(cluster_coord)
        word_clusters.append(word_cluster)

    return coord_clusters, word_clusters


def cluster_points_coord(keywords_list, keyCords_list, keyCords):
    """
    Author : Akshat Goyal

    Args:
        keywords_list : sorted list of dict of words as keys
        keyCords_list : sorted list of dict of coords for respective words

    Return:

    """
    keyList = []

    coord_clusters, word_clusters = actual_clustering(keywords_list, keyCords_list)

    coord_clusters = sorted(coord_clusters, key=len)
    word_clusters = sorted(word_clusters, key=len)

    # taking the biggest cluster
    max_len = len(coord_clusters[-1])

    to_return_coord_cluster = []
    to_return_word_cluster = []
    # print(word_clusters)

    # removing other smaller clusters
    for idx, cluster in enumerate(coord_clusters):
        if len(cluster) == max_len:
            to_return_coord_cluster.append(cluster)
            to_return_word_cluster.append(word_clusters[idx])

    # print(to_return_word_cluster)
    coord_clusters = []
    word_clusters = []
    for idx, cluster in enumerate(to_return_coord_cluster):
        keyCords = {'top': 10000, 'bottom': 0, 'right': 0, 'left': 10000}
        word_cluster = []
        for cluster_idx, point in enumerate(cluster):
            prospective_keyword = to_return_word_cluster[idx][cluster_idx]

            # if prospective keyword equal to the origional without special character
            if make_keyword_string(prospective_keyword):
                keyCords = merge_coord(keyCords, point)
                # todo join string in order according to coordinates
                word_cluster.append(''.join(make_keyword_string(prospective_keyword)))

        word_clusters.append(word_cluster)
        coord_clusters.append(keyCords)

    # print(word_clusters)

    return word_clusters, coord_clusters


def get_definite_checkpoint(keywords_list, keyCords_list):
    """
    Author : Akshat Goyal
    
    give a starting point if 
    """

    # just intialize if we don't find anything to latch on
    keyList = []

    keyCords = {'top': 10000, 'bottom': 0, 'right': 0, 'left': 10000}
    starting = 0

    if keywords_list:
        keyList, keyCords = cluster_points_coord(keywords_list, keyCords_list, keyCords)

    return keyList, keyCords, starting


def compute_all_key_list_coord(keyList, char_index_list, haystack):
    """
    Author : Akshat Goyal
    """

    keyCords_list = []
    keywords_list = []
    counter = 0

    for key in keyList:
        key_param = remove_all_except_al_num(key)
        keyCords, keywords = string_match_python(key_param, char_index_list, haystack)
        # keyCords, keywords = string_match_naive(key_param, ocr_data[page_no], pre_process_char[page_no][0], pre_process_char[page_no][1])
        if not keywords:
            continue
        counter += len(keyCords)
        if keywords:
            keywords_list.append(keywords)
            keyCords_list.append(keyCords)

    keywords_list.sort(key=len)
    keyCords_list.sort(key=len)

    return keyCords_list, keywords_list, counter


def get_key_list_coord(keywords_list, keyCords_list, inp):
    """
    Author : Akshat Goyal
    
    This function takes all the possible options
    for the keywords and compares them and returns 
    the most appropriate keylist and keycoord

    Args:
        keywords_list
        keyCords_list
        inp

    Return:


    """
    if inp:
        inpX = (inp['x'] + inp['x'] + inp['width']) / 2
        inpY = (inp['y'] + inp['y'] + inp['height']) / 2

    keyList, keyCords, starting = get_definite_checkpoint(keywords_list, keyCords_list)

    # if there are multiple cluster then this will take care of it
    if inp:
        DistList = []
        for index, keysDict in enumerate(keyCords[starting:]):
            idx = starting + index
            if keysDict:
                # for i,values in enumerate(keysDict):
                # Store all keywords,distances in a Dict
                # Get midpoint of the input
                midheight = ((keysDict['top'] + keysDict['bottom']) / 2)
                midwidth = ((keysDict['left'] + keysDict['right']) / 2)
                y = abs(midheight - inpY)
                x = abs(midwidth - inpX)
                dist = math.sqrt((x * x) + (y * y))
                DistList.append(round(dist, 2))
                # print("\nKey distance dictionary:\n%s" % DistList)
        try:
            closestKey = min(DistList)
        except:
            return ['', {}]

        minIndex = DistList.index(closestKey)

        keyList = [keyList[minIndex]]

        keyCords = [keyCords[minIndex]]

    return keyList, keyCords


def get_field_dict(tenant_id, for_update=False):
    """
    :return field_dict from db
    """
    db_config = {
        'host': os.environ['HOST_IP'],
        'port': os.environ['LOCAL_DB_PORT'],
        'user': os.environ['LOCAL_DB_USER'],
        'password': os.environ['LOCAL_DB_PASSWORD'],
        'tenant_id': tenant_id
    }
    db = DB('template_db', **db_config)
    db_data = db.get_all('field_dict')
    query_result = json.loads(db_data.to_json(orient='records'))

    fields = {}
    for row in query_result:
        field_type = row['field_type']
        variations = ast.literal_eval(row['variation'])

        # if we want for update then we require dict
        # else we want a list of list
        if not for_update:
            variations = sorted(variations.items(), key=lambda x: x[1], reverse=True)
        fields[field_type] = variations
    return fields


def get_quadrant_dict(tenant_id, for_update=False ):
    """
    :return field_dict from db
    """
    db_config = {
        'host': os.environ['HOST_IP'],
        'port': os.environ['LOCAL_DB_PORT'],
        'user': os.environ['LOCAL_DB_USER'],
        'password': os.environ['LOCAL_DB_PASSWORD'],
        'tenant_id': tenant_id
    }
    db = DB('template_db', **db_config)
    db_data = db.get_all('field_quadrant_dict')
    query_result = json.loads(db_data.to_json(orient='records'))

    fields = {}
    for row in query_result:
        field_type = row['field']
        variations = ast.literal_eval(row['quadrant'])

        # if we want for update then we require dict
        # else we want a list of list
        if not for_update:
            variations = sorted(variations.items(), key=lambda x: x[1], reverse=True)
        fields[field_type] = variations
    return fields


def get_page_dimension(case_id, tenant_id, standard_width=670):
    """
    Author : Akshat Goyal
    """
    db_config = {
        'host': os.environ['HOST_IP'],
        'user': os.environ['LOCAL_DB_USER'],
        'password': os.environ['LOCAL_DB_PASSWORD'],
        'port': os.environ['LOCAL_DB_PORT'],
        'tenant_id': tenant_id
    }

    db = DB('io_configuration', **db_config)
        
    input_config = db.get_all('input_configuration')
    output_config = db.get_all('output_configuration')

    if (input_config.loc[input_config['type'] == 'Document'].empty
                        or output_config.loc[input_config['type'] == 'Document'].empty):
        message = 'Input/Output not configured in DB.'
        logging.error(message)
    else:
        input_path = input_config.iloc[0]['access_1']
        output_path = output_config.iloc[0]['access_1']

    queue_db = DB('queues', **db_config)

    page_dimensions = {}

    try:
        source_folder = parameters['ui_folder']

        query = f'select id, file_name from process_queue where case_id = "{case_id}"'
        file_name = list(queue_db.execute(query)['file_name'])[0]

        try:
            file_name = output_path + '/' + file_name
        except:
            file_name = output_path + '/' + case_id + '.pdf'

        file_path = Path(source_folder) / file_name
        try:
            logging.debug(f'file_path - {file_path}')
            with open(file_path, 'rb') as file_blob:
                file = PdfFileReader(file_blob)
                for page in range(file.numPages):
                    width = float(file.getPage(page).mediaBox[2])
                    rf = float(width / standard_width)
                    height = float(file.getPage(page).mediaBox[3])

                    page_dimensions[page] = (width / rf, height / rf)
        except:
            with Image.open(file_path) as file_blob:
                width, height = file_blob.size
                page_dimensions[0] = (width / rf, height / rf)

    except:
        try:
            query = f'select * from merged_blob where case_id = "{case_id}"'
            merged_blob = list(queue_db.execute(query)['merged_blob'])[0]

            file_blob = io.BytesIO(merged_blob)

            file = PdfFileReader(file_blob)
            for page in range(file.numPages):
                width = float(file.getPage(page).mediaBox[2])
                rf = float(width / standard_width)
                height = float(file.getPage(page).mediaBox[3])

                page_dimensions[page] = (width / rf, height / rf)
        except:
            message = 'merged blob and pdf both are not there'
            logging.warning(message)

    return page_dimensions


def which_quadrant(keyword_dimension, page_dimension):
    """
    Author : Akshat Goyal
    
    Quadrant :

        1,1  1,2  1,3  1,4

        2,1  2,2  2,3  2,4

        3,1  3,2  3,3  3,4

        4,1  4,2  4,3  4,4

    """
    if 'left' not in keyword_dimension:
        return (0, 0)
    mid_x = keyword_dimension['left'] + int((keyword_dimension['right'] - keyword_dimension['left']) / 2)
    mid_y = keyword_dimension['top'] + int((keyword_dimension['bottom'] - keyword_dimension['top']) / 2)

    x_quadrant_width = int(page_dimension[0] / 4)
    y_quadrant_width = int(page_dimension[1] / 4)

    x_quarant = int(mid_x / x_quadrant_width)
    y_quarant = int(mid_y / y_quadrant_width)

    return (y_quarant + 1, x_quarant + 1)


def keywords_lying_in_exact_quadrant(keywords, quadrant_dict, page_dimensions):
    """
    Author : Akshat Goyal
    """
    exact_quadrant_keywords = []

    for quad, _ in quadrant_dict:
        for keyword, weight in keywords:
            keyword_page = keyword['page']

            if quad == str(which_quadrant(keyword, page_dimensions[keyword_page])):
                exact_quadrant_keywords.append([keyword, weight])

    if exact_quadrant_keywords:
        return exact_quadrant_keywords
    else:
        return keywords


def keywords_lying_in_exact_quadrant_value(keywords, quadrant_dict, page_dimensions):
    """
    Author : Akshat Goyal
    """
    exact_quadrant_keywords = []

    for quad, _ in quadrant_dict:
        for keyword in keywords:
            keyword_page = keyword['page']

            if quad == str(which_quadrant(keyword, page_dimensions[keyword_page])):
                exact_quadrant_keywords.append(keyword)

    if exact_quadrant_keywords:
        return exact_quadrant_keywords
    else:
        return keywords


def get_pre_process_char(pre_process_char, ocr_data, page_no):
    """
    """
    if not pre_process_char:
        logging.warning('pre prossesing not done, VERY BADDDDD!!!')
        char_index_list, haystack = convert_ocrs_to_char_dict_only_al_num(ocr_data[page_no])
    else:
        try:
            char_index_list, haystack = pre_process_char[page_no]
        except:
            char_index_list, haystack = convert_ocrs_to_char_dict_only_al_num(ocr_data[page_no])

    return char_index_list, haystack


def check_keyword_present(keyword, old_keywords):
    for key, weight in old_keywords:
        if keyword == key:
            return True
    return False


def get_keywords_in_quadrant(mandatory_fields, ocr_field_keyword, case_id, tenant_id, standard_width=670):
    """
    Author : Akshat Goyal
    """
    quadrant_dict = get_quadrant_dict(tenant_id=tenant_id)
    page_dimensions = get_page_dimension(case_id, standard_width=standard_width, tenant_id=tenant_id)

    for field in mandatory_fields:
        if field in ocr_field_keyword and field in quadrant_dict and page_dimensions:
            ocr_field_keyword[field] = keywords_lying_in_exact_quadrant(ocr_field_keyword[field], quadrant_dict[field],
                                                                        page_dimensions)

    return ocr_field_keyword


def get_keywords_max_length(mandatory_fields, ocr_field_keyword):
    """
    Author : Akshat Goyal
    """
    THRESHOLD_MATCH_PERCENT = parameters['keyword_THRESHOLD_MATCH_PERCENT']
    max_ocr_field_keyword = {}
    for field in mandatory_fields:
        max_len = 0
        if field not in ocr_field_keyword:
            continue

        max_ocr_field_keyword[field] = []

        for keyword, weight in ocr_field_keyword[field]:
            # print(f'max_len - {max_len}')
            word_sans_special = keyword['word']

            if len(word_sans_special) > max_len:
                max_len = len(word_sans_special)
            # print(f'keyword - {keyword["word"]}')

        # print(f'max_len - {max_len}')
        for keyword in ocr_field_keyword[field]:
            threshold = (max_len * THRESHOLD_MATCH_PERCENT) / 100

            word_sans_special = keyword[0]['word']
            if (max_len - len(word_sans_special)) < threshold:
                max_ocr_field_keyword[field].append(keyword)

    return max_ocr_field_keyword


def get_keywords(ocr_data, mandatory_fields, pre_processed_char, tenant_id, field_with_variation={}, quadrant_dict={}, case_id='',
                 standard_width=670):
    """
    Author : Akshat Goyal
    """
    try:
        if not field_with_variation:
            field_with_variation = get_field_dict(tenant_id=tenant_id)
    except:
        logging.error("table field_dict not present")
        field_with_variation = {}


    ocr_keywords = []
    ocr_field_keyword = {}

    for field in mandatory_fields:
        logging.debug(f'field - {field}')
        if field_with_variation and field in field_with_variation:
            for variation, weight in field_with_variation[field]:
                for idx, page in enumerate(pre_processed_char):
                    char_index_list, haystack = page

                    keyCords_list, keywords_list, counter = compute_all_key_list_coord([variation], char_index_list,
                                                                                       haystack)

                    if counter > 0:
                        keyList, keyCords = get_key_list_coord(keywords_list, keyCords_list, {})

                        for index, coord in enumerate(keyCords):
                            keyword = coord

                            # sometimes it is comming empty beware
                            if (''.join(keyList[index])).strip():
                                # if a certain percent of a word match then it should be of
                                # lower weightage than full match
                                # weight = 1/_weight

                                keyword['word'] = (' '.join(keyList[index])).strip()
                                keyword['page'] = idx
                                if keyword not in ocr_keywords:
                                    ocr_keywords.append(keyword)

                                if field in ocr_field_keyword:
                                    if not check_keyword_present(keyword, ocr_field_keyword[field]):
                                        ocr_field_keyword[field].append([keyword, weight])
                                else:
                                    ocr_field_keyword[field] = [[keyword, weight]]

    return ocr_keywords, ocr_field_keyword


def get_keywords_for_value(ocr_data, mandatory_fields, pre_processed_char, tenant_id, field_with_variation={}, quadrant_dict={},
                           case_id=''):
    """
    Author : Akshat Goyal
    """
    if not field_with_variation:
        field_with_variation = get_field_dict(tenant_id=tenant_id)

    ocr_keywords = []
    ocr_field_keyword = {}

    for field in mandatory_fields:
        logging.debug(f'field - {field}')
        if field in field_with_variation:
            for variation, _ in field_with_variation[field]:
                for idx, page in enumerate(pre_processed_char):
                    char_index_list, haystack = page

                    keyCords_list, keywords_list, counter = compute_all_key_list_coord(variation.split(),
                                                                                       char_index_list, haystack)

                    if (counter > 0):
                        keyList, keyCords = get_key_list_coord(keywords_list, keyCords_list, {})

                        for index, coord in enumerate(keyCords):
                            keyword = coord

                            # sometimes it is comming empty beware
                            if (''.join(keyList[index])).strip():
                                # if a certain percent of a word match then it should be of
                                # lower weightage than full match
                                weight = len(keyList[index]) / len(variation.split())

                                keyword['word'] = (' '.join(keyList[index])).strip()
                                keyword['page'] = idx
                                if keyword not in ocr_keywords:
                                    ocr_keywords.append(keyword)

                                if field in ocr_field_keyword:
                                    if not check_keyword_present(keyword, ocr_field_keyword[field]):
                                        ocr_field_keyword[field].append([keyword, weight])
                                else:
                                    ocr_field_keyword[field] = [[keyword, weight]]

    return ocr_keywords, ocr_field_keyword


def get_coords(ocr_data, field, scope, pre_processed_char):
    """
    Author : Akshat Goyal
    """

    char_index_list, haystack = pre_processed_char[scope['page']]

    keyCords_list, keywords_list, counter = compute_all_key_list_coord(field.split(), char_index_list, haystack)

    ocr_keywords = []
    if (counter > 0):
        keyList, keyCords = get_key_list_coord(keywords_list, keyCords_list, scope)

        for index, coord in enumerate(keyCords):
            keyword = coord

            # sometimes it is comming empty beware
            if (''.join(keyList[index])).strip():
                # print('variation - ', variation)
                # print('keyword detected', keyList[index])

                # if a certain percent of a word match then it should be of
                # lower weightage than full match
                weight = len(field.split()) / len(keyList[index])

                keyword['word'] = ' '.join(keyList[index])
                keyword['page'] = scope['page']
                if keyword not in ocr_keywords:
                    ocr_keywords.append([keyword, weight])

    return ocr_keywords
