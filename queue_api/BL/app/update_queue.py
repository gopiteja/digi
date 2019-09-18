import json
import traceback

from datetime import datetime, timedelta
from kafka import KafkaConsumer, TopicPartition
from random import randint
from time import sleep

from db_utils import DB

try:
    from app.producer import produce
    from app.ace_logger import Logging
except:
    from producer import produce
    from ace_logger import Logging

logging = Logging()

def update_queue_trace(queue_db, case_id, latest):
    queue_trace_q = "SELECT * FROM `trace_info` WHERE `case_id`=%s"
    queue_trace_df = queue_db.execute(queue_trace_q, params=[case_id])

    if queue_trace_df.empty:
        message = f' - No such case ID `{case_id}` in `trace_info`.'
        logging.error(f'ERROR: {message}')
        return {'flag': False, 'message': message}
    # Updating Queue Name trace
    try:
        queue_trace = list(queue_trace_df.queue_trace)[0]
    except:
        queue_trace = ''
    if queue_trace:
        queue_trace += ','+latest
    else:
        queue_trace = latest

    #Updating last_updated_time&date

    try:
        last_updated_dates = list(queue_trace_df.last_updated_dates)[0]
    except:
        last_updated_dates = ''
    if last_updated_dates:
        last_updated_dates += ',' + datetime.now().strftime(r'%d/%m/%Y %H:%M:%S')
    else:
        last_updated_dates = datetime.now().strftime(r'%d/%m/%Y %H:%M:%S')

    update = {'queue_trace': queue_trace}
    where = {'case_id': case_id}
    update_q = "UPDATE `trace_info` SET `queue_trace`=%s, `last_updated_dates`=%s WHERE `case_id`=%s"
    queue_db.execute(update_q, params=[queue_trace, last_updated_dates, case_id])

    return {'flag': True, 'message': 'Updated Queue Trace'}

