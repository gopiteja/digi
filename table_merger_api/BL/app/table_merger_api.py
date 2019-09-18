import argparse
import re
import ast
import pandas as pd
import traceback
import requests

from flask import Flask, request, jsonify
from flask_cors import CORS

try:
    from app.db_utils import DB
except:
    from db_utils import DB

from app import app
from py_zipkin.zipkin import zipkin_span, ZipkinAttrs, create_http_headers_for_new_span

try:
    from .ace_logger import Logging
except:
    from ace_logger import Logging

logging = Logging()

def http_transport(encoded_span):
    # The collector expects a thrift-encoded list of spans. Instead of
    # decoding and re-encoding the already thrift-encoded message, we can just
    # add header bytes that specify that what follows is a list of length 1.
    body =encoded_span
    requests.post(
            'http://servicebridge:5002/zipkin',
        data=body,
        headers={'Content-Type': 'application/x-thrift'},
    )

@zipkin_span(service_name='table_merger_api', span_name='table_as_kv')
def table_as_kv(extracted_data_maintable):
    extracted_data_maintable_kv = {}

    table_head = extracted_data_maintable[0]
    # print(table_head)
    nested = False
    if table_head[0][1] == 2:
        nested = True

    table_rows = extracted_data_maintable[1:]
    nested_col = []
    if nested:
        table_rows = extracted_data_maintable[2:]
        nested_col = extracted_data_maintable[1]
    header_names = []

    head_map = {}

    for ind, head in enumerate(table_head):
        head[0] = head[0].replace('<b>','')
        head[0] = head[0].replace('</b>','')
        if nested:
            if head[1] == 1:
                col_span = head[2]
                head_nest = nested_col[:col_span]
                temp = []
                for i in range(len(head_nest)):
                    # print(head[0]+'.'+head_nest[i][0])
                    temp.append(head[0]+'.'+head_nest[i][0].strip())
                    header_names.append(head[0]+'.'+head_nest[i][0].strip())
                if temp:
                    head_map[ind] = temp
                nested_col = nested_col[col_span:]
            else:
                header_names.append(head[0])
                head_map[ind] = head[0]
        else:
            header_names.append(head[0])
            head_map[ind] = head[0]
    # print('header_names',header_names)
    # print(len(header_names))
    for row in table_rows:
        for i in range(len(row)):
            if header_names[i] not in extracted_data_maintable_kv:
                extracted_data_maintable_kv[header_names[i]] = [row[i][0]]
            else:
                extracted_data_maintable_kv[header_names[i]].append(row[i][0])
    return extracted_data_maintable_kv

@app.route('/merge_table', methods=['POST', 'GET'])
def merge_table():
    data = request.json
    tenant_id = data.pop('tenant_id', None)
    with zipkin_span(service_name='table_merger_api', span_name='merge_table', 
            transport_handler=http_transport, port=5007, sample_rate=0.5,) as  zipkin_context:
        try:
            zipkin_context.update_binary_annotations({'Tenant': tenant_id})
        except:

            case_id = data['case_id']

            logging.debug(f"Merging table for case_id:{case_id}")

            tables = ['json_reader','sap','ocr','business_rule']

            # Database configuration
            db_config = {
                'host': 'extraction_db',
                'user': 'root',
                'password': 'root',
                'port': '3306',
                'tenant_id': tenant_id
            }
            db = DB('extraction', **db_config)
            # db = DB('extraction') # Development purpose

            combined_table_data = {}
            for table in tables:
                db_table_data = db.get_all(table)
                try:
                    case_file = db_table_data.loc[db_table_data['case_id'] == case_id]
                    latest_case_file = db.get_latest(case_file, 'case_id', 'created_date')
                except:
                    case_file = db_table_data.loc[db_table_data['Portal Reference Number'] == case_id]
                    latest_case_file = db.get_latest(case_file, 'Portal Reference Number', 'created_date')

                if case_file.empty:
                    logging.debug(f'Case ID `{case_id}` does not exist in table `{table}`. Skipping.')
                    continue

                combined_table_data = {
                    **combined_table_data,
                    **latest_case_file.to_dict(orient='records')[0]
                }

            combined_table_data.pop('created_date')
            table_string = combined_table_data.pop('Table', None)

            if table_string is None:
                logging.debug('No table.')
                table_list = []
            else:
                table_list = ast.literal_eval(table_string)

            try:
                table_kv = table_as_kv(table_list[0][0][0])
            except:
                table_kv = {}

            valid_table_headers = ['Product Description', 'Quantity', 'Rate', 'Gross Amount', 'HSN/SAC']

            list_final_data = []
            if table_kv:
                for table_header, value in table_kv.items():
                    for index, row_value in enumerate(value):
                        if table_header.replace('Table.','') in valid_table_headers:
                            combined_table_data[table_header.replace('Table.','')] = row_value
                            if len(list_final_data) <= index:
                                list_final_data.append(combined_table_data.copy())
                            else:
                                list_final_data[index][table_header.replace('Table.','')] = row_value
            else:
                list_final_data.append(combined_table_data)

            if len(list_final_data) == 0:
                list_final_data.append(combined_table_data)

            for row in list_final_data:
                for key, value in row.items():
                    if key in ['IGST amount', 'Invoice Base Amount', 'Rate', 'Invoice Total', 'SGST/CGST Amount', 'Gross Amount']:
                        try:
                            row[key] = float(''.join(re.findall(r'[0-9\.]', value)))
                        except:
                            pass
                    if key in ['HSN/SAC', 'Quantity']:
                        try:
                            row[key] = int(''.join(re.findall(r'[0-9]', value)))
                        except:
                            pass

            final_df = pd.DataFrame(list_final_data)

            # print(final_df.to_dict(orient='records'))
            try:
                final_df.to_sql('combined', con=db.engine, if_exists='append', index=False, index_label='id')
                return jsonify({'flag': True, 'data': list_final_data})
            except:
                logging.exception('Error combining table.')
                return jsonify({'flag': False, 'message': 'Error combining table.'})
        except Exception as e:
            return jsonify({'flag': False, 'message':'System error! Please contact your system administrator.'})
