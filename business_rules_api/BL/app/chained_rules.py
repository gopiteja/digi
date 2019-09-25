import BusinessRules
import db_utils as db
import sqlalchemy as sql
import pandas as pd
import json
import os
from producer import produce
import traceback
import datetime

class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime.datetime):
            encoded_object = list(obj.timetuple())[0:6]
        else:
            encoded_object =json.JSONEncoder.default(self, obj)
        return encoded_object

def insert_if_not_update_ruleparams(rule_params, unique_id):
    query=f"INSERT INTO `rule_data`(`id`, `case_id`, `rule_params`) VALUES ('NULL','{unique_id}',%s) ON DUPLICATE KEY UPDATE `rule_params`=%s"
    config={'host':os.environ['HOST_IP'],
        'user':'root',
        'password':os.environ['LOCAL_DB_PASSWORD'],
        'port':'3306',
       }

    business_rules_db = db.DB('business_rules',**config)
    params = params = [str(rule_params), str(rule_params)]
    business_rules_db.execute(query, params=params)
    return "UPDATE/INSERT INTO RULE_DATA IS DONE"



def insert_if_not_update_trace_exec(trace_exec, unique_id):
    query=f"INSERT INTO `rule_data`(`id`, `case_id`, `trace_data`) VALUES ('NULL','{unique_id}',%s) ON DUPLICATE KEY UPDATE `trace_data`=%s"
    config={'host':os.environ['HOST_IP'],
        'user':'root',
        'password':os.environ['LOCAL_DB_PASSWORD'],
        'port':'3306',
       }

    business_rules_db = db.DB('business_rules',**config)
    params = params = [str(trace_exec), str(trace_exec)]
    business_rules_db.execute(query, params=params)
    return "UPDATE/INSERT INTO RULE_DATA...TRACE DATA IS DONE"


def get_chain_rules(data_base, table='sequence_data', group='chain'):
    """
        Getting the rule_string, next_if_sucess and next_if_failure data from the database
    """
    
    business_rule_db = db.DB(data_base)
    df = business_rule_db.execute(f"SELECT `id`,`rule_id`,`rule_string`, `next_if_sucess`, `next_if_failure`, `stage`, `description`, `data_source` from `{table}` where `group`='{group}'")
    chained_rules = [[e['rule_id'], e['rule_string'], e['next_if_sucess'], e['next_if_failure'], e['stage'], e['description'], e['data_source']] for e in df.to_dict(orient='records') ]
    return df

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

def get_master_data(db_tables):
    
    to_return = {}

    for key, tables_ in db_tables.items():
        for table in tables_:
            query = f'SELECT * from `{table}`'
            df = execute_query(query, key)
            
            to_return[table] = df.to_dict(orient='list')
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
    return "UPDATE SUCCESSFULLY"

