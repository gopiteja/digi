import argparse
import email
import flask
import json
import numpy as np
import os
import pandas as pd
import pdb
import requests
import sys
import time
import traceback

from colorama import init, Fore
from datetime import datetime
from flask_cors import CORS
from flask import Flask, jsonify, request, redirect, url_for

from db_utils import DB
from mail import Email

app = Flask(__name__)
cors = CORS(app)

@app.route('/get_all_email_details', methods=['POST', 'GET'])
def get_all_email_details():
    # If POST request the get the details of only the email give.
    # Else return all users details.
    if request.method == 'POST':
        user_data = request.json
        email_id = user_data['email_id']
        final_data = get_email_data(email_id)
    elif request.method == 'GET':
        db = DB('email')
        email_data = db.get_all('user_email')
        emails = list(email_data['email'])
        final_data = []

        for email in emails:
            if email_data.pop('flag'):
                final_data.append(email_data)

    return jsonify({'flag': True, 'data': final_data}) 

@app.route('/email', methods=['POST', 'GET'])
def email_monitoring():
    user_data = request.json
    email_id = user_data['email_id']
    password = user_data['password']
    mail_server = user_data['mail_server']
    folder = user_data['folder']
    filtering_rules = user_data['filtering_rules']

    # Convert CC list to comma separated
    for rule in filtering_rules:
        rule['cc'] = ','.join(rule['cc'])
    filtering_rules = pd.DataFrame(filtering_rules) # Convert rules to DataFrame

    mail = Email(mail_server)  # Instantiate IMAP server

    # Step 1: Validate email
    if not valid_email(email_id, password, mail_server):
        message = f'Unable to login. Check email configuration.'
        print(f'{Fore.RED}{message}')
        return jsonify({'flag': False, 'message': message})
    else:
        mail.login(email_id, password)
        print(f'{Fore.GREEN}Logged in succesfully!')

    # Step 2: Add email to db
    db = DB('email')

    existing_data = db.get_all('user_email')
    matched_emails = existing_data.loc[existing_data['email'] == email_id]

    # Add email if it doesn't exist
    if matched_emails.empty:
        # Create new email DataFrame
        email_to_add = [{
            'email': email_id,
            'server': mail_server,
            'folder': folder
        }]
        email_to_add = pd.DataFrame(email_to_add)
        email_to_add.index.name = 'id'

        # Append to the existing one
        final_data = existing_data.append(email_to_add).reset_index()
        final_data = final_data.drop(final_data.columns[0], axis=1) # Remove id/index column

        # Insert new data into database
        db.insert(final_data, 'user_email', if_exists='replace', index_label='id')

    # Step 3: Update filtering rules table
    # Get all filtering rules
    # Remove rules related to the email from original data
    # Join new rules given by th UI with original data
    # Add the final set of rules to the database
    rules_data = db.get_all('test_rules', 'email')
    rules_data = rules_data.drop(rules_data[rules_data['related_id'] == email_id].index)

    # TODO: Related email should be added from UI by default
    filtering_rules['related_id'] = pd.Series(email_id, index=filtering_rules.index)
    rules_to_db = rules_data.append(filtering_rules, ignore_index=True, sort=False)
    db.insert(rules_to_db, 'test_rules', if_exists='replace', index_label='id')

    # TODO: Separate the below code to a different function
    

    return jsonify({'flag': True, 'data': email_data})

def get_email_data(email_id):
    db = DB('email')

    # Get all email details and check if the email ID exists
    email_data = db.get_all('user_email')
    matched_emails = email_data.loc[email_data['email'] == email_id]
    if matched_emails.empty:
        message = f'Email ID {email_id} not found'
        print(f'{Fore.RED}{message}')
        return {'flag': False, 'message': message}

    # Get all filtering rules for the particular email
    filtering_rules_db = db.get_all('filtering_rules')
    related_id_rules = filtering_rules_db.loc[filtering_rules_db['related_id'] == email_id]
    if related_id_rules.empty:
        message = f'No rules found for email ID {email_id}'
        print(f'{Fore.RED}{message}')
        return {'flag': False, 'message': message}

    email_details = json.loads(matched_emails.to_json(orient='records'))[0]
    filtering_rules = json.loads(related_id_rules.to_json(orient='records'))

    # Convert comma separated CC to list
    for rule in filtering_rules:
        rule['cc'] = rule['cc'].split(',')

    final_data = {
        'flag': True,
        **email_details,
        'filtering_rules': filtering_rules,
        'num_of_rules': len(filtering_rules)
    }

    return final_data

def valid_email(email_id, password, mail_server):
    return Email(mail_server).login(email_id, password) # Log in to the mail box

if __name__ == '__main__':
    init(autoreset=True) # Intialize colorama

    parser = argparse.ArgumentParser()
    parser.add_argument('-p', '--port', type=int, help='Port Number', default=5001)
    parser.add_argument('--host', type=str, help='Host', default='0.0.0.0')
    args = parser.parse_args()

    host = args.host
    port = args.port

    app.run(host=host, port=port, debug=True)
