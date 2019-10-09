# -*- coding: utf-8 -*-
"""
Created on Fri Jul 20 13:02:31 2018

@author: Amith-Algonox (No more author but has helped)
@real_authors: Ashyam, Ashish and Bhavik worked under the supervision of Abhishek Rana and Priyatham Katta
"""
from mpu import datastructures

import argparse
import copy
import json
import pandas as pd
import os
import re
import regex
import requests
import math
import glob
import difflib
import threading
import traceback

from datetime import datetime
from dateutil.parser import parse
from flask import Flask, request, jsonify
from flask_cors import CORS
from nltk import edit_distance
from py_zipkin.zipkin import zipkin_span, ZipkinAttrs, create_http_headers_for_new_span

from db_utils import DB
from producer import produce
from ace_logger import Logging

try:
    # from app.db_utils import DB
    from app.extracto_utils import *
    from app.context_field_utils import get_context_box
    from app.multi_key_utils import *
    from app.finding_field_without_keyword import find_field
    from app.string_matching import convert_ocrs_to_char_dict_only_al_num
    from app.string_matching import string_match_python
    from app.string_matching import remove_all_except_al_num
    from app.string_matching import merge_coord
    from app.string_matching import make_keyword_string
    from app.break_boundaries import break_boundaries
    from app.extract_checkbox import *

    with open('app/parameters.json') as f:
        parameters = json.loads(f.read())
    from app import app
except:
    from extracto_utils import *
    from producer import produce
    from context_field_utils import get_context_box
    from multi_key_utils import *
    from finding_field_without_keyword import find_field
    from string_matching import convert_ocrs_to_char_dict_only_al_num
    from string_matching import string_match_python
    from string_matching import remove_all_except_al_num
    from string_matching import merge_coord
    from string_matching import make_keyword_string
    from break_boundaries import break_boundaries
    from ace_logger import Logging

    with open('parameters.json') as f:
        parameters = json.loads(f.read())
    app = Flask(__name__)
    CORS(app)

logging = Logging()

# the multiplier for the distance between the keyword threshold
DISTANCE_THRESHOLD = 2


def http_transport(encoded_span):
    body = encoded_span
    requests.post(
        'http://servicebridge:5002/zipkin',
        data=body,
        headers={'Content-Type': 'application/x-thrift'}, )


@zipkin_span(service_name='extraction_api', span_name='validate_fields_')
def validate_fields_(raw, field_data):
    '''
    Validate extracted fields (if there are any validations for the field)
    '''
    for field in raw:
        if 'amount' in field.lower() and parameters['clean'] == "yes":
            logging.debug("Cleaning amounts..")
            val_list = raw[field].split()
            logging.debug("Val List", val_list)

            temp = []
            for val in val_list:
                if val.isalpha():
                    pass
                else:
                    temp.append(val.replace(',', ''))

            logging.debug("Cleaned:", temp)
            raw[field] = ' '.join(temp)

        for fte, fte_data in field_data.items():
            try:
                validation = fte_data['validation'].replace('\\\\', '\\')
                # Apply validation to the ones which have validation
                if fte == field and validation:
                    if field.lower() == 'pin code':
                        raw[field] = re.validate(raw[field].replace(' ', ''), validation)
                    else:
                        raw[field] = re.validate(raw[field], validation)
                if "date" in field.lower() and raw[field]:
                    try:
                        raw[field] = parse(raw[field].replace('suspicious', '').replace('validation failed!', ''),
                                           dayfirst=True).strftime("%d-%b-%y")
                    except Exception as e:
                        logging.debug("error in date conversion", e)
                        pass
                if "invoice number" in field.lower() and raw[field]:
                    try:
                        raw[field] = raw[field].replace(' ', '')
                    except:
                        pass
                if "gstin" in field.lower() and raw[field]:
                    pattern = r"\d{2}[a-zA-Z]{5}\d{4}[a-zA-Z]{1}\d{1}[a-zA-Z]{1}\w"
                    try:
                        valid_gstin = re.findall(pattern, raw[field].replace('suspicious', '').replace(' ', ''))[-1]
                        if valid_gstin:
                            raw[field] = valid_gstin
                    except:
                        raw[field] = raw[field].replace(' ', '') + 'suspicious'
                if "po number" in field.lower() and raw[field]:
                    try:
                        raw[field] = raw[field][:10]
                    except:
                        raw[field] = raw[field] + 'suspicious'
                if field.lower() in ['invoice base amount', 'invoice total']:
                    try:
                        raw[field] = float(''.join(re.findall(r'[0-9\.]', raw[field].replace('suspicious', ''))))
                    except:
                        raw[field] = raw[field] + 'suspicious'
            except:
                pass
    return raw


@zipkin_span(service_name='extraction_api', span_name='extraction_with_keyword')
def extraction_with_keyword(ocr_data, keyword, scope, fte, fte_data, key_page, ocr_length, context=None,
                            key_val_meta=None, field_conf_threshold=100, pre_process_char=[]):
    logging.info('Extracting with keyword')
    logging.info(fte)
    logging.info(fte_data)
    val = ''
    word_highlights = {}
    method_used = ''

    if (key_page > (ocr_length - 1)):  # if new invoice does not have the trained page number
        for i in range(0, ocr_length):
            val, word_highlights, method_used = keyword_selector(ocr_data, keyword, scope, fte_data, i, context,
                                                                 key_val_meta=key_val_meta,
                                                                 field_conf_threshold=field_conf_threshold)

            if val:
                break
    else:
        # first check page in which field trained
        val, word_highlights, method_used = keyword_selector(ocr_data, keyword, scope, fte_data, key_page, context,
                                                             key_val_meta=key_val_meta,
                                                             field_conf_threshold=field_conf_threshold)

        if not val:  # if value not found in trained page, loop through other pages except trained page
            for i in range(0, ocr_length):
                if i != key_page:
                    val, word_highlights, method_used = keyword_selector(ocr_data, keyword, scope, fte_data, i, context,
                                                                         key_val_meta=key_val_meta,
                                                                         field_conf_threshold=field_conf_threshold)

                    if val:
                        break

    if val:
        pass
    else:
        try:
            if context:
                val, word_highlights, method_used = keyword_selector_inside_word(ocr_data, keyword, scope, fte_data,
                                                                                 key_page, context,
                                                                                 field_conf_threshold=field_conf_threshold)
            else:
                # val,word_highlights=closest_field_extract(ocr_data[i],keyword,scope,fte_data,
                # field_conf_threshold=field_conf_threshold)
                val, word_highlights = closest_field_extract(ocr_data[key_page], keyword, scope, fte_data)
                # val,word_highlights=keyword_selector_inside_word(ocr_data,keyword,scope,fte_data,key_page,
                # field_conf_threshold=field_conf_threshold)
        except:
            logging.warning("Closest not found")
            pass

    if not val:
        # this is when there are special character in either of keyword or ocr but not in other
        val, word_highlights, method_used = keyword_selector_cluster_method(
            ocr_data, keyword, scope,
            fte_data, i,
            key_val_meta=key_val_meta,
            field_conf_threshold=field_conf_threshold,
            pre_process_char=pre_process_char
        )
    if val:
        for word in keyword.split():
            if word in val.split()[0]:
                val = val.replace(word, '')
    return val, word_highlights, method_used


