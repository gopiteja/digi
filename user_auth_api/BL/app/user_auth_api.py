import os
import argparse
import datetime
import json
import random
import requests
import time
import traceback

from flask import Flask, request, jsonify
from flask_cors import CORS
from hashlib import sha256

from py_zipkin.zipkin import zipkin_span,ZipkinAttrs, create_http_headers_for_new_span
from db_utils import DB
from ace_logger import Logging

from app import app

logging = Logging().getLogger('ace')

# Database configuration
db_config = {
    'host': os.environ['HOST_IP'],
    'user': os.environ['LOCAL_DB_USER'],
    'password': os.environ['LOCAL_DB_PASSWORD'],
    'port': os.environ['LOCAL_DB_PORT'],
}

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

def rand_sess_id():
    sid = 'S'
    for _ in range(3):
        sid = sid + str(random.randint(111, 999))
    # print("Starting session:",sid)
    return sid

@app.route('/login', methods=['POST', 'GET'])
def login():
    """
    Log in to ACE.

    Args:
        username (str): Username of the user.
        password (str): Password of the user.

    Returns:
        flag (bool): True if success otherwise False.
        message (str): Message for the user.
        data (dict): User details from the database. This key will not be present
            if any error occurs during the process.
    """
    with zipkin_span(service_name='user_auth_api', span_name='login',
            transport_handler=http_transport, port=5001, sample_rate=0.5,):        
        content = request.get_json(force=True)
        username = content.pop('username')
        password = content.pop('password')
        tenant_id = content.pop('tenant_id', None)

        logging.debug(f'Tenant ID: {tenant_id}')

        db_config['tenant_id'] = tenant_id

        db = DB('group_access', **db_config)
        # db = DB('authentication') # Development purpose

        # Get all the users from the database
        try:
            users = db.get_all('active_directory')
            live_sessions = db.get_all('live_sessions')
        except Exception as e:
            message = f'Error fetching users from database: {e}'
            logging.exception(message)
            return jsonify({'flag': False, 'message': message})

        # Basic input/data sanity checks
        if users.empty:
            message = 'No users in the database.'
            logging.error(message)
            return jsonify({'flag': False, 'message': message})

        if username not in users.username.values:
            message = f'User Not Found.'
            logging.error(message)
            return jsonify({'flag': False, 'message': message})

        user = users.loc[users['username'] == username] # Get the user data

        # Verify entered password
        hashed_pw = sha256(password.encode()).hexdigest()
        user_pw = user.password.values[0]
        if hashed_pw != user_pw:
            message = 'Password Incorrect.'
            logging.error(message)
            return jsonify({'flag': False, 'message': message})

        if user.iloc[0]['status'] and username not in list(live_sessions.loc[live_sessions['status'] == 'active'].user):
            data = json.loads(user.drop(columns='password').to_json(orient='records'))[0]
            session_id = rand_sess_id()
            data['session_id'] = session_id

            if username not in live_sessions.user.values:
                insert = "INSERT INTO `live_sessions`(`user`, `session_id`, `status`) VALUES (%s, %s, %s)"
                params = [username, session_id, 'active']
                db.execute(insert, params=params)
            else:
                update = "UPDATE `live_sessions` SET `session_id`=%s, `status`=%s, `logout`=%s WHERE `user`=%s"
                params = [session_id, 'active', None, username]
                db.execute(update, params=params)

        # Get all the users from the database
        try:
            users = db.get_all('active_directory')
            live_sessions = db.get_all('live_sessions')
        except Exception as e:
            message = f'Error fetching users from database: {e}'
            logging.exception(message)
            return jsonify({'flag': False, 'message': message})

        if user.iloc[0]['status'] and username in live_sessions.loc[live_sessions['status'] == 'active'].user.values:
            message = 'Logged in succesfully. Previous session has been terminated'
            logging.info(message)
            data = json.loads(user.drop(columns='password').to_json(orient='records'))[0]
            session_id = rand_sess_id()
            data['session_id'] = session_id

            update = "UPDATE `live_sessions` SET `session_id`=%s, `logout`=%s WHERE `user`=%s"
            params = [session_id, None, username]
            db.execute(update, params=params)

            return jsonify({'flag': True, 'message': message, 'data': data})
        else:
            message = 'User is inactive.'
            logging.info(message)
            return jsonify({'flag': False, 'message': message})

@app.route('/logout', methods=['POST', 'GET'])
def logout():
    # Database configuration
    content = request.get_json(force=True)
    username = content.pop('username')
    session_id = content.pop('session_id')
    tenant_id = content.pop('tenant_id', None)

    with zipkin_span(service_name='user_auth_api', span_name='logout',
            transport_handler=http_transport, port=5003, sample_rate=0.05,):

        db_config['tenant_id'] = tenant_id

        db = DB('group_access', **db_config)
    

        try:
            update = "UPDATE `live_sessions` SET `status`= %s, `logout`= %s WHERE `user` = %s AND `session_id` = %s"
            currentDT = time.time()
            currentTS = datetime.datetime.fromtimestamp(currentDT).strftime('%Y-%m-%d %H:%M:%S')
            params = ['closed', currentTS, username, session_id]
            db.execute(update, params=params)

            message = 'Logged out successfully'
            logging.info(message)
            return jsonify({'flag': True, 'message': message})
        except:
            message = f'Error logging out.'
            logging.exception(message)
            return jsonify({'flag': False, 'message': message})

@app.route('/verify_session', methods=['POST', 'GET'])
def verify_session():
    try:
        data = request.json

        session_id = data.pop('session_id', None)
        tenant_id = data.pop('session_id', None)

        if session_id is None:
            message = f'No session ID provided. Cannot proceed.'
            logging.error(message)
            return jsonify({'flag': False, 'message': message})

        db_config['tenant_id'] = tenant_id

        db = DB('group_access', **db_config)
        # db = DB('authentication')

        live_sessions = db.get_all('live_sessions')

        session_id_df = live_sessions.loc[live_sessions['session_id'] == session_id]

        if session_id_df.empty:
            message = f'No such session ID `{session_id}`.'
            logging.error(message)
            return jsonify({'flag': False, 'message': message})

        active_session_id_df = session_id_df.loc[session_id_df['status'] == 'active']

        if active_session_id_df.empty:
            message = f'Session inactive. Please login.'
            logging.info(message)
            return jsonify({'flag': False, 'message': message})

        return jsonify({'flag': True})
    except Exception as e:
        message = f'error in database connection'
        return jsonify({'flag': False, 'message': message})

if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument('-p', '--port', type=int, help='Port Number', default=5003)
    parser.add_argument('--host', type=str, help='Host', default='0.0.0.0')
    args = parser.parse_args()

    host = args.host
    port = args.port

    app.run(host=host, port=port, debug=False)
