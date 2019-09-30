import Lib
import _StaticFunctions
import _BooleanReturnFunctions
import _AssignFunction

try:
    from app.ace_logger import Logging
except:
    from ace_logger import Logging
    
logging = Logging()


@Lib.add_methods_from(_StaticFunctions, _BooleanReturnFunctions, _AssignFunction) 
class BusinessRules():
    
    def __init__(self, case_id, rules, table_data, decision = False):
        self.case_id = case_id
        self.rules = rules
        self.data_source = table_data
        self.changed_fields = {}
        self.is_decision = decision
        self.params_data = {}
        self.params_data['input'] = []

    def evaluate_business_rules(self):
        """Evaluate all the rules"""
        for rule in self.rules:
            logging.info("\n Evaluating the rule: " +f"{rule} \n")
            output = self.evaluate_rule(rule)
            logging.info("\n Output: " +f"{output} \n")
        # update the changes fields in database
        logging.info(f"\nchanged fields are \n{self.changed_fields}\n")
        return self.changed_fields
    
    def evaluate_rule(self,rule):
        logging.info(f"\nEvaluating the rule \n{rule}\n")

        rule_type = rule['rule_type']
        
        if  rule_type == 'static':
            function_name = rule['function']
            parameters = rule['parameters']
            return  self.evaluate_static(function_name, parameters)
    
        if rule_type == 'condition':
            evaluations = rule['evaluations']
            return self.evaluate_condition(evaluations)
    
    def conditions_met(self, conditions):
        """Evaluate the conditions and give out the final decisoin
        
        """
        eval_string = ''
        # return True if there are no conditions...that means we are doing else..
        if not conditions:
            return True
        # evaluate the conditions
        for condition in conditions:
            logging.info(f"Evaluting the condition {condition}")
            if condition == 'AND' or condition == 'OR':
                eval_string += ' '+condition.lower()+' '
            else:
                eval_string += ' '+str(self.evaluate_rule(condition))+' '
        logging.info(f"\n eval string is {eval_string} \n output is {eval(eval_string)}")
        return eval(eval_string)

    def evaluate_condition(self, evaluations):
        """Execute the conditional statements.

        Args:
            evaluations(dict) 
        Returns:
            decision(boolean) If its is_decision.
            True If conditions met and it is done with executions.
            False For any other case (scenario).
        """
        for each_if_conditions in evaluations:
            conditions = each_if_conditions['conditions']
            executions = each_if_conditions['executions']
            logging.info(f'\nconditions got are \n{conditions}\n')
            logging.info(f'\nexecutions got are \n{executions}\n')
            decision = self.conditions_met(conditions)
            
            """
            Why this self.is_decision and decision ?
                In decison tree there are only one set of conditions to check
                But other condition rules might have (elif conditions which needs to be evaluate) 
            """
            if self.is_decision:
                if decision:
                    for rule in executions:
                        self.evaluate_rule(rule)
                logging.info(f"\n Decision got for the (for decision tree) condition\n {decision}")    
                return decision
            if decision:
                for rule in executions:
                    self.evaluate_rule(rule)
                return True
        return False

    def get_param_value(self, param_object):
        """Returns the parameter value.

        Args:
            param_object(dict) The param dict from which we will parse and get the value.
        Returns:
            The value of the parameter
        Note:
            It returns a value of type we have defined. 
            If the parameter is itself a rule then it evaluates the rule and returns the value.
        """
        logging.info(f"\nPARAM OBJECT IS {param_object}\n")
        param_source = param_object['source']
        if param_source == 'input_config':
            table_key = param_object['table']
            column_key = param_object['column']
            table_key = table_key.strip() # strip for extra spaces
            column_key = column_key.strip() # strip for extra spaces
            logging.debug(f"\ntable is {table_key} and column key is {column_key}\n")
            try:
                data = {}
                # update params data
                data['type'] = 'from_table'
                data['table'] = table_key
                data['column'] = column_key
                data['value'] = self.data_source[table_key][column_key]
                self.params_data['input'].append(data)
                return data['value']
            except Exception as e:
                logging.error(f"\ntable or column key not found\n")
                logging.error(str(e))
                logging.info(f"\ntable data is {self.data_source}\n")
        if param_source == 'rule':
            param_value = param_object['value']
            return self.evaluate_rule(param_value)
        if param_source == 'input':
            param_value = param_object['value']
            param_value = param_value.strip()
            return  param_value
 



