@zipkin_span(service_name='extraction_api', span_name='update_queue_trace')
def update_queue_trace(queue_db, case_id, latest):
    queue_trace_q = "SELECT * FROM `trace_info` WHERE `case_id`=%s"
    queue_trace_df = queue_db.execute(queue_trace_q, params=[case_id])

    if queue_trace_df.empty:
        message = f' - No such case ID `{case_id}` in `trace_info`.'
        logging.error(message)
        return {'flag': False, 'message': message}
    # Updating Queue Name trace
    try:
        queue_trace = list(queue_trace_df.queue_trace)[0]
    except:
        queue_trace = ''
    if queue_trace:
        queue_trace += ',' + latest
    else:
        queue_trace = latest

    # Updating last_updated_time&date

    try:
        last_updated_dates = list(queue_trace_df.last_updated_dates)[0]
    except:
        last_updated_dates = ''
    if last_updated_dates:
        last_updated_dates += ',' + datetime.now().strftime(r'%d/%m/%Y %H:%M:%S')
    else:
        last_updated_dates = datetime.now().strftime(r'%d/%m/%Y %H:%M:%S')

    update = {'queue_trace': queue_trace}
    where = {'case_id': case_id}
    update_q = "UPDATE `trace_info` SET `queue_trace`=%s, `last_updated_dates`=%s WHERE `case_id`=%s"
    queue_db.execute(update_q, params=[queue_trace, last_updated_dates, case_id])

    return {'flag': True, 'message': 'Updated Queue Trace'}


