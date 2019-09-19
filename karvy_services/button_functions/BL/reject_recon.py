import json
import traceback

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


def recon_function(data):
    try:
        logging.debug(data)
    except Exception as e:
        logging.debug(e)
    return 

def consume(broker_url='broker:9092'):
    try:
        route = 'reject_recon'
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
            group_id='reject_recon',
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
                    group_id='reject_recon',
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
            logging.info(f'Message: {data}')

            try:
                functions = data['functions']
            except Exception as e:
                logging.warning(f'Recieved unknown data. [{data}] [{e}]')
                consumer.commit()
                continue
            
            # Getting the correct data for the functions. This data will be passed through
            # rest of the chained functions.
            function_params = {}
            for function in functions:
                if function['route'] == route:
                    function_params = function['parameters']
                    break

            # Call the function
            try:
                logging.debug(f'Calling function `recon_function`')
                recon_function(function_params)
            except:
                # Unlock the case.
                logging.exception(f'Something went wrong while recon_function. Check trace.')
                consumer.commit()
                continue

            consumer.commit()
    except:
        logging.exception('Something went wrong in consumer. Check trace.')

if __name__ == '__main__':
    consume()
