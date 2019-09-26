import json
import os
import traceback

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

logging = Logging()

db_config = {
    'host': os.environ['HOST_IP'],
    'user': os.environ['LOCAL_DB_USER'],
    'password': os.environ['LOCAL_DB_PASSWORD'],
    'port': os.environ['LOCAL_DB_PORT']
}

def update_table(db, case_id, file_name, changed_fields):
    logging.info('Updating table...')

    query = f"SELECT `fields_changed` from `field_accuracy` WHERE case_id='{case_id}'"
    fields_json_string_df = db.execute_(query)
    if not fields_json_string_df.empty:
        fields_json_string = fields_json_string_df['fields_changed'][0]
        fields_json = json.loads(fields_json_string)
        total_fields = changed_fields.pop('total_fields', 1)
        logging.debug(f"Fields JSON before: {fields_json}")
        fields_json.update(changed_fields)
        logging.debug(f"Fields JSON after: {fields_json}")
        percentage = len(fields_json.keys())/total_fields
        query = f"UPDATE `field_accuracy` SET `fields_changed` = '{json.dumps(fields_json)}', `percentage`= '{percentage}'  WHERE case_id='{case_id}'"
        db.execute(query)
        logging.info(f"Updated field accuracy table for case `{case_id}`")
    else:
        # new case_id that means insert record into the database
        total_fields = changed_fields.pop('total_fields', 1)
        percentage = len(changed_fields.keys())/total_fields
        logging.debug(f"Changed fields are {changed_fields}")
        query = f"INSERT INTO `field_accuracy` (`id`, `case_id`, `file_name`, `fields_changed`, `percentage`) VALUES (NULL,'{case_id}','{file_name}','{json.dumps(changed_fields)}','{percentage}')"
        db.execute(query)
        logging.info(f"Inserted into field accuracy for case `{case_id}`")

    return "UPDATED TABLE"

def prepare_trained_info(coordinates, field, value, width):
    trained_info = {}
    trained_info['coordinates'] = [coordinates]
    trained_info['field'] = field
    trained_info['keyCheck'] = False
    trained_info['keyword'] = ''
    trained_info['validations'] = ''
    trained_info['value'] = value
    trained_info['width'] = width
    trained_info['page'] = coordinates['page']

    return trained_info


def save_changes(case_id, data, tenant_id):
    try:
        logging.info('Saving changes...')
        logging.info(f'Data recieved: {data}')

        fields = data['fields']
        changed_fields = data['field_changes']
        verify_operator = data.get('operator', None)
        
        queue_db = DB('queues', tenant_id=tenant_id, **db_config)
        stats_db = DB('stats', tenant_id=tenant_id, **db_config)

        try:
            update_table(queue_db, case_id, "", changed_fields)
        except:
            pass
        fields_def_df = queue_db.get_all('field_definition')
        tabs_def_df = queue_db.get_all('tab_definition')

        fields_w_name = {}

        value_changes = {}

        for unique_name, value in fields.items():
            logging.debug(f'Unique name: {unique_name}')
            unique_field_def = fields_def_df.loc[fields_def_df['unique_name'] == unique_name]
            print(f'heeeeeeeeeeeeeeeeeeeeeeeeerrrrrrrrrrrrreeeeeeeeeeeeeeeeeeeeeeee{unique_field_def.display_name}')
            display_name = list(unique_field_def.display_name)[0]
            tab_id = list(unique_field_def.tab_id)[0]
            tab_info = tabs_def_df.ix[tab_id]
            table_name = tab_info.source

            if table_name not in fields_w_name:
                fields_w_name[table_name] = {}

            fields_w_name[table_name][display_name] = value

        changed_fields_w_name = {}
        for unique_name, value in changed_fields.items():
            logging.debug(f'Unique name: {unique_name}')
            unique_field_def = fields_def_df.loc[fields_def_df['unique_name'] == unique_name]
            display_name = list(unique_field_def.display_name)[0]
            tab_id = list(unique_field_def.tab_id)[0]
            tab_info = tabs_def_df.ix[tab_id]
            table_name = tab_info.source

            if table_name not in changed_fields_w_name:
                changed_fields_w_name[table_name] = {}

            changed_fields_w_name[table_name][display_name] = fields_w_name[table_name][display_name]

        extraction_db = DB('extraction', tenant_id=tenant_id, **db_config)

        try:
            trained_info = {}
            index = 0
            print(data['cropped_ui_fields'])
            for unique_name, cropped_ui_fields in data['cropped_ui_fields'].items():
                unique_field_def = fields_def_df.loc[fields_def_df['unique_name'] == unique_name]
                display_name = list(unique_field_def.display_name)[0]
                coordinates = cropped_ui_fields['area']

                width = cropped_ui_fields['width']

                value = value_changes[display_name]

                trained_info[index] = prepare_trained_info(coordinates, display_name, value, width)
                index += 1


            value_extract_params = {    
                                        "case_id":case_id,
                                        "field_data":trained_info,
                                        'width' : width,
                                        'force_check' : 'no'
                                    }
        except:
            traceback.print_exc()
            print('not able to train')

        for table, fields in fields_w_name.items():
            fields.pop('Case ID', None)
            extraction_db.update(table, update=fields, where={'case_id': case_id})

        for table, fields in changed_fields_w_name.items():
            audit_data = {
                    "type": "update", "last_modified_by": verify_operator, "table_name": table, "reference_column": "case_id",
                    "reference_value": case_id, "changed_data": json.dumps(fields)
                }
            stats_db.insert_dict(audit_data, 'audit')

        return {'flag': True, 'message': 'Saved changes.'}
    except:
        logging.exception('Something went wrong saving changes. Check trace.')
        return {'flag': False, 'message': 'Something went wrong saving changes. Check logs.'}


def consume(broker_url='broker:9092'):
    try:
        route = 'save_changes'
        logging.info(f'Listening to topic: {route}')

        consumer = KafkaConsumer(
            bootstrap_servers=broker_url,
            value_deserializer=lambda value: json.loads(value.decode()),
            auto_offset_reset='earliest',
            group_id='save_changes',
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
            print(f'Listening to topic `{route}`...')
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
                tenant_id = data['tenant_id']
            except Exception as e:
                logging.warning(f'Recieved unknown data. [{data}] [{e}]')
                consumer.commit()
                continue
            
            queue_db = DB('queues', tenant_id=tenant_id, **db_config)
            kafka_db = DB('kafka', tenant_id=tenant_id, **db_config)

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
                logging.debug(f'`{route}` is the first topic in the group `{group}`.')
                logging.debug(f'Number of topics in group `{group}` is {len(group_messages)}')
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
                logging.debug(f'Calling function `save_changes`')
                result = save_changes(case_id, function_params, tenant_id)
            except:
                # Unlock the case.
                logging.exception(f'Something went wrong while saving changes. Check trace.')
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