@zipkin_span(service_name='extraction_api', span_name='value_extract')
def value_extract(result, api=False, retrained=False):
    if result is None:
        return {'flag': False}

    case_id = result['case_id']
    tenant_id = result['tenant_id']
    is_field_exception = False

    queues_db_config = {
        'host': os.environ['HOST_IP'],
        'user': os.environ['LOCAL_DB_USER'],
        'password': os.environ['LOCAL_DB_PASSWORD'],
        'port': os.environ['LOCAL_DB_PORT'],
        'tenant_id': tenant_id
    }
    queues_db = DB('queues', **queues_db_config)
    # queues_db = DB('queues')

    stats_db_config = {
        'host': os.environ['HOST_IP'],
        'user': os.environ['LOCAL_DB_USER'],
        'password': os.environ['LOCAL_DB_PASSWORD'],
        'port': os.environ['LOCAL_DB_PORT'],
        'tenant_id': tenant_id
    }

    stats_db = DB('stats', **stats_db_config)

    # process_queue = queues_db.get_all('process_queue')
    process_queue = queues_db.get_all('process_queue', discard=['ocr_text', 'xml_data'])

    latest_process_queue = queues_db.get_latest(process_queue, 'case_id', 'created_date')
    process_file = latest_process_queue.loc[latest_process_queue['case_id'] == case_id]
    ocr_data = []
    if not process_file.empty:
        logging.debug(process_file)
        template_name = process_file.template_name.values[0]
        if template_name is None or not template_name:
            message = 'Template name is none/empty string'
            logging.debug(message)
            if not api:
                return {'flag': False, 'message': message}

        query = 'SELECT * FROM `ocr_info` WHERE `case_id`=%s'
        params = [case_id]
        ocr_info = queues_db.execute(query, params=params)
        try:
            ocr_data = json.loads(json.loads(list(ocr_info.ocr_data)[0]))
        except:
            ocr_data = json.loads(list(ocr_info.ocr_data)[0])

        if ocr_data is None or not ocr_data:
            message = 'OCR data is none/empty string'
            logging.debug(message)
            return {'flag': False, 'message': message}
    else:
        message = f'case_id - {case_id} does not exist'
        return {'flag': False, 'message': message}

    if api:
        field_data = result['field_data']
        try:
            checkbox_data = result['checkbox_data']
            logging.info(f'checkbox dataaa `{checkbox_data}`')
        except Exception as e:
            pass
    else:
        # * Get trained info of the template from the template_db
        template_db_config = {
            'host': os.environ['HOST_IP'],
            'user': os.environ['LOCAL_DB_USER'],
            'password': os.environ['LOCAL_DB_PASSWORD'],
            'port': os.environ['LOCAL_DB_PORT'],
            'tenant_id': tenant_id
        }
        templates_db = DB('template_db', **template_db_config)
        # templates_db = DB('template_db')

        trained_info_data = templates_db.get_all('trained_info')
        template_info_df = trained_info_data.loc[trained_info_data['template_name'] == template_name]

        # * Get fields to extract (fte) from the trained info
        field_data = json.loads(template_info_df.field_data.values[0])

        try:
            checkbox_data = json.loads(template_info_df.checkbox_data.values[0])
        except Exception as e:
            pass

        remove_keys = ['header_ocr', 'footer_ocr', 'address_ocr']
        [field_data.pop(key, None) for key in remove_keys]  # Remove unnecessary keys

    # No Template, No Extraction
    ocr_length = len(ocr_data)
    word_highlights = {}
    output = {}
    output_ = {'method_used': {}}

    # to save the method used

    pre_processed_char = []
    for page in ocr_data:
        page = sort_ocr(page)
        char_index_list, haystack = convert_ocrs_to_char_dict_only_al_num(page)
        pre_processed_char.append([char_index_list, haystack])

    # * Get the OCR tab ID
    tab_df = queues_db.get_all('tab_definition')
    ocr_tab = tab_df.loc[tab_df['source'] == 'ocr']
    # tab_id = 1

    # * Get the OCR fields
    ocr_fields = queues_db.get_all('field_definition')
    ocr_fields_list = ocr_fields.to_dict('records')
    ocr_fields_dict = {}

    for ocr_field_data in ocr_fields_list:
        ocr_fields_dict[ocr_field_data['display_name']] = ocr_field_data
    logging.debug(f'OCR Fields: {ocr_fields_dict}')

    for fte, fte_data in field_data.items():
        # * Get fields' confidence threshold
        if fte in ocr_fields_dict:
            field_conf_threshold = ocr_fields_dict[fte]['confidence_threshold']
        else:
            field_conf_threshold = 100

        logging.debug(f'Confidence for `{fte}` is {field_conf_threshold}')

        if 'value' in fte_data:
            output[fte] = fte_data['value']

        val = ''
        if fte == 'Invoice Category':
            output_[fte] = fte_data['keyword']
            output[fte] = fte_data['keyword']
        elif 'boundary_data' in fte_data and fte_data['boundary_data']:
            logging.debug("Trying to use FUED")
            # print('in boundary data')

            val, _ = find_field(fte, field_data, 'template_name', ocr_data)
            if val:
                try:
                    output[fte] = val.strip()
                except:
                    output[fte] = val
                output_['method_used'][fte] = 'FEUD'
                output_[fte] = val
                extract = False
        if not val:
            logging.debug("Unfortunately FUED was unsuccessful")
            logging.debug("But fear not keywords is here to rescue")
            try:
                scope = json.loads(fte_data['scope'])
                scope_value = json.loads(fte_data['scope_value'])
            except:
                scope = fte_data['scope']
                scope_value = fte_data['scope_value']
            keyword = fte_data['keyword']
            page_no = int(fte_data['page'])
            split_check = fte_data.pop('split_check', '')
            validation = fte_data.pop('validation', '')
            key_val_meta = fte_data.pop('key_val_meta', None)
            multi_key_field_info = fte_data.pop('multi_key_field_info', {})
            context_key_field_info = fte_data.pop('context_key_field_info', {})
            if fte not in ['header_ocr', 'footer_ocr', 'address_ocr']:
                # If keyword is there then get the nearest keyword to the trained
                # keyword and use relative position of that keyword to get the value
                if keyword and scope:
                    key_page = int(page_no)
                    try:
                        val, word_highlights[fte], method_used = extraction_with_keyword(
                            ocr_data,
                            keyword,
                            scope,
                            fte,
                            fte_data,
                            key_page,
                            ocr_length,
                            context_key_field_info,
                            key_val_meta=key_val_meta,
                            field_conf_threshold=field_conf_threshold,
                            pre_process_char=pre_processed_char
                        )
                        # updating method used
                        output_['method_used'][fte] = method_used
                    except Exception as e:
                        val = ''
                        logging.exception(
                            'Error in extracting for field:{} keyword:{} due to {}'.format(fte, keyword, e))

                # 2d method
                elif not keyword and multi_key_field_info:
                    try:
                        predicted_val = field_extract_with_cell_method(ocr_data[page_no],
                                                                       multi_key_field_info['cell_data'], fte_data)
                        logging.debug(predicted_val)
                        val = ' '.join([word['word'] for word in predicted_val])
                        word_highlights[fte] = merge_fields(predicted_val, page_no)

                        output_['method_used'][fte] = '2D'

                    except Exception as e:
                        logging.debug('Failed to predict using multikey method')
                        val = ''

                else:
                    # No keyword
                    field_value = []
                    temp_highlight = []

                    try:
                        box_t = scope_value['y']
                        box_r = scope_value['x'] + scope_value['width']
                        box_b = scope_value['y'] + scope_value['height']
                        box_l = scope_value['x']
                    except:
                        box_t = scope_value['top']
                        box_r = scope_value['right']
                        box_b = scope_value['bottom']
                        box_l = scope_value['left']

                    box = [box_l, box_r, box_b, box_t]

                    sorted_data = (sorted(ocr_data[page_no], key=lambda i: (i['top'], i['left'])))
                    for ocr_word in sorted_data:
                        word_t = ocr_word['top']
                        word_r = ocr_word['left'] + ocr_word['width']
                        word_b = ocr_word['bottom']
                        word_l = ocr_word['left']

                        word_box = [word_l, word_r, word_b, word_t]

                        if percentage_inside(box, word_box) > parameters['overlap_threshold']:
                            if ocr_word['confidence'] < field_conf_threshold:
                                field_value.append('suspicious' + ocr_word['word'])
                            else:
                                field_value.append(ocr_word['word'])
                            temp_highlight.append(ocr_word)
                    val = ' '.join(field_value)
                    word_highlights[fte] = merge_fields(temp_highlight, page_number=page_no)
                    output_['method_used'][fte] = 'COORD'

                try:
                    output[fte] = val.strip()
                    if fte == 'Invoice Number' and val:
                        output[fte] = output[fte].replace(" ", "")
                except:
                    output[fte] = val
                    if fte == 'Invoice Number' and val:
                        output[fte] = output[fte].replace(" ", "")
                output_[fte] = val
    logging.info(f'Output: {output}')
    logging.info(f'Output_: {output_}')
    logging.info(f'word_highlight: `{word_highlights}`')
    # try:
    #     word_highlights, output_ = checkbox_selector(case_id, checkbox_data, ocr_data, word_highlights, output, output_)
    # except Exception as e:
    #     pass

    # Check if there are any suspicious value
    if 'suspicious' in json.dumps(output_):
        logging.debug(f"{case_id} -  has suspicious fields")
        is_field_exception = True
    else:
        logging.debug(f"{case_id} - has no suspicious fields")

    ocr_fields_definition = queues_db.get_all('field_definition')
    for field_name, field_value in output_.items():
        is_field_exception = True
        field_definition = ocr_fields_definition.loc[ocr_fields_definition['display_name'] == field_name]

        if field_definition.empty:
            logging.debug(f'Skipping `{field_name}` because its not found `field_definition')
            continue

        if field_value is None and list(field_definition.mandatory)[0]:
            is_field_exception = True
            break
        elif list(field_definition.mandatory)[0] and not field_value.strip():
            is_field_exception = True
            break

    # Find date related fields and change the format of the value to a standard one
    logging.debug(f'Changing date formats in extracted fields...')
    standard_format = r'%Y-%m-%d'
    for field_name, field_value in output_.items():
        field_suspicious_check = False

        if not field_value:
            continue

        if 'suspicious' in field_value:
            field_suspicious_check = True

        if 'date' in field_name.lower().split():
            if field_value is not None or field_value:
                new_field_value = field_value
                raw_field_value = field_value.replace('suspicious', '').replace(' ', '')
                try:
                    parsed_date = parse(raw_field_value, fuzzy=True, dayfirst=True)
                except ValueError:
                    logging.exception(f'Error occured while parsing date field `{field_name}`:`{field_value}`.')
                    parsed_date = None
                if parsed_date is not None:

                    if 'suspicious' in field_value:
                        new_field_value = 'suspicious' + parsed_date.strftime(standard_format)
                    else:
                        new_field_value = parsed_date.strftime(standard_format)
                output_[field_name] = new_field_value.replace('suspicious', '')
        if "invoice number" in field_name.lower() and output_[field_name]:
            try:
                output_[field_name] = output_[field_name].replace(' ', '')
            except:
                pass
        if "gstin" in field_name.lower() and field_value:
            pattern = r"\d{2}[a-zA-Z]{5}\d{4}[a-zA-Z]{1}\d{1}[a-zA-Z]{1}\w"
            try:
                valid_gstin = re.findall(pattern, field_value.replace('suspicious', '').replace(' ', ''))[-1]
                if valid_gstin:
                    output_[field_name] = valid_gstin
            except:
                output_[field_name] = field_value.replace(' ', '') + 'suspicious'
        if "po number" in field_name.lower():
            if field_value:
                if field_suspicious_check:
                    field_value = field_value.replace('suspicious', '')
                    try:
                        field_value = field_value.replace(':', '').replace('.', '')
                        output_[field_name] = field_value[:10] + 'suspicious'
                    except Exception as e:
                        output_[field_name] = field_value + 'suspicious'
                else:
                    try:
                        output_[field_name] = field_value[:10]
                    except Exception as e:
                        output_[field_name] = field_value + 'suspicious'

        if field_name.lower() in ['invoice base amount', 'invoice total']:
            if field_suspicious_check:
                try:
                    output_[field_name] = str(
                        float(''.join(re.findall(r'[0-9\.]', field_value.replace('suspicious', ''))))) + 'suspicious'
                except:
                    if field_value:
                        output_[field_name] = field_value.replace(' ', '') + 'suspicious'
            else:
                try:
                    output_[field_name] = str(
                        float(''.join(re.findall(r'[0-9\.]', field_value.replace('suspicious', '')))))
                except:
                    if field_value:
                        output_[field_name] = field_value.replace(' ', '') + 'suspicious'

    logging.debug('\nExtracted data:')
    logging.debug(json.dumps(output_, indent=2))

    # * Field Validation
    try:
        logging.debug(f' - Checkbox data: `{checkbox_data}`')
        logging.debug(f' - Output before validation: `{output_}`')
        for fiel, out_ in output_.items():
            if fiel in checkbox_data.keys():
                continue
            else:
                output_ = validate_fields(output_, ocr_fields_dict)
        logging.debug(f' - UI Output: `{output_}`')
    except:
        logging.exception(f'Error in validation. Skipping validation.')

    if api:
        logging.info('Its API fields')
        output_.pop('method_used', 0)
        return output_

    # Update queue of the file. Field exceptions if there are any suspicious value else Verify queue.
    is_field_exception = False

    query = 'SELECT * FROM `workflow_definition`, `queue_definition` WHERE ' \
            '`workflow_definition`.`queue_id`=`queue_definition`.`id` '
    template_exc_wf = queues_db.execute(query)
    workflow_frame = template_exc_wf.loc[template_exc_wf['name'] == 'Template Exceptions']

    queue_id = list(workflow_frame['queue_id'])[0]
    move_to_queue_id = list(workflow_frame['move_to'])[0]

    query = 'SELECT * FROM `queue_definition` WHERE `id`=%s'
    move_to_queue_df = queues_db.execute(query, params=[move_to_queue_id])
    move_to_queue = list(move_to_queue_df['unique_name'])[0]

    query = 'SELECT * FROM `queue_definition` WHERE `id`=%s'
    queue_df = queues_db.execute(query, params=[queue_id])
    queue_unique_name = list(move_to_queue_df['unique_name'])[0]

    if os.environ['MODE'] == 'Test':
        output_.pop('method_used', 0)

        return_data = {
            'flag': True,
            'send_data': {
                'case_id': case_id,
                'template_name': template_name,
                'data': output_
            }
        }

        return return_data

    updated_queue = queue_unique_name if is_field_exception else move_to_queue
    query = "UPDATE `process_queue` SET `queue`=%s WHERE `case_id`=%s"
    params = [updated_queue, case_id]
    queues_db.execute(query, params=params)
    audit_data = {
        "type": "update", "last_modified_by": "Extraction", "table_name": "process_queue",
        "reference_column": "case_id",
        "reference_value": case_id, "changed_data": json.dumps({"queue": updated_queue})
    }
    stats_db.insert_dict(audit_data, 'audit')
    logging.debug(f'Updated queue of case ID `{case_id}` to `{updated_queue}`')

    update_queue_trace(queues_db, case_id, updated_queue)

    # * Add the fields to the OCR table of extraction DB
    logging.debug('Adding extracted data to the database')
    extraction_db_config = {
        'host': os.environ['HOST_IP'],
        'user': os.environ['LOCAL_DB_USER'],
        'password': os.environ['LOCAL_DB_PASSWORD'],
        'port': os.environ['LOCAL_DB_PORT'],
        'tenant_id': tenant_id
    }
    extraction_db = DB('extraction', **extraction_db_config)
    # extraction_db = DB('extraction')

    # serializing so that it can be stored
    output_['method_used'] = json.dumps(output_['method_used'])

    if retrained:
        logging.debug(f'Applying retrained info for case `{case_id}`. Updating OCR table.')
        update_status = extraction_db.update('ocr', update=output_, where={'case_id': case_id})
        audit_data = {
            "type": "update", "last_modified_by": "Extraction", "table_name": "ocr", "reference_column": "case_id",
            "reference_value": case_id, "changed_data": json.dumps(output_)
        }
        stats_db.insert_dict(audit_data, 'audit')

        if update_status:
            logging.debug('Updated successfully.')
        else:
            logging.error('Update error.')

        common_db_config = {
            'host': os.environ['HOST_IP'],
            'port': os.environ['LOCAL_DB_PORT'],
            'user': os.environ['LOCAL_DB_USER'],
            'password': os.environ['LOCAL_DB_PASSWORD'],
            'tenant_id': tenant_id
        }
        kafka_db = DB('kafka', **common_db_config)
        # kafka_db = DB('kafka')

        message_flow = kafka_db.get_all('message_flow')
        listen_to_topic_df = message_flow.loc[message_flow['listen_to_topic'] == 'extract']
        send_to_topic = list(listen_to_topic_df.send_to_topic)[0]

        produce(send_to_topic, {'case_id': case_id, 'template_name': template_name})

        output_.pop('method_used', 0)
        return output_

    columns = []
    values = []
    for key, value in output_.items():
        if not key:
            continue
        columns.append(f'`{key}`')
        try:
            values.append(value.strip())
        except:
            # if value is empty .strip() throws error. So appending eemptystring
            # to avoid Column count doesn't match error in sql while inserting
            values.append('')
    logging.debug(f'values `{values}`')
    logging.debug(f'columns `{columns}`')
    query_columns = ', '.join(columns)  # Comma separated column names for the query
    value_placeholders = ', '.join(['%s'] * len(values))  # Placeholders (%s) for the values in the query

    query = f'INSERT INTO `ocr` (`case_id`, `highlight`, {query_columns}) VALUES (%s, %s, {value_placeholders})'
    params = [case_id, json.dumps(word_highlights)] + values
    try:
        extraction_db.execute(query, params=params)
    except Exception as e:
        message = f'Error inserting extracted data into the database. {e}'
        logging.exception(message)
        return {'flag': False, 'message': message}

    try:
        query = f"Select id, communication_date_time, communication_date_time_bot from process_queue where case_id = '{case_id}'"
        communication_date_bot = list(queues_db.execute(query).communication_date_time_bot)[0]
        communication_date = list(queues_db.execute(query).communication_date_time)[0]

        query = f"update ocr set Fax_unique_id = '{case_id}', communication_date_time_bot = '{communication_date_bot}', Communication_date_time = '{communication_date}' where case_id = '{case_id}' "
        extraction_db.execute(query)
    except:
        pass

    return_data = {
        'flag': True,
        'send_data': {
            'case_id': case_id,
            'template_name': template_name
        }
    }

    return return_data


