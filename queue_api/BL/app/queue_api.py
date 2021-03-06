import argparse
import ast
import base64
import json
import requests
import traceback
import warnings
import os
import pandas as pd

from datetime import datetime, timedelta
from db_utils import DB
from flask import Flask, request, jsonify
from flask_cors import CORS
from pandas import Series, Timedelta, to_timedelta
from time import time
from itertools import chain, repeat, islice, combinations

try:
    # from app.db_utils import DB
    from app.get_fields_info import get_fields_info
    from app.get_fields_info_utils import sort_ocr
    from app.ace_logger import Logging
except:
    # from db_utils import DB
    from get_fields_info import get_fields_info
    from get_fields_info_utils import sort_ocr
    from ace_logger import Logging
    
from py_zipkin.zipkin import zipkin_span, ZipkinAttrs, create_http_headers_for_new_span
    
from app import app
from app import cache 

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

def isListEmpty(inList):
    if isinstance(inList, list):    # Is a list
        return all( map(isListEmpty, inList) )
    return False # Not a list


def update_queue_trace(queue_db,case_id,latest):
    queue_trace_q = "SELECT * FROM `trace_info` WHERE `case_id`=%s"
    queue_trace_df = queue_db.execute(queue_trace_q,params=[case_id])

    if queue_trace_df.empty:
        message = f' - No such case ID `{case_id}` in `trace_info`.'
        logging.error(message)
        return {'flag':False,'message':message}
    # Updating Queue Name trace
    try:
        queue_trace = list(queue_trace_df.queue_trace)[0]
    except:
        queue_trace = ''
    if queue_trace:
        queue_trace += ','+latest
    else:
        queue_trace = latest

    #Updating last_updated_time&date

    try:
        last_updated_dates = list(queue_trace_df.last_updated_dates)[0]
    except:
        last_updated_dates = ''
    if last_updated_dates:
        last_updated_dates += ','+ datetime.now().strftime(r'%d/%m/%Y %H:%M:%S')
    else:
        last_updated_dates = datetime.now().strftime(r'%d/%m/%Y %H:%M:%S')

    update = {'queue_trace':queue_trace}
    where = {'case_id':case_id}
    update_q = "UPDATE `trace_info` SET `queue_trace`=%s, `last_updated_dates`=%s WHERE `case_id`=%s"
    queue_db.execute(update_q,params=[queue_trace,last_updated_dates,case_id])

    return {'flag':True,'message':'Updated Queue Trace'}

# @app.route('/get_template_exceptions', methods=['POST', 'GET'])
def get_template_exceptions(db, data):
    # data = request.json

    logging.info('Getting template exceptions')
    logging.info(f'Data: {data}')
    start_point = data['start']
    end_point = data['end']
    offset = end_point - start_point

    template_config = {
        'host': 'template_db',
        'port': 3306,
        'user': 'root',
        'password': 'root'
    }
    template_db = DB('template_db', **template_config)
    # db = DB('queues')

    # TODO: Value of "columns" will come from a database.
    # Columns to display is configured by the user from another screen.
    columns = [
            'case_id',
            'cluster',
            'created_date',
            'operator'
        ]

    column_mapping = {
        "fax_unique_id": "case_id",
        "cluster": "cluster",
        "created_date": "created_date",
        "agent": "operator"
        }

    column_order = list(column_mapping.keys())

    all_st = time()
    logging.debug(f'Selecting columns: {columns}')

    process_queue_df = db.execute("SELECT * from `process_queue` where `queue`= 'Template Exceptions' LIMIT %s, %s", params=[start_point, offset])
    total_files = list(db.execute("SELECT id,COUNT(DISTINCT `case_id`) FROM `process_queue` WHERE `queue`= %s", params=['Template Exceptions'])['COUNT(DISTINCT `case_id`)'])[0]

    logging.debug(f'Loading process queue {time()-all_st}')
    rest_st = time()
    # trained_info = template_db.get_all('trained_info')
    
    try:
        queue_files = process_queue_df
        files = queue_files[columns].to_dict(orient='records')
        for document in files:
            document['created_date'] = (document['created_date']).strftime(r'%B %d, %Y %I:%M %p')
        # trained_templates = sorted(list(trained_info.template_name),key=str.lower)
        trained_templates = []

        if end_point > total_files:
            end_point = total_files

        pagination = {"start": start_point + 1, "end": end_point, "total": total_files}

        db.engine.close()
        template_db.engine.close()

        db.db_.dispose()
        template_db.db_.dispose()

        return {'flag': True, 'data': {'columns': columns, 'column_mapping': column_mapping,'files': files, 'template_dropdown': trained_templates, 'pagination': pagination, 'column_order': column_order}}
    except Exception as e:
        message = f'Error occured while getting template exception details. {e}'
        logging.error(message)
        db.engine.close()
        template_db.engine.close()
        return {'flag': False, 'message': message}

def get_snapshot(db, data):
    # data = request.json
    # db = DB('queues')

    start_point = data['start']
    end_point = data['end']
    offset = end_point - start_point

    # TODO: Value of "columns" will come from a database.
    # Columns to display is configured by the user from another screen.
    columns = [
            'case_id',
            'queue',
            'created_date',
        ]

    column_mapping = {
        "fax_unique_id": "case_id",
        "current_queue": "queue",
        "created_date": "created_date",
        }

    column_order = list(column_mapping.keys())

    all_st = time()
    logging.debug(f'Selecting columns: {columns}')

    process_queue_df = db.execute("SELECT * from `process_queue` LIMIT %s, %s", params=[start_point, offset])
    total_files = list(db.execute("SELECT id,COUNT(DISTINCT `case_id`) FROM `process_queue`")['COUNT(DISTINCT `case_id`)'])[0]

    logging.debug(f'Loading process queue {time()-all_st}')
    rest_st = time()
    # trained_info = template_db.get_all('trained_info')
    
    try:
        queue_files = process_queue_df
        files = queue_files[columns].to_dict(orient='records')
        for document in files:
            document['created_date'] = (document['created_date']).strftime(r'%B %d, %Y %I:%M %p')

        if end_point > total_files:
            end_point = total_files

        pagination = {"start": start_point + 1, "end": end_point, "total": total_files}

        return {'flag': True, 'data': {'columns': columns, 'column_mapping': column_mapping,'files': files, 'pagination': pagination, 'column_order': column_order}}
    except Exception as e:
        message = f'Error occured while getting snapshot details. {e}'
        logging.error(message)
        db.engine.close()
        return {'flag': False, 'message': message}

@cache.memoize(86400)
def get_blob(case_id, tenant_id):
    db_config = {
        'host': 'queue_db',
        'port': 3306,
        'user': 'root',
        'password': 'root',
        'tenant_id': tenant_id
    }
    db = DB('queues', **db_config)

    query = "SELECT id, TO_BASE64(merged_blob) as merged_blob FROM merged_blob WHERE case_id=%s"
    blob_data = 'data:application/pdf;base64,' + list(db.execute(query, params=[case_id]).merged_blob)[0]

    return blob_data

@app.route("/get_blob_data", methods=['POST', 'GET'])
def get_blob_data():
    data = request.json
    case_id = data['case_id']
    tenant_id = data.pop('tenant_id', None)

    blob_data = get_blob(case_id, tenant_id)

    return jsonify({"flag": True, "data": blob_data})

@app.route("/get_blob_data1", methods=['POST', 'GET'])
@app.route('/get_blob_data1/<case_id>', methods=['POST', 'GET'])
def get_blob_data1(case_id=None):
    data = request.json
    case_id = data['case_id']
    tenant_id = data.pop('tenant_id', None)

    blob_data = get_blob(case_id, tenant_id)

    return jsonify({"flag": True, "data": blob_data})

@app.route("/clear_cache", methods=['POST', 'GET'])
def clear_cache():
    with app.app_context():
        cache.clear()
        
    return "cache cleared"

@cache.memoize(86400)
def get_button_attributes(queue_id, queue_definition, tenant_id):
    db_config = {
        'host': 'queue_db',
        'port': 3306,
        'user': 'root',
        'password': 'root',
        'tenant_id': tenant_id
    }
    db = DB('queues', **db_config)

    query = "SELECT * FROM workflow_definition WHERE queue_id=%s"
    queue_workflow = db.execute(query, params=[queue_id])

    button_ids = list(queue_workflow['button_id'])

    if not button_ids:
        return []

    button_ids_str = ', '.join(str(x) for x in button_ids)
    query = f'SELECT `button_function_mapping`.*, `button_definition`.*, `button_functions`.`route`, `button_functions`.`parameters` FROM `button_function_mapping`, `button_definition`, `button_functions` WHERE `button_function_mapping`.`button_id`=`button_definition`.`id` AND `button_function_mapping`.`function_id`=`button_functions`.`id` AND `button_id` in ({button_ids_str})'
    buttons_df = db.execute(query)
    button_attributes = buttons_df.to_dict(orient='records')

    final_dict = {}
    final_button_list = []
    for ele in button_attributes:
        # ele.pop('button_id')
        # ele.pop('function_id')
        route = ele.pop('route')
        parameters = ele.pop('parameters')

        if ele['text'] in final_dict:
            # final_dict.update(ele)
            final_dict[ele['text']]['functions'].append({
                'route': route,
                'parameters': parameters.split(',')
            })
        else:
            ele['functions'] = [{
                'route': route,
                'parameters': parameters.split(',')
            }]
            final_dict[ele['text']] = ele

    for key, value in final_dict.items():
        final_button_list.append(value)

    button_attributes = final_button_list

    for button in button_attributes:
        # button['parameters'] = button['parameters'].split(',')
        workflow_button = queue_workflow.loc[queue_workflow['button_id'] == button['button_id']]
        button_rule_group = list(workflow_button['rule_group'])[0]
        button_move_to = list(workflow_button['move_to'])[0]

        if button_rule_group is not None:
            button['stage'] = button_rule_group.split(',')
        if button_move_to is not None:
            button['move_to'] = list(queue_definition.loc[[button_move_to]]['unique_name'])[0]

    return button_attributes

