import argparse
import ast
import json
import pandas as pd
import numpy as np
import re
import requests
import traceback
import pdb
import os
from db_utils import DB

from flask_cors import CORS
from flask import Flask, jsonify, request
from dateutil.parser import parse
from datetime import datetime, timedelta
from time import time

from py_zipkin.zipkin import zipkin_span,ZipkinAttrs, create_http_headers_for_new_span

try:
    from app.da_bizRul_factory import DABizRulFactory
except:
    from da_bizRul_factory import DABizRulFactory

try:
    from app import app
except:
    app = Flask(__name__)
    CORS(app)

DAO = DABizRulFactory.get_dao_bizRul()

def http_transport(encoded_span):
    body = encoded_span
    requests.post(
        'http://servicebridge:5002/zipkin',
        data=body,
        headers={'Content-Type': 'application/x-thrift'},)

# All do functions are exposed to the UI
def doSelect(record, param_string, table_data):
    """
    param_string: "lhs, rhs   output.file_name,sap.inp,sap.gsitn,invoice.gstin,...."
    lhs: source.field_name
    rhs: source.field_name
    """
    
    parameters = param_string.split(',')
    try:
        assign_parameters = parameters[:2]
        table = assign_parameters[1].split('.')[0]
    except:
        print ("DIDNT MEET THE CRITERIA..PLEASE SEEEEE")
        return record
    case_id = record['case_id'].iloc[0]
    
    N=2

    where = {}

    for a,b in list(zip(*([iter(parameters)] * N)))[1:]:
        if a and b:
            where[a.split('.')[1]] = get_field_value(table_data, b, case_id, record)


    field = ['id', assign_parameters[1].split('.')[1]]

    r = DAO.doSelect_get_data(table=table, field=field, where=where)

    
    if not r.empty:
        assign_string = parameters[0]+","+str(r.iloc[0][1])
    else:
        assign_string = parameters[0]+","
    return doAssign(record, assign_string, table_data)
    
def doContainsSubString(record, param_string, table_data):
    """
    param_string: "lhs, rhs   sap.gsitn contains invoice.gstin"
    lhs: source.field_name
    rhs: source.field_name
    """
    lhs, rhs = param_string.split(',')
    # NOTE: Ensure in UI that LHS has source.field_name
    case_id = record['case_id'].iloc[0]
    lhs_value = get_field_value(table_data, lhs, case_id, record)
    try:
        response = rhs.lower() in lhs_value.lower()
    except:
        return False
    return response
    
def checkDateRange(variable_date,displacement,no_days):
    currdatestring = datetime.now().strftime(r"%Y-%m-%d")
    reference_date = datetime.strptime(currdatestring, r"%Y-%m-%d").date()
    try:
        if variable_date == '2019-05-05T18:30:00.000Z':
            variable_date = '2019-05-06'
            print('variable date',variable_date)
        variable_date = datetime.strptime(variable_date, r"%Y-%m-%d").date()
    except:
        try:
            variable_date = datetime.strptime(parse(variable_date,dayfirst=True).strftime("%d-%b-%y"), r"%Y-%m-%d").date()
        except:
            traceback.print_exc()
            print(f'Date not in YYYY-MM-DD format `{variable_date}`')
            return False

    if(displacement=="before"):
        newdate =  reference_date - timedelta(no_days)
        if(newdate<= variable_date<=reference_date):
            return True
        else:
            return False

    if(displacement=="after"):
        newdate =  reference_date + timedelta(no_days)

        if(reference_date <= variable_date <= newdate):
            return True
        else:
            return False

def doAssignRange(record, param_string, table_data):
    """
    param_string: "lhs, rhs....Have to think about it ...."
    lhs: source.field_name
    rhs: allowed_sources.field_name OR string OR int OR double
    """
    lhs, rhs, range_ = param_string.split(',')
    if range_:
        range_ = int(range_) # right now ..take only end index........DRL Specific
    else:
        print ("FAIL FASTT......")
        return record
    case_id = record['case_id'].iloc[0]
    rhs_value = get_field_value(table_data, rhs, case_id, record)
    try:
        rhs_value = str(rhs_value)[:range_]
    except:
        print ("ISSUE IN RANGE")
        return record
    assign_string = lhs+','+rhs_value
    return doAssign(record, assign_string, table_data)
        
def doDateRange(record, param_string, table_data):
    """
    param_string: "lhs, rhs   sap.invoiceDate,before,no_days"
    lhs: source.field_name
    rhs: source.field_name
    """
    variable_date_param,displacement,no_days=param_string.split(',')
    case_id = record['case_id'].iloc[0]
    variable_date = get_field_value(table_data, variable_date_param, case_id, record)
    try:
        int(no_days)
    except:
        print ("TAKING DEFAULT 180days")
        no_days = 180
    return (checkDateRange(variable_date, displacement, int(no_days)))
   
def doContains(record, param_string, table_data):
    """
    param_string: "lhs, rhs   sap.gsitn, invoice.gstin"
    lhs: source.field_name
    rhs: source.field_name
    """
    lhs, rhs = param_string.split(',')
    # NOTE: Ensure in UI that LHS has source.field_name
    lhs_source, lhs_field_name = lhs.split('.')
    
    case_id = record['case_id'].iloc[0]
    
    result_df = DAO.doContains_get_lhs_field_name(table=lhs_source, field=lhs_field_name)
    
    if not result_df.empty:
        lhs_list = result_df[lhs_field_name].tolist()
    else:
        lhs_list = []
    
    # if '.' in rhs:
    #     rhs_table, rhs_field_name = rhs.split('.')
    #     rhs_value = get_field_value(rhs_table, rhs_field_name, case_id)
    # else:
    #     rhs_value = rhs
     
    rhs_value = get_field_value(table_data, rhs, case_id, record)
    
    return  rhs_value in lhs_list

def doContainsRange(record, param_string, table_data):
    """
    param_string: "lhs, rhs,range   sap.gsitn,invoice.gstin,2"
    lhs: source.field_name
    rhs: source.field_name
    """
    lhs, rhs, range_ = param_string.split(',')
    if range_:
        range_ = int(range_) # right now ..take only end index........DRL Specific
    else:
        print ("FAIL FASTT......")
        return False
    case_id = record['case_id'].iloc[0]
    rhs_value = get_field_value(table_data, rhs, case_id, record)
    try:
        rhs_value = str(rhs_value)[:range_]
    except:
        return False
    contains_string = lhs+","+rhs_value
    return doContains(record, contains_string)
 
