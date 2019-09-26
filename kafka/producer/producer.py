import argparse
import json

from flask import Flask, request, jsonify
from flask_cors import CORS
from kafka import KafkaConsumer, KafkaProducer, errors

from ace_logger import Logging

app = Flask(__name__)
CORS(app)
logging = Logging().getLogger('ace')

KAFKA_BROKER_URL = 'broker:9092'
TRANSACTIONS_TOPIC = 'test.topic'
consumer = None

@app.route('/produce', methods=['POST', 'GET'])
def produce():
    try:
        logging.info('Sending...')
        data = request.json
        topic = data.pop('topic', None)

        if topic is None:
            return 'No topic was given.'

        # Producer send data to a topic
        producer = KafkaProducer(
            bootstrap_servers=KAFKA_BROKER_URL,
            value_serializer=lambda value: json.dumps(value).encode(),
            api_version=(0, 10, 1)
        )
        logging.debug('Created producer object.')

        if type(topic) is list:
            for t in topic:
                logging.debug(f'Producing to topic `{t}`')
                producer.send(t, value=data)
                producer.flush()
        elif type(topic) is str:
            logging.debug(f'Producing to topic `{topic}`')
            producer.send(topic, value=data)
            producer.flush()

        logging.info('Message sent.')
        return 'Sent'
    except Exception as e:
        logging.exeption('Could not produce. Check trace.')
        pass

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-p', '--port', type=int, help='Port Number', default=6061)
    parser.add_argument('--host', type=str, help='Host', default='0.0.0.0')

    args = parser.parse_args()

    host = args.host
    port = args.port

    app.run(host=host, port=port, debug=False)
