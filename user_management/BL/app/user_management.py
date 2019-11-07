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
from sqlalchemy.orm import sessionmaker

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

def get_attribute_value_pairs():
    return    

def delete_user(data, group_access_db):
    try:
        user_id = data['id']
        user_name = data['username']
    except:
        traceback.print_exc()
        message = "id not present in request data."
        return {"flag": False, "message" : message}
    
    try:
        organisation_mapping_query = f"DELETE FROM `user_organisation_mapping` WHERE `user_id` = '{user_id}'" 
        result = group_access_db.execute(organisation_mapping_query)
        if not result:
            message = f"Something went wrong while deleting the user {user_name} | user_id {user_id} from user_organisation_mapping"
            return {"flag": False, "message" : message}
    except:
        traceback.print_exc()
        message = f"Something went wrong while deleting the user {user_name} | user_id {user_id} from user_organisation_mapping"
        return {"flag": False, "message" : message}
    
    try:
        active_directory_query = f"DELETE FROM `active_directory` WHERE `id` = '{user_id}'" 
        result = group_access_db.execute(active_directory_query)
        if not result:
            message = f"Something went wrong while deleting the user {user_name} | user_id {user_id} from active_directory"
            return {"flag": False, "message" : message}
    except:
        traceback.print_exc()
        message = f"Something went wrong while deleting the user {user_name} | user_id {user_id} from active_directory"
        return {"flag": False, "message" : message}
    
    message = f"Successfully deleted {user_name} | user_id {user_id} from database"
    return {"flag": True, "message" : message}

def edit_user(row_data, group_access_db):
    try:
        user_id = row_data.pop('id')
        user_name = row_data['username']
        attributes = row_data.pop('attributes', {})
    except:
        traceback.print_exc()
        message = "id not present in request data."
        return {"flag": False, "message" : message}
    
    try:
        result= group_access_db.update(table='active_directory', update= row_data, where= {'id': user_id})
        if not result:
            message = f"Something went wrong while updating the user {user_name} | user_id {user_id} in active directory"
            return {"flag": False, "message" : message}
    except:
        traceback.print_exc()
        message = f"Something went wrong while updating the user {user_name} | user_id {user_id} in active directory"
        return {"flag": False, "message" : message}
    
    try:
        query = f"SELECT * FROM `active_directory` WHERE `username` = '{user_name}'"
        active_directory_df = group_access_db.execute_(query)
        user_id = list(active_directory_df['id'])[0]
    except:
        traceback.print_exc()
        message = f"Something went wrong while fetching the user {user_name} from active directory"
        return {"flag": False, "message" : message}    
    
    attribute_value_list = ','.join([f"'{x}'" for x in list(attributes.keys())])
    if attribute_value_list:
        try:
            query1 = f"SELECT * FROM `organisation_attributes` WHERE `attribute` in ({attribute_value_list})"
            organisation_attributes_df = group_access_db.execute_(query1)
        except:
            traceback.print_exc()
            message = f"Something went wrong while fetching oraganisation attributes from database"
            return {"flag": False, "message" : message}
    else:
        traceback.print_exc()
        message = f"No records found in oraganisation attributes. Check database"
        return {"flag": False, "message" : message}        
    
    result = generate_insert_list(attributes, organisation_attributes_df, user_id) 
    to_insert = result['data'] if result['flag'] else []
    
    if to_insert:
        try:
            organisation_mapping_delete_query = f"DELETE FROM `user_organisation_mapping` WHERE `user_id` = '{user_id}'" 
            result = group_access_db.execute(organisation_mapping_delete_query)
            if not result:
                message = f"Something went wrong while deleting the user {user_name} | user_id {user_id} from user_organisation_mapping"
                return {"flag": False, "message" : message}
        
        except:
            message = f"Something went wrong while deleting the user {user_name} | user_id {user_id} from user_organisation_mapping"
            return {"flag": False, "message" : message}
        try:    
            insert_query = generate_multiple_insert_query(to_insert, 'user_organisation_mapping')
            print(f"Insert query - {insert_query}")
            result = group_access_db.execute(insert_query)
            if not result:
                message = f"Something went wrong while inserting details for user {user_name} | user_id {user_id} in user_organisation_mapping"
                return {"flag": False, "message" : message}
        except:
            message = f"Something went wrong while inserting details for user {user_name} | user_id {user_id} in user_organisation_mapping"
            return {"flag": False, "message" : message}
    
    else:
        message = f"No data found for user {user_name} | user_id {user_id} to insert in user_organisation_mapping"
        return {"flag": False, "message" : message}
    
    message = f"Successfully updated {user_name} | user_id {user_id} in database"
    return {"flag": True, "message" : message}
              
def create_user(row_data, group_access_db):
    # TRY USING COMMIT AND ROLLBACK WITH SQLALCHEMY
    try:
        attributes = row_data.pop('attributes', {})
        user_name = row_data['username']
        print(f"row_data received : {row_data}")
    except:
        traceback.print_exc()
        message = "id not present in request data."
        return {"flag": False, "message" : message}
    
    try:
        create_user_query = generate_insert_query(row_data, 'active_directory')
        group_access_db.execute(create_user_query)
    except sqlalchemy.exc.IntegrityError:
        message = "Duplicate entry for username"
        return {"flag": False, "message" : message}
    except:
        traceback.print_exc()
        message = "Something went wrong while creating user_name {user_name}."
        return {"flag": False, "message" : message}
    
    try:
        query = f"SELECT * FROM `active_directory` WHERE `username` = '{user_name}'"
        active_directory_df = group_access_db.execute_(query)
        user_id = list(active_directory_df['id'])[0]
    except:
        traceback.print_exc()
        message = f"Something went wrong while fetching the user {user_name} from active directory"
        return {"flag": False, "message" : message}    
    
    attribute_value_list = ','.join([f"'{x}'" for x in list(attributes.keys())])
    if attribute_value_list:
        try:
            query1 = f"SELECT * FROM `organisation_attributes` WHERE `attribute` in ({attribute_value_list})"
            organisation_attributes_df = group_access_db.execute_(query1)
        except:
            traceback.print_exc()
            message = f"Something went wrong while fetching oraganisation attributes from database"
            return {"flag": False, "message" : message}
    else:
        traceback.print_exc()
        message = f"No records found in oraganisation attributes. Check database"
        return {"flag": False, "message" : message}        
    
    result = generate_insert_list(attributes, organisation_attributes_df, user_id) 
    to_insert = result['data'] if result['flag'] else []
    
    if to_insert:
        try:    
            insert_query = generate_multiple_insert_query(to_insert, 'user_organisation_mapping')
            print(f"Insert query - {insert_query}")
            result = group_access_db.execute(insert_query)
            if not result:
                message = f"Something went wrong while inserting details for user {user_name} | user_id {user_id} in user_organisation_mapping"
                return {"flag": False, "message" : message}
        except:
            message = f"Something went wrong while inserting details for user {user_name} | user_id {user_id} in user_organisation_mapping"
            return {"flag": False, "message" : message}
    
    else:
        message = f"No data found for user {user_name} | user_id {user_id} to insert in user_organisation_mapping"
        return {"flag": False, "message" : message}
    
    message = f"Successfully inserted {user_name} into active directory"
    return {"flag": True, "message" : message}      