def doTransform(record, param_string, table_data):
    """
    param_string: "lhs, rhs   output.case_id,input.invoice,+,sap.invoice,*,ocr.times"
    lhs: source.field_name
    rhs: source.field_name
    """
    lhs = param_string.split(',')[0]
    operands = ['+', '-', '*', '/']
    eval_string = ''
    case_id = record['case_id'].iloc[0]
    for param in param_string.split(',')[1:]:
        if param in operands:
            eval_string += ' '+param+' '
        else:
            value = str(get_field_value(table_data, param, case_id, record)) 
            if value is not None:
                r = re.search(r'[0-9]+(.[0-9]{1,})?',value)
                if r:
                    value = r.group()
                else:
                    value = '0'
            eval_string += ' '+value + ' '
    # record[lhs_field_name] = eval(eval_string)
    try:
        assign_string = lhs+","+str(eval(eval_string))
    except:
        assign_string = lhs+","
    return doAssign(record, assign_string, table_data)

def doAssign(record, param_string, table_data):
    """
    param_string: "lhs, rhs"
    lhs: source.field_name
    rhs: allowed_sources.field_name OR string OR int OR double
    """
    lhs, rhs = param_string.split(',')
    # NOTE: Ensure in UI that LHS has source.field_name
    lhs_source, lhs_field_name = lhs.split('.')
    case_id = record['case_id'].iloc[0]
    rhs_value = None
    rhs_field_name = None

    rhs_value = get_field_value(table_data, rhs,case_id,record)
    
    if "." in rhs:
        rhs_field_name = rhs.split('.')[1]
        if rhs_field_name == 'file_name':
            rhs_value = " ".join(rhs_value.split(".")[:-1])
   
    if lhs_source.lower() == 'output':
        record[lhs_field_name] = rhs_value
    else:
        # Update corresponding table - means validation - DO NOT UPDATE record
        if lhs_source in table_data and not table_data[lhs_source].empty:
            case_lhs_data = table_data[lhs_source]
        else:
            case_lhs_data = DAO.doAssign_get_data(table=lhs_source, case_id=case_id)
            table_data[lhs_source] = case_lhs_data
         # = lhs_source_data.loc[lhs_source_data['case_id'] == case_id]

        # Insert if case_id does not exist
        if case_lhs_data.empty:
            dao_input = {
                'table' : lhs_source,
                'to_insert' : {
                    'case_id' : case_id
                }
            }
            DAO.doAssign_insert_case_id(table=lhs_source, case_id=case_id)

            print(f'Case ID `{case_id}` does not exist in `{lhs_source}` table. Inserting.')
            table_data[lhs_source] = table_data[lhs_source].append({'case_id': case_id}, ignore_index=True)
            
        if lhs_source in table_data and not table_data[lhs_source].empty:
            table_data[lhs_source][lhs_field_name] = rhs_value
            # table_data["update"][lhs_source].update(lhs_field_name)
            if lhs_source in table_data["update"]:
                table_data["update"][lhs_source].add(lhs_field_name)
            else:
                table_data["update"][lhs_source] = set()
                table_data["update"][lhs_source].add(lhs_field_name)
        else:
            to_update = {lhs_field_name:rhs_value}
            DAO.doAssign_update_case_id(table=lhs_source, to_update=to_update, case_id=case_id)
            table_data[lhs_source] = table_data[lhs_source].append({'case_id': case_id, lhs_field_name : rhs_value}, ignore_index=True)
            
    return record

def doStartsWith(record, param_string, table_data):
    """
    param_string: "lhs, rhs"
    lhs: allowed_prefix.field_name
    rhs: string
    """
    lhs, rhs = param_string .split(',')
    # # NOTE: Ensure in UI that LHS has allowed_prefix.field_name
    # try:
    #     lhs_table, lhs_field_name = lhs.split('.')
    # except:
    #     print ("LHS NOT IN SPECIFIED FORMAT.............")
    # try:
    #     lhs_value = record[lhs_field_name].iloc[0]  
    # except Exception as e:
    #     print(e)
    #     return False
    # if not lhs_value:
    #     return False
    case_id = record['case_id'].iloc[0]
    lhs_value = get_field_value(table_data, lhs, case_id, record)
    return lhs_value.startswith(rhs) and bool(rhs)

def doDigitalSignature(record, param_string, table_data):
    """
    param_string: file_path (str)
    """
    try:
        filepath = param_string
    except:
        print('file_path missing')
        return False
    with open(filepath, 'rb') as fp:
        parser = PDFParser(fp)
        doc = PDFDocument(parser)
        try:    
            fields = resolve1(doc.catalog['AcroForm'])['Fields']
            for i in fields:
                field = resolve1(i)
                name = field.get('T')
                if 'signature' in str(name).lower():
                    return True
        except Exception as e:
            print (e)
            return False
        return False

def doCompareKeyLength(record, param_string, table_data):
    """
    param_string: "lhs, op, rhs"
    lhs: source.field_name
    rhs: string
    """
    lhs, op, rhs = param_string.split(',')
    # NOTE: Ensure in UI that LHS has source.field_name
    case_id = list(record['case_id'])[0]
    lhs_value = get_field_value(table_data, lhs, case_id, record)
    # try:
    #     lhs_value = (record[lhs_field_name].iloc[0])
    # except:
    #     print(f'{lhs_field_name} not in record')
    #     return False
    if op == '==':
        return str(len(str(lhs_value))) == str(rhs)
    return eval(len(lhs_value) + ' ' + op + ' ' + rhs)

def doFiscalYear(record, param_string, table_data):
    """
    param_string: "lhs sap.date"
    lhs: source.field_name
    rhs: source.field_name
    """
    today = datetime.today()
    fyr = datetime(today.year, today.month, 1).year
    return  doAssign(record, param_string+","+str(fyr), table_data)

def doCompareKeyValue(record, param_string, table_data):
    """
    param_string: "lhs, op, rhs"
    lhs: source.field_name
    rhs: string
    """
    lhs, op, rhs = param_string.split(',')
    # NOTE: Ensure in UI that LHS has source.field_name
    case_id = record['case_id'].iloc[0]
    # try:
    #     lhs_value = record[lhs_field_name].iloc[0]
    # except:
    #     print(f'{lhs_field_name} not in record')
    #     return False
    lhs_value = get_field_value(table_data, lhs, case_id, record)
    # if '.' in rhs:
    #     rhs_table, rhs_field_name = rhs.split('.')
    #     rhs_value = get_field_value(rhs, case_id)
    # else:
    #     rhs_value = rhs
    rhs_value = get_field_value(table_data, rhs, case_id, record)
    # try converting them to  float and  compare...if not thery are comparing strings.....
    if op == '==':
        return str((lhs_value)) == str(rhs_value)
    elif op == '!=':
        return str((lhs_value)) != str(rhs_value)
    elif op == '>':
        try:
            return float(str(lhs_value).replace(",","")) > float(rhs_value)
        except:
            print ("LHS/RHS is empty/None. Can not compare.")
            return False
    else:
        return False

    return eval(lhs_value + ' ' + op + ' ' + rhs_value)

