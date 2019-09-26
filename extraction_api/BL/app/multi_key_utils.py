
import traceback
from difflib import SequenceMatcher
from math import sqrt
try:
  from app.extracto_utils import needle_in_a_haystack
  from app.ace_logger import Logging
except:
  from extracto_utils import needle_in_a_haystack
  from ace_logger import Logging

thres = 0.7
word_space_mul = 1.5
logging = Logging().getLogger('ace')

def get_distance(value1, value2):
    v1_x = value1['left'] + (value1['right']-value1['left'])/2
    v1_y = value1['top'] + (value1['bottom']-value1['top'])/2

    v2_x = value2['x'] + (value2['width'])/2
    v2_y = value2['y'] + (value2['height'])/2

    return sqrt((v1_x - v2_x)*(v1_x - v2_x)+(v1_y - v2_y)*(v1_y - v2_y))


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

def find_in_ocr(ocr_data, value):
    """

    :param ocr_data:
    :param value:
    :return:
    """

    to_return = []
    try:
        if value["regex"] == 'true':
          regex = re.compile(value['keyword'])
          for ind, page_data in enumerate(ocr_data):
              for data in page_data:
                  if regex.search(data['word']) != None:
                      to_return.append([ind, data])
    except:
        for ind, page_data in enumerate(ocr_data):
            for data in page_data:
                for val in value['keyword'].split(' '):
                    ratio = SequenceMatcher(None, val, data['word']).ratio()
                    if ratio > thres:
                        to_return.append([ind, data])

    return to_return

def option_selector(options, value):

    min_m = 8888888
    page = 0

    for data in options:
        ind ,option = data
        temp_m = get_distance(option, value['scope'])
        if temp_m < min_m:
            nearest_option = option
            min_m = temp_m
            page = ind

    return nearest_option, page


def compare_func(data, T,L,R,B):
    left_match = data['left'] + int(0.25 * data['width']) >= L
    right_match = data['right'] - int(0.25 * data['width']) <= R
    top_match = data['top'] + int(0.5 * data['height']) >= T
    bottom_match = data['bottom'] - int(0.5 * data['height']) <= B
    if (left_match and right_match and top_match and bottom_match):
        return  True
    else:
        if percentage_inside((L,R,B,T),(data['left'], data['right'],data['bottom'],data['top'])) > thres:
            return True
        return  False

def crop_ocr_data(ocr_data, box):
  logging('Box:', box)
  cropped_ocr_data = []
  # for page in ocr_data:
  for data in ocr_data:
      if compare_func(data,box['top'], box['left'], box['right'], box['bottom']):
          cropped_ocr_data.append(data)

  return cropped_ocr_data

def get_box(option, value):
  box = {}

  logging.debug('Option:', option)
  if 'left' in option:
    box['top'] = option['left']['top']
    box['bottom'] = option['left']['bottom']
  elif 'right' in option:
    box['top'] = option['right']['top']
    box['bottom'] = option['right']['bottom']
  else:
    box['top'] = value['scope']['y']
    box['bottom'] = value['scope']['y'] + value['scope']['height'] 


  if 'top' in option:
    box['left'] = option['top']['left']
    box['right'] = option['top']['right']
  elif 'bottom' in option:
    box['left'] = option['bottom']['left']
    box['right'] = option['bottom']['right']
  else:
    box['left'] = value['scope']['x']
    box['right'] = value['scope']['x'] + value['scope']['width']


  return box

def expand_coord(boundary, train_data, boundaries):
  
  trained_width = train_data['right'] - train_data['left']
  trained_height = train_data['bottom'] - train_data['top']

  current_width = boundary['right'] - boundary['left']
  current_height = boundary['bottom'] - boundary['top']

  if current_height < trained_height:
    padding = int((trained_height - current_height)/2)
    boundary['top'] -= padding
    boundary['bottom'] += padding

  if current_width < trained_width:
    padding = int((trained_width - current_width)/2)
    boundary['right'] += padding
    boundary['left'] -= padding
  
  return boundary



def field_extract_with_cell_method(ocr_data,cell_data,value):
  try:
    extraction_help_data = cell_data
    boundaries = ['left', 'top', 'right', 'bottom']
    option = {}
    for boundary in boundaries:
      try:
        # boundary_words = find_in_ocr(ocr_data, extraction_help_data[boundary])
        # option[boundary], _ = option_selector(boundary_words, extraction_help_data[boundary])
        # print('')
        option[boundary] = needle_in_a_haystack(extraction_help_data[boundary]['keyword'],ocr_data,extraction_help_data[boundary])
        option[boundary] = expand_coord(option[boundary], extraction_help_data[boundary], boundaries)
      except:
        logging.exception('Something went wrong in field_extract_with_cell_method. Check trace.')
  except:
    option = {}
  logging.debug('Option',option)
  box = get_box(option, value)
  logging.debug('Box',box)
  return crop_ocr_data(ocr_data, box)


# trained = {"value":{"bottom":326,"keyword":"","left":456,"page":"0","right":491,"scope":{"height":18,"width":35,"x":456,"y":308},"top":308,"validation":"", "cell_data" : {"left":{"bottom":323,"keyword":"Total","left":43,"page":"0","right":72,"scope":{"height":14,"width":29,"x":43,"y":309},"top":309,"validation":""},"top":{"bottom":151,"keyword":"Taxable Amt","left":453,"page":"0","right":492,"scope":{"height":22,"width":39,"x":453,"y":129},"top":129,"validation":""}}}}
# trained = {"value":{"bottom":326,"keyword":"","left":456,"page":"0","right":491,"scope":{"height":18,"width":35,"x":456,"y":308},"top":308,"validation":""}}
# print(field_extract_with_cell_method(ocr_data, trained))
