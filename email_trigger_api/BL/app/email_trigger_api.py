import argparse
import csv
import email
import base64
import json
import argparse
import io
import os
import re
import threading
import traceback
import shutil
import requests
import traceback
from pathlib import Path
from collections import defaultdict

from datetime import datetime, timedelta
from dateutil.parser import parse
from flask import request, jsonify
from pandas import Series, Timedelta, to_timedelta
from py_zipkin.zipkin import zipkin_span, ZipkinAttrs, create_http_headers_for_new_span
from time import time, sleep

import socket
import smtplib

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email import encoders
from email.mime.base import MIMEBase
    
from producer import produce
from ace_logger import Logging
from db_utils import DB

from app import app

DATABASE = 'email_trigger'
logging = Logging()

db_config = {
    'host': os.environ['HOST_IP'],
    'port': os.environ['LOCAL_DB_PORT'],
    'user': os.environ['LOCAL_DB_USER'],
    'password': os.environ['LOCAL_DB_PASSWORD']
}

@app.route('/send_email', methods=['POST', 'GET'])
def send_email():
    data = request.json

    case_id = data['case_id']
    tenant_id = data['tenant_id']
    message = data['message']
    file_obj = data.get('file_obj',None)
    template = data['template']
    app_dir = '/var/www/email_trigger_api/app/email/' 
    tenant_dir = tenant_id + '/' + case_id + '/unclassified/'
    parent_dir = app_dir + tenant_dir
    os.makedirs(os.path.dirname(parent_dir+'create.txt'), exist_ok=True)

    db_config['tenant_id'] = tenant_id
    email_db = DB(DATABASE, **db_config)
    text_db = DB('email', **db_config)

    attachment_filenames = []
    if file_obj:
        for obj in file_obj:
            attachment_filenames.append(tenant_dir + obj['file_name'])

    query = "select * from email_template where template = %s"
    template_data = email_db.execute(query, params=[template])
    # attachment_type = list(template_data.attachment_type)[0]

    from_email = list(template_data.from_email)[0]
    password = list(template_data.password)[0]

    msg = MIMEMultipart() # Create a message
    msg['From'] = from_email
    msg['To'] = message["to_email"]
    msg['CC'] = message["cc_to"]
    msg['Subject'] = message["subject"]
    body = message['body']
    msg.attach(MIMEText(body, 'html', 'utf-8'))

    p = MIMEBase('application', 'octet-stream') 
    if file_obj:
        for obj in file_obj: 
            p = MIMEBase('application', 'octet-stream')          
            with open(parent_dir + obj['file_name'], 'wb') as f:
                f.write(base64.b64decode(obj['blob'].split(',')[1])) 
            
            with open(parent_dir + obj['file_name'], 'rb') as read_file:
                p.set_payload((read_file).read())

            encoders.encode_base64(p)
            p.add_header('Content-Disposition', 'attachment; filename={}'.format(obj['file_name']))
            msg.attach(p)

    insert = "INSERT INTO `email_text`(`case_id`, `subject`, `text_array`) VALUES (%s, %s, %s)"
    text_dict = {}
    text_dict['from'] = from_email
    text_dict['body'] = body
    text_dict['time'] = datetime.now().strftime(r'%a, %-d %b %Y %H:%M:%S')
    text_dict['to'] = message["to_email"]
    text_dict['cc'] = message["cc_to"]
    text_dict['attachments'] = attachment_filenames

    text_array = json.dumps([text_dict])
    text_db.execute(insert, params=[case_id, message["subject"], text_array])

    mail_server = os.environ['EMAIL_SERVER'] 

    s = smtplib.SMTP(mail_server, 587)

    # Start TLS for security
    s.starttls()

    # Authentication
    s.login(from_email, password)

    # Converts the Multipart msg into a string
    text = msg.as_string()

    #Adding cc emails 
    to_emails = message["to_email"].split() 
    to_emails += message["cc_to"].split()

    # Send the mail
    # s.sendmail(from_email, to_emails + cc, text)
    s.sendmail(from_email, to_emails, text)

    # Terminate session
    s.quit()
    # except Exception as e:
    #     message = f'Error sending mail: {e}'
    #     print(message)
    #     return jsonify({'flag': False, 'message': message})


    message = f'Succesfully sent mail.'
    print(message)
    return jsonify({'flag': True, 'message': message})