def doCompareKeyValueRange(record, param_string, table_data):
    """
    param_string: "lhs, op, rhs"
    lhs: source.field_name
    rhs: string
    """
    lhs, op, rhs, range_ = param_string.split(',')
    if range_:
        range_ = int(range_) # right now ..take only end index........DRL Specific
    else:
        print ("FAIL FASTT......")
        return False


    # NOTE: Ensure in UI that LHS has source.field_name
    case_id = record['case_id'].iloc[0]
    # try:
    #     lhs_value = record[lhs_field_name].iloc[0]
    # except:
    #     print(f'{lhs_field_name} not in record')
    #     return False
    lhs_value = get_field_value(table_data, lhs, case_id, record)

    # if '.' in rhs:
    #     rhs_table, rhs_field_name = rhs.split('.')
    #     rhs_value = get_field_value(rhs, case_id)
    # else:
    #     rhs_value = rhs
    rhs_value = get_field_value(table_data, rhs, case_id, record)


    lhs_value = str(lhs_value)[:range_]
    rhs_value = str(rhs_value)[:range_]
    # try converting them to  float and  compare...if not thery are comparing strings.....
    if op == '==':
        return str((lhs_value)) == str(rhs_value)
    elif op == '!=':
        return str((lhs_value)) != str(rhs_value)
    elif op == '>':
        try:
            return float(lhs_value) > float(rhs_value)
        except:
            print ("GREATER THAN ERROR")
            return False
    else:
        return False

    return eval(lhs_value + ' ' + op + ' ' + rhs_value)

def doFormat(record, param_string, table_data):
    """
    param_string: "lhs, rhs   sap.gsitn, Date"
    lhs: source.field_name
    rhs: source.field_name
    """
    lhs, rhs = param_string.split(',')
    case_id = record['case_id'].iloc[0]
    inp = get_field_value(table_data, lhs, case_id, record)
    format_type = rhs
    return format_check(inp, format_type)

def doUpdateQueue(record, param_string, table_data):
    queue = param_string
    case_id = record['case_id'].iloc[0]
    DAO.doUpdateQueue(case_id=case_id, queue=queue)
    table_data['process_queue']['queue'] = queue

    if 'process_queue' in table_data['update']:
        table_data["update"]['process_queue'].add('queue')
    else:
        table_data["update"]['process_queue'] = set()
        table_data["update"]['process_queue'].add('queue')

    update_queue_trace(case_id,queue)
    if queue == 'Approved':
        host = 'servicebridge'
        port = '80'
        route = 'generate_json'
        print('Moving to Approved queue and generating JSON')
        data = {"case_id": case_id}
        response = requests.post(f'http://{host}:{port}/{route}', json=data)
    return record


def update_queue_trace(case_id,latest):
    # dao_input = {
    #     'field' : []
    #     'where' : {'case_id' : case_id}
    # }

    queue_trace_df = DAO.update_queue_trace_get_trace_data(case_id)


    if queue_trace_df.empty:
        message = f' - No such case ID `{case_id}` in `trace_info`.'
        print(f'ERROR: {message}')
        return {'flag':False,'message':message}
    # Updating Queue Name trace
    try:
        queue_trace = list(queue_trace_df.queue_trace)[0]
    except:
        queue_trace = ''
    if queue_trace:
        queue_trace += ','+latest
    else:
        queue_trace = latest

    #Updating last_updated_time&date

    try:
        last_updated_dates = list(queue_trace_df.last_updated_dates)[0]
    except:
        last_updated_dates = ''
    if last_updated_dates:
        last_updated_dates += ','+ datetime.now().strftime(r'%d/%m/%Y %H:%M:%S')
    else:
        last_updated_dates = datetime.now().strftime(r'%d/%m/%Y %H:%M:%S')

    update = {'queue_trace':queue_trace}
    where = {'case_id':case_id}

    DAO.update_queue_trace_update(queue_trace=queue_trace, last_updated_dates=last_updated_dates,case_id=case_id)

    return {'flag':True,'message':'Updated Queue Trace'}

# Helper functions
def format_check(inp, format_type):
    if format_type == 'Date':
        try:
            (parse(inp))
            return True
        except:
            return False

    if format_type == 'GST':
        try:
            (re.match("^([0]{1}[1-9]{1}|[1-2]{1}[0-9]{1}|[3]{1}[0-7]{1})([a-zA-Z]{5}[0-9]{4}[a-zA-Z]{1}[1-9a-zA-Z]{1}[zZ]{1}[0-9a-zA-Z]{1})+$", inp))
            return True
        except:
            return False

    return False

def get_field_value(table_data, field, case_id, record_df=None):

    try:
        table, field_name = field.split('.')
    except:
        return field

    if table.lower() == 'output':
        return record_df[field_name].iloc[0]



    # print("table_used",table)
    # query = f"SELECT `id`,`{field_name}` FROM `{table}` WHERE `case_id` = %s"
    # params = [case_id]

    try:
        result_df = table_data[table][[field_name]]
    except:
        traceback.print_exc()
        return field


    if result_df is None:
        return field

    if not result_df.empty:
        if result_df[field_name].iloc[0] is not None:
            return str(result_df[field_name].iloc[0]).replace('suspicious', '')
    else:
        return None

def is_conditions_met(record, conditions, table_data):
    """Return whether the conditions met or not
    Helper function for evaluate_if
    Args:

    Returns;

    Note:

    """
    eval_string = ''
    # that means we are in elseeeeeee..........
    if not conditions:
        return True
    for condition in conditions:
        if condition == 'AND' or condition == 'OR':
            eval_string += ' '+condition.lower()+' '
        else:
            eval_string += ' '+str(evaluate_norm(record, condition, table_data))+' '
    return eval(eval_string)

stage_rules = {}
def initialize_rules():
    global stage_rules
    if not stage_rules:
        stages = ['One', 'Two', 'Three', 'Four', 'Five', 'Six']
        for stage in stages:
            stage_rules[stage] = get_rules(stage)

def get_rules(stage):
    rules = []
    eval_rules = []
    results_df = DAO.get_rules(stage=stage)

    if not results_df.empty:
        rules = list(results_df['rule_string'])

        for rule in rules:
            if rule:
                try:
                    eval_rules.append(ast.literal_eval(rule)[0])
                except:
                    traceback.print_exc()
                    print('Error converting rule string to list.')
    else:
        print('Stage not found')
    return eval_rules

def get_tables_data(tables, case_id):
    """
    Author : Akshat Goyal

    Getting all the tables required in memory

    Args:
        tables(dict) : key as DB and value as list of tables

    return:
        dict : key as table and value as dataframe
    """
    to_return = {}
    # for key, tables in tables.items():
    to_return = DAO.get_tables_data(case_id)

    return to_return

def update_table(table_data, case_id, tables):
    print("table_data update - ",table_data['update'])
    update_values = {}
    for key, values in table_data['update'].items():
        fields = {}
        for field in values:
            fields[field] = list(table_data[key][field])[0]
            # print(f"field - {field} , value = {list(table_data[key][field])}")
            if key in update_values:
                update_values[key].update({field: list(table_data[key][field])[0]})
            else:
                update_values[key] = {field: list(table_data[key][field])[0]}


        DAO.update_table_update(table=key, to_update=fields, case_id=case_id)

    return update_values
