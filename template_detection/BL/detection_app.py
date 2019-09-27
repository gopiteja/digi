"""
@author: Srinivasan Ravichandran
"""
import ast
import base64
import json
import ntpath
import os
import pandas as pd
import pymysql
import requests
import shutil
import subprocess
import sys
import traceback

from flask import Flask, request, jsonify, url_for
from flask_cors import CORS
from pathlib import Path
from datetime import datetime, timedelta

from abbyy_cloud import ocr_cloud
from db_utils import DB
from template_detector import TemplateDetector

try:

    with open('app/configs/template_detection_params.json') as f:
        parameters = json.loads(f.read())
except:
    from ace_logger import Logging

    with open('configs/template_detection_params.json') as f:
        parameters = json.loads(f.read())
from py_zipkin.zipkin import zipkin_span

import xml_parser_sdk

try:
    from .ace_logger import Logging
except:
    from ace_logger import Logging

logging = Logging()

FEF_XML = 7
XCA_Ascii = 1
logging = Logging()

app = Flask(__name__)
cors = CORS(app)


def isListEmpty(inList):
    if not inList:
        return True
    if isinstance(inList, list):  # Is a list
        return all(map(isListEmpty, inList))
    return False


def get_parameters():
    """
    Util function to load app parameters
    """


def get_count(ocr_data):
    with open('./words_dictionary.json') as f:
        words_dict = json.load(f)
    count = 0
    for page in ocr_data:
        for word in page:
            if word['word'].lower() in words_dict.keys():
                count += 1
    return count


def filter_junkwords(ocr_data):
    with open('./words_dictionary.json') as f:
        words_dict = json.load(f)
    positives_count = 0
    positives = []

    for page in ocr_data:
        for word in page:
            if word['word'].lower() in words_dict.keys() and len(word['word']) > 3 \
                    and word['word'].lower() not in positives:
                positives_count += 1
                positives.append(word['word'].lower())
        break

    return {'count': positives_count, 'valid_words': ' '.join(positives)}


