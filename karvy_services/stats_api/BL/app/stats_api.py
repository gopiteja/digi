"""
Author: Ashyam
Created Date: 18-02-2019
"""
import argparse
import requests
import json
import uuid

from db_utils import DB

from datetime import datetime
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from pathlib import Path

try:
    from app import app
    from app.ace_logger import Logging
    from app.producer import produce
except:
    from ace_logger import Logging
    from producer import produce
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

@app.route('/karvy_chart_data', methods=['POST', 'GET'])
def chart_data():
    try:
        ui_data = request.json
        logging.info(f'Data recieved: {ui_data}')
        header = ui_data['header']
        tenant_id = ui_data.get('tenant_id',None)
        data = {}
        if header.lower() == 'snapshot details':
            db_config = {
                'host': '3.208.195.34',
                'port': '3306',
                'user': 'root',
                'password': 'AlgoTeam123',
                'tenant_id': tenant_id
            }

            db = DB('karvy_preprocessed',**db_config)

            test_bank = db.get_all('karvy_bank_test')

            match = []
            unmatch = []
            logging.debug(test_bank['Bank_Name'].unique().tolist())

            for bank in test_bank['Bank_Name'].unique().tolist():
                tot = test_bank[test_bank['Bank_Name'] == '{}'.format(bank)]['diff_amount'].sum() // 5
                tot_un = test_bank[test_bank['Bank_Name'] == '{}'.format(bank)]['Unmatched_Amount'].sum() //5
                match.append(tot)
                unmatch.append(tot_un)
                
            legend_data = test_bank['Bank_Name'].unique().tolist()
            values = []
            chart_type = "stacked_column"
            
            logging.debug(match)
            logging.debug(unmatch)

            stacked_cols = {}
            stacked_cols['Matched'] = match
            stacked_cols['Un Matched'] = unmatch

            data = {
                "axiscolumns" : legend_data,
                "barname": "Cases",
                "axisvalues": values,
                "stackedcolumns":stacked_cols,
                "heading":'Amount of transactions',
                "subheading": '',
                "chart_type": chart_type
            }
    except:
        logging.exception(f"Unexpected error in snapshot")
 
    logging.info(f'Data returned: {data}')
    return jsonify(data)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-p', '--port', type=int, help='Port Number', default=5000)
    parser.add_argument('--host', type=str, help='Host', default='0.0.0.0')
    args = parser.parse_args()

    host = args.host
    port = args.port

    app.run(host=host, port=port, debug=True)
