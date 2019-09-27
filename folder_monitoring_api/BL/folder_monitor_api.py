import argparse
import json
import io
import os
import requests
import shutil
import time
import threading
import uuid

from datetime import datetime, date
from flask_cors import CORS
from flask import Flask, jsonify, request
from pathlib import Path

from producer import produce
from db_utils import DB
from ace_logger import Logging

app = Flask(__name__)
cors = CORS(app)
logging = Logging()

db_config = {
    'host': os.environ['HOST_IP'],
    'user': os.environ['LOCAL_DB_USER'],
    'password': os.environ['LOCAL_DB_PASSWORD'],
    'port': os.environ['LOCAL_DB_PORT']
}

def watch(path_to_watch, output_path, tenant_id):
    logging.info('Watch folder started.')
    logging.debug(f'Watching folder: {path_to_watch}')

    queue_db = DB('queues', tenant_id=tenant_id, **db_config)
    stats_db = DB('stats', tenant_id=tenant_id, **db_config)
    kafka_db = DB('kafka', tenant_id=tenant_id, **db_config)

    supported_files = ['.pdf', '.jpeg', '.jpg', '.png']

    while True:
        time.sleep(5)
        for file_path in path_to_watch.glob('*'):
            logging.debug(f'File detected: {file_path}')

            if file_path is not os.path.isdir(file_path):
                if file_path.suffix.lower() not in supported_files:
                    logging.warning(f'`{file_path.name}` is unsupported format. Supported formats: {supported_files}.')
                    logging.warning('Skipping.')
                    continue

            unique_id = file_path.stem # Some clients require file name as Case ID

            time.sleep(3) # Buffer time. Required to make sure files move without any error.
            shutil.copy(file_path, output_path / (unique_id + file_path.suffix))
            logging.debug(f' - {file_path.name} moved to {output_path.absolute()} directory')

            data = {
                'case_id': unique_id,
                'file_name': unique_id + file_path.suffix,
                'files': [unique_id + file_path.suffix],
                'source': [str(file_path.parent).split('/')[-1]],
                'file_path': file_path,
                'original_file_name': [file_path.name],
                'tenant_id': tenant_id,
                'type': 'file_ingestion'
            }

            query = 'SELECT * FROM `message_flow` WHERE `listen_to_topic`=%s'
            message_flow = kafka_db.execute(query, params=['folder_monitor'])

            if message_flow.empty:
                logging.error('`folder_monitor` is not configured in message flow table.')
            else:
                topic = list(message_flow.send_to_topic)[0]

                if topic is not None:
                    logging.info(f'Producing to topic {topic}')
                    produce(topic, data)
                else:
                    logging.info(f'There is no topic to send to for `folder_monitor`. [{topic}]')

@app.route('/folder_monitor', methods=['POST', 'GET'])
def folder_monitor():
    try:
        data = request.json

        tenant_id = data.get('tenant_id', None)

        db = DB('io_configuration', tenant_id=tenant_id, **db_config)
        
        input_config = db.get_all('input_configuration')
        output_config = db.get_all('output_configuration')

        # Sanity checks
        if (input_config.loc[input_config['type'] == 'Document'].empty
                or output_config.loc[input_config['type'] == 'Document'].empty):
            message = 'Input/Output not configured in DB.'
            logging.error(message)
            return jsonify({'flag': False, 'message': message})
        else:
            input_path = input_config.iloc[0]['access_1']
            output_path = output_config.iloc[0]['access_1']

        logging.debug(f'Input path: {input_path}')
        logging.debug(f'Output path: {output_path}')

        if (input_path is None or not input_path
                or output_path is None or not output_path):
            message = 'Input/Output is empty/none in DB.'
            logging.error(message)
            return jsonify({'flag': False, 'message': message})

        input_path = Path(input_path)
        output_path = Path(output_path)

        # Only watch the folder if both are valid directory
        if input_path.is_dir() and output_path.is_dir():
            try:
                watch_thread = threading.Thread(target=watch, args=(input_path, output_path, tenant_id))
                watch_thread.start()
                message = f'Succesfully watching {input_path}'
                logging.info(output_path)
                return jsonify({'flag': True, 'message': message})
            except Exception as e:
                message = f'Error occured while watching the folder.'
                logging.exception(message)
                return jsonify({'flag': False, 'message': message})
        else:
            message = f'{input_path}/{output_path} not a directory'
            logging.error(message)
            return jsonify({'flag': True, 'message': message})
    except Exception as e:
        logging.exception('Something went wrong watching folder. Check trace.')
        return jsonify({'flag': False, 'message':'System error! Please contact your system administrator.'})


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-p', '--port', type=int, help='Port Number', default=5012)
    parser.add_argument('--host', type=str, help='Host', default='0.0.0.0')
    args = parser.parse_args()

    host = args.host
    port = args.port

    app.run(host=host, port=port, debug=False)