# @app.route('/algonox_detect_template', methods=['POST', 'GET'])
@zipkin_span(service_name='detection_app', span_name='algonox_template_detection')
def algonox_template_detection(case_id, tenant_id, file_path=''):
    # data = request.json

    # # Sanity check
    # if 'file' not in data:
    #     logging.debug(f'{Fore.RED}File path not provided to AlgonoX template detection')
    #     return "File path not provided to AlgonoX template detection"

    detection_method = parameters['algonox_detection_method']

    # Initialization of DB
    template_db_config = {
        'host': os.environ['HOST_IP'],
        'port': 3306,
        'user': os.environ['LOCAL_DB_USER'],
        'password': os.environ['LOCAL_DB_PASSWORD'],
        'tenant_id': tenant_id
    }
    template_db = DB('template_db', **template_db_config)
    # template_db = DB('template_db')

    template_db_config = {
        'host': os.environ['HOST_IP'],
        'port': 3306,
        'user': os.environ['LOCAL_DB_USER'],
        'password': os.environ['LOCAL_DB_PASSWORD'],
        'tenant_id': tenant_id
    }
    queue_db = DB('queues', **template_db_config)
    # queue_db = DB('queues')

    # Get OCR data of the file
    query = 'SELECT * FROM `ocr_info` WHERE `case_id`=%s'
    params = [case_id]
    ocr_info = queue_db.execute(query, params=params)

    if ocr_info.empty:
        ocr_data = {}
        logging.warning('OCR data is not in DB or is empty.')
    else:
        ocr_data = json.loads(list(ocr_info.ocr_data)[0])

    if ocr_data:
        td = TemplateDetector(tenant_id=tenant_id,
                              threshold=parameters['matching_threshold'],
                              address_threshold=parameters["address_threshold"]
                              )
        # predicted_template_with_keyword = ''
        # print_score = None

        # if detection_method == 'ngram':
        #     predicted_template_with_keyword = td.predict_combo_ngram(ocr_data)
        # elif detection_method == 'vname':
        #     predicted_template_with_keyword = td.predict_with_vname(ocr_data)
        # else:
        #     print(f'Unknown detection method {detection_method}')
        #     return

        predicted_template = td.unique_fields(ocr_data)
        print(f'predicted_template_with_unique_fields - {predicted_template}')

        # predicted_template_with_aankho_dekhi = ''
        # predicted_template_with_aankho_dekhi = td.aankho_dekhi_method(ocr_data, predicted_template_with_keyword) 
        # print(f'predicted_template_with_aankho_dekhi - {predicted_template_with_aankho_dekhi}')
        # print(f'predicted_template_with_keyword - {predicted_template_with_keyword}')
        # if not predicted_template_with_aankho_dekhi:
        #     predicted_template_with_aankho_dekhi = td.unique_fields(ocr_data)
        #     print(f'predicted_template_with_unique_fields - {predicted_template_with_aankho_dekhi}')

        # if (predicted_template_with_aankho_dekhi and predicted_template_with_keyword\
        #     and predicted_template_with_aankho_dekhi == predicted_template_with_keyword) \
        #     or (not predicted_template_with_aankho_dekhi and predicted_template_with_keyword) \
        #     or (predicted_template_with_aankho_dekhi and not predicted_template_with_keyword):

        #     #if aankho dekhi does not give anything, then take keyword template
        #     if (not predicted_template_with_aankho_dekhi and predicted_template_with_keyword):
        #         predicted_template = predicted_template_with_keyword
        #     else:
        #         predicted_template = predicted_template_with_aankho_dekhi

        # print(f'Predicted template is {predicted_template}')
        # if print_score:
        #     logging.debug(f'Score: {print_score}')
        # to track which method prediction what
        # template_prediction_record = {'AD':predicted_template_with_aankho_dekhi, 'kv':predicted_template_with_keyword}

        template_prediction_record = {'unique': predicted_template}
        query = "UPDATE `process_queue` SET `template_name`= %s, `template_prediction_record` =%s WHERE `case_id` = %s"
        params = [predicted_template, json.dumps(template_prediction_record), case_id]
        logging.debug('Setting template name for the file in DB')
        queue_db.execute(query, params=params)
        # if parameters['abbyy_classification_enabled']:
        #     query = "SELECT `id`, `count` FROM `trained_info` WHERE `template_name` = %s"
        #     params = [predicted_template]
        #     data = template_db.execute(query, params=params)

        #     if not data.empty:
        #         count = int(data['count'].iloc[0])
        #         count = count + 1
        #         count_query = "UPDATE `trained_info` SET `count`= %s WHERE `template_name` = %s;"
        #         count_params = [count, predicted_template]

        #         parameters = get_parameters()
        #         sample_count = parameters['n_training_samples']

        #         # Update sample paths until sufficient samples are received for ABBYY training
        #         if count <= sample_count:
        #             query = "SELECT `id`, `sample_paths` FROM `trained_info` WHERE `template_name` = %s"
        #             data_df = template_db.execute(query, params=[predicted_template])
        #             if not data_df.empty:
        #                 sample_file_paths_str = data_df['sample_paths'].iloc[0]
        #                 sample_file_paths = []
        #                 if sample_file_paths_str:
        #                     sample_file_paths = ast.literal_eval(data_df['sample_paths'].iloc[0])
        #                     if str(Path(file_path).name) not in sample_file_paths:
        #                         sample_file_paths.append(str(Path(file_path).name))
        #                         template_db.execute(count_query, params=count_params)
        #                 else:
        #                     sample_file_paths = [str(Path(file_path).name)]
        #                     template_db.execute(count_query, params=count_params)

        #                 logging.debug(Path(file_path).name)

        #                 query = "UPDATE `trained_info` SET `sample_paths`= %s WHERE `template_name` = %s;"
        #                 params = [str(sample_file_paths), predicted_template]
        #                 template_db.execute(query, params=params)
        #             else:
        #                 # This should never happen
        #                 logging.warning('Template not found in trained_info')
        #         # If sufficient samples are received, call abbyy_training if not done already
        #         else:
        #             query = "SELECT `id`, `sample_paths`, `ab_train_status` FROM `trained_info` WHERE `template_name` = %s"
        #             params = [predicted_template]
        #             data_df = template_db.execute(query, params=params)

        #             if not data_df.empty:
        #                 ab_train_status = data_df['ab_train_status'].iloc[0]
        #                 # If ABBYY trainining isn't done
        #                 if not int(ab_train_status):
        #                     # Call ABBYY template training
        #                     sample_file_paths_str = eval(data_df['sample_paths'].iloc[0])
        #                     payload = {'template_name': predicted_template, 'sample_file_paths': sample_file_paths_str}
        #                     logging.debug (payload)
        #                     host = os.environ['HOST_IP']
        #                     port = 5009
        #                     route = 'abbyy_train_template'
        #                     response = requests.post(f'http://{host}:{port}/{route}', json=payload)
        #                     train_output = response.json()
        #                     logging.debug(f'{sample_count} samples obtained. Calling ABBYY template training.')
        #                     # If ABBYY training is successful, mark in trained_info
        #                     if train_output['flag']:
        #                         update_ab_status_query = "UPDATE trained_info SET `ab_train_status` = %s WHERE `template_name` = %s"
        #                         params = [1, predicted_template]
        #                         template_db.execute(update_ab_status_query, params=params)
        #             # Template not found in trained_info
        #             else:
        #                 # This should never happen
        #                 logging.warning('Template not found in trained_info')
        # return {'template_name': predicted_template, 'probability': td.max_match_score}
        #         # return predicted_template
        #     # Template not found in trained_info
        # else:
        #     logging.info('Skipping ABBYY training since not enabled')
        #     return {'template_name': predicted_template, 'probability': td.max_match_score}
        #     pass
        # No template predicted
        if predicted_template == '':
            logging.warning('No matching template found. Updating queue to `Template Exceptions`.')
            # Mark for clustering
            query = 'SELECT * FROM `queue_definition` WHERE `name`=%s'
            move_to_queue_df = queue_db.execute(query, params=['Template Exceptions'])
            move_to_queue = list(move_to_queue_df['unique_name'])[0]


            query = "UPDATE `process_queue` SET `queue`= %s WHERE `case_id` = %s;"
            queue_db.execute(query, params=[move_to_queue, case_id])

            # Updating in trace_info table  as well
            query = "UPDATE `trace_info` SET `queue_trace`= 'Template Exceptions',`last_updated_dates`=%s  WHERE " \
                    "`case_id` = %s; "
            queue_db.execute(query, params=[datetime.now().strftime(r'%d/%m/%Y %H:%M:%S'), case_id])

            predicted_template = ''

        return {'template_name': predicted_template, 'probability': -1}
    # OCR data is empty
    else:
        message = f'Template Detection Error: OCR data for case `{case_id}` not found.'
        logging.error(message)
        predicted_template = ''
        return {'template_name': predicted_template, 'probability': -1}


