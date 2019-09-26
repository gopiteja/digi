import json
import math
import traceback

from kafka import KafkaConsumer

from clustering_app import cluster
from db_utils import DB
from producer import produce
try:
    from .ace_logger import Logging
except:
    from ace_logger import Logging

logging = Logging()

from py_zipkin.zipkin import zipkin_span,ZipkinAttrs, create_http_headers_for_new_span

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

        message_flow = kafka_db.get_all('message_flow')
        listen_to_topic_df = message_flow.loc[message_flow['listen_to_topic'] == 'clustering']
        topic = list(listen_to_topic_df.listen_to_topic)[0]
        send_to_topic = list(listen_to_topic_df.send_to_topic)[0]

        logging.info(f'Listening to topic `{topic}`...')
        consumer = KafkaConsumer(
            topic,
            bootstrap_servers=broker_url,
            value_deserializer=lambda value: json.loads(value.decode()),
            auto_offset_reset='earliest',
            api_version=(0,10,1),
            enable_auto_commit=True
        )
        logging.info('Consumer object created.')

        cluster_me = False
        try:
            process_queue_df = queue_db.get_all('process_queue',discard=['ocr_data','ocr_text','xml_data'])
            case_id_process = process_queue_df.loc[process_queue_df['queue'] == 'Template Exceptions']
            temp_exceptions = list(case_id_process.cluster)

            for i in temp_exceptions:
                # print(i)
                if i:
                    if math.isnan(i):
                        cluster_me = True
                        break

            # cluster_me = True

            if cluster_me:
                try:
                    cluster()
                    # consumer.commit()
                    logging.info('Message commited!')
                except:
                    logging.exception('Message not consumed. Some error must have occured. Will try again!')
            else:
                logging.info('Already clustered')
        except Exception as e:
            logging.info("Consuming old message", e)
        consumer.commit()
    except Exception as e:
        logging.exception('Something went wrong in consumer. Check trace.')        

if __name__ == '__main__':
    consume()
