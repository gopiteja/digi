import argparse
import json
import sys
import subprocess
import time

from abbyy_sdk import ABBYY
from flask import Flask, request, jsonify
from flask_cors import CORS
from pathlib import Path
try:
    from .ace_logger import Logging
except:
    from ace_logger import Logging

logging = Logging().getLogger('ace')

app = Flask(__name__)
CORS(app)


@app.route('/sdk', methods=['POST', 'GET'])
def sdk():
    data = request.files

    file_data = data['file_data']

    count = 0
    while True:
        try:
            file_data.save('C:/Users/t00004100/Desktop/abbyy/received/ocr_file.pdf')
            break
        except:
            count += 1
            time.sleep(5)
        if count == 20:
            return jsonify({})

    logging.debug(f'{type(file_data)}')

    abbyy = ABBYY()

    sdk_output = abbyy.rotation_and_ocr("C:/Users/t00004100/Desktop/abbyy/received/ocr_file.pdf")
    return jsonify(sdk_output)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-p', '--port', type=int, help='Port Number', default=5003)
    parser.add_argument('--host', type=str, help='Host', default='0.0.0.0')

    args = parser.parse_args()

    host = args.host
    port = args.port

    app.run(host=host, port=port, debug=False)
