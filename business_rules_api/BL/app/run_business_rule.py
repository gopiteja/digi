import json
import traceback

from db_utils import DB
from kafka import KafkaConsumer, TopicPartition
from random import randint
from time import time, sleep

from field_validations import apply_field_validations
from chained_rules import run_chained_rules

from producer import produce
from business_rules_api import apply_business_rules, update_table, initialize_rules, get_tables_data

try:
    from app.da_bizRul_factory import DABizRulFactory
    from app.ace_logger import Logging
except:
    from da_bizRul_factory import DABizRulFactory
    from ace_logger import Logging

DAO = DABizRulFactory.get_dao_bizRul()
logging = Logging()



import BusinessRules
import json

def get_chain_rules(data_base):
    """
        Getting the rule_string, next_if_sucess and next_if_failure data from the database
    """
    
    business_rule_db = DB(data_base, host='business_rules_db')
    df = business_rule_db.execute(f"SELECT `id`, `rule_id`,`rule_string`, `next_if_sucess`, `next_if_failure`, `group`, `description`, `data_source` from `sequence_rule_data`")
    chained_rules = [[e['rule_id'], e['rule_string'], e['next_if_sucess'], e['next_if_failure'], e['group'],e['description'], e['data_source']] for e in df.to_dict(orient='records') ]
    
    return chained_rules

database = 'business_rules'
rules = get_chain_rules(database)
    
# print (rules[0])
# rules = [rules[0]]
rules_id_mapping = {rule.pop(0):rule for i,rule in enumerate(rules)}


data = {'id': 1, 'case_id': '2000441939', 'highlight': '{"Document Heading": {"height": 12, "width": 63, "y": 38, "x": 297, "right": 364, "word": "Tax Invoice", "page": 0}, "Vendor GSTIN": {"height": 7, "width": 101, "y": 117, "x": 102, "right": 203, "word": "37AAUFA4486C1Z5", "page": 0}, "Billed To (DRL Name)": {"height": 9, "width": 197, "y": 159, "x": 39, "right": 252, "word": "Dr. Reddys Laboratories Limited CTO-6", "page": 0}, "DRL GSTIN": {"height": 10, "width": 105, "y": 205, "x": 128, "right": 239, "word": "37AAACD7999Q1ZJ", "page": 0}, "Invoice Number": {"height": 9, "width": 24, "y": 79, "x": 364, "right": 389, "word": "6106", "page": 0}, "Vendor Name": {"height": 7, "width": 93, "y": 816, "x": 529, "right": 628, "word": "Akshaya Lab Products", "page": 0}, "Invoice Date": {"height": 9, "width": 60, "y": 79, "x": 498, "right": 559, "word": "4-May-2019", "page": 0}, "PO Number": {"height": 10, "width": 61, "y": 157, "x": 364, "right": 426, "word": "5800438872", "page": 0}, "Invoice Total": {"height": 7, "width": 163, "y": 708, "x": 325, "right": 629, "word": "50,000.00 4,500.00 4,500.00 9,000.00", "page": 0}}', 'PO Number': '5800438872', 'Invoice Number': '6106', 'Invoice Category': None, 'Invoice Date': '2019-05-04', 'Invoice Total': '59000', 'Invoice Base Amount': '50000', 'GST Percentage': '', 'IGST Amount': '0', 'DRL GSTIN': '37AAACD7999Q1ZJ', 'Vendor GSTIN': '37AAUFA4486C1Z5', 'Billed To (DRL Name)': 'Dr. Reddys Laboratories Limited CTO-6', 'Vendor Name': 'Akshaya Lab Products', 'Special Instructions': '', 'Digital Signature': 'Yes', 'Document Heading': 'Tax Invoice', 'HSN/SAC': '', 'DC Number': '', 'SGST/CGST Amount': '', 'GRN Number': '', 'Service Entry Number': '', 'Comments': None, 'Table': '[[[[[["<b>Product description</b>",1,1],["<b>HSN/SAC</b>",1,1],["<b>Quantity</b>",1,1],["<b>Rate</b>",1,1],["<b>Gross Amount</b>",1,1]],[[" Headspace Vials 20ml - Pk/100 Cat No: FULV21 Make: Saint-Gobain Material Code: 940003734",1,1],[" Rate 70179090 18 %",1,1],[" 50 Pack",1,1],[" 1,000.00",1,1],[" 50,000.00",1,1]],[[" SGST Output @ 9%",1,1],["",1,1],["",1,1],[" 9",1,1],[" 4,500.00",1,1]],[[" CGST Output @ 9%",1,1],["",1,1],["",1,1],[" 9",1,1],[" 4,500.00",1,1]]]]]]'}
# data['PO Number'] = "4"

