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

import app.xml_parser_sdk as xml_parser
from app.producer import produce

ImageFile.LOAD_TRUNCATED_IMAGES = True

try:
    from app import app
except:
    app = Flask(__name__)
    cors = CORS(app)


logging = Logging()
logging_config = {
        'level': logging.DEBUG,
        'format': '%(asctime)s - %(levelname)s - %(filename)s @%(lineno)d : %(funcName)s() - %(message)s'
    }
logging.basicConfig(**logging_config)

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
            logging.info("MySQL connection is closed")

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
    ingestion_db = DB('db_ingestion_data', **db_config)
    queues_db = DB('queues', **db_config)

    try:
        if case_id_process.empty:
            logging.info("Calling Abbyy")
            host = os.environ['HOST_IP']
            port = 5555
            route = 'database_ocr'
            data = {
                'case_id': key
            }
            logging.info ("calling the bloblby")
            response = requests.post(f'http://{host}:{port}/{route}', json=data)

            xml_string = response.json()['xml_string']

            ocr_data = xml_parser.convert_to_json(xml_string)

            ocr_text = ' '.join([word['word'] for page in ocr_data for word in page])

            ocr_data_s = json.dumps(ocr_data)

            insert_query = f"INSERT INTO `ocr_info`( `case_id`, `xml_data`, `ocr_text`, `ocr_data`) VALUES (%s,%s,%s,%s)"
            queues_db.execute(insert_query, params=[key,xml_string,ocr_text,ocr_data_s])

        query = "SELECT * from process_queue where case_id = %s"
        case_id_process = queues_db.execute(query,params=[key])

        query = "SELECT id, Agent, Communication_date, History from screen_shots where Fax_unique_id = %s"
        agent = list(ingestion_db.execute(query,params=[key]).Agent)[0]
        com_date = list(ingestion_db.execute(query,params=[key]).Communication_date)[0]
        history = list(ingestion_db.execute(query,params=[key]).History)[0]

        if case_id_process.empty:
            insert_query = ('INSERT INTO `process_queue` (`case_id`, `agent`,`source_of_invoice`, `Fax_unique_id`, `communication_date_time`, `communication_date_time_bot`) '
                'VALUES (%s, %s, %s, %s, %s, %s)')
            params = [key, agent, 'database', key, com_date, history]
            queues_db.execute(insert_query, params=params)
            logging.info(f' - {key} inserted successfully into the database')

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
        query = 'SELECT * FROM `message_flow` WHERE `listen_to_topic`=%s'
        message_flow = kafka_db.execute(query, params=['database_ingestion'])

        if message_flow.empty:
            logging.error('`database_ingestion` is not configured in message flow table.')
        else:
            topic = list(message_flow.send_to_topic)[0]

            if topic is not None:
                logging.info(f'Producing to topic {topic}')
                produce(topic, data)
            else:
                logging.info(f'There is no topic to send to for `database_ingestion`. [{topic}]')

    except:
        logging.exception('')
        query = f"Update screen_shots set `processed` = 2 where Fax_unique_id = '{key}'"
        ingestion_db.execute(query)
        query = f"delete from merged_blob where case_id = '{key}'"
        queues_db.execute(query)


    return jsonify({"flag": True, "message": "Files sent to Template Detection"})
