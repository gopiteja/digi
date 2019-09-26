#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Nov 20 17:36:39 2018

@author: ashyamzubair
"""
import argparse
import json
import traceback

from ABBYY import CloudOCR
from pathlib import Path
from xml_parser_sdk import convert_to_json
try:
    from .ace_logger import Logging
except:
    from ace_logger import Logging

logging = Logging().getLogger('ace')

DEBUG = True

def ocr_cloud(image_path, output_type='xml', ocr_user='oasis-dr', ocr_pass='u6OP5oCPEpQwIAD7MJf+6rB2'):
    logging.info('Running OCR on cloud')

    logging.info(f' - ID:{ocr_user}')
    logging.info(f' - PW:{ocr_pass}')

    try:
        # Instantiate CloudOCR
        ocr_engine = CloudOCR(application_id=ocr_user, password=ocr_pass)

        # Create file
        # image = open(image_path, 'rb')
        # file = {image_path: image}

        # OCR MICR text
        # micr_string = ocr_engine.process_and_download(file, exportFormat=output_type, textType='e13b')

        # Create file
        image = open(image_path, 'rb')
        file = {str(image_path): image}

        # OCR normal text
        parameters = {
            'language': 'English',
            'exportFormat': output_type
        }
        text_xml = ocr_engine.process_and_download(file, **parameters)

        if 'rtf' in text_xml:
            text_data = text_xml['rtf'].read().decode()
        elif output_type == 'txt':
            text_data = text_xml[output_type].read().decode()
        elif output_type == 'xml':
            text_data = text_xml[output_type].read().decode()

        return text_data
    except:
        logging.exception('error in ocr')
        return None

log = lambda *args: print(*args) if DEBUG else print(end='')

# if __name__ == '__main__':
#     init(autoreset=True)
