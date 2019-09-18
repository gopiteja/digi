import Lib
import logging
import pandas as pd
import json
import datetime
from db_utils import DB


__methods__ = [] # self is a BusinessRules Object
register_method = Lib.register_method(__methods__)

@register_method
def evaluate_static(self, function, parameters):
    if function == 'Assign':
        return self.doAssign(parameters)
    if function == 'AssignQ':
        return self.doAssignQ(parameters)
    if function == 'Add':
        return self.doAdd(parameters)
    if function == 'CompareKeyValue':
        return self.doCompareKeyValue(parameters)
    if function == 'GetLength':
        return self.doGetLength(parameters)
    if function == 'GetRange':
        return self.doGetRange(parameters)
    if function == 'Select':
        return self.doSelect(parameters)
    if function == 'Transform':
        return self.doTransform(parameters)
    if function == 'Count':
        return self.doCount(parameters)
    if function == 'Contains':
        return self.doContains(parameters)
    if function == 'ContainsCPT':
        return self.doContainsCPT(parameters)
    if function == 'CheckMultipleCategory':
        return self.doCheckMultipleCategory(parameters)
    if function == 'CheckMultipleCategoryPA':
        return self.doCheckMultipleCategoryPA(parameters)
    if function == 'CheckDate':
        return self.doCheckDate(parameters)
    if function == 'DeleteRow':
        return self.doDeleteRow(parameters)
    if function == 'ContainsCPTandState':
        return self.doContainsCPTandState(parameters)
    if function == 'UpdateNewCase':
        return self.doUpdateNewCase(parameters)
    
    

@register_method
def doAdd(self, parameters):
    """Adds one to the paramter and returns the value"""
    print (f"parameters areeeeeeeeeeeeeeeee {parameters}")
    value = float(self.get_param_value(parameters[0]))
    print (f"HEREEEEEEEEEEEE {value}")
    return value + 1

@register_method
def doGetLength(self, parameters):
    """Returns the lenght of the parameter value.
    Args:
        parameters (dict): The parameter from which the needs to be taken. 
    eg:
       'parameters': {'param':{'source':'input', 'value':5},
                      }
    Note:
        1) Recursive evaluations of rules can be made.
    
    """
    try:
        value = len(self.get_param_value(parameters['param']))
    except Exception as e:
        logging.error(e)
        logging.error(f"giving the defalut lenght 0")
        value = 0
    return value

@register_method
def doGetRange(self, parameters):
    """Returns the parameter value within the specific range.
    Args:
        parameters (dict): The source parameter and the range we have to take into. 
    eg:
       'parameters': {'value':{'source':'input', 'value':5},
                        'range':{'start_index': 0, 'end_index': 4}
                      }
    Note:
        1) Recursive evaluations of rules can be made for the parameter value.
        2) Range is the python range kind of (exclusive of the end_index)
    """
    logging.info(f"parameters got are {parameters}")
    value = self.get_param_value(parameters['value'])
    range_ = parameters['range']
    start_index = range_['start_index']
    end_index = range_['end_index']
    try:
        return (str(value)[start_index: end_index])
    except Exception as e:
        logging.error(f"some error in the range function")
        logging.error(e)
    return ""

@register_method
def doSelect(self, parameters):
    """Returns the vlookup value from the tables.
    Args:
        parameters (dict): The table from which we have to select and the where conditions. 
    eg:
        'parameters': {
            'from_table': 'ocr',
            'select_column': 'highlight',
            'lookup_filters':[
                {
                    'column_name': 'Vendor GSTIN',
                    'compare_with':  {'source':'input', 'value':5}
                },
                {
                    'column_name': 'DRL GSTIN',
                    'compare_with':  {'source':'input', 'value':5}
                },
            ]
        }
    Note:
        1) Recursive evaluations of rules can be made for the parameter value.
        2) Its like vlook up in the dataframe and the from_table must have the primary key...case_id.
    """
    logging.info(f"parameters got are {parameters}")
    from_table = parameters['from_table']
    column_name_to_select = parameters['select_column']
    lookup_filters = parameters['lookup_filters']

    # convert the from_table dictionary into pandas dataframe
    try:
        master_data = self.data_source[from_table]
    except Exception as e:
        logging.error(f"data source does not have the table {from_table}")
        logging.error(e)
        master_data = {}

    master_df = pd.DataFrame(master_data) 

    # build the query
    query = ""
    for lookup in lookup_filters:
        lookup_column = lookup['column_name']
        compare_value = self.get_param_value(lookup['compare_with'])
        query += f"{lookup_column} == {compare_value} & "
    query = query.strip(' & ') # the final strip for the extra &
    result_df = master_df.query(query)

    # get the wanted column from the dataframe
    if not result_df.empty:
        try:
            return result_df[column_name_to_select][0] # just return the first value of the matches
        except Exception as e:
            logging.error(f"error in selecting the required data from the result")
            logging.error(e)
            return ""

