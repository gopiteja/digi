import os
from flask_cors import CORS
from flask import Flask, jsonify, request
import subprocess

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

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5555, debug=False)
