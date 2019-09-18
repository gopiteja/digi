import json,sys
from get_fields_info_utils import *

class DevNull(object):
    def write(self, arg):
        pass
    def flush(self):
        pass

# sys.stdout = DevNull()
# ''' All this is debuggin stuff :(
# import cv2
# from pprint import pprint

# print("this goes to nirvana!")

# with open('ocr_data.json') as f:
#     ocr_data = json.load(f)

# with open('field_data.json') as f:
#     field_data = json.load(f)

# with open('highlight.json') as f:
#     highlight = json.load(f)

# img = cv2.imread('test.jpg')

# w,h = img.shape[:2]
# rf = 670/int(h)
# img = cv2.resize(img, (0,0), fx=rf, fy=rf)


def get_fields_info(ocr_data,highlight,field_data):
    all_fields_data = {}
    try:
        for field,highlight_data in highlight.items():
            field_info = {}
            keyword = field_data[field]['keyword']
            page_no = int(field_data[field]['page'])
            # print('keyword',keyword)

            if highlight_data:
                highlight_data['top'] = highlight_data['y']
                highlight_data['left'] = highlight_data['x']
                highlight_data['bottom'] = highlight_data['y']+highlight_data['height']
                page_no = int(highlight_data['page'])
                # print('highlight_data',highlight_data)
                # try:
                #     cv2.rectangle(img,(highlight_data['x'],highlight_data['y']),(highlight_data['right'],highlight_data['y']+highlight_data['height']),(123,0,255),2)
                # except:
                #     print('field',field)
                #     pass
                
                if keyword:
                    try:
                        keyword_meta = needle_in_a_haystack(keyword,ocr_data[page_no],highlight_data)
                        # cv2.rectangle(img,(keyword_meta['left'],keyword_meta['top']),(keyword_meta['right'],keyword_meta['bottom']),(0,0,0),2)
                    except:
                        keyword_meta = {}
                try:
                    box_list = [highlight_data,keyword_meta]
                except:
                    box_list = [highlight_data]
                    
                combined_box = merge_fields(box_list,page_no)

                # cv2.rectangle(img,(combined_box['x'],combined_box['y']),(combined_box['right'],combined_box['y']+combined_box['height']),(0,0,255),2)

                field_info['box'] = combined_box
                field_info['box_value'] = keyword+' '+highlight_data['word']
                field_info['keyword'] = keyword
                field_info['value'] = highlight_data['word']
                try:
                    validation = field_data[field]['validation']
                except:
                    validation = ''
                field_info['validation'] = validation
            elif not highlight_data and keyword:
                try:
                    keyword_meta = needle_in_a_haystack(keyword,ocr_data[page_no],field_data[field]['scope'])
                    field_info['box_value'] = keyword
                    field_info['keyword'] = keyword
                    field_info['value'] = ''
                    field_info['box'] = keyword_meta
                except Exception as e:
                    print('Failed to fetch the keyword')
            if field_info:   
                all_fields_data[field] = field_info
            # cv2.namedWindow('matrix',cv2.WINDOW_NORMAL)
            # cv2.resizeWindow('matrix', 1200,1200)
            # cv2.imshow('matrix',img)
            # cv2.waitKey()
        # pprint(all_fields_data)
    except Exception as e:
        print('Error in sending fields info while retraining')
    return all_fields_data

# get_fields_info(ocr_data,highlight,field_data)