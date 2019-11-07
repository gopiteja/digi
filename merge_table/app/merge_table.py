"""
Author: Ashyam
Created Date: 20-02-2019
"""
import json
import os
import pandas as pd
import requests

from flask import Flask, request, jsonify, flash

from app import app
from ace_logger import Logging
from db_utils import DB

logging = Logging()
db_config = {
    'host': os.environ['HOST_IP'],
    'user': os.environ['LOCAL_DB_USER'],
    'password': os.environ['LOCAL_DB_PASSWORD'],
    'port': os.environ['LOCAL_DB_PORT']
}

SOURCE_TYPES = ['db']
JOIN_TYPES = ['left', 'inner']

def ace_table_to_df(table_data):
    logging.info('Converting ACE table format to DataFrame.')

    cleaned_data = []
    header = []

    for idx, row in enumerate(table_data):
        row_data = []
        
        for col in row:
            if idx == 0:
                header.append(col[0])
            else: 
                row_data.append(col[0])
        
        if idx != 0:
            logging.debug(f'Row: {row_data}')
            cleaned_data.append(row_data)

    data = pd.DataFrame(cleaned_data, columns=header)

    logging.debug(f'Extracted data (DF): {data}')

    return data

def df_to_ace_table(df):
    logging.info(f'Converting DF to ACE format')

    ace_header_row = [[header, 1, 1] for header in list(df)]
    logging.debug(f'Headers: {ace_header_row}')

    ace_table = [ace_header_row]
    for _, df_row in df.iterrows():
        logging.debug(f'DF Row: {df_row}')
        row = []

        for header_col in ace_header_row:
            row.append([df_row[header_col[0]], 1, 1])

        ace_table.append(row)

    return ace_table

def get_db_data(config, columns):
    logging.info('Getting data from DB')

    required_keys = ['database', 'table']

    if not all(key in required_keys for key in config):
        raise ValueError(f'Invalid source config. Required keys - {required_keys}, got keys - {list(config.keys())}')

    database = config['database']
    table = config['table']

    host = config.get('host', None)
    port = config.get('port', None)
    user = config.get('user', None)
    password = config.get('password', None)
    
    # Check if any custom server outside ACE is to be used
    if all(i is None for i in [host, port, user, password]):
        logging.info(f'Using ACE SQL server.')
        db = DB(database, **db_config)
    else:
        logging.info(f'Found custom SQL configuration. {[host, port, user, password]}')
        db = DB(database, host=host, port=port, user=user, password=password)

    # If columns are not given, select all
    if columns is None:
        logging.debug(f'No columns given. Selecting all.')
        data = db.get_all(table)
    elif isinstance(columns, list):
        logging.debug(f'Selecting columns: {columns}')
        select_part = ', '.join([f'`{col}`' for col in columns])
        query = f'SELECT {select_part} FROM {table}'
        data = db.execute_(query)

    return data

def fetch_external_data(source_type, source_config, source_columns):
    logging.info('Fetching external data')

    if source_type == 'db':
        return get_db_data(source_config, source_columns)

def merge_data(extracted, external, join_on, join_type):
    logging.info('Merging data')

    join_extract_col, join_external_col = join_on

    logging.debug(f'Column to join from extracted data: {join_extract_col}')
    logging.debug(f'Column to join from external data: {join_external_col}')

    if join_external_col != join_extract_col:
        logging.debug('Join columns are not same. Renaming external data column.')
        external = external.rename(columns={join_external_col: join_extract_col})
        logging.debug(f'Renamed external data columns: {list(external.columns)}')
    
    merged_data = pd.merge(extracted, external, on=join_extract_col, how=join_type).fillna('')

    logging.debug(f'Merged data: {merged_data}')

    return merged_data

