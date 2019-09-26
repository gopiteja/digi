"""
Author: Akshat Goyal
Created Date: 04-02-2019
Contributors:
"""

# Python Packages
import argparse
import pdfplumber
import re
import os
import json
import pdb
import requests

from pathlib import Path
from flask import Flask, request, jsonify
from flask_cors import CORS

from ace_logger import Logging

from py_zipkin.zipkin import zipkin_span, ZipkinAttrs, create_http_headers_for_new_span

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

#global parameters
app = Flask(__name__)
cors = CORS(app)
logging = Logging().getLogger('ace')

global parameters
with open('./parameters.json') as f:
    parameters = json.loads(f.read())

""" Functions """
@zipkin_span(service_name='pdf_plumber_api', span_name='resize')
def resize(result,resize_factor):
    """
    Resizes the ocr data according to resize factor.

    Args:
            result (list[dict]): the list of words that needs to be resized
            resize_factor (float): the factor by which to resize the words dimensions and coordinates

    Returns:
            the resized data
    """
    logging.info('Entering resize')
    for i in result:
        i["width"] = int(i["width"] * resize_factor)
        i["height"] = int(i["height"] * resize_factor)
        i["top"] = int(i["top"] * resize_factor)
        i["left"] = int(i["left"] * resize_factor)
        i["bottom"] = int(i["bottom"] * resize_factor)
        i["right"] = int(i["right"] * resize_factor)

    logging.info('Exiting resize')
    return result[0]

@zipkin_span(service_name='pdf_plumber_api', span_name='ocr')
def ocr(file_path, default_img_width):
    """
    Extracts embedded ocr from digitized pdf.

    Args:
            filename (str):
            default_img_width (int): The default image width for which we have to resize the ocr

    Returns:
            ocr data as a list of dict
    """
    logging.info('Entering ocr')
    with pdfplumber.open(file_path) as pdf:
        ocr_data = []
        for page in pdf.pages:
            width = page.width
            page_data = []
            for word in page.extract_words():
                new_word = {}
                new_word['width'] = int(int(word['x1']) - int(word['x0']))
                new_word['height'] = int(int(word['bottom']) - int(word['top']))
                new_word['top'] = int(word['top'])
                new_word['bottom'] = int(word['bottom'])
                new_word['right'] = int(word['x1'])
                new_word['left'] = int(word['x0'])
                word = word['text'].replace("'",'').replace('"',"")
                word = re.sub('[(][cid].*[)]','',word)
                new_word['word'] = word

                new_word['confidence']  = 100

                resize_factor = float(default_img_width)/float(width)
                new_word =  resize([new_word], resize_factor)
                page_data.append(new_word)
            ocr_data.append(page_data)
    logging.info('Exiting ocr')
    return ocr_data

@app.route('/plumb', methods = ['POST'])
def plumb():
    """
    route to get the ocr data of the files

    Args:
            jsonified dict with key as:
            file_id (str)
            source_folder (str)

    Returns:
            dict with key as ocr_data and value as list of ocr_data
    """
    logging.info('Entering get_ocr route')
    result = request.json
    if 'tenant_id' in result:
        tenant_id = result['case_id'] 
    else:
        tenant_id = '' 
    with zipkin_span(service_name='pdf_plumber_api', span_name='plumb', 
            transport_handler=http_transport, port=5007, sample_rate=0.5,) as  zipkin_context:
        zipkin_context.update_binary_annotations({'Tenant':tenant_id})

        file_id = result['file_name']
        source_folder = './invoice_files'

        file_path  = Path(source_folder) / file_id

        try:
            response = ocr(file_path, parameters['default_img_width'])
            return jsonify({'flag': True, 'data': response})
        except:
            return jsonify({'flag': False, 'message': 'PDF Plumbing failed.'})

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-p', '--port', type=int, help='Port Number', default=5000)
    parser.add_argument('--host', type=str, help='Host', default='0.0.0.0')

    args = parser.parse_args()

    host = args.host
    port = args.port

    app.run(host=host, port=port, debug=False)