# ###########################################################################################
# ############################## Testings ###################################################
# ###########################################################################################
# # sample rule....
# rule2 = {'rule_type': 'static',
#         'function': 'Add',
#         'parameters': [{'source':'input_config', 'table':'ocr', 'column': 'PO Number'}]
#        }

# rule = {'rule_type': 'static',
#         'function': 'Add',
#         'parameters': [{'source':'rule', 'value':rule2}]
#        }

# rule1 = {'rule_type': 'static',
#         'function': 'Assign',
#         'parameters': {'assign_table':{'table':'ocr', 'column':'PO Number'}, 
#                        'assign_value':{'source':'rule', 'value':rule}
#                       }
#        }

# rule2 = {'rule_type': 'static',
#         'function': 'CompareKeyValue',
#         'parameters': {'left_param':{'source':'input', 'value':5},
#                        'operator':'>',
#                        'right_param':{'source':'input', 'value':4}
#                       }
#        }

# comparision_add_rule = {'rule_type':'condition','evaluations': [{ 'conditions':[rule2], 
#                                                  'executions':[rule1]},
#                     {'conditions':[], 'executions':[]}]}

# ###########################################################################################
# ###########################################################################################

# # test rule ............DRL 1...compare key valuesss....
# test_1_if_assign_rule = {'rule_type': 'static',
#         'function': 'Assign',
#         'parameters': {'assign_table':{'table':'validation', 'column':'PO Number'}, 
#                        'assign_value':{'source':'input', 'value':1}
#                       }
# }
# test_1_else_assign_rule = {'rule_type': 'static',
#         'function': 'Assign',
#         'parameters': {'assign_table':{'table':'validation', 'column':'PO Number'}, 
#                        'assign_value':{'source':'input', 'value':"PO number length is not equal to 10"}
#                       }
# }

# test_1_else1_assign_rule = {'rule_type': 'static',
#         'function': 'Assign',
#         'parameters': {'assign_table':{'table':'process_queue', 'column':'failure_status'}, 
#                        'assign_value':{'source':'input', 'value':"1"}
#                       }
# }
# test1_get_length_rule = {
#     'rule_type':'static',
#     'function': 'GetLength',
#     'parameters': {'param':{'source':'input_config', 'table':'ocr', 'column': 'Patient_first_name'},
#                       }
# }
# test1_compare_key_value_rule = {'rule_type': 'static',
#                 'function': 'CompareKeyValue',
#                 'parameters': {'left_param':{'source':'rule', 'value':test1_get_length_rule},
#                        'operator':'==',
#                        'right_param':{'source':'input', 'value':10}
#                       }
# }
# test_rule1 = {
#     'rule_type':'condition',
#     'evaluations': [{'conditions':[test1_compare_key_value_rule], 'executions': [test_1_if_assign_rule]},
#                     {'conditions':[], 'executions':[test_1_else_assign_rule, test_1_else1_assign_rule]}
#                     ]
# }

# ###########################################################################################
# ###########################################################################################

# # test rule ............DRL 1...compare key valuesss...rangessssss.
# test_range_if_assign_rule = {'rule_type': 'static',
#         'function': 'Assign',
#         'parameters': {'assign_table':{'table':'busiess_rule', 'column':'Tax Code'}, 
#                        'assign_value':{'source':'input', 'value':70}
#                       }
# }
# test_range_else_assign_rule = {'rule_type': 'static',
#         'function': 'Assign',
#         'parameters': {'assign_table':{'table':'busiess_rule', 'column':'Tax Code'}, 
#                        'assign_value':{'source':'input', 'value':73}
#                       }
# }

# test1_get_range_rule_1 = {
#     'rule_type':'static',
#     'function': 'GetRange',
#     'parameters': { 'value':{'source':'input_config', 'table':'ocr', 'column': 'Vendor GSTIN'},
#                         'range':{'start_index': 0, 'end_index': 2}
#                 }
# }
# test1_get_range_rule_2 = {
#     'rule_type':'static',
#     'function': 'GetRange',
#     'parameters': { 'value':{'source':'input_config', 'table':'ocr', 'column': 'DRL GSTIN'},
#                         'range':{'start_index': 0, 'end_index': 2}
#                 }
# }
# test1_range_compare_key_value_rule = {'rule_type': 'static',
#                 'function': 'CompareKeyValue',
#                 'parameters': {'left_param':{'source':'rule', 'value':test1_get_range_rule_1},
#                        'operator':'==',
#                        'right_param':{'source':'rule', 'value':test1_get_range_rule_2}
#                       }
# }
# test_rule1_range = {
#     'rule_type':'condition',
#     'evaluations': [{'conditions':[test1_range_compare_key_value_rule], 'executions': [test_range_if_assign_rule]},
#                     {'conditions':[], 'executions':[test_range_else_assign_rule]}
#                     ]
# }

