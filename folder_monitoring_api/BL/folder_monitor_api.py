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

# from email.mime.multipart import MIMEMultipart
# from email.mime.text import MIMEText
# from email.mime.base import MIMEBase
# from email import encoders
# import smtplib

from producer import produce
from db_utils import DB
from ace_logger import Logging

app = Flask(__name__)
cors = CORS(app)
logging = Logging()

# path_to_watch = Path('./input')
# output_path = Path('./output')

def watch(path_to_watch, output_path):
    logging.info('Watch folder started.')
    logging.debug(f'Watching folder: {path_to_watch}')

    db_config = {
        'host': 'queue_db',
        'port': '3306',
        'user': 'root',
        'password': 'root'
    }
    queue_db = DB('queues', **db_config)
    # queue_db = DB('queues')

    stats_db_config = {
            'host': 'stats_db',
            'user': 'root',
            'password': 'root',
            'port': '3306'
        }

    stats_db = DB('stats', **stats_db_config)

    query = "SELECT id, case_id, batch_id from process_queue"
    process_queue = queue_db.execute(query)
    existing_case_ids = list(process_queue.case_id)
    existing_batch_ids = list(process_queue.batch_id)
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

            # Get unique case ID. Check whether generated case ID already exists
            # while True:
            #     unique_id = uuid.uuid4().hex[:7].upper()
            #     if unique_id not in existing_case_ids:
            #         break

            unique_id = file_path.stem # Some clients require file name as Case ID

            # Create Batch ID
            current_date = date.today()
            counter = 0
            while True:
                batch_id = f'{current_date.year}{current_date.month}{current_date.day}{counter}'
                counter += 1
                if batch_id not in existing_batch_ids:
                    break

            process_queue_df = queue_db.get_all('process_queue')
            case_id_process = process_queue_df.loc[process_queue_df['file_name'] == file_path.name]
            if case_id_process.empty:
                insert_query = ('INSERT INTO `process_queue` (`file_name`, `batch_id`, `case_id`, `reference_number`, `file_path`, `source_of_invoice`) '
                    'VALUES (%s, %s, %s, %s, %s, %s)')
                params = [file_path.name, batch_id, unique_id, file_path.stem, str(file_path.parent.absolute()), str(file_path.parent).split('/')[-1]]
                queue_db.execute(insert_query, params=params)
                logging.debug(f' - {file_path.name} inserted successfully into the database')
            else:
                logging.debug("File already exists in the database")
            #Inserting ocr data in ocr_info table
            ocr_info_df = queue_db.get_all('ocr_info',discard=['ocr_data','xml_data','ocr_text'])
            case_id_ocr_info = ocr_info_df.loc[ocr_info_df['case_id'] == unique_id]
            if case_id_ocr_info.empty:
                insert_query = 'INSERT INTO `ocr_info` (`case_id`) VALUES (%s)'
                params = [unique_id]
                queue_db.execute(insert_query, params=params)
                logging.debug(f' - OCR info for {file_path.name} inserted successfully into the database')

                # Stats
                query = "select * from process_queue where created_date = CURDATE()"
                no_files = len(list(queue_db.execute(query).case_id))
                query = "SELECT * from invoices_uploaded where date = CURDATE()"
                current_date = stats_db.execute(query)
                if current_date.empty:
                    insert_query = f'INSERT INTO `invoices_uploaded` (`no_of_files`) VALUES ({no_files})'
                    stats_db.execute(insert_query)
                else:
                    update_query = f'Update invoices_uploaded set `no_of_files` = {no_files} where date = CURDATE()'
                    stats_db.execute(update_query)
            else:
                logging.debug("File already exists in the ocr info database")

            #Inserting into trace_info table as well
            trace_info_df = queue_db.get_all('trace_info',discard=['last_updated_dates','queue_trace','operators'])
            case_id_trace_info = trace_info_df.loc[trace_info_df['case_id'] == unique_id]
            if case_id_trace_info.empty:
                insert_query = 'INSERT INTO `trace_info` (`case_id`) VALUES (%s)'
                params = [unique_id]
                queue_db.execute(insert_query, params=params)
                logging.debug(f' - Trace info for {file_path.name} inserted successfully into the database')
            else:
                logging.debug("File already exists in the Trace info database")


            time.sleep(3) # Buffer time. Required to make sure files move without any error.
            # Delete file for Alorica
            # os.remove(file_path)
            shutil.copy(file_path, output_path / (unique_id + file_path.suffix))
            # shutil.copyfile(file_path, 'angular/' + (unique_id + file_path.suffix))
            # shutil.move(file_path, 'training_ui/' + (unique_id + file_path.suffix))
            logging.debug(f' - {file_path.name} moved to {output_path.absolute()} directory')

            # TODO - Should not be a list. Change in abbyy detection function
            data = {
                'case_id': unique_id,
                'file_name': unique_id + file_path.suffix,
                'files': [unique_id + file_path.suffix],
                'source': [str(file_path.parent).split('/')[-1]],
                'original_file_name': [file_path.name],
                'tenant_id': None,
                'type': 'file_ingestion'
            }

            common_db_config = {
                'host': 'common_db',
                'port': '3306',
                'user': 'root',
                'password': 'root'
            }
            kafka_db = DB('kafka', **common_db_config)
            # kafka_db = DB('kafka')

            message_flow = kafka_db.get_all('message_flow')
            topic = list(message_flow.listen_to_topic)[0] # Get the first topic from message flow

            logging.info(f'Producing to topic {topic}')
            produce(topic, data)