def perform(record, executions, table_data):
    """Perform the executions....executions are rules itself"""
    for execution in executions:
        evaluate_norm_start = time()
        record = evaluate_norm(record, execution, table_data)
        print("time_taken - evalulate norm - rule - ", execution[1][0], time() - evaluate_norm_start)
    return record

def evaluate_norm(record, rule, table_data):
    """Execute static function on the record.
    Args:
        record(list) A database record.
        rule
    Returns:
        record(list) An updated record after applying the static function.

    """
    values = rule[1]
    function_name = values[0]
    parameters_string = values[1]

    if function_name == 'Assign':
        return_assign = doAssign(record, parameters_string, table_data)
        return return_assign
    if function_name == 'CompareKeyValue':
        return doCompareKeyValue(record, parameters_string, table_data)
    if function_name == 'CompareKeyLength':
        return doCompareKeyLength(record, parameters_string, table_data)
    if function_name == 'StartsWith':
        return doStartsWith(record, parameters_string, table_data)
    if function_name == 'Contains':
        return doContains(record, parameters_string, table_data)
    if function_name == 'DigitalSignature':
        return doDigitalSignature(record, parameters_string, table_data)
    if function_name == 'Format':
        return doFormat(record, parameters_string, table_data)
    if function_name == 'FiscalYear':
        return doFiscalYear(record, parameters_string, table_data)
    if function_name == 'ContainsSubString':
        return doContainsSubString(record, parameters_string, table_data)
    if function_name == 'CompareKeyValueRange':
        return doCompareKeyValueRange(record, parameters_string, table_data)
    if function_name == 'Transform':
        return doTransform(record, parameters_string, table_data)
    if function_name == 'Select':
        return doSelect(record, parameters_string, table_data)
    if function_name == 'DateRange':
        return doDateRange(record, parameters_string, table_data)
    if function_name == 'doAssignRange':
        return doAssignRange(record, parameters_string, table_data)
    if function_name == 'UpdateQueue':
        return doUpdateQueue(record, parameters_string, table_data)

def evaluate_if(record, rule, table_data):
    """Evaluate the if condition and return response

    Args:
        rule See the rule documentation above
    Returns:

    """
    ifrules = rule[1]
    for conditions, executions in ifrules:
        if is_conditions_met(record, conditions, table_data):
            return perform(record, executions, table_data)
    return record

def evaluate_business_rules(record, rules, table_data):
    """Evaluate all the rules on the record and return the record.

    Args:
        record(dataframe) A database record.
        rules(list) All the business rules that are to be evaluated.
    Returns:
        record(dataframe) An updated record after applying the business rules.
    """
    # apply rules on each record and return the record
    for rule in rules:
        print('Processing Rule: ', str(rule))
        if rule[0] == 'if':
            record = evaluate_if(record, rule, table_data)
        else:
            record = evaluate_norm(record, rule, table_data)
    return record


# # -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
# #####################  
#                         KARVY Business Rules start here
# #####################
# # -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

def doTakeSubString(df, col_toManipulate, start_pos, length, new_col_name):

    new_df = df.copy(deep = True)
    new_df[new_col_name] = new_df[col_toManipulate].astype("str")
    new_df[new_col_name] = new_df[new_col_name].str.slice(start_pos, start_pos+length, 1)

    return new_df

def doDelRowWhereColumnExist(df, focus_col):

    df_upd = df.copy(deep = True)
    df_upd = df_upd[df_upd[focus_col].isnull()]

    return df_upd

def doFlagRowWhereColumnExist(df, focus_col, new_col_name):

    df_upd = df.copy(deep = True)
    df_upd[new_col_name] = np.where(df_upd[focus_col].isnull(), "False", "True")

    return df_upd

def doColumnSplit(df1, col_name, delimeter, new_col, split_num):

    df_upd = df1.copy(deep = True)

    df_upd[new_col] = df_upd[col_name].str.split(delimeter).str[split_num]

    return df_upd



def doManipluteColifWhereExist(df, maniplute_col, if_col_list, operation, by_value):

    df_upd = df.copy(deep = True)
    opert = operation
    oper_byval = int(by_value)
#    print(oper_byval)
    for i, row in df_upd.iterrows():
        if row[if_col_list[0]] == if_col_list[1]:
#            print(row[maniplute_col])
            if opert == "*":
#                print("in if ")
                upd_val = oper_byval*row[maniplute_col]
#                print("upd val in if", upd_val)
            else:
#                print("in else")
                upd_val = row[maniplute_col]
#            print(row[maniplute_col])
#            print("upd val in ", upd_val)
            df_upd.set_value(i, maniplute_col, upd_val)

    return df_upd

def doCompareSumByGroupby(df1, df2, groupby_string, sumfield_string):

    no_of_GroupByFields = groupby_string.count("|")+1
    no_of_SumFields = sumfield_string.count("|")+1

    if no_of_GroupByFields > 1:
        groupby_fields_df1 = [ele.split(",")[0].split(".")[1] for ele in groupby_string.split("|")]
        groupby_fields_df2 = [ele.split(",")[1].split(".")[1] for ele in groupby_string.split("|")]
    else:
        groupby_fields_df1 = [[ele.split(".")[1] for ele in groupby_string.split(",")][0]]
        groupby_fields_df2 = [[ele.split(".")[1] for ele in groupby_string.split(",")][1]]

    if no_of_SumFields > 1:
        sum_fields_df1 = [ele.split(",")[0].split(".")[1] for ele in sumfield_string.split("|")]
        sum_fields_df2 = [ele.split(",")[1].split(".")[1] for ele in sumfield_string.split("|")]
    else:
        sum_fields_df1 = [[ele.split(".")[1] for ele in sumfield_string.split(",")][0]]
        sum_fields_df2 = [[ele.split(".")[1] for ele in sumfield_string.split(",")][1]]

    print(groupby_fields_df1, groupby_fields_df2)
    print(sum_fields_df1, sum_fields_df2)

    df1_sum = df1.groupby(groupby_fields_df1)[sum_fields_df1].apply(lambda x : x.astype(int).sum())
    df2_sum = df2.groupby(groupby_fields_df2)[sum_fields_df2].apply(lambda x : x.astype(int).sum())

    df1_groupby = df1_sum.reset_index()
    df2_groupby = df2_sum.reset_index()


    return df1_groupby, df2_groupby

def doCompareRows(row, df2, fields_df1, fields_df2):
    if len(fields_df1) != len(fields_df2):
        print("issue in format of match fields")
        return "issue in format of match fields"
    else:
        loop_len = len(fields_df1)
#        print("len of loop", loop_len)
#        print(df2.dtypes)
        target_df = df2[fields_df2]
        print(fields_df1)
        print(fields_df2)