# ###########################################################################################
# ###########################################################################################

# # test rule2 for seeing source is getting updated or not
# test2_compare_key_value_rule = {'rule_type': 'static',
#                 'function': 'CompareKeyValue',
#                 'parameters': {'left_param':{'source':'input_config', 'table':'validation', 'column': 'PO Number'},
#                        'operator':'==',
#                        'right_param':{'source':'input', 'value':1}
#                       }
# }
# test_2_if_assign_rule = {'rule_type': 'static',
#         'function': 'Assign',
#         'parameters': {'assign_table':{'table':'ocr', 'column':'highlight'}, 
#                        'assign_value':{'source':'input', 'value':""}
#                       }
# }
# test_2_if_assign_rule_1 = {'rule_type': 'static',
#         'function': 'Assign',
#         'parameters': {'assign_table':{'table':'ocr', 'column':'Vendor GSTIN'}, 
#                        'assign_value':{'source':'input', 'value':""}
#                       }

# }
# test_rule2 = {
#     'rule_type':'condition',
#     'evaluations': [{'conditions':[test1_compare_key_value_rule], 'executions': [test_2_if_assign_rule, test_2_if_assign_rule_1]},
#                     {'conditions':[], 'executions':[test_1_else_assign_rule, test_1_else1_assign_rule]}
#                     ]
# }

# ###########################################################################################
# ###########################################################################################
# test3_compare_key_value_rule = {'rule_type': 'static',
#                 'function': 'CompareKeyValue',
#                 'parameters': {'left_param':{'source':'input_config', 'table':'ocr', 'column': 'Invoice Total'},
#                        'operator':'>',
#                        'right_param':{'source':'input', 'value':5000000}
#                       }
# }
# simple_assign_if = {'rule_type': 'static',
#         'function': 'Assign',
#         'parameters': {'assign_table':{'table':'validation', 'column':'highlight'}, 
#                        'assign_value':{'source':'input', 'value':"total greater than 50000000"}
#                       }
# }
# simple_assign_else = {'rule_type': 'static',
#         'function': 'Assign',
#         'parameters': {'assign_table':{'table':'validation', 'column':'highlight'}, 
#                        'assign_value':{'source':'input', 'value':"total not greater than 50000000"}
#                       }
# }

# test_rule3 = {
#     'rule_type':'condition',
#     'evaluations': [{'conditions':[test3_compare_key_value_rule], 'executions': [simple_assign_if]},
#                     {'conditions':[], 'executions':[simple_assign_else]}
#                     ]
# }

# ###########################################################################################
# ###########################################################################################
# simple_assign_if = {'rule_type': 'static',
#         'function': 'Assign',
#         'parameters': {'assign_table':{'table':'validation', 'column':'highlight'}, 
#                        'assign_value':{'source':'input', 'value':"total greater than 50000000"}
#                       }
# }

# ###########################################################################################
# ###########################################################################################
# rule = {
#     'rule_type':'static',
#     'function': 'GetRange',
#     'parameters': { 'value':{'source':'input_config', 'table':'ocr', 'column': 'Vendor GSTIN'},
#                         'range':{'start_index': 0, 'end_index': 3}
#                 }
# }
# simple_assign_recursive = {'rule_type': 'static',
#         'function': 'Assign',
#         'parameters': {'assign_table':{'table':'validation', 'column':'highlight'}, 
#                        'assign_value':{'source':'rule', 'value':rule}
#                       }
# }

# ###########################################################################################
# ###########################################################################################


