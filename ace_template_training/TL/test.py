import unittest
import json
import requests
import os

from db_utils import DB
from ace_logger import Logging
logging = Logging()

"""
BEWARE RUNNING THIS SCRIPT in a environment will delete all of it's tables for the tenant.
"""

with open('./test_cases.json') as f:
    test_cases = json.loads(f.read())
    testFields_data = test_cases['test_fields']
    get_ocr_data_DATA = test_cases['get_ocr_data']
    train_DATA = test_cases['train']


trained_db_config = {
    'host': os.environ['HOST_IP'],
    'user': os.environ['LOCAL_DB_USER'],
    'password': os.environ['LOCAL_DB_PASSWORD'],
    'port': os.environ['LOCAL_DB_PORT'],
}


def insert_into_db(db, data, table):
    db.insert_dict(data, table)


def delete_from_db(db, table, where):
    query = f"delete from {table} where "
    for key, value in where.items():
        query += key + ' = ' + value

    db.execute(query)


class MyTestCase(unittest.TestCase):
    def test_testFields(self):
        # TODO also add the test for forcedcheck
        files = testFields_data['files']
        for file, data in files.items():
            ocr_data = json.loads(data['ocr'])
            input_data = data['input']
            output = data['output']

            tenant_id = input_data['tenant_id']
            case_id = input_data['case_id']

            queue_db = DB('queues', **trained_db_config, tenant_id=tenant_id)

            ocr_info = {'ocr_data': data['ocr'], 'case_id': case_id}
            process_queue = {'case_id': case_id, 'queue': 'templateExceptions'}

            insert_into_db(queue_db, ocr_info, 'ocr_info')
            insert_into_db(queue_db, process_queue, 'process_queue')

            host = os.environ['HOST_IP']
            port = 5002
            route = 'testFields'
            headers = {'Content-type': 'application/json; charset=utf-8', 'Accept': 'text/json'}
            url = f"http://{host}:{port}/{route}"
            response = requests.post(url, json=input_data, headers=headers)

            delete_from_db(queue_db, 'process_queue', {'case_id': case_id})
            delete_from_db(queue_db, 'ocr_info', {'case_id': case_id})

            print(response.json())
            self.assertEqual(response.json(), output)

    def test_train(self):
        # todo add for already existing template also
        files = train_DATA['files']
        for file, data in files.items():
            # ocr_data = json.loads(data['ocr'])
            input_data = data['input']
            output = data['output']

            tenant_id = input_data['tenant_id']
            case_id = input_data['case_id']

            template_db = DB('template_db', **trained_db_config, tenant_id=tenant_id)
            table_db = DB('table_db', **trained_db_config, tenant_id=tenant_id)
            queue_db = DB('queues', **trained_db_config, tenant_id=tenant_id)

            table_truncate = ['field_dict', 'field_neighbourhood_dict', 'field_quadrant_dict', 'trained_info_predicted',
                              'trained_info', 'vendor_list']

            for table in table_truncate:
                query = f"delete from {table}"
                template_db.execute(query)

            query = f"delete from table_info"
            table_db.execute(query)

            ocr_info = {'ocr_data': data['ocr'], 'case_id': case_id}
            process_queue = {'case_id': case_id, 'queue': 'templateExceptions'}

            # add case id to process queue with template exceptions
            # add case_id to ocr_info
            insert_into_db(queue_db, ocr_info, 'ocr_info')
            insert_into_db(queue_db, process_queue, 'process_queue')

            host = os.environ['HOST_IP']
            port = 5002
            route = 'train'
            headers = {'Content-type': 'application/json; charset=utf-8', 'Accept': 'text/json'}
            url = f"http://{host}:{port}/{route}"
            response = requests.post(url, json=input_data, headers=headers)

            total_test = 0
            test_passed = 0

            # check if table stored or not
            query = "select id, template_name, table_data from table_info"
            table_info = table_db.execute(query)

            try:
                total_test += 1
                self.assertEqual(json.loads(table_info.to_json(orient='records')), data['table_data'])
                test_passed += 1
            except:
                logging.exception("table_data is not stored")
                logging.info(table_info.to_json(orient='records'))
            finally:
                query = f"delete from table_info"
                table_db.execute(query)



            # check if table_keyword stored or not

            # check if field_dict updated or not
            query = "select id, field_type, variation from field_dict"
            field_dict = template_db.execute(query)

            try:
                total_test += 1
                self.assertEqual(json.loads(field_dict.to_json(orient='records')), data['field_dict'])
                test_passed += 1
            except:
                logging.error("field_dict is not stored")
                logging.info(field_dict.to_json(orient='records'))
            finally:
                query = f"delete from field_dict"
                template_db.execute(query)

            # check if field_neighbourhood_dict updated or not
            query = "select id, field, neighbourhood_dict, orientation_variation from field_neighbourhood_dict"
            field_neighbourhood_dict = template_db.execute(query)

            try:
                total_test += 1
                self.assertEqual(json.loads(field_neighbourhood_dict.to_json(orient='records')), data['field_neighbourhood_dict'])
                test_passed += 1
            except:
                logging.error("field_neighbourhood_dict is not stored")
                logging.info(field_neighbourhood_dict.to_json(orient='records'))
            finally:
                query = f"delete from field_neighbourhood_dict"
                template_db.execute(query)


            # check if field_quadrant_dict updated or not
            query = "select id, field, quadrant from field_quadrant_dict"
            field_quadrant_dict = template_db.execute(query)


            try:
                total_test += 1
                self.assertEqual(json.loads(field_quadrant_dict.to_json(orient='records')), data['field_quadrant_dict'])
                test_passed += 1
            except:
                logging.error("field_quadrant_dict is not stored")
                logging.info(field_quadrant_dict.to_json(orient='records'))
            finally:
                query = f"delete from field_quadrant_dict"
                template_db.execute(query)

            # check if trained_info updated or not
            query = "select id, template_name, field_data, checkbox_data, " \
                    "header_ocr, footer_ocr, address_ocr, unique_fields, operator from trained_info"
            trained_info = template_db.execute(query)

            try:
                total_test += 1
                self.assertEqual(json.loads(trained_info.to_json(orient='records')), data['trained_info'])
                test_passed += 1
            except:
                logging.exception("trained_info is not stored")
                logging.info(trained_info.to_json(orient='records'))
            finally:
                query = f"delete from trained_info"
                template_db.execute(query)


            #
            # check if we are storing in ui_train data or not
            # check if ocr in extraction updated or not
            # check if stats_db updated or not
            #
            # check if process_queue is updated with template_name and queue
            # check if queue_trace if updated or not
            #
            # check if cluster id is there for files in same cluster


            delete_from_db(queue_db, 'process_queue', {'case_id': case_id})
            delete_from_db(queue_db, 'ocr_info', {'case_id': case_id})


            try:
                total_test += 1
                self.assertEqual(response.json()['flag'], True)
                test_passed += 1
            except:
                logging.error("test failed somewhere")

            self.assertEqual(total_test, test_passed)


    def test_get_ocr_data(self):
        # TODO many moving parts in db beware of those
        files = get_ocr_data_DATA['files']
        for file, data in files.items():
            # ocr_data = json.loads(data['ocr'])
            input_data = data['input']
            output = data['output']

            tenant_id = input_data['tenant_id']
            case_id = input_data['case_id']

            template_db = DB('template_db', **trained_db_config, tenant_id=tenant_id)
            queue_db = DB('queues', **trained_db_config, tenant_id=tenant_id)

            table_truncate = ['field_dict', 'field_neighbourhood_dict', 'field_quadrant_dict', 'trained_info_predicted',
                              'trained_info', 'vendor_list']

            for table in table_truncate:
                query = f"delete from {table}"
                template_db.execute(query)

            ocr_info = {'ocr_data': data['ocr'], 'case_id': case_id}
            process_queue = {'case_id': case_id, 'queue': 'templateExceptions', 'document_type': 'folder'}

            insert_into_db(queue_db, ocr_info, 'ocr_info')
            insert_into_db(queue_db, process_queue, 'process_queue')

            host = os.environ['HOST_IP']
            port = 5002
            route = 'get_ocr_data_training'
            headers = {'Content-type': 'application/json; charset=utf-8', 'Accept': 'text/json'}
            url = f"http://{host}:{port}/{route}"
            response = requests.post(url, json=input_data, headers=headers)

            delete_from_db(queue_db, 'process_queue', {'case_id': case_id})
            delete_from_db(queue_db, 'ocr_info', {'case_id': case_id})
            delete_from_db(template_db, 'trained_info_predicted', {'case_id': case_id})

            self.assertEqual(response.json(), output)

    def test_retrain(self):
        self.assertEqual(True, True)

    def test_force_template(self):
        self.assertEqual(True, True)

    def test_table(self):

        self.assertEqual(True, True)



if __name__ == '__main__':
    unittest.main()
