import traceback
from fuzzywuzzy import fuzz

try:
    from app.ace_logger import Logging
except:
    from ace_logger import Logging

logging = Logging()

def get_context_box(ocr_data, keyword_boxes, context):
    context_box_dict = None
    high_fuzzy_score = 0
    context_match_threshold = 70

    # Loop through all keywords found
    for keyword_data in keyword_boxes:
        # Get Context box relative to keyword box
        context_box = context['box']
        relative_coords = context['relative']
        logging.debug(f'keyword_data - {keyword_data}')

        L = keyword_data['left'] - relative_coords['left']
        T = keyword_data['top'] - relative_coords['top']
        R = L + context_box['width']
        B = T + context_box['height']

        # Find OCR data inside the context box
        ocr_box_data = []
        logging.debug(f'context_box - {context_box}')
        logging.debug(f'L: {L}')
        logging.debug(f'R: {R}')
        logging.debug(f'T: {T}')
        logging.debug(f'B: {B}')

        for data in ocr_data:
            if  (data['left'] + int(0.5 * data['width']) >= L
                    and data['right'] - int(0.5 * data['width']) <= R
                    and data['top'] + int(0.5 * data['height']) >= T
                    and data['bottom'] - int(0.5 * data['height']) <= B):
                ocr_box_data.append(data)

        # Compare text from OCR data with context text
        ocr_box_text = ' '.join([data['word'] for data in ocr_box_data])
        context_text = context['text']
        
        # If score is greater than some percentage get return the box, else return None
        logging.debug(f'ocr_box_text - {ocr_box_text}')
        logging.debug(f'context_text- {context_text}')
        try:
            fuzzy_score = fuzz.partial_ratio(ocr_box_text, context_text)
        except:
            logging.exception('Something went wrong getting fuzzy match.')
            continue
        
        logging.debug(f'Fuzzy Score: {fuzzy_score}')
        logging.debug(f'Highest Fuzzy Score: {high_fuzzy_score}')
        logging.debug(f'Context Match Threshold: {context_match_threshold}')
        
        if fuzzy_score >= context_match_threshold and fuzzy_score >= high_fuzzy_score:
            context_box_dict = {
                'x': L,
                'y': T,
                'width': context_box['width'],
                'height': context_box['height']
            }
            high_fuzzy_score = fuzzy_score

    return context_box_dict
