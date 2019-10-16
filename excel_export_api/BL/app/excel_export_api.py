"""
Author: Ashyam
Created Date: 18-02-2019
"""
import argparse
import json
import openpyxl
import os

from flask import Flask, request, jsonify
from flask_cors import CORS
from pathlib import Path
from py_zipkin.zipkin import zipkin_span, ZipkinAttrs, create_http_headers_for_new_span

from ace_logger import Logging
from db_utils import DB

try:
    from app.excel_export import ExportExcel
except:
    from excel_export import ExportExcel
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

@app.route('/export_excel', methods=['POST', 'GET'])
def export_excel():
    """
    Export the results into an excel sheet.

    Args:
        output_dir (str/Path): Where the excel file(s) should be exported.
        file_name (str): Name of the exported file. This will be ignored if the
            excel format configured if FPD. (See README.md for details)

    Returns:
        flag (bool): Flag for success status.
        message (str): Message to UI.
    """
    with zipkin_span(service_name='excel_export_api', span_name='export_excel', 
            transport_handler=http_transport, port=5007, sample_rate=0.5,) as  zipkin_context:
        try:
            logging.info('Export Excel API called.')

            content = request.json
            logging.debug(f'Data recieved: {content}')

            case_id = content.get('case_id', None)
            tenant_id = content.get('tenant_id', None) 

            zipkin_context.update_binary_annotations({'Tenant':tenant_id})
            # Sanity checks
            if case_id is not None and not case_id.strip():
                message = f'Case ID cant be empty string.'
                logging.error(message)
                return jsonify({'flag': False, 'message': message})

            # * STEP 1 - Get data to export
            db = DB('extraction', tenant_id=tenant_id, **db_config)

            if case_id is not None:
                data = db.get_all('combined', condition={'case_id': case_id})
            else:
                data = db.get_all('combined')
            
            if data.empty:
                message = 'No data or case ID not in combined table. Merge table before exporting.'
                logging.error(message)
                return jsonify({'flag': True, 'message': message})

            # * STEP 2 - Getting export configuration
            excel_export_db = DB('excel_export', tenant_id=tenant_id, **db_config)

            # Get active configuration
            all_configs = excel_export_db.get_all('configuration')
            all_active_configs = all_configs.loc[all_configs['active'] == 1]
            
            if all_configs.empty:
                message = 'There are no configuration made. Please create a configuration first.'
                logging.error(message)
                return jsonify({'flag': False, 'message': message})

            if len(all_active_configs) > 1:
                logging.warning('Multiple active configurations found. Using the first one.')
            elif all_active_configs.empty:
                message = 'There are no active configuration. Activate a configuration to export in excel.'
                logging.warning(message)
                return jsonify({'flag': False, 'message': message})
            
            active_config = all_active_configs.to_dict('records')[0]
            logging.info(f'Configuration: {active_config}')

            # * STEP 3 - Get all the configuration parameters in the right format
            export_type = active_config['export_type']
            save_type = active_config['save_type']
            custom_name = active_config['custom_name']

            if active_config['exclude_fields'] is not None:
                exclude_fields = active_config['exclude_fields'].split(',')
            else:
                exclude_fields = []

            try:
                field_mapping = json.loads(active_config['field_mapping'])
            except:
                field_mapping = {}

            ee = ExportExcel(export_type, exclude_fields, save_type, custom_name, field_mapping)

            return jsonify(ee.export(data))
        except Exception as e:
            return jsonify({'flag':False, 'message':'System error! Please contact your system administrator.'})

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-p', '--port', type=int, help='Port Number', default=5000)
    parser.add_argument('--host', type=str, help='Host', default='0.0.0.0')
    args = parser.parse_args()

    host = args.host
    port = args.port

    app.run(host=host, port=port, debug=True)
