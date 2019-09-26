"""
@author: Srinivasan Ravichandran
"""
import os
import re
import ast
import sys
import json
import pymysql
import pythoncom
import requests

import FREConfig
from ClassifierTypeEnum import ClassifierTypeEnum

from flask import Flask, jsonify, request, url_for
from comtypes import client as cc
from flask_cors import CORS
from pprint import pprint
from pathlib import Path
from db_utils import DB
from py_zipkin.zipkin import zipkin_span,ZipkinAttrs, create_http_headers_for_new_span
from inspect import currentframe, getframeinfo

from ace_logger import Logging
logging = Logging()

def http_transport(encoded_span):
    # The collector expects a thrift-encoded list of spans. Instead of
    # decoding and re-encoding the already thrift-encoded message, we can just
    # add header bytes that specify that what follows is a list of length 1.
    body =encoded_span
    requests.post(
            'http://servicebridge:5002/zipkin',
        data=body,
        headers={'Content-Type': 'application/x-thrift'},
    )

app = Flask(__name__)
cors = CORS(app)

def get_parameters():
    """
    Util function to read config file
    """
    with open('configs/template_training_params.json') as f:
        return json.loads(f.read())

def list_routes():
    import urllib
    output = []
    for rule in app.url_map.iter_rules():

        options = {}
        for arg in rule.arguments:
            options[arg] = "[{0}]".format(arg)

        methods = ','.join(rule.methods)
        url = url_for(rule.endpoint, **options)
        if rule.endpoint != 'static':
            line = urllib.parse.unquote("{:50s} {:20s} {}".format(rule.endpoint, methods, url))
            output.append(line)
    return output

@app.route('/', methods = ['POST','GET'])
def hello_world():
    """
    To check if the app is up
    """
    try:
        name = "Template training is up and running!"
        routes = '\n'.join(list_routes())
        description = name + '\nAvailable routes are \n\n' + routes
        return description
    except Exception as e:
        return jsonify({'flag': False, 'message':'System error! Please contact your system administrator.'})

@app.route('/abbyy_initial_train', methods=['POST', 'GET'])
def initial_training():
    try:
        template1_name = request.form['template1_name']
        template2_name = request.form['template2_name']
        sample1_file_paths = ast.literal_eval(request.form['sample1_file_paths'])
        sample2_file_paths = ast.literal_eval(request.form['sample2_file_paths'])

        if sys.platform == 'win32':
                pythoncom.CoInitialize()
        engine_holder = cc.CreateObject("FREngine.OutprocLoader")
        engine = engine_holder.InitializeEngine(FREConfig.get_customer_project_id(),
                                                FREConfig.get_license_path(),
                                                FREConfig.get_license_password(),
                                                "",
                                                "",
                                                False)
        classification_engine = engine.CreateClassificationEngine()
        training_data = classification_engine.CreateTrainingData()
        parameters = get_parameters()
        path = os.path.join(parameters['training_data_path'], 'training_data.dat')
        logging.debug (f'Setting `{path}` as training_data path')
        training_data_path = path
        path = os.path.join(parameters['model_path'], 'model.dat')
        logging.debug (f'Setting `{path}` as model path')
        model_path = path
        new_template = training_data.Categories.AddNew(template1_name)
        for file_path in sample1_file_paths:
            fr_doc = engine.CreateFRDocumentFromImage(file_path, None)
            cl_obj = classification_engine.CreateObjectFromDocument(fr_doc)
            cl_obj.Description = file_path
            new_template.Objects.Add(cl_obj)
        new_template = training_data.Categories.AddNew(template2_name)
        for file_path in sample2_file_paths:
            fr_doc = engine.CreateFRDocumentFromImage(file_path, None)
            cl_obj = classification_engine.CreateObjectFromDocument(fr_doc)
            cl_obj.Description = file_path
            new_template.Objects.Add(cl_obj)
        training_data.SaveToFile(training_data_path)
        trainer = classification_engine.CreateTrainer()
        trainer.TrainingParams.ClassifierType = ClassifierTypeEnum.CT_Image
        training_data.LoadFromFile(training_data_path)
        results = trainer.TrainModel(training_data)
        model = results[0].Model
        model.SaveToFile(model_path)
        logging.debug (f'Model saved at `{model_path}`')
    except Exception as e:
        return jsonify({'flag': False, 'message':'System error! Please contact your system administrator.'})

@app.route('/abbyy_train_template', methods=['POST', 'GET'])
def abbyy_train_template():
    try:
        data = request.json
        if 'template_name' not in data:
            logging.info(f'template_name not provided in request')
            return "template_name not provided in request"
        if 'sample_file_paths' not in data:
            logging.info(f'sample_file_paths not provided in request')
            return "sample_file_paths not provided in request"
        template_name = data['template_name']
        file_names = data['sample_file_paths']
        prefix = Path('c//Users/t00004100/Desktop/ashyam/output')
        sample_file_paths = [str(prefix/x) for x in file_names]
        try:
            if sys.platform == 'win32':
                pythoncom.CoInitialize()

            # Setup ABBYY Engine
            engine_holder = cc.CreateObject("FREngine.OutprocLoader")
            engine = engine_holder.InitializeEngine(FREConfig.get_customer_project_id(),
                                                    FREConfig.get_license_path(),
                                                    FREConfig.get_license_password(),
                                                    "",
                                                    "",
                                                    False)
            classification_engine = engine.CreateClassificationEngine()
            training_data = classification_engine.CreateTrainingData()
            parameters = get_parameters()
            path = parameters['training_data_path']
            logging.info (f'Setting `{path}` as training_data path')
            training_data_path = path
            path = parameters['model_path']
            logging.info (f'Setting `{path}` as model path')
            model_path = path
            training_data.LoadFromFile(training_data_path.replace('\\', '\\\\'))

            # Create a new template and add the samples
            new_template = training_data.Categories.AddNew(template_name)
            logging.info(f'Sample file paths is `{sample_file_paths}`')
            for file_path in sample_file_paths:
                fr_doc = engine.CreateFRDocumentFromImage(file_path, None)
                cl_obj = classification_engine.CreateObjectFromDocument(fr_doc)
                cl_obj.Description = file_path
                new_template.Objects.Add(cl_obj)

            training_data.SaveToFile(training_data_path)
            logging.info (f'New data saved at `{training_data_path}`')
            trainer = classification_engine.CreateTrainer()
            trainer.TrainingParams.ClassifierType = ClassifierTypeEnum.CT_Image
            training_data.LoadFromFile(training_data_path)
            results = trainer.TrainModel(training_data)
            model = results[0].Model
            model.SaveToFile(model_path)
            logging.info (f'Model saved at `{model_path}`')
            return jsonify({"flag": True, "message" : "ABBYY Training Success"})
        except Exception as e:
            logging.exception(e)
            return jsonify({"flag": False, "message" : "ABBYY Training Failed"})
    except Exception as e:
        return jsonify({'flag': False, 'message':'System error! Please contact your system administrator.'})

if __name__ == '__main__':
    # Load app parameters from config file
    parameters = get_parameters()
    db_name = parameters['database_name']
    machines = parameters['platform']
    host = parameters['machine_ip']
    user = parameters['db_user']
    password = parameters['db_password']
    db_port = parameters['db_port']
    app_port = parameters['template_training_port']
    # Instantiate DB object
    db = DB(db_name, host=host, user=user, password=password)
    # Run app
    app.run(host=host, port=app_port, debug=False, threaded=True)