def delete_report(data, group_access_db):
    try:
        report_id = data['id']
        report_type = data['report_type']
    except:
        traceback.print_exc()
        message = "id not present in request data."
        return {"flag": False, "msg" : message}
    
    try:
        delete_report_query = f"DELETE FROM `report_types` WHERE `id` = '{report_id}'" 
        result = group_access_db.execute(delete_report_query)
        if not result:
            message = f"Something went wrong while deleting the report {report_type} | id {report_id} from report_types"
            return {"flag": False, "msg" : message}
    except:
        traceback.print_exc()
        message = f"Something went wrong while deleting the report {report_type} | id {report_id} from report_types"
        return {"flag": False, "msg" : message}
    message = f"Successfully deleted {report_type} | id {report_id} from table"
    return {"flag": True, "msg" : message}

def edit_report(row_data, group_access_db):
    try:
        report_id = row_data.pop('id')
        report_type = row_data['report_type']
        
    except:
        traceback.print_exc()
        message = "id not present in request data."
        return {"flag": False, "msg" : message}
    
    try:
        result= group_access_db.update(table='report_types', update= row_data, where= {'id': report_id})
        if not result:
            message = f"Something went wrong while updating the report {report_type} | report_id {report_id} in report_types"
            return {"flag": False, "msg" : message}
    except:
        traceback.print_exc()
        message = f"Something went wrong while updating the report {report_type} | report_id {report_id} in report_types"
        return {"flag": False, "msg" : message}
    message = f"Successfully updated {report_type} | report_id {report_id} in table"
    return {"flag": True, "msg" : message}

def create_report(row_data, group_access_db):
    try:
        report_type = row_data['report_type']
        print(f"row_data received : {row_data}")
    except:
        traceback.print_exc()
        message = "id not present in request data."
        return {"flag": False, "msg" : message}
    
    try:
        create_report_query = generate_insert_query(row_data, 'report_types')
        group_access_db.execute(create_report_query)
    except sqlalchemy.exc.IntegrityError:
        message = "Duplicate entry for report_type"
        return {"flag": False, "msg" : message}
    except:
        traceback.print_exc()
        message = "Something went wrong while creating report{report_type}."
        return {"flag": False, "msg" : message}
    message = f"Successfully inserted {report_type} into report_types"
    return {"flag": True, "msg" : message}  
        
def generate_insert_query(dict_data, table_name):
    columns_list,values_list = [],[]
    
    for column, value in dict_data.items():
        columns_list.append(f"`{column}`")
        values_list.append(f"'{value}'")

    columns_list = ', '.join(columns_list)
    values_list= ', '.join(values_list)

    insert_query = f"INSERT INTO `{table_name}` ({columns_list}) VALUES ({values_list})"
    
    return insert_query

def generate_multiple_insert_query(data, table_name):
    values_list = []
    for row in data:
        values_list_element = []
        for column, value in row.items():
            values_list_element.append(f"'{value}'")
        values_list.append('(' + ', '.join(values_list_element) + ')')
    values_list = ', '.join(values_list)
    columns_list = ', '.join([f"`{x}`" for x in list(data[0].keys())])
    query = f"INSERT INTO `{table_name}` ({columns_list}) VALUES {values_list}"
    
    return query

def generate_insert_list(attributes, organisation_attributes_df, user_id):
    to_insert = []
    try:
        for attribute_name, value in attributes.items():
            try:
                attribute_id = list(organisation_attributes_df[organisation_attributes_df['attribute'] == attribute_name].id)[0]
            except:
                print(f"SKipping key {attribute_id}")
            if value:
                to_insert.append({
                        'user_id': user_id,
                        'organisation_attribute': attribute_id,
                        'value': value})
        return {"flag": True, "data" : to_insert}
    except:     
        traceback.print_exc()
        message = f"Something went wrong while generating rows to be inserted."
        return {"flag": False, "message" : message}   

@app.route("/show_existing_users", methods=['POST', 'GET'])
def show_existing_users():
    try:
        data = request.json
        logging.info(f'Request data: {data}')
        tenant_id = data.pop('tenant_id', None)
    except:
        traceback.print_exc()
        message = "Received unexpected request data."
        return jsonify({"flag": False, "message" : message})
    
    try:
        start_point = data['start'] - 1
        end_point = data['end']
        offset = end_point - start_point
    except:
        start_point = 0
        end_point = 20
        offset = 20
        
    db_config = {
        'host': os.environ['HOST_IP'],
        'port': '3306',
        'user': 'root',
        'password': os.environ['LOCAL_DB_PASSWORD'],
        'tenant_id': tenant_id
    }

    group_access_db = DB('group_access', **db_config)

    try:
        active_directory_query = f"SELECT * FROM `active_directory` WHERE `status` = 1 LIMIT {start_point}, {offset}"
        active_directory_df = group_access_db.execute_(active_directory_query)
        total_users = list(group_access_db.execute_(f"SELECT COUNT(*) FROM `active_directory` WHERE `status` = 1")['COUNT(*)'])[0]
        if active_directory_df.empty:
            message = "No users present in Active Directory"
            logging.exception(message)    
    except:
        traceback.print_exc()
        message = "Could not load from Active Directory"
        return jsonify({"flag": False, "message" : message})
    
    active_user_ids = ','.join([json.dumps(str(x)) for x in list(active_directory_df['id'])])
    
    try:
        if active_user_ids:
            organisation_mapping_query = f"SELECT `user_organisation_mapping`.*, `organisation_attributes`.`attribute` FROM `user_organisation_mapping`, `organisation_attributes` WHERE `user_id` in ({active_user_ids}) AND `organisation_attributes`.`id` = `user_organisation_mapping`.`organisation_attribute`"
        else:
            organisation_mapping_query = f"SELECT `user_organisation_mapping`.*, `organisation_attributes`.`attribute` FROM `user_organisation_mapping`, `organisation_attributes` WHERE `user_id` in ('abcde') AND `organisation_attributes`.`id` = `user_organisation_mapping`.`organisation_attribute`"
        organisation_mapping_df = group_access_db.execute_(organisation_mapping_query)
        if organisation_mapping_df.empty:
            message = "No users present in User Organisation Mapping"
            logging.exception(message)
    except:
        traceback.print_exc()
        message = "Could not load from User Organisation Mapping"
        return jsonify({"flag": False, "message" : message})
    
    active_directory_df['attributes'] = None
    try:
        for idx, row in active_directory_df.iterrows():
            attributes= {}
            for _, user_mapping_row in organisation_mapping_df[organisation_mapping_df['user_id'] == row['id']].iterrows():
                attributes = {**attributes, **{user_mapping_row['attribute']: user_mapping_row['value']}}
            print(attributes)
            active_directory_df.at[idx, 'attributes'] = attributes
    except:
        traceback.print_exc()
        message = "Something went wrong while fetching user attributes"
        return jsonify({"flag": False, "message" : message})
    
    active_directory_dict = active_directory_df.to_dict(orient= 'records')
    try:
        result = get_dropdown_definition(tenant_id)
        if result['flag'] == True:
            dropdown_definition = result['data']['dropdown_definition'] 
        else: 
            dropdown_definition = {}
    except:
        traceback.print_exc()
        dropdown_definition = {}
    
    columns_to_remove = ['attributes', 'password', 'status', 'id']
    columns_to_display = list(active_directory_df.columns)
    for element in columns_to_remove:
        columns_to_display.remove(element)
        
    if end_point > total_users:
        end_point = total_users
    if start_point == 1:
        pass
    else:
        start_point += 1
    
    pagination = {"start": start_point, "end": end_point, "total": total_users}
    
    try:
        field_definition_query = f"SELECT * FROM `field_definition` WHERE `status` = 1"
        field_definition_df = group_access_db.execute_(field_definition_query)
        field_definition_dict = field_definition_df.to_dict(orient= 'records')    
    except:
        traceback.print_exc()
        message = "Could not load from Active Directory"
        return jsonify({"flag": False, "message" : message})
    
    data = {
        "header" : columns_to_display,
        "rowdata" : active_directory_dict,
        "dropdown_definition": dropdown_definition,
        "pagination": pagination,
        "field_def": field_definition_dict
    }
    
    return jsonify({"flag": True, "data" : data})
        
