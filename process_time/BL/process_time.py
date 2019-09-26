import argparse
import json
import requests
import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from kafka import KafkaConsumer, TopicPartition

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

from db_utils import DB
from ace_logger import Logging
from producer import produce

# Database configuration
db_config = {
    'host': os.environ['HOST_IP'],
    'user': os.environ['LOCAL_DB_USER'],
    'password': os.environ['LOCAL_DB_PASSWORD'],
    'port': os.environ['LOCAL_DB_PORT'],
}

logging = Logging().getLogger('ace')

@zipkin_span(service_name='process_time_consumer', span_name='process_time')
def process_time(data, tenant_id=None):
    logging.info(f'Data recieved: {data}')

    case_id = data['case_id']

    db_config['tenant_id'] = tenant_id
    
    audit_db = DB('stats', **db_config)
    query = f"SELECT * from audit where table_name = 'process_queue' and reference_value = '{case_id}' and changed_data LIKE '%%state%%'" 
    case_id_changed = list(audit_db.execute(query).changed_data)
    case_id_time = list(audit_db.execute(query).updated_date)

    time_taken_between_queues = {}
    prev_time = 0
    for index, value in enumerate(case_id_changed):
        if index == 0:
            queue = json.loads(value)["queue"]
            time_taken_between_queues[queue] = (case_id_time[index+1] - case_id_time[index]).total_seconds()
        else:
            if queue != json.loads(value)["queue"]:
                queue = json.loads(value)["queue"]
                try:
                    time_taken_between_queues[queue] = (case_id_time[index+1] - prev_time).total_seconds()
                except:
                    time_taken_between_queues[queue] = "Last queue"
                    break
            
        prev_time = case_id_time[index+1]
        
    for key, val in time_taken_between_queues.items():
        query = f"SELECT * from queue_time where state = '{key}' and date = CURDATE()" 
        state_details = audit_db.execute(query).to_dict(orient='records')[0]

        if state_details:
            no_files = state_details['no_of_files'] + 1
            try:
                aht = (state_details['aht_in_sec'] + val) / no_files
            except:
                break
            
            update_query = f"update queue_time set no_of_files = {no_files}, aht_in_sec = {aht} where state = '{key}'"
            audit_db.execute(update_query)
        else:
            try:
                aht = int(val)
            except:
                aht = 0
            insert_query = f"INSERT INTO `queue_time`(`date`, `no_of_files`, `state`, `aht_in_sec`) VALUES (CURDATE(),1,'{key}',{aht})"
            audit_db.execute(insert_query)
    return "Updated Successfully"

def consume(broker_url='broker:9092'):
    try:
        route = 'process_time'

        logging.debug(f'Listening to topic `{route}`...')
        consumer = KafkaConsumer(
            bootstrap_servers=broker_url,
            value_deserializer=lambda value: json.loads(value.decode()),
            auto_offset_reset='earliest',
            group_id=route,
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
            while parts is None:
                consumer = KafkaConsumer(
                    bootstrap_servers=broker_url,
                    value_deserializer=lambda value: json.loads(value.decode()),
                    auto_offset_reset='earliest',
                    group_id=route,
                    api_version=(0,10,1),
                    enable_auto_commit=False,
                    session_timeout_ms=800001,
                    request_timeout_ms=800002
                )
                parts = consumer.partitions_for_topic(route)
                logging.warning("No partition. In while loop. Make it stop")

        partitions = [TopicPartition(route, p) for p in parts]
        consumer.assign(partitions)

        for message in consumer:
            data = message.value
            try:
                case_id = data['case_id']
                functions = data['functions']
                tenant_id = data['tenant_id']
            except Exception as e:
                logging.warning(f'Recieved unknown data. [{data}] [{e}]')
                tenant_id = ''
                consumer.commit()
                continue
            with zipkin_span(service_name='process_time_consumer', span_name='consume', 
                    transport_handler=http_transport, port=5007, sample_rate=0.5,) as  zipkin_context:
                zipkin_context.update_binary_annotations({'Tenant':tenant_id})

                db_config['tenant_id'] = tenant_id

                kafka_db = DB('kafka', **db_config)
                queue_db = DB('queues', **db_config)

                message_flow = kafka_db.get_all('grouped_message_flow')
                
                query = 'SELECT * FROM `button_functions` WHERE `route`=%s'
                function_info = queue_db.execute(query, params=[route])
                in_progress_message = list(function_info['in_progress_message'])[0]
                failure_message = list(function_info['failure_message'])[0]
                success_message = list(function_info['success_message'])[0]
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

                # Call the function
                try:
                    result = process_time(function_params, tenant_id)
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
