# comment below two for local testing
from ace_logger import Logging
logging = Logging()

# uncomment these below lines for local testing
# import logging 
# logger=logging.getLogger() 
# logger.setLevel(logging.DEBUG) 



import json
import os
from db_utils import DB 

from BusinessRules import BusinessRules

# one configuration
db_config = {
    'host': os.environ['HOST_IP'],
    'user': os.environ['LOCAL_DB_USER'],
    'password': os.environ['LOCAL_DB_PASSWORD'],
    'port': os.environ['LOCAL_DB_PORT']
}

def get_data_sources(tenant_id, case_id, master=False):
    """Helper to get all the required table data for the businesss rules to apply
    """
    get_datasources_query = "SELECT * from `data_sources`"
    business_rules_db = DB('business_rules', tenant_id=tenant_id, **db_config)
    data_sources = business_rules_db.execute(get_datasources_query)

    # case_id based
    case_id_based_sources = json.loads(list(data_sources['case_id_based'])[0])
    
    data = {}
    for database, tables in case_id_based_sources.items():
        db = DB(database, tenant_id=tenant_id, **db_config)
        for table in tables:
            if master:
                query = f"SELECT * from `{table}`"
                df = db.execute(query)
            else:
                query = f"SELECT * from `{table}` WHERE case_id = %s"
                params = [case_id]
                df = db.execute(query, params=params)
            if not df.empty:
                data[table] = df.to_dict(orient='records')[0]
            else:
                data[table] = {}
    
    
    case_id_based_sources = json.loads(list(data_sources['case_id_based'])[0])
    
    return data
                
def get_rules(tenant_id, group):
    """Get the rules based on the stage, tenant_id"""
    business_rules_db = DB('business_rules', tenant_id=tenant_id, **db_config)
    get_rules_query = "SELECT * from `sequence_rule_data` where `group` = %s"
    params = [group]
    rules = business_rules_db.execute(get_rules_query, params=params)
    return rules

def update_tables(case_id, tenant_id, updates):
    """Update the values in the database"""
    extraction_db = DB('extraction', tenant_id=tenant_id, **db_config) # only in ocr or process_queue we are updating
    queue_db = DB('queues', tenant_id=tenant_id, **db_config) # only in ocr or process_queue we are updating
    
    for table, colum_values in updates.items():
        if table == 'ocr':
            extraction_db.update(table, update=colum_values, where={'case_id':case_id})
        if table == 'process_queue':
            queue_db.update(table, update=colum_values, where={'case_id':case_id})
    return "UPDATED IN THE DATABASE SUCCESSFULLY"

def run_group_rules(case_id, rules, data):
    """Run the rules"""
    rules = [json.loads(rule) for rule in list(rules['rule_string'])] 
    BR  = BusinessRules(case_id, rules, data)
    updates = BR.evaluate_business_rules()
    
    logging.info(f"\n updates from the group rules are \n{updates}\n")
    return updates

def apply_business_rule(case_id, function_params, tenant_id):
    """Run the business rules based on the stage in function params and tenant_id
    Args:
        case_id: Unique id that we pass
        function_params: Parameters that we get from the configurations
        tenant_id: Tenant on which we have to apply the rules
    Returns:

    """
    updates = {} # keep a track of updates that are being made by business rules
    try:
        # get the stage from the function_parameters...As of now its first ele..
        # need to make generic or key-value pairs
        logging.info(f"\n case_id {case_id} \nfunction_params {function_params} \ntenant_id {tenant_id}\n")
        stage = function_params['stage'][0]
        
        
        # get the rules
        rules = get_rules(tenant_id, stage)
        
        # get the mapping of the rules...basically a rule_id maps to a rule.
        # useful for the chain rule evaluations
        rule_id_mapping = {}
        for ind, rule in rules.iterrows():
            rule_id_mapping[rule['rule_id']] = [rule['rule_string'], rule['next_if_sucess'], rule['next_if_failure'], rule['stage'], rule['description'], rule['data_source']]

        # making it generic takes to take a type parameter from the database..
        # As of now make it (all others  or chained) only
        is_chain_rule = '' not in rule_id_mapping
        
        # get the required table data on which we will be applying business_rules  
        data_tables = get_data_sources(tenant_id, case_id) 
        
        logging.info(f"\ndata got from the tables is\n")
        logging.info(data_tables)
        # apply business rules
        if is_chain_rule:
            # updates = run_chained_rules()
            pass
        else:
            updates = run_group_rules(case_id, rules, data_tables)
            
        
        # update in the database, the changed fields eventually when all the stage rules were got
        update_tables(case_id, tenant_id, updates)
        
        #  return the updates for viewing
        return {'flag': True, 'message': 'Applied business rules successfully.', 'updates':updates}
    except Exception as e:
        logging.exception('Something went wrong while applying business rules. Check trace.')
        return {'flag': False, 'message': 'Something went wrong while applying business rules. Check logs.', 'error':str(e)}