#        match_count = 0
        for i, rows in target_df.iterrows():
            row_output = []
            match = False
            match_cols = []
            nonmatch_cols = []
            for j in range(0, loop_len):
                if rows[fields_df2[j]] == row[fields_df1[j]]:
                    print(rows)
                    match = True
                    print(match)
                    match_cols.append(fields_df2[j])
                else:
                    match = False
                    print(match)
                    nonmatch_cols.append(fields_df2[j])
                    break
#                match_count =+1
#            print("macth")
            if match:
                row_output.append("Matched")
                # row_output.append(i)
                break
            else:
                row_output.append("Un Matched")
                # row_output.append("")
#                row_output.append(nonmatch_cols)
        return row_output



def doCompareRecordsinTwoTables(base_df, df2, col_pair_list):

    comp_fields_df1 = [ele.split(",")[0].split(".")[1] for ele in col_pair_list.split("|")]
    comp_fields_df2 = [ele.split(",")[1].split(".")[1] for ele in col_pair_list.split("|")]

    result_df = base_df.copy(deep = True)

    result_df["Match_ids"] = ""
#    matched_ids = []
    for i, row in base_df.iterrows():
        match_id_list= doCompareRows(row, df2, comp_fields_df1, comp_fields_df2)
        result_df.set_value(i, "Match_ids", match_id_list)
#        matched_ids = matched_ids+match_id_list

    return result_df


def preprocess_rt(df1_t):

    df1_processed = df1_t.copy(deep = True)

    df1_processed["DebitTag"] = np.where(df1_processed["Debit / Credit"] == "D", 0, 1)

    df1_processed_true = df1_processed[df1_processed["DebitTag"] == 0]
    df1_processed_flase = df1_processed[df1_processed["DebitTag"] == 1]

    col_pair_list = "df1_processed.Transaction Amount,df1_processed_true.Transaction Amount|df1_processed.Client Code,df1_processed_true.Client Code"
    df_analysis = doCompareRecordsinTwoTables(df1_processed, df1_processed_true, col_pair_list)

    df_analysis_ = doTakeSubString(df_analysis, "Match_ids", 2, 1, "match_tag")
    df_analysis_["DebitTag"] = np.where(df_analysis_["match_tag"] == "M", 0, 1)

    df_analysis_ = df_analysis_.drop(columns = ["Match_ids","match_tag"])

    return df_analysis_


def doVloop(df, ref_df, lookup_col, to_lookup_col_list, new_col_name):

    vlookup_dict = ref_df.set_index(to_lookup_col_list[0])[to_lookup_col_list[1]].to_dict()

    df[new_col_name] = df[lookup_col].map(vlookup_dict)

    return df


def doCreateTimestampinFeedTable(karvy_df1, df1_t):

    b_statement_df_trans = preprocess_rt(df1_t)

    b_statement_df_trans = b_statement_df_trans[b_statement_df_trans["DebitTag"] == 1]

    karvy_df1_ti = doVloop(karvy_df1, b_statement_df_trans, "CLIENT_CODE", ["Client Code","Transaction Date"], "Time Stamp")

#    karvy_df1_ti["Time Stamp"] = df2_t1 = doManipluteColifWhereExist(karvy_df1, "ENTRY_AMT", ["DR_CR", "D"], "*", "-1")

    return karvy_df1_ti

def doKarvy_CMS_FeedVsBank(bank_st_path, feed_path):
    db_config = {
        'host': 'common_db',
        'port': '3306',
        'user': 'root',
        'password': 'root'
        }

    db = DB('excel_karvy', **db_config)
    CMS_Bank = db.get_all('CMS_Bank')
    CMS_feed = db.get_all('CMS_feed')

    df1_t = doTakeSubString(CMS_Bank, "Transaction Description", 4, 6, "Client Code")
    df1_t1 = doManipluteColifWhereExist(df1_t, "Transaction Amount", ["Debit / Credit", "D"], "*", "-1")
    df2_t1 = doManipluteColifWhereExist(CMS_feed, "ENTRY_AMT", ["DR_CR", "D"], "*", "-1")
    groupby_string_kar = "df1_t.Client Code,sample_df1.CLIENT_CODE"
    sumfield_string_kar = "df1_t.Transaction Amount,sample_df1.ENTRY_AMT"

    df1_sum_k, df2_sum_k = doCompareSumByGroupby(df1_t1, df2_t1, groupby_string_kar, sumfield_string_kar)


    col_pair_list = "df1_sum_k.Client Code,df2_sum_k.CLIENT_CODE|df1_sum_k.Transaction Amount,df2_sum_k.ENTRY_AMT"
    #comp_fields_df1 = [ele.split(",")[0].split(".") for ele in col_pair_list.split("|")]

    df_analysis_cms = doCompareRecordsinTwoTables(df1_sum_k, df2_sum_k, col_pair_list)

    karvy_df1_ti = doCreateTimestampinFeedTable(CMS_feed, df1_t)

    karvy_df1_ti_flagg = doFlagRowWhereColumnExist(karvy_df1_ti, "RT_REASON", "RT_REASON_flag")

    req_cols = ["CLIENT_CODE", "ENTRY_AMT", "RT_REASON", "In House number","RT_REASON_flag", "Time Stamp"]

    karvy_df1_ti_flagg_req = karvy_df1_ti_flagg[req_cols]

    match_dict = df_analysis_cms.set_index('Client Code')['Match_ids'].to_dict()

    karvy_df1_ti_flagg_req['Match_Tag'] = karvy_df1_ti_flagg_req["CLIENT_CODE"].map(match_dict)

    karvy_df1_ti_flagg_req.loc[karvy_df1_ti_flagg_req.RT_REASON_flag == 'True', "Match_Tag"] = "RT exception"

    karvy_df1_ti_flagg_req["Time Stamp"] = karvy_df1_ti_flagg_req["Time Stamp"].astype(str)

    return karvy_df1_ti_flagg_req

