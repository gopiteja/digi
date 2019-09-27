import json
import os
import requests

from kafka import KafkaConsumer, TopicPartition

from db_utils import DB
from table_api import predict_with_template
from producer import produce
from py_zipkin.zipkin import zipkin_span, ZipkinAttrs, create_http_headers_for_new_span

try:
    from app.ace_logger import Logging
except:
    from ace_logger import Logging

logging = Logging()


def http_transport(encoded_span):
    # The collector expects a thrift-encoded list of spans. Instead of
    # decoding and re-encoding the already thrift-encoded message, we can just
    # add header bytes that specify that what follows is a list of length 1.
    body = encoded_span
    requests.post(
        'http://servicebridge:5002/zipkin',
        data=body,
        headers={'Content-Type': 'application/x-thrift'},
    )


def consume(broker_url='broker:9092'):
    try:
        topic = 'table_extract'

        logging.info(f'Listening to topic `{topic}`...')
        consumer = KafkaConsumer(
            bootstrap_servers=broker_url,
            value_deserializer=lambda value: json.loads(value.decode()),
            auto_offset_reset='earliest',
            group_id='table_api',
            api_version=(0, 10, 1),
            enable_auto_commit=False,
            session_timeout_ms=800001,
            request_timeout_ms=800002
        )
        logging.info('Consumer object created.')

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
                'port': os.environ['LOCAL_DB_PORT'],
                'user': os.environ['LOCAL_DB_USER'],
                'password': os.environ['LOCAL_DB_PASSWORD'],
                'tenant_id': tenant_id
            }

            kafka_db = DB('kafka', **db_config)

            case_id = data['case_id']
            if 'zipkin_headers' in data:
                zipkin_headers = data['zipkin_headers']
            else:
                zipkin_headers = ''
            with zipkin_span(service_name='table_api', span_name='consumer',
                             zipkin_attrs=ZipkinAttrs(trace_id=zipkin_headers['X-B3-TraceId'],
                                                      span_id=zipkin_headers['X-B3-SpanId'],
                                                      parent_span_id=zipkin_headers['X-B3-ParentSpanId'],
                                                      flags=zipkin_headers['X-B3-Flags'],
                                                      is_sampled=zipkin_headers['X-B3-Sampled'], ),
                             transport_handler=http_transport,
                             # port=5014,
                             sample_rate=100, ):
                try:
                    message_flow = kafka_db.get_all('message_flow')
                    listen_to_topic_df = message_flow.loc[message_flow['listen_to_topic'] == topic]
                    send_to_topic = list(listen_to_topic_df.send_to_topic)[0]

                    response_data = predict_with_template(**data)
                    if response_data['flag']:
                        send_data = {
                            'case_id': case_id,
                            'send_to_topic': 'sap',
                        }
                        logging.debug('Message committed!')
                        produce(send_to_topic, send_data)
                    else:
                        logging.debug('Message not consumed. Some error must have occurred. Will try again!')
                except:
                    logging.exception("Error. Moving to next message")
                consumer.commit()
    except Exception as e:
        logging.exception('Error in table consumer')


if __name__ == '__main__':
    consume()