@cache.memoize(86400)
def queue_name_type(queue_id, tenant_id):
    db_config = {
        'host': 'queue_db',
        'port': 3306,
        'user': 'root',
        'password': 'root',
        'tenant_id': tenant_id
    }
    db = DB('queues', **db_config)

    # Get queue name using queue ID
    qid_st = time()
    queue_definition = db.get_all('queue_definition')
    queue_df = queue_definition.loc[queue_id]

    queue_name = queue_df['name']
    queue_uid = queue_df['unique_name']
    queue_type = queue_df['type']
    logging.info(f'Queue name: {queue_name}')
    logging.info(f'Queue UID: {queue_uid}')
    logging.debug(f'Time taken for fetching q name {time()-qid_st}')

    return queue_uid, queue_name, queue_type, queue_definition

@cache.memoize(86400)
def get_columns(queue_id, queue_name, tenant_id):
    logging.debug('Getting columns (cache)')
    logging.debug(f'Queue ID: {queue_id}')
    logging.debug(f'Queue Name: {queue_name}')
    logging.debug(f'Tenant ID: {tenant_id}')

    db_config = {
        'host': 'queue_db',
        'port': 3306,
        'user': 'root',
        'password': 'root',
        'tenant_id': tenant_id
    }
    db = DB('queues', **db_config)

    # * COLUMNS
    logging.info(f'Getting column details for `{queue_name}`...')
    query = "SELECT id, column_id from queue_column_mapping where queue_id = %s ORDER BY column_order ASC"
    queue_column_ids = list(db.execute(query, params=[queue_id]).column_id) 

    # Get columns using column ID and above result from column configuration table
    columns_time = time()
    columns_definition = db.get_all('column_definition')
    columns_df = columns_definition.ix[queue_column_ids]

    extraction_columns_df = columns_df.loc[columns_df['source'] != 'process_queue']
    logging.debug(f'Columns DF: {columns_df}')
    columns = list(columns_df.loc[columns_df['source'] == 'process_queue']['column_name'])
    logging.debug(f'Columns: {columns}')
    logging.debug(f'Time taken for columns in q {time()-columns_time}')

    util_columns = ['total_processes', 'completed_processes', 'case_lock', 'failure_status']
    logging.debug(f'Appending utility columns {util_columns}')
    columns += util_columns
    logging.debug(f'Columns after appending utility columns: {columns}')

    extraction_columns_list = list(extraction_columns_df['column_name'])

    return_data = {
        'columns': columns,
        'util_columns': util_columns,
        'extraction_columns_df': extraction_columns_df,
        'extraction_columns_list': extraction_columns_list,
        'columns_df': columns_df
    }

    return return_data

@cache.memoize(86400)
def get_fields_tab_queue(queue_id, tenant_id):

    db_config = {
        'host': 'queue_db',
        'port': 3306,
        'user': 'root',
        'password': 'root',
        'tenant_id': tenant_id
    }
    db = DB('queues', **db_config)

    extraction_db_config = {
        'host': 'extraction_db',
        'port': 3306,
        'user': 'root',
        'password': 'root',
        'tenant_id': tenant_id
    }
    extraction_db = DB('extraction', **extraction_db_config)
    query = f"SELECT * FROM field_definition WHERE FIND_IN_SET({queue_id},queue_field_mapping) > 0"
    fields_df = db.execute(query)
    tab_definition = db.get_all('tab_definition')
    # Replace tab_id in fields with the actual tab names
    # Also create unique name for the buttons by combining display name
    # and tab name
    datasrc_time = time()
    excel_display_data = {}
    tab_type_mapping = {}

    logging.debug('Formatting field info...')
    for index, row in fields_df.iterrows():
        logging.debug(f' => {row}')
        tab_id = row['tab_id']
        tab_name = tab_definition.loc[tab_id]['text']
        tab_source = tab_definition.loc[tab_id]['source']
        tab_type = tab_definition.loc[tab_id]['type']
        fields_df.loc[index, 'tab_id'] = tab_name

        tab_type_mapping[tab_name] = tab_type

        if tab_type == 'excel':
            source_table_name = tab_source + '_source'

            # Get excel source data and convert it to dictionary
            excel_source_data = extraction_db.get_all(source_table_name)

            if tab_name not in excel_display_data:
                excel_display_data[tab_name] = {
                    'column': list(excel_source_data),
                    'data': excel_source_data.to_dict(orient='records')[:100]
                }
    logging.debug(f'Time taken for formatting field {time()-datasrc_time}')
    field_attributes = fields_df.to_dict(orient='records')
    tabs = list(fields_df.tab_id.unique())
    tabs_def_list = list(tab_definition['text'])
    tabs_reordered = []

    for tab in tabs_def_list:
        if tab in tabs:
            tabs_reordered.append(tab)

    return field_attributes, tabs_reordered, excel_display_data, tab_type_mapping

def recon_get_columns(table_unique_id, tenant_id):

    db_config = {
                'host': os.environ['HOST_IP'],
                'port': 3306,
                'user': 'root',
                'password': 'AlgoTeam123',
                'tenant_id': tenant_id
            }
    db = DB('queues', **db_config)

    # * COLUMNS
#    logging.info(f'Getting column details for `{queue_name}`...')
    # query = "SELECT id, column_id from recon_column_mapping where table_unique_id = %s ORDER BY column_order ASC"
    # table_column_ids = list(db.execute(query, params=[table_unique_id]).column_id) 

    # Get columns using column ID and above result from column configuration table
#    columns_time = time()
    query = f"SELECT `column_definition`.*, `recon_column_mapping`.`column_order` FROM `column_definition`, `recon_column_mapping` where `column_definition`.`id` = `recon_column_mapping`.`column_id` and `recon_column_mapping`.`table_unique_id` = %s ORDER BY `recon_column_mapping`.`column_order` ASC"
    columns_df = db.execute_(query, params=[table_unique_id])
    # columns_df = columns_definition_df[columns_definition_df['id'].isin(table_column_ids)]

    extraction_columns_df = columns_df.loc[columns_df['source'] != 'process_queue']
#    logging.debug(f'Columns DF: {columns_df}')
    columns = list(columns_df['column_name'])
#    logging.debug(f'Columns: {columns}')
#    logging.debug(f'Time taken for columns in q {time()-columns_time}')

#    util_columns = ['total_processes', 'completed_processes', 'case_lock', 'failure_status']
#    logging.debug(f'Appending utility columns {util_columns}')
#    columns += util_columns
#    logging.debug(f'Columns after appending utility columns: {columns}')

    extraction_columns_list = list(extraction_columns_df['column_name'])

    return_data = {
        'columns': columns,
        # 'util_columns': util_columns,
        'extraction_columns_df': extraction_columns_df.to_dict(orient= 'records'),
        'extraction_columns_list': extraction_columns_list,
        'columns_df': columns_df
    }

    return return_data

def get_recon_data(queue_id, queue_name, tenant_id):
    db_config = {
                'host': os.environ['HOST_IP'],
                'port': 3306,
                'user': 'root',
                'password': 'AlgoTeam123',
                'tenant_id': tenant_id
                }
    db = DB('queues', **db_config)
    
    # queue_id = '49'
    query = f"SELECT * FROM `recon_table_mapping` where `queue_id` = '{queue_id}'"
    recon_table_mapping_df = db.execute(query)
    
    table_unique_ids_mapped = list(recon_table_mapping_df['table_unique_id'])
    table_unique_ids_mapped = ["'" +x+ "'" for x in table_unique_ids_mapped]
    in_clause = ','.join(table_unique_ids_mapped)
    

    query_1 = f"SELECT * FROM `recon_definition` where `table_unique_id` in (SELECT `table_unique_id` FROM `recon_table_mapping` where `queue_id` = '{queue_id}')"
    recon_definition_df = db.execute(query_1)
    
    if len(recon_definition_df) > 2:
        return {'flag' : 'False', 'msg' : 'Too many queues mapped in DB.'}
    to_return = {}
    keys_ = {}  #for the UI to know which is primary and secondary table
    for _, row in recon_definition_df.iterrows():
        table_column_mapping = recon_get_columns(row['table_unique_id'], 'karvy')
        
        if row['dependency']:
            keys_['primary_table'] = row['table_unique_id']
        else:
            keys_['secondary_table'] = row['table_unique_id']
        
        if len(recon_definition_df) == 1:
            keys_['primary_table'] = row['table_unique_id']
            
        dd = table_column_mapping['columns_df'].to_dict(orient='list')
        final ={}
        to_map = []
        logging.debug(f'DD: {dd}')

        for key, value in dd.items():
            to_map.append(value)

        logging.debug(f'To Map: {to_map}')
        column_mapping = {}
        print("********************to_map" , to_map)
        for i in range(len(to_map[0])):
            column_mapping[to_map[2][i]] = to_map[1][i] 
        logging.debug(f'Column Mapping: {column_mapping}') 
        #Check if unique id is in columns extracted from recon_get_columns
        to_return[row['table_unique_id']] = { 
                'route' : row['route'],
                'parameters' : row['parameters'],
                'show_table' : row['show_table'],
                'unique_key' : row['unique_key'],
                'match_id_field': row['match_id_field'],
                'match_table' : row['match_table'],
                'dependency' : row['dependency'] if row['dependency'] else '',
                'columns' : table_column_mapping['columns'],
                'columns_df' : table_column_mapping['columns_df'].to_dict(orient= 'records'),
                'column_mapping': column_mapping,
                'column_order': list(column_mapping.keys()),
                'queue_table_name' : row['queue_table_name'] if row['queue_table_name'] else '',
                'check_box' : row['check_box']
                }
    to_return  = {**to_return, **keys_}
    #Add button_attributes_key
    return to_return

