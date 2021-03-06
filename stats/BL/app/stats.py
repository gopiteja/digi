#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Jul 18 11:37:38 2019

@author: Amith
"""

import json
import requests
from db_utils import DB
from flask import Flask, request, jsonify
from flask_cors import CORS
from app.stats_db import Stats_db
from datetime import datetime, timedelta
from statistics import mean

try:
    from app.ace_logger import Logging
except:
    from ace_logger import Logging

from app import app
from py_zipkin.zipkin import zipkin_span,ZipkinAttrs, create_http_headers_for_new_span

logging = Logging()

db_config = {
    'host': 'queue_db',
    'port': 3306,
    'user': 'root',
    'password': ''
}

stats_db = DB('stats', **db_config)
queue_db = DB('queues', **db_config)
template_db = DB('template_db', **db_config)

dummy = False

def http_transport(encoded_span):
    # The collector expects a thrift-encoded list of spans. Instead of
    # decoding and re-encoding the already thrift-encoded message, we can just
    # add header bytes that specify that what follows is a list of length 1.
    body =encoded_span
    requests.post(
            'http://servicebridge:80/zipkin',
        data=body,
        headers={'Content-Type': 'application/x-thrift'},
    )

def make_chunks(chart_data, split):
    for i in range(0, len(chart_data), split):
        yield chart_data[i:i + split]
        
def sum_points(chunks):
    average_points = []
    for chunk in chunks:
        average_points.append(sum(chunk))
    return average_points

def create_data(all_dates, db_data):
    chart_data = []
    for i, day in enumerate(all_dates):
        found = None
        for ele in db_data:
            if day.date() == ele['date']:
                chart_data.append(ele['no_of_files'])
                found = True
        if not found:
            chart_data.append(0)
    return chart_data


@app.route("/get_stats_cards", methods = ['POST', 'GET'])
def get_stats():
    data = request.json
    tenant_id = data.pop('tenant_id', None)
    print(f'tenant id {tenant_id}')
    with zipkin_span(service_name='stats', span_name='get_stats_cards', 
            transport_handler=http_transport, port=5007, sample_rate=0.5,) as  zipkin_context:
        zipkin_context.update_binary_annotations({'Tenant': tenant_id})
    
        try:
            from_date = data['fromDate']
            to_date = data['toDate']
        except Exception as e:
            logging.error("Unexpected request data", e)
            return "Unexpected request data" 
        stats_db_obj = Stats_db(tenant_id=f'{tenant_id}')
        try:
            active_stats_dict = stats_db_obj.active_stats() #List of dictionaries - one for each card
        except:
            logging.exception("Something went wrong in stats DB. Check trace.")
            return "Failed - Unable to connect to the database stats, Please check configuration in stats_db.py"
        return jsonify({"data" : active_stats_dict})

def fix_JSON(json_message=None):
    result = None
    try:
        result = json.loads(json_message)
    except Exception as e:
        # Find the offending character index:
        idx_to_replace = int(str(e).split(' ')[-1].replace(')',''))
        # Remove the offending character:
        json_message = list(json_message)
        json_message[idx_to_replace] = ' '
        new_message = ''.join(json_message)
        return fix_JSON(json_message=new_message)
    return result

@app.route('/text_data', methods=['POST', 'GET'])
def text_data():
    data = request.json
    from_date = data['fromDate']
    to_date = data['toDate']
    total_fields = 10
    if not dummy:
        """Return the ocr stats from the from_date, to_date"""
        print (from_date, to_date, "dates")
        try:
            if (not to_date) or (not from_date):
                query = "SELECT fa.fields_changed, pq.created_date FROM `field_accuracy` fa,process_queue pq where fa.case_id =pq.case_id and pq.queue='Completed'"
                df = queue_db.execute_(query)
            else:
                if to_date == from_date:
                    from_date += " 00:00:01"
                    to_date += " 23:59:59"
                query = "SELECT fa.fields_changed, pq.created_date FROM `field_accuracy` fa,process_queue pq where fa.case_id =pq.case_id and pq.queue='Completed' and pq.created_date > %s and pq.created_date < %s"
                df = queue_db.execute_(query, params=[from_date, to_date])

            fields_changes_list = []

            for ele in list(df['fields_changed']):
                try:
                    fields_changes_list.append(len(json.loads(ele,strict=False)))
                except:
                    fix_json_ele = fix_JSON(ele)
                    fields_changes_list.append(len(fix_json_ele))

            manual_changes = sum(fields_changes_list)
            total = len(df['fields_changed'])*total_fields
            extracted_ace = total - manual_changes
            print (f"{manual_changes} {extracted_ace} {total} {manual_changes + extracted_ace}")

            manual_percent = int(manual_changes/total)*100
            auto_percent = 100 - manual_percent
        except:
            manual_percent = 0
            auto_percent = 0
    else:
        manual_percent = 20
        auto_percent = 80

    data = [{"name":'Manual ',"value":manual_percent},{"name":'Auto',"value":auto_percent }]
    return jsonify({"data":data, "name": "Fields Captured"})

@app.route('/string_data', methods=['POST', 'GET'])
def string_data():
    ui_data = request.json
    header = ui_data['header']
    try:
        scale = ui_data['scale']
    except:
        scale = 'week'
    
    data = {}
    total_invoices = 0
    chart_heading = ''
    return_data = [0]*7

    if scale in ['week', 'today']:
        no_days = 7
        split = 1
        week_days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
        today = datetime.today().strftime('%A')[:3]
        index = week_days.index(today) + 1
        week_list = week_days[index:] + week_days[:index]
        return_data = [0]*7
    if scale == 'month':
        no_days = 28
        split = 7
        week_list = ['4 weeks', '3 weeks', 'Last week', 'This week']
        return_data = [0]*4
    if scale == 'year':
        no_days = 360
        split = 30
        week_days = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
        index = datetime.today().month
        week_list = week_days[index:] + week_days[:index]
        return_data = [0]*12
    
    end = (datetime.today() + timedelta(days=1)).strftime('%Y-%m-%d')
    begin = (datetime.today() - timedelta(days=no_days)).strftime('%Y-%m-%d')
    all_dates = []
    for i in range(1,no_days+1):
        day = datetime.today() - timedelta(days=no_days) + timedelta(days=i)
        all_dates.append(day)
        
    if header.lower() == 'ace details':
        if not dummy:
            # query = "SELECT id, case_id FROM process_queue"
            # total_invoices = len(list(queue_db.execute(query).case_id))
            
            try:
                query = f"SELECT date, no_of_files from state_stats where date > '{begin}' and date < '{end}' and state = 'Completed'"
                query_result = stats_db.execute_(query)
                audit = query_result.to_dict(orient='records')

                total_invoices = sum(list(audit.no_of_files))
                    
                chart_data = create_data(all_dates, audit)

                chunks = list(make_chunks(chart_data, split))

                # return_data = sum_points(chunks)
                return_data = chunks
            except:
                total_invoices = 0
                return_data = [0]*len(week_days)
        else:
            week_days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
            today = datetime.today().strftime('%A')[:3]
            index = week_days.index(today) + 1
            week_list = week_days[index:] + week_days[:index]
            total_invoices = 63
            return_data = [10, 5, 8, 9, 4, 11, 6]
            
        data = {
          "data": {
            "name": "Cases processed in ACE",
            "value": total_invoices,
            "chartHeading": '',
            "chartHeadingData": week_list,
            "chartData": return_data
          }
        }

    if header.lower() == 'bot flow':
        if not dummy:           
            query = f"SELECT date, no_of_files from state_stats where state = 'by bot' and date > '{begin}' and date < '{end}'"
            query_result = stats_db.execute_(query)
            audit = query_result.to_dict(orient='records')
            total_invoices = sum(list(query_result.no_of_files))
                
            chart_data = create_data(all_dates, audit)

            chunks = list(make_chunks(chart_data, split))

            return_data = sum_points(chunks)  
        else:
            week_days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
            today = datetime.today().strftime('%A')[:3]
            index = week_days.index(today) + 1
            week_list = week_days[index:] + week_days[:index]
            total_invoices = 13
            return_data = [2, 1, 3, 2, 2, 1, 3]         
            
        data = {
          "data": {
            "name": "Cases processed by Bot",
            "value": total_invoices,
            "chartHeading": '',
            "chartHeadingData": week_list,
            "chartData": return_data
          }
        }
 
    if header.lower() == 'manually processed':    
        if not dummy:
            query = f"SELECT date, no_of_files from state_stats where state = 'Enhance Decision' and date > '{begin}' and date < '{end}'"
            query_result = stats_db.execute_(query)
            audit = query_result.to_dict(orient='records')
            total_invoices = sum(list(query_result.no_of_files))

            chart_data = create_data(all_dates, audit)

            chunks = list(make_chunks(chart_data, split))

            return_data = sum_points(chunks)
        else:
            week_days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
            today = datetime.today().strftime('%A')[:3]
            index = week_days.index(today) + 1
            week_list = week_days[index:] + week_days[:index]
            total_invoices = 50
            return_data = [8, 4, 5, 7, 2, 10, 3]
                
        data = {
          "data": {
            "name": "Cases processed Manually",
            "value": total_invoices,
            "chartHeading": '',
            "chartHeadingData": week_list,
            "chartData": return_data
          }
        }
          
    if header.lower() == 'unique templates':
        query = "SELECT id, template_name FROM trained_info"
        total_invoices = len(list(template_db.execute(query).template_name))
        
        data = {
          "data": {
            "name": "Unique templates trained in ACE",
            "value": total_invoices,
            "chartHeading": "",
            "chartHeadingData": [],
            "chartData": []
          }
        }
      
    return jsonify(data)

@app.route('/flip_card', methods=['POST', 'GET'])
def flip_card():
    ui_data = request.json
    header = ui_data['header']   
    flip_side = ui_data['flip_side']
    
    if header.lower() == 'aht(bot)':
        if flip_side == 'front':
            data = {
                "data": {
                    "name": "AHT for Bot",
                    "value": 10,
                    "chartHeading": "",
                    "chartHeadingData": [],
                    "chartData": []
                }
                }

        else:
            legend_data = ["AHT for Screenshot by Bot","AHT for Ace Fax Fields","AHT for Fax making manually",
            "AHT for Decisioning in ACE","AHT for ICUE validation by bot","AHT for Checker","AHT for ICUE case creation by bot"] 
            values = [1,1,2,1,2,2,1]
            stacked_cols = {
                "AHT for Screenshot by Bot": 1,
                "AHT for Ace Fax Fields":1,
                "AHT for Fax making manually":2,
                "AHT for Decisioning in ACE":1,
                "AHT for ICUE validation by bot":2,
                "AHT for Checker":2,
                "AHT for ICUE case creation by bot":1
            }
            data = {
                "axiscolumns" : legend_data,
                "barname": "Avg Time Taken",
                "axisvalues": values,
                "stackedcolumns":stacked_cols,
                "heading":'Cases in progress',
                "subheading": '',
                "chart_type": "column"
                }
    if header.lower() == 'aht(manual)':
        if flip_side == 'front':
            data = {
                "data": {
                    "name": "AHT for Manual Processing",
                    "value": 15,
                    "chartHeading": "",
                    "chartHeadingData": [],
                    "chartData": []
                }
                }

        else:
            legend_data = ["AHT for Screenshot by Bot","AHT for Ace Fax Fields","AHT for Fax making manually",
            "AHT for Decisioning in ACE","AHT for ICUE case creation by bot"] 
            values = [1,1,2,1,10]
            stacked_cols = {
                "AHT for Screenshot by Bot": 1,
                "AHT for Ace Fax Fields":1,
                "AHT for Fax making manually":2,
                "AHT for Decisioning in ACE":1,
                "AHT for ICUE case creation by bot":10
            }
            data = {
                "axiscolumns" : legend_data,
                "barname": "Avg Time Taken",
                "axisvalues": values,
                "stackedcolumns":stacked_cols,
                "heading":'Cases in progress',
                "subheading": '',
                "chart_type": "column"
                }

    return jsonify(data)
    
@app.route('/chart_data', methods=['POST', 'GET'])
def chart_data():
    try:
        ui_data = request.json
        header = ui_data['header']

        tenant_id = ui_data['tenant_id']
         
        print(f'Tenant_id_in_chart_data{tenant_id}')

        queue_db_config = {
            'host': 'queue_db',
            'port': 3306,
            'user': 'root',
            'password': 'root',
            'tenant_id': tenant_id
        }
        queue_db = DB('queues', **queue_db_config)
        
        if header.lower() == 'snapshot details':
            if not dummy:
                query = "SELECT id, queue as name, COUNT(*) as value FROM process_queue GROUP BY queue"
                real_time = queue_db.execute(query).to_dict(orient='records')

                legend_data = []
                for i in real_time:
                    if not i['name']:
                        i['name'] = 'Unassigned'
                    legend_data.append(i['name'])
                    
                values = []
                for i in real_time:
                    values.append(i['value'])  

                stacked_cols = {}
                for ele in real_time:
                    if not ele['name']:
                        ele['name'] = 'Unassigned'
                    stacked_cols[ele['name']] = ele['value']
            else:
                stacked_cols = {'Completed': 63, 'Fax Data': 25, 'Enhance Decision': 36, 'Decision Review': 13, 'Processing': 17}
                legend_data = list(stacked_cols.keys())
                values = list(stacked_cols.values())

            data = {
            "axiscolumns" : legend_data,
            "barname": "Cases",
            "axisvalues": values,
            "stackedcolumns":stacked_cols,
            "heading":'In progress cases ' + str(sum(values[1:])),
            "subheading": '',
            "chart_type": "column"
            }

            data = {"axiscolumns":["Unassigned","Completed","Decision Review","DEF345","Enhance Decision","Fax Data","GHI678","Manual","Processing","QRS234","Review Cases","Template Exceptions"],"axisvalues":[1,2,2,3,1,7,1,2,1,1,4,14],"barname":"Cases","chart_type":"stacked_column","heading":"In progress cases 38","stackedcolumns":{"Completed":2,"DEF345":3,"Decision Review":2,"Enhance Decision":1,"Fax Data":7,"GHI678":1,"Manual":2,"Processing":1,"QRS234":1,"Review Cases":4,"Template Exceptions":14,"Unassigned":1},"subheading":""}


    except Exception as e:
        logging.exception(f"Unexpected error in snapshot{e}")
 
    return jsonify(data)
