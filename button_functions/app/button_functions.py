import argparse
import ast
import json
import os
import requests
import traceback
import warnings

from datetime import datetime, timedelta
from flask import Flask, request, jsonify
from flask_cors import CORS
from pandas import Series, Timedelta, to_timedelta
from py_zipkin.zipkin import zipkin_span, ZipkinAttrs, create_http_headers_for_new_span
from time import time

from db_utils import DB
from producer import produce
from ace_logger import Logging

from app import app

logging = Logging()

db_config = {
    'host': os.environ['HOST_IP'],
    'user': os.environ['LOCAL_DB_USER'],
    'password': os.environ['LOCAL_DB_PASSWORD'],
    'port': os.environ['LOCAL_DB_PORT']
}

def http_transport(encoded_span):
    # The collector expects a thrift-encoded list of spans. Instead of
    # decoding and re-encoding the already thrift-encoded message, we can just
    # add header bytes that specify that what follows is a list of length 1.
    body =encoded_span
    requests.post(
            'http://servicebridge:80/zipkin',
        data=body,
        headers={'Content-Type': 'application/x-thrift'},
    )

@zipkin_span(service_name='folder_monitor', span_name='produce_with_zipkin')
def produce_with_zipkin(first_route, data):
    logging.info('Producing with zipkin...')

    zipkin_headers = create_http_headers_for_new_span()
    data['zipkin_headers'] = zipkin_headers
    logging.debug(f'Zipkin data: {data}')
    
    produce(first_route, data)

@app.route('/execute_button_function', methods=['POST', 'GET'])
def execute_button_function():
    data = request.json
    logging.debug(f'Data: {data}')

    with zipkin_span(service_name='button_functions', span_name='execute_button_function', 
            transport_handler=http_transport, port=5007, sample_rate=0.5,):
        try:
            group = data['group']
            case_id = data['case_id']
            tenant_id = data['tenant_id']

            queue_db = DB('queues', tenant_id=tenant_id, **db_config)
            kafka_db = DB('kafka', tenant_id=tenant_id, **db_config)

            message_flow = kafka_db.get_all('grouped_message_flow')
            group_messages = message_flow.loc[message_flow['message_group'] == group]

            if group_messages.empty:
                message = f'Group `{group}` is not configured.'
                logging.error(message)
                return jsonify({'flag': False, 'message': message})

            first_route = list(group_messages['listen_to_topic'])[0]
            logging.debug(f'First Route: {first_route}')
            try:
                query_ = f"SELECT * FROM `button_functions` where `route` = '{first_route}'"
                button_functions_df = queue_db.execute(query_)
                button_type = list(button_functions_df['type'])[0]
                if button_type == 'api':
                    return jsonify({'flag' : True, 'show_decision_tree': True })
            except:
                logging.exception("failed in the changes made in button functions")

            query = 'UPDATE `process_queue` SET `case_lock`=1, `failure_status`=0, `completed_processes`=0, `total_processes`=0, `status`=NULL WHERE `case_id`=%s'
            queue_db.execute(query, params=[case_id])
            
            produce_with_zipkin(first_route, data)

            return jsonify({'flag': True, 'message': f'Started processing... ({first_route})'})
        except KeyError as e:
            logging.exception('Something went wrong executing button functions. Check Trace.')
            return jsonify({'flag': False, 'message': f'ERROR: [{e}]'})