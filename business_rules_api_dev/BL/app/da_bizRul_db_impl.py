"""
@Author : Akshat Goyal
"""

import pdb
from flask import jsonify

try:
    from app.db_utils import DB
    from app.da_bizRul_abc import BusinessRulesDAOABC
except:
    from db_utils import DB
    from da_bizRul_abc import BusinessRulesDAOABC


business_rules_db_config = {
        'host': 'business_rules_db',
        'port': 3306,
        'user': 'root',
        'password': 'root'
    }

db_config = {
            'host': '172.31.45.112',
            'port': 3306,
            'user': 'root',
            'password': ''
        }

queue_db_config = {
            'host': '172.31.45.112',
            'port': 3306,
            'user': 'root',
            'password': ''
        }

common_db_config = {
        'host': 'common_db',
        'port': '3306',
        'user': 'root',
        'password': 'root'
    }

db_configuration = {}

db_configuration['business_rules'] = business_rules_db_config
db_configuration['extraction'] = db_config
db_configuration['queues'] = queue_db_config
db_configuration['kafka'] = common_db_config


def join_strings(list_of_string):
    to_return = '`,`'.join(list_of_string)

    return to_return

def join_where_with_and(wheres):
    where = []
    for field, value in wheres.items():
        if value is None:
            continue
        temp = ''
        if type(value) is str:
            temp = f'`{field}` = "{value}"'
        else:
            temp = f'`{field}` = {value}'
        where.append(temp)

    where = ' AND '.join(where)

    return where

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



def get_db(db_string):
    db = DB(db_string, **db_configuration[db_string])

    return db

class BusinessRulesDAOImpl(BusinessRulesDAOABC):
    def __init__(self):
        self.tables = {
            "extraction" : ["business_rule","ocr","sap","validation"],
            "queues" : ["ocr_info", "process_queue"]
        }

    def extraction_db_get_data(self, table, case_id):
        query = f"SELECT * from `{table}` WHERE case_id = %s"
        db = get_db('extraction')
        to_return = db.execute(query, params=[case_id])
        db.db_.dispose()

        return to_return

    def doSelect_get_data(self, table, field, where):
        fields = ''
        if type(field) is list:
            fields = join_strings(field)
        else:
            fields = field

        if where is not None:
            wheres = f'WHERE {join_where_with_and(where)}'
        else:
            wheres = ''

        if fields:
            query = f'SELECT `{fields}` FROM `{table}` {wheres}'
        else:
            query = f'SELECT * FROM `{table}` {wheres}'

        print("query = ", query)
        db = get_db('extraction')
        to_return = db.execute(query)
        print(to_return)
        db.db_.dispose()

        return to_return


    def doContains_get_lhs_field_name(self, table, field):
        fields = ''
        if type(field) is list:
            fields = join_strings(field)
        else:
            fields = field

        if fields:
            query = f'SELECT `{fields}` FROM `{table}` '
        else:
            query = f'SELECT * FROM `{table}`'

        if table == 'process_queue': 
            db = get_db('queues')
        else:
            db = get_db('extraction')

        to_return = db.execute(query)
        db.db_.dispose()

        return to_return

    def doAssign_get_data(self, table, case_id):
        query = f'SELECT * from `{table}` WHERE `case_id` = "{case_id}"'
        
        if table == 'process_queue': 
            db = get_db('queues')
        else:
            db = get_db('extraction')

        to_return = db.execute(query)
        db.db_.dispose()

        return to_return

    def doAssign_insert_case_id(self, table, case_id):
        query = f'INSERT INTO `{table}` (`case_id`) VALUES ("{case_id}")'
        db = get_db('extraction')

        to_return = db.execute(query)
        db.db_.dispose()

        return to_return

    def doAssign_update_case_id(self, table, to_update, case_id):
        updates = join_update(to_update)

        query = f'UPDATE `{table}` SET {updates} WHERE `case_id` = "{case_id}"'
        db = get_db('extraction')

        to_return = db.execute(query)
        db.db_.dispose()

        return to_return

    def doUpdateQueue(self, case_id, queue):
        query = f'UPDATE `process_queue` SET `queue` = "{queue}" WHERE `case_id` = "{case_id}"'
        db = get_db('queues')

        to_return = db.execute(query)
        db.db_.dispose()

        return to_return

    def update_queue_trace_get_trace_data(self, case_id):
        query = f'SELECT `id`, `queue_trace`, `last_updated_dates` from `trace_info` WHERE `case_id` = "{case_id}"'
        db = get_db('queues')

        to_return = db.execute(query)
        db.db_.dispose()

        return to_return

    def update_queue_trace_update(self, queue_trace, last_updated_dates,case_id):
        query = f'UPDATE `trace_info` SET `queue_trace` = "{queue_trace}", `last_updated_dates` = "{last_updated_dates}" WHERE `case_id` = "{case_id}"'
        db = get_db('queues')

        to_return = db.execute(query)
        db.db_.dispose()

        return to_return

    def get_rules(self, stage):
        query = f'SELECT `id`, `rule_string` FROM `sequence_data` WHERE `group` = "{stage}"'
        db = get_db('business_rules')

        to_return = db.execute(query)
        db.db_.dispose()

        return to_return

    def get_tables_data(self, case_id):
        to_return = {}
        db_ext = get_db('extraction')
        db_queue = get_db('queues')

        for key, tables in self.tables.items():
            if key == "extraction":
                for table in tables:
                    query = f'SELECT * from `{table}` WHERE `case_id` = "{case_id}"'
                    to_return[table] = db_ext.execute(query)
                
            elif key == "queues":
                for table in tables:
                    query = f'SELECT * from `{table}` WHERE `case_id` = "{case_id}"'
                    to_return[table] = db_queue.execute(query)

        db_ext.db_.dispose()
        db_queue.db_.dispose()

        return to_return


    def update_table_update(self, table, to_update, case_id):
        updates = join_update(to_update)
        query = f'UPDATE `{table}` SET {updates} WHERE `case_id` = "{case_id}"'

        if table in self.tables['extraction']:
            db = get_db('extraction')
        else:
            db = get_db('queues')
        

        to_return = db.execute(query)
        db.db_.dispose()

        return to_return

    def validate_rules_get_data(self, case_id):
        query = f'SELECT * from validation WHERE `case_id` = "{case_id}"'
        db = get_db('extraction')

        to_return = db.execute(query)
        db.db_.dispose()

        return to_return
        
    def kafka_consume_get_messages(self, table='message_flow'):
        db = get_db('kafka')

        to_return = db.get_all(table)
        db.db_.dispose()

        return to_return

    def kafka_consume_get_data(self, case_id):
        query = f'SELECT `id`, `case_id` from `business_rule` WHERE `case_id` = "{case_id}"'
        db = get_db('extraction')

        to_return = db.execute(query)
        db.db_.dispose()

        return to_return

    def run_business_rule_update_case(self, case_meta, case_id):

        db = get_db('queues')
        to_return = db.update('process_queue', update=case_meta, where={'case_id': case_id})

        db.db_.dispose()

        return to_return

    def update_error_msg(self, message, case_id):
        db = get_db('queues')
        query = f"UPDATE `process_queue` set `error_logs` = concat(ifnull(error_logs,''), '{'|'+message}') WHERE case_id={case_id}"

        to_return = db.execute(query)

        db.db_.dispose()

        return to_return



