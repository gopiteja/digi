import sqlalchemy as sql
import pandas as pd
import db_utils as db
import BusinessRules
import json
import os

import pandas as pd
import sqlalchemy as sql
import MySQLdb
import logging

def execute_query(query, database, host='127.0.0.1', user='root', password='', port='3306'):
    host = os.environ['HOST_IP']
    password = os.environ['LOCAL_DB_PASSWORD']
    connect_string = f'mysql://{user}:{password}@{host}/{database}'
    sql_engine = sql.create_engine(connect_string)
    df = []
    try:
        df = pd.read_sql_query(query, sql_engine)
    except sql.exc.ResourceClosedError:
        print ("QUERY OTHER THAN SELECT")
    sql_engine.dispose()
    return df

def get_tables_data(unique_column=None, unique_column_value=None, db_tables={}):
    
    to_return = {}

    for key, tables_ in db_tables.items():
        for table in tables_:
            if unique_column and unique_column_value:
                query = f'SELECT * from `{table}` WHERE `{unique_column}` = "{unique_column_value}"'
            df = execute_query(query, key)
            if not df.empty:
                to_return[table] = df.to_dict(orient='records')[0]
            else:
                to_return[table] = {}
    return to_return

def join_update(updates):
    update = []

    for field, value in updates.items():
        temp = ''
        if type(value) is str:
            temp = f'`{field}` = "{value}"'
        else:
            temp = f'`{field}` = {value}'
        update.append(temp)

    update = ', '.join(update)

    return update

def update_table(table, to_update, unique_column, unique_column_value, database='alorica_data'):
    updates = join_update(to_update)
    query = f'UPDATE `{table}` SET {updates} WHERE `{unique_column}` = "{unique_column_value}"'
    print (query)
    execute_query(query, database)
    return "UPDATED IN DB"

def update(table_updates, unique_id):
    for table,column_values in table_updates.items():
        # as of now hardcode ...actully find the database name
        if table == 'process_queue':
            db = 'queues'
            update_table(table, column_values, 'case_id', unique_id,  db)
        else:
            db = 'extraction'
            update_table(table, column_values, 'case_id', unique_id,  db)
    return "UPDATED SUCCESSFULLY"
   
def get_validation_rules(data_base, group=None):
    """
        Getting the rule_string, next_if_sucess and next_if_failure data from the database
    """
    
    business_rule_db = db.DB(data_base)
    if group:
        df = business_rule_db.execute(f"SELECT `id`,`rule_string` from `sequence_rule_data` WHERE `group`= '{group}'")
    else:
        df = business_rule_db.execute(f"SELECT `id`,`rule_string` from `sequence_rule_data`")
#     print (df.to_dict(orient='records'))
    chained_rules = [e['rule_string'] for e in df.to_dict(orient='records')]
    return chained_rules

def apply_field_validations(unique_id, stage='validation', db_tables = {
                "extraction" : ["ocr"],
                "queues":["process_queue"]

            }):
    
    data = get_tables_data('case_id', unique_id, db_tables)
    rules = [json.loads(rule) for rule in get_validation_rules('business_rules', stage)]
    BR  = BusinessRules.BusinessRules(unique_id, rules, data)
    updates = BR.evaluate_business_rules()
    update(updates, unique_id)
    
    
    return updates

