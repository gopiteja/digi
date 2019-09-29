def get_rules(stage, tenant_id):
    """Get the rules based on the stage, tenant_id"""
    return []

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
        # get the stage wise rules
        stage = function_params['stage'][0]
        
        # get the rules
        rules = get_rules(stage, tenant_id)
        # apply business rules
        
        # update in the database, the changed fields eventually when all the stage rules were got
        
        #  return the updates for viewing
        return {'flag': True, 'message': 'Applied business rules successfully.', 'updates':updates}
    except Exception as e:
        logging.exception('Something went wrong while applying business rules. Check trace.')
        return {'flag': False, 'message': 'Something went wrong saving changes. Check logs.', 'error':str(e)}
