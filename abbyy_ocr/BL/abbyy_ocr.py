"""
@author: Srinivasan Ravichandran
"""
import base64
import json
import ntpath
import os
import pandas as pd
import requests
import traceback

from db_utils import DB
from py_zipkin.zipkin import zipkin_span
import xml_parser_sdk
from ace_logger import Logging

logging = Logging()

@zipkin_span(service_name='abbyy_ocr', span_name='abbyy_ocr')
def abbyy_ocr(case_id, tenant_id=None):
    db_config = {
        'host': os.environ['HOST_IP'],
        'port': 3306,
        'user': os.environ['LOCAL_DB_USER'],
        'password': os.environ['LOCAL_DB_PASSWORD'],
        'tenant_id': tenant_id
    }

    queue_db = DB('queues', **db_config)

    query = "Select file_name from process_queue where case_id = %s"
    file_name = list(queue_db.execute_(queue_db).file_name)[0]

    angular_path = '/app/angular/'

    try:
        files_data = {'file': (file_name, open(angular_path + file_name, 'rb'))}
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

        xml_string = sdk_output['xml_string'].encode('utf-8')

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

    if xml_string is not None or xml_string:
        try:
            ocr_data = xml_parser_sdk.convert_to_json(xml_string)
        except Exception as e:
            ocr_data = []
            logging.exception(f'Error parsing XML. Check trace. {e}')
            pass
        
        ocr_text = ' '.join([word['word'] for page in ocr_data for word in page])
        query = 'INSERT into `ocr_info` (`case_id`, `ocr_text`, `xml_data`, `ocr_data`) values (%s, %s, %s ,%s)'
        params = [case_id, ocr_text, xml_string, json.dumps(ocr_data)]
        queue_db.execute(query, params=params)
        logging.debug('OCR data saved into ocr_info table.')

        query = 'UPDATE `process_queue` SET `ocr_status`=1 WHERE `case_id`=%s'
        params = [case_id]
        queue_db.execute(query, params=params)
        logging.debug('Updated OCR status to 1 in process_queue table.')

    return {'flag': True}

