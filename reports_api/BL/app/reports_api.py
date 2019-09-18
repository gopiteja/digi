"""
Author: Ashyam
Created Date: 18-02-2019
"""
import argparse
import json

from flask import Flask, request, jsonify
from flask_cors import CORS
from pathlib import Path

try:
    from app import app
    from app.ace_logger import Logging
except:
    from ace_logger import Logging
    app = Flask(__name__)
    CORS(app)

logging = Logging()

from py_zipkin.zipkin import zipkin_span, ZipkinAttrs, create_http_headers_for_new_span

def http_transport(encoded_span):
    # The collector expects a thrift-encoded list of spans. Instead of
    # decoding and re-encoding the already thrift-encoded message, we can just
    # add header bytes that specify that what follows is a list of length 1.
    body =encoded_span
    requests.post(
            'http://servicebridge:5002/zipkin',
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

        # Sanity check
        if user is None:
            message = 'User not provided in request.'
            logging.error(message)
            return jsonify({'flag': False, 'message': message})

        # Connect to reports database
        reports_db_config = {
            'host': 'reports_db',
            'tenant_id': tenant_id
        }
        reports_db = DB('reports_queue', **reports_db_config)

        # Fetch reports
        logging.debug(f'Fetching reports for user `{user}`')
        query = 'SELECT * FROM `reports_queue` WHERE `requested_by`=%s'
        try:
            user_reports_data = reports_db.execute(query, params=[user])
            user_reports_data_json = user_reports_data.to_dict('records')
        except:
            message = 'Error fetching data from database'
            logging.exception(message)
            return jsonify({'flag': False, 'message': message})

        respose_data = {
            'flag': True,
            'data': {
                'files': user_reports_data_json,
                'columns': list(user_reports_data)
                }
            }
        logging.info(f'Response data: {respose_data}')
        return jsonify(respose_data)
    except:
        logging.exception('Something went wrong while getting reports queue. Check trace.')
        response = {'flag': False, 'message': 'System error [/get_reports_queue]! Please contact your system administrator.'}
        return jsonify(response)

@app.route('/generate_report', methods=['POST', 'GET'])
def generate_report():
    # Get data from UI

    # Generate a reference ID

    # Check if reference ID already exists

    # Generate file name if not given

    # Add file to database

    # Produce to reports consumer

    return ''

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-p', '--port', type=int, help='Port Number', default=5000)
    parser.add_argument('--host', type=str, help='Host', default='0.0.0.0')
    args = parser.parse_args()

    host = args.host
    port = args.port

    app.run(host=host, port=port, debug=True)
