import pandas as pd
import json
from  difflib import SequenceMatcher
# from string_matching import remove_all_except_al_num
from smart_training.string_matching import remove_all_except_al_num
from db_utils import DB


from training_api import prepare_neighbours
from training_api import get_nearest_neighbour
from training_api import update_field_neighbour_dict
from training_api import extract_quadrant_information
from training_api import update_quadrant_dict
from get_keywords import get_keywords, sort_ocr, get_coords, get_field_dict, get_keywords_for_value

data = pd.read_csv("/home/akshat/program/key_dict_saturation/trained_info (2).csv", sep=';', header=0)

print(data.columns)
field_dict = list(data['field_data'])
ocr_data = list(data['ocr_data'])


def key_there(word, key_list):
    """
    """
    for index,key_w in enumerate(key_list):
        key,_ = key_w
        if remove_all_except_al_num(key) == remove_all_except_al_num(word):
            return True, index

    return False, -1

def make_final_field_list(field_dict, ocr_data_list):
    """
    """
    final_dict_list = {}
    for idx, field_data in enumerate(field_dict):
        print(idx)

        ocr_data = json.loads(ocr_data_list[idx])
        
        for page in ocr_data:
            page = sort_ocr(page)
            char_index_list, haystack = convert_ocrs_to_char_dict_only_al_num(page)
            pre_processed_char.append([char_index_list, haystack])

        trained_info = json.loads(field_data)

        field_with_variation = get_field_dict()

        _, ocr_field_keyword = get_keywords(ocr_data, field_with_variation, pre_processed_char, field_with_variation)


        field_neighbourhood = prepare_neighbours(ocr_field_keyword, trained_info)
        # ocr_keywords = covert_keyword_to_trianed_info(ocr_keywords)

        neighbour_dict = get_nearest_neighbour(trained_info, field_neighbourhood)

        logging.debug(f'neighbour_dict - {neighbour_dict}')

        update_field_neighbour_dict(neighbour_dict, trained_info)

        quadrant_dict = extract_quadrant_information(trained_info, file_name)

        update_quadrant_dict(quadrant_dict)

dict_k = make_final_field_list(field_dict, ocr_data)


# final_field_dict = {}

# trained_db_config = {
#         'host': 'template_db',
#         'user': 'root',
#         'password': 'root',
#         'port': '3306'
#     }
# trained_db = DB('template_db', **trained_db_config)

#   # f.write('field_type; variation\n\r')
# for field, lis in dict_k.items():
#   field_dic = {}
#   for variant in lis:
#       field_dic[variant[0]] = variant[1]

#   trained_db.insert_dict({"field_type": field, "variation":json.dumps(field_dic)}, 'field_dict')