@zipkin_span(service_name='extraction_api', span_name='validate_fields')
def validate_fields(extracted_data, ocr_fields_config):
    logging.debug(f'\nValidating fields...')

    # Iterate through each field and check if there is any validation required
    for field, raw_value in extracted_data.items():
        logging.debug(f'`{field}`:')
        if field not in ocr_fields_config:
            logging.debug(
                f' - Not in field configuration! Check configuration immediately! Skipping')
            continue

        field_pattern = ocr_fields_config[field]['pattern']
        if field_pattern is None:
            logging.debug(f' - No pattern configured. Skipping.')
            continue
        else:
            logging.debug(f' - Applying regex: `{field_pattern}`')

        matches = re.findall(
            field_pattern, raw_value.replace('suspicious', ''))

        if matches:
            logging.debug(f' - Matches found: {matches}')
            extracted_data[field] = matches[0]
        else:
            logging.debug(f' - No pattern found for `{field}`.')

    return extracted_data


@zipkin_span(service_name='extraction_api', span_name='field_extract')
def field_extract(page_data, query, sort=True):
    for page_number, data in enumerate(page_data):
        if sort:
            data = sorted(data, key=lambda i: (i['top']))
        for i in range(len(data) - 1):
            if abs(data[i]['top'] - data[i + 1]['top']) < 5:
                data[i + 1]['top'] = data[i]['top']

        if sort:
            sorted_data = (sorted(data, key=lambda i: (i['top'], i['left'])))
        else:
            sorted_data = data
        field_tokens = query.lower().split()
        length = len(field_tokens)

        for line_no, _ in enumerate(sorted_data[:-length]):
            flag = True
            index = 0
            while (flag == True and index < length):
                if field_tokens[index].lower() not in sorted_data[line_no + index]['word'].lower():
                    flag = False
                index += 1

            if flag == True and index == length:
                return merge_fields(sorted_data[line_no: line_no + length], page_number)


