# -*- coding: utf-8 -*-
"""
Created on Tue Aug 27 20:35:20 2019

@author: Admin
"""

import schedule
import time
from datetime import datetime, timedelta
from db_utils import DB
import json
import traceback

db_config = {
    'host': 'queue_db',
    'port': 3306,
    'user': 'root',
    'password': ''
}

queue_db = DB('queues', **db_config)
extraction_db = DB('extraction', **db_config)
alorica_db = DB('alorica_data', **db_config)

def delete_data():
    query = "SELECT * from process_queue where queue = 'Completed'"
    case_ids = list(queue_db.execute(query).case_id)
    
    create_tuple = ''
    for i, case_id in enumerate(case_ids):
        if i == 0:
            create_tuple += f'("{case_id}",'
        elif i == len(case_ids) - 1:
            create_tuple += f'"{case_id}")'
        else:
            create_tuple += f'"{case_id}",'
    
    delete_query = f"DELETE FROM `process_queue` WHERE case_id in {create_tuple}"
    queue_db.execute(delete_query)
    
    delete_query = f"DELETE FROM `merged_blob` WHERE case_id in {create_tuple}"
    queue_db.execute(delete_query)

    delete_query = f"DELETE FROM `screen_shots` WHERE Fax_unique_id in {create_tuple}"
    alorica_db.execute(delete_query)
    
    delete_query = f"DELETE FROM `ocr` WHERE case_id in {create_tuple}"
    extraction_db.execute(delete_query)
    
    return "Done"
    
    
    
def move_to_manual():
    query = "SELECT * from process_queue where queue not in ('Enhance Decision', 'Express Cases', 'Completed', 'Template Exceptions')"
    case_ids = list(queue_db.execute(query).case_id)
    
    for case_id in case_ids:
        try:
            query = f"SELECT id, communication_date_time from process_queue where case_id = '{case_id}'"
            communication_date = list(extraction_db.execute(query).communication_date_time)[0]
            
            communication_date = datetime.strptime(communication_date, '%d-%m-%Y %H:%M:%S')
            get_current_time = datetime.now() 

            time_difference = (get_current_time - communication_date).total_seconds()/3600

            if time_difference > 2:
                query = f"Update process_queue set queue = 'Express Cases', case_lock = 0, state = 'Bot failed', failure_status = 2, 'error_logs' = 'remaining TAT is less than 2 hours' where case_id = '{case_id}'"
                queue_db.execute(query)
        except:
            traceback.print_exc()
            pass
            
    return "Done"
            
schedule.every(15).minutes.do(move_to_manual)
schedule.every().day.at("23:30").do(delete_data)


if __name__ == '__main__':
    while True:
        schedule.run_pending()
        time.sleep(10)