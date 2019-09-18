import argparse
import json

from flask import Flask, request, jsonify
from flask_cors import CORS
from kafka import KafkaConsumer, KafkaProducer, errors

app = Flask(__name__)
CORS(app)

KAFKA_BROKER_URL = 'broker:9092'
consumer = None

@app.route('/consume', methods=['POST', 'GET'])
def consume():
    try:
        print('Listening...')
        data = request.json
        topic = data.pop('topic', None)

        # Consumer listens to a topic
        consumer = KafkaConsumer(
            bootstrap_servers=KAFKA_BROKER_URL,
            value_deserializer=lambda value: json.loads(value.decode()),
            auto_offset_reset='earliest',
            group_id='1',
            api_version=(0,10,1),
            enable_auto_commit=True
        )
        print('Created consumer object.')

        if consumer is not None:
            if topic is None:
                consumer.subscribe(consumer.topics())
            else:
                consumer.subscribe(topic)

            for message in consumer:
                print()
                print(f'Topic: {message.topic}')
                print(f'Value: {message.value}')
                print(f'Offset: {message.offset}')
                consumer.commit()
        else:
            return 'Consumer is None'
    except Exception as e:
        pass

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-p', '--port', type=int, help='Port Number', default=6060)
    parser.add_argument('--host', type=str, help='Host', default='0.0.0.0')

    args = parser.parse_args()

    host = args.host
    port = args.port

    app.run(host=host, port=port, debug=False)