# simple_select_rule = {
#     'rule_type':'static',
#     'function': 'Select',
#     'parameters': {
#             'from_table': 'master',
#             'select_column': 'Name',
#             'lookup_filters':[
#                 {
#                     'column_name': 'Age',
#                     'compare_with':  {'source':'input', 'value':21}
#                 },
#                 {
#                     'column_name': 'Percentage',
#                     'compare_with':  {'source':'input', 'value':88}
#                 },
#             ]
#         }
# }
# ###########################################################################################
# ###########################################################################################
# transform_rule = {
#     'rule_type':'static',
#     'function': 'Transform',
#     'parameters':[
#             {'param':{'source':'input', 'value':5}},
#             {'operator':'+'},
#             {'param':{'source':'input', 'value':7}},
#             {'operator':'-'},
#             {'param':{'source':'input', 'value':1}},
#             {'operator':'*'},
#             {'param':{'source':'input', 'value':3}}
#     ]
# }

# ###########################################################################################
# ########################################## D ##############################################
# ###########################################################################################

# ##################################### chain check rule##################################################
# chain_check_rule = { 'rule_type': 'static',
#         'function': 'CompareKeyValue',
#         'parameters': {'left_param':{'source':'input_config', 'table':'process_queue', 'column': 'queue'},
#                        'operator':'==',
#                        'right_param':{'source':'input', 'value': 'Processing'}
#         }

# }
# ##################################### cpt check rule##################################################

# cpt_check_rule = {'rule_type': 'static',
#         'function': 'ContainsCPT',
#         'parameters': { 'table_name': 'master','column_name': 'CPT_Code',
#                        'value':{'source':'input_config', 'table':'ocr', 'column': 'CPT_Codes'}
#                       }
# }
# #################################### state s#######################################################

# state_AZ_check ={'rule_type': 'static',
#         'function': 'CompareKeyValue',
#         'parameters': {'left_param':{'source':'input_config', 'table':'ocr', 'column': 'STATE'},
#                 'operator':'==',
#                 'right_param':{'source':'input', 'value': 'AZ'}
#         }
# }

# state_TX_check ={'rule_type': 'static',
#         'function': 'CompareKeyValue',
#         'parameters': {'left_param':{'source':'input_config', 'table':'ocr', 'column': 'STATE'},
#                 'operator':'==',
#                 'right_param':{'source':'input', 'value': 'TX'}
#         }
# }

# state_rule = {'rule_type': 'condition',
#         'function': 'condition',
#         'evaluations': [{ 'conditions':[state_AZ_check,"OR",state_TX_check], 'executions':[]
#         }]
# }
# #################################### cpt and state#######################################################
# CPT_State_rule = { 'rule_type':'static',
#         'function': 'ContainsCPTandState',
#         'parameters' : { 'table_name1': 'master','column_name1': 'CPT_Code',
#                         'table_name2': 'master','column_name2': 'State',
#                         'value1':{'source':'input_config', 'table':'ocr', 'column': 'Add_on_Table'},
#                         'value2':{'source':'input_config', 'table':'ocr', 'column': 'STATE'}
#         }

# }
# #################################### authorisation  #######################################################

# prior_auth_rule1 = { 'rule_type' : 'static' ,
#         'function': 'CheckMultipleCategory',
#         'parameters': { 
#                 'value':{'source':'input_config', 'table': 'ocr','column': 'CPT_Codes' }
#         }
# }

# prior_auth_rule2 = { 'rule_type' : 'static' ,
#         'function': 'CheckMultipleCategoryPA',
#         'parameters': { 
#         'value':{'source':'input_config', 'table': 'ocr','column': 'CPT_Codes' }
#         }
# }

# ######################################### assign service type s##############################################
# assign_service_type_check = {'rule_type': 'static',
#         'function': 'CompareKeyValue',
#         'parameters': {'left_param':{'source':'input_config', 'table':'ocr', 'column': 'Type_of_request'},
#                        'operator':'==',
#                        'right_param':{'source':'input', 'value': ''}
#         }
# }
# select_service_type_check = { 'rule_type': 'static',
#         'function': 'Select',
#         'parameters': {'from_table': 'master','select_column': 'Service_type',
#         'lookup_filters':[
#                 {
#                     'column_name': 'CPT_Codes',
#                     'compare_with':  {'source':'input_config', 'table':'ocr', 'column': 'CPT_Codes'}
#                 }
#             ]
#         }
# }
# service_type_rule = { 'rule_type' : 'condition',
#         'evaluations': [{ 'conditions':[assign_service_type_check], 'executions':[select_service_type_check]
#         }]
# }