@zipkin_span(service_name='extraction_api', span_name='closest_field_extract')
def closest_field_extract(ocr_og, keyword_sentence, scope, field_data, field_conf_threshold=100):
    highlight = {}
    temp_highlight = []
    size_increment = 100  # Constant value of expanding of scope field box
    sort = True
    right_offset = 0
    page_data = copy.deepcopy(ocr_og)

    original_field_tokens = keyword_sentence.lower().split()  # All original keywords with special chars
    field_tokens = []
    for index, val in enumerate(original_field_tokens):
        if not re.match(r'^[_\W]+$', val):
            field_tokens.append(val)  # add only non special characters to field kw list
            right_offset += 7  # because special character removed, keyword's right should not reduce
    length = len(field_tokens)
    logging.debug(f"No. of keywords to be found: {length} ")

    logging.debug(f"Final field tokens: {field_tokens}")
    logging.debug(f"Original field tokens : {original_field_tokens}")
    scope_page_data = []

    if scope:
        box_t = scope['y'] - size_increment
        box_r = (scope['x'] + scope['width']) + size_increment
        box_b = (scope['y'] + scope['height']) + size_increment
        box_l = scope['x'] - size_increment

        box = [box_l, box_r, box_b, box_t]
        logging.debug(f"Expanded scope box {box} ")
        for data in page_data:
            word_t = data['top']
            word_r = data['left'] + data['width']
            word_b = data['bottom']
            word_l = data['left']

            word_box = [word_l, word_r, word_b, word_t]
            if percentage_inside(box, word_box) > parameters['overlap_threshold']:
                scope_page_data.append(data)

    if sort:
        data = sorted(scope_page_data, key=lambda i: (i['top']))
        logging.debug(f"Data: {data}")
    else:
        data = scope_page_data

    for i in range(len(data) - 1):
        if abs(data[i]['top'] - data[i + 1]['top']) < 5:
            data[i + 1]['top'] = data[i]['top']

    if sort:
        sorted_data = (sorted(data, key=lambda i: (i['top'], i['left'])))
    else:
        sorted_data = data

    with_special = copy.deepcopy(sorted_data)  # store original ocr words in scope box

    for i in scope_page_data:
        if not re.match(r'^[_\W]+$', i["word"]):
            i["word"] = re.sub('[^ a-zA-Z0-9]', '', i["word"])  # remove special character from scope box
    logging.debug(f"Sorted data: {sorted_data}")
    logging.debug(f"With_special {with_special} ")

    og_words = []  # to store all closest keywords found,in original format,with special characters
    for line_no, _ in enumerate(sorted_data):
        flag = True
        index = 0
        while (flag == True and index < length):

            kw = field_tokens[index].lower()
            ocr_word = sorted_data[line_no + index]['word'].lower()
            ed = edit_distance(kw, ocr_word)
            if not ((ed <= 1 and 1 < len(ocr_word) <= 4) or (ed <= 2 and 10 >= len(ocr_word) > 4) or (
                    ed <= 3 and len(ocr_word) > 10)):
                flag = False
            else:
                og_words.append(with_special[line_no + index]['word'].lower())
            index += 1
        if flag == True and index == length:
            logging.debug(f"\nKeywords coords to merge:\n {sorted_data[line_no: line_no + length]}")
            result = merge_fields(sorted_data[line_no: line_no + length])  # get combined coordinates
            logging.debug(f"\nMerged kw box\n {result} ")
            result["left"] = result["x"]
            result["top"] = result["y"]
            result["bottom"] = result["y"] + result["height"]

            rel_top = field_data['top']
            rel_bottom = field_data['bottom']
            rel_left = field_data['left']
            rel_right = field_data['right']

            box_top = result['top'] - rel_top
            box_bottom = result['bottom'] + rel_bottom
            box_left = result['left'] - rel_left
            box_right = result['right'] + rel_right + right_offset  # offset is imp

            box = [box_left, box_right, box_bottom, box_top]
            logging.debug(f"Box to extract {box}")
            word = []

            for w in ocr_og:
                word_box = [w['left'], w['right'], w['bottom'], w['top']]
                logging.debug(f"WORD_BOX {word_box} IS for {w['word']}")
                if (percentage_inside(box, word_box) > parameters['overlap_threshold']
                        and w['word'].lower() not in og_words + original_field_tokens):
                    if w['confidence'] < field_conf_threshold:
                        word.append('suspicious' + w['word'])
                        # word.append(data['word'])
                    else:
                        word.append(w['word'])
                    temp_highlight.append(w)
            highlight = merge_fields(temp_highlight)
            logging.debug(f"\nOriginal ocr keywords {og_words}")

            return [' '.join(word), highlight]
    return None, None


@zipkin_span(service_name='extraction_api', span_name='merge_fields')
def merge_fields(box_list, page_number=0):
    '''
    Merge 2 or more words and get combined coordinates
    '''
    if box_list and type(box_list[0]) is dict:
        min_left = min([word['left'] for word in box_list])
        min_top = min([word['top'] for word in box_list])
        max_right = max([word['right'] for word in box_list])
        max_bottom = max([word['bottom'] for word in box_list])

        max_height = max_bottom - min_top
        total_width = max_right - min_left
        word = ' '.join([word['word'] for word in box_list])

        return {'height': max_height, 'width': total_width, 'y': min_top, 'x': min_left, 'right': max_right,
                'word': word.strip(), 'page': page_number}
    else:
        return {}


@zipkin_span(service_name='extraction_api', span_name='add_field_value')
def add_field_value(field_value, box, word, rel_coord, ocr_word, parameters, offset_percentage=90):
    if (percentage_inside(word, box) > offset_percentage):
        if 'validation' not in rel_coord and ocr_word['confidence'] < parameters['ocr_confidence']:
            field_value.append('suspicious' + ocr_word['word'])
            # field_value.append(ocr_word['word'])
        else:
            field_value.append(ocr_word['word'])
    return field_value


@zipkin_span(service_name='extraction_api', span_name='percentage_inside')
def percentage_inside(box, word):
    '''
    Get how much part of the word is inside the box
    '''
    box_l, box_r, box_b, box_t = box
    word_l, word_r, word_b, word_t = word
    area_of_word = (word_r - word_l) * (word_b - word_t)
    area_of_intersection = get_area_intersection(box, word, area_of_word)
    try:
        return area_of_intersection / area_of_word
    except:
        return 0


@zipkin_span(service_name='extraction_api', span_name='get_area_intersection')
def get_area_intersection(box, word, area_of_word):
    box_l, box_r, box_b, box_t = box
    word_l, word_r, word_b, word_t = word

    mid_x = box_l + (box_r - box_l) / 2
    mid_y = box_t + (box_b - box_t) / 2

    width = box_r - box_l
    height = box_b - box_t

    margin_wid = (width * 5) / 100
    margin_hig = (height * 5) / 100

    # this means that word is can be too big for the box
    if (word_l >= box_l and word_l <= mid_x + margin_wid):
        dx = word_r - word_l
    else:
        dx = min(word_r, box_r) - max(word_l, box_l)

    if (word_t >= box_t and word_t <= mid_y + margin_hig):
        dy = word_b - word_t
    else:
        dy = min(word_b, box_b) - max(word_t, box_t)

    if (dx >= 0) and (dy >= 0):
        return dx * dy

    return 0


@zipkin_span(service_name='extraction_api', span_name='sort_ocr')
def sort_ocr(data):
    data = sorted(data, key=lambda i: i['top'])
    for i in range(len(data) - 1):
        data[i]['word'] = data[i]['word'].strip()
        data[i + 1]['word'] = data[i + 1]['word'].strip()
        if abs(data[i]['top'] - data[i + 1]['top']) < 6:
            data[i + 1]['top'] = data[i]['top']
    data = sorted(data, key=lambda i: (i['top'], i['left']))
    return data


def caculate_dis(box1, box2):
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


