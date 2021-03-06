import json
import traceback
import requests

from kafka import KafkaConsumer, TopicPartition

from db_utils import DB
from detection_app import abbyy_template_detection, algonox_template_detection
from producer import produce
try:
    from .ace_logger import Logging
except:
    from ace_logger import Logging

from py_zipkin.zipkin import zipkin_span,ZipkinAttrs, create_http_headers_for_new_span

logging = Logging()

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

        queue_db_config = {
            'host': 'queue_db',
            'port': '3306',
            'user': 'root',
            'password': 'root'
        }
        queue_db = DB('queues', **queue_db_config)

        overwrite = False

        message_flow = kafka_db.get_all('message_flow')
        listen_to_topic_df = message_flow.loc[message_flow['listen_to_topic'] == 'detection']
        topic = list(listen_to_topic_df.listen_to_topic)[0]
        send_to_topic = list(listen_to_topic_df.send_to_topic)[0]

        logging.info(f'Listening to topic `{topic}`...')
        consumer = KafkaConsumer(
            bootstrap_servers=broker_url,
            value_deserializer=lambda value: json.loads(value.decode()),
            auto_offset_reset='earliest',
            group_id='detection',
            api_version=(0,10,1),
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
                    api_version=(0,10,1),
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

            if not data:
                logging.info(f'Got empty data. {data}')
                consumer.commit()
                continue
                
            tenant_id = ''
            if 'tenant_id' in data:
                tenant_id = data['tenant_id']
            consumer.commit()
            zipkin_headers = None
            # If folder monitor sends multiple messages, think about this
            if 'zipkin_headers' in data:
                zipkin_headers = data['zipkin_headers']
            if not zipkin_headers:
                logging.warning(f'Critical error: Zipkin headers not found')
                # print (f'Critical error: Zipkin headers not found')
            try:
                with zipkin_span(
                        service_name='detection_app',
                        span_name='consume',
                        zipkin_attrs=ZipkinAttrs(trace_id=zipkin_headers['X-B3-TraceId'],
                            span_id=zipkin_headers['X-B3-SpanId'],
                            parent_span_id=zipkin_headers['X-B3-ParentSpanId'],
                            flags=zipkin_headers['X-B3-Flags'],
                            is_sampled=zipkin_headers['X-B3-Sampled'],),
                        transport_handler=http_transport,
                        sample_rate=100,
                ):
                    case_id = data['case_id']
                    ingestion_type = data['type']
                    query = "SELECT * from process_queue where case_id = %s"
                    case_id_process = queue_db.execute(query, params = [case_id])
                    current_queue = 'Old file' if case_id_process.empty else list(case_id_process.queue)[0]
                    if not current_queue:
                        current_queue = 'New file'
                    # print(current_queue)
                    if current_queue == 'New file' or overwrite:
                        if ingestion_type == 'file_ingestion':
                            response_data = abbyy_template_detection(data)
                        else:
                            response_data = algonox_template_detection(case_id)
                        # print(response_data)
                        if response_data['flag'] == True:
                            data = response_data['send_data'] if 'send_data' in response_data else {}
                            # consumer.commit()
                            logging.info('Message commited!')
                            produce(send_to_topic, data)
                        else:
                            if 'send_to_topic' in response_data:
                                send_to_topic_bypassed = response_data['send_to_topic']
                                produce(send_to_topic_bypassed, {})
                            else:
                                logging.error('Message not consumed. Some error must have occured. Will try again!')
                    else:
                        logging.info("Consuming old message.")
            except:
                try:
                    case_id = data['case_id']
                    ingestion_type = data['type']
                    query = "SELECT * from process_queue where case_id = %s"
                    case_id_process = queue_db.execute(query, params = [case_id])
                    current_queue = 'Old file' if case_id_process.empty else list(case_id_process.queue)[0]
                    if not current_queue:
                        current_queue = 'New file'
                    # print(current_queue)
                    if current_queue == 'New file' or overwrite:
                        if ingestion_type == 'file_ingestion':
                            response_data = abbyy_template_detection(data)
                        else:
                            response_data = algonox_template_detection(case_id)
                        # print(response_data)
                        if response_data['flag'] == True:
                            data = response_data['send_data'] if 'send_data' in response_data else {}
                            # consumer.commit()
                            logging.info('Message commited!')
                            produce(send_to_topic, data)
                        else:
                            if 'send_to_topic' in response_data:
                                send_to_topic_bypassed = response_data['send_to_topic']
                                produce(send_to_topic_bypassed, {})
                            else:
                                logging.error('Message not consumed. Some error must have occured. Will try again!')
                    else:
                        logging.info("Consuming old message.")
                except Exception as e:
                    logging.warning(f"Error. Moving to next message. [{e}]")
                consumer.commit()
    except:
        logging.warning('Something went wrong in consumer. Check trace.')

if __name__ == '__main__':
    consume()