@app.route('/merge_table', methods=['POST', 'GET'])
def merge_table():
    data = request.json
    logging.info(f'Data Received: {data}')

    tenant_id = data.get('tenant_id', None)
    table_data = data.get('table', None)
    button_id = data.get('button_id', None)

    # Sanity check
    try:
        assert (None not in [table_data, button_id]), 'Incorrect data recieved.'
    except:
        return jsonify({'flag': False, 'message': 'Incorrect data recieved.'})
    
    # Fetch merge configuration using button ID
    merge_db = DB('merge_table', tenant_id=tenant_id, **db_config)
    config = merge_db.get_all('merge_table_config', condition={'id': button_id})
    
    if config.empty:
        message = f'No config found for ID `{button_id}`'
        logging.error(message)
        return jsonify({'flag': False, 'message': message})

    source_type = list(config['source_type'])[0].lower()
    source_config = list(config['source_config'])[0]
    source_columns = list(config['source_columns'])[0]
    join_on = list(config['join_on'])[0]
    join_type = list(config['join_type'])[0].lower()

    logging.debug(f'Source Type: {source_type}')
    logging.debug(f'Source Config: {source_config}')
    logging.debug(f'Source Column: {source_columns}')
    logging.debug(f'Join On: {join_on}')
    logging.debug(f'Join Type: {join_type}')

    # * Check if all configurations are correct
    # Check source type
    if source_type not in SOURCE_TYPES:
        message = f'Invalid source type. [valid: {SOURCE_TYPES}]'
        logging.error(message)
        return jsonify({'flag': False, 'message': message})

    # Check source config
    try:
        source_config = json.loads(list(config['source_config'])[0])
    except:
        message = 'Error loading the config'
        logging.exception(message)
        return jsonify({'flag': False, 'message': message})

    # Convert source column to list is given. Else use all columns.
    if isinstance(source_columns, str):
        source_columns = source_columns.split(',')

    # Check join_on
    if isinstance(join_on, str):
        join_on = join_on.split(',')

        if len(join_on) != 2:
            message = f'Join on columns are not configured correctly. It has to have 2 comma separated values.'
            logging.error(message)
            return jsonify({'flag': False, 'message': message})
        elif '' in join_on:
            message = f'Join on columns are not configured correctly. Found an empty string in join columns.'
            logging.error(message)
            return jsonify({'flag': False, 'message': message})
    else:
        message = f'Join on columns is not a string. [type: {type(join_on)}]'
        logging.error(message)
        return jsonify({'flag': False, 'message': message})

    # Check join type
    if join_type not in JOIN_TYPES:
        message = f'Invalid join type. [valid: {JOIN_TYPES} got: {join_type}]'
        logging.error(message)
        return jsonify({'flag': False, 'message': message})

    # * Convert table data to df
    try:
        table_df = ace_table_to_df(table_data)
    except:
        message = 'Could not convert extracted data to DataFrame.'
        logging.exception(message)
        return jsonify({'flag': False, 'message': message})

    # * Fetch external data based on the source type and configuration
    try:
        external_df = fetch_external_data(source_type, source_config, source_columns)
        logging.debug(f'External Data: {external_df}')
    except ValueError as e:
        logging.error(e)
        return jsonify({'flag': False, 'message': str(e)})
    except:
        message = f'Unable to fetch external data source.'
        logging.exception(message)
        return jsonify({'flag': False, 'message': message})

    if not isinstance(external_df, pd.DataFrame):
        message = f'External data is not dataframe ({type(external_df)}). Can not proceed.'
        logging.error(message)
        return jsonify({'flag': False, 'message': message})

    # * Merge the 2 data
    try:
        merged_data = merge_data(table_df, external_df, join_on, join_type)
    except:
        message = f'Unable to merge data.'
        logging.exception(message)
        return jsonify({'flag': False, 'message': message})

    # * Convert DataFrame back to ACE table format
    try:
        final_table_data = df_to_ace_table(merged_data)
    except:
        message = f'Unable to convert merged data into ACE table format.'
        logging.exception(message)
        return jsonify({'flag': False, 'message': message})

    return jsonify(final_table_data)
