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

def to_DT_data(parameters):
    """Amith's processing for parameters"""
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

def get_data_sources(tenant_id, case_id, column_name, master=False):
    """Helper to get all the required table data for the businesss rules to apply
    """
    get_datasources_query = "SELECT * from `data_sources`"
    business_rules_db = DB('business_rules', tenant_id=tenant_id, **db_config)
    data_sources = business_rules_db.execute(get_datasources_query)


    # sources
    sources = json.loads(list(data_sources[column_name])[0])
    
    
    data = {}
    for database, tables in sources.items():
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

def run_chained_rules(case_id, tenant_id, chain_rules, start_rule_id=None, updated_tables=False, trace_exec=None, rule_params=None):
    """Execute the chained rules"""
    
    # get the mapping of the rules...basically a rule_id maps to a rule
    rule_id_mapping = {}
    for ind, rule in chain_rules.iterrows():
        rule_id_mapping[rule['rule_id']] = [rule['rule_string'], rule['next_if_sucess'], rule['next_if_failure'], rule['stage'], rule['description'], rule['data_source']]
    logging.info(f"\n rule id mapping is \n{rule_id_mapping}\n")
    
    # evaluate the rules one by one as chained
    # start_rule_id = None
    if start_rule_id is None:
        if rule_id_mapping.keys():
            start_rule_id = list(rule_id_mapping.keys())[0]
            trace_exec = []
            rule_params = {}
            
    # if start_rule_id then. coming from other service 
    # get the existing trace and rule params data
    business_rules_db = DB('business_rules', tenant_id=tenant_id, **db_config)
    rule_data_query = "SELECT * from `rule_data` where `case_id`=%s"
    params = [case_id]
    df = business_rules_db.execute(rule_data_query, params=params)
    try:
        trace_exec = json.loads(list(df['trace_data'])[0])
        logging.info(f"\nexistig trace exec is \n{trace_exec}\n")
    except Exception as e:
        logging.info(f"no existing trace data")
        logging.info(f"{str(e)}")
        trace_exec = []
    
    try:
        rule_params = json.loads(list(df['rule_params'])[0])
        logging.info(f"\nexistig rule_params is \n{rule_params}\n")
    except Exception as e:
        logging.info(f"no existing rule params data")
        logging.info(f"{str(e)}")
        rule_params = {}
      
    # usually master data will not get updated...for every rule
    master_data_tables = get_data_sources(tenant_id, case_id, 'master', master=True)
 
    logging.info(f"\nStart rule id got is {start_rule_id}\n ")
    while start_rule_id != "END":
        # get the rules, next rule id to be evaluated
        rule_to_evaluate, next_if_sucess, next_if_failure, stage, description, data_source = rule_id_mapping[str(start_rule_id)]  
    
        logging.info(f"\nInside the loop \n rule_to_evaluate  {rule_to_evaluate}\n \
                      \nnext_if_sucess {next_if_sucess}\n \
                      \nnext_if_failure {next_if_failure}\n ")
        
        # update the data_table if there is any change
        case_id_data_tables = get_data_sources(tenant_id, case_id, 'case_id_based')
        master_updated_tables = {} 
        if updated_tables:
            master_updated_tables = get_data_sources(tenant_id, case_id, 'updated_tables')
        # consolidate the data into data_tables
        data_tables = {**case_id_data_tables, **master_data_tables, **master_updated_tables} 
        
        # evaluate the rule
        rules = [json.loads(rule_to_evaluate)] 
        BR  = BusinessRules(case_id, rules, data_tables)
        decision = BR.evaluate_rule(rules[0])
        
        logging.info(f"\n got the decision {decision} for the rule id {start_rule_id}")
        logging.info(f"\n updates got are {BR.changed_fields}")
        
        updates = {}
        # update the updates if any
        if BR.changed_fields:
            updates = BR.changed_fields
            update_tables(case_id, tenant_id, updates)

        
        # update the trace_data
        trace_exec.append(start_rule_id)

        logging.info(f"\n params data used from the rules are \n {BR.params_data}\n")
        # update the rule_params
        trace_dict = {
                        str(start_rule_id):{
                            'description' : description if description else 'No description available in the database',
                            'output' : "",
                            'input' : to_DT_data(BR.params_data['input'])
                            }
                        }
        rule_params.update(trace_dict)
        # update the start_rule_id based on the decision
        if decision:
            start_rule_id = next_if_sucess
        else:
            start_rule_id = next_if_failure
        logging.info(f"\n next rule id to execute is {start_rule_id}\n")
        
    
    # off by one updates...
    trace_exec.append(start_rule_id)
    
    # store the trace_exec and rule_params in the database
    update_rule_params_query = f"INSERT INTO `rule_data`(`id`, `case_id`, `rule_params`) VALUES ('NULL',%s,%s) ON DUPLICATE KEY UPDATE `rule_params`=%s"
    params = [case_id, json.dumps(rule_params), json.dumps(rule_params)]
    business_rules_db.execute(update_rule_params_query, params=params)
    
    update_trace_exec_query = f"INSERT INTO `rule_data` (`id`, `case_id`, `trace_data`) VALUES ('NULL',%s,%s) ON DUPLICATE KEY UPDATE `trace_data`=%s"
    params = [case_id, json.dumps(trace_exec), json.dumps(trace_exec)]
    business_rules_db.execute(update_trace_exec_query, params=params)
    
    logging.info("\n Applied chained rules successfully")
    return 'Applied chained rules successfully'

def run_group_rules(case_id, rules, data):
    """Run the rules"""
    rules = [json.loads(rule) for rule in rules] 
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
        case_id_data_tables = get_data_sources(tenant_id, case_id, 'case_id_based') 
        master_data_tables = get_data_sources(tenant_id, case_id, 'master', master=True)
        
        # consolidate the data into data_tables
        data_tables = {**case_id_data_tables, **master_data_tables} 
        
        logging.info(f"\ndata got from the tables is\n")
        logging.info(data_tables)
        
        updates = {}
        # apply business rules
        if is_chain_rule:
            run_chained_rules(case_id, tenant_id, rules)
        else:
            updates = run_group_rules(case_id, list(rules['rule_string']), data_tables)
            
        # update in the database, the changed fields eventually when all the stage rules were got
        update_tables(case_id, tenant_id, updates)
        
        #  return the updates for viewing
        return {'flag': True, 'message': 'Applied business rules successfully.', 'updates':updates}
    except Exception as e:
        logging.exception('Something went wrong while applying business rules. Check trace.')
        return {'flag': False, 'message': 'Something went wrong while applying business rules. Check logs.', 'error':str(e)}