def get_dropdown_definition(tenant_id):
    
    db_config = {
        'host': os.environ['HOST_IP'],
        'port': '3306',
        'user': 'root',
        'password': os.environ['LOCAL_DB_PASSWORD'],
        'tenant_id': tenant_id
    }

    group_access_db = DB('group_access', **db_config)
    try:
        attribute_dropdown_definition_query = f"SELECT `attribute_dropdown_definition`.*, `organisation_attributes`.`attribute` FROM `attribute_dropdown_definition`, `organisation_attributes` WHERE `attribute_dropdown_definition`.`attribute_id` = `organisation_attributes`.`id`"
        attribute_dropdown_definition_df = group_access_db.execute_(attribute_dropdown_definition_query)
        if attribute_dropdown_definition_df.empty:
            message = "No defintions present in Attribute Dropdown definition."
            return jsonify({"flag": False, "message" : message})       
    except:
        traceback.print_exc()
        message = "Could not load from Attribute Dropdown definition."
        return jsonify({"flag": False, "message" : message})
    
    dropdown_definition = {}
    try:
        for attribute in list(attribute_dropdown_definition_df['attribute'].unique()):
            attribute_value_arr = []
            attribute_id_df = attribute_dropdown_definition_df[attribute_dropdown_definition_df['attribute'] == attribute]
            for idx, row in attribute_id_df.iterrows():
                attribute_value_arr.append(row['value'])
            dropdown_definition = {**dropdown_definition, **{str(attribute) : attribute_value_arr}}
    except:
        traceback.print_exc()
        message = "Could not load convert Attribute Dropdown definition for UI."
        return jsonify({"flag": False, "message" : message})
    
    data= {
        "dropdown_definition": dropdown_definition
    }
    
    return {"flag": True, "data" : data}

@app.route("/modify_user", methods=['POST', 'GET'])
def modify_user():
    try:
        data = request.json
        logging.info(f'Request data in /modify_user: {data}')
        tenant_id = data.pop('tenant_id', None)
        operation = data.pop('operation').lower()
        row_data = data.pop('rowData')
    except:
        traceback.print_exc()
        message = "Received unexpected request data."
        return jsonify({"flag": False, "message" : message})
        
    db_config = {
        'host': os.environ['HOST_IP'],
        'port': '3306',
        'user': 'root',
        'password': os.environ['LOCAL_DB_PASSWORD'],
        'tenant_id': tenant_id
    }

    group_access_db = DB('group_access', **db_config)
    
    if operation == 'edit':
        result = edit_user(row_data, group_access_db)
        return jsonify(result)
    elif operation == 'delete':
        result = delete_user(row_data, group_access_db)
        return jsonify(result)
    elif operation == 'create':
        result = create_user(row_data, group_access_db)
        return jsonify(result)

@app.route("/attribute_definition", methods=['POST', 'GET'])
def attribute_definition():
    try:
        data = request.json
        logging.info(f'Request data in /attribute_definition: {data}')
        tenant_id = data.pop('tenant_id', None)
        flag = data.pop('flag')
    except:
        traceback.print_exc()
        message = "Received unexpected request data."
        return jsonify({"flag": False, "message" : message})
    
    db_config = {
        'host': os.environ['HOST_IP'],
        'port': '3306',
        'user': 'root',
        'password': os.environ['LOCAL_DB_PASSWORD'],
        'tenant_id': tenant_id
    }
    
    if flag == 'fetch':
        try:
            group_access_db = DB('group_access', **db_config)
            query = "SELECT `organisation_attributes`.*, `attribute_dropdown_definition`.`value` FROM `organisation_attributes`, `attribute_dropdown_definition` WHERE `organisation_attributes`.`id` = `attribute_dropdown_definition`.`attribute_id`"
            join_df = group_access_db.execute_(query)
            
            attributes = list(join_df['attribute'].unique())
            to_return = []
            for attribute in attributes:
                temp = {
                        'id': list(join_df[join_df['attribute'] == attribute].id)[0],
                        'attribute': attribute,
                        'value': list(join_df[join_df['attribute'] == attribute].value)
                        }
                to_return.append(temp)
        except:
            traceback.print_exc()
            message = f"Something went wrong while fetching attribute data."
            return jsonify({"flag": False, "message" : message})       
        return jsonify({"flag": True, "data" : to_return})   
    elif flag == 'save':
        try:
            attribute_data = data.pop('data')
            group_access_db = DB('group_access', **db_config)
            
            attribute_ui_df = pd.DataFrame(attribute_data)

            values_list = []
            values_arr = []
            for idx, row in attribute_ui_df.iterrows():
                for value in row['value']:        
                    values_arr.append(value)
                    values_list.append(f"('{row['id']}', '{value}')")
                    print(f"'{row['id']}',", f"'{value}'")

            values_string = ', '.join(values_list)

            user_mapping_query = "SELECT * FROM `user_organisation_mapping`"
            user_mapping_df = group_access_db.execute(user_mapping_query)

            
            if not user_mapping_df.empty:
                user_mapping_delete_query = "DELETE FROM `user_organisation_mapping`"
                user_mapping_ai_query = "ALTER TABLE `attribute_dropdown_definition` AUTO_INCREMENT=1"
                group_access_db.execute(user_mapping_delete_query)
                group_access_db.execute(user_mapping_ai_query)
                
            dropdown_delete_query = "DELETE FROM `attribute_dropdown_definition`"
            dropdown_ai_query = "ALTER TABLE `attribute_dropdown_definition` AUTO_INCREMENT=1"
            group_access_db.execute(dropdown_delete_query)
            group_access_db.execute(dropdown_ai_query)

            organisation_heirarchy_delete_query = "DELETE FROM `organisation_hierarchy`"
            organisation_heirarchy_ai_query = "ALTER TABLE `organisation_hierarchy` AUTO_INCREMENT=1"
            group_access_db.execute(organisation_heirarchy_delete_query)
            group_access_db.execute(organisation_heirarchy_ai_query)

            organisation_attribute_delete_query = "DELETE FROM `organisation_attributes`"
            organisation_attribute_ai_query = "ALTER TABLE `organisation_attributes` AUTO_INCREMENT=1"
            group_access_db.execute(organisation_attribute_delete_query)
            group_access_db.execute(organisation_attribute_ai_query)

            organisation_attribute_df = attribute_ui_df.drop(columns= ['value'])
            organisation_attribute_df.to_sql(name= 'organisation_attributes', con = group_access_db.engine, if_exists='append', index= False, method= 'multi')

            organisation_heirarchy_df = attribute_ui_df.drop(columns= ['value', 'attribute']).rename(columns={'id': 'parent_id'})
            organisation_heirarchy_df.to_sql(name= 'organisation_hierarchy', con = group_access_db.engine, if_exists='append', index= False, method= 'multi')

            query = f"INSERT INTO `attribute_dropdown_definition` (`attribute_id`, `value`) VALUES {values_string}"
            group_access_db.execute(query)

            user_mapping_join_df = user_mapping_df[user_mapping_df['organisation_attribute'].isin(list(attribute_ui_df['id'])) & user_mapping_df['value'].isin(values_arr)]

            if not user_mapping_join_df.empty:
                user_mapping_join_df.to_sql(name= 'user_organisation_mapping', con = group_access_db.engine, if_exists='append', index= False, method= 'multi')    
        except:
            message = f"Something went wrong"
            return jsonify({"flag": False, "message" : message})    
        message = f"Successfully updated attribute definition tables for tenant id {tenant_id}"
        return jsonify({"flag": True, "message" : message})

