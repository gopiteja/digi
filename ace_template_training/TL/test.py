import unittest
import json
import requests
from db_utils import DB

with open('test_cases.json') as f:
    test_cases = json.loads(f.read())

trained_db_config = {
    'host': "127.0.0.1",
    'user': "root",
    'password': "",
    'port': "3306",
}


def insert_into_db(db, data, table):
    db.insert_dict(data, table)


def delete_from_db(db, table, where):
    query = f"delete from {table} where "
    for key, value in where.items():
        query += key + ' = ' + value

    db.execute(query)


class MyTestCase(unittest.TestCase):
    def test_value_extract_(self):
        files = test_cases['files']
        data = files['2000470835']
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

        host = '127.0.0.1'
        port = 5002
        route = 'predict_field'
        headers = {'Content-type': 'application/json; charset=utf-8', 'Accept': 'text/json'}
        url = f"http://{host}:{port}/{route}"
        response = requests.post(url, json=input_data, headers=headers)

        delete_from_db(queue_db, 'process_queue', {'case_id': case_id})
        delete_from_db(queue_db, 'ocr_info', {'case_id': case_id})

        self.assertEqual(response.json(), output['data'])


if __name__ == '__main__':
    unittest.main()
