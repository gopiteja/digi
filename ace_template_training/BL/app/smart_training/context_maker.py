try:
    from app.smart_training.utils import calculate_limit
    from app.smart_training.utils import ocrDataLocal
except:
    from smart_training.utils import calculate_limit
    from smart_training.utils import ocrDataLocal

def add_padding_to_scope(scope, padding, max_width, max_height):
    """
    """
    context_coords = {}

    left = scope['left'] - padding/2
    context_coords['left'] = max(left, 0)

    top = scope['top'] - padding/2
    context_coords['top'] = max(top,0)

    right = scope['right'] + padding/2
    context_coords['right'] = min(right, max_width)

    bottom = scope['bottom'] + padding/2
    context_coords['bottom'] = min(bottom, max_height)

    context_coords['width'] = context_coords['right'] - context_coords['left']

    context_coords['height'] = context_coords['bottom'] - context_coords['top']    


    return context_coords



def get_context(ocr_data, scope, page_no):
    """

    """

    max_width ,max_height = calculate_limit(ocr_data, page_no)
    context_coords = add_padding_to_scope(scope, 50, max_width, max_height)
    padding = 50
    # context_coords = resize_coordinates(additional_field_info['coordinates'][0],resize_factor)
    context_scope = {
                        'x':context_coords['left'],
                        'y':context_coords['top'],
                        'width':context_coords['width'] ,
                        'height':context_coords['height']
                    }
    box = {}
    box['width'] = context_coords['width']
    box['height'] = context_coords['height']
    relative = {
                    'left': scope['left'] - context_scope['x'],
                    'top': scope['top'] - context_scope['y']
               }
    # print('context_coords',context_coords)
    # print('ocr_data type',type(ocr_data))
    context_ocr_data = ocrDataLocal(
                            context_coords['top'], 
                            context_coords['left'],
                            context_coords['right'],
                            context_coords['bottom'],
                            ocr_data[int(page_no)]
                        )

    context_text = ' '.join([word['word'] for word in context_ocr_data])
    context_key_field_info = {
                                'text': context_text,
                                'box': box,
                                'relative':relative
                             }

    return context_key_field_info