#Put this in a separate microservice
@app.route('/get_action_table/<action_table_id>', methods=['POST', 'GET'])
def get_action_table(action_table_id = None):
    if action_table_id is None:
        message = f'Action Table ID not provided.'
        logging.error(message)
        return jsonify({'flag': False, 'message': message})

    try:
        action_table_id = int(action_table_id)
    except ValueError:
        message = f'Invalid Action Table. Expected Action Table to be integer. Got {action_table_id}.'
        logging.exception(message)
        return jsonify({'flag': False, 'message': message})
    
    
    try:
        data = request.json
        tenant_id = data.pop('tenant_id', None)

        at_db = DB('queues', tenant_id=tenant_id, **db_config)
        at_def_query = f"SELECT * FROM `action_table_definition` WHERE `id` = '{action_table_id}'"
        at_def_df = at_db.execute_(at_def_query)
        
        at_columns_query = f"SELECT * FROM `action_table_columns` WHERE FIND_IN_SET('{action_table_id}', mapping) > 0 ORDER BY `display_order` ASC"
        at_columns_df = at_db.execute_(at_columns_query)
        
        at_buttons_query = f"SELECT * FROM `action_table_buttons` WHERE FIND_IN_SET('{action_table_id}', mapping) > 0 ORDER BY `display_order` ASC"
        at_buttons_df = at_db.execute_(at_buttons_query)
                
        columns_dict = at_columns_df.to_dict(orient= 'records')
        
        for idx, row in enumerate(columns_dict):
            if row['type'] == 'button':
                match_df = at_buttons_df[at_buttons_df['button_name'] == row['unique_name']]
                if not match_df.empty:
                    columns_dict[idx] = {**match_df.to_dict(orient= 'records')[0], **row}
                else:
                    message = f"In-table {row['unique_name']} button  not defined in action table buttons"
                    jsonify({"flag": False, "message" : message})
                    
        to_return = {
                **{
                "columns" : columns_dict,
                "buttons" : at_buttons_df.to_dict(orient= 'records'),
                }, **at_def_df.to_dict(orient= 'records')[0]
                }
    except:
        traceback.print_exc()
        message = f'Something went wrong check logs.'
        return jsonify({"flag": False, "message" : message})
    
    return jsonify({"flag": True, "data" : to_return})

@app.route("/get_queue_definition", methods=['POST', 'GET'])     
def get_queue_definition():
    try:
        try:
            data = request.json
            tenant_id = data['tenant_id']
        except:
            traceback.print_exc()
            message = f'tenant_id not received.'
            return jsonify({'flag' : False, 'message': message})

        queues_db = DB('queues', tenant_id=tenant_id,**db_config)
        kafka_db = DB('kafka', tenant_id=tenant_id,**db_config)
        
        queues_query = f"SELECT * FROM `queue_definition`"
        queues_df = queues_db.execute_(queues_query)
        queues_arr = queues_df.to_dict(orient= 'records')
        
        button_functions_query = f"SELECT * FROM `button_functions`"
        button_functions_df = queues_db.execute_(button_functions_query)
        button_functions_arr = button_functions_df.to_dict(orient= 'records')
        
        button_definition_query = f"SELECT * FROM `button_definition`"
        button_definition_df = queues_db.execute_(button_definition_query)
        button_definition_arr = button_definition_df.to_dict(orient= 'records')
        
        workflow_query = f"SELECT * FROM `workflow_definition`"
        workflow_df = queues_db.execute_(workflow_query)
        workflow_arr = workflow_df.to_dict(orient= 'records')
        
        kafka_query = f"SELECT * FROM `grouped_message_flow`"
        kafka_df = kafka_db.execute_(kafka_query)
        kafka_arr = kafka_df.to_dict(orient= 'records')
        
        for idx, row in enumerate(button_definition_arr):
            group_rows = kafka_df[kafka_df['message_group'] == row['text']]
            functions = list(dict.fromkeys(list(group_rows['listen_to_topic']) + list(group_rows['send_to_topic'])))
            button_definition_arr[idx]['functions'] = functions
            source_id = list(workflow_df[workflow_df['button_id'] == row['id']].queue_id)[0]
            source_queue = list(queues_df[queues_df['id'] == source_id].unique_name)[0]
            target_id = list(workflow_df[workflow_df['button_id'] == row['id']].move_to)[0]
            target_queue = list(queues_df[queues_df['id'] == target_id].unique_name)[0]
            button_definition_arr[idx]['source'] = source_queue
            button_definition_arr[idx]['target'] = target_queue            
        
        button_functions_dict = {}
        for idx, row in button_functions_df.iterrows():
            button_functions_dict[row['route']] = button_functions_arr[idx]
        
        to_return = {
                'queues_arr': queues_arr,
                'buttons_arr': button_definition_arr,
                'button_function': button_functions_dict
                    }
    except:
        traceback.print_exc()
        message = f'Something went wrong. Check Logs'
        return ({'flag': False, 'message': message})
    
    return jsonify({'flag': True, 'data': to_return})