# ##################################### mannual rule##################################################
# manual_rule = { 'rule_type': 'static',
#         'function': 'Assign',
#         'parameters': { 'assign_table':{'source':'input_config','table':'process_queue', 'column':'queue'},
#                         'assign_value':{'source':'input', 'value':'manual'}
#         }
# }
# ##################################### duplicate case rule##############################################
# duplicate_case_rule = { 'rule_type': 'static',
#         'function': 'Assign',
#         'parameters': { 'assign_table':{'source':'input_config','table':'process_queue', 'column':'case_type'},
#                         'assign_value':{'source':'input', 'value':'duplicate case'}
#         }
# }
# ##################################### new case rule##############################################
# new_case_rule = { 'rule_type': 'static',
#         'function': 'Assign',
#         'parameters': { 'assign_table':{'source':'input_config','table':'process_queue', 'column':'case_type'},
#                         'assign_value':{'source':'input', 'value':'new case'}
#         }
# }
# ##################################### end contact rule##############################################
# end_contact_rule = { 'rule_type': 'static',
#         'function': 'Assign',
#         'parameters': { 'assign_table':{'source':'input_config','table':'process_queue', 'column':'case_type'},
#                         'assign_value':{'source':'input', 'value':'end contact'}
#         }
# }
# #################################### validate member ###################################################

# unique_rule_check= { 'rule_type': 'static',
#         'function': 'Count',
#        'parameters': {
#             'from_table': 'member',
#             'lookup_filters':[
#                 {
#                     'column_name': 'Last_name',
#                     'compare_with':  {'source':'input_config', 'table':'ocr', 'column': 'Patient_last_name'}
#                 },
#                 {
#                     'column_name': 'DOB',
#                     'compare_with':  {'source':'input_config', 'table':'ocr', 'column': 'DOB'}
#                 },
#                 {
#                     'column_name': 'State',
#                     'compare_with':  {'source':'input_config', 'table':'ocr', 'column': 'STATE'}
#                 }
#             ]
#         }
# }

# unique_rule1 = {'rule_type': 'static',
#         'function': 'CompareKeyValue',
#         'parameters': {'left_param':{'source':'rule', 'value': unique_rule_check},
#                        'operator':'==',
#                        'right_param':{'source':'input', 'value': 1}
#         }
# }

# card_id_check1 = {'rule_type': 'static',
#         'function': 'CompareKeyValue',
#         'parameters': {'left_param':{'source':'input_config', 'table':'member', 'column': 'Member_card_id'},
#                        'operator':'==',
#                        'right_param':{'source':'input_config', 'table':'ocr', 'column': 'Member_card_id'}
#         }
# }


# ###################################### hippa1 s#####################################################
# hippa_rule_fname1 = { 'rule_type': 'static',
#         'function': 'CompareKeyValue',
#         'parameters': {'left_param':{'source':'input_config', 'table':'demographics', 'column': 'First_name'},
#                        'operator':'==',
#                        'right_param':{'source':'input_config', 'table':'ocr', 'column': 'Patient_first_name'}
#         }
    
# }

# hippa_rule_lname1 = { 'rule_type': 'static',
#         'function': 'CompareKeyValue',
#         'parameters': {'left_param':{'source':'input_config', 'table':'demographics', 'column': 'Last_name'},
#                        'operator':'==',
#                        'right_param':{'source':'input_config', 'table':'ocr', 'column': 'Patient_last_name'}
#         }    
# }

# hippa_rule_dob1 = { 'rule_type': 'static',
#         'function': 'CompareKeyValue',
#         'parameters': {'left_param':{'source':'input_config', 'table':'demographics', 'column': 'DOB'},
#                        'operator':'==',
#                        'right_param':{'source':'input_config', 'table':'ocr', 'column': 'DOB'}
#         }
# }

# hippa_rule_state1 = { 'rule_type': 'static',
#         'function': 'CompareKeyValue',
#         'parameters': {'left_param':{'source':'input_config', 'table':'demographics', 'column': 'State'},
#                        'operator':'==',
#                        'right_param':{'source':'input_config', 'table':'ocr', 'column': 'STATE'}
#         }    
# }


# hippa_check_rule1 = { 'rule_type': 'condition',
#         'evaluations': [{ 'conditions':[hippa_rule_fname1,"AND",hippa_rule_lname1,"AND",hippa_rule_dob1,"AND",hippa_rule_state1],  'executions':[]
#         }]
# }
# ###################################### hippa1 c#####################################################

# validate_member_rule1 = {'rule_type': 'condition',
#         'evaluations': [{ 'conditions':[unique_rule1,"AND",card_id_check1,"AND",hippa_check_rule1], 'executions':[]
#         }]
# }

