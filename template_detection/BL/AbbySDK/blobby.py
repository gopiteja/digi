import os
from flask_cors import CORS
from flask import Flask, jsonify, request
import subprocess
import time
import os
import traceback
import json
import ast
import base64

from threading import Lock

# from ace_logger import Logging

app = Flask(__name__)
cors = CORS(app)
# logging = Logging()
mutex = Lock()


@app.route('/database_ocr', methods=['POST', 'GET'])
def database_ocr():
    case_id = request.json['case_id']
    inp = './Run.sh '+ str(case_id)
    #inp = "/usr/bin/java -classpath '.:bin/.:libs/abbyy.FREngine.jar:libs/mysql-connector-java-8.0.17.jar' com.algonox.abbyy.OCRExtraction " + case_id 
    xml_string = subprocess.check_output(['./Run.sh',str(case_id)]).decode('utf-8').replace('\\r\\n','')
    return jsonify({'xml_string': xml_string[1:]})

@app.route('/file_ocr', methods=['POST', 'GET'])
def file_ocr():
    mutex.acquire()
    try:
        data = request.files

        curr_dir = os.path.dirname(os.path.abspath(__file__))

        # print(curr_dir)
        file_data = data['file']
        page_data = data['json']

        file_name = os.path.join(curr_dir, 'ocr_file.pdf')
        count = 0
        while True:
            try:
                print('logging to save the file')
                file_data.save(file_name)
                # print(file_name)
                # print('tryingggg')
                break
            except:
                # print('exceptingg')
                count += 1
                time.sleep(5)
            if count == 20:
                return jsonify({})

        print(f'{type(file_data)}')

        command = {'fileName': file_name}
        if page_data:
            command.update(page_data)
        command = json.dumps(command)
        # inp = './Run.sh ' + file_name
        # inp = "/usr/bin/java -classpath '.:bin/.:libs/abbyy.FREngine.jar:libs/mysql-connector-java-8.0.17.jar' com.algonox.abbyy.OCRExtraction " + case_id
        whole_load = subprocess.check_output(['./Run.sh', command]).decode('utf-8').replace('\\r\\n', '')
        # whole_load = ast.literal_eval(whole_load)
        with open('/home/ubuntu/oasis-main/template_detection/BL/AbbySDK/ocr_file.pdf','rb') as f:
            blob = base64.b64encode(f.read())

        return jsonify({'xml_string': whole_load, 'blob': blob.decode()})
    except:
        traceback.print_exc()
        return jsonify({'xml_string': ''})
    finally:
        mutex.release()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5005, debug=False, threaded=True)
