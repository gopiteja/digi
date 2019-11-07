import argparse
import ast
import base64
import json
import requests
import traceback
import warnings
import os
import pandas as pd
import sqlalchemy

from datetime import datetime, timedelta
from db_utils import DB
from flask import Flask, request, jsonify
from flask_cors import CORS
from pandas import Series, Timedelta, to_timedelta
from time import time
from itertools import chain, repeat, islice, combinations
from io import BytesIO

try:
    from app.ace_logger import Logging
except:
    from ace_logger import Logging

from app import app
from app import cache

logging = Logging()

db_config = {
    'host': os.environ['HOST_IP'],
    'port': os.environ['LOCAL_DB_PORT'],
    'user': os.environ['LOCAL_DB_USER'],
    'password': os.environ['LOCAL_DB_PASSWORD']
}

def dataframe_to_blob(data_frame):
    bio = BytesIO()
    writer = pd.ExcelWriter(bio, sheet_name = 'sheet1')
    data_frame.to_excel(writer, index= False)
    writer.save()
    bio.seek(0)
    blob_data = base64.b64encode(bio.read())
    return blob_data

def fix_json_decode_error(data_frame):
    for column in data_frame.columns:
        if isinstance(data_frame.loc[0, column], (pd._libs.tslibs.timedeltas.Timedelta, pd._libs.tslibs.timestamps.Timestamp)):       
            data_frame[column] = data_frame[column].astype(str)
    return data_frame

@app.route('/upload_master_blob', methods = ['GET', 'POST'])
def upload_master_blob():
    data = request.json
    logging.info(f'Request data: {data}')
    tenant_id = data.pop('tenant_id', None)
    duplicate_check = data.pop('duplicate_check', True)
    insert_flag = data.pop('insert_flag', 'append')
        
    try:
        master_table_name = data.pop('master_table_name')
    except:
        traceback.print_exc()
        message = f"Master table name not provided"
        return jsonify({"flag": False, "message" : message})
    try:
        blob_data = data.pop('blob')
    except:
        traceback.print_exc()
        message = f"Blob data not provided"
        return jsonify({"flag": False, "message" : message})

    
    database = 'extraction'
    extraction_db = DB(database, tenant_id=tenant_id,**db_config)
    
    try:
        blob_data = blob_data.split(",", 1)[1]
        #Padding
        blob_data += '='*(-len(blob_data)%4)
        file_stream = BytesIO(base64.b64decode(blob_data))
        data_frame = pd.read_excel(file_stream)
        data_frame.fillna(value= '', inplace=True)
    except:
        traceback.print_exc()
        message = f"Could not convert blob to dataframe"
        return jsonify({"flag": False, "message" : message})
    
    if duplicate_check == True and insert_flag == 'append':
        try:
            master_df = extraction_db.execute_(f"SELECT * FROM `{master_table_name}`")
            duplicate_check_df = extraction_db.execute_(f"SELECT * FROM `duplicate_check` WHERE `table_name` = '{master_table_name}'")
            
            if not duplicate_check_df.empty:
                columns_string = list(duplicate_check_df['columns'])[0]
            else:
                message = f"Duplicate columns not defined in Extraction DB"
                return jsonify({"flag": False, "message" : message})
            
            columns = columns_string.split(",")
            
            columns_ = list(data_frame.columns) 
            columns_.remove('id') #ALL COLUMNS EXCEPT ID 
            
            data_frame.drop_duplicates(subset= columns_, keep = 'first', inplace = True)
            df_all = data_frame.merge(master_df[columns], how = 'left', on= columns, indicator = True)
            
            unique_df = df_all[df_all['_merge'] == 'left_only'].drop(columns = ['_merge'])
            duplicates_df = df_all[df_all['_merge'] == 'both'].drop(columns = ['_merge']) #NEED THIS FOR KARVY
            
            df_to_insert = unique_df.drop(columns = ['id'])
            logging.info(f"Data to be inserted after duplicate check - ", df_to_insert)
            df_to_insert.to_sql(name= master_table_name, con = extraction_db.engine, if_exists='append', index= False, method= 'multi')
            
        except:
            traceback.print_exc()
            message = f"Could not append data to {master_table_name}"
            return jsonify({"flag": False, "message" : message})
    
    elif duplicate_check == False and insert_flag == 'append':
        try:
            data_frame = data_frame.drop(columns = ['id'])
            data_frame.to_sql(name= master_table_name, con = extraction_db.engine, if_exists='append', index= False, method= 'multi')
        except:
            traceback.print_exc()
            message = f"Could not update {master_table_name}"
            return jsonify({"flag": False, "message" : message})
    
    elif insert_flag == 'overwrite':    
        try:
            data_frame = data_frame.drop(columns = ['id'])
            delete_query = f"DELETE FROM `{master_table_name}`"
            ai_query = f"ALTER TABLE `{master_table_name}` AUTO_INCREMENT = 1"
            extraction_db.execute(delete_query)
            extraction_db.execute(ai_query)
            data_frame.to_sql(name= master_table_name, con = extraction_db.engine, if_exists='append', index= False, method= 'multi')
        except:
            traceback.print_exc()
            message = f"Could not update {master_table_name}"
            return jsonify({"flag": False, "message" : message})
        
    message = f"Successfully update {master_table_name} in {database}"
    return jsonify({'flag': True, 'message': message})

