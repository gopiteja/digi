import argparse
import json
import requests
from py_zipkin.zipkin import zipkin_span, ZipkinAttrs, create_http_headers_for_new_span

from flask import Flask, request, jsonify
from flask_cors import CORS
from ace_logger import Logging
from db_utils import DB

try:
    from app.table_predict import complex_table_prediction
    from app.table_predict_abbyy import table_prediction_abbyy
    from app.table_predict_abbyy import table_training_abbyy
    from app.complex_data_table_generator import complex_data_table_generator
    from app.find_intersections import find_intersections
    with open('app/parameters.json') as f:
        parameters = json.loads(f.read())
except:
    from ace_logger import Logging
    from db_utils import DB
    from table_predict import complex_table_prediction
    from table_predict_abbyy import table_prediction_abbyy
    from table_predict_abbyy import table_training_abbyy
    from complex_data_table_generator import complex_data_table_generator
    from find_intersections import find_intersections
    with open('parameters.json') as f:
        parameters = json.loads(f.read())

try:
    from app import app
except:
    app = Flask(__name__)
    CORS(app)


def http_transport(encoded_span):
    body = encoded_span
    requests.post(
        'http://servicebridge:5002/zipkin',
        data=body,
        headers={'Content-Type': 'application/x-thrift'}, )


logging = Logging()


@zipkin_span(service_name='table_api', span_name='apply_business_rules')
def predict_with_template(case_id, template_name, tenant_id=None):
    logging.info(f'in predict with template')
    queue_db_config = {
        'host': os.environ['HOST_IP'],
        'port': 3306,
        'user': os.environ['LOCAL_DB_USER'],
        'password': os.environ['LOCAL_DB_PASSWORD'],
        'tenant_id': tenant_id
    }
    queue_db = DB('queues', **queue_db_config)
    # queue_db = DB('queues')

    query = 'SELECT * FROM `process_queue` WHERE `case_id`=%s'
    case_data = queue_db.execute(query, params=[case_id])
    # process_queue = queue_db.get_all('process_queue')
    # case_data = process_queue.loc[process_queue['case_id'] == case_id]
    file_name = list(case_data.file_name)[0]

    query = 'SELECT * FROM `ocr_info` WHERE `case_id`=%s'
    params = [case_id]
    ocr_info = queue_db.execute(query, params=params)
    ocr_data = json.loads(list(ocr_info.ocr_data)[0])
    xml_string = list(ocr_info.xml_data)[0]

    table_db_config = {
        'host': os.environ['HOST_IP'],
        'port': 3306,
        'user': os.environ['LOCAL_DB_USER'],
        'password': os.environ['LOCAL_DB_PASSWORD'],
        'tenant_id': tenant_id
    }
    table_db = DB('table_db', **table_db_config)
    # table_db = DB('table_db')

    query = 'SELECT * FROM `table_info` WHERE `template_name`=%s'
    # table_info_df = table_db.get_all('table_info')

    template_name = template_name.strip()
    logging.debug(f'template name `{template_name}`')

    # template_data = table_info_df.loc[table_info_df['template_name'] == template_name]
    template_data = table_db.execute(query, params=[template_name])

    table_list = template_data.to_dict(orient='records')
    table_data = []
    for table in table_list:
        method = table.pop('method')
        trained_data = json.loads(table.pop('table_data'))
        trained_data['headerCheck'] = table.pop('header_check')
        trained_data['footerCheck'] = table.pop('footer_check')
        file_path = f'./invoice_files/{file_name}'

        if method == 'abbyy':
            logging.debug(f'Running `table_predict_abbyy`')
            predicted_table = table_prediction_abbyy(ocr_data, parameters['default_img_width'], trained_data, file_path, xml_string=xml_string)
            table_data.append([predicted_table['table'][0][0]])
        elif method == 'tnox':
            logging.debug(f'Running `complex_table_prediction`')
            predicted_table = complex_table_prediction(ocr_data, file_name, trained_data)
            try:
                table_data.append([predicted_table['table'][0][0]])
            except:
                table_data.append([])
        else:
            message = 'Unknown table prediction method `{method}`'
            logging.info(message)
            return {'flag': False, 'message': message}

    extraction_db_config = {
        'host': os.environ['HOST_IP'],
        'port': 3306,
        'user': os.environ['LOCAL_DB_USER'],
        'password': os.environ['LOCAL_DB_PASSWORD'],
        'tenant_id': tenant_id
    }
    extraction_db = DB('extraction', **extraction_db_config)
    # extraction_db = DB('extraction')

    queue_db_config = {
        'host': os.environ['HOST_IP'],
        'port': 3306,
        'user': os.environ['LOCAL_DB_USER'],
        'password': os.environ['LOCAL_DB_PASSWORD'],
        'tenant_id': tenant_id
    }
    queue_db = DB('queues', **queue_db_config)

    stats_db_config = {
        'host': os.environ['HOST_IP'],
        'user': os.environ['LOCAL_DB_USER'],
        'password': os.environ['LOCAL_DB_PASSWORD'],
        'port': os.environ['LOCAL_DB_PORT'],
        'tenant_id': tenant_id
    }

    stats_db = DB('stats', **stats_db_config)

    update_params = {
        'update': {
            'Table': json.dumps(table_data)
        },
        'where': {
            'case_id': case_id
        }
    }
    if extraction_db.update('ocr', **update_params):
        audit_data = {
            "type": "update", "last_modified_by": "Table Consumer", "table_name": "ocr", "reference_column": "case_id",
            "reference_value": case_id, "changed_data": json.dumps(update_params['update'])
        }
        stats_db.insert_dict(audit_data, 'audit')
        return {'flag': True, 'data': table_data}
    else:
        message = f'Error updating table in OCR table for case ID `{case_id}`.'
        logging.info(message)
        return {'flag': False, 'message': message}


