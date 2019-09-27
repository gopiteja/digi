import json
import os
import traceback

from datetime import datetime, timedelta
from kafka import KafkaConsumer, TopicPartition
from random import randint
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

def add_file_to_db(data):
    logging.info('Adding file to database.')
    logging.info(f'Data recieved: {data}')

    unique_id = data.get('case_id', None)
    file_name = data.get('file_name', None)
    file_path = data.get('file_path', None)
    tenant_id = data.get('tenant_id', None)

    # Check if we recieved the right data
    check_list = [unique_id, file_name, file_path]
    assert (None not in check_list), '`case_id`, `file_name`, `file_path` cant be None.'

    queue_db = DB('queues', tenant_id=tenant_id, **db_config)
    stats_db = DB('stats', tenant_id=tenant_id, **db_config)

    process_queue_df = queue_db.get_all('process_queue')
    case_id_process = process_queue_df.loc[process_queue_df['file_name'] == file_path.name]
    if case_id_process.empty:
        insert_query = ('INSERT INTO `process_queue` (`file_name`, `case_id`, `file_path`, `source_of_invoice`) '
            'VALUES (%s, %s, %s, %s)')
        params = [file_path.name, unique_id, str(file_path.parent.absolute()), str(file_path.parent).split('/')[-1]]
        queue_db.execute(insert_query, params=params)
        logging.debug(f' - {file_path.name} inserted successfully into the database')
    else:
        logging.debug("File already exists in the database")

    audit_data = {
            "type": "insert",
            "last_modified_by": "add_file",
            "table_name": "process_queue",
            "reference_column": "case_id",
            "reference_value": unique_id,
            "changed_data": json.dumps({"stats_stage": 'Document ingested'})
        }
    stats_db.insert_dict(audit_data, 'audit')

def consume(broker_url='broker:9092'):
    try:
        route = 'add_file'
        logging.info(f'Listening to topic: {route}')

        consumer = KafkaConsumer(
            bootstrap_servers=broker_url,
            value_deserializer=lambda value: json.loads(value.decode()),
            auto_offset_reset='earliest',
            group_id='add_file',
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
                    group_id='add_file',
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

            if not data:
                logging.debug('Recieved no data. Commiting.')
                consumer.commit()
                continue
            
            try:
                logging.info(f'Message: {data}')

                try:
                    # Call the function
                    logging.debug(f'Calling function `add_file_to_db`')
                    add_file_to_db(data)
                    
                    tenant_id = data.get('tenant_id', None)
                    kafka_db = DB('kafka', tenant_id=tenant_id, **db_config)
                        
                    query = 'SELECT * FROM `message_flow` WHERE `listen_to_topic`=%s'
                    message_flow = kafka_db.execute(query, params=['add_file'])

                    if message_flow.empty:
                        logging.error('`add_file` is not configured in message flow table.')
                    else:
                        topic = list(message_flow.send_to_topic)[0]

                        if topic is not None:
                            logging.info(f'Producing to topic {topic}')
                            produce(topic, data)
                        else:
                            logging.info(f'There is no topic to send to for `add_file`. [{topic}]')
                except:
                    logging.exception(f'Something went wrong while adding file to database. Check trace.')
                    consumer.commit()
            except:
                logging.exception('Something went wrong.')
                consumer.commit()
    except:
        logging.exception('Something went wrong in consumer. Check trace.')

if __name__ == '__main__':
    consume()