def ocrDataLocal_special(T, L, R, B, ocrData):
    '''
        Parameters : Boundaries of Scope
        Output     : Returns that part of ocrdata which is confined within given boundaries
    '''

    ocrDataLocal = []
    for data in ocrData:
        logging.debug(data)

        if (data['left'] + int(0.2 * data['width']) >= L
                and data['left'] <= R
                and data['top'] + int(0.1 * data['height']) >= T
                and data['bottom'] - int(0.1 * data['height']) <= B):
            ocrDataLocal.append(data)
    return ocrDataLocal


def value_split_method(key_val_meta, keycoord, ocr_data, page_no):
    """
    now the split method in this new shiny package
    """
    # return '', {}
    logging.debug('using value split method')
    logging.debug(f'keycoord - {keycoord}')
    logging.debug(f'key_val_meta - {key_val_meta}')

    key_mid_x = keycoord['left'] + (keycoord['right'] - keycoord['left']) / 2

    key_mid_y = keycoord['top'] + (keycoord['bottom'] - keycoord['top']) / 2

    value_midpoint = point_pos(key_mid_x, key_mid_y, key_val_meta['dist'], key_val_meta['angle'])
    value_box_padding = parameters['value_box_padding']
    value_box = {
        'top': value_midpoint[1] - int((key_val_meta['bottom'] - key_val_meta['top']) / 2) - value_box_padding,
        'bottom': value_midpoint[1] + int((key_val_meta['bottom'] - key_val_meta['top']) / 2) + value_box_padding,
        'left': value_midpoint[0] - int((key_val_meta['right'] - key_val_meta['left']) / 2) - value_box_padding,
        'right': value_midpoint[0] + int((key_val_meta['right'] - key_val_meta['left']) / 2) + value_box_padding
    }
    logging.debug(f'value_box - {value_box}')

    value_ocr = ocrDataLocal_special(value_box['top'], value_box['left'], value_box['right'], value_box['bottom'],
                                     ocr_data[page_no])
    # print('value_ocr',value_ocr)
    # print('value_text',' '.join([word['word'] for word in value_ocr]))
    val = ' '.join([word['word'] for word in value_ocr])
    highlight = {
        'word': val,
        'x': value_box['left'], 'right': value_box['right'], 'width': value_box['right'] - value_box['left'],
        'height': value_box['bottom'] - value_box['top'], 'y': value_box['top'],
        'page': page_no
    }

    return val, highlight


def find_value_using_box(keyList, ocr_data, page_no, box, field_data, field_conf_threshold, parameters):
    word = []
    temp_highlight = []

    logging.debug(box)

    for data in ocr_data[page_no]:
        if (data['left'] + int(parameters['box_left_margin_ratio'] * data['width']) >= box[0]
                and data['right'] - int(parameters['box_right_margin_ratio'] * data['width']) <= box[1]
                and data['top'] + int(parameters['box_top_margin_ratio'] * data['height']) >= box[3]
                and data['bottom'] - int(parameters['box_bottom_margin_ratio'] * data['height']) <= box[2]):
            logging.debug('keyword select word - ', data['word'])
            word_box = [data['left'], data['right'], data['bottom'], data['top']]
            logging.debug('word box - ', word_box)
            if (percentage_inside(box, word_box) > parameters['overlap_threshold']
                    and data['word'] not in keyList):
                if 'junk' in field_data:
                    data['word'] = data['word'].replace(field_data['junk'], '')
                if data['confidence'] < field_conf_threshold:
                    word.append('suspicious' + data['word'])
                else:
                    word.append(data['word'])
                temp_highlight.append(data)
    highlight = merge_fields(temp_highlight, page_no)

    if not word:
        word, temp_highlight = break_boundaries(ocr_data[page_no], field_data, box, field_conf_threshold)
        highlight = merge_fields(temp_highlight, page_no)

    val = ' '.join(word).strip()

    return [val, highlight]


def actual_clustering(keywords_list, keyCords_list):
    smallest_list_coord = keyCords_list[0]

    coord_clusters = []
    word_clusters = []

    for idx, coord in enumerate(smallest_list_coord):
        cluster_coord = [coord]
        word_cluster = [keywords_list[0][idx]]

        for rem_idx, remaining_coords in enumerate(keyCords_list[1:]):
            all_dist = []
            width = []
            height = []
            for remaining_coord in remaining_coords:
                tot_dis = 0
                for point in cluster_coord:
                    tot_dis += caculate_dis(point, remaining_coord)
                    width.append(point['right'] - point['left'])
                    height.append(point['bottom'] - point['top'])
                all_dist.append(tot_dis)

            min_dis = min(all_dist)

            max_width = max(width)
            max_height = max(height)

            threshold = calculate_threhold(max_width, max_height)

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

    logging.debug(f'keywords_list {keywords_list}')
    logging.debug(f'keyCords_list {keyCords_list}')

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
            keyCords = merge_coord(keyCords, point)

            prospective_keyword = to_return_word_cluster[idx][cluster_idx]
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
    try:
        inpX = (inp['x'] + inp['x'] + inp['width']) / 2
        inpY = (inp['y'] + inp['y'] + inp['height']) / 2
    except:
        inpX = (inp['left'] + inp['right']) / 2
        inpY = (inp['top'] + inp['bottom']) / 2

    keyList, keyCords, starting = get_definite_checkpoint(keywords_list, keyCords_list)

    # if there are multiple cluster then this will take care of it
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

    keyList = keyList[minIndex]

    keyCords = keyCords[minIndex]

    return keyList, keyCords


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


def compute_all_key_list_coord(keyList, char_index_list, haystack):
    """
    """

    keyCords_list = []
    keywords_list = []
    counter = 0

    for key in keyList:
        key_param = remove_all_except_al_num(key)
        keyCords, keywords = string_match_python(key_param, char_index_list, haystack)
        # keyCords, keywords = string_match_naive(key_param, ocr_data[page_no], pre_process_char[page_no][0], pre_process_char[page_no][1])
        if not keywords:
            counter = 0
            break
        counter = len(keyCords)
        keywords_list.append(keywords)
        keyCords_list.append(keyCords)

    keywords_list.sort(key=len)
    keyCords_list.sort(key=len)

    return keyCords_list, keywords_list, counter


def keyword_selector_cluster_method(ocr_data, keyword, inp, field_data, page, context=None, key_val_meta=None,
                                    field_conf_threshold=100, pre_process_char=[]):
    '''
    Author : Akshat Goyal

    Algo:
    1. concatinate the ocr into string and then search keyword. 
    2. If multiple location of keyword then cluster based on a distance threshold 
    3. Take the biggest cluster. 
    4. If more than one biggest cluster then chose one closest to context.
    '''
    highlight = {}
    temp_highlight = []

    method_used = ''

    rel_top = field_data['top']
    rel_bottom = field_data['bottom']
    rel_left = field_data['left']
    rel_right = field_data['right']

    keyList = keyword.split()

    # print("\nKeyList:\n%s" % keyList)
    keyLength = len(keyword)
    page_no = page

    keyword = remove_all_except_al_num(keyword)

    keyCords = []

    # get the pre process character list for the page no
    char_index_list, haystack = get_pre_process_char(pre_process_char, ocr_data, page_no)

    # Search OCR for the key pattern
    # print('keywords - ', keyList)
    ori_keyList = keyList

    keyCords_list, keywords_list, counter = compute_all_key_list_coord(keyList, char_index_list, haystack)

    if (counter > 0):
        keyList, keyCords = get_key_list_coord(keywords_list, keyCords_list, inp)

        keyList = ' '.join(keyList)

        # print(keyList)
        # print(keyCords)
        box_top = keyCords['top'] + rel_top
        box_bottom = keyCords['bottom'] + rel_bottom
        box_left = keyCords['left'] + rel_left
        box_right = keyCords['right'] + rel_right

        val = ''
        if key_val_meta:
            val, highlight = value_split_method(key_val_meta, keyCords, ocr_data, page)
            if val:
                method_used = 'VALUE_SPLIT'

        if not val:

            box = [box_left, box_right, box_bottom, box_top]

            val, highlight = find_value_using_box(keyList, ocr_data, page_no, box, field_data, field_conf_threshold,
                                                  parameters)

            if val:
                method_used = 'KV'

        return [val, highlight, method_used]


    else:
        # print('Exact Keyword not found in OCR')
        return [''.strip(), highlight, method_used]


