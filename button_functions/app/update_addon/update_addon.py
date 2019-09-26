import json
import traceback
import os

from datetime import datetime, timedelta
from kafka import KafkaConsumer, TopicPartition
from random import randint
from time import sleep

from db_utils import DB

try:
    from app.producer import produce
    from app.ace_logger import Logging
except:
    from producer import produce
    from ace_logger import Logging

logging = Logging().getLogger('ace')

db_config = {
    'host': os.environ['HOST_IP'],
    'user': os.environ['LOCAL_DB_USER'],
    'password': os.environ['LOCAL_DB_PASSWORD'],
    'port': os.environ['LOCAL_DB_PORT']
}

def get_details(customer_id, tenant_id):
    """very hsbc specific ...lot of hard codings"""
    stats_db = DB('hsbc_stats', tenant_id=tenant_id, **db_config)
    params = [customer_id]
    query = "SELECT `Global Business` from `UCIC_Details_Source` where `Customer Id` = %s"
    lob = list(stats_db.execute_default_index(query, params=params)['Global Business'])[0]
    query = "SELECT `Account Number`, `GHO` from `Closed_Accounts_Source` where `Customer Id` = %s"
    df = stats_db.execute_default_index(query, params=params)
    accn_num, gho = (list(df['Account Number'])[0], list(df['GHO'])[0])
    
    return accn_num, gho, lob

def update_addon(data, tenant_id):
    try:
        case_id = data['case_id']

        extraction_db = DB('extraction', tenant_id=tenant_id, **db_config)
        # get the data from the ocr table
        query = "SELECT `id`,`Add On Table` from `ocr` where case_id = %s"
        params = [case_id]
        df = extraction_db.execute(query, params=params)
        new_addon_tables = []
        new_addon_table = {}
        
        addon_table_string = list(df['Add On Table'])[0]
        addon_table = json.loads(addon_table_string)
        # print (addon_table)
        header = addon_table[0]['header'] # hard coded part
        new_addon_table['header'] = header
        # print (new_addon_table)
        customer_ids = [val['Customer ID'] for val in addon_table[0]['rowData']] # hard coded part
        row_data = []
        for customer_id in customer_ids:
            cust_acc_num, gho_code, lob = get_details(customer_id, tenant_id)
            row_data.append({'Customer ID': customer_id, 'Customer Account Number': cust_acc_num, 'GHO Code':gho_code,  'LOB':lob})
        new_addon_table['rowData'] = row_data
        new_addon_tables.append(new_addon_table)
        # update in the data base
        extraction_db.update('ocr', {'Add On Table':json.dumps(new_addon_tables)}, where={'case_id':case_id})
        # return success
        return {'flag':True, 'message': "Addon_Table updated successfully"}
    except Exception as e:
        print ('error updating addon table')
        print (str(e))
        return {'flag':False, 'error':str(e), 'message':"Error in updating addon_table"}


