import json
import pymysql
import pytz
from datetime import datetime

def get_parameters():
    with open('parameters.json') as f:
        return json.loads(f.read())

params=get_parameters()
db_host=params['db']['host']
db_pass=params['db']['pass']
db_user=params['db']['user']
db_name=params['db']['database_name']

def execute_query(sql, db=db_name):
    data = None
    conn = pymysql.connect(host=db_host, user=db_user, password=db_pass, db=db_name,use_unicode=True, charset="utf8")
    try:
        a = conn.cursor()
        a.execute(sql)
        data = a.fetchall()
        conn.commit()
    except Exception as e:
        print(e)
        with open('sql.txt', 'w') as f:
            f.write(sql)
        # print(sql)
        conn.rollback()
    conn.close()
    return data

def get_time(format_type=0):
    f = ['%b %d %Y %I:%M %p', '%d-%m-%Y %I:%M:%S %p']
    try:
        format = f[format_type]
    except:
        format = f[0]

    tz = pytz.timezone('Asia/Kolkata')
    return datetime.now(tz).strftime(format)