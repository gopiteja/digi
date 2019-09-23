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

def generate_report(data):
    report_type = data['report_type']
    tenant_id = data['tenant_id']
    file_name = data['filename']
    reference_id = data['reference_id']
#    from_date = data['from_date']
#    to_date = data['to_date']

    reports_db_config = {
        'host': 'reports_db',
        'tenant_id': tenant_id
    }
    reports_db = DB('reports', **reports_db_config)

    # Get the report type configuration
    query = 'SELECT * FROM `report_types` WHERE `report_type`=%s'
    report_type_df = reports_db.execute(query, params=[report_type])

    report_type_query = list(report_type_df['query'])[0]
    report_type_db = list(report_type_df['db'])[0]
    report_type_function = list(report_type_df['function'])[0]

    # Get the report data using query or function
    if report_type_query:
        query_db_config = {
            'host': 'queue_db',
            'tenant_id': tenant_id
        }
        query_db = DB(report_type_db, **query_db_config)
        report_df = query_db.execute_(report_type_query)
        logging.debug('DF to export:')
        logging.debug(report_df)
    elif report_type_function:
        logging.warning('Function type does not work.')
        pass

    # Generate the report
    report_df.to_excel(f'./reports/{file_name}.xlsx', index=False)
    logging.info(f'Reported generated')
    
    # Update status of the reference ID
    query = 'UPDATE `reports_queue` SET `status`=%s WHERE `reference_id`=%s'
    reports_db.execute(query, params=['Download', reference_id])

def consume(broker_url='broker:9092'):
    try:
        route = 'generate_report'
        logging.info(f'Listening to topic: {route}')

        consumer = KafkaConsumer(
            bootstrap_servers=broker_url,
            value_deserializer=lambda value: json.loads(value.decode()),
            auto_offset_reset='earliest',
            group_id='generate_report',
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
                    group_id='generate_report',
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
                logging.info(f'Message: {data}')
                reference_id = data.get('reference_id', None)
                tenant_id = data.get('tenant_id', None)

                if reference_id is None:
                    logging.debug('Recieved wrong data. Commiting.')
                    consumer.commit()
                    continue

                try:
                    # Call the function
                    logging.debug(f'Calling function `generate_report`')
                    generate_report(data)
                    consumer.commit()
                except:
                    # Change status to failed
                    logging.exception(f'Something went wrong while generating report. Check trace.')
                    reports_db_config = {
                        'host': 'reports_db',
                        'tenant_id': tenant_id
                    }
                    reports_db = DB('reports', **reports_db_config)
                    query = 'UPDATE `reports_queue` SET `status`=%s WHERE `reference_id`=%s'
                    reports_db.execute(query, params=['Failed', reference_id])
                    consumer.commit()
                    continue
            except:
                logging.exception('Something went wrong.')
                consumer.commit()
    except:
        logging.exception('Something went wrong in consumer. Check trace.')

if __name__ == '__main__':
    consume()