@zipkin_span(service_name='extraction_api', span_name='keyword_selector')
def keyword_selector(ocr_data, keyword, inp, field_data, page, context=None, key_val_meta=None,
                     field_conf_threshold=100):
    '''
    Get closest keyword to the trained keyword.
    '''
    logging.debug(field_data)
    # Find_box value
    highlight = {}
    temp_highlight = []

    method_used = ''

    rel_top = field_data['top']
    rel_bottom = field_data['bottom']
    rel_left = field_data['left']
    rel_right = field_data['right']

    keyList = keyword.split()
    # logging.debug("\nKeyList:\n%s" % keyList)
    keyLength = len(keyList)
    page_no = page

    ocr_data[page_no] = sort_ocr(ocr_data[page_no])

    keyCords = []
    counter = 0
    if (keyLength > 0):
        # Search OCR for the key pattern
        for i, data in enumerate(ocr_data[page_no]):
            data['word'] = data['word'].strip()
            ocr_length = len(ocr_data[page_no])
            regex = re.compile(r'[@_!#$%^&*()<>?/\|}{~:]')
            check = False
            if (data['word'] == keyList[0] or (regex.search(data['word']) is not None and re.search('[a-zA-Z]',
                                                                                                    data[
                                                                                                        'word'].replace(
                                                                                                        keyList[0],
                                                                                                        '')) is not None and
                                               keyList[0] in data['word'])):
                if (keyLength > 1):
                    for x in range(0, keyLength):
                        if i + x >= ocr_length:
                            check = False
                            break
                        else:
                            if (ocr_data[page_no][i + x]['word'] == keyList[x] or (
                                    regex.search(ocr_data[page_no][i + x]['word']) is not None and re.search('[a-zA-Z]',
                                                                                                             data[
                                                                                                                 'word'].replace(
                                                                                                                 keyList[
                                                                                                                     x],
                                                                                                                 '')) is None and
                                    keyList[x] in ocr_data[page_no][i + x]['word'])):
                                check = True
                            else:
                                check = False
                                break
                else:
                    check = True

            tempCords = [{}] * 1
            if (check):
                logging.debug(data['word'])
                counter = counter + 1
                top = 1000
                bottom = 0
                # Left is of the first word
                if (data['word'] == keyList[0] or (regex.search(data['word']) != None and re.search('[a-zA-Z]', data[
                    'word'].replace(keyword, '')) == None and keyList[0] in data['word'])):
                    tempCords[0]['left'] = data['left']
                    for x in range(0, keyLength):
                        # Right is of the last word
                        if (x == (keyLength - 1)):
                            tempCords[0]['right'] = ocr_data[page_no][i + x]['right']

                        # If multi word key
                        if (keyLength > 1):
                            if (ocr_data[page_no][i + x]['word'] == keyList[x]):
                                logging.debug("%s" % keyList[x])
                                if (ocr_data[page_no][i + x]['top'] < top):
                                    top = ocr_data[page_no][i + x]['top']
                                if (ocr_data[page_no][i + x]['bottom'] > bottom):
                                    bottom = ocr_data[page_no][i + x]['bottom']
                        else:
                            top = data['top']
                            bottom = data['bottom']

                    tempCords[0]['top'] = top
                    tempCords[0]['bottom'] = bottom
                    logging.debug(tempCords)
                    keyCords.append(tempCords[0])

    logging.debug("No of occurences of %s: %s" % (keyword, counter))
    if context is not None:
        logging.debug('Context available. Finding context box.')
        # Find context box and get new scope box
        context = get_context_box(ocr_data[page_no], keyCords, context)
        if context:
            inp = context
            logging.debug(f'contect box found - {context}')

    if (counter > 0):
        keysDict = keyCords
        inpX = (inp['y'] + inp['y'] + inp['height']) / 2
        inpY = (inp['x'] + inp['x'] + inp['width']) / 2
        DistList = []
        for i, values in enumerate(keysDict):
            # Store all keywords,distances in a Dict
            # Get midpoint of the input
            midheight = ((keysDict[i]['top'] + keysDict[i]['bottom']) / 2)
            midwidth = ((keysDict[i]['left'] + keysDict[i]['right']) / 2)
            x = abs(midheight - inpX)
            y = abs(midwidth - inpY)
            dist = math.sqrt((x * x) + (y * y))
            DistList.append(round(dist, 2))
        logging.debug("Key distance dictionary: %s" % DistList)
        try:
            closestKey = min(DistList)
        except:
            return ['', {}]
        minIndex = DistList.index(closestKey)

        box_top = keyCords[minIndex]['top'] + rel_top
        box_bottom = keyCords[minIndex]['bottom'] + rel_bottom
        box_left = keyCords[minIndex]['left'] + rel_left
        box_right = keyCords[minIndex]['right'] + rel_right

        keyList = ' '.join(keyList)
        logging.debug(keyList)

        val = ''
        if key_val_meta:
            val, highlight = value_split_method(key_val_meta, keyCords[minIndex], ocr_data, page)
            if val:
                logging.debug(f'value found by value split method - {val}')
                method_used = 'VALUE_SPLIT'

        if not val:
            logging.debug('now using our plain old box method')
            box = [box_left, box_right, box_bottom, box_top]
            logging.debug(f'box - {box}')

            val, highlight = find_value_using_box(keyList, ocr_data, page_no, box, field_data, field_conf_threshold,
                                                  parameters)

            if val:
                method_used = 'KV'

        return [val, highlight, method_used]


    else:
        logging.warning('Exact Keyword not found in OCR')
        return [''.strip(), highlight, method_used]