#Put this in a separate microservice
@app.route('/queue_definition', methods=['POST', 'GET'])
def queue_definition():
    data = request.json
    print(data)
    try:
        queues_data_ui = data['data']['queues_arr']
        buttons_data_ui = data['data']['buttons_arr']
        button_function_data_ui = data['data']['button_function']
        tenant_id = data.pop('tenant_id', None)
    except:
        message = f'Received unexpected data from UI'
        return jsonify({'flag': False, 'message': message})

    queues_db = DB('queues', tenant_id=tenant_id,**db_config)
    kafka_db = DB('kafka', tenant_id=tenant_id,**db_config)
    
    try:
        queues_data_df = pd.DataFrame(queues_data_ui)
        queue_defintion_delete_query = f'DELETE FROM `queue_definition`'
        queues_db.execute(queue_defintion_delete_query)
        queues_data_df.to_sql(name= 'queue_definition', con = queues_db.engine, if_exists='append', index= False, method= 'multi')
        
        button_definition_df = pd.DataFrame(buttons_data_ui)
        button_definition_df = button_definition_df[['id','text', 'color','confirmation','confirmation_message']]
        button_definition_delete_query = f'DELETE FROM `button_definition`'
        queues_db.execute(button_definition_delete_query)
        button_definition_df.to_sql(name= 'button_definition', con = queues_db.engine, if_exists='append', index= False, method= 'multi')
    
        button_functions_arr = []
        for key, value in button_function_data_ui.items():
            button_functions_arr.append(value)
        button_function_df = pd.DataFrame(button_functions_arr)
        button_function_delete_query = f'DELETE FROM `button_functions`'
        queues_db.execute(button_function_delete_query)
        button_function_df.to_sql(name= 'button_functions', con = queues_db.engine, if_exists='append', index= False, method= 'multi')
    
        #Workflow definition
        workflow_arr = []
        kafka_arr = []
        
        for idx, row in pd.DataFrame(buttons_data_ui).iterrows():
            workflow_dict = {
                             'queue_id': list(queues_data_df[queues_data_df['unique_name'] == row['source']].id)[0],
                             'button_id': row['id'],
                             'move_to': list(queues_data_df[queues_data_df['unique_name'] == row['target']].id)[0]
                             }
            workflow_arr.append(workflow_dict)
            
            #Kafka grouped message flow
            if len(row['functions']) == 1:
                kafka_dict = {
                        'listen_to_topic': row['functions'][0], 
                        'send_to_topic': None,
                        'message_group': row['text']
                            }
                kafka_arr.append(kafka_dict)
            else:
                for idx in range(len(row['functions'])-1):
                    kafka_dict = {
                            'listen_to_topic': row['functions'][idx], 
                            'send_to_topic': row['functions'][idx+1],
                            'message_group': row['text']
                                }
                    kafka_arr.append(kafka_dict)                
        
        workflow_df = pd.DataFrame(workflow_arr)
        kafka_df = pd.DataFrame(kafka_arr)
        
        workflow_delete_query = "DELETE FROM `workflow_definition`"
        workflow_ai_query = "ALTER TABLE `workflow_definition` AUTO_INCREMENT=1"
        
        queues_db.execute(workflow_delete_query)
        queues_db.execute(workflow_ai_query)
        
        kafka_delete_query = "DELETE FROM `grouped_message_flow`"
        kafka_ai_query = "ALTER TABLE `grouped_message_flow` AUTO_INCREMENT=1"
        
        kafka_db.execute(kafka_delete_query)
        kafka_db.execute(kafka_ai_query)
        
        workflow_df.to_sql(name= 'workflow_definition', con = queues_db.engine, if_exists='append', index= False, method= 'multi')
        kafka_df.to_sql(name= 'grouped_message_flow', con = kafka_db.engine, if_exists='append', index= False, method= 'multi')
        
    except:
        traceback.print_exc()
        message = f'Something went wrong. Check Logs'
        return jsonify({'flag': False, 'message': message})
    
    message = f'Successfuly updated workflow related tables in database.'
    return jsonify({'flag': True, 'message': message})

#Put this in a separate microservice
@app.route('/download_excel_blob', methods = ['GET', 'POST'])
def download_excel_blob():
    try:
        data = request.json
        tenant_id = data.pop('tenant_id', None)
        file_name = data['file'] + '.xlsx'
    except:
        traceback.print_exc()
        message = f'File name not received'
        return jsonify({"flag": False, "message" : message})
    source = '/var/www/user_management/app/excel_templates_input'
    strfile = os.path.join(source,file_name )
    xl = pd.ExcelFile(strfile)
    sheet_names=xl.sheet_names  # see all sheet names

    list_columns=[]
    for sheet in sheet_names:
        if 'm#' in sheet.split('_')[0]:
            master = sheet
            table_name = '_'.join(sheet.split('_')[1:])
            #print('table name', table_name)
            df_master=xl.parse(master)#
            df_master['Index']=df_master['Index'].fillna('null')
            for ind in df_master.index: 
                column=str(df_master['Name'][ind])+' '+str(df_master['Type'][ind])+' '+'('+str(int(df_master['Length'][ind]))+')'+' '+str(df_master['Index'][ind])
                list_columns.append(column)
                #print(list_columns)
            list_columns_final = ', '.join(list_columns)
            #print('list_columns_final', list_columns_final)
            database = df_master['database'][0]
            db = DB(database, tenant_id=tenant_id,**db_config)
            # db.execute(r"create database if not exists {0} ".format(database))
            try:
                db.execute(r'create table  if not exists '+table_name+'('+list_columns_final+')')
            except sqlalchemy.exc.OperationalError as err:
                message="Something went wrong: {}".format(err)
                return jsonify({"flag": False, "message" : message})   
            except sqlalchemy.exc.IntegrityError as err1:
                message='duplicate entry:{}'.format(err1)
                return jsonify({"flag": False, "message" : message})  
            query='select * from '+' '+table_name
            df =db.execute_(query)  #USE DB UTILS
            #print('df', df)
            bio = BytesIO()
            writer = pd.ExcelWriter(bio)
            for sheet in xl.sheet_names:
                if sheet == table_name:
                    df.to_excel(writer, index= False, sheet_name = table_name)
                xl.parse(sheet).to_excel(writer, index= False, sheet_name = sheet) 
            writer.save()
            bio.seek(0)
            blob_data = base64.b64encode(bio.read())
    return jsonify({"flag": True, "blob" : blob_data.decode('utf-8'), 'file_name' : file_name})