@app.route('/reply', methods=['POST', 'GET'])
def reply():
    data = request.json

    case_id = data.get('case_id', None)
    tenant_id = data.get('tenant_id',None)
    subject = data.get('subject',None)
    body = data.get('body',None)
    send_to = data.get('send_to',None)
    cc = data.get('cc',None)
    file_obj = data.get('file_obj',None)
    from_email = os.environ['EMAIL_ADD']
    password = os.environ['EMAIL_PASS']
    app_dir = '/var/www/email_trigger_api/app/email/' 
    tenant_dir = tenant_id + '/' + case_id + '/email/'
    parent_dir = app_dir + tenant_dir
    os.makedirs(os.path.dirname(parent_dir+'create.txt'), exist_ok=True)

    attachment_filenames = []
    for obj in file_obj:
        attachment_filenames.append(tenant_dir + obj['file_name'])

    db_config['tenant_id'] = tenant_id
    email_db = DB('email', **db_config)

    if from_email not in send_to:
        query = "select * from email_text where subject = %s"
        text_data = email_db.execute(query, params=[subject])
        try:
            text_array = json.loads(list(text_data.text_array)[0])
            new_dict = {}
            new_dict['from'] = from_email
            new_dict['time'] = datetime.now().strftime(r'%a, %-d %b %Y %H:%M:%S')
            new_dict['body'] = body
            new_dict['to'] = send_to
            new_dict['cc'] = cc
            new_dict['attachments'] = attachment_filenames

            text_array.append(new_dict)
            text_array = json.dumps(text_array)
            update = "update email_text set text_array = %s where subject = %s"
            email_db.execute(update, params=[text_array, subject])
        except Exception as e:
            logging.debug(e)
            return jsonify({'flag': False, 'message': 'Some error occured saving reply to DB'})

    # try:
    msg = MIMEMultipart() # Create a message
    msg['From'] = from_email
    msg['To'] = send_to
    msg['CC'] = cc
    msg['Subject'] = subject 
    msg.attach(MIMEText(body, 'html', 'utf-8'))

    if file_obj:
        for obj in file_obj: 
            p = MIMEBase('application', 'octet-stream')          
            with open(parent_dir + obj['file_name'], 'wb') as f:
                f.write(base64.b64decode(obj['blob'].split(',')[1])) 
            
            with open(parent_dir + obj['file_name'], 'rb') as read_file:
                p.set_payload((read_file).read())

            encoders.encode_base64(p)
            p.add_header('Content-Disposition', 'attachment; filename={}'.format(obj['file_name']))
            msg.attach(p)

    mail_server = os.environ['EMAIL_SERVER'] 

    s = smtplib.SMTP(mail_server, 587)

    # Start TLS for security
    s.starttls()

    # Authentication
    s.login(from_email, password)

    # Converts the Multipart msg into a string
    text = msg.as_string()

    #Adding cc emails 
    to_emails = send_to.split() 
    to_emails += cc.split()

    # Send the mail
    # s.sendmail(from_email, to_emails + cc, text)
    s.sendmail(from_email, to_emails, text)

    # Terminate session
    s.quit()
    # except Exception as e:
    #     message = f'Error sending mail: {e}'
    #     print(message)
    #     return jsonify({'flag': False, 'message': message})


    message = f'Succesfully sent mail.'

    return jsonify({'flag': True, 'message': message})

@app.route('/get_template', methods=['POST', 'GET'])
def get_template():
    data = request.json
    case_id = data.get('case_id', None)
    template = data.get('template', None)
    tenant_id = data.get('tenant_id', None)
    
    db_config['tenant_id'] = tenant_id
    email_db = DB(DATABASE, **db_config)
    queue_db = DB('queues', **db_config)
    extraction_db = DB('extraction', **db_config)

    query = "select * from email_template where template = %s"
    template_data = email_db.execute(query, params=[template])

    placeholders = json.loads(list(template_data.placeholder)[0])

    placeholder_values = defaultdict(lambda: defaultdict(dict))

    email_adds = ["to_email", "cc_to"]

    for column, value in placeholders.items():
        for key, val in value.items():
            source = val.split('.')[0]
            field_val = val.split('.')[-1]
            logging.debug(source)
            if source == 'db':
                placeholder_values[column][key] = list(template_data[key])[0]
            elif source == 'process_queue':
                query = f"select `{field_val}` from `{source}` where `case_id` = {case_id}" 
                placeholder_values[column][key] = list(queue_db.execute_(query)[field_val])[0]
            else:
                query = f"select `{field_val}` from `{source}` where `case_id` = {case_id}" 
                placeholder_values[column][key] = list(extraction_db.execute_(query)[field_val])[0]
                
    for ele in email_adds:
        if ele not in placeholder_values:
            placeholder_values[ele] = list(template_data[ele])[0]
        else:
            placeholder_values[ele] = placeholder_values[ele][ele]

    try:
        subject = list(template_data.subject)[0].format(**placeholder_values['subject'])
    except:
        subject = list(template_data.subject)[0]
    placeholder_values['subject'] = subject
    try:
        body = list(template_data.body)[0].format(**placeholder_values['body'])
    except:
        body = list(template_data.body)[0]
    placeholder_values['body'] = body.replace("\r\n", "<br />")

    try:
        placeholder_values['to_email'] = placeholder_values['to_email'].replace('"','')
    except:
        placeholder_values['to_email'] = ''
    try:
        placeholder_values['cc_to'] = placeholder_values['cc_to'].replace('"','')
    except:
        placeholder_values['cc_to'] = ''
      
    logging.debug(placeholder_values)

    return jsonify({"flag": True, "data": placeholder_values})
