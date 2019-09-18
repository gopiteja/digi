"""
Author: Ashyam
Created Date: 18-02-2019
"""
import traceback

from datetime import datetime
from openpyxl import load_workbook, Workbook
from pandas import ExcelWriter
from pathlib import Path

from ace_logger import Logging

logging = Logging()

class ExportExcel(object):
    """
    Exports data to excel.

    Attributes:
        export_type (str): SPD, FPD or RPD (See README.md for details)
    """
    def __init__(self,
            export_type,
            exclude_fields=[],
            save_type=None,
            custom_name=None,
            field_mapping={}):
        logging.debug('Intializing Excel Export object.')
        self.export_type = export_type
        self.exclude_fields = exclude_fields
        self.save_type = save_type if save_type is not None else 'timestamp'
        self.custom_name = custom_name
        self.output_directory = Path('./output')
        self.field_mapping = field_mapping
        self.case_id = None

    # * TESTED & WORKING
    def change_field_names(self, data):
        """Return the dataframe with new field names based on the configuration."""

        logging.info('Changing field names...')
        logging.debug(f' - Before: {list(data)}')
        renamed_data = data.rename(columns=self.field_mapping)
        logging.debug(f' - After: {list(renamed_data)}')
        return renamed_data

    # * TESTED & WORKING
    def exclude_columns(self, data):
        """Excluded columns based on the configuration"""

        logging.info('Excluding columns (if any)...')
        default_columns = ['id', 'created_date', 'highlight', 'case_id']
        columns_to_exclude = default_columns + self.exclude_fields
        columns_to_exclude = [x for x in columns_to_exclude if x in list(data)]
        logging.debug(f' - Excluding: {columns_to_exclude}')

        return data.drop(columns_to_exclude, axis=1)

    def generate_file_name(self, case_id=None):
        if self.save_type == 'timestamp':
            current_time = datetime.now()
            return current_time.strftime(f'%Y%m%d%H%M%S')
            
        if case_id is not None:
            if self.save_type == 'case_id':
                file_stem = f'{case_id}'
            elif self.save_type == 'file_name':
                file_stem = f'FILENAME_OF_{case_id}' # ! GET FILE NAME OF THE CASE ID
        else:
            current_time = datetime.now()
            file_stem = current_time.strftime(f'%Y%m%d%H%M%S')

        return file_stem

    # * BASIC TESTING DONE. WORKING.
    def spd(self):
        logging.info('Format: Sheet Per Document (SPD)')
        unique_case_ids = list(self.data['case_id'].unique())

        # If there are multiple case IDs then the file should be saved using the timestamp
        # because we can not decide which case ID should be used as file name. There will
        # be only one excel file generated in this method.
        if len(unique_case_ids) > 1:
            logging.warning('Multiple case IDs detected. Saving file using timestamp.')
            self.save_type = 'timestamp'
            file_stem = self.generate_file_name()
        else:
            file_stem = self.generate_file_name(unique_case_ids[0])

        file_name = f'{file_stem}.xlsx'
        logging.debug(f' - Filename: {file_name}')

        # Set up the workbook
        save_path = self.output_directory / file_name  # Path of excel including filename
        book = Workbook()
        writer = ExcelWriter(save_path, engine='openpyxl')
        writer.book = book
        writer.book.remove(writer.book.worksheets[0])  # Remove default sheet

        for case_id in unique_case_ids:
            logging.debug(f' - Case ID: {case_id}')
            case_data = self.data_to_export.loc[self.data_to_export['case_id'] == case_id]
            case_data = self.exclude_columns(case_data)  # Filter columns out

            # Add each row of the DataFrame into
            # corresponding sheet
            logging.debug('Creating sheets for documents...')
            case_data.to_excel(writer, engine='openpyxl', index=False, sheet_name=case_id)

        logging.info(f'Saving excel file as {file_name}...')
        writer.save()

        return {'flag': True, 'message': 'Successfully exported to excel.'}

    # * BASIC TESTING DONE. WORKING.
    def fpd(self, sheet_name='Sheet1'):
        logging.info('Format: File Per Document (FPD)')
        unique_case_ids = list(self.data['case_id'].unique())

        for case_id in unique_case_ids:
            logging.debug(f' - Case ID: {case_id}')
            
            file_stem = self.generate_file_name(case_id)
            file_name = f'{file_stem}.xlsx'
            logging.debug(f'   - Filename: {file_name}')

            case_data = self.data_to_export.loc[self.data_to_export['case_id'] == case_id]
            case_data = self.exclude_columns(case_data) # Filter some columns out

            # Save data with new column headers. Have to transpose the row since
            # row is Series instead of a DataFrame.
            save_path = self.output_directory / file_name  # Path of excel including filename
            logging.info(f'Saving excel file as {file_name}...')
            case_data.to_excel(save_path, engine='openpyxl', index=False, sheet_name='Sheet 1')

        return {'flag': True, 'message': 'Successfully exported to excel.'}

    # * BASIC TESTING DONE. WORKING.
    def rpd(self):
        logging.info('Format: Rows Per Document (RPD)')
        unique_case_ids = list(self.data['case_id'].unique())

        # If there are multiple case IDs then the file should be saved using the timestamp
        # because we can not decide which case ID should be used as file name. There will
        # be only one excel file generated in this method.
        if len(unique_case_ids) > 1:
            logging.warning('Multiple case IDs detected. Saving file using timestamp.')
            self.save_type = 'timestamp'
            file_stem = self.generate_file_name()
        else:
            file_stem = self.generate_file_name(unique_case_ids[0])

        file_name = f'{file_stem}.xlsx'
        logging.debug(f' - Filename: {file_name}')

        save_path = self.output_directory / file_name  # Path of excel including filename

        filtered_data = self.exclude_columns(self.data_to_export)  # Filter some columns out
        logging.info(f'Saving excel file as {file_name}...')
        filtered_data.to_excel(save_path, engine='openpyxl', index=False, sheet_name='Sheet 1')

        return {'flag': True, 'message': 'Successfully exported to excel.'}

    def export(self, data):
        """
        Exports the data into excel.

        Args:
            data (DataFrame): Data that needs to be exported

        Returns:
            flag (bool): Flag for success status.
            message (str): Message to UI.
        """
        self.data = data

        self.data_to_export = self.change_field_names(self.data)

        if self.export_type == 'SPD':
            return self.spd()
        elif self.export_type == 'FPD':
            return self.fpd()
        elif self.export_type == 'RPD':
            return self.rpd()
        else:
            message = f'Unknown format `{self.export_type}`'
            logging.error(message)
            return {'flag': False, 'message': message}