@app.route('/upload_excel_blob', methods = ['GET', 'POST'])
def upload_excel_blob():
    data= request.json
    print(data)
    try:
        blob_data = data['blob']
        tenant_id = data.get('tenant_id', None)
    except:
        message = f'Blob data not received'
        return jsonify({"flag": False, 'message': message})
    try:
        blob_data = blob_data.replace("data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,", "")
        #Padding
        blob_data += '='*(-len(blob_data)%4)
        file_stream = BytesIO(base64.b64decode(blob_data))
        xll = pd.ExcelFile(file_stream)
        for sheet in xll.sheet_names:
            if 'mstr' in sheet.split('_')[0]:
                master = sheet
                table_name = '_'.join(sheet.split('_')[1:])
                #print('table name', table_name)
                df_master=xll.parse(master)
        #print(xll.sheet_names)
        for sheet in xll.sheet_names:
            if sheet ==table_name:
                df_to_insert=xll.parse(sheet)
                #print(df_to_insert)
            else:
                df_s=xll.parse(sheet)
                #print(df_s)
        #deleting data in table
        database = df_master['database'][0]

        db = DB(database,tenant_id=tenant_id,**db_config)
        query='delete from'+' '+table_name
        db.execute(query)
        df_to_insert.to_sql(table_name, con=db.engine, if_exists='append', index=False, method= 'multi')
    except:
        message = f"Something went wrong. Check logs."
        return jsonify({"flag": False, "message" : message})    
    message=f"Sucessfully inserted into the database"
    return jsonify({"flag": True, "message" : message})

@app.route("/show_existing_reports", methods=['POST', 'GET'])
def show_existing_reports():
    try:
        data = request.json
        logging.info(f'Request data: {data}')
        tenant_id = data.pop('tenant_id', None)
    except:
        traceback.print_exc()
        message = "Received unexpected request data."
        return jsonify({"flag": False, "message" : message})

    reports_db= DB('reports', tenant_id=tenant_id,**db_config)
    try:
        reports_query=f"select * from `report_types`"
        reports_type_df = reports_db.execute_(reports_query)
        if reports_type_df.empty:
            message = "No reports present in report_types"
            return jsonify({"flag": False, "msg" : message})    
    except:
        traceback.print_exc()
        message = "Could not load from report_types"
        return jsonify({"flag": False, "msg" : message})
    report_ids =','.join([json.dumps(str(x)) for x in list(reports_type_df['id'])])
    print(report_ids)
    reports_type_dict = reports_type_df.to_dict(orient= 'records')
    print(reports_type_dict)
    columns_to_display = list(reports_type_df.columns)
    data = {
    "header" : columns_to_display,
    "rowdata" : reports_type_dict,  
    }
    return jsonify({"flag": True, "data" : data})

@app.route("/modify_reports", methods=['POST', 'GET'])     
def modify_reports():
    try:
        data = request.json
        tenant_id = data.pop('tenant_id', None)
        operation = data.pop('operation').lower()
        row_data = data.pop('rowData')
    except:
        traceback.print_exc()
        message = "Received unexpected request data."
        return jsonify({"flag": False, "msg" : message})

    reports_db = DB('reports', tenant_id=tenant_id,**db_config)
    if operation == 'edit':
        result = edit_report(row_data, reports_db)
        return jsonify(result)
    elif operation == 'delete':
        result = delete_report(row_data, reports_db)
        return jsonify(result)
    elif operation == 'create':
        result = create_report(row_data, reports_db)
        return jsonify(result)

@app.route("/builder_stats", methods=['POST', 'GET'])     
def builder_stats():
    try:
        data = request.json
        tenant_id = data['tenant_id']
        flag = data['flag']
    except:
        traceback.print_exc()
        message = "Recevied unexpected data"
        return jsonify({"flag": False, "message" : message})    
    
    stats_db = DB('stats', tenant_id=tenant_id,**db_config)
    group_access_db = DB('group_access', tenant_id=tenant_id, **db_config)
    if flag == 'fetch':
        try:
            query = f"SELECT * FROM `stats_master`"
            stats_master_df = stats_db.execute_(query)
            stats_master_dict = stats_master_df.to_dict(orient= 'records')
            
            access_query = f"SELECT * FROM `stats_access"
            access_df = group_access_db.execute_(access_query)

            group_def_query = f"SELECT * FROM `group_definition`"
            group_def_df = group_access_db.execute_(group_def_query)
            groups_dropdown_list = list(group_def_df.id)
            
            for idx, row in enumerate(stats_master_dict):
                stats_master_dict[idx] = {**stats_master_dict[idx], **{'access_groups': list(access_df[access_df['stats_id'] == row['id']].group_id)}}

            return jsonify({"flag": True, "data" : {"data": stats_master_dict, "groups_dropdown_list": groups_dropdown_list}})
        except:
            traceback.print_exc()
            message = f'Something went wrong while fetching stats'
            return jsonify({"flag": False, "message" : message})
    elif flag == 'save':
        try:
            stats_dict = data['data']
        except:
            traceback.print_exc()
            message = "No data received to update"
            return jsonify({"flag": False, "message" : message}) 
        try:
            delete_query = "DELETE FROM `stats_access`"
            ai_query = "ALTER TABLE `stats_access` AUTO_INCREMENT=1"
            group_access_db.execute(delete_query)
            group_access_db.execute(ai_query)  
            delete_query = "DELETE FROM `stats_master`"
            ai_query = "ALTER TABLE `stats_master` AUTO_INCREMENT=1"
            stats_db.execute(delete_query)
            stats_db.execute(ai_query)    
            groups_arr = []
            for idx, row in enumerate(stats_dict):
                groups_list = stats_dict[idx].pop("access_groups", [])
                for group_id in groups_list:
                    groups_arr.append({"group_id" : group_id, "stats_id": row["id"]})

            result = stats_db.execute_(generate_multiple_insert_query(stats_dict,'stats_master'))
            if result: 
                result = group_access_db.execute_(generate_multiple_insert_query(groups_arr, "stats_access") )
                if result:
                    message = f'Updated stats master and stats_access'
                return jsonify({"flag": True, "message" : message})
                else:
                    message = f"Something went wrong while updating stats access"
                    return jsonify({"flag": False, "message" : message})
            else:
                message = f"Something went wrong while updating stats master"
                return jsonify({"flag": False, "message" : message})
        except:
            traceback.print_exc()               
            message = f"Something went wrong while updating stats master"
            return jsonify({"flag": False, "message" : message})

@app.route("/get_tenant_info", methods=['POST', 'GET'])
def get_tenant_info():
    try:
        data = request.json
        tenant_id = data['tenant_id']
    except:
        traceback.print_exc()
        message = "tenant_id not received"
        return jsonify({"flag": False, "message" : message})    

    tenant_master_db = DB('tenant_master',**db_config)
    
    try:
        query = f"SELECT * FROM `tenant_information` WHERE `Tenant Name` = '{tenant_id}'"
        tenant_info_df = tenant_master_db.execute_(query)
        if not tenant_info_df.empty:
            tenant_info_dict = tenant_info_df.to_dict(orient= 'records')[0]
            return jsonify({"flag": True, "data" : tenant_info_dict})
        else:
            message = f"No record in DB for tenant_id : {tenant_id}"
            return jsonify({"flag": False, "message" : message})
    except sqlalchemy.exc.IntegrityError as err:
         message = f"something went wrong {err}"
         return jsonify({"flag": False, "message" : message})
    