def update_queue(data):
    try:
        verify_operator = data['operator']
    except:
        logging.debug("operator key not found")
        verify_operator = None

    # logging.debug(data.keys())

    if 'case_id' not in data or 'queue' not in data or 'fields' not in data:
        message = f'Invalid JSON recieved. MUST contain `case_id`, `queue` and `fields` keys.'
        logging.error(f'ERROR: {message}')
        return {'flag': False, 'message': message}

    case_id = data['case_id']
    queue = data['queue']

    if data is None or not data:
        message = f'Data not provided/empty dict.'
        logging.error(f'ERROR: {message}')
        return {'flag': False, 'message': message}

    if case_id is None or not case_id:
        message = f'Case ID not provided/empty string.'
        logging.error(f'ERROR: {message}')
        return {'flag': False, 'message': message}

    if queue is None or not queue:
        message = f'Queue not provided/empty string.'
        logging.error(f'ERROR: {message}')
        return {'flag': False, 'message': message}

    db_config = {
        'host': 'queue_db',
        'port': 3306,
        'user': 'root',
        'password': 'root'
    }
    db = DB('queues', **db_config)
    # db = DB('queues')

    stats_db_config = {
        'host': 'stats_db',
        'user': 'root',
        'password': 'root',
        'port': '3306'
    }

    stats_db = DB('stats', **stats_db_config)

    # Get latest data related to the case from invoice table
    invoice_files_df = db.get_all('process_queue')
    # latest_case_file = db.get_latest(invoice_files_df, 'case_id', 'created_date')
    latest_case_file = invoice_files_df
    case_files = latest_case_file.loc[latest_case_file['case_id'] == case_id]

    if case_files.empty:
        message = f'No case ID `{case_id}` found in process queue.'
        logging.error(f'ERROR: {message}')
        return {'flag': False, 'message': message}

    query = f'UPDATE `process_queue` SET `queue`=%s, `stats_stage`=%s WHERE `case_id`=%s'
    params = [queue,queue,case_id]
    update_status = db.execute(query, params=params)

    audit_data = {
            "type": "update", "last_modified_by": verify_operator, "table_name": "process_queue", "reference_column": "case_id",
            "reference_value": case_id, "changed_data": json.dumps({"queue": queue, "stats_stage": queue})
        }
    stats_db.insert_dict(audit_data, 'audit')

    if update_status:
        message = f'Updated queue for case ID `{case_id}` successfully.'
        logging.debug(f' -> {message}')
    else:
        message = f'Something went wrong updating queue. Check logs.'
        logging.error(f'ERROR: - {message}')
        return {'flag': False, 'message': message}

    # ! UPDATE TRACE INFO TABLE HERE
    update_queue_trace(db, case_id, queue)

    # # Inserting fields into respective tables
    # field_definition = db.get_all('field_definition')
    # tab_definition = db.get_all('tab_definition')

    # # Change tab ID to its actual names
    # for index, row in field_definition.iterrows():
    #     tab_id = row['tab_id']
    #     tab_name = tab_definition.loc[tab_id]['text']
    #     field_definition.loc[index, 'tab_id'] = tab_name

    # # Create a new dictionary with key as table, and value as fields dict (column name: value)
    # table_fields = {}
    # for unique_name, value in fields.items():
    #     unique_field_name = field_definition.loc[field_definition['unique_name'] == unique_name]

    #     if unique_field_name.empty:
    #         logging.debug(
    #             f'No unique field name for {unique_name}. Check `field_defintion` database.')
    #         continue
        
    #     tab_name = list(unique_field_name.tab_id)[0]
    #     table = list(tab_definition.loc[tab_definition['text'] == tab_name]['source'])[0]
    #     display_name = list(unique_field_name.display_name)[0]

    #     if table not in table_fields:
    #         table_fields[table] = {}

    #     table_fields[table][display_name] = value
    # logging.debug(f'Table <-> Fields: {table_fields}')

    # extraction_db_config = {
    #     'host': 'extraction_db',
    #     'port': 3306,
    #     'user': 'root',
    #     'password': 'root'
    # }
    # extraction_db = DB('extraction', **extraction_db_config)
    # # extraction_db = DB('extraction')

    # # ! GET HIGHLIGHT FROM PREVIOUS RECORD BECAUSE UI IS NOT SENDING
    # ocr_files_df = extraction_db.get_all('ocr')
    # latest_ocr_files = extraction_db.get_latest(
    #     ocr_files_df, 'case_id', 'created_date')
    # ocr_case_files = latest_ocr_files.loc[latest_ocr_files['case_id'] == case_id]
    # highlight = list(ocr_case_files.highlight)[0]

    # for table_name, fields_dict in table_fields.items():
    #     # Only in OCR table add the highlight
    #     if table_name == 'ocr':
    #         column_names = ['`case_id`', '`highlight`']
    #         params = [case_id, highlight]
    #     else:
    #         column_names = ['`case_id`']
    #         params = [case_id]

    #     for column, value in fields_dict.items():
    #         if column == 'Verify Operator':
    #             column_names.append(f'`{column}`')
    #             params.append(verify_operator)
    #         else:
    #             column_names.append(f'`{column}`')
    #             params.append(value)
    #     query_column_names = ', '.join(column_names)
    #     query_values_placeholder = ', '.join(['%s'] * len(params))

    #     query = f'INSERT INTO `{table_name}` ({query_column_names}) VALUES ({query_values_placeholder})'
    #     logging.debug(f'INFO: Inserting into {table_name}')

    #     extraction_db.execute(query, params=params)

    return {'flag': True, 'message': 'Changing queue completed.'}