# unique_rule2 = {'rule_type': 'static',
#         'function': 'CompareKeyValue', 
#         'parameters': {'left_param':{'source':'rule', 'value': unique_rule_check},
#                        'operator':'<=',
#                        'right_param':{'source':'input', 'value': 1}
#         }
# }

# card_id_check2 = {'rule_type': 'static',
#         'function': 'CompareKeyValue',
#         'parameters': {'left_param':{'source':'input_config', 'table':'member', 'column': 'Member_card_id'},
#                        'operator':'!=',
#                        'right_param':{'source':'input_config', 'table':'ocr', 'column': 'Member_card_id'}
#         }
# }
# ###################################### hippa2 s#####################################################

# hippa_rule_fname2 = { 'rule_type': 'static',
#         'function': 'CompareKeyValue',
#         'parameters': {'left_param':{'source':'input_config', 'table':'demographics', 'column': 'First_name'},
#                        'operator':'!=',
#                        'right_param':{'source':'input_config', 'table':'ocr', 'column': 'Patient_first_name'}
#         }
    
# }
# hippa_rule_lname2 = { 'rule_type': 'static',
#         'function': 'CompareKeyValue',
#         'parameters': {'left_param':{'source':'input_config', 'table':'demographics', 'column': 'Last_name'},
#                        'operator':'!=',
#                        'right_param':{'source':'input_config', 'table':'ocr', 'column': 'Patient_last_name'}
#         }
    
# }
# hippa_rule_dob2 = { 'rule_type': 'static',
#         'function': 'CompareKeyValue',
#         'parameters': {'left_param':{'source':'input_config', 'table':'demographics', 'column': 'DOB'},
#                        'operator':'!=',
#                        'right_param':{'source':'input_config', 'table':'ocr', 'column': 'DOB'}
#         }
# }

# hippa_rule_state2 = { 'rule_type': 'static',
#         'function': 'CompareKeyValue',
#         'parameters': {'left_param':{'source':'input_config', 'table':'demographics', 'column': 'State'},
#                        'operator':'!=',
#                        'right_param':{'source':'input_config', 'table':'ocr', 'column': 'STATE'}
#         }    
# }


# hippa_check_rule2 = { 'rule_type': 'condition',
#         'evaluations': [{ 'conditions':[hippa_rule_fname2,"AND",hippa_rule_lname2,"AND",hippa_rule_dob2,"AND",hippa_rule_state2],  'executions':[]
#         }]
# }
# ###################################### hippa2 c#####################################################

# validate_member_rule2 = {'rule_type': 'condition',
#         'evaluations': [{ 'conditions':[unique_rule2,"OR",card_id_check2,"OR",hippa_check_rule2], 'executions':[]
#         }]
# }

# validate_member_rule3 = {'rule_type': 'static',
#         'function': 'CompareKeyValue',
#         'parameters': {'left_param':{'source':'rule','value':unique_rule_check},
#                        'operator':'>',
#                        'right_param':{'source':'input', 'value': 1}
#         }
# }

# validate_member_rule4 = {'rule_type': 'static',
#         'function': 'CompareKeyValue',
#         'parameters': {'left_param':{'source':'rule','value':unique_rule_check},
#                        'operator':'==',
#                        'right_param':{'source':'input', 'value': 0}
#         }
# }
# ###################################### insurance s#####################################################


# insurance_medicaid_check = {'rule_type': 'static',
#         'function': 'CompareKeyValue',
#         'parameters': {'left_param':{'source':'input_config', 'table':'insurance', 'column': 'Insurance_type'},
#                        'operator':'==',
#                        'right_param':{'source':'input', 'value': 'medicaid'}
#         }
# }

# insurance_leagacyEntity_check = {'rule_type': 'static',
#         'function': 'CompareKeyValue',
#         'parameters': {'left_param':{'source':'input_config', 'table':'insurance', 'column': 'Legacy_entity'},
#                        'operator':'==',
#                        'right_param':{'source':'input', 'value': 'UHC C&S'}
#         }
# }

# date_validate_rule = { 'rule_type': 'static',
# 'function': 'CheckDate',
# 'parameters': {'value':{'source':'input_config', 'table':'ocr', 'column': 'End_date'}}
# }

# validate_insurance_rule1 = {'rule_type': 'condition',
# 'evaluations': [{ 'conditions':[insurance_medicaid_check,"AND", date_validate_rule,"AND",insurance_leagacyEntity_check], 'executions':[]
#         }]
# }

