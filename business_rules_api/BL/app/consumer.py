import json
import traceback
import requests

from kafka import KafkaConsumer, TopicPartition

from run_business_rule import run_business_rule_consumer_
from business_rules_api import apply_business_rules
from producer import produce

from da_bizRul_factory import DABizRulFactory

try:
    from app.ace_logger import Logging
except:
    from ace_logger import Logging

from py_zipkin.zipkin import zipkin_span,ZipkinAttrs, create_http_headers_for_new_span

DAO = DABizRulFactory.get_dao_bizRul()
logging = Logging()

def http_transport(encoded_span):
    body = encoded_span
    requests.post(
        'http://servicebridge:5002/zipkin',
        data=body,
        headers={'Content-Type': 'application/x-thrift'},)

@zipkin_span(service_name='business_rules', span_name='dostuff')
def dostuff(data):
    # zipkin_headers = create_http_headers_for_new_span()
    # data['zipkin_headers'] = zipkin_headers
    response_data = run_business_rule_consumer_(**data)

    return response_data

def consume(broker_url='broker:9092'):
    try:
        overwrite = False

        message_flow = DAO.kafka_consume_get_messages()

        listen_to_topic_df = message_flow.loc[message_flow['listen_to_topic'] == 'business_rules']
        topic = list(listen_to_topic_df.listen_to_topic)[0]

        print(f'Listening to topic `{topic}`...')
        consumer = KafkaConsumer(
            bootstrap_servers=broker_url,
            value_deserializer=lambda value: json.loads(value.decode()),
            auto_offset_reset='earliest',
            group_id='business_rules_consumer',
            api_version=(0,10,1),
            enable_auto_commit=False,
            session_timeout_ms=800001,
            request_timeout_ms=800002
        )

        print('Consumer object created.')

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

            tenant_id = data['tenant_id']
            case_id = data.pop('case_id', None)
            file_name = data.pop('file_name', None)
            zipkin_headers = data['zipkin_headers']
            # print('ZH', zipkin_headers)
            with zipkin_span(service_name='business_rules', span_name='consumer', 
                zipkin_attrs=ZipkinAttrs(trace_id=zipkin_headers['X-B3-TraceId'],
                span_id=zipkin_headers['X-B3-SpanId'],
                parent_span_id=zipkin_headers['X-B3-ParentSpanId'],
                flags=zipkin_headers['X-B3-Flags'],
                is_sampled=zipkin_headers['X-B3-Sampled'],),
                transport_handler=http_transport,
                # port=5014,
                sample_rate=0.5,):
                try:
                    case_id = data['case_id']
                    
                    case_id_business_rule = DAO.extraction_db_get_data(table='business_rule', case_id=case_id)

                    if case_id_business_rule.empty or overwrite:
                        data["stage"] = "default"
                        send_to_topic = data.pop('send_to_topic', None)
                        # response_data = apply_business_rules(**data)
                        response_data = dostuff(data)

                        if response_data['flag'] == True:
                            if send_to_topic is not None or not send_to_topic:
                                message_data = response_data['send_data'] if 'send_data' in response_data else {}
                                produce(send_to_topic, message_data)
                        else:
                            traceback.print_exc()
                            print('Message consumed but some error must have occured. Will try again!')
                        print('Message commited!')
                        consumer.commit()
                    else:
                        consumer.commit()
                        print("Consuming old message.")
                except:
                    print("Error. Moving to next message")
                    continue
    except:
        logging.exception('Something went wrong in consumer. Check trace.')

    
if __name__ == '__main__':
    consume()
