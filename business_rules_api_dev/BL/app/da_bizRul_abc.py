"""
@Author : Akshat Goyal
"""

from abc import ABC, abstractmethod

class BusinessRulesDAOABC(ABC):
    tables = None

    @abstractmethod
    def doSelect_get_data(self, table, field, where):
        """
        Args:
            table(str) : table_name,
            fields(list) : [field, ...],
            where(dict) : {field_name : field_value, ... }
                        validation
        Return:
            DataFrame

        Note:
            `fields` is the field to be returned
            `where` is condition on which data is to extracted 
        """

    @abstractmethod
    def doContains_get_lhs_field_name(self, table, field):
        """
        Args:
            table(str) : table_name
            field(str) : field_name

        Return:
            DataFrame
    
        Note:
            `fields` is the field to be returned
            'fields' : ['id', field_name]

        """

    @abstractmethod
    def doAssign_get_data(self, table, case_id):
        """
        Args:
            table(str) : table_name
            case_id(str)

        Return:
            DataFrame

        DataKnown:
            where : {'case_id' : case_id}
        
        Note:
            `where` is condition on which data is to extracted 
        """

    @abstractmethod
    def doAssign_insert_case_id(self, table, case_id):
        """
        Args:
            table : table_name
            case_id(str)

        Return:
            Insert Succesful or not

        DataKnown:
            'to_insert' : {'case_id' : case_id}
        """

    @abstractmethod
    def doAssign_update_case_id(self, table, to_update, case_id):
        """
        Args:
            table : table_name
            to_update : {field_name : field_value}
            case_id(str)

        Return:
            if the update is succeeful or not

        DataKnown:
            where : {'case_id' : case_id}
        """

    @abstractmethod
    def doUpdateQueue(self, case_id, queue):
        """
        Args:
            case_id(str) : case_id
            queue(str) : queue

        Returns:
            if the update is succeeful or not

        DataKnown:
            to_update : {'case_id':case_id},
            where : {'queue':queue}   
            table : 'process_queue'
        """
        
    @abstractmethod
    def update_queue_trace_get_trace_data(self, case_id):
        """
        Args:
            case_id(str)

        Returns:
            DataFrame

        DataKnown:
            'table' : 'trace_info'
            'field' : ['id', 'queue_trace', 'last_updated_dates']
            'where' : case_id
        """
        
    @abstractmethod
    def update_queue_trace_update(self, queue_trace, last_updated_dates, case_id):
        """
        Args:
            queue_trace(str)
            last_updated_dates(str)
            case_id(str)

        Returns:
            if the update is succeeful or not

        DataKnown:
            table : 'trace_info'
            to_update = {'queue_trace':queue_trace, 'last_updated_dates': last_updated_dates}
            where = {'case_id':case_id}
        """

    @abstractmethod
    def get_rules(self, stage):
        """
        Args:
            stage(str) : the stage of the business rule

        Return:
            DataFrame

        DataKnown:
            table : 'sequence_data'
            field=['id' , 'rule_string']
            where={'group':stage}
        """
    
    @abstractmethod
    def get_tables_data(self, case_id):
        """
        Args:
            case_id(str)

        Return :
            DataFrame

        DataKnown:
            table from which data has to be given something like this:
            tables = {
                "extraction" : ["business_rule","ocr","sap","validation"],
                "queues" : ["ocr_info"]
            }
        """
        
    @abstractmethod
    def update_table_update(self, table, to_update, case_id):
        """
        Args:
            table(str) : table_name
            to_update(dict) : {field_name : field_value}
            case_id(str)

        Return:
            if the update is succeeful or not

        DataKnown:
            where : {'case_id' : case_id}
        """
        
    @abstractmethod
    def validate_rules_get_data(self, case_id):
        """
        Args:
            case_id(str)

        Return:
            DataFrame

        DataKnown:
            table : 'validation'
            where : {'case_id' : case_id}
        """

    @abstractmethod
    def kafka_consume_get_messages(self):
        """
        Args:

        Return:
            DataFrame

        DataKnown:
            table : 'message_flow'
        """

    @abstractmethod
    def kafka_consume_get_data(self, case_id):
        """
        Args:
            case_id(str)

        Return:
            DataFrame

        DataKnown:
            table : 'business_rule'
            field : 'id', 'case_id'
            where : {'case_id' : case_id}
        """

    @abstractmethod
    def run_business_rule_update_case(self, case_meta, case_id):
        """
        Args:
            case_meta(dict):
            case_id:

        Return:
            if update successful or not

        DataKnown:
            table:
            where : case_id
        """

    @abstractmethod
    def update_error_msg(self, message, case_id):
        """
        Args:
            message : message that is to be added

        Return:
            if update successful or not

        DataKnown:
            table : process_queue
            update : `error_logs`
        """






