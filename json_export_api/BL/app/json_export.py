import argparse
import json

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

try:
    from app.ace_logger import Logging
    from app.db_utils import DB
    from app.json_exporter import JSONExport
    from app.producer import produce
except:
    from ace_logger import Logging
    from db_utils import DB
    from json_exporter import JSONExport
    from producer import produce

logging = Logging()

@zipkin_span(service_name='excel_export_api', span_name='export_json')
def export_json(content):
    logging.info('Exporting to JSON.')
    logging.debug(f'Data recieved: {content}')

    case_id = content.pop('case_id', None)

    # Sanity checks
    if case_id is not None and not case_id.strip():
        message = f'Case ID cant be empty string.'
        logging.error(message)
        return {'flag': False, 'message': message}

    # * STEP 0 - Get metadata
    # Database configuration
    queue_db_config = {
        'host': 'queue_db',
        'user': 'root',
        'password': 'root',
        'port': '3306'
    }
    queue_db = DB('queues', **queue_db_config)
    # queue_db = DB('queues_')  # Development purpose

    case_data = queue_db.get_all('process_queue', {'case_id': case_id})
    # latest_case_file = queue_db.get_latest(case_files, 'case_id', 'created_date')

    if case_data.empty:
        message = f'Case ID `{case_id}` not in process queue.'
        logging.error(message)
        return {'flag': False, 'message': message}

    # * STEP 1 - Get data to export
    # Database configuration
    extraction_db_config = {
        'host': 'extraction_db',
        'user': 'root',
        'password': 'root',
        'port': '3306'
    }
    extraction_db = DB('extraction', **extraction_db_config)
    # extraction_db = DB('extraction')  # Development purpose

    if case_id is not None:
        data = extraction_db.get_all('combined', condition={'case_id': case_id})
    else:
        data = extraction_db.get_all('combined')

    if data.empty:
        message = 'No data or case ID not in combined table. Merge table before exporting.'
        logging.error(message)
        return {'flag': False, 'message': message}

    # * STEP 2 - Getting export configuration
    # Database configuration
    json_export_db_config = {
        'host': 'json_export_db',
        'user': 'root',
        'password': 'root',
        'port': '3306'
    }
    json_export_db = DB('json_export', **json_export_db_config)
    # json_export_db = DB('json_export')  # Development purpose

    # Get active configuration
    all_configs = json_export_db.get_all('configuration')
    all_active_configs = all_configs.loc[all_configs['active'] == 1]

    if all_configs.empty:
        message = 'There are no configuration made. Please create a configuration first.'
        logging.error(message)
        return {'flag': False, 'message': message}

    if len(all_active_configs) > 1:
        logging.warning('Multiple active configurations found. Using the first one.')
    elif all_active_configs.empty:
        message = 'There are no active configuration. Activate a configuration to export in excel.'
        logging.warning(message)
        return {'flag': False, 'message': message}

    active_config = all_active_configs.to_dict('records')[0]
    logging.info(f'Configuration: {active_config}')

    # * STEP 3 - Get all the configuration parameters in the right format
    try:
        field_mapping = json.loads(active_config['field_mapping'])
    except:
        field_mapping = {}

    json_export_config = {
        'export_type': active_config['export_option'],
        'excluded_fields': active_config['excluded_fields'].split(','),
        'field_mapping': field_mapping
    }

    json_export = JSONExport(**json_export_config)

    return json_export.export(case_data, data)

def consume(broker_url='broker:9092'):
    try:
        route = 'generate_json'

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
            group_id='generate_json',
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
            try:
                case_id = data['case_id']
                functions = data['functions']
                tenant_id = data['tenant_id']
            except Exception as e:
                logging.warning(f'Recieved unknown data. [{data}] [{e}]')
                tenant_id = ''
                consumer.commit()
                continue
            with zipkin_span(service_name='json_export', span_name='consume', 
                    transport_handler=http_transport, port=5007, sample_rate=0.5,) as  zipkin_context:
                zipkin_context.update_binary_annotations({'Tenant':tenant_id})

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
                    result = export_json(function_params)
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
