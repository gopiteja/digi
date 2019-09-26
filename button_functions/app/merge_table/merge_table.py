import ast
import json
import os
import traceback
import pandas as pd

from datetime import datetime, timedelta
from kafka import KafkaConsumer, TopicPartition
from random import randint
from requests import post
from time import sleep

from db_utils import DB
from producer import produce
from ace_logger import Logging

logging = Logging()

db_config = {
    'host': os.environ['HOST_IP'],
    'user': os.environ['LOCAL_DB_USER'],
    'password': os.environ['LOCAL_DB_PASSWORD'],
    'port': os.environ['LOCAL_DB_PORT']
}

def table_as_kv(extracted_data_maintable):
    extracted_data_maintable_kv = {}

    table_head = extracted_data_maintable[0]
    # print(table_head)
    nested = False
    if table_head[0][1] == 2:
        nested = True

    table_rows = extracted_data_maintable[1:]
    nested_col = []
    if nested:
        table_rows = extracted_data_maintable[2:]
        nested_col = extracted_data_maintable[1]
    header_names = []

    head_map = {}

    for ind, head in enumerate(table_head):
        head[0] = head[0].replace('<b>', '')
        head[0] = head[0].replace('</b>', '')
        if nested:
            if head[1] == 1:
                col_span = head[2]
                head_nest = nested_col[:col_span]
                temp = []
                for i in range(len(head_nest)):
                    # print(head[0]+'.'+head_nest[i][0])
                    temp.append(head[0]+'.'+head_nest[i][0].strip())
                    header_names.append(head[0]+'.'+head_nest[i][0].strip())
                if temp:
                    head_map[ind] = temp
                nested_col = nested_col[col_span:]
            else:
                header_names.append(head[0])
                head_map[ind] = head[0]
        else:
            header_names.append(head[0])
            head_map[ind] = head[0]
    # print('header_names',header_names)
    # print(len(header_names))
    for row in table_rows:
        for i in range(len(row)):
            if header_names[i] not in extracted_data_maintable_kv:
                extracted_data_maintable_kv[header_names[i]] = [row[i][0]]
            else:
                extracted_data_maintable_kv[header_names[i]].append(row[i][0])
    return extracted_data_maintable_kv

def merge_table(data, tenant_id):
    case_id = data['case_id']

    logging.debug(f"Merging table for case_id:{case_id}")

    tables = ['json_reader', 'sap', 'ocr', 'business_rule']

    db = DB('extraction', tenant_id=tenant_id, **db_config)

    combined_table_data = {}
    for table in tables:
        db_table_data = db.get_all(table)
        try:
            case_file = db_table_data.loc[db_table_data['case_id'] == case_id]
            latest_case_file = db.get_latest(
                case_file, 'case_id', 'created_date')
        except:
            case_file = db_table_data.loc[db_table_data['Portal Reference Number'] == case_id]
            latest_case_file = db.get_latest(
                case_file, 'Portal Reference Number', 'created_date')

        if case_file.empty:
            logging.debug(
                f'Case ID `{case_id}` does not exist in table `{table}`. Skipping.')
            continue

        combined_table_data = {
            **combined_table_data,
            **latest_case_file.to_dict(orient='records')[0]
        }

    combined_table_data.pop('created_date')
    table_string = combined_table_data.pop('Table', None)

    if table_string is None:
        logging.debug('No table.')
        table_list = []
    else:
        table_list = ast.literal_eval(table_string)

    try:
        table_kv = table_as_kv(table_list[0][0][0])
    except:
        table_kv = {}

    valid_table_headers = ['Product Description',
                           'Quantity', 'Rate', 'Gross Amount', 'HSN/SAC']

    list_final_data = []
    if table_kv:
        for table_header, value in table_kv.items():
            for index, row_value in enumerate(value):
                if table_header.replace('Table.', '') in valid_table_headers:
                    combined_table_data[table_header.replace(
                        'Table.', '')] = row_value
                    if len(list_final_data) <= index:
                        list_final_data.append(combined_table_data.copy())
                    else:
                        list_final_data[index][table_header.replace(
                            'Table.', '')] = row_value
    else:
        list_final_data.append(combined_table_data)

    if len(list_final_data) == 0:
        list_final_data.append(combined_table_data)

    for row in list_final_data:
        for key, value in row.items():
            if key in ['IGST amount', 'Invoice Base Amount', 'Rate', 'Invoice Total', 'SGST/CGST Amount', 'Gross Amount']:
                try:
                    row[key] = float(''.join(re.findall(r'[0-9\.]', value)))
                except:
                    pass
            if key in ['HSN/SAC', 'Quantity']:
                try:
                    row[key] = int(''.join(re.findall(r'[0-9]', value)))
                except:
                    pass

    final_df = pd.DataFrame(list_final_data)

    # print(final_df.to_dict(orient='records'))
    try:
        final_df.to_sql('combined', con=db.engine,
                        if_exists='append', index=False, index_label='id')
        return {'flag': True, 'data': list_final_data}
    except:
        traceback.print_exc()
        return {'flag': False, 'message': 'Error combining table.'}


def consume(broker_url='broker:9092'):
    try:
        route = 'merge_table'

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

        logging.debug(f'Listening to topic `{route}`...')
        consumer = KafkaConsumer(
            bootstrap_servers=broker_url,
            value_deserializer=lambda value: json.loads(value.decode()),
            auto_offset_reset='earliest',
            group_id='merge_table',
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
            print(f'Listening to topic `{route}`...')
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
            tenant_id = data.get('tenant_id', None)
            try:
                case_id = data['case_id']
                functions = data['functions']
            except Exception as e:
                logging.exception(f'Recieved unknown data. [{data}] [{e}]')
                consumer.commit()
                continue

            # Get which button (group in kafka table) this function was called from
            try:
                group = data['group']
            except:
                consumer.commit()
                continue

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

            # Call save changes function
            try:
                result = merge_table(function_params, tenant_id)
            except:
                # Unlock the case.
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
                        produce(next_topic, data)

                    # Update the progress count by 1
                    query = 'UPDATE `process_queue` SET `status`=%s, `completed_processes`=`completed_processes`+1 WHERE `case_id`=%s'
                    queue_db.execute(query, params=[success_message, case_id])
                    consumer.commit()
                else:
                    # It is the last message. So update file status to completed.
                    query = 'UPDATE `process_queue` SET `status`=%s, `case_lock`=0, `completed_processes`=`completed_processes`+1 WHERE `case_id`=%s'
                    queue_db.execute(query, params=[success_message, case_id])
                    consumer.commit()
            else:
                # Unlock the case.
                query = 'UPDATE `process_queue` SET `status`=%s, `case_lock`=0, `failure_status`=1 WHERE `case_id`=%s'
                queue_db.execute(query, params=[failure_message, case_id])
                consumer.commit()
    except:
        logging.exception('Something went wrong in consumer. Check trace.')


if __name__ == '__main__':
    consume()
