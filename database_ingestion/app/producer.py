import json
import traceback
import requests

from kafka import KafkaConsumer, KafkaProducer, errors
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
    body =encoded_span
    requests.post(
            'http://servicebridge:5002/zipkin',
        data=body,
        headers={'Content-Type': 'application/x-thrift'},
    )

@zipkin_span(service_name='data_ingestion', span_name='produce_with_zipkin')
def produce_with_zipkin(producer, topic, data):
    logging.info('Producing with zipkin...')

    zipkin_headers = create_http_headers_for_new_span()
    data['zipkin_headers'] = zipkin_headers
    logging.debug(f'Zipkin data: {data}')
    
    logging.info(f'Sent to topic `{topic}` succesfully.')
    logging.debug(f'Sent data: {data}')

    producer.send(topic, value=data)
    producer.flush()


def produce(topic, data, broker_url='broker:9092'):
    logging.info(f'Sending to topic `{topic}`...')
    with zipkin_span(service_name='data_ingestion', span_name='produce', 
            transport_handler=http_transport, sample_rate=0.5,) as  zipkin_context:
        try:
            zipkin_context.update_binary_annotations({'Tenant': data['tenant_id']})
        except:
            zipkin_context.update_binary_annotations({'Tenant': None})
        try:
            # Producer send data to a topic
            producer = KafkaProducer(
                bootstrap_servers=broker_url,
                value_serializer=lambda value: json.dumps(value).encode(),
                api_version=(0,10,1)
            )

            produce_with_zipkin(producer, topic, data)
            logging.info(f'Sent to topic `{topic}` succesfully.')
            logging.debug(f'Sent data: {data}')
            return True
        except:
            logging.exception(f'Error sending to topic `{topic}`.')
            return False
