import pandas as pd
import argparse
import pdb
import ast

from flask_cors import CORS
from flask import Flask, jsonify, request, redirect, url_for
from py_zipkin.zipkin import zipkin_span,ZipkinAttrs, create_http_headers_for_new_span

from ace_logger import Logging
from db_utils import DB
try:
    from app import app
except:
    app = Flask(__name__)
    cors = CORS(app)

logging = Logging()
logging_config = {
        'level': logging.DEBUG,
        'format': '%(asctime)s - %(levelname)s - %(filename)s @%(lineno)d : %(funcName)s() - %(message)s'
    }
logging.basicConfig(**logging_config)

db_config = {
    'host': os.environ['HOST_IP'],
    'user': os.environ['LOCAL_DB_USER'],
    'password': os.environ['LOCAL_DB_PASSWORD'],
    'port': os.environ['LOCAL_DB_PORT'],
}

@app.route('/store_config', methods=['POST'])
def store_config():
    """
    store the configuration for classification of email

    Args:
        label(str) : the label of the rule
        rules(json string) : the rules in the form of a json string
        tenant_id()

    return:
        {'flag':True} if success
        {'flag':False, 'msg':''} False
    """
    try:
        data = request.json

        logging.info( 'Data send to api')
        logging.info(data)

        to_store = {}
        try:
            to_store['rule_name'] = data['rule_name']
        except:
            msg = 'no rule_name found'
            logging.exception(msg)

            return jsonify({'flag':False, 'msg': msg})

        try:
            to_store['rules'] = data['rules']
        except:
            msg = 'no rules found'
            logging.exception(msg)

            return jsonify({'flag':False, 'msg':msg})

        try:
            to_store['tenant_id'] = data['tenant_id']
        except:
            msg = 'no tenant_id found'
            logging.exception(msg)

            return jsonify({'flag':False, 'msg': msg})

        db = DB('email', **db_config)
        to_store_df = pd.DataFrame([to_store])

        to_store_df.reset_index(drop=True)
        success = db.insert(to_store_df, 'email_categorization', if_exists='append',index=False)

        if success:
            return jsonify({'flag':True})
        else:
            return jsonify({'flag':False})
    except Exception as e:
        return jsonify({'flag':False})

@app.route('/get_metadata', methods=['POST'])
def get_filter_point():
    """
    Api which gives the data associated to the particular filter point

    args:
        filter_point(str) : the filter point for which the client wants data
        tenant_id() :

    return:
        {'flag':True, 'filter_point':[]} if succes
        {'flag':False} else
    """
    try:
        data = request.json

        logging.info( 'Data send to api')
        logging.info(data)

        filter_point = data['filter_point']

        logging.info("get data for filter points")
        logging.info("filter_point")
        tenant_id = data['tenant_id']

        db = DB('email', **db_config)
        email_data = db.get_all('table_name')


        return jsonify({'flag':True, 'filter_point':email_data[[filter_point,tenant_id]].to_dict('list')})
    except Exception as e:
        return jsonify({'flag':False})

@zipkin_span(service_name='email_api', span_name='categorize')
@app.route('/categorize', methods=['POST'])
def categorize():
    """
    Api which categorizes and saves the category in the associated column

    args:
        tenant_id() :
        id_of_emails([str]) :

    return:
        {'flag':True } if sucess
        {'flag':False } else
    """
    try:
        data = request.json

        logging.info( 'Data send to api')
        logging.info(data)

        try:
            tenant_id = data['tenant_id']
        except:
            msg = 'no tenant_id found'
            logging.exception(msg)

            return jsonify({'flag':False, 'msg': msg})

        try:
            id_emails = data['id']
        except:
            msg = 'no id of email found'
            logging.exception(msg)

            return jsonify({'flag':False, 'msg': msg})

        db = DB('email', **db_config)

        email_category_data = db.get_all('email_categorization')

        email_category_data = email_category_data[email_category_data['tenant_id'] == tenant_id]

        email_data = db.get_all('email_data')

        email_data = email_data[email_data['tenant_id'] == tenant_id]

        email_data = email_data[email_data['id'].isin(id_emails)]

        logging.debug("categorizing email")
        #for each row in email data table
        for _, row in email_data.iterrows():
            #for each rule
            for _, rule_string in email_category_data.iterrows():
                rules = ast.literal_eval(rule_string['rules'])
                #executing rule
                for key, value in rules.items():
                    if row[key] == value:
                        row['category'] = rule_string['rule_name']
                        query = 'update email_data set email_category = "{}" where id = {}'.format(rule_string['rule_name'], row['id'])
                        db.execute(query)
                    # email_data.loc[email_data[key] == value, 'category'] = rule_string['rule_name']

        logging.debug("categorizing email complete")
        return jsonify({'flag':True})
    except Exception as e:
        return jsonify({'flag':False})

@app.route('/stored_config', methods=['POST'])
def stored_config():
    """
    return the stored config for a specific tenant

    Args:
        tenant_id():

    return:
        {'flag':True} if succes
        {'flag':False, 'msg':''} False
    """
    try:
        data = request.json

        logging.info( 'Data send to api')
        logging.info(data)

        try:
            tenant_id = data['tenant_id']
        except:
            msg = 'no tenant_id found'
            logging.exception(msg)

            return jsonify({'flag':False, 'msg': msg})


        db = DB('email', **db_config)

        stored_data = db.get_all('email_categorization')

        if stored_data:
            return jsonify({'flag':True, 'data':stored_data.to_dict('list')})
        else:
            return jsonify({'flag':False, 'data':{}})
    except Exception as e:
        return jsonify({'flag':False, 'data':{}})

@app.route('/delete_stored_config', methods=['POST'])
def delete_stored_config():
    """
    delete the stored config associated with particular id

    Args:
        id ():

    return:
        {'flag':True} if succes
        {'flag':False, 'msg':''} False
    """
    try:
        data = request.json

        logging.info( 'Data send to api')
        logging.info(data)

        try:
            config_id = data['id']
        except:
            msg = 'no config ids found'
            logging.exception(msg)


            return jsonify({'flag':False, 'msg': msg})

        db = DB('email', **db_config)

        query = "delete from email_categorization where id in ({})".format(" ,".join(str(elm) for elm in config_id))

        if db.execute(query):
            return jsonify({'flag':True})
        else:
            return jsonify({'flag':False})
    except Exception as e:
        return jsonify({'flag':False})

if __name__ == '__main__':
    # init(autoreset=typerue) # Intialize colorama

    parser = argparse.ArgumentParser()
    parser.add_argument('-p', '--port', type=int, help='Port Number', default=5001)
    parser.add_argument('--host', type=str, help='Host', default='0.0.0.0')
    args = parser.parse_args()

    host = args.host
    port = args.port

    app.run(host=host, port=port, debug=True)