@app.route('/download_master_blob', methods = ['GET', 'POST'])
def download_master_blob():
    data = request.json
    logging.info(f'Request data: {data}')
    tenant_id = data.pop('tenant_id', None)
    download_type = data.pop('dowload_type', 'Data')
    
    try:
        master_table_name = data.pop('master_table_name')
    except:
        traceback.print_exc()
        message = f"Master table name not provided"
        return jsonify({"flag": False, "message" : message})

    database = 'extraction'
    extraction_db = DB(database,tenant_id=tenant_id, **db_config)
    
    if download_type == 'Data':
        try:
            data_frame = extraction_db.execute_(f"SELECT * FROM `{master_table_name}`")
            data_frame = data_frame.astype(str)
            data_frame.replace(to_replace= 'None', value= '', inplace= True)
            blob_data = dataframe_to_blob(data_frame)
        except:
            traceback.print_exc()
            message = f"Could not load from {master_table_name}"
            return jsonify({"flag": False, "message" : message})
    elif download_type == 'template':
        try:
            data_frame = extraction_db.execute_(f"SELECT * FROM `{master_table_name}` LIMIT 0")
            data_frame = data_frame.astype(str)
            data_frame.replace(to_replace= 'None', value= '', inplace= True)
            blob_data = dataframe_to_blob(data_frame)
        except:
            traceback.print_exc()
            message = f"Could not load from {master_table_name}"
            return jsonify({"flag": False, "message" : message})
    return jsonify({'flag': True, 'blob': blob_data.decode('utf-8'), 'file_name' : master_table_name + '.xlsx'})

@app.route('/get_master_data', methods= ['GET', 'POST'])
def get_master_data():
    data = request.json
    logging.info(f'Request data: {data}')
    tenant_id = data.pop('tenant_id', None)
    master_table_name = data.pop('master_table_name', None)

    database = 'extraction'
    extraction_db = DB(database, tenant_id=tenant_id,**db_config)
    
    try:
        start_point = data['start'] - 1
        end_point = data['end']
        offset = end_point - start_point
    except:
        start_point = 0
        end_point = 20
        offset = 20
    
    if master_table_name:
        table_name = master_table_name
    else:
        tables_df = extraction_db.execute_(f"SELECT * FROM `master_upload_tables`")
        if not tables_df.empty:
            tables_list = list(tables_df["table_name"])
            table_name = tables_list[0]
        else:
            traceback.print_exc()
            message = f"No tables in extraction database"
            return jsonify({"flag": False, "message" : message})
    try:
        data_frame = extraction_db.execute_(f"SELECT * FROM `{table_name}` LIMIT {start_point}, {offset}")
        data_frame = data_frame.astype(str)
        total_rows = list(extraction_db.execute_(f"SELECT COUNT(*) FROM `{table_name}`")['COUNT(*)'])[0]
        data_frame.replace(to_replace= "None", value= '', inplace= True)
        data_dict = data_frame.to_dict(orient= 'records')
    except:
        traceback.print_exc()
        message = f"Could not load {table_name} from {database}"
        return jsonify({"flag": False, "message" : message})
    
    if end_point > total_rows:
        end_point = total_rows
    if start_point == 1:
        pass
    else:
        start_point += 1
    
    pagination = {"start": start_point, "end": end_point, "total": total_rows}
    
    data = {
        "header": list(data_frame.columns),
        "rowData": data_dict,
        "pagination": pagination
    }
    
    button_options_data=button_options(extraction_db)
    if button_options_data['flag']==True:
        options_data=button_options_data["options_data"]
    else:
        message=f"unable to load options data"
        return jsonify({'flag':False,'message':message})
    
    if master_table_name:
        to_return = {
            'flag': True,
            'data': {
                'data': data,
                'options_data':options_data
                }
            }
    else:        
        to_return = {
            'flag': True,
            'data': {
                'master_data': tables_list,
                'data': data,
                'options_data':options_data
                }
            }
    return jsonify(to_return)

def button_options(extraction_db):
    try:   
        button_options_query=f"SELECT * FROM `button_options`"
        button_options_query_df=extraction_db.execute_(button_options_query)
        button_options_query_df.to_dict(orient='records')
        for idx, row in button_options_query_df.iterrows():
            if row['type'] == 'dropdown':
                button_options_query_df.at[idx, 'options'] = json.loads(row['options'])
        button_list=[]
        options_data={}
        for row in button_options_query_df['button'].unique():
            button_list=[]
            button_options_df =button_options_query_df[button_options_query_df['button']==row]
            for display_name in button_options_df['display_name'].unique():
                button_option_df=button_options_query_df[button_options_query_df['display_name']==display_name]
                button_df=button_option_df.to_dict(orient='records')
                button_list.append({"display_name":display_name,"options":button_df})
            options_data[row]=button_list
        return {"flag":True,"options_data":options_data }
    except:
        traceback.print_exc()
        message = f"something went wrong while generating button_options data"
        return {"flag": False, "message" : message}   