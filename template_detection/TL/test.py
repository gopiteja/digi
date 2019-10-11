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


def consumer_creator(topic, broker_url='broker:9092'):
    consumer = KafkaConsumer(
        bootstrap_servers=broker_url,
        value_deserializer=lambda value: json.loads(value.decode()),
        auto_offset_reset='earliest',
        group_id=topic,
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
    def test_consumer(self):
        topic = 'test_detection'
        broker_url = 'broker:9092'
        send_to_topic = 'detection'

        files = test_cases['files']
        data = files['2000459558']

        input_data = data['input']
        output = data['output']

        tenant_id = input_data['tenant_id']
        case_id = input_data['case_id']

        queue_db = DB('queues', **trained_db_config, tenant_id=tenant_id)
        template_db = DB('template_db', **trained_db_config, tenant_id=tenant_id)

        process_queue = {'case_id': case_id}
        # trained_info = {'template_name': 'test', 'field_data': json.dumps(data['input']['field_data'])}

        insert_into_db(queue_db, process_queue, 'process_queue')
        # insert_into_db(template_db, trained_info, 'trained_info')


        produce(send_to_topic, input_data)
        to_consume = 1

        try:
            logging.info(f'Listening to topic `{topic}`...')
            consumer = consumer_creator(topic=topic)
            logging.debug('Consumer object created.')
            parts = consumer.partitions_for_topic(topic)

            parts = partition_creator(parts, topic, broker_url)

            partitions = [TopicPartition(topic, p) for p in parts]
            consumer.assign(partitions)

            total = 0
            correct = 0

            for message in consumer:
                data = message.value

                consumer.commit()

                logging.info(data)


                # output = files[case_id]['output']
                try:
                    case_id = data['case_id']
                    total += 1
                    output_df = queue_db.get_all('process_queue')
                    output = files[case_id]['output']
                    self.assertEqual(list(output_df['queue'])[0], output)
                    correct += 1
                    delete_from_db(queue_db, 'process_queue', {'case_id': case_id})
                except:
                    logging.exception('something wrong with detection')

                to_consume -= 1
                if to_consume <= 0:
                    break
        except:
            logging.exception('Something went wrong in consumer. Check trace.')

        self.assertEqual(total, correct)


if __name__ == '__main__':
    unittest.main()
