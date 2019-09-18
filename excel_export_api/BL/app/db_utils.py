"""
Author: Ashyam Zubair
Created Date: 14-02-2019
"""
import pandas as pd
import sqlalchemy
import os

from ace_logger import Logging
from sqlalchemy import create_engine, exc


class DB(object):
    def __init__(self, database, host='127.0.0.1', user='root', password='', port='3306', tenant_id=None):
        """
        Initialization of databse object.

        Args:
            databse (str): The database to connect to.
            host (str): Host IP address. For dockerized app, it is the name of
                the service set in the compose file.
            user (str): Username of MySQL server. (default = 'root')
            password (str): Password of MySQL server. For dockerized app, the
                password is set in the compose file. (default = '')
            port (str): Port number for MySQL. For dockerized app, the port that
                is mapped in the compose file. (default = '3306')
            tenant_id (str): Name of the tenant to connect to.
        """
        self.logging = Logging()

        self.HOST = os.environ['HOST_IP']
        self.USER = user
        self.PASSWORD = password
        self.PORT = port
        self.DATABASE = f'{tenant_id}_{database}' if tenant_id is not None and tenant_id else database

        # Create the engine
        try:
            config = f'mysql://{self.USER}:{self.PASSWORD}@{self.HOST}:{self.PORT}/{self.DATABASE}?charset=utf8'
            logging.info(
                f'Creating engine for database `{self.DATABASE}`...')
            logging.debug(f'Databse config: {config}')
            self.engine = create_engine(config)
            logging.info(f'Databse engine created.')
        except:
            logging.exception('Error creating engine.')
            return

    def execute(self, query, **kwargs):
        """
        Executes an SQL query.

        Args:
            query (str): The query that needs to be executed.
            params (list/tuple/dict): List of parameters to pass to in the query.

        Returns:
            (DataFrame) A pandas dataframe containing the data from the executed
            query. (None if an error occurs)
        """
        logging.info(f'Executing query...')
        data = None

        try:
            data = pd.read_sql(query, self.engine, index_col='id', **kwargs)
        except exc.ResourceClosedError:
            logging.debug(
                'Query does not have any data to return. Probably because query is not a `SELECT` statement.')
            pass
        except:
            logging.exception('Error executing query')

        logging.info(f'Executed query.')
        return data.where((pd.notnull(data)), None)

    def insert(self, data, table, **kwargs):
        """
        Write records stored in a DataFrame to a SQL database table.

        Args:
            data (DataFrame): The DataFrame that needs to be write to SQL database.
            table (str): The table in which the rcords should be written to.
            kwargs: Keyword arguments for pandas to_sql function.
                See https://pandas.pydata.org/pandas-docs/stable/reference/api/pandas.DataFrame.to_sql.html
                to know the arguments that can be passed.

        Returns:
            (bool) True is succesfully inserted, else false.
        """
        logging.info(f'Inserting dataframe into `{table}`...')
        logging.debug(f'Data:\n{data}')

        try:
            data.to_sql(table, engine, **kwargs)
            try:
                logging.debug('Making `id` column as primary key.')
                self.execute(f'ALTER TABLE `{table}` ADD PRIMARY KEY (`id`);')
            except:
                logging.warning(
                    'Failed to make `id` column as primary key.')
                pass
            logging.info(f'Inserted data into `{table}` successfully.')
            return True
        except:
            logging.exception('Error inserting data.')
            return False

    def insert_dict(self, data, table):
        """
        Insert dictionary into a SQL database table.

        Args:
            data (DataFrame): The DataFrame that needs to be write to SQL database.
            table (str): The table in which the rcords should be written to.

        Returns:
            (bool) True is succesfully inserted, else false.
        """
        logging.info(f'Inserting dictionary data into `{table}`...')
        logging.debug(f'Data:\n{data}')

        try:
            column_names = []
            params = []

            for column_name, value in data.items():
                column_names.append(f'`{column_name}`')
                params.append(value)

            logging.debug(f'Column names: {column_names}')
            logging.debug(f'Params: {params}')

            columns_string = ', '.join(column_names)
            param_placeholders = ', '.join(['%s'] * len(column_names))

            query = f'INSERT INTO {table} ({columns_string}) VALUES ({param_placeholders})'

            return self.execute(query, params=params)
        except:
            logging.exception('Error inserting data.')
            return False

    def update(self, table, update=None, where=None, force_update=False):
        """
        Updates a table in the SQL database.

        Args:
            table (str): The table in which the record(s) needs to be updated.
            update (dict): Key-value pair of column name and the new value to be updated.
                Eg: {'column_1': value_1} => SET column_1=value_1
            where (dict): Key-value pair of column name and the value to check.
                Eg: {'column_1': value_1} => WHERE column_1=value_1
            force_update: If where parameter is None/empty, by default updation will fail.
                If force_update flag is True it will update all rows in the table.

        Returns:
            (bool) True if succesfully updated, else false.
        """
        logging.info(f'Updating table `{table}`...')
        logging.debug(f'Update values: {update}')
        logging.debug(f'Where conditions: {where}')
        logging.debug(f'Force update: {force_update}')

        try:
            set_clause = []
            set_value_list = []
            where_clause = []
            where_value_list = []

            if where is not None and where:
                for set_column, set_value in update.items():
                    set_clause.append(f'`{set_column}`=%s')
                    set_value_list.append(set_value)
                set_clause_string = ', '.join(set_clause)
            else:
                logging.warning(
                    f'Update dictionary is None/empty. Must have some update clause.')
                return False

            if where is not None and where:
                for where_column, where_value in where.items():
                    where_clause.append(f'{where_column}=%s')
                    where_value_list.append(where_value)
                where_clause_string = ' AND '.join(where_clause)
                query = f'UPDATE `{table}` SET {set_clause_string} WHERE {where_clause_string}'
            else:
                if force_update:
                    query = f'UPDATE `{table}` SET {set_clause_string}'
                else:
                    message = 'Where dictionary is None/empty. If you want to force update every row, pass force_update as True.'
                    logging.warning(f'{message}')
                    return False

            params = set_value_list + where_value_list
            self.execute(query, params=params)
            logging.info(f'Updated table `{table}` successfully.')
            return True
        except:
            logging.exception('Error occured while updating table.')
            return False

    def get_column_names(self, table):
        """
        Get all column names from an SQL table.

        Args:
            table (str): Name of the table from which column names should be extracted.

        Returns:
            (list) List of headers. (None if an error occurs)
        """
        logging.info(f'Getting column names of table `{table}`...')
        try:
            return list(self.execute(f'SELECT * FROM `{table}`'))
        except:
            logging.warning(f'Error occured while getting column names.')
            return

    def get_all(self, table, condition=None):
        """
        Get all data from an SQL table.

        Args:
            table (str): Name of the table from which data should be extracted.
            condition (dict): Key-value pair of column name and the value to check.
                Eg: {'column_1': value_1} => WHERE column_1=value_1

        Returns:
            (DataFrame) A pandas dataframe containing the data. (None if an error
            occurs)
        """
        logging.info(f'Getting all data from table `{table}`...')

        if condition is not None:
            logging.info(f' - Applying condition(s)...')

            where_clause = []
            where_value_list = []

            for where_column, where_value in condition.items():
                where_clause.append(f'{where_column}=%s')
                where_value_list.append(where_value)
            where_clause_string = ' AND '.join(where_clause)
            query = f'SELECT * FROM `{table}` WHERE {where_clause_string}'
            return self.execute(query, params=where_value_list)
        else:
            return self.execute(f'SELECT * FROM `{table}`')

    def get_latest(self, data, group_by_col, sort_col):
        """
        Group data by a column containing repeated values and get latest from it by
        taking the latest value based on another column.

        Example:
        Get the latest products
            id     product   date
            220    6647     2014-09-01
            220    6647     2014-10-16
            826    3380     2014-11-11
            826    3380     2015-05-19
            901    4555     2014-09-01
            901    4555     2014-11-01

        The function will return
            id     product   date
            220    6647     2014-10-16
            826    3380     2015-05-19
            901    4555     2014-11-01

        Args:
            data (DataFrame): Pandas DataFrame to query on.
            group_by_col (str): Column containing repeated values.
            sort_col (str): Column to identify the latest record.

        Returns:
            (DataFrame) Contains the latest records. (None if an error occurs)
        """
        logging.info(f'Getting all latest data...')
        logging.debug(f'Group By Column: {group_by_col}')
        logging.debug(f'Sort Column: {sort_col}')
        logging.debug(f'Data:\n{data}')

        try:
            return data.sort_values(sort_col).groupby(group_by_col).tail(1)
        except KeyError as e:
            logging.warning(f'Column `{e.args[0]}` does not exist.')
            return None
        except:
            logging.exception(
                f'Error occured while getting the latest data.')
            return None