@app.route('/builder_queues', methods=['POST', 'GET'])
def builder_queues():
    try:
        try:
            data = request.json
            tenant_id = data['tenant_id']
        except:
            traceback.print_exc()
            message = "tenant_id not received"
            return jsonify({"flag": False, "message" : message})

        queues_db = DB('queues',tenant_id=tenant_id, **db_config)
        
        queues_query = f"SELECT * FROM `queue_definition`"
        queues_df = queues_db.execute_(queues_query)
        
        max_level = queues_df['level'].max()
        
        queues_arr = []
        for n in range(1, max_level +1):          
            level_n = queues_df[(queues_df['level'] == n) & (queues_df['child'] == 'no')]
            for idx, row in level_n.iterrows():
                queues_arr.append( {
                        'id': row['id'],
                        'name':row['name'],
                        'unique_name': row['unique_name']
                            })
        
        message = f'Successfully fetched queue details'
        
        layout_query = f"SELECT * FROM `layout_definition`"
        layout_df = queues_db.execute_(layout_query)

        queue_names = list(layout_df['queue_unique_name'].unique())

        layout_dict = {}
        for queue_name in queue_names:
            layout_dict[queue_name] = layout_df[layout_df['queue_unique_name'] == queue_name].drop(columns = 'queue_unique_name').to_dict(orient= 'records')

        return jsonify({'flag': True, 'data': {'queues_arr': queues_arr, 'layout': layout_dict}})
    except:
        traceback.print_exc()
        message = 'Something went wrong while fetching data. Check logs.'
        return jsonify({'flag': False, 'message': message})

@app.route("/save_layout_definition", methods=['POST', 'GET'])
def save_layout_definition():
    try:
        data = request.json
        tenant_id = data.pop('tenant_id', None)
        ui_data = data.pop('data')
    except:
        traceback.print_exc()
        message = "Received unexpected request data."
        return jsonify({"flag": False, "message" : message})

    queues_db = DB('queues',tenant_id=tenant_id, **db_config)
    engine = queues_db.engine
    Session = sessionmaker(bind = engine)
    session = Session()
    try:
        delete_query = f'DELETE FROM `layout_definition`'
        engine.execute(delete_query)
        ai_query = "ALTER TABLE `layout_definition` AUTO_INCREMENT=1"
        session.execute(ai_query)
    except:
        message= f'something went wrong while deletion of previous_data in layout_defintion'
        return jsonify({"flag": False, "message" : message})
    try:
        rows_arr = []
        for queue_unique_name, rows in ui_data.items():
            for row in rows:
                rows_arr.append({**row, **{'queue_unique_name': queue_unique_name}})
        insert_query = generate_multiple_insert_query(rows_arr, 'layout_definition')  
        session.execute(insert_query)
        message=f'sucessfully inserted data in layout_definition'
        session.commit()
        session.close()
        return jsonify({"flag": True, "message":message })
    except:
        traceback.print_exc()
        session.rollback()
        print('rolling back')
        session.close()
        print('closing session')
        message = f"Something went wrong while inserting the data in layout_definition"
        return {"flag": False, "message" : message}

@app.route("/bank_master_trigger", methods=['POST', 'GET'])
def bank_master_trigger():
    try:
        data = request.json
        logging.info(f'Request data: {data}')
        tenant_id = data.pop('tenant_id', None)
    except:
        traceback.print_exc()
        message = "Received unexpected request data."
        return jsonify({"flag": False, "message" : message})

    try:
        start_point = data['start'] - 1
        end_point = data['end']
        offset = end_point - start_point
    except:
        start_point = 0
        end_point = 20
        offset = 20

    db = DB('extraction',tenant_id=tenant_id,**db_config)
    total_rows = list(db.execute_(f"SELECT COUNT(*) FROM `bank_master`")['COUNT(*)'])[0]
    query_ = f"SELECT `ID`, `Bank name`, `Bank URL`, `Account number`, `A/c Type`, `bot_trigger` FROM `bank_master` LIMIT {start_point}, {offset}"
    list_ = db.execute_(query_)
    list_ = list_.to_dict(orient = "records")
    logging.debug(f"Data recevied:  {list_} ")
    values_ = []
    for i in list_:
        temp = {}
        if i['bot_trigger'] == 0 :
            status = "Bot is not running"
        elif i['bot_trigger'] == 1 :
            status = "Bot is running"
        elif i['bot_trigger'] == -1:
            status = "Trigger failed"
        else:
            status = None
        
        temp["ID"] = i['ID']
        temp["Bank_name"] = i['Bank name']
        temp["Bank_URL"] = i['Bank URL']
        temp["Account_number"] = i['Account number']
        temp["A/c_Type"] = i['A/c Type']
        temp["bot_trigger"] = status
        values_.append(temp)

    if end_point > total_rows:
        end_point = total_rows
    if start_point == 1:
        pass
    else:
        start_point += 1
    
    pagination = {"start": start_point, "end": end_point, "total": total_rows}
    
    data = {
        "rowdata" : values_,
        'pagination': pagination
    }
    
    final_ = {}
    final_["flag"] = True
    final_["data"] = data

    return final_

@app.route("/bot_button_trigger_accept", methods=['POST', 'GET'])
def bot_button_trigger_accept():
    try:
        try:
            data = request.json
            logging.info(f'Request data: {data}')
            tenant_id = data.pop('tenant_id', None)
        except:
            traceback.print_exc()
            message = "Received unexpected request data."
            return jsonify({"flag": False, "message" : message})

        rowdata = data["data"]
        if len(rowdata) == 0:
            return {"flag": False, "message":"Select atleast one"}

        db = DB('extraction',tenant_id=tenant_id,**db_config)
        
        for i in rowdata:
            query_ = f"update `bank_master` set `bot_trigger` = 1 where id = {i}"
            db.execute(query_)

    except Exception as e:
        logging.exception(f"Unexpected error in bot_button_trigger_accept{e}")

    return {"flag": True, "message":"Selected Bots called"}