# insurance_multiple_check = {'rule_type': 'static',
# 'function': 'CheckMultipleInsurance',
# 'parameters': [{'source':'input_config', 'table':'insurance', 'column': 'Insurance_type'}]
# }

# insurance_medicare_check = {'rule_type': 'static',
#         'function': 'CompareKeyValue',
#         'parameters': {'left_param':{'source':'input_config', 'table':'insurance', 'column': 'Insurance_type'},
#                        'operator':'==',
#                        'right_param':{'source':'input', 'value': 'medicare'}
#         }
# }

# validate_insurance_rule2 = {'rule_type': 'condition',
# 'evaluations': [{ 'conditions':[ insurance_multiple_check,"OR",insurance_medicare_check ],'executions':[]
#         }]
# }
# ########################################## history #################################################
# history_match_rule = {'rule_type': 'static',
#         'function': 'CompareKeyValue',
#         'parameters': {'left_param':{'source':'input_config', 'table':'history', 'column': 'History_match'},
#                'operator':'==',
#                'right_param':{'source':'input', 'value': 'yes'}
# }

# }
# history_case_rule = { 'rule_type': 'static',
#         'function': 'CompareKeyValue',
#         'parameters': {'left_param':{'source':'input_config', 'table':'history', 'column': 'Case_Status'},
#                'operator':'==',
#                'right_param':{'source':'input', 'value': 'open'}
# }
# }

# """history_rule = { 'rule_type' : 'condition',
# 'evaluations': [{ 'conditions':[history_match_check],'executions':[history_case_check]
#         }]
# }"""
# ########################################### total units################################################
# total_units_count = { 'rule_type':'static',
#         'function':'CountTotalUnits',
#         'parameters': {'table_name': 'master','column_name': 'CPT_Code', 
#                 'value':{'source':'input_config', 'table':'ocr', 'column': 'CPT_Codes'}
#                     }

# }

# total_unit_rule = {'rule_type':'static',
#         'function':'assign',
#         'parameters': {'assign_table':{'source':'input_config', 'table':'ocr', 'column':'Total_Units'},
#                        'assign_value':{'source':'rule', 'value':total_units_count}
#                     }

# }

# ###########################################################################################
# ###########################################################################################

# data = {'id': 1, 'case_id': '2000441939', 'highlight': '{"Document Heading": {"height": 12, "width": 63, "y": 38, "x": 297, "right": 364, "word": "Tax Invoice", "page": 0}, "Vendor GSTIN": {"height": 7, "width": 101, "y": 117, "x": 102, "right": 203, "word": "37AAUFA4486C1Z5", "page": 0}, "Billed To (DRL Name)": {"height": 9, "width": 197, "y": 159, "x": 39, "right": 252, "word": "Dr. Reddys Laboratories Limited CTO-6", "page": 0}, "DRL GSTIN": {"height": 10, "width": 105, "y": 205, "x": 128, "right": 239, "word": "37AAACD7999Q1ZJ", "page": 0}, "Invoice Number": {"height": 9, "width": 24, "y": 79, "x": 364, "right": 389, "word": "6106", "page": 0}, "Vendor Name": {"height": 7, "width": 93, "y": 816, "x": 529, "right": 628, "word": "Akshaya Lab Products", "page": 0}, "Invoice Date": {"height": 9, "width": 60, "y": 79, "x": 498, "right": 559, "word": "4-May-2019", "page": 0}, "PO Number": {"height": 10, "width": 61, "y": 157, "x": 364, "right": 426, "word": "5800438872", "page": 0}, "Invoice Total": {"height": 7, "width": 163, "y": 708, "x": 325, "right": 629, "word": "50,000.00 4,500.00 4,500.00 9,000.00", "page": 0}}', 'PO Number': '5800438872', 'Invoice Number': '6106', 'Invoice Category': None, 'Invoice Date': '2019-05-04', 'Invoice Total': '59000', 'Invoice Base Amount': '50000', 'GST Percentage': '', 'IGST Amount': '0', 'DRL GSTIN': '37AAACD7999Q1ZJ', 'Vendor GSTIN': '37AAUFA4486C1Z5', 'Billed To (DRL Name)': 'Dr. Reddys Laboratories Limited CTO-6', 'Vendor Name': 'Akshaya Lab Products', 'Special Instructions': '', 'Digital Signature': 'Yes', 'Document Heading': 'Tax Invoice', 'HSN/SAC': '', 'DC Number': '', 'SGST/CGST Amount': '', 'GRN Number': '', 'Service Entry Number': '', 'Comments': None, 'Table': '[[[[[["<b>Product description</b>",1,1],["<b>HSN/SAC</b>",1,1],["<b>Quantity</b>",1,1],["<b>Rate</b>",1,1],["<b>Gross Amount</b>",1,1]],[[" Headspace Vials 20ml - Pk/100 Cat No: FULV21 Make: Saint-Gobain Material Code: 940003734",1,1],[" Rate 70179090 18 %",1,1],[" 50 Pack",1,1],[" 1,000.00",1,1],[" 50,000.00",1,1]],[[" SGST Output @ 9%",1,1],["",1,1],["",1,1],[" 9",1,1],[" 4,500.00",1,1]],[[" CGST Output @ 9%",1,1],["",1,1],["",1,1],[" 9",1,1],[" 4,500.00",1,1]]]]]]'}
# data['PO Number'] = "4"
# ocr = {'CPT_Codes' : '{"55980":"2","6789":"3","7890":"1","0553":"2"}' ,
#         'id':[43,34,21], 
#         'STATE':['TX'], 
#         'catogery': ["in","out"],
#         'type_of_request':'',#['inpatient','','outpatient'],
#         'Patient_first_name':'divya',
#         'Patient_last_name' : ['bojanapalli'],
#         'Requesting_Provider__Address' :['amalapuram'],
#         'DOB': ['1997-09-18 00:00:00'],
#         'Member_card_id' : ['508'],
#         'Fax_unique_id' : ['TX05D36FF31C451'],
#         'End_date' : '2019-08-23 00:00:00'
# }