@register_method
def doTransform(self,parameters) :
    """Returns the evalated data of given equations
    Args:
        parameters (dict): The source parameter which includes values and operators.
    eg:
        'parameters':[
            {'param':{'source':'input', 'value':5}},
            {'operator':'+'},
            {'param':{'source':'input', 'value':7}},
            {'operator':'-'},
            {'param':{'source':'input', 'value':1}},
            {'operator':'*'},
            {'param':{'source':'input', 'value':3}}
        ]
    Note:
        1) Recursive evaluations of rules can be made.
    """
    equation = ''
    logging.info(f"parameters got are {parameters}")
    for dic in parameters :
        for element,number_operator in dic.items() :
            if element == 'param' :
                value = f'{self.get_param_value(number_operator)}'
            elif element == 'operator' :
                value = f' {number_operator} '
        equation = equation + value
    return(eval(equation))

@register_method
def doContains(self,parameters):
    """ Returns true value if the data is present in the data_source
    Args:
        parameters (dict): The source parameter which includes values that should be checked.
    eg:
            cpt_check_rule = {'rule_type': 'static',
                'function': 'Contains',
                'parameters': { 'table_name': 'ocr','column_name': 'cpt_codes',
                                'value':{'source':'input', 'value':92610}
                        }
            }
    """
    logging.info(f"parameters got are {parameters}")
    table_name = parameters['table_name']
    column_name = parameters['column_name']
    value = self.get_param_value(parameters['value'])
    print(value)
    if value in self.data_source[table_name][column_name]:
        return True
    else :
        return False

@register_method
def doCheckMultipleCategory(self,parameters):
    """ 
    Returns type of the data received or else returns false
    Args:
        parameters (dict): The source parameter which includes values that to be checked.
    eg:
    prior_auth_rule1 = { 'rule_type' : 'static' ,
        'function': 'CheckMultipleCategory',
        'parameters': {
                'value':{'source':'input_config', 'table': 'master','column': 'CPT_Code' }
        }
        }
    """
    logging.info(f"parameters got are {parameters}")
    value = self.get_param_value(parameters['value'])
    #print(value)
    #cpt_codes = value.split(',')
    # cpt_codes = json.loads(value)
    # print ("hereeeeeeeeeee",cpt_codes)
    try:
        
        value = json.loads(value)
        
        # presumed format....alorica specific....[{"header":["CPT Code","Total Units"],"rowData":[]}]
        cpt_codes = [e["CPT Code"] for e in value[0]["rowData"]]
    except Exception as e:
        logging.error("JSON COULD NOT BE LOADED")
        logging.error(e)
        cpt_codes = []

    categories = []
    master_df = pd.DataFrame(self.data_source['master'])
    print (master_df)
    for code in cpt_codes:
        try:
            categories.append(list(master_df[master_df['CPT_Code'] == str(code)]['Category'])[0])
        except Exception as e:
            print(e)
    #print ('**********',categories)
    return len(set(categories)) == 1

