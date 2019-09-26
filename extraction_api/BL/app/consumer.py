import json
import requests
import os
import sys
import traceback

from kafka import KafkaConsumer, TopicPartition

from extraction_api import value_extract

from py_zipkin.zipkin import zipkin_span, ZipkinAttrs, create_http_headers_for_new_span

try:
    from app.ace_logger import Logging
    from app.db_utils import DB
    from app.producer import produce
except:
    from ace_logger import Logging
    from db_utils import DB
    from producer import produce

logging = Logging()


def http_transport(encoded_span):
    body = encoded_span
    requests.post(
        'http://servicebridge:5002/zipkin',
        data=body,
        headers={'Content-Type': 'application/x-thrift'}, )


@zipkin_span(service_name='extraction_api', span_name='value_extract')
def value_extract_with_zipkin(data):
    response_data = value_extract(data)

    return response_data


def consume(broker_url='broker:9092'):
    try:
        overwrite = False

        topic = 'extract'

        logging.info(f'Listening to topic `{topic}`...')
        consumer = KafkaConsumer(
            bootstrap_servers=broker_url,
            value_deserializer=lambda value: json.loads(value.decode()),
            auto_offset_reset='earliest',
            group_id='extraction',
            api_version=(0, 10, 1),
            enable_auto_commit=False,
            session_timeout_ms=800001,
            request_timeout_ms=800002
        )
        logging.debug('Consumer object created.')

        parts = consumer.partitions_for_topic(topic)
        if parts is None:
            logging.warning(f'No partitions for topic `{topic}`')
            logging.debug(f'Creating Topic: {topic}')
            produce(topic, {})
            print(f'Listening to topic `{topic}`...')
            while parts is None:
                consumer = KafkaConsumer(
                    bootstrap_servers=broker_url,
                    value_deserializer=lambda value: json.loads(value.decode()),
                    auto_offset_reset='earliest',
                    group_id='sap_portal',
                    api_version=(0, 10, 1),
                    enable_auto_commit=False,
                    session_timeout_ms=800001,
                    request_timeout_ms=800002
                )
                parts = consumer.partitions_for_topic(topic)
                logging.warning("No partition. In while loop. Make it stop")

        partitions = [TopicPartition(topic, p) for p in parts]
        consumer.assign(partitions)

        for message in consumer:
            data = message.value

            try:
                tenant_id = data['tenant_id']
            except Exception as e:
                logging.warning(f'Received unknown data. [{data}] [{e}]')
                consumer.commit()
                continue

            db_config = {
                'host': os.environ['HOST_IP'],
                'port': '3306',
                'user': 'root',
                'password': os.environ['LOCAL_DB_PASSWORD'],
                'tenant_id': tenant_id
            }
            extraction_db = DB('queues', **db_config)
            kafka_db = DB('kafka', **db_config)

            logging.info(f'Recieved message: {data}')

            if 'zipkin_headers' in data:
                zipkin_headers = data['zipkin_headers']
                zikpkin_atrr = ZipkinAttrs(trace_id=zipkin_headers['X-B3-TraceId'],
                                           span_id=zipkin_headers['X-B3-SpanId'],
                                           parent_span_id=zipkin_headers['X-B3-ParentSpanId'],
                                           flags=zipkin_headers['X-B3-Flags'],
                                           is_sampled=zipkin_headers['X-B3-Sampled'], )
            else:
                logging.error("no zipkin_headers")
                zipkin_headers = ''
                zikpkin_atrr = ''

            logging.debug(f'Zipkin headers: {zipkin_headers}')
            with zipkin_span(
                    service_name='extraction_api',
                    span_name='consumer',
                    zipkin_attrs=ZipkinAttrs(trace_id=zipkin_headers['X-B3-TraceId'],
                                             span_id=zipkin_headers['X-B3-SpanId'],
                                             parent_span_id=zipkin_headers['X-B3-ParentSpanId'],
                                             flags=zipkin_headers['X-B3-Flags'],
                                             is_sampled=zipkin_headers['X-B3-Sampled'], ),
                    transport_handler=http_transport,
                    port=5010,
                    sample_rate=0.5, ):
                try:
                    message_flow = kafka_db.get_all('message_flow')
                    listen_to_topic_df = message_flow.loc[message_flow['listen_to_topic'] == topic]
                    send_to_topic = list(listen_to_topic_df.send_to_topic)[0]

                    data = message.value
                    case_id = data['case_id']
                    ocr_df = extraction_db.get_all('ocr')
                    case_id_ocr = ocr_df.loc[ocr_df['case_id'] == case_id]
                    if case_id_ocr.empty or overwrite:
                        logging.debug(f'Extraction message:{data}')
                        response_data = value_extract(data)
                        if response_data['flag']:
                            data = response_data['send_data'] if 'send_data' in response_data else {}
                            logging.info('Message commited!')
                            produce(send_to_topic, data)
                        else:
                            logging.info('Message not consumed. Some error must have occured. Will try again!')
                    else:
                        logging.info('Consuming old message.')
                except Exception as e:
                    logging.exception('Error. Moving to next message')
                consumer.commit()
    except:
        logging.exception('Something went wrong in consumer. Check trace.')


if __name__ == '__main__':
    consume()