@app.route('/get_recon_secondary_table', methods = ['GET', 'POST'])
def get_recon_secondary_table():
    data = request.json
    tenant_id = data['tenant_id']
    db_config = {
                'host': os.environ['HOST_IP'],
                'port': 3306,
                'user': 'root',
                'password': 'AlgoTeam123',
                'tenant_id': tenant_id
                }
    unique_key = data['unique_key']
    primary_unique_key_value = data['primary_unique_key_value']
    primary_table_unique_key = data['primary_table_unique_key']
    primary_queue_table_name = data['primary_queue_table_name']
    columns_df = data['columns_df']
    columns = data['columns']
    queue_id = data['queue_id'] #Need UI to send this 
    queue_db = DB('queues', **db_config)
    extraction_db = DB('extraction', **db_config)
    # query = f"SELECT `unique_name` FROM `queue_definition` where `id` = '{queue_id}'"
    # print(query)
    # queue_unique_name = queue_db.execute_(query)
    # print(queue_unique_name)
    # queue_unique_name  = list(queue_unique_name['unique_name'])[0]
    # invoice_files_df = extraction_db.execute_(f"SELECT * from `{queue_table_name}` where `queue`= '{queue_unique_name}'")
    # # files = invoice_files_df[columns].to_dict(orient='records')
    # case_ids = list(invoice_files_df[unique_key].unique())
    extraction_columns_df = pd.DataFrame(columns_df)
    # extraction_columns_df = columns_df[columns_df['source'] != 'process_queue']
    # print("case_id ",case_ids)
    # if case_ids:    
    #     placeholders = ','.join(['%s'] * len(case_ids))
    if not extraction_columns_df.empty:
        select_columns_list = []
        for index, row in extraction_columns_df.iterrows():
            col_name = row['column_name']                   
            table = row['source']
        
            if table:
                select_columns_list.append(f'`{table}`.`{col_name}`')
        
        tables_list = [source for source in list(extraction_columns_df['source'].unique()) if source]
        print(f'Tables to fetch from: {tables_list}')
        tables_list_ = []
        if primary_queue_table_name not in tables_list:
            tables_list_ = tables_list + [primary_queue_table_name]
            print(tables_list_)
        else:
            tables_list_ = tables_list
        where_conditions_list = []
        for combo in combinations(tables_list_, 2):
            where_conditions_list.append(f'`{combo[0]}`.`{primary_table_unique_key}` = `{combo[1]}`.`{primary_table_unique_key}`')

        # select_columns_list += ['`ocr`.`id`', '`ocr`.`case_id`']
        where_conditions_list += [f"`{tables_list[0]}`.`{primary_table_unique_key}` IN ('{primary_unique_key_value}')"]

        select_part = ', '.join(select_columns_list)
        from_part = ', '.join([f'`{table}`' for table in tables_list_])
        where_part = ' AND '.join(where_conditions_list)
        
        
        query = f'SELECT {select_part} FROM {from_part} WHERE {where_part}'
        print('query is ',query)
        query_result_df = extraction_db.execute_(query)
        try:
            query_result_list = query_result_df.to_dict('records')
        except:
            pass
        print(f'Extraction data: {query_result_list}')
        
        rows_arr = []
        for idx, row in query_result_df.iterrows():
            rows_dict = {}
            for col in columns:
                rows_dict = {**rows_dict, **{col : row[col]}}
            rows_arr.append(rows_dict)
        return jsonify({'columns' : columns,'rows' : rows_arr})
    else:
        sample = {"columns":["case_id","operator"],"rows":[{"case_id":"2000443305","operator":"ab"},{"case_id":"2000443312","operator":"abc"},{"case_id":"2000443320","operator":"a"},{"case_id":"2000443334","operator":"ab"},{"case_id":"2000443344","operator":"123"},{"case_id":"2000443415","operator":"abc"}]}  
        return jsonify("No data to display")

@app.route('/get_recon_table_data', methods = ['GET', 'POST'])
def get_recon_table_data():
    data = request.json
    tenant_id = data['tenant_id']
    db_config = {
                'host': os.environ['HOST_IP'],
                'port': 3306,
                'user': 'root',
                'password': 'AlgoTeam123',
                'tenant_id': tenant_id
                }
    unique_key = data['unique_key']
    queue_table_name = data['queue_table_name']
    columns_df = data['columns_df']
    columns = data['columns']
    queue_id = data['queue_id'] #Need UI to send this 
    queue_db = DB('queues', **db_config)
    extraction_db = DB('extraction', **db_config)
    query = f"SELECT `unique_name` FROM `queue_definition` where `id` = '{queue_id}'"
    print(query)
    queue_unique_name = queue_db.execute_(query)
    print(queue_unique_name)
    queue_unique_name  = list(queue_unique_name['unique_name'])[0]
    invoice_files_df = extraction_db.execute_(f"SELECT * from `{queue_table_name}` where `queue`= '{queue_unique_name}'")
    # files = invoice_files_df[columns].to_dict(orient='records')
    case_ids = list(invoice_files_df[unique_key].unique())
    extraction_columns_df = pd.DataFrame(columns_df)
    # extraction_columns_df = columns_df[columns_df['source'] != 'process_queue']
    print("case_id ",case_ids)
    if case_ids:    
        placeholders = ','.join(['%s'] * len(case_ids))
        if not extraction_columns_df.empty:
            select_columns_list = []
            for index, row in extraction_columns_df.iterrows():
                col_name = row['column_name']                   
                table = row['source']
            
                if table:
                    select_columns_list.append(f'`{table}`.`{col_name}`')
            
            tables_list = [source for source in list(extraction_columns_df['source'].unique()) if source]
            print(f'Tables to fetch from: {tables_list}')
            tables_list_ = []
            if queue_table_name not in tables_list:
                tables_list_ = tables_list + [queue_table_name]
                print(tables_list_)
            else:
                tables_list_ = tables_list
            where_conditions_list = []
            for combo in combinations(tables_list_, 2):
                where_conditions_list.append(f'`{combo[0]}`.`{unique_key}` = `{combo[1]}`.`{unique_key}`')

            # select_columns_list += ['`ocr`.`id`', '`ocr`.`case_id`']
            where_conditions_list += [f'`{queue_table_name}`.`{unique_key}` IN ({placeholders})']
        
            select_part = ', '.join(select_columns_list)
            from_part = ', '.join([f'`{table}`' for table in tables_list_])
            where_part = ' AND '.join(where_conditions_list)


            query = f'SELECT {select_part} FROM {from_part} WHERE {where_part}'
            print('query is ',query)
            query_result_df = extraction_db.execute_(query, params=case_ids)
            query_result_list = query_result_df.to_dict('records')
            print(f'Extraction data: {query_result_list}')
            
            rows_arr = []
            for idx, row in query_result_df.iterrows():
                rows_dict = {}
                for col in columns:
                    rows_dict = {**rows_dict, **{col : row[col]}}
                rows_arr.append(rows_dict)
            return jsonify({'columns' : columns,'rows' : rows_arr})
    else:
        sample = {"columns":["case_id","operator"],"rows":[{"case_id":"2000443305","operator":"ab"},{"case_id":"2000443312","operator":"abc"},{"case_id":"2000443320","operator":"a"},{"case_id":"2000443334","operator":"ab"},{"case_id":"2000443344","operator":"123"},{"case_id":"2000443415","operator":"abc"}]}  
        return jsonify("No data to display")