@zipkin_span(service_name='extraction_api', span_name='keyword_selector_inside_word')
def keyword_selector_inside_word(ocr_data, keyword, inp, field_data, page, context=None, field_conf_threshold=100):
    '''
    Get closest keyword to the trained keyword.
    '''
    logging.info(field_data)
    # Find_box value
    highlight = {}
    temp_highlight = []

    method_used = ''

    rel_top = field_data['top']
    rel_bottom = field_data['bottom']
    rel_left = field_data['left']
    rel_right = field_data['right']

    keyList = keyword.split()
    logging.debug("\nKeyList:\n%s" % keyList)
    keyLength = len(keyList)
    logging.debug(f'key list length - {keyLength}')
    page_no = page

    keyCords = []
    counter = 0
    if (keyLength > 0):
        # Search OCR for the key pattern
        for i, data in enumerate(ocr_data[page_no]):
            ocr_length = len(ocr_data[page_no])
            regex = re.compile(r'[@_!#$%^&*()<>?/\|}{~:]')
            check = False
            # if data['word'] == 'Fori':
            #     logging.debug('yes hihi')
            #     logging.debug(data['word'])
            #     logging.debug(keyList[0] in data['word'])
            #     logging.debug(regex.search(data['word'])!=None)
            #     logging.debug(re.search('[a-zA-Z]', data['word'].replace(keyList[0],''))==None)
            if (data['word'] == keyList[0] or (regex.search(data['word']) != None and re.search('[a-zA-Z]',
                                                                                                data['word'].replace(
                                                                                                    keyList[0],
                                                                                                    '')) == None and
                                               keyList[0] in data['word']) or keyList[0] in data['word']):
                if (keyLength > 1):
                    x = 0
                    key_words_idx = 0
                    while (key_words_idx < keyLength and x < keyLength):
                        logging.debug(ocr_data[page_no][i + x]['word'])
                        if i + x >= ocr_length:
                            check = False
                            break
                        else:
                            if (ocr_data[page_no][i + x]['word'] == keyList[key_words_idx] or (
                                    regex.search(ocr_data[page_no][i + x]['word']) != None and re.search('[a-zA-Z]',
                                                                                                         data[
                                                                                                             'word'].replace(
                                                                                                             keyList[
                                                                                                                 x],
                                                                                                             '')) == None and
                                    keyList[key_words_idx] in ocr_data[page_no][i + x]['word'])):
                                check = True
                            elif (keyList[key_words_idx] in ocr_data[page_no][i + x]['word']):
                                check = True
                                if key_words_idx + 1 < keyLength and keyList[key_words_idx + 1] in \
                                        ocr_data[page_no][i + x]['word']:
                                    x -= 1
                            else:
                                check = False
                                break
                        x += 1
                        key_words_idx += 1
                else:
                    check = True

            tempCords = [{}] * 1
            if (check):
                logging.debug(data['word'])
                counter = counter + 1
                top = 1000
                bottom = 0
                # Left is of the first word
                if (data['word'] == keyList[0] or (regex.search(data['word']) != None and re.search('[a-zA-Z]', data[
                    'word'].replace(keyword, '')) == None and keyList[0] in data['word']) or keyList[0] in data[
                    'word']):
                    tempCords[0]['left'] = data['left']
                    x = 0
                    key_words_idx = 0
                    while (key_words_idx < keyLength and x < keyLength):
                        # Right is of the last word
                        if (key_words_idx == (keyLength - 1)):
                            logging.debug('word', ocr_data[page_no][i + x])
                            tempCords[0]['right'] = ocr_data[page_no][i + x]['right']

                        # If multi word key
                        if (keyLength > 1):
                            if (ocr_data[page_no][i + x]['word'] == keyList[key_words_idx] or keyList[key_words_idx] in
                                    ocr_data[page_no][i + x]['word']):
                                if (ocr_data[page_no][i + x]['top'] < top):
                                    top = ocr_data[page_no][i + x]['top']
                                if (ocr_data[page_no][i + x]['bottom'] > bottom):
                                    bottom = ocr_data[page_no][i + x]['bottom']
                        else:
                            top = data['top']
                            bottom = data['bottom']

                        if (keyList[key_words_idx] in ocr_data[page_no][i + x]['word']):
                            if key_words_idx + 1 < keyLength and keyList[key_words_idx + 1] in ocr_data[page_no][i + x][
                                'word']:
                                x -= 1
                        x += 1
                        key_words_idx += 1

                    tempCords[0]['top'] = top
                    tempCords[0]['bottom'] = bottom
                    keyCords.append(tempCords[0])

    logging.debug("No of occurences of %s: %s" % (keyword, counter))
    if context is not None:
        logging.debug('Context available. Finding context box.')
        # Find context box and get new scope box
        inp = get_context_box(ocr_data[page_no], keyCords, context)

    if (counter > 0):
        keysDict = keyCords
        inpX = (inp['y'] + inp['y'] + inp['height']) / 2
        inpY = (inp['x'] + inp['x'] + inp['width']) / 2
        DistList = []
        for i, values in enumerate(keysDict):
            # Store all keywords,distances in a Dict
            # Get midpoint of the input
            midheight = ((keysDict[i]['top'] + keysDict[i]['bottom']) / 2)
            midwidth = ((keysDict[i]['left'] + keysDict[i]['right']) / 2)
            x = abs(midheight - inpX)
            y = abs(midwidth - inpY)
            dist = math.sqrt((x * x) + (y * y))
            DistList.append(round(dist, 2))
        logging.debug("\nKey distance dictionary: %s" % DistList)
        closestKey = min(DistList)
        minIndex = DistList.index(closestKey)

        box_top = keyCords[minIndex]['top'] + rel_top
        box_bottom = keyCords[minIndex]['bottom'] + rel_bottom
        box_left = keyCords[minIndex]['left'] + rel_left
        box_right = keyCords[minIndex]['right'] + rel_right

        keyList = ' '.join(keyList)
        val = ''
        if key_val_meta:
            val, highlight = value_split_method(key_val_meta, keyCords[minIndex], ocr_data, page)
            if val:
                method_used = 'VALUE_SPLIT'

        if not val:
            box = [box_left, box_right, box_bottom, box_top]

            val, highlight = find_value_using_box(keyList, ocr_data, page_no, box, field_data, field_conf_threshold,
                                                  parameters)

            if val:
                method_used = 'KV'

        return [val, highlight, method_used]


    else:
        logging.warning('Exact Keyword not found in OCR')
        return [''.strip(), highlight, '']


@app.route('/extract_for_template', methods=['POST', 'GET'])
def extract_for_template():
    with zipkin_span(
            service_name='extraction_api',
            span_name='extract_for_template',
            transport_handler=http_transport,
            port=5010,
            sample_rate=0.5, ):
        try:
            data = request.json
            logging.debug(f'UI data: {data}')

            # Get vendor name from UI
            template_name = data.pop('template_name', None)
            retrained_case = data.pop('case_id', None)
            tenant_id = data.pop('tenant_id', None)

            if template_name is None or not template_name:
                message = f'Template name is not provided or is empty string.'
                return jsonify({'flag': False, 'message': message})

            # Get all the cases from that vendor
            db_config = {
                'host': os.environ['HOST_IP'],
                'port': 3306,
                'user': os.environ['LOCAL_DB_USER'],
                'password': os.environ['LOCAL_DB_PASSWORD'],
                'tenant_id': tenant_id
            }
            db = DB('queues', **db_config)
            # db = DB('queues') # Development purpose

            template_cases_df = db.get_all_with_condition('process_queue',
                                                          condition={'template_name': template_name, 'queue': 'Verify'})
            case_ids = list(template_cases_df['case_id'])
            logging.debug(f'Case IDs with template `{template_name}` in Verify: {case_ids}')

            # Loop through the cases and call value_extract (thread it)
            for case_id in case_ids:
                if case_id != retrained_case:
                    t1 = threading.Thread(target=value_extract,
                                          args=({'case_id': case_id, 'tenant_id': tenant_id}, False, True))
                    t1.start()
                    logging.debug(f'Extracting for `{case_id}`...')

            # Return the number of cases that are being processed
            return jsonify({'flag': True, 'data': f'Processing {len(case_ids) - 1} other cases.'})
        except Exception as e:
            logging.exception('Something went wrong extracting from template. Check trace.')
            return jsonify({'flag': False, 'message': 'System error! Please contact your system administrator.'})


@app.route('/predict_field', methods=['POST', 'GET'])
def predict_field():
    try:
        data = request.json
        response_data = value_extract(data, api=True)
        logging.debug(response_data)
        return jsonify(response_data)
    except Exception as e:
        logging.exception('Something went wrong while extracting. Check trace.')
        return jsonify({'flag': False, 'message': 'System error! Please contact your system administrator.'})