@app.route('/upload_dropdown_definition', methods = ['GET', 'POST'])
def upload_dropdown_definition():
    data = request.json
    tenant_id = data.pop('tenant_id', None)
    try:
        blob_data = data.pop('blob')
    except:
        traceback.print_exc()
        message = f"Blob data not provided"
        return jsonify({"flag": False, "message" : message})
    db_config = {
        'host': os.environ['HOST_IP'],
        'port': '3306',
        'user': 'root',
        'password': os.environ['LOCAL_DB_PASSWORD'],
        'tenant_id': tenant_id
    }
    database = 'test2'
    group_access_db = DB(database,**db_config)
    engine = group_access_db.engine
    try: 
        usr_org_map_query=f"SELECT * FROM `user_organisation_mapping`"
        usr_org_map_df=group_access_db.execute_(usr_org_map_query)
        #print( usr_org_map_df)
        usr_org_map_del_query=f"delete from `user_organisation_mapping`"
        engine.execute(usr_org_map_del_query)
        ai_query = "ALTER TABLE `user_organisation_mapping` AUTO_INCREMENT=1"
        engine.execute(ai_query)
    except:
        traceback.print_exc()
        message= f'something went wrong while deletion of previous_data in user organisation mapping'
        return jsonify({"flag": False, "message" : message})
    try:
        attr_dp_def_del_query=f"delete from `attribute_dropdown_definition`"
        engine.execute(attr_dp_def_del_query)
        ai_query = "ALTER TABLE `attribute_dropdown_definition` AUTO_INCREMENT=1"
        engine.execute(ai_query)
    except:
        traceback.print_exc()
        message= f'something went wrong while deletion of previous_data in attribute_dropdown_definition'
        return jsonify({"flag": False, "message" : message})
    try:
        org_hierarchy_del_query=f"delete from `organisation_heirarchy`"
        engine.execute(org_hierarchy_del_query)
        ai_query = "ALTER TABLE `organisation_heirarchy` AUTO_INCREMENT=1"
        engine.execute(ai_query)
    except:
        traceback.print_exc()
        message= f'something went wrong while deletion of previous_data in organisation_heirarchy'
        return jsonify({"flag": False, "message" : message})
    try:
        org_attr_del_query=f"delete from `organisation_attributes`"
        engine.execute(org_attr_del_query)
        ai_query = "ALTER TABLE `organisation_attributes` AUTO_INCREMENT=1"
        engine.execute(ai_query)
    except:
        traceback.print_exc()
        message= f'something went wrong while deletion of previous_data in organisation_attributes'
        return jsonify({"flag": False, "message" : message})
    #blob to dataframe
    try:
        #blob_data = blob_data.decode('utf-8')
        blob_data = blob_data.replace("data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,", "")
        #Padding
        blob_data += '='*(-len(blob_data)%4)
        file_stream = BytesIO(base64.b64decode(blob_data))
        data_frame = pd.read_excel(file_stream)
        data_frame.fillna(value= '', inplace=True)
        print(data_frame)
    except:
        traceback.print_exc()
        message = f"Could not convert blob to dataframe"
        return jsonify({"flag": False, "message" : message})
    #insertion of data to organisation_attributes
    try: 
        attribute_names = list(data_frame['attribute_name'].unique())
        org_attr_dict = []
        for idx,i in enumerate(attribute_names):
             org_attr_dict.append({'id': idx+1, 'attribute': i})
        #print('org_attr_dict',org_attr_dict)
        org_attr_df=pd.DataFrame(org_attr_dict)
        org_attr_df.to_sql('organisation_attributes', con=engine, if_exists='append', index=False, index_label='id')
    except:
        traceback.print_exc()
        message= f'something went wrong while inserting data to organisation_attributes'
        return jsonify({"flag": False, "message" : message})
    #insertion of data to organisation hierarchy
    try:
        org_hier_query=f'INSERT INTO `organisation_heirarchy`(`parent_id`) SELECT (`id`) FROM `organisation_attributes`'
        org_hier_df=group_access_db.execute_(org_hier_query) 
        #print(org_hier_df)
    except:
        traceback.print_exc()
        message= f'something went wrong while inserting data to organisation_hierarchy'
        return jsonify({"flag": False, "message" : message})
    #insertion of data to attrbute_dropdown defintion
    try:
         attr_id= {attribute_names[i]:i+1  for i in range(len(attribute_names) ) }
         def func(row):
             row['attribute_id'] = attr_id[str(row['attribute_name'])]
             return row
         orginal_df=data_frame.apply(func, axis=1)
         columns=['id','attribute_id','value']
         attr_dpdn_def_df=pd.DataFrame(columns=columns)
         attr_dpdn_def_df=attr_dpdn_def_df[['id','attribute_id','value']]=orginal_df[['id','attribute_id','value']]
         attr_dpdn_def_df.to_sql('attribute_dropdown_definition', con=engine, if_exists='append', index=False, index_label='id')
    except:
        traceback.print_exc()
        message= f'something went wrong while inserting data to attribute_dropdown_definition'
        return jsonify({"flag": False, "message" : message})
    try:
       id_list=list(org_attr_df['id'])
       attr_dpdn_query=f"select * from `attribute_dropdown_definition`"
       attr_dpdn_df=group_access_db.execute_(attr_dpdn_query)
       value_list=list(attr_dpdn_df['value'])
       columns=['user_id','organisation_attribute','value']
       usr_org_mapping_df=pd.DataFrame(columns=columns)
       for i,row in usr_org_map_df.iterrows():
           if (row['organisation_attribute'] in id_list) and (row['value']in value_list):
                   usr_org_mapping_df=usr_org_mapping_df.append(row)
       usr_org_mapping_df.to_sql('user_organisation_mapping', con=engine, if_exists='append', index=False, index_label='id')
       message= f'Inserted data to user_organisation_mapping'
       return jsonify({"flag": True, "message" : message})
    except:
        traceback.print_exc()
        message= f'something went wrong while inserting data to user_organisation_mapping'
        return jsonify({"flag": False, "message" : message})

@app.route('/download_dropdown_definition', methods = ['GET', 'POST'])
def download_dropdown_definition():
    try:
       data = request.json
       tenant_id = data.pop('tenant_id', None)
    except:
        traceback.print_exc()
        message= f'data_not recieved in  correct format'
        return jsonify({"flag": False, "message" : message})
    try:
       db_config = {
        'host': os.environ['HOST_IP'],
        'port': '3306',
        'user': 'root',
        'password': os.environ['LOCAL_DB_PASSWORD'],
        'tenant_id': tenant_id
                    }
       database = 'test2'
       group_access_db = DB(database,**db_config)
       attr_dpdn_query=f"select * from `attribute_dropdown_definition`"
       attr_dpdn_df=group_access_db.execute_(attr_dpdn_query)
       #print(attr_dpdn_df)
       org_attr_query=f"select * from `organisation_attributes`"
       org_attr_df=group_access_db.execute_(org_attr_query)
       #print(org_attr_df)
       org_attr_lst_dict=org_attr_df.to_dict(orient='records')
       attribute_names_df=org_attr_df['attribute']
       attr_ids= {i+1:attribute_names_df[i]  for i in range(len(attribute_names_df) ) }
       def func(row):
             row['attribute_name'] = attr_ids[(row['attribute_id'])]
             return row
       orginal_df=attr_dpdn_df.apply(func, axis=1)
       #print(orginal_df)
       columns=['id','attribute_name','value']
       data_frame=pd.DataFrame(columns=columns)
       data_frame=data_frame[['id','attribute_name','value']]=orginal_df[['id','attribute_name','value']]
       #blob_data = dataframe_to_blob(data_frame)
       bio = BytesIO()
       writer = pd.ExcelWriter(bio)
       data_frame.to_excel(writer, index= False, sheet_name ='attribute_dropdown_definition')
       writer.save()
       bio.seek(0)
       blob_data = base64.b64encode(bio.read())
       return jsonify({"flag": True, "blob" : blob_data.decode('utf-8')})
    except:
       traceback.print_exc()
       message= f'something went wrong while converting to blob'
       return jsonify({"flag": False, "message" : message}) 
