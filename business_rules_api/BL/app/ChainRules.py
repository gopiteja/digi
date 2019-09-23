import db_utils as db

def get_chain_rules(data_base):
    """Getting the rule_string, next_if_sucess and next_if_failure data from the database
    """
    business_rule_db = db.DB(data_base)
    df = business_rule_db.execute("SELECT `rule_string`, `next_if_sucess`, `next_if_failure` from `sequence_data`")
    chained_rules = [[e['rule_string'], e['next_if_sucess'], e['next_if_failure']] for e in df.to_dict(orient='records') ]
    return(evaluate_chained_rule(chained_rules))



def evaluate_chained_rule(rules):
    """Evaluate the chained specific rules
    """
    rules_id_mapping = {i:rule for i,rule in enumerate(rules)}
    rule_id = 0
    while (rule_id != "END" and (int(rule_id) < len(rules))):
        rule_string, next_ruleid_if_success, next_ruleid_if_fail = rules_id_mapping[rule_id]
        
        
        
        decision = True # here evaluate the rule using business rules class
        
        if decision:
            rule_id =  next_ruleid_if_success
        else:
            rule_id = next_ruleid_if_fail
    return rule_id




if(__name__) == "__main__" :
    rule_id = get_chain_rules('business_rules')
    print(rule_id)