def consume(broker_url='broker:9092'):
    try:
        route = 'update_queue'
        logging.info(f'Listening to topic: {route}')

        common_db_config = {
            'host': 'common_db',
            'port': '3306',
            'user': 'root',
            'password': 'root'
        }
        kafka_db = DB('kafka', **common_db_config)
        # kafka_db = DB('kafka')

        queue_db_config = {
            'host': 'queue_db',
            'port': '3306',
            'user': 'root',
            'password': 'root'
        }
        queue_db = DB('queues', **queue_db_config)
        # queue_db = DB('queues')

        message_flow = kafka_db.get_all('grouped_message_flow')

        consumer = KafkaConsumer(
            bootstrap_servers=broker_url,
            value_deserializer=lambda value: json.loads(value.decode()),
            auto_offset_reset='earliest',
            group_id='update_queue',
            api_version=(0,10,1),
            enable_auto_commit=False,
            session_timeout_ms=800001,
            request_timeout_ms=800002
        )
        logging.debug('Consumer object created.')

        parts = consumer.partitions_for_topic(route)
        if parts is None:
            logging.warning(f'No partitions for topic `{route}`')
            logging.debug(f'Creating Topic: {route}')
            produce(route, {})
            logging.info(f'Listening to topic `{route}`...')
            while parts is None:
                consumer = KafkaConsumer(
                    bootstrap_servers=broker_url,
                    value_deserializer=lambda value: json.loads(value.decode()),
                    auto_offset_reset='earliest',
                    group_id='sap_portal',
                    api_version=(0,10,1),
                    enable_auto_commit=False,
                    session_timeout_ms=800001,
                    request_timeout_ms=800002
                )
                parts = consumer.partitions_for_topic(route)
                logging.warning("No partition. In while loop. Make it stop")

        partitions = [TopicPartition(route, p) for p in parts]
        consumer.assign(partitions)

        query = 'SELECT * FROM `button_functions` WHERE `route`=%s'
        function_info = queue_db.execute(query, params=[route])
        in_progress_message = list(function_info['in_progress_message'])[0]
        failure_message = list(function_info['failure_message'])[0]
        success_message = list(function_info['success_message'])[0]

        for message in consumer:
            data = message.value
            logging.info(f'Message: {data}')

            try:
                case_id = data['case_id']
                functions = data['functions']
            except Exception as e:
                logging.warning(f'Recieved unknown data. [{data}] [{e}]')
                consumer.commit()
                continue

            # Get which button (group in kafka table) this function was called from
            group = data['group']

            # Get message group functions
            group_messages = message_flow.loc[message_flow['message_group'] == group]

            # If its the first function the update the progress count
            first_flow = group_messages.head(1)
            first_topic = first_flow.loc[first_flow['listen_to_topic'] == route]

            query = 'UPDATE `process_queue` SET `status`=%s, `total_processes`=%s, `case_lock`=1 WHERE `case_id`=%s'
            if not first_topic.empty:
                if list(first_flow['send_to_topic'])[0] is None:
                    queue_db.execute(query, params=[in_progress_message, len(group_messages), case_id])
                else:
                    queue_db.execute(query, params=[in_progress_message, len(group_messages) + 1, case_id])

            # Getting the correct data for the functions. This data will be passed through
            # rest of the chained functions.
            function_params = {}
            for function in functions:
                if function['route'] == route:
                    function_params = function['parameters']
                    break

            # Call the function
            try:
                logging.debug(f'Calling function `update_queue`')
                result = update_queue(function_params)
            except:
                # Unlock the case.
                logging.exception(f'Something went wrong while updating changes. Check trace.')
                query = 'UPDATE `process_queue` SET `status`=%s, `case_lock`=0, `failure_status`=1 WHERE `case_id`=%s'
                queue_db.execute(query, params=[failure_message, case_id])
                consumer.commit()
                continue

            # Check if function was succesfully executed
            if result['flag']:
                # If there is only function for the group, unlock case.
                if not first_topic.empty:
                    if list(first_flow['send_to_topic'])[0] is None:
                        # It is the last message. So update file status to completed.
                        query = 'UPDATE `process_queue` SET `status`=%s, `case_lock`=0, `completed_processes`=`completed_processes`+1 WHERE `case_id`=%s'
                        queue_db.execute(query, params=[success_message, case_id])
                        consumer.commit()
                        continue

                last_topic = group_messages.tail(
                    1).loc[group_messages['send_to_topic'] == route]
                
                # If it is not the last message, then produce to next function else just unlock case.
                if last_topic.empty:
                    # Get next function name
                    next_topic = list(
                        group_messages.loc[group_messages['listen_to_topic'] == route]['send_to_topic'])[0]

                    if next_topic is not None:
                        logging.debug('Not the last topic of the group.')
                        produce(next_topic, data)

                    # Update the progress count by 1
                    query = 'UPDATE `process_queue` SET `status`=%s, `completed_processes`=`completed_processes`+1 WHERE `case_id`=%s'
                    queue_db.execute(query, params=[success_message, case_id])
                    consumer.commit()
                else:
                    # It is the last message. So update file status to completed.
                    logging.debug('Last topic of the group.')
                    query = 'UPDATE `process_queue` SET `status`=%s, `case_lock`=0=0, `completed_processes`=`completed_processes`+1 WHERE `case_id`=%s'
                    queue_db.execute(query, params=[success_message, case_id])
                    consumer.commit()
            else:
                # Unlock the case.
                logging.debug('Flag false. Unlocking case with failure status 1.')
                query = 'UPDATE `process_queue` SET `status`=%s, `case_lock`=0, `failure_status`=1 WHERE `case_id`=%s'
                queue_db.execute(query, params=[failure_message, case_id])
                consumer.commit()
    except:
        logging.exception('Something went wrong in consumer. Check trace.')

if __name__ == '__main__':
    consume()
