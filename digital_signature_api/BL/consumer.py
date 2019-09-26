import json

from kafka import KafkaConsumer, TopicPartition

from db_utils import DB
from digital_signature import is_pdf_signed
from producer import produce

try:
    from app.ace_logger import Logging
except:
    from ace_logger import Logging

from py_zipkin.zipkin import zipkin_span,ZipkinAttrs, create_http_headers_for_new_span

logging = Logging().getLogger('ace')

def http_transport(encoded_span):
    body = encoded_span
    requests.post(
        'http://servicebridge:5002/zipkin',
        data=body,
        headers={'Content-Type': 'application/x-thrift'},)

def consume(broker_url='broker:9092'):
    try:
        common_db_config = {
            'host': 'common_db',
            'port': '3306',
            'user': 'root',
            'password': 'root'
        }
        kafka_db = DB('kafka', **common_db_config)
        # kafka_db = DB('kafka')

        extraction_db_config = {
            'host': 'extraction_db',
            'port': '3306',
            'user': 'root',
            'password': 'root'
        }
        extraction_db = DB('extraction', **extraction_db_config)

        overwrite = True

        message_flow = kafka_db.get_all('message_flow')
        listen_to_topic_df = message_flow.loc[message_flow['listen_to_topic'] == 'digital_signature']
        topic = list(listen_to_topic_df.listen_to_topic)[0]
        send_to_topic = list(listen_to_topic_df.send_to_topic)[0]

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

            if not data:
                logging.info(f'Got empty data. {data}')
                consumer.commit()
                continue

            tenant_id = data['tenant_id']
            zipkin_headers = data['zipkin_headers']
            case_id = data.pop('case_id', None)
            with zipkin_span(service_name='digital_signature', span_name='consumer', 
                zipkin_attrs=ZipkinAttrs(trace_id=zipkin_headers['X-B3-TraceId'],
                span_id=zipkin_headers['X-B3-SpanId'],
                parent_span_id=zipkin_headers['X-B3-ParentSpanId'],
                flags=zipkin_headers['X-B3-Flags'],
                is_sampled=zipkin_headers['X-B3-Sampled'],),
                transport_handler=http_transport,
                # port=5014,
                sample_rate=0.5,):

                if case_id is None:
                    logging.debug(f'Recieved unknown data. [{data}]')
                    consumer.commit()

                validation_df = extraction_db.get_all('validation')
                case_id_validation = validation_df.loc[validation_df['case_id'] == case_id]
                if case_id_validation.empty or overwrite:
                    file_name = data.pop('file_name', None)
                    response_data = is_pdf_signed(case_id, file_name)
                    if response_data['flag'] == True:
                        produce(send_to_topic, data)
                        logging.info('Message commited!')
                    else:
                        logging.warning('Message not consumed. Some error must have occured. Will try again!')
                else:
                    logging.debug("Consuming old message.")
                consumer.commit()
    except:
        logging.exception('Something went wrong in consumer. Check trace.')

if __name__ == '__main__':
    consume()
