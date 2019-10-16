import json
import requests
import os

from kafka import KafkaConsumer, TopicPartition

from db_utils import DB
from abbyy_ocr import abbyy_ocr
from producer import produce

from ace_logger import Logging

from py_zipkin.zipkin import zipkin_span, ZipkinAttrs, create_http_headers_for_new_span

logging = Logging()


def http_transport(encoded_span):
    # The collector expects a thrift-encoded list of spans. Instead of
    # decoding and re-encoding the already thrift-encoded message, we can just
    # add header bytes that specify that what follows is a list of length 1.
    body = encoded_span
    requests.post(
        'http://servicebridge:80/zipkin',
        data=body,
        headers={'Content-Type': 'application/x-thrift'},
    )

def create_consumer(route, broker_url='broker:9092'):
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

    return consumer

def consume(broker_url='broker:9092'):
    try:
        overwrite = False
        topic = 'abbyy_ocr'

        logging.info(f'Listening to topic `{topic}`...')
        consumer = create_consumer(topic)
        logging.debug('Consumer object created.')

        parts = consumer.partitions_for_topic(topic)
        if parts is None:
            logging.warning(f'No partitions for topic `{topic}`')
            logging.debug(f'Creating Topic: {topic}')
            produce(topic, {})
            logging.debug(f'Listening to topic `{topic}`...')
            while parts is None:
                consumer = create_consumer(topic)
                parts = consumer.partitions_for_topic(topic)
                logging.warning("No partition. In while loop. Make it stop")

        partitions = [TopicPartition(topic, p) for p in parts]
        consumer.assign(partitions)

        for message in consumer:
            data = message.value
            try:
                tenant_id = data['tenant_id']
                workflow = data['workflow']
            except Exception as e:
                logging.warning(f'Recieved unknown data. [{data}] [{e}]')
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
            queue_db = DB('queues', **db_config)


            query = 'SELECT * FROM `message_flow` WHERE `listen_to_topic`=%s AND `workflow`=%s'
            message_flow = kafka_db.execute(query, params=[topic, workflow])    
            consumer.commit()
            zipkin_headers = None
            # If folder monitor sends multiple messages, think about this
            if 'zipkin_headers' in data:
                zipkin_headers = data['zipkin_headers']
            if not zipkin_headers:
                logging.warning(f'Critical error: Zipkin headers not found')
            try:
                with zipkin_span(
                        service_name='abbyy_ocr',
                        span_name='consume',
                        zipkin_attrs=ZipkinAttrs(trace_id=zipkin_headers['X-B3-TraceId'],
                                                 span_id=zipkin_headers['X-B3-SpanId'],
                                                 parent_span_id=zipkin_headers['X-B3-ParentSpanId'],
                                                 flags=zipkin_headers['X-B3-Flags'],
                                                 is_sampled=zipkin_headers['X-B3-Sampled'], ),
                        transport_handler=http_transport,
                        sample_rate=100,
                ):
                    case_id = data['case_id']
                    # Get OCR data of the file
                    query = 'SELECT * FROM `ocr_info` WHERE `case_id`=%s'
                    params = [case_id]
                    ocr_info = queue_db.execute(query, params=params)

                    if ocr_info.empty:
                        ocr_data = {}
                        logging.warning('OCR data is not in DB or is empty.')
                    else:
                        try:
                            ocr_data = json.loads(json.loads(list(ocr_info.ocr_data)[0]))
                        except:
                            ocr_data = json.loads(list(ocr_info.ocr_data)[0])


                    if ocr_data or overwrite:
                        response_data = abbyy_ocr(case_id, tenant_id)
                        if response_data['flag']:
                            data = response_data['send_data'] if 'send_data' in response_data else {}
                            consumer.commit()
                            logging.info('Message commited!')
                            if message_flow.empty:
                                logging.error('`folder_monitor` is not configured correctly in message flow table.')
                            else:
                                topic = list(message_flow.send_to_topic)[0]

                                if topic is not None:
                                    logging.info(f'Producing to topic {topic}')
                                    produce(topic, data)
                                else:
                                    logging.info(f'There is no topic to send to for `{topic}`.')
                        else:
                            logging.error('Message not consumed. Some error must have occured. Will try again!')
                    else:
                        logging.info("Consuming old message.")
            except:
                try:
                    case_id = data['case_id']
                    logging.info(f'case_id - {case_id}')
                    query = 'SELECT * FROM `ocr_info` WHERE `case_id`=%s'
                    params = [case_id]
                    ocr_info = queue_db.execute(query, params=params)

                    if ocr_info.empty:
                        ocr_data = {}
                        logging.warning('OCR data is not in DB or is empty.')
                    else:
                        try:
                            ocr_data = json.loads(json.loads(list(ocr_info.ocr_data)[0]))
                        except:
                            ocr_data = json.loads(list(ocr_info.ocr_data)[0])

                    if ocr_data or overwrite:
                        response_data = abbyy_ocr(case_id, tenant_id)
                        if response_data['flag']:
                            data = response_data['send_data'] if 'send_data' in response_data else {}
                            logging.info('Message commited!')
                            if message_flow.empty:
                                logging.error('`folder_monitor` is not configured correctly in message flow table.')
                            else:
                                topic = list(message_flow.send_to_topic)[0]

                                if topic is not None:
                                    logging.info(f'Producing to topic {topic}')
                                    produce(topic, data)
                                else:
                                    logging.info(f'There is no topic to send to for `{topic}`.')
                        else:
                            logging.error('Message not consumed. Some error must have occured. Will try again!')
                    else:
                        logging.info("Consuming old message.")
                except Exception as e:
                    logging.exception(f"Error. Moving to next message. [{e}]")
    except:
        logging.exception('Something went wrong in consumer. Check trace.')


if __name__ == '__main__':
    consume()
