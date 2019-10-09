import unittest
import json
import requests
import os
from db_utils import DB
from ace_logger import Logging
from producer import produce
from kafka import KafkaConsumer, TopicPartition

logging = Logging()

with open('test_cases.json') as f:
    test_cases = json.loads(f.read())

trained_db_config = {
    'host': os.environ['HOST_IP'],
    'user': os.environ['LOCAL_DB_USER'],
    'password': os.environ['LOCAL_DB_PASSWORD'],
    'port': os.environ['LOCAL_DB_PORT']
}


def insert_into_db(db, data, table):
    db.insert_dict(data, table)


def delete_from_db(db, table, where):
    query = f"delete from {table} where "
    for key, value in where.items():
        query += key + ' = ' + value

    db.execute(query)


def consumer_creator(broker_url='broker:9092'):
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

    return consumer


def partition_creator(parts, topic, broker_url):
    if parts is None:
        logging.warning(f'No partitions for topic `{topic}`')
        logging.debug(f'Creating Topic: {topic}')
        produce(topic, {})
        logging.info(f'Listening to topic `{topic}`...')
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

    return parts


class MyTestCase(unittest.TestCase):
    # def test_value_extract_(self):
    #     files = test_cases['files']
    #     data = files['2000470835']
    #     ocr_data = json.loads(data['ocr'])
    #     input_data = data['input']
    #     output = data['output']
    #
    #     tenant_id = input_data['tenant_id']
    #     case_id = input_data['case_id']
    #
    #     queue_db = DB('queues', **trained_db_config, tenant_id=tenant_id)
    #
    #     ocr_info = {'ocr_data': data['ocr'], 'case_id': case_id}
    #     process_queue = {'case_id': case_id, 'queue': 'templateExceptions'}
    #
    #     insert_into_db(queue_db, ocr_info, 'ocr_info')
    #     insert_into_db(queue_db, process_queue, 'process_queue')
    #
    #     host = os.environ['HOST_IP']
    #     port = 5002
    #     route = 'predict_field'
    #     headers = {'Content-type': 'application/json; charset=utf-8', 'Accept': 'text/json'}
    #     url = f"http://{host}:{port}/{route}"
    #     logging.info(f"url - {url}")
    #     response = requests.post(url, json=input_data, headers=headers)
    #
    #     delete_from_db(queue_db, 'process_queue', {'case_id': case_id})
    #     delete_from_db(queue_db, 'ocr_info', {'case_id': case_id})
    #
    #     self.assertEqual(response.json(), output['data'])

    def test_consumer(self):
        topic = 'test'
        broker_url = 'broker:9092'
        send_to_topic = 'extract'

        files = test_cases['files']
        data = files['2000470835']
        ocr_data = json.loads(data['ocr'])
        input_data = data['input']
        output = data['output']

        tenant_id = input_data['tenant_id']
        case_id = input_data['case_id']

        queue_db = DB('queues', **trained_db_config, tenant_id=tenant_id)
        template_db = DB('template_db', **trained_db_config, tenant_id=tenant_id)

        ocr_info = {'ocr_data': data['ocr'], 'case_id': case_id}
        process_queue = {'case_id': case_id, 'queue': 'templateExceptions', 'template_name': 'test'}
        trained_info = {'template_name': 'test', 'field_data': json.dumps(data['input']['field_data'])}

        insert_into_db(queue_db, ocr_info, 'ocr_info')
        insert_into_db(queue_db, process_queue, 'process_queue')
        insert_into_db(template_db, trained_info, 'trained_info')


        produce(send_to_topic, input_data)
        to_consume = 1

        try:
            logging.info(f'Listening to topic `{topic}`...')
            consumer = consumer_creator()
            logging.debug('Consumer object created.')
            parts = consumer.partitions_for_topic(topic)

            parts = partition_creator(parts, topic, broker_url)

            partitions = [TopicPartition(topic, p) for p in parts]
            consumer.assign(partitions)

            total = 0
            correct = 0

            for message in consumer:
                data = message.value

                case_id = '2000470835'

                output = files[case_id]['output']

                consumer.commit()
                try:
                    total += 1
                    self.assertEqual(data['data'], output['data'])
                    correct += 1
                except:
                    logging.error('something wrong with extracton')

                to_consume -= 1
                if to_consume <= 0:
                    break

        except:
            logging.exception('Something went wrong in consumer. Check trace.')

        self.assertEqual(total, correct)


if __name__ == '__main__':
    unittest.main()