def consume(broker_url='broker:9092'):
    try:
        route = 'update_addon'
        logging.info(f'Listening to topic: {route}')

        consumer = KafkaConsumer(
            bootstrap_servers=broker_url,
            value_deserializer=lambda value: json.loads(value.decode()),
            auto_offset_reset='earliest',
            group_id='update_addon',
            api_version=(0,10,1),
            enable_auto_commit=False,
            session_timeout_ms=800001,
            request_timeout_ms=800002
        )
        logging.debug('Consumer object created.')

        parts = consumer.partitions_for_topic(route)
        if parts is None:
            logging.warning(f'No partitions for topic `{route}`')
            logging.debug(f'Creating Topic: {route}')
            produce(route, {})
            logging.info(f'Listening to topic `{route}`...')
            while parts is None:
                consumer = KafkaConsumer(
                    bootstrap_servers=broker_url,
                    value_deserializer=lambda value: json.loads(value.decode()),
                    auto_offset_reset='earliest',
                    group_id='sap_portal',
                    api_version=(0,10,1),
                    enable_auto_commit=False,
                    session_timeout_ms=800001,
                    request_timeout_ms=800002
                )
                parts = consumer.partitions_for_topic(route)
                logging.warning("No partition. In while loop. Make it stop")

        partitions = [TopicPartition(route, p) for p in parts]
        consumer.assign(partitions)


        for message in consumer:
            data = message.value
            logging.info(f'Message: {data}')

            try:
                case_id = data['case_id']
                functions = data['functions']
                tenant_id = data.get('tenant_id', None)
            except Exception as e:
                logging.warning(f'Recieved unknown data. [{data}] [{e}]')
                consumer.commit()
                continue
            
            kafka_db = DB('kafka', tenant_id=tenant_id, **db_config)
            queue_db = DB('queues', tenant_id=tenant_id, **db_config)

            query = 'SELECT * FROM `button_functions` WHERE `route`=%s'
            function_info = queue_db.execute(query, params=[route])
            in_progress_message = list(function_info['in_progress_message'])[0]
            failure_message = list(function_info['failure_message'])[0]
            success_message = list(function_info['success_message'])[0]
            
            message_flow = kafka_db.get_all('grouped_message_flow')
            # Get which button (group in kafka table) this function was called from
            group = data['group']

            # Get message group functions
            group_messages = message_flow.loc[message_flow['message_group'] == group]

            # If its the first function the update the progress count
            first_flow = group_messages.head(1)
            first_topic = first_flow.loc[first_flow['listen_to_topic'] == route]

            query = 'UPDATE `process_queue` SET `status`=%s, `total_processes`=%s, `case_lock`=1 WHERE `case_id`=%s'
            if not first_topic.empty:
                if list(first_flow['send_to_topic'])[0] is None:
                    queue_db.execute(query, params=[in_progress_message, len(group_messages), case_id])
                else:
                    queue_db.execute(query, params=[in_progress_message, len(group_messages) + 1, case_id])

            # Getting the correct data for the functions. This data will be passed through
            # rest of the chained functions.
            function_params = {}
            for function in functions:
                if function['route'] == route:
                    function_params = function['parameters']
                    break

            # Call the function
            try:
                logging.debug(f'Calling function `update_addon`')
                result = update_addon(function_params, tenant_id)
            except:
                # Unlock the case.
                logging.exception(f'Something went wrong while updating changes. Check trace.')
                query = 'UPDATE `process_queue` SET `status`=%s, `case_lock`=0, `failure_status`=1 WHERE `case_id`=%s'
                queue_db.execute(query, params=[failure_message, case_id])
                consumer.commit()
                continue

            # Check if function was succesfully executed
            if result['flag']:
                # If there is only function for the group, unlock case.
                if not first_topic.empty:
                    if list(first_flow['send_to_topic'])[0] is None:
                        # It is the last message. So update file status to completed.
                        query = 'UPDATE `process_queue` SET `status`=%s, `case_lock`=0, `completed_processes`=`completed_processes`+1 WHERE `case_id`=%s'
                        queue_db.execute(query, params=[success_message, case_id])
                        consumer.commit()
                        continue

                last_topic = group_messages.tail(
                    1).loc[group_messages['send_to_topic'] == route]
                
                # If it is not the last message, then produce to next function else just unlock case.
                if last_topic.empty:
                    # Get next function name
                    next_topic = list(
                        group_messages.loc[group_messages['listen_to_topic'] == route]['send_to_topic'])[0]

                    if next_topic is not None:
                        logging.debug('Not the last topic of the group.')
                        produce(next_topic, data)

                    # Update the progress count by 1
                    query = 'UPDATE `process_queue` SET `status`=%s, `completed_processes`=`completed_processes`+1 WHERE `case_id`=%s'
                    queue_db.execute(query, params=[success_message, case_id])
                    consumer.commit()
                else:
                    # It is the last message. So update file status to completed.
                    logging.debug('Last topic of the group.')
                    query = 'UPDATE `process_queue` SET `status`=%s, `case_lock`=0, `completed_processes`=`completed_processes`+1 WHERE `case_id`=%s'
                    queue_db.execute(query, params=[success_message, case_id])
                    consumer.commit()
            else:
                # Unlock the case.
                logging.debug('Flag false. Unlocking case with failure status 1.')
                query = 'UPDATE `process_queue` SET `status`=%s, `case_lock`=0, `failure_status`=1 WHERE `case_id`=%s'
                queue_db.execute(query, params=[failure_message, case_id])
                consumer.commit()
    except:
        logging.exception('Something went wrong in consumer. Check trace.')

if __name__ == '__main__':
    consume()