record = { 
  'Name': ['Ankit', 'Amit', 'Aishwarya', 'Priyanka', 'Priya', 'Shaurya' ], 
  'Age': [21, 19, 20, 18, 17, 21], 
  'Stream': ['Math', 'Commerce', 'Science', 'Math', 'Math', 'Science'], 
  'Percentage': [88, 92, 95, 70, 65, 78]
} 

def evaluate_chained_rules(start=None, fax_unique_id=None):
    """Evaluate the chained rules"""
    # this means we are just starting..
    if start == None:
        start = '1'
        
    rule_id = start
    
    # dangerous...might end in infinite loop..take care
    while rule_id != "END":
        
        rule_string, next_ruleid_if_success, next_ruleid_if_fail,stage, description, data_source = rules_id_mapping[rule_id]

        rule_to_evaluate = json.loads(rule_string)
    

        # get the data_source according to the case_id...and..the stage...
        data_source = {"ocr":data, "validation": data.copy(), "master":record}
        BR = BusinessRules.BusinessRules(fax_unique_id,[rule_to_evaluate], data_source)
        
        
        decision = BR.evaluate_rule(rule_to_evaluate)
        print ("HEREEE", decision)
        
        if decision:
            rule_id =  next_ruleid_if_success
        else:
            rule_id = next_ruleid_if_fail
            
        if rule_id == "BOT":
            # send to the microservices
            # parameters- case_id, start, stage, table_name that bot should update
            return 
    
    result = {}
    result['flag'] = True
    return result
        
        
        
def run_business_rule_consumer_(data, function_params):
    print ("GOT THE PARAMTERTES", data, function_params)
    print (f"\n the data got is \n {data} \n")
        # evaluate the field validation
    case_id = data['case_id'] 
    start_rule_id = data.get('next_rule_id', None)
    bot_message = data.get('bot_message', False)
    bot_status = data.get('bot_status', None)
    stage = None
    try:

        for func in data['functions']:
            try:
                if func['route'] == 'run_business_rule':
                    stage = func['parameters']['stage'][0]
            except Exception as e:
                print (f"No stage is got {e}")
                stage = None
    except Exception as e:
        print (e)
        

    # stage = data.get('stage', None)
    print (f"\n GOT THE STAGE {stage} \n")
    if stage == 'default':
        db_tables = {
                "alorica_data": ['screen_shots'],
                "extraction" : ["ocr"],
            }
        apply_field_validations(case_id, stage, db_tables)
        return {'flag': True, 'message': 'Completed runninig default business rules.', 'updates': updates}

    if stage == 'validation':
        db_tables = {
                "extraction" : ["ocr"],
                "queues":["process_queue"]

            }
        updates = apply_field_validations(case_id, stage, db_tables)
        return {'flag': True, 'message': 'Completed runninig validation business rules.', 'updates': updates}
    if not bot_message:
        # updates = apply_field_validations(case_id)
        updates = None
    else:
        print ("CALLED BY BOT")
        print (case_id, start_rule_id, bot_message)

        updates = None
    # run all the chained rules
    print ("RUNNING CHAINED RULES ", start_rule_id,bot_message )
    run_chained_rules(case_id,data, start_rule_id=start_rule_id, bot_finished=bot_message, bot_status=bot_status)
    
    return {'flag': True, 'message': 'Completed runninig business rules.', 'updates': updates}
     
    