@app.route('/extract_header', methods=['POST', 'GET'])
def extract_header():
    data = request.json

    case_id = data['case_id']
    hors = data['hors']
    vers = data['vers']
    page = data['page']
    ocr_data = data['ocr_data']

    hors_formatted = []
    vers_formatted = []

    for line in hors:
        x1, y1 = line['l'], line['t']
        x2, y2 = x1 + line['w'], y1
        hors_formatted.append([(x1, y1), (x2, y2)])

    for line in vers:
        x1, y1 = line['l'], line['t']
        x2, y2 = x1, y1 + line['h']
        vers_formatted.append([(x1, y1), (x2, y2)])

    # queue_db_config = {
    #     'host': os.environ['HOST_IP'],
    #     'port': 3306,
    #     'user': os.environ['LOCAL_DB_USER'],
    #     'password': os.environ['LOCAL_DB_PASSWORD']
    # }
    # queue_db = DB('queues', **queue_db_config)
    # queue_db = DB('queues')

    # query = 'SELECT * FROM `ocr_info` WHERE `case_id`=%s'
    # ocr_info = queue_db.execute(query, params=[case_id])

    # try:
    #     ocr_data = list(ocr_info['ocr_data'])[0]
    # except:
    #     message = f'No OCR data found for case `{case_id}`'
    #     logging.exception(message)
    #     return jsonify({'flag': False, 'message': message})

    try:
        ocr_page = ocr_data[page]
    except KeyError:
        message = f'Page number ({page}) exceeds max page ({len(ocr_data)})'
        logging.warning(message)
        return jsonify({'flag': False, 'message': message})

    try:
        logging.debug(f'Hors: {hors_formatted}')
        logging.debug(f'Vers: {vers_formatted}')
        intersections = find_intersections(hors_formatted, vers_formatted)
    except:
        message = f'Error occured while finding intersection. Check trace.'
        logging.exception(message)
        return jsonify({'flag': False, 'message': message})

    try:
        logging.debug(f'Intersections: {intersections}')
        data = complex_data_table_generator(ocr_page, intersections)
    except:
        message = f'Error occured while generating headers. Check trace.'
        logging.exception(message)
        return jsonify({'flag': False, 'message': message})

    return jsonify(data)


@app.route('/predict_with_ui_data', methods=['POST', 'GET'])
def predict_with_ui_data():
    with zipkin_span(service_name='table_api', span_name='predict_with_ui_data',
                     transport_handler=http_transport,
                     # port=5014,
                     sample_rate=0.5, ):
        try:
            data = request.json
            logging.info(f'data{data}')
            table_data = data['table_data']
            method = data['method']
            case_id = data['case_id']
            image_width = data['img_width']
            tenant_id = data['tenant_id'] if 'tenant_id' in data else None

            queue_db_config = {
                'host': os.environ['HOST_IP'],
                'port': 3306,
                'user': os.environ['LOCAL_DB_USER'],
                'password': os.environ['LOCAL_DB_PASSWORD'],
                'tenant_id': tenant_id
            }
            queue_db = DB('queues', **queue_db_config)
            # queue_db = DB('queues')

            process_queue = queue_db.get_all('process_queue')
            case_data = process_queue.loc[process_queue['case_id'] == case_id]

            query = 'SELECT * FROM `ocr_info` WHERE `case_id`=%s'
            params = [case_id]
            ocr_info = queue_db.execute(query, params=params)
            ocr_data = json.loads(list(ocr_info.ocr_data)[0])
            xml_string = list(ocr_info.xml_data)[0]

            # ocr_data = json.loads(list(case_data.ocr_data)[0])
            # xml_string = list(case_data.xml_data)[0]
            file_name = list(case_data.file_name)[0]

            file_path = f'./invoice_files/{file_name}'

            if method == 'abbyy':
                logging.debug(f'Running `table_predict_abbyy`')
                table_data = table_training_abbyy(ocr_data, image_width, table_data, xml_string, file_path)
            elif method == 'tnox':
                logging.debug(f'Running `complex_table_prediction`')
                table_data = complex_table_prediction(ocr_data, file_name, table_data['trained_data'])
            else:
                message = 'Unknown table prediction method `{method}`'
                logging.info(message)
                return jsonify({'flag': False, 'message': message})

            return jsonify({'flag': True, 'message': 'Predicted table.', 'data': table_data})
        except Exception as e:
            logging.exception(e)
            return jsonify({'flag': False, 'message': 'System error! Please contact your system administrator.'})