def doKarvy_BSE_FeedVsBank(bank_st_path, feed_path):
    db_config = {
        'host': 'common_db',
        'port': '3306',
        'user': 'root',
        'password': 'root'
        }

    db = DB('excel_karvy', **db_config)
    # CMS_Bank = db.get_all('CMS_Bank')
    # CMS_feed = db.get_all('CMS_feed')

    bse_df1 = pd.read_csv("/home/user/Algonox/Projects/201908/recon/biz_rules/exchange mfu/Exchange/BSE/MAF_CREDIT_20062019_1831_002046.txt", delimiter= "|")
    bse_df1["Trans_desc"] = "Payout"

    bse_df2 = pd.read_csv("/home/user/Algonox/Projects/201908/recon/biz_rules/exchange mfu/Exchange/BSE/MAF_CREDIT_28062019_1343_000033_L0.txt", delimiter= "|")
    bse_df2["Trans_desc"] = "L0"

    bse_df3 = pd.read_csv("/home/user/Algonox/Projects/201908/recon/biz_rules/exchange mfu/Exchange/BSE/MAF_CREDIT_28062019_1436_000056_L1.txt", delimiter= "|")
    bse_df3["Trans_desc"] = "L1"

    bse_bank = pd.read_excel("/home/user/Algonox/Projects/201908/recon/biz_rules/exchange mfu/Exchange/HDFC BANK Statements MAR 2019.xls")
    bse_bank_ = doColumnSplit(bse_bank, "Transaction Description", "-", "Trans_desc", 1)

    bse_groupbystr = "bse_bank.Value Date,bse_df1.OrderDate"
    bse_sumbystr = "bse_bank.Transaction Amount,bse_df1.Amount"

    bse_df1_sum_k, bse_df2_sum_k = doCompareSumByGroupby(bse_bank_,bse_df1, bse_groupbystr, bse_sumbystr)

    bse_df2_sum_k_date = doStandardizeDate(bse_df2_sum_k, "OrderDate", "%d %b %Y", "date_std")

    bse_df1_sum_k_date = doStandardizeDate(bse_df1_sum_k, "Value Date", "%Y-%m-%d", "date_std")


    col_pair_list = "bse_df1_sum_k_date.date_std,bse_df2_sum_k_date.date_std|bse_df1_sum_k_date.Trans_desc,bse_df2_sum_k_date.Trans_desc|bse_df1_sum_k_date.Transaction Amount,bse_df2_sum_k_date.Amount"
    #comp_fields_df1 = [ele.split(",")[0].split(".") for ele in col_pair_list.split("|")]

    df_analysis_bse = doCompareRecordsinTwoTables(bse_df1_sum_k_date, bse_df2_sum_k_date, col_pair_list)

    return df_analysis_bse


# # -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
# #####################  
#                         KARVY Routes start here
# #####################
# # -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

@app.route("/open_tabs", methods=["POST", "GET"])
def open_tabs():

    # response_dict["tabs"] = tabs
    # response_dict["displayType"] = displayType
    # response_dict["tabDataMap"] = tabDataMap
    print('in open tab route')
    # try:
    # print('in try')
    data = request.json
    print(data)
    flag = True
    feed_type = data["feed_type"]
    print(feed_type)

    # db_config = {
    #     'host': 'common_db',
    #     'port': '3306',
    #     'user': 'root',
    #     'password': 'root',
    #     'tenant_id': 'karvy'
    # }
    # db = DB('excel_configuration', **db_config)
    # # # db = DB('io_configuration')

    # excel_config = db.get_all('excel_configuration')

    # # Sanity checks
    # if (excel_config.loc[excel_config['type'] == 'Document'].empty):
    #     message = 'Excel not configured in DB.'
    #     # logging.error(message)
    #     return jsonify({'flag': False, 'message': message})
    # else:
    #     excel_path = excel_config.iloc[0]['access_1']

    # # logging.debug(f'excel_path : {excel_path}')

    # if (excel_path is None or not excel_path):
    #     message = 'Email is empty/none in DB.'
    #     # logging.error(message)
    #     return jsonify({'flag': False, 'message': message})

    # excel_path = Path(excel_path)

    excel_path = "./excel"

    print(excel_path)

    bank_st_path = "/home/ubuntu//karvy_excel/CMS/HDFC BANK Statements MAR 2019.xlsx"
    feed_path = "/home/ubuntu//karvy_excel/CMS/MIRAE-25Jun2019.xlsx"
    # text_sample = ""
    # with open("/home/user/Desktop/ACE Testing Folders/excel/Untitled.txt", 'wb') as f:
    #     text_sample = f.read()
    #     print(text_sample)            
    analysed_df_cms = doKarvy_CMS_FeedVsBank(bank_st_path,feed_path)
    print(analysed_df_cms)
    return jsonify({"flag":flag, "msg":"try printing"})
    # except:
    #     print('in except')
    #     flag = False
    #     return jsonify({"flag":flag, "msg":"except printing"})

@app.route("/get_ds1_data", methods=["POST", "GET"])
def get_ds1_data():
    print('in get ds1 route route')

    print('in try')
    data = request.json
    print(data)
    feed_type = data["feed_type"]
    print(feed_type)

    if feed_type == "CMS":
        bank_st_path = "/home/ubuntu/karvy_excel/CMS/HDFC BANK Statements MAR 2019.xls"
        feed_path = "/home/ubuntu/karvy_excel/CMS/MIRAE-25Jun2019.xls"
        # text_sample = ""
        # with open("/home/user/Desktop/ACE Testing Folders/excel/Untitled.txt", 'wb') as f:
        #     text_sample = f.read()
        #     print(text_sample)            
        # try:
        analysed_df_cms = doKarvy_CMS_FeedVsBank(bank_st_path,feed_path)
        # analysed_df_cms['match_tag'] = analysed_df_cms['Match_ids'][0] 
        print(analysed_df_cms)
        columns = analysed_df_cms.columns.tolist()
        # except Exception as e:
        #     print(e)
        print(analysed_df_cms.T.to_dict())
        response = {}
        response["columns"] = columns
        response["records"] = list(analysed_df_cms.T.to_dict().values())
    else:
        response = {"columns": [], "records":[]}

    return jsonify({"data": response})