@app.route('/get_queue', methods=['POST', 'GET'])
@app.route('/get_queue/<queue_id>', methods=['POST', 'GET'])
def get_queue(queue_id=None):
    with zipkin_span(service_name='button_functions', span_name='execute_button_function', 
            transport_handler=http_transport, port=5007, sample_rate=0.5,) as zipkin_context:
        try:
            rt_time = time()
            data = request.json
            
            logging.info(f'Request data: {data}')
            logging.info(f'Queue ID: {queue_id}')
            
            operator = data.get('user', None)
            tenant_id = data.get('tenant_id', '')
            
            zipkin_context.update_binary_annotations({'Tenant':tenant_id})

            try:
                start_point = data['start'] - 1
                end_point = data['end']
                offset = end_point - start_point
            except:
                start_point = 0
                end_point = 20
                offset = 20

            logging.debug(f'Start point: {start_point}')
            logging.debug(f'End point: {end_point}')
            logging.debug(f'Offset: {offset}')

            if queue_id is None:
                message = f'Queue ID not provided.'
                logging.error(message)
                return jsonify({'flag': False, 'message': message})

            try:
                queue_id = int(queue_id)
            except ValueError:
                message = f'Invalid queue. Expected queue ID to be integer. Got {queue_id}.'
                logging.exception(message)
                return jsonify({'flag': False, 'message': message})

            db_config = {
                'host': os.environ['HOST_IP'],
                'port': 3306,
                'user': 'root',
                'password': 'AlgoTeam123',
                'tenant_id': tenant_id
            }
            db = DB('queues', **db_config)

            # user_db_config = {
            #     'host': os.environ['HOST_IP'],
            #     'user': 'root',
            #     'password': 'AlgoTeam123',
            #     'port': '3306',
            #     'tenant_id':tenant_id
            # }
            # user_db = DB('authentication', **user_db_config)

            extraction_db_config = {
                'host': 'extraction_db',
                'port': 3306,
                'user': 'root',
                'password': 'AlgoTeam123',
                'tenant_id': tenant_id
            }
            extraction_db = DB('extraction', **extraction_db_config)

            if operator is not None:
                oper_st = time()
                update_operator_q = "UPDATE `process_queue` SET `operator`=%s WHERE `operator`=%s"
                db.execute(update_operator_q,params=[None,operator])
                logging.debug(f'Time taken for operator update: {time()-oper_st}')

            try:
                queue_uid, queue_name, queue_type, queue_definition = queue_name_type(queue_id, tenant_id)
            except:
                message = 'Some column ID not found in column definition table.'
                logging.exception(message)
                return jsonify({'flag': False, 'message': message})

            if queue_type == 'train':
                logging.info(f' > Redirecting to `get_template_exception` route.')

                response = get_template_exceptions(db, {'start': start_point, 'end': end_point})

                # user_db.engine.close()
                extraction_db.engine.close()

                logging.info(f'Response: {response}')
                return jsonify(response)
            elif queue_type == 'reports':
                logging.info(f' > Redirecting to `get_reports_queue` route.')

                host = 'reportsapi'
                port = 80
                route = 'get_reports_queue'
                response = requests.post(f'http://{host}:{port}/{route}', json=data)
                response_data = response.json()

                return jsonify(response_data)

            elif queue_type == 'snapshot':
                logging.info(f' > Redirecting to `get_snapshot` route.')

                response_data = get_snapshot(db, {'start': start_point, 'end': end_point})

                return jsonify(response_data)
            
            elif queue_type == 'recon':
                logging.info(f' > Redirecting to `/get_recon` route.')
                response_data = get_recon_data(queue_id, queue_name, tenant_id)
                button_time = time()
                logging.info(f'Getting button details for `{queue_name}`...')
                button_attributes = get_button_attributes(queue_id, queue_definition, tenant_id)
                logging.debug(f'Time taken for button functions {time()-button_time}')
                response_data['buttons'] = button_attributes
                
                return jsonify({'data':response_data, 'flag' : True})
            # Get data related to the queue name from OCR table
            all_st = time()
            invoice_files_df = db.execute("SELECT * from `process_queue` where `queue`= %s ORDER by `failure_status` desc, `created_date` desc LIMIT %s, %s", params=[queue_uid, start_point, offset])
            total_files = list(db.execute("SELECT id, COUNT(DISTINCT `case_id`) FROM `process_queue` WHERE `queue`= %s", params=[queue_uid])['COUNT(DISTINCT `case_id`)'])[0]
            logging.debug(f'Loading process queue {time()-all_st}')
            case_ids = list(invoice_files_df['case_id'].unique())
            logging.debug(f'Case IDs: {case_ids}')

            
            try:
                columns_data = get_columns(queue_id, queue_name, tenant_id)
                columns = columns_data['columns']
                util_columns = columns_data['util_columns']
                extraction_columns_df = columns_data['extraction_columns_df']
                extraction_columns_list = columns_data['extraction_columns_list']
                columns_df = columns_data['columns_df']
                
                logging.debug(f'Extraction Columns: {extraction_columns_df}')
            except:
                message = 'Some column ID not found in column definition table.'
                logging.exception(message)
                return jsonify({'flag': False, 'message': message})
            
            queue_files = invoice_files_df
            logging.debug(f'Queue Files: {queue_files}')
            files = queue_files[columns].to_dict(orient='records')
            logging.debug(f'Files info: {files}')

            if queue_type != 'formqueue':
                if case_ids:
                    placeholders = ','.join(['%s'] * len(case_ids))

                    select_columns_list = []
                    for index, row in extraction_columns_df.iterrows():
                        col_name = row['column_name']                   
                        table = row['source']

                        if table:
                            select_columns_list.append(f'`{table}`.`{col_name}`')

                    tables_list = [source for source in list(extraction_columns_df['source'].unique()) if source]
                    logging.debug(f'Tables to fetch from: {tables_list}')

                    where_conditions_list = []
                    for combo in combinations(tables_list, 2):
                        where_conditions_list.append(f'`{combo[0]}`.`case_id` = `{combo[1]}`.`case_id`')
                    
                    select_columns_list += ['`ocr`.`id`', '`ocr`.`case_id`']
                    where_conditions_list += [f'`ocr`.`case_id` IN ({placeholders})']

                    select_part = ', '.join(select_columns_list)
                    from_part = ', '.join([f'`{table}`' for table in tables_list])
                    where_part = ' AND '.join(where_conditions_list)

                    logging.debug(f'Select part: {select_part}')
                    logging.debug(f'From part: {from_part}')
                    logging.debug(f'Where part: {where_part}')

                    
                    # query = f'SELECT `business_rule`.`id`, `business_rule`.`case_id`, `business_rule`.`Verify Operator`, `ocr`.`Vendor Name` FROM `business_rule`, `ocr` WHERE `business_rule`.`case_id`=`ocr`.`case_id` AND `business_rule`.`case_id` in ({placeholders})'
                    query = f'SELECT {select_part} FROM {from_part} WHERE {where_part}'
                    
                    query_result = extraction_db.execute(query, params=case_ids)
                    query_result_list = query_result.to_dict('records')
                    logging.debug(f'Extraction data: {query_result_list}')
                

                    for document in files:
                        try:
                            document['created_date'] = (document['created_date']).strftime(r'%B %d, %Y %I:%M %p')
                        except:
                            logging.debug(f'Could not parse created date value. `created_date` might not be mapped for the queue `{queue_name}`.')
                            pass
                        
                        try:
                            percentage_done = str(int((document['completed_processes']/document['total_processes'])*100))
                        except:
                            percentage_done = '0'
                        if int(percentage_done) > 100:
                            percentage_done = '100'
                            
                        try:
                            if document['status']:
                                document['status'] = {
                                    'percent_done': percentage_done,
                                    'current_status':document['status'],
                                    'case_lock':document['case_lock'],
                                    'failure_status':document['failure_status']
                                }
                            else:
                                document['status'] = None
                        except:
                            pass

                        for row in query_result_list:
                            row_case_id = row['case_id']
                            logging.debug(f'Row Case: {row_case_id}')
                            for col, val in row.items():
                                doc_case = document['case_id']
                                logging.debug(f'Doc Case: {doc_case}')
                                if row_case_id == doc_case:
                                    logging.debug(f'Case matched!\n')
                                    document[col] = val
                                    continue

                columns = [col for col in columns if col not in util_columns]
                columns += extraction_columns_list
                logging.debug(f'New columns: {columns}')

                
                dd = columns_df.to_dict(orient='list')
                final ={}
                to_map = []
                logging.debug(f'DD: {dd}')

                for key, value in dd.items():
                    to_map.append(value)

                logging.debug(f'To Map: {to_map}')
                column_mapping = {}
                for i in range(len(to_map[0])):
                    column_mapping[to_map[1][i]] = to_map[0][i] 
                logging.debug(f'Column Mapping: {column_mapping}')
            else:
                column_mapping = {}
            # * RENAME COLUMNS
            # logging.debug(f'Before Renaming Columns: {columns}')
            # temp_columns = columns.copy()
            # for index, column in enumerate(temp_columns):
            #     col_info = columns_df.loc[columns_df['column_name'] == column]
            #     logging.debug(f'Column: {column}')
            #     logging.debug(f'Column Info: {col_info}')
            #     if not col_info.empty:
            #         columns[index] = list(col_info['label_key'])[0]
            # logging.debug(f'After Renaming Columns: {columns}')

            # logging.debug(f'Before Renaming Files: {files}')
            # for file_ in files:
            #     for col in list(columns_df['column_name']):
            #         if col in file_:
            #             new_col_name = list(columns_df.loc[columns_df['column_name'] == col]['label_key'])[0]
            #             file_[new_col_name] = file_.pop(col)
            # logging.debug(f'After Renaming Files: {files}')

            # * BUTTONS
            button_time = time()
            logging.info(f'Getting button details for `{queue_name}`...')
            button_attributes = get_button_attributes(queue_id, queue_definition, tenant_id)
            logging.debug(f'Time taken for button functions {time()-button_time}')
        
            # * FIELDS
            logging.info(f'Getting fields details for `{queue_name}`...')
            fieldid_time = time()
            field_attributes, tabs, excel_display_data, tab_type_mapping = get_fields_tab_queue(queue_id, tenant_id)
            logging.debug(f'Time taken for fetching fields ids {time()-fieldid_time}')
            
            if end_point > total_files:
                end_point = total_files

            pagination = {"start": start_point + 1, "end": end_point, "total": total_files}

            # query = "SELECT id,username from users where role = 'TL_Prod'"
            # retrain_access = operator in list(user_db.execute(query).username)

            # if queue_name == 'Verify' and retrain_access:
            #     retrain = 1
            # else:
            #     retrain = 0

            db.engine.close()
            # user_db.engine.close()
            extraction_db.engine.close()

            db.db_.dispose()
            # user_db.db_.dispose()
            extraction_db.db_.dispose()
            
            data = {
                'files': files,
                'buttons': button_attributes,
                'field': field_attributes,
                'tabs': tabs,
                'excel_source_data': excel_display_data,
                'tab_type_mapping': tab_type_mapping,
                'pagination': pagination,
                # 'retrain': retrain,
                'column_mapping': column_mapping,
                'column_order': list(column_mapping.keys()),
                'pdf_type': 'folder' if tenant_id else 'blob'
            }
            logging.debug(f'Total time taken to get `{queue_name}` {time()-rt_time}')

            response = {'flag': True, 'data': data}
            logging.info(f'Response: {response}')
            return jsonify(response)
        except:
            logging.exception('Something went wrong while getting queues. Check trace.')
            response = {'flag': False, 'message':'System error! Please contact your system administrator.'}
            return jsonify(response)

