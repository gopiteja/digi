"""
Author: Ashyam
Created Date: 18-02-2019
"""
import argparse
import base64
import json
import os
import requests
import uuid

from datetime import datetime
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from pathlib import Path
from py_zipkin.zipkin import zipkin_span, ZipkinAttrs, create_http_headers_for_new_span

from ace_logger import Logging
from db_utils import DB
from producer import produce

try:
    from app import app
except:
    app = Flask(__name__)
    CORS(app)

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

@app.route('/get_reports_queue', methods=['POST', 'GET'])
def get_reports_queue():
    try:
        data = request.json
        logging.info(f'Data recieved: {data}')
        tenant_id = data.get('tenant_id', None)
        user = data.get('user', None)

        start = data.get('start', 1) - 1
        end = data.get('end', 20)
        offset = end - start

        # Sanity check
        if user is None:
            message = 'User not provided in request.'
            logging.error(message)
            return jsonify({'flag': False, 'message': message})

        # Connect to reports database
        reports_db = DB('reports', tenant_id=tenant_id, **db_config)

        # Fetch reports
        logging.debug(f'Fetching reports for user `{user}`')
        query = 'SELECT * FROM `reports_queue` WHERE `requested_by`=%s LIMIT %s, %s'
        try:
            user_reports_data = reports_db.execute(query, params=[user, start, offset])
            user_reports_data_json = user_reports_data.to_dict('records')
        except:
            message = 'Error fetching data from database'
            logging.exception(message)
            return jsonify({'flag': False, 'message': message})
        
        total_reports_query = 'SELECT id, COUNT(*) AS COUNT FROM `reports_queue`'
        total_count = list(reports_db.execute(total_reports_query)['COUNT'])[0]

        # Get report types
        query = 'SELECT * FROM `report_types`'
        report_types_df = reports_db.execute(query)

        respose_data = {
            'flag': True,
            'data': {
                'files': user_reports_data_json,
                'columns': list(user_reports_data),
                'report_types': list(report_types_df['report_type'].unique()),
                'pagination': {
                    'start': start + 1,
                    'end': end if end < len(user_reports_data_json) else len(user_reports_data_json),
                    'total': total_count}
                }
            }
        logging.info(f'Response data: {respose_data}')
        return jsonify(respose_data)
    except:
        logging.exception('Something went wrong while getting reports queue. Check trace.')
        response = {'flag': False, 'message': 'System error [/get_reports_queue]! Please contact your system administrator.'}
        return jsonify(response)

@app.route('/generate_reports', methods=['POST', 'GET'])
def generate_reports():
    # Get data from UI
    data = request.json
    requested_by = data.get('user', None)
    report_type = data.get('report_type', None)
    tenant_id = data.get('tenant_id', None)

    # Sanity check
    if requested_by is None:
        message = 'User not provided in request.'
        logging.error(message)
        return jsonify({'flag': False, 'message': message})
    
    if report_type is None:
        message = 'Report type not provided in request.'
        logging.error(message)
        return jsonify({'flag': False, 'message': message})

    # Generate a reference ID (10 digits)
    reference_id = uuid.uuid4().hex[:10].upper()

    # Generate file name if not given
    timestamp = datetime.now().strftime(f'%d%m%Y%H%M%S')
    file_name = f'{reference_id[:3]}-{timestamp}'

    # Add file to database
    reports_db = DB('reports', tenant_id=tenant_id, **db_config)

    insert_data = {
        'reference_id': reference_id,
        'requested_by': requested_by,
        'filename': file_name,
        'status': 'Processing'
    }
    reports_db.insert_dict(insert_data, 'reports_queue')

    # Produce to reports consumer
    produce('generate_report', {'tenant_id': tenant_id, 'report_type': report_type, **insert_data})

    return jsonify({'flag': True, 'message': f'The report will be available soon to download. (Ref No. {reference_id})'})

@app.route('/download_report', methods=['POST', 'GET'])
def download_report():
    # Get data from UI
    data = request.json
    logging.info(f'Recieved data: {data}')

    tenant_id = data.get('tenant_id', None)
    reference_id = data.get('reference_id', None)

    if reference_id is None:
        message = 'Reference ID is not provided.'
        logging.error(message)
        return jsonify({'flag': False, 'message': message})

    # Add file to database
    reports_db = DB('reports', tenant_id=tenant_id, **db_config)

    query = 'SELECT * FROM `reports_queue` WHERE `reference_id`=%s'
    report_info = reports_db.execute(query, params=[reference_id])

    report_file_name = list(report_info['filename'])[0]
    report_path = Path(f'./reports/{report_file_name}.xlsx')

    with open(report_path, 'rb') as f:
        report_blob = base64.b64encode(f.read())

    try:
        return jsonify({'flag': True, 'blob': report_blob.decode('utf-8'), 'filename': f'{report_file_name}.xlsx'})
    except:
        message = 'Something went wrong while downloading report.'
        logging.exception(message)
        return jsonify({'flag': False, 'message': message})
    

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-p', '--port', type=int, help='Port Number', default=5000)
    parser.add_argument('--host', type=str, help='Host', default='0.0.0.0')
    args = parser.parse_args()

    host = args.host
    port = args.port

    app.run(host=host, port=port, debug=True)