# master = { 
#   'CPT_Code': ["55980","6553","7890","6789"],
#   'State': ['AZ','XY','AX',''], 
#   'Category': ['Outpatient Speech Therapy','Outpatient Speech Therapy','Outpatient Speech Therapy','Outpatient Speech Therapy'], 
#   'PA_Reqd': ['not required','not required','not required','required'],
#   'service_type': ['inpatient','outpatient','','']
# } 

# member = {
#         'DOB' : ['18-09-1997'],
#         'State' : ['AZ'],
#         'Member_card_id' : ['508'],
#         'First_name':['divya'],
#         'Last_name' : ['bojanapalli'],
#         'Address1' :['amalapuram']
# }

# insurance = { 'Fax_unique_id' : ['TX05D36FF31C451'],
#                 'Insurance_type': ['medicaid','madicare'],
#                 'Insurance_Status': []

# }
# demographics ={
#         'DOB' : ['1997-09-18 00:00:00'],
#         'State' : ['AZ'],
#         'First_name':['divya'],
#         'Last_name' : ['bojanapalli']
# }
# history = {
#         'History_match':'yes',
#         'Case_Status':'open'
# }
# process_queue = {
#         'queue' : [],
#         'case_type' : []
# }


# addrule = {'rule_type': 'static',
#         'function': 'Add',
#         'parameters': [{'source':'input_config', 'table':'ocr', 'column': 'PO Number'}]
#        }

# rule = {'rule_type': 'static',
#         'function': 'Add',
#         'parameters': [{'source':'rule', 'value':addrule}]
#        }

# rule1 = {'rule_type': 'static',
#         'function': 'Assign',
#         'parameters': {'assign_table':{'table':'ocr', 'column':'PO Number'}, 
#                        'assign_value':{'source':'rule', 'value':rule}
#                       }
#        }

# rule2 = {'rule_type': 'static',
#         'function': 'CompareKeyValue',
#         'parameters': {'left_param':{'source':'input', 'value':5},
#                        'operator':'>',
#                        'right_param':{'source':'input', 'value':4}
#                       }
#        }

# comparision_add_rule = {'rule_type':'condition','evaluations': [{ 'conditions':[rule2], 
#                                                  'executions':[rule1]},
#                     {'conditions':[], 'executions':[]}]}

# a  = BusinessRules(2000384768,[comparision_add_rule], {"ocr":ocr, "validation": ocr.copy(), "master":master,"demographics":demographics , "member":member,"insurance":insurance,"history":history,"process_queue":process_queue})
# print (a.evaluate_business_rules())
# print(a.data_source['process_queue'])
#print (service_type_rule)

