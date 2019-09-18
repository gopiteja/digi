import argparse
import json
import requests
import traceback

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

logging = Logging()

# @zipkin_span(service_name='process_time_consumer', span_name='process_time')
def process_time(case_id, tenant_id=None):
    logging.debug('Calculating queue time.')
    try:
        logging.info(f'Data recieved: {case_id}')    
        db_config = {
            'host': 'queue_db',
            'port': 3306,
            'user': 'root',
            'password': '',
            'tenant_id': tenant_id
        }
        
        audit_db = DB('stats', **db_config)
        query = f"SELECT * from audit where table_name = 'process_queue' and reference_value = '{case_id}' and changed_data LIKE '%%stats_stage%%'" 
        case_id_changed = list(audit_db.execute(query).changed_data)
        case_id_time = list(audit_db.execute(query).updated_date)

        del_index = []
        for i,j in enumerate(case_id_changed):
            if i == 0:
                prev_queue = json.loads(j)["stats_stage"]
                continue
            if json.loads(j)["stats_stage"] == prev_queue:
                del_index.append(i)
                prev_queue = json.loads(j)["stats_stage"]

        case_id_changed = [i for j, i in enumerate(case_id_changed) if j not in del_index]
        case_id_time = [i for j, i in enumerate(case_id_time) if j not in del_index]

        time_taken_between_queues = {}
        prev_time = 0
        for index, value in enumerate(case_id_changed):
            logging.debug('Case ID found')
            if index == 0:
                queue = json.loads(value)["stats_stage"]
                time_taken_between_queues[queue] = (case_id_time[index+1] - case_id_time[index]).total_seconds()
            else:
                if queue != json.loads(value)["stats_stage"]:
                    queue = json.loads(value)["stats_stage"]
                    try:
                        time_taken_between_queues[queue] = (case_id_time[index+1] - prev_time).total_seconds()
                    except:
                        time_taken_between_queues[queue] = "Last queue"
                        break
                
            prev_time = case_id_time[index+1]
            
        for key, val in time_taken_between_queues.items():
            logging.debug('Updating queue time in db')
            query = f"SELECT * from queue_time where state = '{key}' and date = CURDATE()" 
            state_details = None
            try:
                state_details = audit_db.execute(query).to_dict(orient='records')[0]
            except:
                pass

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
        return {'flag': True, 'message': "Updated successfully"}
    except Exception as e:
        logging.exception(f'Error: {e}')
        return {'flag': False, 'message': "Updated failed"}

def consume(broker_url='broker:9092'):
    try:
        route = 'process_time'

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
            group_id=route,
            api_version=(0,10,1),
            enable_auto_commit=False,
            session_timeout_ms=800001,
            request_timeout_ms=800002
        )
        logging.debug(f'Consumer object created for {route}')

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

        query = 'SELECT * FROM `button_functions` WHERE `route`=%s'
        function_info = queue_db.execute(query, params=[route])
        in_progress_message = list(function_info['in_progress_message'])[0]
        failure_message = list(function_info['failure_message'])[0]
        success_message = list(function_info['success_message'])[0]

        for message in consumer:
            logging.debug('Consumer is listening.')
            data = message.value
            try:
                case_id = data['case_id']
                tenant_id = data['tenant_id']
            except Exception as e:
                logging.warning(f'Recieved unknown data. [{data}] [{e}]')
                tenant_id = ''
                consumer.commit()
                continue
            # with zipkin_span(service_name='process_time_consumer', span_name='consume', 
            #         transport_handler=http_transport, port=5007, sample_rate=0.5,) as  zipkin_context:
            #     zipkin_context.update_binary_annotations({'Tenant':tenant_id})

            # Get which button (group in kafka table) this function was called from
            try:
                group = 'Complete'
            except:
                traceback.print_exc()
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

            # Call the function
            try:
                result = process_time(case_id, tenant_id)
                consumer.commit()
            except:
                traceback.print_exc()
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