@register_method
def doCheckMultipleCategoryPA(self,parameters):
    """ 
    Returns type of the data received or else returns false
    Args:
        parameters (dict): The source parameter which includes values that to be checked.
    eg:
    prior_auth_rule1 = { 'rule_type' : 'static' ,
        'function': 'CheckMultipleCategoryPA',
        'parameters': {
                'value':{'source':'input_config', 'table': 'master','column': 'CPT_Code' }
        }
        }
    """
    logging.info(f"parameters got are {parameters}")
    value = self.get_param_value(parameters['value'])
    print(value)
    #cpt_codes = value.split(',')
    # cpt_codes = json.loads(value)
    
    try:
        
        value = json.loads(value)
        
        # presumed format....alorica specific....[{"header":["CPT Code","Total Units"],"rowData":[]}]
        cpt_codes = [e["CPT Code"] for e in value[0]["rowData"]]
    except Exception as e:
        logging.error("JSON COULD NOT BE LOADED")
        logging.error(e)
        cpt_codes = []
    
    print ("hereeeeeeeeeee",cpt_codes)
    categories = []
    master_df = pd.DataFrame(self.data_source['master'])
    for code in cpt_codes:
        try:
            categories.append(list(master_df[master_df['CPT_Code'] == str(code)]['PA_Reqd'])[0])
        except Exception as e:
            print ("exception",e)
    return 'required' in categories


@register_method
def doCount(self, parameters):
    """Returns the count of records from the tables.
    Args:
        parameters (dict): The table from which we have to select and the where conditions. 
    eg:
        'parameters': {
            'from_table': 'ocr',
            'lookup_filters':[
                {
                    'column_name': 'Vendor GSTIN',
                    'compare_with':  {'source':'input', 'value':5}
                },
                {
                    'column_name': 'DRL GSTIN',
                    'compare_with':  {'source':'input', 'value':5}
                },
            ]
        }
    Note:
        1) Recursive evaluations of rules can be made for the parameter value.
        2) Its like vlook up in the dataframe and the from_table must have the primary key...case_id.
    """
    logging.info(f"parameters got are {parameters}")
    from_table = parameters['from_table']
    lookup_filters = parameters['lookup_filters']

    # convert the from_table dictionary into pandas dataframe
    try:
        master_data = self.data_source[from_table]
    except Exception as e:
        logging.error(f"data source does not have the table {from_table}")
        logging.error(e)
        master_data = {}

    master_df = pd.DataFrame(master_data) 

    # build the query
    query = ""
    for lookup in lookup_filters:
        lookup_column = lookup['column_name']
        compare_value = self.get_param_value(lookup['compare_with'])
        query += f"{lookup_column} == {compare_value} & "
    query = query.strip(' & ') # the final strip for the extra &
    result_df = master_df.query(query)

    # get the wanted column from the dataframe
    if not result_df.empty:
        try:
            return len(result_df) # just return the first value of the matches
        except Exception as e:
            logging.error(f"error in selecting the required data from the result")
            logging.error(e)
            return 0
    else:
        return 0


@register_method
def doCheckDate(self,parameters):
    """
    Args:
        parameters (dict): The source parameter which includes values that should be checked.
    eg:
        date_validate_rule = { 'rule_type': 'static',
            'function': 'CheckDate',
            'parameters': {'value':{'source':'input_config', 'table':'ocr', 'column': 'End_date'}}

        }
    """
    logging.info(f"parameters got are {parameters}")
    value = self.get_param_value(parameters['value'])

    try:
        if value == '':
            return True
        elif datetime.date.today() < value:
            return True
        return False
    except Exception as e:
        logging.error(f"error in checking end date")
        logging.error(e)
        return False


@register_method
def doContainsCPT(self,parameters):
    """ Returns true value if the data is present in the data_source
    Args:
        parameters (dict): The source parameter which includes values that should be checked.
    eg:
        cpt_check_rule = {'rule_type': 'static',
        'function': 'ContainsCPT',
        'parameters': { 'table_name': 'master','column_name': 'CPT_Code',
                       'value':{'source':'input_config', 'table':'ocr', 'column': 'CPT_Codes'}
                      }
            }
    """
    logging.info(f"parameters got are {parameters}")
    table_name = parameters['table_name']
    column_name = parameters['column_name']
    value = self.get_param_value(parameters['value'])
    #value = value.split(',')
    try:
        value = json.loads(value)
        
        # presumed format....alorica specific....[{"header":["CPT Code","Total Units"],"rowData":[]}]
        # codes = [e[0] for e in value[0]["rowData"]]
        codes = [e["CPT Code"] for e in value[0]["rowData"]]
        
        # codes = value.keys()
        for code in codes:
            if code in self.data_source[table_name][column_name]:
                return True
    except Exception as e:
        logging.error(f"Cant load the json format table:{parameters['value']['table']} column:{parameters['value']['column']}")
        logging.error(e)
        return False
    return False


