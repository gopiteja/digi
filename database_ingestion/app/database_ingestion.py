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
from db_utils import DB

import app.xml_parser_sdk as xml_parser
from app.producer import produce

ImageFile.LOAD_TRUNCATED_IMAGES = True

from app import app

def insertstitchedBLOB(name, photo):
    try:
        connection = mysql.connector.connect(host=os.environ['HOST_IP'],
                             database='queues',
                             user='root',
                             password='AlgoTeam123')
        cursor = connection.cursor(prepared=True)
        sql_insert_blob_query = """ INSERT INTO `merged_blob`
                          (`case_id`, `merged_blob`) VALUES (%s,%s)"""
        # Convert data into tuple format
        insert_blob_tuple = (name, photo)
        result  = cursor.execute(sql_insert_blob_query, insert_blob_tuple)
        connection.commit()
    except mysql.connector.Error as error :
        connection.rollback()
        print("Failed inserting BLOB data into MySQL table {}".format(error))
    finally:
        #closing database connection.
        if(connection.is_connected()):
            cursor.close()
            connection.close()
            print("MySQL connection is closed")           

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
    db_config = {
        'host': 'queue_db',
        'port': 3306,
        'user': 'root',
        'password': 'root',
        'tenant_id': tenant_id
    }

    alorica_db = DB('alorica_data', **db_config)
    queues_db = DB('queues', **db_config)
    stats_db = DB('stats', **db_config)

    query = "Select * from screen_shots where processed = 0 order by Fax_unique_id, Screen_Page_number, Screen_Page_part asc"
    query_dict = alorica_db.execute(query).to_dict(orient='records')
    
    case_id_dict = {}
    for i in query_dict:
        try:
            case_id_dict[i['Fax_unique_id']].append(i['Fax_Screen'])
        except:
            case_id_dict[i['Fax_unique_id']] = [i['Fax_Screen']]
    screenshots_per_page = 2
    
    for key, val in case_id_dict.items():
        try:
            imgs = []
            for i in val:
                try:
                    print(i[:100])
                    print("Trying old")
                    imgs.append(Image.open(BytesIO(i)))
                except:
                    blob_type = type(i)
                    print("old failed. trying new", blob_type)
                    i = base64.b64decode(i)
                    print(i[:100])
                    print("first decode", type(i))
                    if blob_type == str:
                        i = base64.b64decode(i)
                        print(i[:100])
                        print("second decode", type(i))
                    imgs.append(Image.open(BytesIO(i))) 

            print("making chunks")

            chunks = make_chunks(imgs, screenshots_per_page)
            pages_images = []
            for page in chunks:
                min_shape = sorted( [(np.sum(i.size), i.size ) for i in page])[0][1]  
                
                imgs_comb = np.vstack( (np.asarray( i.resize(min_shape) ) for i in page ) )
                imgs_comb = Image.fromarray( imgs_comb)
                rgb = Image.new('RGB', imgs_comb.size, (255, 255, 255)) 
                rgb.paste(imgs_comb, mask=imgs_comb.split()[3])
                pages_images.append(rgb)
                
            rgbByteArr = BytesIO()
            pages_images[0].save(rgbByteArr, format='PDF',resolution=100.0, save_all=True, append_images=pages_images[1:])
            pdf_blob = rgbByteArr.getvalue()

            print("converted to PDF")
            
            insertstitchedBLOB(key, pdf_blob)

            print("Inserted to PDF")
            
            # To save blob to file
            # text_file = open(folder_monitor+key+'.pdf','wb')
            # text_file.write(pdf_blob)
            # text_file.close()
            
            query = f"Update screen_shots set `processed` = 1 where Fax_unique_id = '{key}'"
            alorica_db.execute(query)

            query = "SELECT * from ocr_info where case_id = %s"
            case_id_process = queues_db.execute(query,params=[key])

            if case_id_process.empty:
                print("Calling Abbyy")
                host = os.environ['HOST_IP']
                port = 5555
                route = 'database_ocr'
                data = {
                    'case_id': key
                }
                print ("calling the bloblby")
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
            agent = list(alorica_db.execute(query,params=[key]).Agent)[0]
            com_date = list(alorica_db.execute(query,params=[key]).Communication_date)[0]
            history = list(alorica_db.execute(query,params=[key]).History)[0]

            if case_id_process.empty:
                insert_query = ('INSERT INTO `process_queue` (`case_id`, `agent`,`source_of_invoice`, `Fax_unique_id`, `communication_date_time`, `communication_date_time_bot`) '
                    'VALUES (%s, %s, %s, %s, %s, %s)')
                params = [key, agent, 'database', key, com_date, history]
                queues_db.execute(insert_query, params=params)
                print(f' - {key} inserted successfully into the database')

                audit_data = {
                        "type": "insert", "last_modified_by": 'Bot', "table_name": "process_queue", "reference_column": "case_id",
                        "reference_value": key, "changed_data": json.dumps({"stats_stage": "OCR Time"})
                    }
                stats_db.insert_dict(audit_data, 'audit')

            # Produce message to detection

            data = {
                'case_id': key,
                'tenant_id': None,
                'type': 'database_ingestion'
            }

            topic = 'detection' # Get the first topic from message flow

            produce(topic, data)
        except:
            traceback.print_exc()
            query = f"Update screen_shots set `processed` = 2 where Fax_unique_id = '{key}'"
            alorica_db.execute(query)
            query = f"delete from merged_blob where case_id = '{key}'"
            queues_db.execute(query)
            
  
    return jsonify({"flag": True, "message": "Files sent to Template Detection"})
