from math import sin, cos, radians, pi
import math
from  difflib import SequenceMatcher
import itertools

try:
    from app.ace_logger import Logging
except:
    from ace_logger import Logging

logging = Logging()

def ocrDataLocal(T,L,R,B,ocrData):
    '''
        Parameters : Boundaries of Scope
        Output     : Returns that part of ocrdata which is confined within given boundaries
    '''
    ocrDataLocal = []
    for data in ocrData:
        if  (data['left'] + int(0.25*data['width'])  >= L
            and data['right'] - int(0.25*data['width']) <= R
            and data['top'] + int(0.5*data['height']) >= T
            and data['bottom'] - int(0.5*data['height']) <= B ):
            ocrDataLocal.append(data)
    return ocrDataLocal

def sort_ocr(data):
    data = sorted(data, key = lambda i: i['top'])
    for i in range(len(data)-1):
        if abs(data[i]['top'] - data[i+1]['top']) <4 :
            data[i+1]['top'] = data[i]['top']
    data = sorted(data, key = lambda i: (i['top'], i['left']))
    return data


def needle_in_a_haystack(needle,haystack,proximity=None):

    words = needle.split()

    occurences = {}
    for hay in haystack:
        for word in words:
            if SequenceMatcher(None,hay['word'],word).ratio()>0.8:
                if word not in occurences:
                    occurences[word] = [hay]
                else:
                    occurences[word].append(hay)
    logging.debug(f'Occurences: - {occurences}')
    all_combos = list(itertools.product(*occurences.values()))
    final_matches = []
    for combo in all_combos:
        min_left = min([word['left'] for word in combo])
        min_top = min([word['top'] for word in combo])
        max_right = max([word['right'] for word in combo])
        max_bottom = max([word['bottom'] for word in combo])
        combo_proxim = ocrDataLocal(min_top,min_left,max_right,max_bottom,haystack)
        combo_proxim = sort_ocr(combo_proxim)
        combo_proxim_str = ' '.join([word['word'] for word in combo_proxim])
        logging.debug(f'Combo Proxim: - {combo_proxim_str}')
        match_score = SequenceMatcher(None,combo_proxim_str.lower(),needle.lower()).ratio()
        if match_score > 0.8:
            area = (max_bottom-min_top)*(max_right-min_left)
            midpoint = (min_left+int((max_right-min_left)/2),min_top+int((max_bottom-min_top)/2))
            final_matches.append({'words':combo,'top':min_top,'left':min_left,'right':max_right,'bottom':max_bottom,'score':match_score,'area':area,'midpoint':midpoint})

            # final_matches.append({'words':combo,'top':min_top,'left':min_left,'right':max_right,'bottom':max_bottom,'score':match_score,'area':area})
  
    if proximity:
        return get_best_match(proximity,final_matches)
  
    final_matches = sorted(final_matches , key = lambda x:(x['area'],-x['score']))
    try:
        best_match = final_matches[0]
        if final_matches[0]['score'] > 0.6:
            return best_match
    except:
        return {}

    return {}


def get_rel_info(box1,box2):
    mid1 = (box1['left']+int(abs(box1['left']-box1['right'])/2),box1['top']+int(abs(box1['top']-box1['bottom'])/2))
    mid2 = (box2['left']+int(abs(box2['left']-box2['right'])/2),box2['top']+int(abs(box2['top']-box2['bottom'])/2))

    dist = math.hypot(mid2[0] - mid1[0], mid2[1] - mid1[1])
    angle = math.atan((mid2[1]-mid1[1])/(mid2[0] - mid1[0]))
    angle = abs(math.degrees(angle))
    angle = math.degrees(angle)

    logging.debug({'dist':dist,'angle':angle})
    return {'dist':dist,'angle':angle}


def point_pos(x0, y0, d, theta):
    theta = abs(theta)
    theta_rad = radians(theta)
    return int(x0 + d*round(cos(theta_rad))), int(y0 + d*round(sin(theta_rad)))

def get_best_match(inp,keysDict):

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
    logging.debug("Key distance dictionary: %s" % DistList)
    closestKey=min(DistList)
    minIndex=DistList.index(closestKey)
    return keysDict[minIndex]