# @app.route('/abbyy_detect_template', methods=['POST', 'GET'])
@zipkin_span(service_name='detection_app', span_name='abbyy_template_detection')
def abbyy_template_detection(data):
    # data = request.json

    # Sanity checks
    if 'files' not in data:
        message = '`files` key not in request'
        logging.error(message)
        return {'flag': False, 'message': message}

    files = data['files']
    original_file_names = data['original_file_name']

    if not files:
        message = 'Files list is empty'
        logging.error(message)
        return {'flag': False, 'message': message}

    tenant_id = ''
    if 'tenant_id' in data:
        tenant_id = data['tenant_id']

    # Initialization of DB
    template_db_config = {
        'host': os.environ['HOST_IP'],
        'port': 3306,
        'user': os.environ['LOCAL_DB_USER'],
        'password': os.environ['LOCAL_DB_PASSWORD'],
        'tenant_id': tenant_id
    }
    template_db = DB('template_db', **template_db_config)
    # template_db = DB('template_db')

    template_db_config = {
        'host': os.environ['HOST_IP'],
        'port': 3306,
        'user': os.environ['LOCAL_DB_USER'],
        'password': os.environ['LOCAL_DB_PASSWORD'],
        'tenant_id': tenant_id
    }
    queue_db = DB('queues', **template_db_config)
    # queue_db = DB('queues')

    success_files = {}
    failed_files = {}

    pdf_working = None

    # Process files one by one
    for index, file_name in enumerate(files):
        file_path = './input/' + file_name
        case_id = file_name.rsplit('.', 1)[0]
        original_file_name = original_file_names[index]
        xml_string = None
        label = ''
        probability = 0.0

        static_input_path = Path(parameters['static_input_path'])
        model_path = parameters['model_path']

        logging.info(f'Processing file {original_file_name}')
        try:
            query = "SELECT id, ocr_data from ocr_info where case_id = %s"
            logging.debug(f'Case ID: `{case_id}`')
            case_id_process = list(queue_db.execute(query, params=[case_id]).ocr_data)[0]
        except:
            case_id_process = None

        if case_id_process == '' or case_id_process is None:
            try:
                logging.info('Detecting using Abbyy')

                db = DB('io_configuration', **template_db_config)
        
                input_config = db.get_all('input_configuration')
                output_config = db.get_all('output_configuration')

                logging.debug(f'Input Config: {input_config.to_dict()}')
                logging.debug(f'Output Config: {output_config.to_dict()}')

                # Sanity checks
                if (input_config.loc[input_config['type'] == 'Document'].empty
                        or output_config.loc[input_config['type'] == 'Document'].empty):
                    message = 'Input/Output not configured in DB.'
                    logging.error(message)
                else:
                    input_path = input_config.iloc[0]['access_1']
                    output_path = output_config.iloc[0]['access_1']

                file_path = './input/'+ output_path + '/' + file_name

                logging.info(' -> Trying PDF plumber...')
                host = 'pdf_plumber_api'
                port = parameters['pdf_plumber_port']
                route = 'plumb'
                data = {
                    'file_name': file_name,
                    'tenant_id': tenant_id,
                    'pdf' : pdfplumber.open(file_path)
                }
                response = requests.post(f'http://{host}:{port}/{route}', json=data)
                pdf_response = response.json()

                if pdf_response['flag']:
                    pdf_data = pdf_response['data']
                    pdf_working = True
                else:
                    pdf_data = None
            except:
                logging.exception('PDF plumbing failed.')
                pdf_data = None

            if isListEmpty(pdf_data):
                pdf_working = False
            else:
                proper_ocr = filter_junkwords(pdf_data)
                junk_words_thres = parameters['junk_words_thres']
                if proper_ocr['count'] < junk_words_thres:
                    pdf_working = False

            # no matter what ....try..abbyyy....
            # if isListEmpty(pdf_data) or not pdf_working:
            try:
                

                # file_data = open(file_path, 'rb')

                # 172.31.45.112
                # host = '152.63.4.80'
                # port = 5003
                # route = 'sdk'
                # data = {
                #     'static_path': str(static_input_path),
                #     'file_name': file_name,
                #   'tenant_id':tenant_id
                # }

                # data = {'file_data': file_data, 'file_name': file_name}
                # response = requests.post(f'http://{host}:{port}/{route}', files=data)

                # Delete file for alorica
                # os.remove(file_path)

                # SDK
                def path_leaf(path):
                    """give any path...platform independent...get the base name"""
                    head, tail = ntpath.split(path)
                    return tail or ntpath.basename(head)

                file_name_ = path_leaf(Path(file_path).absolute())
                files_data = {'file': (file_name_, open(file_path, 'rb'))}
                url = parameters['abbyy_url']

                logging.debug(url)
                response = requests.post(url, files=files_data)

                logging.debug(type(response))
                sdk_output = response.json()
                logging.debug(type(sdk_output))
                logging.debug(sdk_output.keys())
                try:
                    pdf = base64.b64decode(sdk_output['blob'])
                    with open(file_path, 'wb') as f:
                        f.write(pdf)
                except:
                    logging.error('no blob data')

                # unique_id = file_path.stem
                # Delete file for alorica
                os.remove(file_path)
                # shutil.copyfile(file_path, 'angular/' + file_name)
                # shutil.move(file_path, 'training_ui/' + file_name)

                xml_string = sdk_output['xml_string'].encode('utf-8')

                classification = sdk_output.pop('classification', None)

                if classification is not None:
                    label = classification['label']
                    probability = classification['probability']

                logging.info(f' - Template: {label}')
                logging.info(f' - Probability: {probability}')
            except:
                xml_string = None
                message = f'Failed to OCR {file_name} using SDK'
                logging.exception(message)
                try:
                    logging.debug('Trying Abbyy Cloud OCR')
                    xml_string = ocr_cloud(file_path)
                except:
                    message = f'Failed to OCR {file_name} using Cloud SDK too'
                    logging.exception(message)

                label = ''
                probability = 0.0
                failed_files[file_name] = message

            # If OCR-ed successfully, insert into process_queue with status 1 (success)
            # else insert with status 0 (failed)
            print("pdf_data", pdf_data)
            # print("saving ocr data")
            # if xml_string is None and isListEmpty(pdf_data):
            #     query = "UPDATE `process_queue` SET `ocr_status`=0, `queue`='Failed' WHERE `case_id`=%s"
            #     queue_db.execute(query, params=[case_id])
            #     print(f'No OCR data for {file_name}. Continuing to next file.')
            #     print('Updated OCR status in process_queue table to 0.')
            #     continue

            if xml_string is not None or xml_string or not isListEmpty(pdf_data):
                logging.debug('now the battle being')
                try:
                    abbyy_ocr_data = xml_parser_sdk.convert_to_json(xml_string)
                except Exception as e:
                    abbyy_ocr_data = []
                    logging.exception(f'Error parsing XML. Check trace.')
                    pass
                pdfplumber_ocr_data = pdf_data
                abbyy_word_count = get_count(abbyy_ocr_data)
                if abbyy_word_count == 0:
                    xml_string = ''
                pdfplumber_word_count = get_count(pdfplumber_ocr_data)
                logging.debug(f"abby_count: {abbyy_word_count} pdfplumbercount: {pdfplumber_word_count}")
                if abbyy_word_count - pdfplumber_word_count > parameters['battle_resolver_threshold']:
                    logging.info(f"abbyy ocr data is being used")
                    ocr_data = abbyy_ocr_data
                else:
                    logging.info(f"pdf plumber ocr data is being used")
                    ocr_data = pdfplumber_ocr_data

                ocr_text = ' '.join([word['word'] for page in ocr_data for word in page])
                query = 'INSERT into `ocr_info` (`case_id`, `ocr_text`, `xml_data`, `ocr_data`) values (%s%s, %s ,%s)'
                params = [case_id, ocr_text, xml_string, json.dumps(ocr_data)]
                queue_db.execute(query, params=params)
                logging.debug('OCR data saved into ocr_info table.')

                query = 'UPDATE `process_queue` SET `ocr_status`=1 WHERE `case_id`=%s'
                params = [case_id]
                queue_db.execute(query, params=params)
                logging.debug('Updated OCR status to 1 in process_queue table.')
            else:
                query = "UPDATE `process_queue` SET `ocr_status`=0, `queue`='Failed' WHERE `case_id`=%s"
                queue_db.execute(query, params=[case_id])
                logging.debug(f'No OCR data for {file_name}. Continuing to next file.')
                logging.debug('Updated OCR status in process_queue table to 0.')
                continue

        # If the probability > threshold the use Abbyy's prediction
        # else use our custom prediction algorithm to predict template
        if probability >= float(parameters['abbyy_detection_thresh']):
            # Whats going on here? Why increase the count here?
            # Update count in trained_info
            query = "SELECT `id`, `count` FROM `trained_info` WHERE `template_name` = %s"
            result_df = template_db.execute(query, params=[label])

            # If trained_info contains this template, increase the count
            if not result_df.empty:
                count = int(result_df['count'].iloc[0])
                count = count + 1
                query = "UPDATE `trained_info` SET `count`= %s WHERE `template_name` = %s"
                params = [count, label]
                logging.debug('Updating count in DB')
                template_db.execute(query, params=params)

                # Update template_name in process_queue
                query = "UPDATE `process_queue` SET `template_name`= %s WHERE `case_id` = %s"
                params = [label, case_id]
                logging.debug('Setting template name for the file in DB')
                queue_db.execute(query, params=params)

            response_data = {
                'template_name': label,
                'probability': probability,
                'method': 'Abbyy'
            }
            response = {
                'flag': True,
                'send_data': {
                    'file_name': original_file_name,
                    'case_id': case_id,
                    'tenant_id': tenant_id
                }
            }
            return response
        else:
            try:
                logging.debug('Detecting using ACE')
                response_json = algonox_template_detection(case_id, file_path=file_path, tenant_id=tenant_id)
                label = response_json['template_name']
                probability = response_json['probability']
                response_data = {
                    'template_name': label,
                    'probability': probability,
                    'method': 'ACE'
                }
                logging.debug(label)
                if label:
                    response = {
                        'flag': True,
                        'send_data': {
                            'file_name': original_file_name,
                            'case_id': case_id,
                            'tenant_id': tenant_id
                        }
                    }
                    return response
            except Exception as e:
                message = f'Error occured while detecting template using ACE. {e}'
                logging.exception(message)
                failed_files[file_name] = message
                return {'flag': False, 'send_to_topic': 'clustering'}

    return {'flag': False, 'send_to_topic': 'clustering'}

# if __name__ == '__main__':
#     init(autoreset=True) # Intialize colorama

# Load app parameters from config file
# parameters = get_parameters()
# machines = parameters['platform']
# app_host = parameters['machine_ip']
# app_port = parameters['template_detection_port']

# # Run app
# app.run(host=app_host, port=app_port, debug=False, threaded=True)