@app.route('/get_display_fields/<case_id>', methods=['POST', 'GET'])
def get_display_fields(case_id=None):
    # ! MAKE THIS ROUTE AFTER THE PREVIOUS ROUTE IS STABLE
    try:
        data = request.json
        
        logging.info(f'Request data: {data}')
        queue_id = data.pop('queue_id', None)

        if queue_id is None:
            message = f'Queue ID not provided.'
            logging.error(message)
            return jsonify({'flag': False, 'message': message})

        if case_id is None:
            message = f'Case ID not provided.'
            logging.error(message)
            return jsonify({'flag': False, 'message': message})

        db_config = {
            'host': 'queue_db',
            'port': 3306,
            'user': 'root',
            'password': 'root',
            'tenant_id': tenant_id
        }
        db = DB('queues', **db_config)
        # db = DB('queues')

        # Get queue name using queue ID
        queue_definition = db.get_all('queue_definition')

        # * BUTTONS
        logging.info('Getting button data...')

        logging.debug(f'Fetching workflow for queue `{queue_id}`')
        # Get workflow definition for the selected queue ID
        workflow_definition = db.get_all('workflow_definition')
        queue_workflow = workflow_definition.loc[workflow_definition['queue_id'] == queue_id]

        logging.debug(f'Fetching button IDs for queue `{queue_id}`')
        # Get button IDs for the queue ID
        button_ids = list(queue_workflow['button_id'])

        logging.debug(f'Fetching button attributes for queue `{queue_id}`')
        # Get buttons' attributes from button definition
        button_definition = db.get_all('button_definition')
        buttons_df = button_definition.ix[button_ids]
        button_attributes = buttons_df.to_dict(orient='records')

        logging.debug(f'Converting button IDs to button name in workflow')
        # Add which queue to move to in button attributes
        raw_move_to_ids = list(queue_workflow['move_to'])
        move_to_ids = [id if id is not None else -1 for id in raw_move_to_ids]
        move_to_df = queue_definition.ix[move_to_ids]
        move_to = list(move_to_df['unique_name'])
        for index, button in enumerate(button_attributes):
            if move_to[index] != -1:
                button['move_to'] = move_to[index]

        logging.debug(f'Fetching button functions and mappings for queue `{queue_id}`')
        # Get button functions
        button_functions_df = db.get_all('button_functions')
        button_function_mapping = db.get_all('button_function_mapping')
        button_id_function_mapping = button_function_mapping.loc[button_function_mapping['button_id'].isin(button_ids)]
        # TODO: Convert this loop into a function. Using it later again for tab_id
        for index, row in button_id_function_mapping.iterrows():
            button_id = row['button_id']
            button_name = button_definition.loc[button_id]['text']
            button_id_function_mapping.loc[index, 'button_id'] = button_name

        for button in button_attributes:
            button_name = button['text']
            button_function_id_df = button_id_function_mapping.loc[button_id_function_mapping['button_id'] == button_name]
            button_function_id = list(button_function_id_df['function_id'])
            button['functions'] = []
            # Add all functions
            for function_id in button_function_id:
                function_id_df = button_functions_df.loc[function_id]
                function = function_id_df.to_dict()
                function['parameters'] = function['parameters'].split(',') # Send list of parameters instead of string
                button['functions'].append(function)

        buttons = list(buttons_df['text'])

        # * FIELDS
        logging.info(f'Getting field data...')

        logging.debug(f'Fetching queue field maping for queue `{queue_id}`')
        # Get field IDs for the queue field mapping
        query = f"SELECT id FROM field_definition WHERE FIND_IN_SET({queue_id},queue_field_mapping) > 0"
        field_ids = list(db.execute_(query).id)

        logging.debug(f'Fetching field defintion for queue `{queue_id}`')
        # Get field definition corresponding the field IDs
        field_definition = db.get_all('field_definition')
        fields_df = field_definition.ix[field_ids]
        fields_df['unique_name'] = Series('', index=fields_df.index)

        logging.debug(f'Fetching tab defintion for queue `{queue_id}`')
        # Get tab definition
        tab_definition = db.get_all('tab_definition')

        # Replace tab_id in fields with the actual tab names
        # Also create unique name for the buttons by combining display name
        # and tab name
        logging.debug(f'Renaming tab ID to tab name')
        for index, row in fields_df.iterrows():
            logging.debug(f' => {row}')
            tab_id = row['tab_id']
            tab_name = tab_definition.loc[tab_id]['text']
            fields_df.loc[index, 'tab_id'] = tab_name

            formate_display_name = row['display_name'].lower().replace(' ', '_')
            unique_name = f'{formate_display_name}_{tab_name.lower()}'.replace(' ', '_')
            fields_df.loc[index, 'unique_name'] = unique_name

        field_attributes = fields_df.to_dict(orient='records')
        fields = list(fields_df.display_name.unique())
        tabs = list(fields_df.tab_id.unique())

        response_data = {
            'buttons': button_attributes,
            'field': field_attributes,
            'tabs': tabs
        }

        response = {'flag': True, 'data': response_data}
        logging.info(f'Response: {response}')
        return jsonify(response)
    except Exception as e:
        logging.exception('Something went wrong while getting display fields. Check trace.')        
        return jsonify({'flag': False, 'message':'System error! Please contact your system administrator.'})

@app.route('/get_fields', methods=['POST', 'GET'])
@app.route('/get_fields/<case_id>', methods=['POST', 'GET'])
def get_fields(case_id=None):
    try:
        st_time = time()
        data = request.json

        logging.info(f'Request data: {data}')
        operator = data.pop('user', None)
        tenant_id = data.pop('tenant_id', None)

        if operator is None:
            message = f'Operator name not provided.'
            logging.error(message)
            return jsonify({'flag': False, 'message': message})

        if case_id is None:
            message = f'Case ID not provided.'
            logging.error(message)
            return jsonify({'flag': False, 'message': message})


        queue_db_config = {
            'host': 'queue_db',
            'port': 3306,
            'user': 'root',
            'password': 'root',
            'tenant_id': tenant_id
        }
        queue_db = DB('queues', **queue_db_config)
        # queue_db = DB('queues')

        logging.debug(f'Getting ID and operator from process queue for case `{case_id}`')
        query = "SELECT id, operator from process_queue where case_id = %s"
        locked_user = list(queue_db.execute(query, params=[case_id]).operator)[0]
        if locked_user == '':
            locked_user = None

        if locked_user != operator and locked_user:
            logging.info(f'Case `{case_id}` is in use by another user')
            return jsonify({'flag': False, 'message': 'File in use by another user'})

        extraction_db_config = {
            'host': 'extraction_db',
            'port': 3306,
            'user': 'root',
            'password': 'root',
            'tenant_id': tenant_id
        }
        extraction_db = DB('extraction', **extraction_db_config)
        # extraction_db = DB('extraction')

        template_db_config = {
            'host': 'template_db',
            'port': 3306,
            'user': 'root',
            'password': 'root',
            'tenant_id': tenant_id
        }
        template_db = DB('template_db', **template_db_config)

        template_list = sorted(list(template_db.get_all('trained_info').template_name))

        # Get tab definition
        tab_definition = queue_db.get_all('tab_definition')

        logging.debug(f'Getting OCR data')
        # Get queue ID using exception type from case files in process_queue table
        qid_st = time()
        try:
            query = 'SELECT * FROM `ocr_info` WHERE `case_id`=%s'
            ocr_data = queue_db.execute(query, params=[case_id])
            ocr_data = list(ocr_data['ocr_data'])[0]
        except Exception as e:
            ocr_data = '[[]]'
            logging.exception('Error in extracting ocr from db')
            pass

        logging.debug(f'Getting all data from process queue for case `{case_id}`')
        query = 'SELECT * FROM `process_queue` WHERE `case_id`=%s'
        case_files = queue_db.execute(query, params=[case_id])

        if case_files.empty:
            message = f'No case ID `{case_id}` found in process queue.'
            logging.error(message)
            return jsonify({'flag': False, 'message': message})
        else:
            file_name = list(case_files.file_name)[0]
            if list(case_files.queue)[0] == 'Failed':
                message = 'Just display the image'
                return jsonify({'flag': True, 'message': message, 'corrupted': True, 'file_name':file_name})

        case_operator = list(case_files.operator)[0]
        
        if case_operator is not None and case_operator != operator:
            message = f'This file/cluster is in use by the user `{case_operator}`.'
            logging.error(message)
            return jsonify({'flag': False, 'message': message})

        queue_name = list(case_files['queue'])[0]
        queue_definition = queue_db.get_all('queue_definition')
        queue_info = queue_definition.loc[queue_definition['unique_name'] == queue_name]
        print("queue_name", queue_name)
        queue_id = queue_definition.index[queue_definition['unique_name'] == queue_name].tolist()[0]
        logging.debug(f'Time taken for getting qid basis exception type {time()-qid_st}')

        logging.debug(f'Getting queue field mapping info for case `{case_id}`')
        # Get field related to case ID from queue_field_mapping
        fields_ids_time = time()
        query = f"SELECT id FROM field_definition WHERE FIND_IN_SET({queue_id},queue_field_mapping) > 0"
        field_ids = list(queue_db.execute_(query).id)
        print("field list ids", field_ids)
        logging.debug(f'Time taken for getting fields ids {time()-fields_ids_time}')

        # Get dropdown values using field IDs which have dropdown values dropdown_definition
        dropdown_time = time()
        dropdown_definition = queue_db.get_all('dropdown_definition')
        field_dropdown = dropdown_definition.loc[dropdown_definition['field_id'].isin(field_ids)] # Filter using only field IDs from the file
        unique_field_ids = list(field_dropdown.field_id.unique()) # Get unique field IDs from dropdown definition
        field_definition = queue_db.get_all('field_definition')
        dropdown_fields_df = field_definition.ix[unique_field_ids] # Get field names using the unique field IDs
        dropdown_fields_names = list(dropdown_fields_df.unique_name)

        dropdown = {}
        for index, f_id in enumerate(unique_field_ids):
            dropdown_options_df = field_dropdown.loc[field_dropdown['field_id'] == f_id]
            dropdown_options = list(dropdown_options_df.dropdown_option)
            dropdown[dropdown_fields_names[index]] = dropdown_options

        fields_df = field_definition.ix[field_ids] # Get field names using the unique field IDs
        print("Get field names",fields_df)
        logging.debug(f'Getting highlights for case `{case_id}`')
        # Get higlights
        highlight_time = time()
        query = "SELECT * FROM ocr WHERE case_id= %s ORDER BY created_date limit 1"
        case_id_ocr = extraction_db.execute(query, params=[case_id])
        try:
            highlight = json.loads(list(case_id_ocr['highlight'])[0])
        except:
            highlight = {}
        try:
            if 'Table' in list(case_id_ocr.columns):
                table = list(case_id_ocr['Table'])[0]
            else:
                table = '[]'
        except:
            table = '[]'

        # Renaming of fields
        rename_time = time()
        renamed_fields = {}
        renamed_higlight = {}

        field_source_data = {}

        logging.debug(f'Renaming fields for case `{case_id}`')
        logging.debug(f'Fields DF: {fields_df}')
        for index, row in fields_df.to_dict('index').items():
            for_time = time()
            tab_id = row['tab_id']
            tab_name = tab_definition.loc[tab_id]['text']
            table_name = tab_definition.loc[tab_id]['source']
            fields_df.loc[index, 'tab_id'] = tab_name

            display_name = row['display_name']
            unique_name = row['unique_name']

            if unique_name == 'addon_table':
                continue

            # Get data related to the case from table for the corresponding tab
            get_all_time = time()
            query_time = time()

            # Check if such table exists. If not then skip tab
            try:
                if table_name not in field_source_data:
                    get_fieldsinfo_q = f"SELECT * FROM `{table_name}` WHERE case_id=%s"
                    field_source_data[table_name] = extraction_db.execute(get_fieldsinfo_q, params=[case_id])

                tab_files_df = field_source_data[table_name]
                if tab_files_df is False:
                    message = f'No table named `{table_name}`.'
                    logging.warning(message)
                    continue

                case_tab_files = queue_db.get_latest(tab_files_df, 'case_id', 'created_date')

                if case_tab_files.empty:
                    message = f'No such case ID `{case_id}` in `{table_name}`.'
                    logging.warning(message)
                    continue
            except:
                logging.exception('Exception in getting table fields')
                continue

            # case_files_filtered = case_tab_files.loc[:, 'created_date':] # created_date column will be included
            fields_df = case_tab_files.drop(columns='created_date') # Drop created_date column
            table_fields_ = fields_df.to_dict(orient='records')[0] # Get corresponding table fields

            if display_name in table_fields_:
                renamed_fields[unique_name] = table_fields_[display_name]

            if display_name in highlight and table_name == 'ocr':
                renamed_higlight[unique_name] = highlight[display_name]

            timespent = list(case_files.time_spent)[0]
            h, m, s = timespent.split(':')
            timespent_in_secs = (int(h) * 3600) + (int(m) * 60) + int(s)

        logging.debug('Fetching table data')    
        if table != '[]':
            if table:
                table = [ast.literal_eval(table)]
        else:
            table = []

        logging.debug('Fetching failure messages')
        failure_msgs_data = {}
        # query = "SELECT * from `validation` where `case_id` = %s"
        # validation_results = extraction_db.execute(query, params=[case_id])
        # if not validation_results.empty:
        #     validation_results = validation_results.to_dict(orient='records')[0]
            
        #     for field in validation_results:
        #         msg = validation_results[field] 
        #         if  msg and (msg != '1') and (msg != '0'):
        #             failure_msgs_data[field] = msg
        failure_msgs_data.pop('case_id', None)
        failure_msgs_data.pop('highlight', None)
        
        try:
            error_logs_str = list(case_files.error_logs)[0]
        except:
            error_logs_str = ''
        error_logs_list = []
        if error_logs_str:
            if error_logs_str[0] == '|':
                error_logs_str = error_logs_str[1:]
            
            error_logs_list = error_logs_str.split('|')

        failures = {
            'validation_errors': failure_msgs_data,
            'processing_errors': error_logs_list
        }
        
        logging.debug(f'Failures: {failures}')

        response_data = {}
        query = "SELECT id, tab_id, pattern FROM field_definition WHERE unique_name = 'addon_table'"
        try:
            result = queue_db.execute(query)
            pattern = list(result.pattern)
            tab_id = list(result.tab_id)[0]
            query = f"Select id, text from tab_definition where id = {tab_id}"
            addon_column = list(queue_db.execute(query).text)[0]
            if pattern:
                table_pattern = json.loads(pattern[0])
                addon_table = get_addon_table(table_pattern,case_id_ocr)
            else:
                addon_table = {}
        except:
            logging.debug(f'Failed while fetching addon table details. Initializing it to empty dictionary')
            addon_table = {}

        if table:
            response_data['table'] = table
        
        response_data = {
            'flag': True,
            'addon_table': addon_table,
            'addon_tab': addon_column,
            'data': renamed_fields,
            'dropdown_values': dropdown,
            'highlight': renamed_higlight,
            'file_name': list(case_files.file_name)[0],
            'table': table,
            'addon_table' : addon_table,
            'time_spent': 0,
            'timer': list(queue_info.timer)[0],
            'ocr_data': ocr_data,
            'failures':failures,
            'template_name': list(case_files.template_name)[0],
            'template_list': template_list,
            'pdf_type': 'folder' if tenant_id else 'blob'
        }

        logging.info(f'Locking case `{case_id}` by operator `{operator}`')
        # Lock the file and assign it to the operator
        update = {
            'operator': operator
        }
        where = {
            'case_id': case_id
        }
        oper_time = time()
        queue_db.update('process_queue', update=update, where=where)

        # if len(json.dumps(response_data)) > 200:
        #     logging.info(f'Response: {json.dumps(response_data)[:100]}...{json.dumps(response_data)[-100:]}')
        # else:
        #     logging.info(f'Response: {response_data}')
        return jsonify(response_data)

    except Exception as e:
        traceback.print_exc()
        logging.exception('Something went wrong getting fields data. Check trace.')
        return jsonify({'flag': False, 'message':'System error! Please contact your system administrator.'})