# @register_method
# def doCountTotalUnits(self,parameters):
#     """ 
#         Return total no.of units.
#     Args:
#         parameters (dict): The source parameter which includes values that should be checked.
#     eg:
#             cpt_check_rule = {'rule_type': 'static',
#                 'function': 'doCountTotalUnits',
#                 'parameters': { 'table_name': 'ocr','column_name': 'cpt_codes',
#                                 'value':{'source':'input', 'value':92610}
#                         }
#             }
#     Note : for cpt_codes format {"code":"units","code":"units","code":"units"}
#     """
#     logging.info(f"parameters got are {parameters}")
#     table_name = parameters['table_name']
#     column_name = parameters['column_name']
#     value = self.get_param_value(parameters['value'])
#     value = json.loads(value)
#     total = 0
#     for code,unit in value:
#         if code in self.data_source[table_name][column_name]:
#             total = total + float(unit)
#     return total
# 

@register_method
def doContainsCPTandState(self,parameters):
    """ Returns true value if the data is present in the data_source
    Args:
        parameters (dict): The source parameter which includes values that should be checked.
    eg:
         CPT_State_rule = {'rule_type': 'static',
                'function': 'Contains',
                'parameters': { 'table_name1': 'ocr','column_name1': 'cpt_codes',
                                'table_name2': 'ocr','column_name2': 'state',
                                'value1':{'source':'input_config', 'table':'ocr', 'column': 'CPT_Codes'},
                                'value2':{'source':'input_config', 'table':'ocr', 'column': 'STATE'}
                        }
            }
    """
    logging.info(f"parameters got are {parameters}")
    table_name_cpt = parameters['table_name1']
    column_name_cpt = parameters['column_name1']
    table_name_state = parameters['table_name2']
    column_name_state = parameters['column_name2']
    value_cpt = self.get_param_value(parameters['value1'])
    value_state = self.get_param_value(parameters['value2'])
    try:
        value_cpt = json.loads(value_cpt)
        
        # presumed format....alorica specific....[{"header":["CPT Code","Total Units"],"rowData":[]}]
        # codes = [e[0] for e in value[0]["rowData"]]
        codes = [e["CPT Code"] for e in value_cpt[0]["rowData"]]
        # codes = value.keys()
        for code in codes:
            if (code,value_state) in zip(self.data_source[table_name_cpt][column_name_cpt] , self.data_source[table_name_state][column_name_state]) :
                return True
    except Exception as e:
        logging.error(f"Cant load the json format table:{parameters['value1']['table']} column:{parameters['value1']['column']}")
        logging.error(e)
        return False
    return False


@register_method
def doDeleteRow(self,parameters):
    """ Delete the data in table for particular fax unique id
    Args:
        parameters (dict): The source parameter which includes values that should be deleted.
    eg:
        delete_row_rule = {'function': 'DeleteRow',
        'parameters': { 
                       'database':'alorica_data',
                       'tables': ['demographics','eligibility','insurance','history','member','provider']
                      }
        }
    """
    logging.info(f"parameters got are {parameters}")
    database = parameters['database']
    tables = parameters['tables']
    query = ""
    try:
        for table in tables:
            query = f"DELETE FROM `{table}` WHERE `Fax_unique_id`='{self.case_id}'"

            logging.info(f"Deleting the data in table {table}")
            db_ob = db.DB(database)
            db_ob.execute(query)
        return True
    except Exception as e:
        logging.error("Cannot delete data from table")
        logging.error(e)
        return False
    
    
