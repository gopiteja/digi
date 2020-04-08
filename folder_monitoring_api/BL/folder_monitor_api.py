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

def watch(path_to_watch, output_path, tenant_id, workflow):
    logging.info('Watch folder started.')

    path_to_watch = Path('./input').absolute() / Path(path_to_watch)
    output_path = Path('./output').absolute() / Path(output_path)

    logging.debug(f'Watching folder: {path_to_watch}')
    logging.debug(f'Output folder: {output_path}')

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
            shutil.move(file_path, output_path / (unique_id + file_path.suffix))
            logging.debug(f' - {file_path.name} moved to {output_path.absolute()} directory')

            data = {
                'case_id': unique_id,
                'file_name': unique_id + file_path.suffix,
                'files': [unique_id + file_path.suffix],
                'source': [str(file_path.parents[0])],
                'file_path': str(file_path),
                'original_file_name': [file_path.name],
                'tenant_id': tenant_id,
                'type': 'file_ingestion',
                'workflow': workflow
            }

            query = 'SELECT * FROM `message_flow` WHERE `listen_to_topic`=%s AND `workflow`=%s'
            message_flow = kafka_db.execute(query, params=['folder_monitor', workflow])

            if message_flow.empty:
                logging.error('`folder_monitor` is not configured correctly in message flow table.')
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
        logging.debug(f'Connecting to tenant {tenant_id}')

        db = DB('io_configuration', tenant_id=tenant_id, **db_config)
        
        input_config = db.get_all('input_configuration', condition={'active': 0})
        output_config = db.get_all('output_configuration')

        logging.debug(f'Input Config: {input_config.to_dict()}')
        logging.debug(f'Output Config: {output_config.to_dict()}')

        # Sanity checks
        if (input_config.loc[input_config['type'] == 'Document'].empty
                or output_config.loc[input_config['type'] == 'Document'].empty):
            message = 'Input/Output not configured in DB.'
            logging.error(message)
            return jsonify({'flag': False, 'message': message})

        for index, row in input_config.iterrows():
            input_path = row['access_1']
            output_path = output_config.ix[row['output']]['access_1']
            workflow = row['workflow']

            logging.debug(f'Input path: {input_path}')
            logging.debug(f'Output path: {output_path}')

            if (input_path is None or not input_path
                    or output_path is None or not output_path):
                message = 'Input/Output is empty/none in DB.'
                logging.error(message)
                return jsonify({'flag': False, 'message': message})

            input_path = Path('./input').absolute() / Path(input_path)
            output_path = Path('./output').absolute() / Path(output_path)

            # Only watch the folder if both are valid directory
            if input_path.is_dir() and output_path.is_dir():
                try:
                    watch_thread = threading.Thread(target=watch, args=(input_path, output_path, tenant_id, workflow))
                    watch_thread.start()
                    message = f'Succesfully watching {input_path}. Updating active IO config to 1.'
                    logging.info(message)
                    query = 'UPDATE `input_configuration` SET `active`=1 WHERE `id`=%s'
                    db.execute(query, params=[index])
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

@app.route("/get_upload_files", methods = ["GET", "POST"])
def get_upload_files():
    try:
        print('Hit. Getting files ')
        upload_files = os.listdir('/app/upload/digi')
        print('Upload files are ', upload_files)
        return jsonify({'data':{'filename':list(upload_files)}})
    except Exception as e:
        print('Error getting upload files ', e)


@app.route("/upload_selected_files", methods = ["GET", "POST"])
def upload_selected_files():
    print("REUQEST IS ",request.json)
    print('reuest is ', type(request.json))
    upload_files = request.json
    upload_files = upload_files['selected_files']
    print('upload files are ', upload_files)
    for up_file in upload_files:
        try:
            old_path = '/app/upload/digi/' + up_file
            new_path = '/app/input/digi/' + up_file
            print('uploading ', up_file)
            shutil.copyfile(old_path, new_path)
        except Exception as e:
            print('Error uploading files ', e)
            return jsonify({"message":"Error uploading files", "flag":False})
    return jsonify({"message":"Uploaded Successfully", "flag":True})
        



if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-p', '--port', type=int, help='Port Number', default=5012)
    parser.add_argument('--host', type=str, help='Host', default='0.0.0.0')
    args = parser.parse_args()

    host = args.host
    port = args.port

    app.run(host=host, port=port, debug=False)