@app.route('/refresh_fields', methods=['POST', 'GET'])
def refresh_fields(case_id=None):
    try:
        data = request.json

        logging.info(f'Request data: {data}')
        case_id = data.pop('case_id')
        tenant_id = data.get('tenant_id', None)

        if case_id is None:
            message = f'Case ID not provided.'
            logging.error(message)
            return jsonify({'flag': False, 'message': message})

        queue_db_config = {
            'host': 'queue_db',
            'port': 3306,
            'user': 'root',
            'password': 'root',
            'tenant_id': tenant_id
        }
        queue_db = DB('queues', **queue_db_config)
        # queue_db = DB('queues')

        extraction_db_config = {
            'host': 'extraction_db',
            'port': 3306,
            'user': 'root',
            'password': 'root',
            'tenant_id': tenant_id
        }
        extraction_db = DB('extraction', **extraction_db_config)

        # Get tab definition
        tab_definition = queue_db.get_all('tab_definition')

        logging.debug(f'Getting case info from process queue for case `{case_id}`...')
        query = 'SELECT * FROM `process_queue` WHERE `case_id`=%s'
        case_files = queue_db.execute(query, params=[case_id])

        if case_files.empty:
            message = f'No case ID `{case_id}` found in process queue.'
            logging.warning(message)
            return jsonify({'flag': False, 'message': message})

        logging.debug('Fetching queue info')
        queue_name = list(case_files['queue'])[0]
        queue_definition = queue_db.get_all('queue_definition')
        queue_info = queue_definition.loc[queue_definition['unique_name'] == queue_name]
        queue_id = queue_definition.index[queue_definition['unique_name'] == queue_name].tolist()[0]

        query = f"SELECT id FROM field_definition WHERE FIND_IN_SET({queue_id},queue_field_mapping) > 0"
        field_ids = list(queue_db.execute_(query).id)
        field_definition = queue_db.get_all('field_definition')

        fields_df = field_definition.ix[field_ids] # Get field names using the unique field IDs

        logging.debug(f'Renaming fields for case `{case_id}`')
        # Renaming of fields
        renamed_fields = {}
        for index, row in fields_df.iterrows():
            tab_id = row['tab_id']
            tab_name = tab_definition.loc[tab_id]['text']
            table_name = tab_definition.loc[tab_id]['source']
            fields_df.loc[index, 'tab_id'] = tab_name

            display_name = row['display_name']
            unique_name = row['unique_name']

            query = f'SELECT * FROM `{table_name}` WHERE `case_id`=%s'
            case_tab_files = extraction_db.execute(query, params=[case_id])
            if case_tab_files.empty:
                message = f' - No such case ID `{case_id}` in `{table_name}`.'
                logging.error(message)
                continue
            case_files_filtered = case_tab_files.loc[:, 'created_date':] # created_date column will be included
            fields_df = case_files_filtered.drop(columns='created_date') # Drop created_date column
            table_fields_ = fields_df.to_dict(orient='records')[0] # Get corresponding table fields

            if display_name in table_fields_:
                renamed_fields[unique_name] = table_fields_[display_name]

        response_data = {
            'flag': True,
            'updated_fields_dict': renamed_fields,
            'message': "Successfully applied all validations"
        }

        queue_db.db_.dispose()
        extraction_db.db_.dispose()

        logging.info(f'Response: {response_data}')
        return jsonify(response_data)
    except Exception as e:
        logging.exception('Something went wrong refreshin fields. Check trace.')
        return jsonify({'flag': False, 'message':'System error! Please contact your system administrator.'})

def get_addon_table(table_pattern, case_id_ocr):
    try:
        addon_table = json.loads(list(case_id_ocr['Add_on_Table'])[0])
    except:
        addon_table = []
        
    if len(addon_table) < len(table_pattern): 
        addon_headers = []
        for i in addon_table:
            addon_headers.append(i['header'])
        for i in table_pattern:
            if i not in addon_headers:
                addon_table.append({'header': i, 'rowData': []})                

    return addon_table

@app.route('/unlock_case', methods=['POST', 'GET'])
def unlock_case():
    try:
        data = request.json

        logging.info(f'Request data: {data}')
        # case_id = data.pop('case_id', None)
        operator = data.pop('username', None)

        if operator is None:
            message = f'Username not provided.'
            logging.error(message)
            return jsonify({'flag': False, 'message': message})

        queue_db_config = {
            'host': 'queue_db',
            'port': 3306,
            'user': 'root',
            'password': 'root'
        }
        queue_db = DB('queues', **queue_db_config)
        # queue_db = DB('queues')

        # logging.debug('Fetching process queue data')
        # # Get queue ID using exception type from case files in process_queue table
        # files_df = queue_db.get_all('process_queue', discard=['ocr_data','ocr_text','xml_data'])
        # latest_case_file = files_df
        # case_files = latest_case_file.loc[latest_case_file['case_id'] == case_id]
        # operator = list(case_files.operator)[0]


        # logging.debug('Unlock case and update time spent')
        # Update the time spent on the particular file
        update = {
            'operator': None,
            'last_updated_by': operator
        }
        where = {
            'operator': operator
        }
        queue_db.update('process_queue', update=update, where=where)

        # logging.debug('Unlock case in same cluster')
        # Update the operator to None on the files in the same cluster
        # update = {
        #     'operator': None
        # }
        # where = {
        #     'cluster': list(case_files.cluster)[0]
        # }
        queue_db.update('process_queue', update=update, where=where)

        logging.info('Unlocked file(s).')
        return jsonify({'flag': True, 'message': 'Unlocked file.'})
    except:
        logging.exception('Something went wrong unlocking case. Check trace.')
        return jsonify({'flag': False, 'message':'System error! Please contact your system administrator.'})