@register_method
def doSelectandAssign(self, parameters):
    """Returns the vlookup value from the tables.
    Args:
        parameters (dict): The table from which we have to select and the where conditions. 
    eg:
        'parameters': {
            'from_table': 'ocr',
            'select_column': 'highlight',
            'lookup_filters':[
                {
                    'column_name': 'Vendor GSTIN',
                    'compare_with':  {'source':'input', 'value':5}
                },
                {
                    'column_name': 'DRL GSTIN',
                    'compare_with':  {'source':'input', 'value':5}
                },
            ]
        }
    Note:
        1) Recursive evaluations of rules can be made for the parameter value.
        2) Its like vlook up in the dataframe and the from_table must have the primary key...case_id.
    """
    logging.info(f"parameters got are {parameters}")
    from_table = parameters['from_table']
    column_name_to_select = parameters['select_column']
    lookup_filters = parameters['lookup_filters']

    # convert the from_table dictionary into pandas dataframe
    try:
        master_data = self.data_source[from_table]
    except Exception as e:
        logging.error(f"data source does not have the table {from_table}")
        logging.error(e)
        master_data = {}

    master_df = pd.DataFrame(master_data) 

    # build the query
    query = ""
    for lookup in lookup_filters:
        lookup_column = lookup['column_name']
        compare_value = self.get_param_value(lookup['compare_with'])
        query += f"{lookup_column} == {compare_value} & "
    query = query.strip(' & ') # the final strip for the extra &
    result_df = master_df.query(query)

    
    # here hopefullyy always gets only one column or no column
    if not result_df.empty:
        try:
            return result_df[column_name_to_select][0] # just return the first value of the matches
        except Exception as e:
            logging.error(f"error in selecting the required data from the result")
            logging.error(e)
            return ""
    return False

    # get the wanted column from the dataframe
    if not result_df.empty:
        try:
            return result_df[column_name_to_select][0] # just return the first value of the matches
        except Exception as e:
            logging.error(f"error in selecting the required data from the result")
            logging.error(e)
            return ""



def update_fax_matched(where):
    from db_utils import DB
    db = DB('alorica_data')

    providers = db.get_all('Provider', condition=where)

    if providers.empty:
        return False, None
    if len(providers) == 1:
        db.update('Provider', update={'fax_matched': 1}, where=where)
        return True,providers
    return False, None
    

#### very very specifi to alorica
@register_method
def doUpdateNewCase(self, parameters):
    """Returns the vlookup value from the tables.
    Args:
        parameters (dict): The table from which we have to select and the where conditions. 
    eg:
        'parameters': {
            'from_table': 'Provider',
            'update_column': 'fax_matched',
            'update_value': '1',
            'lookup_filters':[
                {
                    'column_name': 'State',
                    'compare_with':  {'source':'input_config', 'table': 'ocr','column': 'State' }
                },
                {
                    'column_name': 'Name',
                    'compare_with':  {'source':'input_config', 'table': 'ocr','column': 'Name' }
                },
               
            ]
        }
    Note:
        1) Recursive evaluations of rules can be made for the parameter value.
        2) Its like vlook up in the dataframe and the from_table must have the primary key...case_id.
    """
    try:
        
        logging.info(f"parameters got are {parameters}")
        from_table = parameters['from_table']
        # column_name_to_select = parameters['select_column']
        lookup_filters = parameters['lookup_filters']

        fax_matched_where = {
            'Fax_unique_id': self.case_id,
            'Type_Of_Provider':'Service'
        }
        
        for lu_filter in lookup_filters:
            fax_matched_where[lu_filter['column_name']] = self.get_param_value(lu_filter['compare_with'])
        

        if 'Name' in fax_matched_where:
            Service_name = fax_matched_where['Name']['Service']
            Requesting_name = fax_matched_where['Name']['Requesting']
            
            fax_matched_where['Name'] = Service_name

        service_unique, service_record = update_fax_matched(fax_matched_where)
        

        if 'Name' in fax_matched_where:
            fax_matched_where['Name'] = Requesting_name

        fax_matched_where['Type_Of_Provider'] = 'Requesting'

        
        request_unique, request_record = update_fax_matched(fax_matched_where)
        from db_utils import DB
        if service_unique and request_unique:
            if list(service_record['Contracted_Status'])[0].strip().lower() == 'both' and list(request_record['Contracted_Status'])[0].strip().lower() == 'both':
                # update end_contact
                # from db_utils import DB
                db = DB('queues')
                where = {'case_id':self.case_id}
                updates = {'case_type':'end contact'}
                db.update('process_queue', updates, where=where)
            else:
                # from db_utils import DB
                db = DB('queues')
                where = {'case_id':self.case_id}
                updates = {'case_type':'new case'}
                db.update('process_queue', updates, where=where)
                
        db = DB('queues')
        where = {'case_id':self.case_id}
        updates = {'case_type':'end contact'}
        db.update('process_queue', updates, where=where)
        return True
    except Exception as e:
        logging.error('New case error')
        logging.error(e)
        return False
    return False
    