@app.route("/sample_route_karvy", methods=["POST", "GET"])
def sample_route_karvy():

    # response_dict["tabs"] = tabs
    # response_dict["displayType"] = displayType
    # response_dict["tabDataMap"] = tabDataMap
    print('in sample karvy route')
    try:
        print('in try')
        data = request.json
        print(data)
        flag = True
        feed_type = data["feed_type"]
        print(feed_type)
        response = {}
        tabs = ['Matched']
        response['tabs'] = tabs
        displayType = 'vertical'
        response['displayType'] = displayType
        tabDataMap = {"Matched": {
        "firstgrid": {
            "route": "get_ds1_data",
            "route_params": {"tab_type" : "Matched"}, #pagination details???
            "row_type": "click",
            "row_click_route": "get_row_match_data",
            "row_click_route_params":{"tab_type" : "Matched", "id":0}
        },
        "secondgrid": {
            "row_type": "action_column",
            "action_items": [
            {
            "confirmation": 1,
            "confirmation_message": "Confirm?",
            "parameters": {"tab_type" : "Matched", "action_type" : "Accept", "id":0, "map_to":"map_to"},
            "route": "row_accept",
            "text": "Accept"
            },
            {
            "confirmation": 1,
            "confirmation_message": "Confirm?",
            "parameters": {"tab_type" : "Matched", "action_type" : "Reject", "id":0},
            "route": "row_reject",
            "text": "Reject"
            },
            {
            "confirmation": 1,
            "confirmation_message": "Confirm?",
            "parameters": {"tab_type" : "Matched", "action_type" : "Hold", "id":0},
            "route": "row_hold",
            "text": "Hold"
            }
            ]
        }
        }
        # "Un Matched": {
        # "firstgrid": {
        #     "route": "get_ds1_data",
        #     "route_params": {"tab_type" : "Un Matched"}
        #     # "row_type": "click",
        #     # "row_click_route": "get_row_match_data", #no clicks here as it is unmatched
        #     # "row_click_route_params":[]
        # },
        # "secondgrid": {}
        # },
        # "Potential Match": {
        # "firstgrid": {
        #     "route": "get_ds1_data",
        #     "route_params": {"tab_type" : "Potential Match"},
        #     "row_type": "click",
        #     "row_click_route": "get_row_match_data",
        #     "row_click_route_params":{"tab_type" : "Potential Match", "id":0}
        # },
        # "secondgrid": {
        #     "row_type": "action_column",
        #     "action_items": [
        #     {
        #     "confirmation": 1,
        #     "confirmation_message": "Confirm?",
        #     "parameters": {"tab_type" : "Potential Match", "action_type" : "Accept", "id":0, "map_to":"map_to"},
        #     "route": "row_accept",
        #     "text": "Accept"
        #     },
        #     {
        #     "confirmation": 1,
        #     "confirmation_message": "Confirm?",
        #     "parameters": {"tab_type" : "Potential Match", "action_type" : "Reject", "id":0},
        #     "route": "row_reject",
        #     "text": "Reject"
        #     },
        #     {
        #     "confirmation": 1,
        #     "confirmation_message": "Confirm?",
        #     "parameters": {"tab_type" : "Potential Match", "action_type" : "Hold", "id":0},
        #     "route": "row_hold",
        #     "text": "Hold"
        #     }
        #     ]
        # }
        # },
        # "Others": {
        # "firstgrid": {
        #     "route": "get_ds1_data",
        #     "route_params": {"tab_type" : "Others"},
        #     "row_type": "click",
        #     "row_click_route": "get_row_match_data",
        #     "row_click_route_params":{"tab_type" : "Others", "id":0}
        # },
        # "secondgrid": {
        #     "row_type": "action_column",
        #     "action_items": [
        # {
        #     "confirmation": 1,
        #     "confirmation_message": "Confirm?",
        #     "parameters": {"tab_type" : "Others", "action_type" : "Accept", "id":0, "map_to":"map_to"},
        #     "route": "row_accept",
        #     "text": "Accept"
        #     },
        #     {
        #     "confirmation": 1,
        #     "confirmation_message": "Confirm?",
        #     "parameters": {"tab_type" : "Others", "action_type" : "Reject", "id":0},
        #     "route": "row_reject",
        #     "text": "Reject"
        #     },
        #     {
        #     "confirmation": 1,
        #     "confirmation_message": "Confirm?",
        #     "parameters": {"tab_type" : "Others", "action_type" : "Hold", "id":0},
        #     "route": "row_hold",
        #     "text": "Hold"
        #     }
        #     ]
        # }
        # }
        }

        excel_path = "./excel"

        print(excel_path)

        response['tabDataMap'] = tabDataMap
        return jsonify({"flag":flag, "data":response})
    except:
        print('in except')
        flag = False
        return jsonify({"flag":flag, "data":{}})


@zipkin_span(service_name='business_rules', span_name='apply_business_rules')
def apply_business_rules(api=False, table_data = None, stage=None, case_id=None):
    # queue_db_config = {
    #     'host': 'queue_db',
    #     'port': 3306,
    #     'user': 'root',
    #     'password': 'root'
    # }



    # queue_db = DB('queues', **queue_db_config)
    # queue_db = DB('queues')

    # process_queue = queue_db.get_all('process_queue')
    # start_get_queue = time()
    # process_queue = queue_db.execute(f"select id, case_id, file_name from process_queue where `case_id` = '{case_id}'")
    # process_queue = queue_db.get_all('process_queue',discard=['ocr_data','ocr_text','xml_data'])
    # print("time_takne - queue_db get all - ",time()-start_get_queue)


    # start_process_queue = time()
    # case_data = process_queue.loc[process_queue['case_id'] == case_id]
    # file_name = list(process_queue.file_name)[0]
    # print("time_taken - process_queue - ", time() - start_process_queue)

    file_name = ''
    start_get_rule = time()
    if stage in stage_rules:
        rules = stage_rules[stage]
    else:
        rules = get_rules(stage)
    # rules = get_rules(stage)
    result_dict = {'case_id': [case_id], 'file_name': [file_name]}
    record = pd.DataFrame.from_dict(result_dict)
    print("time_taken - get rules - ", time() - start_get_rule)

    tables = {"extraction" : ["business_rule","ocr","sap","validation"],
        "queues" : ["ocr_info"]}
    if not table_data:
        table_data = get_tables_data(tables, case_id)
        table_data['update'] = {}

    try:
        print(f'\nRunning stage `{stage}`...')
        record = evaluate_business_rules(record, rules, table_data)
        if not api:
            update_values = update_table(table_data, case_id, tables)
            return {'flag': True, 'message': 'Applied business rules.', 'send_data': {'case_id': case_id},'updates': update_values}
        return {'flag': True, 'message': 'Applied business rules.', 'send_data': {'case_id': case_id}}
    except:
        traceback.print_exc()
        return {'flag': False, 'message': 'Business rules execution failed'}

@app.route('/run_business_rule', methods=['POST', 'GET'])
# @zipkin_span(service_name='business_rules', span_name='run_business_rule')
def run_business_rule():
    with zipkin_span(service_name='business_rules', span_name='run_business_rule', 
        transport_handler=http_transport,
        # port=5014,
        sample_rate=0.5,):
        data = request.json

        print("Submit data", data)
        if 'case_id' not in data:
            message = f'`case_id` key not provided.'
            print(message)
            return jsonify({'flag': False, 'message': message})
        
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
                if stage == 'One':
                    case_meta = {
                        'status':'Validating',
                        'case_lock':1
                    }
                    DAO.run_business_rule_update_case(case_meta=case_meta, case_id=case_id)
                    
                data = apply_business_rules(api=True, table_data= table_data,stage=stage, case_id=case_id)
                print("time taken - ",time() - starting_time)
                
                if data['flag'] and stage == 'One':
                    case_meta = {
                        'status':'Validated Successfully',
                        'case_lock':0
                    }
                    DAO.run_business_rule_update_case(case_meta=case_meta, case_id=case_id)

                if not data['flag'] and stage == 'One':
                    case_meta = {
                                    'status':'Validation Failed',
                                    'case_lock':0,
                                    'failure_status':1
                                }
                    DAO.run_business_rule_update_case(case_meta=case_meta, case_id=case_id)
                    
                    DAO.update_error_msg(data['message'], case_id)


            
            update_values = update_table(table_data, case_id, tables)

            return jsonify({'flag': True, 'message': 'Applied all business rules.', 'updates':update_values})
        
        stages = data['stage']
        starting_time = time()
        if type(stages) is str:

            if stages == 'One':
                case_meta = {
                    'status':'Validating',
                    'case_lock':1
                }
                DAO.run_business_rule_update_case(case_meta=case_meta, case_id=case_id)
                

            data = apply_business_rules(api=True, table_data = table_data,**data)
            time_taken = time() - starting_time
            data['time_taken'] = time_taken
            # print("time takne - ",time_taken)
            update_values = update_table(table_data, case_id, tables)
            data['updates'] = update_values

            if data['flag'] and stages == 'One':
                case_meta = {
                    'status':'Validated Successfully',
                    'case_lock':0
                }
                DAO.run_business_rule_update_case(case_meta=case_meta, case_id=case_id)

            if not data['flag'] and stages == 'One':
                case_meta = {
                    'status':'Validation Failed',
                    'case_lock':0,
                    'failure_status':1
                }
                DAO.run_business_rule_update_case(case_meta=case_meta, case_id=case_id)

                DAO.update_error_msg(data['message'], case_id)

            return jsonify(data)
        elif type(stages) is list:
            for stage in stages:
                # starting_time = time()
                rule_response = apply_business_rules(api=True, table_data= table_data,stage=stage, case_id=case_id)
                if not rule_response['flag']:
                    message = f'Something went wrong running stage at `{stage}`. Skipping other rules.'
                    print(message)
                    update_values = update_table(table_data, case_id, tables)

                    return jsonify({'flag': False, 'message': message, 'updates':update_values})

        update_values = update_table(table_data, case_id, tables)

        print("time takne - ",time() - starting_time)
        return jsonify({'flag': True, 'message': 'Completed runninig business rules.', 'updates':update_values})

