import math



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
    elif (word_r <= box_r and word_r >= mid_x + margin_wid):
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


def calulcate_centroid(coordinates):
    """
    Author : Akshat Goyal

    Args ;
        coordinates :
            {
                'left' : int,
                'right' : int,
                'top' : int,
                'bottom' : int
            }

    Return :
        {
            'x':mid_x, 
            'y':mid_y
        }
    """
    mid_x = coordinates['left'] + (coordinates['right'] - coordinates['left'])/2
    mid_y = coordinates['top'] + (coordinates['bottom'] - coordinates['top'])/2

    return {'x':mid_x, 'y':mid_y}

def centroid_hunt(word_list):
    """
    Author : Akshat Goyal

    Args:
        word_list :
            [
                {
                    'word' : str,
                    coordinates
                }
            ]

    Return:
        [
            {
                ''
                'mid_x':int
                'mid_y':int
            }
        ]

    """
    for word in word_list:
        temp = calulcate_centroid(word)
        word['mid_x'] = int(temp['x'])
        word['mid_y'] = int(temp['y'])

    return word_list

def caculate_dis(box1, box2):
    mid1 = (
                box1['left']+int(abs(box1['left']-box1['right'])/2),
                box1['top']+int(abs(box1['top']-box1['bottom'])/2)
            )
    mid2 = (
                box2['left']+int(abs(box2['left']-box2['right'])/2),
                box2['top']+int(abs(box2['top']-box2['bottom'])/2)
            )

    dist = math.hypot(mid2[0] - mid1[0], mid2[1] - mid1[1])

    return dist

def validate_fields(extracted_data, field_validation):
    print(f'Validating fields...')

    if not field_validation:
        print(
            f' - Not in field configuration! Check configuration immediately! Skipping')
    else:
        field_pattern = field_validation['pattern']
        if field_pattern is None:
            print(f' - No pattern configured. Skipping.')
        else:
            print(f' - Applying regex: `{field_pattern}`')

            matches = re.findall(
                field_pattern, raw_value.replace('suspicious', ''))

            if matches:
                print(f' - Matches found: {matches}')
                extracted_data = matches[0]
            else:
                print(f' - No pattern found for `{field}`.')
                extracted_data = ''

    return extracted_data

def find_closest_mate(lonely_soul, world, no_of_mate=1, field_validation=None):
    """
    Author : Akshat Goyal

    Args:
        lonely_soul :
            {
                'word' : str,
                coordinates,
                'mid_x' : int,
                'mid_y' : int
            }
        world:
            [
                {
                    'word' : str,
                    coordinates,
                    'mid_x' : int,
                    'mid_y' : int
                }
            ]
        no_of_mate (int) : how many closest mate to find

    return: list of closest mate
        [
            {
                'word' : str,
                coordinates,
                'mid_x' : int,
                'mid_y' : int
            },

        ]
    """
    connection_of_soul = []

    for idx, soul in enumerate(world):
        dis = caculate_dis(soul, lonely_soul)
        connection_of_soul.append([dis, idx])

    sorted_soul = sorted(connection_of_soul,key=lambda x: x[0])

    mate_location = [idx for dis, idx in sorted_soul[:no_of_mate]]

    closest_souls = []

    for location in mate_location:
        closest_souls.append(world[location])

    if closest_souls and no_of_mate==1:
        closest_souls = [validate_fields(closest_souls[0], field_validation)]

    return closest_souls




def ocrDataLocal(T,L,R,B,ocrData):
    '''
        Parameters : Boundaries of Scope
        Output     : Returns that part of ocrdata which is confined within given boundaries
    '''
    ocrDataLocal = []
    for data in ocrData:
        width = data['right'] - data['left']
        height = data['bottom'] - data['top']
        if  (data['left'] + int(0.25*width)  >= L
            and data['right'] - int(0.25*width) <= R
            and data['top'] + int(0.5*height) >= T
            and data['bottom'] - int(0.5*height) <= B ):
            ocrDataLocal.append(data)
    return ocrDataLocal

def resize_coordinates(box,resize_factor):

    box["width"] = int(box["width"] / resize_factor)
    box["height"] = int(box["height"] / resize_factor)
    box["y"] = int(box["y"] / resize_factor)
    box["x"] = int(box["x"] / resize_factor)

    return box

def merge_coord(prev, nex):
    if prev['top'] > nex['top']:
        prev['top'] = nex['top']

    if prev['left'] > nex['left']:
        prev['left'] = nex['left']

    if prev['right'] < nex['right']:
        prev['right'] = nex['right']

    if prev['bottom'] < nex['bottom']:
        prev['bottom'] = nex['bottom']

    return prev

def make_scope(values):
    """
    """
    try:
        if values:
            scope = dict(values[-1])
        else:
            scope = {}
    except:
        scope = {}

    for value in values[:-1]:
        scope = merge_coord(scope, value)

    return scope

def calculate_limit(ocr_data_whole, page_no=None):
    #todo Write code for this
    right = 0
    bottom = 0

    if page_no is not None:
        ocr_data = ocr_data_whole[page_no]
    else:
        ocr_data = ocr_data_whole

    for ocr in ocr_data:
        if right < ocr['right']:
            right = ocr['right']
        if bottom < ocr['bottom']:
            bottom = ocr['bottom']

    return right, bottom

def get_rel_info(box1,box2,direction=None):
    """
    box1 : key
    box2 : value
    """
    if 'left' not in box1 or 'left' not in box2:
        return {}

    mid1 = (box1['left']+int(abs(box1['left']-box1['right'])/2),box1['top']+int(abs(box1['top']-box1['bottom'])/2))
    mid2 = (box2['left']+int(abs(box2['left']-box2['right'])/2),box2['top']+int(abs(box2['top']-box2['bottom'])/2))

    dist = math.hypot(mid2[0] - mid1[0], mid2[1] - mid1[1])
    try:
        angle = math.atan((mid2[1]-mid1[1])/(mid2[0] - mid1[0]))
        angle = math.degrees(angle)
    except:
        #value at top
        if mid2[1] < mid1[1]:
            angle = -90
        else:
            angle = 90

    if direction:
        if int(angle) in range(-30,30):
            return 'left'
        elif int(angle) in range(150,180) or int(angle) in range(-180,-150):
            return 'right'
        elif int(angle) in range(-120,-60):
            return 'bottom'
        else:
            return 'top'

    print({'dist':dist,'angle':angle})
    return {'dist':dist,'angle':angle}