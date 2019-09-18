#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Jul 18 11:40:37 2019

@author: user
"""

from sqlalchemy import create_engine, exc
from time import time
import pandas as pd
import os

try:
    from app.ace_logger import Logging
except:
    from ace_logger import Logging
     
logging = Logging()

class Stats_db:
    def __init__(self, database = 'stats', host='172.31.45.112', user='root', password='AlgoTeam123', port='3306'):
        host = os.environ['HOST_IP']
        config = f'mysql://{user}:{password}@{host}:{port}/{database}?charset=utf8'
        print(config)
        retry = 1
        max_retry = 5
        try:
            self.engine = create_engine(config, 
                                connect_args={'connect_timeout': 2}, pool_recycle=300)
            while retry <= max_retry:
                try:
                    self.connection = self.engine.connect()
                    logging.info(f'Connection established succesfully to `{self.DATABASE}`! ({round(time() - start, 2)} secs to connect)')
                    break
                except Exception as e:
                    logging.warning(f'Connection failed. Retrying... ({retry}) [{e}]')
                    retry += 1
                    self.engine.dispose()
            # try:
            #     self.connection = self.engine.connect()
            # except Exception as e:
            #     print("Unable to connect to Database", e)                
        except Exception as e:
            print("Unable to create engine", e)
                
    def get_stats_master(self):
        result_proxy = self.connection.execute(f'SELECT * FROM `stats_master`')
        d, a = {}, []
        for row in result_proxy:
            for column, value in row.items():
                d = {**d, **{column : value}}
            a.append(d)
        stats_master_df = pd.DataFrame(a)
        return stats_master_df
    
    def get_active_stats(self):
        result_proxy = self.connection.execute(f'SELECT * FROM `active_stats`')
        d, a = {}, []
        for row in result_proxy:
            for column, value in row.items():
                d = {**d, **{column : value}}
            a.append(d)
        active_stats_df = pd.DataFrame(a)
        return active_stats_df
    
    def active_stats(self):
        stats_master_df = self.get_stats_master()
        active_stats_df = self.get_active_stats()
        self.close_db_object()
        return pd.merge(stats_master_df, active_stats_df, on = 'id', how = 'inner').to_dict(orient = 'records')

    def close_db_object(self):
        self.connection.close()
        self.engine.dispose()