def run_business_rule_consumer(data):
    
    queue_db_config = {
        'host': '172.31.45.112',
        'user': 'root',
        'password': 'AlgoTeam123',
        'port': '3306'
    }
    queue_db = DB('queues', **queue_db_config)

    print("Submit data", data)
    if 'case_id' not in data:
        message = f'`case_id` key not provided.'
        print(message)
        return {'flag': False, 'message': message}

    case_id = data['case_id']

    initialize_rules()

    tables = {
        "extraction" : ["business_rule","ocr","sap","validation"],
        "queues" : ["ocr_info", "process_queue"]
        }

    table_data = get_tables_data(tables, case_id)
    table_data['update'] = {}

    if 'stage' not in data:
        message = f'`{case_id}` key not provided. Running all stages...'
        print(message)

        stages = ['One']

        for stage in stages:
            starting_time = time()
            data = apply_business_rules(api=True, table_data= table_data,stage=stage, case_id=case_id)
            print("time taken - ",time() - starting_time)

            if not data['flag'] and stage == 'One':
                DAO.update_error_msg(data['message'], case_id)

        update_values = update_table(table_data, case_id, tables)

        if data['flag']:
            return {'flag': data['flag'], 'message': 'Applied all business rules.', 'updates': update_values}
        else:
            return {'flag': data['flag'], 'message': 'Something failed.', 'updates': update_values}

    stages = data['stage']
    starting_time = time()
    if type(stages) is str:

        data = apply_business_rules(api=True, table_data = table_data,**data)
        time_taken = time() - starting_time
        data['time_taken'] = time_taken
        # print("time takne - ",time_taken)
        update_values = update_table(table_data, case_id, tables)
        data['updates'] = update_values

        if not data['flag'] and stages == 'One':
            DAO.update_error_msg(data['message'], case_id)

        return data
    elif type(stages) is list:
        for stage in stages:
            # starting_time = time()

            rule_response = apply_business_rules(api=True, table_data= table_data,stage=stage, case_id=case_id)

            if not rule_response['flag'] and stage == 'One':
                try:
                    messsage = rule_response['message']
                except:
                    messsage = 'Validation Failed due to execution error in business rules.'
                DAO.update_error_msg(message, case_id)

            if not rule_response['flag']:
                message = f'Something went wrong running stage at `{stage}`. Skipping other rules.'
                print(message)
                update_values = update_table(table_data, case_id, tables)

                return {'flag': False, 'message': message, 'updates':update_values}

    update_values = update_table(table_data, case_id, tables)

    print("time takne - ",time() - starting_time)
    if rule_response['flag']:
        return {'flag': rule_response['flag'], 'message': 'Completed runninig business rules.', 'updates': update_values}
    else:
        return {'flag': rule_response['flag'], 'message': 'Something wrong happened.', 'updates': update_values}

