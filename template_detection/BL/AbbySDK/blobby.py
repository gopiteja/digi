import os
from flask_cors import CORS
from flask import Flask, jsonify, request
import subprocess
import time
import os
import traceback


# from ace_logger import Logging

app = Flask(__name__)
cors = CORS(app)
# logging = Logging()


@app.route('/database_ocr', methods=['POST', 'GET'])
def database_ocr():
    case_id = request.json['case_id']
    inp = './Run.sh '+ str(case_id)
    #inp = "/usr/bin/java -classpath '.:bin/.:libs/abbyy.FREngine.jar:libs/mysql-connector-java-8.0.17.jar' com.algonox.abbyy.OCRExtraction " + case_id 
    xml_string = subprocess.check_output(['./Run.sh',str(case_id)]).decode('utf-8').replace('\\r\\n','')
    return jsonify({'xml_string': xml_string[1:]})

@app.route('/file_ocr', methods=['POST', 'GET'])
def file_ocr():
    try:
        data = request.files

        curr_dir = os.path.dirname(os.path.abspath(__file__))


        file_data = data['file']

        file_name = os.path.join(curr_dir, 'ocr_file.pdf')
        count = 0
        while True:
            try:
                file_data.save(file_name)
                break
            except:
                count += 1
                time.sleep(5)
            if count == 20:
                return jsonify({})

        print(f'{type(file_data)}')

        case_id = request.json['case_id']
        inp = './Run.sh ' + str(case_id)
        # inp = "/usr/bin/java -classpath '.:bin/.:libs/abbyy.FREngine.jar:libs/mysql-connector-java-8.0.17.jar' com.algonox.abbyy.OCRExtraction " + case_id
        xml_string = subprocess.check_output(['./Run.sh', file_name]).decode('utf-8').replace('\\r\\n', '')
        return jsonify({'xml_string': xml_string[1:]})
    except:
        traceback.print_exc()
        return jsonify({'xml_string': ''})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5555, debug=False)
