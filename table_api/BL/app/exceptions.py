
from difflib import SequenceMatcher
import re
try:
    from app.ace_logger import Logging
except:
    from ace_logger import Logging

logging = Logging().getLogger('ace')

'''
twins- Helper function which return whether two words are close based
        on SequenceMatcher
    Parameters : two words to be validated
    output     : True if twins
'''
def twins(word1,word2):
    twin_threshold = 0.90
    if SequenceMatcher(None,word1.lower(),word2.lower()).ratio() > twin_threshold:
        return True
    return False


'''
Header exceptions
    Parameters : header_list_json - Table Header Words List from json train data
                 header_words_detected - Words detected in the invoice as header
    Output     : 70% of number of headers found with that of header words from json_data
                and 30% of average of match score of each individual header
'''

def header_exceptions(header_list_json,header_words_detected):
    headers_found = len(header_words_detected)/len(header_list_json)
    scores = []
    for header_actual in  header_list_json:
        for header_detected in header_words_detected:
            if twins(header_actual,header_detected):
                header_actual = re.sub(' +',' ',header_actual)
                logging.debug('Header')
                logging.debug(f"{header_actual},':',{header_detected}")
                scores.append(SequenceMatcher(lambda x: x == " ",header_actual.lower(),header_detected.lower()).ratio())
    avg_scores = sum(scores)/len(scores)

    score = 0.7*headers_found + 0.3*avg_scores

    return score

'''
Vertical lines Exceptions
    Parameters : vers - Vertical Lines drawn after corrections and everything
                 table_ocr - ocr data for table part
    Output     : score based on num of vertical lines correctly drawn which
                dont cut any of words in the table
'''
def vertical_lines_exceptions(vers,table_ocr):

    vertical_coords = []
    for each_vertical in vers:
        vertical_coords.append(each_vertical[0][0])
    breaks = 0
    for each_word in table_ocr:
        for vertical in vertical_coords:
            if(each_word['left']<vertical and each_word['right']>vertical):
                breaks += 1
                break
    score = (len(vertical_coords) - breaks)/len(vertical_coords)

    return score

# def horizontal_lines_exceptions():
#

'''
Footer exceptions
    Parameters : footer_json - Footer from json train data
                 footer_found - Footer returned from match list function
    Output     : score based on SequenceMatcher
'''
def footer_exceptions(footer_json,footer_found):
    logging.debug('footer_json',footer_json)
    logging.debug('footer_found',footer_found)
    score = SequenceMatcher(None,footer_json.lower(),footer_found.lower()).ratio()

    return score
