# -*- coding: utf-8 -*-
"""
Created on Fri Aug  9 17:34:10 2019

@author: Admin
"""

import base64
from io import BytesIO
import json
import os
import requests
import traceback
import numpy as np
from PIL import Image, ImageFile
import mysql.connector
from flask import Flask, jsonify, request
from flask_cors import CORS
from PyPDF2 import PdfFileReader
from ace_logger import Logging
from db_utils import DB
import argparse
from producer import produce
import app.xml_parser_sdk as xml_parser
# from app.producer import produce

ImageFile.LOAD_TRUNCATED_IMAGES = True

try:
    from app import app
except:
    app = Flask(__name__)
    cors = CORS(app)


logging = Logging()

db_config = {
    'host': os.environ['HOST_IP'],
    'user': os.environ['LOCAL_DB_USER'],
    'password': os.environ['LOCAL_DB_PASSWORD'],
    'port': os.environ['LOCAL_DB_PORT'],
}

def insertstitchedBLOB(name, photo):
    try:
        connection = mysql.connector.connect(host=os.environ['HOST_IP'],
                             database='queues',
                             user=os.environ['LOCAL_DB_USER'],
                             password=os.environ['LOCAL_DB_PASSWORD'])
        cursor = connection.cursor(prepared=True)
        sql_insert_blob_query = """ INSERT INTO `merged_blob`
                          (`case_id`, `merged_blob`) VALUES (%s,%s)"""
        # Convert data into tuple format
        insert_blob_tuple = (name, photo)
        result  = cursor.execute(sql_insert_blob_query, insert_blob_tuple)
        connection.commit()
    except mysql.connector.Error as error :
        connection.rollback()
        logging.exception("Failed inserting BLOB data into MySQL table {}".format(error))
    finally:
        #closing database connection.
        if(connection.is_connected()):
            cursor.close()
            connection.close()
            logging.debug("MySQL connection is closed")

def make_chunks(l, n):
    """Yield successive n-sized chunks from l."""
    for i in range(0, len(l), n):
        yield l[i:i + n]


@app.route('/database_upload', methods=['POST', 'GET'])
def database_upload():

    data = request.json
    if not data:
       data = {}
    try:
        tenant_id = data.pop('tenant_id', None)
    except:
        tenant_id = None

    db_config['tenant_id'] = tenant_id
    queue_db = DB('queues', **db_config)

    query = "Select * from merged_blob where processed = 0"
    query_dict = queue_db.execute(query).to_dict(orient='records')

    case_id_dict = {}
    for i in query_dict:
        print('i', i)
        try:
            case_id_dict[i['case_id']].append(i['merged_blob'])
        except:
            case_id_dict[i['case_id']] = [i['merged_blob']]

    for key, val in case_id_dict.items():
        try:
            query = "SELECT * from ocr_info where case_id = %s"
            case_id_process = queue_db.execute(query,params=[key])
            if case_id_process.empty:
                logging.debug("Calling Abbyy")
                host = os.environ['HOST_IP']
                port = 5555
                route = 'database_ocr'
                data = {
                    'case_id': key
                }
                logging.debug ("calling the blobby")
                response = requests.post(f'http://{host}:{port}/{route}', json=data)

                xml_string = response.json()['xml_string']

                ocr_data = xml_parser.convert_to_json(xml_string)

                ocr_text = ' '.join([word['word'] for page in ocr_data for word in page])

                ocr_data_s = json.dumps(ocr_data)

                insert_query = f"INSERT INTO `ocr_info`( `case_id`, `xml_data`, `ocr_text`, `ocr_data`) VALUES (%s,%s,%s,%s)"
                queue_db.execute(insert_query, params=[key,xml_string,ocr_text,ocr_data_s])

            query = "SELECT * from process_queue where case_id = %s"
            case_id_process = queue_db.execute(query,params=[key])


            if case_id_process.empty:
                insert_query = ('INSERT INTO `process_queue` (`case_id`) '
                    'VALUES (%s)')
                params = [key]
                queue_db.execute(insert_query, params=params)
                logging.debug(f' - {key} inserted successfully into the database')

            # Produce message to detection

            data = {
                'case_id': key,
                'tenant_id': None,
                'type': 'database_ingestion'
            }
            #
            # topic = 'detection' # Get the first topic from message flow
            #
            # produce(topic, data)
            kafka_db = DB('kafka', **db_config)
            query = 'SELECT * FROM `message_flow` WHERE `listen_to_topic`=%s'
            message_flow = kafka_db.execute(query, params=['database_ingestion'])

            if message_flow.empty:
                logging.error('`database_ingestion` is not configured in message flow table.')
            else:
                topic = list(message_flow.send_to_topic)[0]

                if topic is not None:
                    logging.debug(f'Producing to topic {topic}')
                    produce(topic, data)
                else:
                    logging.debug(f'There is no topic to send to for `database_ingestion`. [{topic}]')
        except:
            logging.exception('')
            query = f"delete from merged_blob where case_id = '{key}'"
            queue_db.execute(query)


    return jsonify({"flag": True, "message": "Files sent to Template Detection"})

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-p', '--port', type=int, help='Port Number', default=5012)
    parser.add_argument('--host', type=str, help='Host', default='0.0.0.0')
    args = parser.parse_args()

    host = args.host
    port = args.port

    app.run(host=host, port=port, debug=False)