def trigger_email_function(attachment_paths,fromaddr = "testalgox123@gmail.com",password = "@lgoSecure" ):
    toaddr = "priyatham.katta@algonox.com, ashish.khan@algonox.com, bharat.vavilapalli@algonox.com, sankar.v@algonox.com, rahul.saxena@algonox.com, srinivas.sanke@algonox.com, abhishek.alluri@algonox.com"

    msg = MIMEMultipart()

    msg['From'] = fromaddr
    msg['To'] = toaddr
    msg['Subject'] = "MIS Report"

    body = "Please find attached the MIS report and Processed files report"

    msg.attach(MIMEText(body, 'plain'))

    # filename = "MIS_report.xlsx"
    for attachment_path in attachment_paths:
        file_name = attachment_path.split('/')[-1]
        attachment = open(attachment_path, "rb")

        part = MIMEBase('application', 'octet-stream')
        part.set_payload((attachment).read())
        encoders.encode_base64(part)
        part.add_header('Content-Disposition', 'attachment; filename="%s"' % file_name)
        msg.attach(part)

    server = smtplib.SMTP('smtp.gmail.com', 587)
    server.starttls()

    server.login(fromaddr, password)

    text = msg.as_string()
    server.sendmail(fromaddr, toaddr, text)
    server.quit()


@app.route('/generate_report', methods=['POST', 'GET'])
def generate_report():
    try:
        extraction_db_config = {
            'host': 'extraction_db',
            'port': '3306',
            'user': 'root',
            'password': 'root'
        }
        extraction_db = DB('extraction', **extraction_db_config)

        queue_db_config = {
            'host': 'queue_db',
            'port': '3306',
            'user': 'root',
            'password': 'root'
        }
        queue_db = DB('queues', **queue_db_config)

        ocr_df = extraction_db.get_all('ocr')
        select_columns = ['created_date', 'case_id', 'Document Heading', 'PO Number', 'Invoice Number',	'Invoice Date',	'Invoice Total', 'Invoice Base Amount',	'DRL GSTIN', 'Vendor GSTIN', 'Billed To (DRL Name)', 'Vendor Name',	'GST Percentage', 'Digital Signature']

        filtered_df = ocr_df[select_columns]

        # Export Excel
        filtered_df.to_excel("output/MIS Report.xlsx")

        queue_query = "SELECT id, case_id, queue, created_date from `process_queue`"
        queue_df = queue_db.execute(queue_query)
        # Export Excel
        queue_df.to_excel("output/Queue Report.xlsx")

        combined_df = extraction_db.get_all('combined')
        combined_df = extraction_db.get_latest(combined_df,'case_id','created_date')
        combined_columns = list(combined_df)
        combined_columns = [col for col in combined_columns if col not in ['highlight']]
        combined_df = combined_df[combined_columns]
        combined_df.to_excel("output/processed_files_master.xlsx")

        # trigger_email_function(["output/MIS Report.xlsx","output/processed_files_master.xlsx"])
        logging.info('Sent Mail Successfully')
        return "Successfully generated report"
    except Exception as e:
        return jsonify({'flag': False, 'message':'System error! Please contact your system administrator.'})

@app.route('/folder_monitor', methods=['POST', 'GET'])
def folder_monitor():
    try:
        db_config = {
            'host': 'common_db',
            'port': '3306',
            'user': 'root',
            'password': 'root'
        }
        db = DB('io_configuration', **db_config)
        # db = DB('io_configuration')

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
                watch_thread = threading.Thread(target=watch, args=(input_path, output_path))
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