def run_chained_rules(unique_id,kafka_data, start_rule_id=None, bot_finished=False, bot_status=None):
    
    unique_id = unique_id.strip()
    
    # get the chained rules 
    chain_rules = get_chain_rules('business_rules', 'sequence_rule_data')

    # get the mapping of the rules...basically a rule_id maps to a rule
    rule_id_mapping = {}
    for ind, rule in chain_rules.iterrows():
        rule_id_mapping[rule['rule_id']] = [rule['rule_string'], rule['next_if_sucess'], rule['next_if_failure'], rule['stage'], rule['description'], rule['data_source']]
        
    # evaluate the rules one by one
    # start_rule_id = None
    if start_rule_id is None:
        if rule_id_mapping.keys():
            start_rule_id = list(rule_id_mapping.keys())[0]
            kafka_data['trace_exec'] = []
            kafka_data['rule_params'] = {}
            
    
    query = "select * from rule_data where case_id=%s"
    params = [unique_id]
    config={'host':os.environ['HOST_IP'],
        'user':'root',
        'password':os.environ['LOCAL_DB_PASSWORD'],
        'port':'3306',
    }
    business_rule_db = db.DB('business_rules', **config)
    df = business_rule_db.execute(query, params=params)


    print (start_rule_id)
    try:
        trace_exec = json.loads(list(df['trace_data'])[0])
        print (f"trace exec is {trace_exec}")
        kafka_data['trace_exec'] = trace_exec
    except:

        kafka_data['trace_exec'] = []
    
    try:
        rule_params = json.loads(list(df['rule_params'])[0])
        print (f"rule_params is {rule_params}")
        kafka_data['rule_params'] = rule_params
    except:
        kafka_data['rule_params'] = {}

    kafka_data['trace_exec'].append(str(start_rule_id))
    db_tables = {
                    "extraction" : ["ocr"],
                    "queues":["process_queue"]
                }
    master_db_tables = {"alorica_data": ['master']}
    # unique_id = 'TX05D36FF31C451'
    # bot_finished = False
    tables_data = get_tables_data('case_id', unique_id, db_tables)
    master_data = get_master_data(master_db_tables)
    data = {**tables_data, **master_data}
    # start_rule_id = 20
    trace_array = []
    rule_params = []
    trace_dict = {}
    while True:
        rule_to_evaluate, next_if_sucess, next_if_failure, stage, description, data_source = rule_id_mapping[str(start_rule_id)]  
        print (rule_to_evaluate)
        print (stage)
        trace_array.append(start_rule_id)

        rule_to_evaluate = json.loads(rule_to_evaluate)
        
        if bot_status == 'Bot failed':            
            break 
        if bot_finished:
            # ideally these will come from the database tables.....sequence_rule_data...the tables that bot updates
            bot_tables = {"alorica_data": ['demographics', 'eligibility', 'insurance', 'history', 'Member']}
            data.update(get_tables_data('Fax_unique_id', unique_id, bot_tables))
        
        BR = BusinessRules.BusinessRules(unique_id,[rule_to_evaluate], data, decision=True)
        #Need to get 'parameters' from evaluate_rule 
        decision = BR.evaluate_rule(rule_to_evaluate)
        params_data = BR.params_data
        print(params_data)
        input_ = to_DT_data(params_data['input'])
        print(input_)
        trace_dict = {
            str(start_rule_id):{
                'description' : description if description else 'No description available in the database',
                'output' : decision,
                'input' : input_
                }
            }
        kafka_data['rule_params'] = {**kafka_data['rule_params'] , **trace_dict}

        # update the rule_params
        # rule_params.append(BR.params_data)
        # config={'host':os.environ['HOST_IP'],
        # 'user':'root',
        # 'password':os.environ['LOCAL_DB_PASSWORD'],
        # 'port':'3306',
        # }
        # business_rule_db = db.DB('business_rules', **config)

        # try:
        #     query = "SELECT `id`, `rule_params` from rule_data where case_id=%s"
        #     params=[unique_id]
        #     df = business_rule_db.execute(query, params=params)
        #     trace_data = list(df['rule_params'])[0]

        #     if trace_data:
        #         existing_trace = json.loads(trace_data)
        #     else:
        #         existing_trace = []
        #     updated_trace = existing_trace+ kafka_data.get('trace_exec',[])
        #     # right now..validations will pass..so alwayss insert....
        #     # insert
        #     query = "UPDATE `rule_data` SET `trace_data`=%s where case_id=%s"
        #     params = [json.dumps(updated_trace), unique_id]
        #     business_rule_db.execute(query,params=params)
        # except Exception as e:
        #     print ("excepitn iin inserting the trace data")
        #     print (e)



        #Expected input format for trace_dict_transform:
        # {
        # "ocr": [
        #     "Fax_unique_id",
        #     "Communication_date_time"
        # ],
        # "process_queue": [
        #     "queue",
        #     "state"
        # ],
        # "master": [
        #     "CPT_Code",
        #     "Category",
        #     "State"
        # ]
        # }
        # trace_dict = trace_dict_transform(parameters)
        # insert 'trace_dict' in the dictionary below
        # update the stage
        update({'process_queue': {'state': stage}}, unique_id)

        stats_db_config = {
        'host': 'stats_db',
        'user': 'root',
        'password': 'root',
        'port': '3306'
            }
        stats_db = db.DB('stats', **stats_db_config)
        if stage:   
            audit_data = {
                    "type": "update", "last_modified_by": "user_name", "table_name": "process_queue", "reference_column": "case_id",
                    "reference_value": unique_id, "changed_data": json.dumps({"stats_stage":stage})
                }
            stats_db.insert_dict(audit_data, 'audit')  

        print ("DECISION < NEXT_IF_SUCEESS < NEXT_IF_FAILURE < STAGE")
        print (decision, next_if_sucess, next_if_failure, stage)

        # params_data = BR.params_data
        # rule_id_data = {}
        # rule_id_data[start_rule_id] = params_data['input']
        # kafka_data['rule_params'].append(json.dumps(rule_id_data, cls=DateTimeEncoder))
        # kafka_data['trace_exec'].append(str(start_rule_id))

        if decision:
            start_rule_id = next_if_sucess
        else:
            start_rule_id = next_if_failure
        print (start_rule_id)

        kafka_data['trace_exec'].append(str(start_rule_id))



       

        # ideally this has to be BOT_name_of_the_stage...for ex BOT_member etc
        if start_rule_id == "BOT":
            rule_to_evaluate, next_if_sucess, next_if_failure, stage, description, data_source = rule_id_mapping[str(start_rule_id)]  
            trace_dict = {
                        str(start_rule_id):{
                            'description' : description if description else 'No description available in the database',
                            'output' : "",
                            'input' : []
                            }
                        }
            kafka_data['rule_params'] = {**kafka_data['rule_params'] , **trace_dict}
            next_rule_id = rule_id_mapping[str(start_rule_id)][1] 
            # kafka_data['trace_exec'].append("BOT")
            kafka_data['next_rule_id'] = next_rule_id
            print ("BOT SERVICE TO BE CALLED")
            produce('bot_watcher', kafka_data)
            trace_array.append("BOT")
            print("trace_rule_id in BOT", trace_array)
            try:
                process_queue_db = db.DB("queues")
                trace_array = json.dumps(trace_array)
                trace_dict = json.dumps(trace_dict)
                query = f"INSERT INTO `decision_tree_trace` (case_id, trace_array, trace_dict) VALUES('{unique_id}', '{trace_array}', '{trace_dict}') ON DUPLICATE KEY UPDATE `trace_array`= '{trace_array}', `trace_dict` = '{trace_dict}'"
                update_status = process_queue_db.execute(query)
                if update_status:
                    print("Inserted into decision_tree_trace table")
                else:
                    print("Insert failed")
            except:
                traceback.print_exc()
                print("Something went wrong while inserting trace_array")
                pass
            break
        if start_rule_id == "END":
            print (BR.changed_fields)
            update(BR.changed_fields, unique_id)
            print("trace_rule_id in END", trace_array)
            try:
                process_queue_db = db.DB("queues")
                query = f"SELECT * FROM `decision_tree_trace` WHERE `case_id` = '{unique_id}'"
                df = process_queue_db.execute(query)
                if not df.empty:
                    trace_dict_old = json.loads(list(df['trace_dict'])[0])
                    trace_array_old = json.loads(list(df['trace_array'])[0])
                    trace_array = trace_array + trace_array_old
                    trace_array = list(dict.fromkeys(trace_array))
                    trace_dict = {**trace_dict_old, **trace_dict}
                    trace_array = json.dumps(trace_array)
                    trace_dict = json.dumps(trace_dict)
                    query = f"UPDATE `decision_tree_trace` SET `trace_array` = '{trace_array}', `trace_dict` = '{trace_dict}' WHERE `case_id` = '{unique_id}'" 
                    update_status = process_queue_db.execute(query)
                    if update_status:
                        print("Inserted into decision_tree_trace table")
                    else: 
                        print("Insert failed")
                else:
                    print("Bot start sequence not found in the DB")
            except:
                traceback.print_exc()
                print("Something went wrong while inserting trace_array")
                pass
            # kafka_data['trace_exec'].append("END")
            break

        print (f"updated fields are .....at the end of one decison...{BR.changed_fields}", BR.changed_fields)
        if BR.changed_fields:
            update(BR.changed_fields, unique_id)

    # update trace
    # if duplicate is present..that means....update the trace info
    query = "select * from rule_data where case_id=%s"
    params = [unique_id]
    config={'host':os.environ['HOST_IP'],
        'user':'root',
        'password':os.environ['LOCAL_DB_PASSWORD'],
        'port':'3306',
       }
    business_rule_db = db.DB('business_rules', **config)
    df = business_rule_db.execute(query, params=params)


    try:
        # query = "SELECT `id`, `trace_data` from rule_data where case_id=%s"
        # params=[unique_id]
        # df = business_rule_db.execute(query, params=params)
        # trace_data = list(df['trace_data'])[0]

        # if trace_data:
        #     existing_trace = json.loads(trace_data)
        # else:
        #     existing_trace = []
        updated_trace = kafka_data.get('trace_exec',[])
        # right now..validations will pass..so alwayss insert....
        # insert
        insert_if_not_update_trace_exec(json.dumps(updated_trace), unique_id)

        insert_if_not_update_ruleparams(json.dumps(kafka_data['rule_params'], indent=4, sort_keys=True, default=str), unique_id)
        # query = "UPDATE `rule_data` SET `trace_data`=%s where case_id=%s"
        # params = [json.dumps(updated_trace), unique_id]
        # business_rule_db.execute(query,params=params)
    except Exception as e:
        print ("excepitn iin inserting the trace data")
        print (e)
   