def consume(broker_url='broker:9092'):
    try:
        route = 'run_business_rule'

        common_db_config = {
            'host': 'common_db',
            'port': '3306',
            'user': 'root',
            'password': 'root'
        }
        kafka_db = DB('kafka', **common_db_config)
        # kafka_db = DB('kafka')

        queue_db_config = {
            'host': 'queue_db',
            'port': '3306',
            'user': 'root',
            'password': ''
        }
        queue_db = DB('queues', **queue_db_config)
        # queue_db = DB('queues')

        message_flow = kafka_db.get_all('grouped_message_flow')

        print(f'Listening to topic `{route}`...')
        consumer = KafkaConsumer(
            bootstrap_servers=broker_url,
            value_deserializer=lambda value: json.loads(value.decode()),
            auto_offset_reset='earliest',
            group_id='run_business_rule',
            api_version=(0,10,1),
            enable_auto_commit=False,
            session_timeout_ms=800001,
            request_timeout_ms=800002
        )
        print('Consumer object created.')

        parts = consumer.partitions_for_topic(route)
        if parts is None:
            logging.warning(f'No partitions for topic `{route}`')
            logging.debug(f'Creating Topic: {route}')
            produce(route, {})
            print(f'Listening to topic `{route}`...')
            while parts is None:
                consumer = KafkaConsumer(
                    bootstrap_servers=broker_url,
                    value_deserializer=lambda value: json.loads(value.decode()),
                    auto_offset_reset='earliest',
                    group_id='sap_portal',
                    api_version=(0,10,1),
                    enable_auto_commit=False,
                    session_timeout_ms=800001,
                    request_timeout_ms=800002
                )
                parts = consumer.partitions_for_topic(route)
                logging.warning("No partition. In while loop. Make it stop")

        partitions = [TopicPartition(route, p) for p in parts]
        consumer.assign(partitions)

        query = 'SELECT * FROM `button_functions` WHERE `route`=%s'
        function_info = queue_db.execute(query, params=[route])
        in_progress_message = list(function_info['in_progress_message'])[0]
        failure_message = list(function_info['failure_message'])[0]
        success_message = list(function_info['success_message'])[0]

        for message in consumer:
            data = message.value
            try:
                case_id = data['case_id']
                functions = data['functions']
            except Exception as e:
                print(f'Recieved unknown data. [{data}] [{e}]')
                consumer.commit()
                continue
            function_params = {}

            # coming from bot_watcher .... not button function
            print ("CHECKING FOR THE IS BUTTON", data,data.get('is_button', True))
            if 'is_button' in data.keys():
            # if not data.get('is_button', False):
                try:
                    result = run_business_rule_consumer_(data, function_params)
                except Exception as e:
                    print (f"Error runnign the business_rules {e}")
                    print (str(e))
                    query = 'UPDATE `process_queue` SET `queue`=%s, `status`=%s, `case_lock`=0, `failure_status`=1 WHERE `case_id`=%s'
                    queue_db.execute(query, params=['GHI678', failure_message, case_id])
                    consumer.commit()

                # # Get which button (group in kafka table) this function was called from
                # group = data['group']

                # # Get message group functions
                # group_messages = message_flow.loc[message_flow['message_group'] == group]

                # # If its the first function the update the progress count
                # first_flow = group_messages.head(1)
                # first_topic = first_flow.loc[first_flow['listen_to_topic'] == route]

                # query = 'UPDATE `process_queue` SET `status`=%s, `total_processes`=%s WHERE `case_id`=%s'
                # if not first_topic.empty:
                #     if list(first_flow['send_to_topic'])[0] is None:
                #         queue_db.execute(query, params=[in_progress_message, len(group_messages), case_id])
                #     else:
                #         queue_db.execute(query, params=[in_progress_message, len(group_messages) + 1, case_id])

                # # Getting the correct data for the functions. This data will be passed through
                # # rest of the chained functions.
                # function_params = {}
                # for function in functions:
                #     if function['route'] == route:
                #         function_params = function['parameters']
                #         break
                    
                # if result['flag']:
                #     # If there is only function for the group, unlock case.
                #     if not first_topic.empty:
                #         if list(first_flow['send_to_topic'])[0] is None:
                #             # It is the last message. So update file status to completed.
                #             print("\n CASE IS UNLOCKED \n")
                #             query = 'UPDATE `process_queue` SET `status`=%s, `case_lock`=0, `completed_processes`=`completed_processes`+1 WHERE `case_id`=%s'
                #             queue_db.execute(query, params=[success_message, case_id])
                #             consumer.commit()
                #             continue

                #     last_topic = group_messages.tail(
                #         1).loc[group_messages['send_to_topic'] == route]

                #     # If it is not the last message, then produce to next function else just unlock case.
                #     if last_topic.empty:
                #         # Get next function name
                #         print ("\n CHECKING FOR THE DATA \n")
                #         print (data)
                #         next_topic = list(
                #             group_messages.loc[group_messages['listen_to_topic'] == route]['send_to_topic'])[0]

                #         if next_topic is not None:
                #             produce(next_topic, data)

                #         # Update the progress count by 1
                #         query = 'UPDATE `process_queue` SET `status`=%s, `completed_processes`=`completed_processes`+1 WHERE `case_id`=%s'
                #         queue_db.execute(query, params=[success_message, case_id])
                #         consumer.commit()
                #     else:
                #         # It is the last message. So update file status to completed.
                #         query = 'UPDATE `process_queue` SET `status`=%s, `case_lock`=0, `completed_processes`=`completed_processes`+1 WHERE `case_id`=%s'
                #         queue_db.execute(query, params=[success_message, case_id])
                #         consumer.commit()
                # else:
                #     # Unlock the case.
                #     query = 'UPDATE `process_queue` SET `status`=%s, `case_lock`=0, `failure_status`=1 WHERE `case_id`=%s'
                #     queue_db.execute(query, params=[failure_message, case_id])
                #     consumer.commit()




                continue

            
            
            # Get which button (group in kafka table) this function was called from
            group = data['group']

            # Get message group functions
            group_messages = message_flow.loc[message_flow['message_group'] == group]

            # If its the first function the update the progress count
            first_flow = group_messages.head(1)
            first_topic = first_flow.loc[first_flow['listen_to_topic'] == route]

            query = 'UPDATE `process_queue` SET `status`=%s, `total_processes`=%s WHERE `case_id`=%s'
            if not first_topic.empty:
                if list(first_flow['send_to_topic'])[0] is None:
                    queue_db.execute(query, params=[in_progress_message, len(group_messages), case_id])
                else:
                    queue_db.execute(query, params=[in_progress_message, len(group_messages) + 1, case_id])

            # Getting the correct data for the functions. This data will be passed through
            # rest of the chained functions.
            function_params = {}
            for function in functions:
                if function['route'] == route:
                    function_params = function['parameters']
                    break

            # Call save changes function
            try:
                print (f"\n the data got is \n {data} \n")
                result = run_business_rule_consumer_(data, function_params)
                # return {'flag': True, 'message': 'Completed runninig business rules.', 'updates': None}

            except Exception as e:
                # Unlock the case.
                logging.error(e)
                query = 'UPDATE `process_queue` SET `queue`=%s, `status`=%s, `case_lock`=0, `failure_status`=1 WHERE `case_id`=%s'
                queue_db.execute(query, params=['Maker', failure_message, case_id])

                consumer.commit()
                continue

            # Check if function was succesfully executed
            if result['flag']:
                # If there is only function for the group, unlock case.
                if not first_topic.empty:
                    if list(first_flow['send_to_topic'])[0] is None:
                        # It is the last message. So update file status to completed.
                        print("\n CASE IS UNLOCKED \n")
                        query = 'UPDATE `process_queue` SET `status`=%s, `case_lock`=0, `completed_processes`=`completed_processes`+1 WHERE `case_id`=%s'
                        queue_db.execute(query, params=[success_message, case_id])
                        consumer.commit()
                        continue

                last_topic = group_messages.tail(
                    1).loc[group_messages['send_to_topic'] == route]

                # If it is not the last message, then produce to next function else just unlock case.
                if last_topic.empty:
                    # Get next function name
                    print ("\n CHECKING FOR THE DATA \n")
                    print (data)
                    next_topic = list(
                        group_messages.loc[group_messages['listen_to_topic'] == route]['send_to_topic'])[0]

                    if next_topic is not None:
                        produce(next_topic, data)

                    # Update the progress count by 1
                    query = 'UPDATE `process_queue` SET `status`=%s, `completed_processes`=`completed_processes`+1 WHERE `case_id`=%s'
                    queue_db.execute(query, params=[success_message, case_id])
                    consumer.commit()
                else:
                    # It is the last message. So update file status to completed.
                    query = 'UPDATE `process_queue` SET `status`=%s, `case_lock`=0, `completed_processes`=`completed_processes`+1 WHERE `case_id`=%s'
                    queue_db.execute(query, params=[success_message, case_id])
                    consumer.commit()
            else:
                # Unlock the case.
                query = 'UPDATE `process_queue` SET `status`=%s, `case_lock`=0, `failure_status`=1 WHERE `case_id`=%s'
                queue_db.execute(query, params=[failure_message, case_id])
                consumer.commit()
    except:
        logging.exception('Something went wrong in consumer. Check trace.')

if __name__ == '__main__':
    consume()
