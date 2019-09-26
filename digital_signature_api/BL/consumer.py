import json
import os
import requests

from kafka import KafkaConsumer, TopicPartition
from py_zipkin.zipkin import zipkin_span,ZipkinAttrs, create_http_headers_for_new_span

from db_utils import DB
from digital_signature import is_pdf_signed
from producer import produce
from ace_logger import Logging

logging = Logging()

db_config = {
    'host': os.environ['HOST_IP'],
    'user': os.environ['LOCAL_DB_USER'],
    'password': os.environ['LOCAL_DB_PASSWORD'],
    'port': os.environ['LOCAL_DB_PORT']
}

def http_transport(encoded_span):
    body = encoded_span
    requests.post(
        'http://servicebridge:5002/zipkin',
        data=body,
        headers={'Content-Type': 'application/x-thrift'},)

def consume(broker_url='broker:9092'):
    try:
        topic = 'digital_signature'

        logging.info(f'Listening to topic `{topic}`...')
        consumer = KafkaConsumer(
            bootstrap_servers=broker_url,
            value_deserializer=lambda value: json.loads(value.decode()),
            auto_offset_reset='earliest',
            group_id='digital_signature',
            api_version=(0,10,1),
            enable_auto_commit=False,
            session_timeout_ms=800001,
            request_timeout_ms=800002
        )

        logging.debug('Consumer object created.')

        parts = consumer.partitions_for_topic(topic)
        if parts is None:
            logging.error('No partitions')
            logging.debug('Creating Topic', topic)
            produce(topic, {})
            while parts is None:
                print(f'Listening to topic `{topic}`...')
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
                parts = consumer.partitions_for_topic(topic)
                logging.error("No partition. In while loop. Make it stop")

        partitions = [TopicPartition(topic, p) for p in parts]
        consumer.assign(partitions)

        for message in consumer:
            data = message.value
            
            if not isinstance(data, dict):
                logging.warning(f'Received data is not a dictionary. [{data}]')
                consumer.commit()
                continue

            if not data:
                logging.info(f'Got empty data. {data}')
                consumer.commit()
                continue
                
            case_id = data.get('case_id', None)
            tenant_id = data.get('tenant_id', None)
            zipkin_headers = data['zipkin_headers']
            
            if case_id is None:
                logging.debug(f'Recieved unknown data. [{data}]')
                consumer.commit()

            kafka_db = DB('kafka', tenant_id=tenant_id, **db_config)
            extraction_db = DB('extraction', tenant_id=tenant_id, **db_config)

            query = 'SELECT * FROM `message_flow` WHERE `listen_to_topic`=%s'
            message_flow = kafka_db.execute(query, params=[topic])
            send_to_topic = list(message_flow.send_to_topic)[0]

            with zipkin_span(service_name='digital_signature', span_name='consumer', 
                    zipkin_attrs=ZipkinAttrs(trace_id=zipkin_headers['X-B3-TraceId'],
                    span_id=zipkin_headers['X-B3-SpanId'],
                    parent_span_id=zipkin_headers['X-B3-ParentSpanId'],
                    flags=zipkin_headers['X-B3-Flags'],
                    is_sampled=zipkin_headers['X-B3-Sampled'],),
                    transport_handler=http_transport,
                    # port=5014,
                    sample_rate=0.5,):

                file_name = data.get('file_name', None)
                response_data = is_pdf_signed(case_id, file_name)
                if response_data['flag'] == True:
                    produce(send_to_topic, data)
                    logging.info('Message commited!')
                else:
                    logging.warning('Message not consumed. Some error must have occured. Will try again!')
                consumer.commit()
    except:
        logging.exception('Something went wrong in consumer. Check trace.')

if __name__ == '__main__':
    consume()