@app.route('/get_ocr_data', methods=['POST', 'GET'])
def get_ocr_data():
    try:
        data = request.json

        logging.info(f'Request data: {data}')
        case_id = data['case_id']
        try:
            retrain = data['retrain']
        except:
            retrain = ''

        db_config = {
            'host': 'queue_db',
            'port': 3306,
            'user': 'root',
            'password': 'root'
        }
        db = DB('queues', **db_config)
        # db = DB('queues')

        trained_db_config = {
            'host': 'template_db',
            'user': 'root',
            'password': 'root',
            'port': '3306'
        }
        trained_db = DB('template_db', **trained_db_config)

        extarction_db_config = {
            'host': 'extraction_db',
            'user': 'root',
            'password': 'root',
            'port': '3306'
        }
        extraction_db = DB('extraction', **extarction_db_config)

        table_db_config = {
            'host': 'table_db',
            'user': 'root',
            'password': 'root',
            'port': '3306'
        }
        table_db = DB('table_db', **table_db_config)

        logging.debug('Getting mandatory fields')
        # Get all OCR mandatory fields
        try:
            tab_df = db.get_all('tab_definition')
            ocr_tab_id = tab_df.index[tab_df['source'] == 'ocr'].tolist()
            logging.debug('ocr_tabi_id')
            logging.debug(ocr_tab_id)
            # tab_list = ','.join(ocr_tab_id)
            tab_list = str(tuple(ocr_tab_id))
            query = f'SELECT * FROM `field_definition` WHERE `tab_id`in {tab_list}'
            
            ocr_fields_df = db.execute(query)
            mandatory_fields = list(ocr_fields_df.loc[ocr_fields_df['mandatory'] == 1]['display_name'])
            logging.debug(f'OCR Fields DF: {ocr_fields_df}')
            
        except Exception as e:
            logging.warning(f'Error getting mandatory fields: {e}')
            mandatory_fields = []

        # Get data related to the case from invoice table
        query = "Select * from process_queue where case_id = %s"

        case_files = db.execute(query,params=[case_id])
        if case_files.empty:
            message = f'No such case ID {case_id}.'
            logging.error(message)
            return jsonify({'flag': False, 'message': message})

        query = 'SELECT * FROM `ocr_info` WHERE `case_id`=%s'
        params = [case_id]
        ocr_info = db.execute(query, params=params)
        ocr_data = list(ocr_info.ocr_data)[0].replace('\\','\\\\')
        ocr_data = json.loads(ocr_data)
        ocr_data = [sort_ocr(data) for data in ocr_data]

        vendor_list = list(trained_db.get_all('vendor_list').vendor_name)
        template_list = list(trained_db.get_all('trained_info').template_name)

        fields_list = list(ocr_fields_df['display_name'])
        logging.debug(f'Fields List: {fields_list}')

        if retrain.lower() == 'yes':
            template_name = list(case_files['template_name'])[0]
            trained_info = trained_db.get_all('trained_info')
            trained_info = trained_info.loc[trained_info['template_name'] == template_name]
            field_data = json.loads(list(trained_info.field_data)[0])
            
            # Fetch Table train info from database
            table_train_info = table_db.get_all('table_info')
            table_train_info = table_train_info.loc[table_train_info['template_name'] == template_name]
            try:
                table_info = json.loads(list(table_train_info.table_data)[0])
            except:
                table_info = {}
            extraction_ocr = extraction_db.get_all('ocr')
            extraction_ocr = extraction_ocr.loc[extraction_ocr['case_id'] == case_id]
            highlight = json.loads(list(extraction_ocr.highlight)[0])

            fields_info = get_fields_info(ocr_data,highlight,field_data)

            return jsonify({'flag': True,
                'data': ocr_data,
                'info': {
                    'fields': fields_info,
                    'table': table_info
                },
                'template_name': template_name,
                'vendor_list': sorted(vendor_list),
                'template_list': sorted(template_list),
                'mandatory_fields': mandatory_fields,
                'fields': fields_list,
                'type': 'blob'})

        return jsonify({'flag': True, 'data': ocr_data, 'vendor_list': sorted(vendor_list), 'template_list': sorted(template_list), 'mandatory_fields': mandatory_fields,'fields': fields_list, 'type': 'blob'})
    except Exception as e:
        logging.exception('Something went wrong when getting ocr data. Check trace.')
        return jsonify({'flag':False, 'message':'System error! Please contact your system administrator.'})

@app.route('/update_queue', methods=['POST', 'GET'])
def update_queue():
    try:
        data = request.json

        logging.info(f'Request data: {data}')
        try:
            verify_operator = data['operator']
        except:
            logging.warning('Setting verify operator to None.')
            verify_operator = None

        if 'case_id' not in data or 'queue' not in data or 'fields' not in data:
            message = f'Invalid JSON recieved. MUST contain `case_id`, `queue` and `fields` keys.'
            logging.error(message)
            return jsonify({'flag': False, 'message': message})

        case_id = data['case_id']
        queue = data['queue']
        fields = data['fields']

        if data is None or not data:
            message = f'Data not provided/empty dict.'
            logging.error(message)
            return jsonify({'flag': False, 'message': message})

        if case_id is None or not case_id:
            message = f'Case ID not provided/empty string.'
            logging.error(message)
            return jsonify({'flag': False, 'message': message})

        if queue is None or not queue:
            message = f'Queue not provided/empty string.'
            logging.error(message)
            return jsonify({'flag': False, 'message': message})

        db_config = {
            'host': 'queue_db',
            'port': 3306,
            'user': 'root',
            'password': 'root'
        }
        db = DB('queues', **db_config)
        # db = DB('queues')

        # Get latest data related to the case from invoice table
        invoice_files_df = db.get_all('process_queue')
        latest_case_file = invoice_files_df
        case_files = latest_case_file.loc[latest_case_file['case_id'] == case_id]

        if case_files.empty:
            message = f'No case ID `{case_id}` found in process queue.'
            logging.error(message)
            return jsonify({'flag': False, 'message': message})

        logging.debug(f'Setting queue to `{queue}` for case `{case_id}`')
        query = f'UPDATE `process_queue` SET `queue`=%s WHERE `case_id`=%s'
        params = [queue, case_id]
        update_status = db.execute(query, params=params)

        if update_status:
            message = f'Updated queue for case ID `{case_id}` successfully.'
            logging.debug('Set successfully.')
        else:
            message = f'Something went wrong updating queue. Check logs.'
            logging.error(message)
            return jsonify({'flag': False, 'message': message})

        # ! UPDATE TRACE INFO TABLE HERE
        update_queue_trace(db,case_id,queue)

        # Inserting fields into respective tables
        field_definition = db.get_all('field_definition')
        tab_definition = db.get_all('tab_definition')

        # Change tab ID to its actual names
        for index, row in field_definition.iterrows():
            tab_id = row['tab_id']
            tab_name = tab_definition.loc[tab_id]['text']
            field_definition.loc[index, 'tab_id'] = tab_name

        # Create a new dictionary with key as table, and value as fields dict (column name: value)
        table_fields = {}
        for unique_name, value in fields.items():
            unique_field_name = field_definition.loc[field_definition['unique_name'] == unique_name]

            if unique_field_name.empty:
                logging.warning(f'No unique field name for {unique_name}. Check `field_defintion` database.')
                continue

            table = list(unique_field_name.tab_id)[0].lower().replace(' ', '_')
            display_name = list(unique_field_name.display_name)[0]

            if table not in table_fields:
                table_fields[table] = {}

            table_fields[table][display_name] = value

        extraction_db_config = {
            'host': 'extraction_db',
            'port': 3306,
            'user': 'root',
            'password': 'root'
        }
        extraction_db = DB('extraction', **extraction_db_config)
        # extraction_db = DB('extraction')

        # ! GET HIGHLIGHT FROM PREVIOUS RECORD BECAUSE UI IS NOT SENDING
        ocr_files_df = extraction_db.get_all('ocr')
        latest_ocr_files = extraction_db.get_latest(ocr_files_df, 'case_id', 'created_date')
        ocr_case_files = latest_ocr_files.loc[latest_ocr_files['case_id'] == case_id]
        highlight = list(ocr_case_files.highlight)[0]

        for table_name, fields_dict in table_fields.items():
            # Only in OCR table add the highlight
            if table_name == 'ocr':
                column_names = ['`case_id`', '`highlight`']
                params = [case_id, highlight]
            else:
                column_names = ['`case_id`']
                params = [case_id]

            for column, value in fields_dict.items():
                if column == 'Verify Operator':
                    column_names.append(f'`{column}`')
                    params.append(verify_operator)
                else:
                    column_names.append(f'`{column}`')
                    params.append(value)
            query_column_names = ', '.join(column_names)
            query_values_placeholder = ', '.join(['%s'] * len(params))

            query = f'INSERT INTO `{table_name}` ({query_column_names}) VALUES ({query_values_placeholder})'

            extraction_db.execute(query, params=params)

        return jsonify({'flag': True, 'message': 'Changing queue completed.'})
    except Exception as e:
        return jsonify({'flag':False, 'message':'System error! Please contact your system administrator.'})

@app.route('/execute_button_function', methods=['POST', 'GET'])
def execute_button_function():
    try:
        functions = request.json
        message = None
        updated_fields_dict = None
        status_type = None

        if functions is None or not functions:
            message = f'Data recieved is none/empty. No function to execute.'
            logging.error(message)
            return jsonify({'flag': False, 'message': message})

        for function in functions:
            host = 'servicebridge'
            port = 80
            data = function['parameters']
            route = function['route']
            response = requests.post(f'http://{host}:{port}/{route}', json=data)
            response_data = response.json()

            if not response_data['flag']:
                try:
                    message = response_data['message']
                except:
                    message = f'Failed during execute of route `{route}`. Check logs.'
                logging.error(message)
                return jsonify({'flag': False, 'message': message})
            else:
                if 'message' in response_data:
                    message = response_data['message']
                if 'updated_fields_dict' in response_data:
                    updated_fields_dict = response_data['updated_fields_dict']
                if 'status_type' in response_data:
                    status_type = response_data['status_type']

        if message is not None:
            return jsonify({'flag': True, 'message': message, 'updated_fields_dict': updated_fields_dict, 'status_type': status_type})
        else:
            return jsonify({'flag': True, 'message': f'Succesfully executed functions', 'updated_fields_dict': updated_fields_dict, 'status_type': status_type})
    except Exception as e:
        return jsonify({'flag':False, 'message':'System error! Please contact your system administrator.'})

def create_children(queue, queue_definition_record,list_):
    queue_name = queue['name']
    queue_uid = queue['unique_name']
    queue_children = list(queue_definition_record.loc[queue_definition_record['parent'] == queue_uid].name)
    logging.debug(f'Queue Name: {queue_name}')
    logging.debug(f'Queue UID: {queue_uid}')
    logging.debug(f'Queue Children: {queue_children}')
    if queue_children:
        queue['children'] = []
        temp_dict = queue_definition_record.loc[queue_definition_record['parent'] == queue_uid].to_dict(orient='records')
        for index, definition in enumerate(temp_dict):
            if definition['id'] not in list_:
                continue
            children = {}
            children['name'] = definition['name']
            tokens = definition['name'].split()
            children['path'] = definition['unique_name'].replace(' ', '')
            children['pathId'] = definition['id']
            children['type'] = definition['type'] 
            children['unique_name'] = definition['unique_name']
            queue['children'].append(children)
    
    return queue