@app.route('/validate_rules', methods=['POST', 'GET'])
# @zipkin_span(service_name='business_rules', span_name='validate_rules')
def validate_rules():
    with zipkin_span(service_name='business_rules', span_name='validate_rules', 
        transport_handler=http_transport,
        # port=5014,
        sample_rate=0.5,):
        data = request.json

        if 'case_id' not in data:
            message = f'`case_id` key not provided.'
            print(message)
            return jsonify({'flag': False, 'message': message})
        
        case_id = data['case_id']
        columns = data.pop('columns', None)
        
        case_validation_df = DAO.validate_rules_get_data(case_id=case_id)

        # If no columns are provided check validation result of all columns
        if columns is None:
            columns = list(validation_df)

        print(f' - Selecting columns: {columns}')
        validation_selected_columns = case_validation_df[columns]
        validation_dict = validation_selected_columns.to_dict(orient='records')[0]

        for column, value in validation_dict.items():
            if value is not None and not value:
                message = f'`{column}` is not validated. ({value})'
                print(message)
                return jsonify({'flag': False, 'message': message}) 

        return jsonify({'flag': True, 'message': 'All validations are true.'}) 

@app.route('/run_business_rule_cg', methods=['POST', 'GET'])
def run_business_rule_cg():
    with zipkin_span(service_name='business_rules', span_name='run_business_rule_cg', 
        transport_handler=http_transport,
        # port=5014,
        sample_rate=0.5,):
        try:
            data = request.json
            case_id = data['case_id']
            fields = data['fields']

            # queue_db_config = {
            #     'host': 'queue_db',
            #     'port': 3306,
            #     'user': 'root',
            #     'password': 'root'
            # }
            # queue_db = DB('queues', **queue_db_config)

            fields_def_df = queue_db.get_all('field_definition')
            tabs_def_df = queue_db.get_all('tab_definition')
            fields_w_name = {}
            for k,v in fields.items():
                # print(k)
                field_k_df = fields_def_df.loc[fields_def_df['unique_name'] == k] 
                disp_name = list(field_k_df.display_name)[0]
                tab_id = list(field_k_df.tab_id)[0]
                # print(tabs_def_df.ix[tab_id])
                # print(list(tabs_def_df.ix[tab_id]))
                tab_name = list(tabs_def_df.ix[tab_id])[0]
                table_name = tab_name.lower().replace(' ', '_')
                
                if table_name not in fields_w_name:
                    fields_w_name[table_name] = {}

                fields_w_name[table_name][disp_name] = v

            extraction_db_config = {
                'host': 'extraction_db',
                'port': 3306,
                'user': 'root',
                'password': 'root'
            }
            extraction_db = DB('extraction', **extraction_db_config)
            
            # print(fields_w_name)
            for table, fields in fields_w_name.items():
                extraction_db.update(table, update=fields, where={'case_id': case_id})
            
            return jsonify({'flag': True, 'message': 'All validations are true.'}) 
        except Exception as e:
            print(e)
            return jsonify({'flag': False, 'message': 'Something fishy.'}) 

@app.route('/show_decision_tree', methods=['POST', 'GET'])
def show_decision_tree():
    data = request.json
    print(data)
    case_id = data['case_id']

    business_rules_db_config = {
                            'host':os.environ['HOST_IP'],
                            'user':'root',
                            'password':os.environ['LOCAL_DB_PASSWORD'],
                            'port':'3306'
                            }
    business_rules_db = DB('business_rules', **business_rules_db_config)
    # queues_db_config = {
    #                 'host': 'queue_db',
    #                 'port': 3306,
    #                 'user': 'root',
    #                 'password': 'AlgoTeam123'
    #             }
    # queues_db = DB('queues', **queues_db_config)
    
    try:
        sequence_rule_data_df = business_rules_db.execute("SELECT * from `sequence_rule_data` where `group`='chain'")
        # chained_rules = [[e['rule_id'], e['rule_string'], e['next_if_sucess'], e['next_if_failure'], e['stage']] for e in df.to_dict(orient='records') ]
        chained_rules = sequence_rule_data_df.to_dict(orient = 'records')
        print(chained_rules)
    except:
        print("Error fetching details from sequence_rule_data.")
        traceback.print_exc()   
        chained_rules = []
    try:
        rule_data_df = business_rules_db.execute(f"SELECT * FROM `rule_data` WHERE `case_id` = '{case_id}'")
        trace_array = json.loads(list(rule_data_df['trace_data'])[0])
    except:
        print("Error in Fetching trace_array from decision_tree_trace.")
        traceback.print_exc()
        trace_array = []
    try:
        trace_dict = json.loads(list(rule_data_df['rule_params'])[0])
    except:
        print("Error in Fetching trace_dict from decision_tree_trace.")
        traceback.print_exc()
        trace_dict = {}
    print("trace_dict", trace_dict)
    # Uncomment trace_dict line in the output dictionary once trace_dict generation
    # is enabled in chained_rules.py 
    if chained_rules:
        output = {
                    'flag' : 'True',
                    'data' : chained_rules,
                    'trace': trace_array,
                    'testData' : trace_dict
                    }
        return jsonify(output)
    else:
        return jsonify({'flag' : 'False', 'msg' : 'No chained rules in DB'})


def result_proxy_to_df(result_proxy):
    a, d = [], {} 
    for row in result_proxy:
        for column, value in row.items():
            d= {**d, **{column : value}}
        a.append(d)
    return a
