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

class Stats_db:
    def __init__(self, database = 'stats', host=None, user=None, password=None, port='3306',tenant_id = None):
        host = os.environ['HOST_IP']
        user = os.environ['LOCAL_DB_USER']
        password = os.environ['LOCAL_DB_PASSWORD']
        port = os.environ['LOCAL_DB_PORT']
        if tenant_id == 'None':
            tenant_db = f'{database}'
        else:
            tenant_db = f'{tenant_id}_{database}'

        config = f'mysql://{user}:{password}@{host}:{port}/{tenant_db}?charset=utf8'
        print(config)
        try:
            self.engine = create_engine(config, 
                                 pool_size=10, 
                                 max_overflow=20)
            try:
                self.connection = self.engine.connect()
            except Exception as e:
                print("Unable to connect to Database", e)                
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