def trace_dict_transform(parameters, data_source):
    data_source_dict = {}
    for table, column_list in parameters.items():
        table_temp = {}
        if table == 'master':
            master_df = pd.DataFrame.from_dict(data_source[table])
            try:
                temp_df = master_df[column_list]
                temp_df = temp_df[temp_df['CPT_Code'].isin(['P9604', '21011']) & temp_df['State'].isin(['TX'])]
            except:
                traceback.print_exc()
                print(f"Skipped inserting {table} {column_list}")
                temp_df = pd.DataFrame()
            data_source_dict[table] = temp_df.to_dict(orient= 'records')
        else:
            for column in column_list:
                try:
                    table_temp = {**table_temp, **{column : data_source[table][column]}}
                except:
                    traceback.print_exc()
                    print(f"Skipped inserting {table} {column}")
            data_source_dict[table] = [table_temp]
    #    print(data_source_dict)
    return data_source_dict

def to_DT_data(parameters):
    output = []
    try:
        for param_dict in parameters:
            print(param_dict)    
            if param_dict['column'] == 'Add_on_Table':
                output.append({'table': param_dict['table'],'column': param_dict['column'],'value': param_dict['value']})
                # Need to add a function to show this or tell Kamal check if its addon table and parse accordingly
            else:                
                output.append({'table': param_dict['table'],'column': param_dict['column'],'value': param_dict['value']})
    except:
        print("Error in to_DT_data()")
        traceback.print_exc()
        return []
    try:
        output = [dict(t) for t in {tuple(d.items()) for d in output}]
    except:
        print("Error in removing duplicate dictionaries in list")
        traceback.print_exc()
        pass
    return output
