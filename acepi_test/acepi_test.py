import argparse
import acepi

from ace_logger import Logging

from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

logging = Logging()

@app.route('/acepi_test', methods=['POST', 'GET'])
def acepi_test():
    data = request.json

    logging.info(f'Data: {data}')

    api_id = data.get('api_id', None)
    api_data = data.get('api_data', None)
    tenant_id = data.get('tenant_id', None)

    if api_id is None:
        return jsonify({'flag': False, 'message': 'API ID cant be none.'})

    return acepi.hit(api_id, data=api_data, tenant_id=tenant_id)

@app.route('/test_api', methods=['POST'])
def test_api():
    data = request.json

    logging.info(f'Received Data: {data}')
    logging.info(f'Args Data: {request.args.to_dict()}')

    return jsonify({'data': data, 'args': request.args.to_dict()})

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-p', '--port', type=int, help='Port Number', default=5090)
    parser.add_argument('--host', type=str, help='Host', default='0.0.0.0')

    args = parser.parse_args()

    host = args.host
    port = args.port

    app.run(host=host, port=port, debug=True)