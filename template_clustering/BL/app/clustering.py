# -*- coding: utf-8 -*-
"""
Created on Thu Mar 14 13:54:54 2019

@author: Khan
"""

import argparse
import json
import traceback

import ast
import ntpath
import numpy as np

from datetime import datetime
from dateutil.parser import parse
from flask import Flask, request, jsonify
from flask_cors import CORS
from sklearn.metrics import silhouette_score
from sklearn.cluster import AgglomerativeClustering
from sklearn.feature_extraction.text import TfidfVectorizer

try:
    from app.db_utils import DB
    from app.ace_logger import Logging
except:
    from db_utils import DB
    from ace_logger import Logging

from app import app


logging = Logging().getLogger('ace')

def get_field_dict(tenant_id):
    """
    :return field_dict from db
    """
    db_config = {
        'host': 'template_db',
        'port': '3306',
        'user': 'root',
        'password': 'root',
        'tenant_id': tenant_id
    }
    db = DB('template_db', **db_config)
    db_data = db.get_all('field_dict')
    query_result = json.loads(db_data.to_json(orient='records'))

    fields = {}
    for row in query_result:
        field_type = row['field_type']
        variations = ast.literal_eval(row['variation'])
        fields[field_type] = variations
    return fields

@app.route('/cluster', methods=['POST', 'GET'])
# @zipkin_span(service_name='clustering_app', span_name='cluster')
def cluster():
    '''
    Clusters a list of documents whose filenames
    '''
    try:
        try:
            data = request.json
            tenant_id = data['tenant_id']
        except:
            tenant_id = None
        db_config = {
            'host': 'queue_db',
            'port': '3306',
            'user': 'root',
            'password': 'root',
            'tenant_id': tenant_id
        }
        db = DB('queues', **db_config)

        query = "SELECT * from process_queue where queue = 'Template Exceptions'"
        template_exception = db.execute(query)

        case_ids = template_exception.case_id.tolist()

        ocr_data = []
        for case_id in case_ids:
            query = 'SELECT id, ocr_data FROM `ocr_info` WHERE `case_id`=%s'
            params = [case_id]
            ocr_info = db.execute(query, params=params)
            ocr_data.append(list(ocr_info.ocr_data)[0])

        files =  [(x[0], x[1]) for x in zip(case_ids, ocr_data)]

        # No clustering to be done
        if len(files) == 1:
            query = 'UPDATE `process_queue` SET `cluster`=1 WHERE `case_id`=%s'
            db.execute(query, params=[files[0][0]])
            logging.info(f'Updated cluster to `1` for case ID `{files[0][0]}`')
            return

        # Get the list of keywords for all fields from db
        db_text = []
        for kwds in get_field_dict(tenant_id).values():
            for kwd in kwds:
                for w in kwd.split():
                    db_text.append(w.lower())

            plain_text_top = []
            plain_text_middle = []
            plain_text_bottom = []
            invoices = []

            for file in files:
                text_top = []
                text_middle = []
                text_bottom = []
                ocr_data = json.loads(file[1])[0]

                if not ocr_data:
                    continue

                invoices.append(file[0])

                height = []
                for word in ocr_data:
                    height.append(int(word['top']))

                min_ = min(height)
                max_ = max(height)

                by_3 = (max_ - min_)/3

                ocr_data_top = []
                ocr_data_middle = []
                ocr_data_bottom = []
                for word in ocr_data:
                    if word['top'] < (by_3 + min_):
                        ocr_data_top.append(word)
                    elif word['top'] > (2*by_3 + min_):
                        ocr_data_bottom.append(word)
                    else:
                        ocr_data_middle.append(word)

                for i in ocr_data_top:
                    text_top.append(i['word'].lower())
                text_top = [word for word in text_top if word not in db_text]
                plain_text_top.append(' '.join(text_top))

                for i in ocr_data_middle:
                    text_middle.append(i['word'].lower())
                text_middle = [word for word in text_middle if word not in db_text]
                plain_text_middle.append(' '.join(text_middle))

                for i in ocr_data_bottom:
                    text_bottom.append(i['word'].lower())
                text_bottom = [word for word in text_bottom if word not in db_text]
                plain_text_bottom.append(' '.join(text_bottom))

            vect = TfidfVectorizer(stop_words = 'english')
            tfidf = vect.fit_transform(plain_text_top)
            match_top = (tfidf * tfidf.T).A.tolist()

            vect = TfidfVectorizer(stop_words = 'english')
            tfidf = vect.fit_transform(plain_text_middle)
            match_middle = (tfidf * tfidf.T).A.tolist()

            vect = TfidfVectorizer(stop_words = 'english')
            tfidf = vect.fit_transform(plain_text_bottom)
            match_bottom = (tfidf * tfidf.T).A.tolist()


            no_files = len(invoices)

            match = (np.array(match_top)*3+np.array(match_middle)+np.array(match_bottom)*2)/6
            match = match.tolist()

            final_dict = {}
            clusters = []

            for k in range(len(match)):
                cluster = []
                for i in range(len(invoices)):
                    if no_files > 0 and i == k or match[k][i] >= 0.6:
                    	cluster.append(invoices[i])
                    	if invoices[i] not in cluster:
                    		match.pop(i)
                    		no_files -= 1
                if cluster not in clusters:
                    clusters.append(cluster)


            query = 'UPDATE `process_queue` SET `cluster`=%s WHERE `case_id`=%s'
            for k in range(len(clusters)):
                for case in clusters[k]:
                    params = [k+1, case]
                    db.execute(query, params=params)
                    logging.info(f'Updated cluster to `{k+1}` for case ID `{case}`')

                final_dict[str(k+1)] = clusters[k]
            return final_dict
    except Exception as e:
        return jsonify({'flag': False, 'message':'System error! Please contact your system administrator.'})
