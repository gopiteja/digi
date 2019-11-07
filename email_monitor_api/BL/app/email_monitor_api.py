import argparse
import csv
import email
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

from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from dateutil.parser import parse
from flask import request, jsonify
from itertools import chain, repeat, islice, combinations
from pandas import Series, Timedelta, to_timedelta
from py_zipkin.zipkin import zipkin_span, ZipkinAttrs, create_http_headers_for_new_span
from time import time, sleep
from email_reply_parser import EmailReplyParser

try:
    from app.mail import Email
except:
    from mail import Email
    
from producer import produce
from ace_logger import Logging
from db_utils import DB

from app import app

DATABASE = 'email'
logging = Logging()

db_config = {
    'host': os.environ['HOST_IP'],
    'port': os.environ['LOCAL_DB_PORT'],
    'user': os.environ['LOCAL_DB_USER'],
    'password': os.environ['LOCAL_DB_PASSWORD']
}

def monitor(mail, folder, output_parent, user_data):
    tenant_id = user_data.get('tenant_id', None)

    db = DB('email', tenant_id=tenant_id, **db_config)
    queue_db = DB('queues', tenant_id=tenant_id, **db_config)  
    
    logging.info('Monitoring email...')
    while True:
        mail.select(folder)
        # Check for unread
        if mail.has_unread():
            try:
                # Fetches latest unread mail and initializes all the instance variables
                email_data = mail.get_unread(today='Yes')

                logging.debug(f'Email Data: {email_data}')
                
                sender_email_id = mail.mail_from()
                sender_email_id = email.utils.parseaddr(sender_email_id)[1]
                mail_subject = mail.mail_subject().lower()
                mail_body = mail.mail_body()
                mail_body = EmailReplyParser.parse_reply(mail_body)

                p = re.compile( '([\[\(] *)?(RE?S?|FYI|RIF|I|FS|VB|RV|ENC|ODP|PD|YNT|ILT|SV|VS|VL|AW|WG|ΑΠ|ΣΧΕΤ|ΠΡΘ|תגובה|הועבר|主题|转发|FWD?) *([-:;)\]][ :;\])-]*|$)|\]+ *$', re.IGNORECASE)
                mail_subject =  p.sub( '', mail_subject).strip()
                
                user_data['subject'] = mail_subject
                user_data['sender_email'] = sender_email_id
                user_data['mail_body'] = mail_body
                
                logging.debug(f'Subject: {mail_subject}')
                logging.debug(f'Sender Email: {sender_email_id}')

                case_emails = db.get_all('case_emails')
                case_email = case_emails.loc[case_emails['email_id'].str.contains(sender_email_id, na=False)]
                logging.debug(f'Sender attachments are case files: {case_email}')

                if case_email.empty:
                    logging.debug(f'No match found. [{mail_subject}, {sender_email_id}]')
                    mail_type = 'email'
                else:
                    mail_type = 'case'

                query = "select * from folder_rules"
                output = db.execute(query)
                folder_dict = list(output.name)[0]
                try:
                    folder_dict = json.loads(folder_dict)
                except:
                    pass

                if "dynamic" in folder_dict:
                    folder_key = folder_dict.get('dynamic', None)
                    sub_folder_string = user_data.get(folder_key, None)
                    pattern = list(output.pattern)[0]
                    link = list(output.link)[0]
                    table = link.split('.')[0]
                    field = link.split('.')[1]
                    if pattern:
                        try:
                            if 'process_queue' in link:
                                link_db = queue_db
                            else:
                                link_db = DB('extraction', tenant_id=tenant_id, **db_config)  

                            m = re.search(pattern, sub_folder_string)
                            field_value = m.group()
                            query = f"select id, case_id from `{table}` where `{field}` = {field_value}" 
                            query_output = link_db.execute(query)
                            logging.debug(f"Params are {table, field, field_value}")
                            sub_folder = list(query_output.case_id)[0]
                            logging.debug(f"sub folder is {sub_folder}")

                            query = "update process_queue set unread_email = 1 where case_id = %s"
                            queue_db.execute(query, params=[sub_folder])
                        except:
                            sub_folder = None
                else:
                    sub_folder = folder_dict

                text_dict = {}
                text_dict['from'] = sender_email_id
                text_dict['body'] = mail_body
                to_email_ids = mail.mail_to()
                cc_email_ids = mail.mail_cc()
                to_email_ids = to_email_ids.split(',')
                for i, j in enumerate(to_email_ids):
                    if '<' in j:
                        to_email_ids[i] = re.findall(r'(?<=<).+(?=>)', j)[0]
                    else:
                        pass
                try:
                    cc_email_ids = cc_email_ids.split(',')
                    for i, j in enumerate(cc_email_ids):
                        if '<' in j:
                            cc_email_ids[i] = re.findall(r'(?<=<).+(?=>)', j)[0]
                        else:
                            pass
                    cc_email_ids = ', '.join(cc_email_ids)
                except:
                    cc_email_ids = ''
                to_email_ids = ', '.join(to_email_ids)

                text_dict['time'] = mail.mail_time()
                text_dict['to'] = to_email_ids
                text_dict['cc'] = cc_email_ids

                attachment_files = []
                if mail.has_attachments():
                    logging.info('Email has atatchement.')
                    attachments_dict = mail.get_attachments()
                    if sub_folder:                      
                        app_dir = '/var/www/email_monitor_api/app/email/' 
                        tenant_dir = tenant_id + '/' + sub_folder + '/'
                        parent_dir = app_dir + tenant_dir
                        for filename, data in attachments_dict.items():
                            final_path = parent_dir + mail_type + '/' + filename

                            logging.debug(f'Attachement Filename: {filename}')
                            logging.debug(f'Feed Folder: {sub_folder}')
                            logging.debug(f'Output Path: {final_path}')
                            os.makedirs(os.path.dirname(final_path), exist_ok=True)

                            try:
                                logging.debug('Saving file...')
                                with open(final_path, 'wb') as f:
                                    f.write(data)
                                logging.debug(f'File saved. [{final_path}]')
                                attachment_files.append(tenant_id + '/' + str(Path(sub_folder) / Path(mail_type) / filename))
                            except:
                                logging.exception('Error saving file.')
                    else:
                        logging.debug('No attachment path defined')
                else:
                    logging.info('Email has no atatchment.')

                text_dict['attachments'] = attachment_files
                    
                # Save email text 
                query = "select text_array from email_text where subject = %s"
                try:
                    text_array = list(db.execute_(query, params=[mail_subject]).text_array)[0]
                    text_array = json.loads(text_array)
                    text_array.append(text_dict)
                    text_array = json.dumps(text_array)
                    update = "update email_text set case_id = %s, text_array = %s where subject = %s"
                    db.execute(update, params=[sub_folder, text_array, mail_subject])
                    mail_type = 'email'
                except:
                    insert = "INSERT INTO `email_text`(`case_id`, `subject`, `text_array`) VALUES (%s, %s, %s)"
                    text_array = json.dumps([text_dict])
                    db.execute(insert, params=[sub_folder, mail_subject, text_array])
            except:
                logging.exception(f'Error occured processing email.')
        sleep(5)