@cache.memoize(86400)
def get_queues_cache(username, tenant_id=None):
    logging.info('First time. Caching.')
    logging.debug(f'Username: {username}')
    logging.debug(f'Tenant ID: {tenant_id}')

    db_config = {
        'host': 'queue_db',
        'port': 3306,
        'user': 'root',
        'password': 'AlgoTeam123',
        'tenant_id': tenant_id
    }

    group_db = DB('group_access', **db_config)
    queue_db = DB('queues', **db_config)

    query = "SELECT id, username from active_directory"
    user_list = group_db.execute(query).username.to_dict()

    query = "SELECT * from user_organisation_mapping"
    user_details = group_db.execute(query).to_dict()

    query = "SELECT * from organisation_attributes"
    attributes = group_db.execute(query).to_dict()

    query = "SELECT id, parent_id from organisation_hierarchy"
    hierarchy_id = group_db.execute(query).parent_id.to_dict()

    hierarchy = []
    for k,v in hierarchy_id.items():
        hierarchy.append(attributes['attribute'][v])
    
    query = "SELECT * from queue_access"
    queue_access = group_db.execute(query).to_dict()

    query = "SELECT id,group_definition from group_definition"
    group_definition = group_db.execute(query).group_definition.to_dict()

    user_info = {}
    for k, v in user_details['user_id'].items():
        name = user_list[v]
        index = user_details['organisation_attribute'][k]
        attribute_name = attributes['attribute'][index]
        attribute_value = user_details['value'][k]              
        try:
            user_info[name][attribute_name] = attribute_value
        except:
            user_info[name] = {attribute_name: attribute_value}
    

    # Optimize below   
    group_dict = {}
    for k, v in user_info.items():
        group_list = []
        for key, val in v.items():
            subset = []
            for group, attribute in group_definition.items():       
                attribute = json.loads(attribute)
                for x,y in attribute.items():
                    if key.lower() == x.lower() and val.lower() == y.lower():
                        subset.append(group)
            if subset != []:
                group_list.append(subset)
        group_dict[k] = group_list

    classify_users = {}
    for user, value in group_dict.items():
        if value and len(value) > 1:
            classify_users[user] = list(set.intersection(*map(set,value)))
        else:
            classify_users[user] = value[0]


    query = "SELECT * from queue_access"
    queue_group_id = group_db.execute(query)

    user_queues = {}

    for user, group_id in classify_users.items():
        user_queues[user] = list(set(queue_group_id.loc[queue_group_id['group_id'].isin(group_id)].queue_id))

    for user, value in user_queues.items(): 
        queues = []
        if value:
            placeholders = ','.join(['%s'] * len(value))
            query = f"SELECT * FROM queue_definition WHERE `id` IN ({placeholders}) ORDER BY `queue_order` ASC"
            full_query = "SELECT * FROM queue_definition ORDER BY `queue_order` ASC"
            queue_definition_full = queue_db.execute_(full_query)
            queue_definition_dict = queue_db.execute_(query, params=[value]).to_dict(orient='records')
            child_query = "SELECT * FROM queue_definition WHERE level=2 ORDER BY `queue_order` ASC"
            child_queues = list(queue_db.execute_(child_query).unique_name)
            for index, definition in enumerate(queue_definition_dict):
                if definition['unique_name'] in child_queues:
                    continue
                queue = {}
                queue['name'] = definition['name']
                tokens = definition['unique_name'].split()
                # queue['path'] = tokens[0].lower() + ''.join(x.title() for x in tokens[1:]) if len(tokens) > 1 else tokens[0].lower()
                queue['path'] = definition['unique_name'].replace(' ','')
                queue['pathId'] = definition['id']
                queue['type'] = definition['type']
                queue['unique_name'] = definition['unique_name']
                queue = create_children(queue, queue_definition_full,value)
                queues.append(queue) 
                
        user_queues[user] = queues

    return user_queues[username]

@app.route('/get_queues', methods=['POST', 'GET'])
def get_queues():
    try:
        data = request.json

        logging.info(f'Request data: {data}')
        if data is None or not data:
            message = f'Data recieved is none/empty.'
            logging.error(message)
            return jsonify({'flag': False, 'message': message})

        username = data.pop('username', None)
        tenant_id = data.pop('tenant_id', None)

        logging.debug('Getting queues')
        # r = redis.StrictRedis(host='3.208.195.34', port=6379, db=0)
        # user_queues_get = json.loads(r.get("user_queues"))

        # queues = user_queues_get[username]

        queues = get_queues_cache(username, tenant_id)

        if not username:
            return jsonify({'flag': False, 'message': 'logout'})

        if not queues:
            message = f'No queues available for role `{username}`.'
            logging.error(message)
            return jsonify({'flag': False, 'message': message})

        logging.info('Successfully got queues.')
        return jsonify({'flag': True, 'data': {'queues': queues}})
    except Exception as e:
        logging.exception('Something went wrong getting queues. Check trace.')
        return jsonify({'flag':False, 'message':'System error! Please contact your system administrator.'})


def fix_JSON(json_message=None):
    logging.info('Fixing JSON')
    logging.info(f'JOSN Message: {json_message}')
    result = None
    try:
        result = json.loads(json_message)
    except Exception as e:
        # Find the offending character index:
        idx_to_replace = int(str(e).split(' ')[-1].replace(')',''))

        # Remove the offending character:
        json_message = list(json_message)
        json_message[idx_to_replace] = ' '
        new_message = ''.join(json_message)
    
        return fix_JSON(json_message=new_message)

    logging.info(f'Response: {result}')
    return result


def get_ocr_stats(db,from_date=None, to_date=None, total_fields  = 9):
    """Return the ocr stats from the from_date, to_date"""
    logging.info('Getting OCR Stats')

    if (not to_date) or (not from_date):
        query = "SELECT fa.fields_changed, pq.created_date FROM `field_accuracy` fa,process_queue pq where fa.case_id =pq.case_id and pq.queue='Approved'"
        df = db.execute_(query)
    else:
        if to_date == from_date:
            from_date += " 00:00:01"
            to_date += " 23:59:59"
        query = "SELECT fa.fields_changed, pq.created_date FROM `field_accuracy` fa,process_queue pq where fa.case_id =pq.case_id and pq.queue='Approved' and pq.created_date > %s and pq.created_date < %s"
        df = db.execute_(query, params=[from_date, to_date])

    fields_changes_list = []

    for ele in list(df['fields_changed']):
        try:
            fields_changes_list.append(len(json.loads(ele,strict=False)))
        except Exception as e:
            logging.warning(f'Exception handled. [{e}]')
            fix_json_ele = fix_JSON(ele)
            fields_changes_list.append(len(fix_json_ele))

    manual_changes = sum(fields_changes_list)
    total = len(df['fields_changed'])*total_fields
    extracted_ace = total - manual_changes
    
    logging.debug(f'Manual changes: {manual_changes}')
    logging.debug(f'Extracted ACE: {extracted_ace}')
    logging.debug(f'Total: {total}')
    logging.debug(f'Manual + Extracted ACE: {manual_changes + extracted_ace}')

    return manual_changes, extracted_ace, total

@app.route('/move_to_verify', methods=['POST', 'GET'])
def move_to_verify():
    try:
        data = request.json
        
        logging.info(f'Request data: {data}')
        case_id = data['case_id']
        queue = data['queue']

        db_config = {
            'host': 'queue_db',
            'port': 3306,
            'user': 'root',
            'password': 'root'
        }
        db = DB('queues', **db_config)

        extraction_db_config = {
            'host': 'extraction_db',
            'port': 3306,
            'user': 'root',
            'password': 'root'
        }
        extraction_db = DB('extraction', **extraction_db_config)

        stats_db_config = {
            'host': 'stats_db',
            'user': 'root',
            'password': 'root',
            'port': '3306'
        }

        stats_db = DB('stats', **stats_db_config)

        # Step 1: Change queue to Verify, Update Source of Invoice, Reference Number
        query = "SELECT id, created_date FROM process_queue WHERE case_id = %s"
        created_date = str(list(db.execute(query, params = [case_id]).created_date)[0])
        batch_id = created_date[:4] + created_date[5:6].replace('0','') + created_date[6:10].replace('-','') + '0'

        if queue == 'failed':
            template_name = 'Failed Template'
        else:
            template_name = 'Dummy Template'

        get_queue_name_query = 'SELECT `id`, `name`, `unique_name` FROM `queue_definition` WHERE `id` IN (SELECT `workflow_definition`.`move_to` FROM `queue_definition`, `workflow_definition` WHERE `queue_definition`.`name`=%s AND `workflow_definition`.`queue_id`=`queue_definition`.`id`)'
        new_queue = list(db.execute(get_queue_name_query, params=[queue]).name)[0]
        update_fields = {'queue': new_queue, 'template_name': template_name}

        logging.debug(f'Updating queue to `{new_queue}` for case `{case_id}`')
        db.update('process_queue', update=update_fields, where={'case_id': case_id})
        audit_data = {
                "type": "update", "last_modified_by": "Move to Verify", "table_name": "process_queue", "reference_column": "case_id",
                "reference_value": case_id, "changed_data": json.dumps(update_fields)
            }
        stats_db.insert_dict(audit_data, 'audit')

        # Step 2: Update extraction table
        logging.debug(f'Inserting to OCR')
        query = "INSERT into ocr (`case_id`, `highlight`) VALUES (%s,%s)"
        extraction_db.execute(query, params=[case_id, '{}'])

        response = {'flag': True, 'status_type': 'success', 'message': "Successfully sent to Verify"}
        logging.info(f'Response: {response}')
        return jsonify(response)
    except Exception as e:
        logging.exception(f'Something went wrong while getting queues. Check trace.')
        return jsonify({'flag':False, 'status_type': 'failed', 'message':'System error! Please contact your system administrator.'})
