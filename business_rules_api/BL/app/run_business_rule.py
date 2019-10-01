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
     

if __name__ == '__main__':
    consume()