@app.route('/email_monitor_api', methods=['POST', 'GET'])
def email_monitor():
    user_data = request.json
    logging.debug(f'Data received: {user_data}')
    folder = 'inbox'
    output_parent = '/var/www/email_monitor_api/app/Portal'
    email_id = os.environ['EMAIL_ADD']
    password = os.environ['EMAIL_PASS']
    mail_server = os.environ['EMAIL_SERVER'] 
    
    logging.debug(f'Email ID: {email_id}')
    logging.debug(f'Password: {password}')
    logging.debug(f'Server: {mail_server}')   

    mail = Email(mail_server)
    
    logging.debug('Logging in...')
    if not mail.login(email_id, password):
        message = 'Unable to login.'
        logging.error(message)
        return jsonify({'flag': False, 'message': message})

    monitor_thread = threading.Thread(target=monitor, args=[mail, folder, output_parent, user_data])
    monitor_thread.start()

    return jsonify({'flag':True, 'message':'Monitoring email successfully.'})

@app.route('/get_email_chain', methods=['POST', 'GET'])
def get_email_chain():
    data = request.json
    case_id = data['case_id']
    tenant_id = data.get('tenant_id', None)

    queue_db = DB('queues', tenant_id=tenant_id, **db_config)
    email_db = DB('email', tenant_id=tenant_id, **db_config)
    trigger_db = DB('email_trigger', tenant_id=tenant_id, **db_config)

    query = "select * from email_text where case_id = %s"  
    output = email_db.execute(query, params=[case_id])  
    keys = list(output.subject)
    values = list(output.text_array)
    unread = list(output.unread)
    
    output_dict = {}
    for i, key in enumerate(keys):
        email_chain = json.loads(values[i])
        email_chain[-1]['unread'] = unread[i]
        output_dict[key] = email_chain

    query = "update process_queue set unread_email = 0 where case_id = %s"  
    queue_db.execute(query, params=[case_id])

    query = "select template from email_template"
    templates = list(trigger_db.execute_(query).template)

    query = "select name from template_label"
    template_label = list(trigger_db.execute_(query).name)[0]

    return jsonify({'flag':True, 'chain': output_dict, 'templates': templates, 'template_label': template_label})

@app.route('/move_to_case', methods=['POST', 'GET'])
def move_to_case():
    data = request.json
    case_id = data.get('case_id',None)
    tenant_id = data.get('tenant_id', None)
    move_file = data.get('file_path', None)
    case_file = move_file.split('/')[-1]

    app_dir = '/var/www/email_monitor_api/app/email/' 
    tenant_dir = tenant_id + '/' + case_id
    parent_dir = app_dir + tenant_dir + '/'
    move_to = parent_dir + 'case/' + case_file

    shutil.copyfile(app_dir+move_file, move_to)

    return {"flag": True, "message": "Successfully linked file to case"}


